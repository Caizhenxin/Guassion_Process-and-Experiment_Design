# -*- coding: utf-8 -*-
"""power_recovery.py —— 「为什么是 55 人」：N_精度 与 N_区分 两条曲线（D122）

背景
----
`intake.py` 的统计层用解析式 ``n = (SD / 目标 SE)²`` 给每组定编（AIPE 口径，
Maxwell, Kelley & Rausch 2008）。但它**建立在一个假设上**：端点量在跨被试上
近似正态、且 SE(mean) = SD/√N。本脚本做两件事：

* **N_精度**：用真值群体模拟「N 人 × 576 试次」的批次，逐人算三个端点量
  （ΔRT 中位、Δacc、分位斜率），直接量出 **跨被试 SD**，再用
  ``n = (SD/目标SE)²`` 反推每组要几人；并用自助重抽样量出 SE(N) 的实际曲线，
  **检验正态近似**（若两条线重合，"解析定编"就是可信的）。
* **N_区分**：M-T1（ρ 自由）与 M-T3（ρ ≡ 1）是**嵌套**关系（见 `twophase.py`），
  所以"两个模型能不能分开"= "ρ 能不能显著偏离 1"。逐人算似然比
  ``LRT = 2(ℓ_M1 − ℓ_M3)``，再按独立同分布合成 N 人的总 LRT，给出
  「区分所需人数」与「80% 检验力所需人数」。

两个 N 回答两个不同问题（见 `5_Reference/03_论文写作/真实数据分析_首轮结果_20261024.md`
与 D122 的推导）：
  * N_精度 —— 端点量估得够不够准（决定"效应量能否报出 CI"）；
  * N_区分 —— 两个机制假设能不能分开（决定"理论取舍有没有证据"）。

用法
----
    python -X utf8 1_Code/Experiment/power_recovery.py --mode precision --n-pool 100
    python -X utf8 1_Code/Experiment/power_recovery.py --mode discriminate --n-subj 8
    python -X utf8 1_Code/Experiment/power_recovery.py --mode all

产物
----
``2_Data/Generate_Data/_power/``：
  `power_precision.csv`（逐组 × 逐指标的 SD / 定编）、
  `power_precision_curve.csv`（SE(N) 与检验力曲线）、
  `power_discriminate.csv`（逐人 LRT）、
  `power_meta.json`（真值、种子、耗时、口径）。
``3_Figures/_power/``：`fig12_power_precision.png`、`fig13_power_discriminate.png`。

口径提醒
--------
* 生成器用 Euler（`twophase.simulate_euler_subject`，dt=1e-4，|Δacc| ≈ 0.005），
  理由见该函数 docstring：解析逆 CDF 抽样在本设计上要 70 s/人。
* 逐人参数从群体真值抽（`simulate.draw_subject_params`，`mode="truncate"`）——
  这是**被试间异质性**的唯一来源，也是 SD 的来源；不抽就只剩二项噪声。
* 端点量的清洗口径与 `real_data_check.clean` 一致：只用正式段、丢掉
  ``RT ≤ 120 ms`` 与 ``RT > W + 50 ms`` 的试次。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

OUT = ROOT / "2_Data" / "Generate_Data" / "_power"
FIG_OUT = ROOT / "3_Figures" / "_power"

from likelihood import fit_mle, trials_from_arrays          # noqa: E402
from mapping import MappingParams, match_lin_to_exp          # noqa: E402
from recover_group import GROUP_INIT_LIN, GROUP_TRUTH_EXP   # noqa: E402
from simulate import (SUBJECT_SD, build_design, design_arrays,  # noqa: E402
                      draw_subject_params)
from twophase import fit_mle_step, simulate_euler_subject    # noqa: E402

# ------------------------------------------------------------------ 口径常量
#: 设计（与真实实验一致：4 P 组 × 4 T × 3 W × 2 身份 × 2 匹配 × 12 重复）
P_GROUPS = (0.0, 8.0, 32.0, 120.0)
T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
N_CELL = 48                       # 4T × 3W × 2 身份 × 2 匹配
TRIALS = N_CELL * N_REP           # = 576

#: 目标 SE（与 `intake.TARGET` 完全一致，改这里必须同步改那里）
TARGET = {"drt_med": 10.0, "d_acc": 0.03, "slope": 30.0}
METRIC_CN = {"drt_med": "ΔRT 中位 (ms)", "d_acc": "Δacc（比例）", "slope": "分位斜率 (ms)"}

#: 分位点（与 `real_data_check.spe_per_subject` 一致）
QS = (0.10, 0.30, 0.50, 0.70, 0.90)

#: 真值：lin 形状（与 `recover_group.GROUP_TRUTH_LIN` 同一把尺子换算）
TRUTH_EXP = GROUP_TRUTH_EXP
TRUTH_LIN, _ = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)

DT_GEN = 1e-4                     # Euler 步长（|Δacc| ≈ 0.005，3.1 s/人）
CHI2_1_95 = 3.841458820694124

#: 真实数据的读数（D119/D120，正式段口径），用作对账
REAL_REF = {"sd_drt_med": 32.6, "sd_d_acc": 0.112, "sd_slope": 89.1,
            "mean_drt_med": 38.8, "mean_d_acc": 0.052, "mean_slope": 44.0}


# ------------------------------------------------------------------ 单被试
def endpoints(rt: np.ndarray, side: np.ndarray, om: np.ndarray,
              is_self: np.ndarray, is_match: np.ndarray,
              W: np.ndarray) -> dict:
    """把一名被试的试次级数组压成三个端点量（口径同 `real_data_check`）。"""
    ok = (om == 0) & (rt > 0.120) & (rt <= W + 0.050)
    rt_ms = rt * 1000.0
    correct = side == np.where(is_match == 1, 1, -1)

    acc, quant = {}, {}
    for lab, mask in (("other", (is_self == 0) & ok), ("self", (is_self == 1) & ok)):
        acc[lab] = float(correct[mask].mean()) if mask.any() else np.nan
        quant[lab] = np.quantile(rt_ms[mask], QS) if mask.sum() >= 10 else np.full(len(QS), np.nan)

    drt = quant["other"] - quant["self"]          # 他人 − 自我 > 0 ⇒ 自我更快
    slope = float(np.polyfit(QS, drt, 1)[0]) if np.all(np.isfinite(drt)) else np.nan
    return {"drt_med": float(drt[2]), "d_acc": acc["self"] - acc["other"],
            "slope": slope,
            "acc_self": acc["self"], "acc_other": acc["other"],
            "n_clean": int(ok.sum())}


def simulate_one(P: float, rng: np.random.Generator, design: dict,
                 arrays: tuple, rho: float = 1.0, dt: float = DT_GEN) -> dict:
    """模拟一名被试（群体真值抽一次个体参数），返回端点量与试次数组。"""
    p_sub = draw_subject_params(TRUTH_LIN, rng, mode="truncate")
    sim = simulate_euler_subject(design, p_sub, rho, rng, dt=dt)
    ep = endpoints(sim["rt"], sim["side"], sim["omission"],
                   design["is_self"], design["is_match"], design["W"])
    ep.update({"P": P, "rt": sim["rt"], "side": sim["side"],
               "omission": sim["omission"]})
    return ep


# ------------------------------------------------------------------ N_精度
def se_boot(x: np.ndarray, n: int, rng: np.random.Generator, B: int = 2000) -> float:
    """从池里**有放回**抽 N 人、重复 B 次，返回均值的标准误（实测曲线）。"""
    x = np.asarray(x, dtype=float)
    idx = rng.integers(0, x.size, size=(B, n))
    return float(np.std(x[idx].mean(axis=1), ddof=0))


def n_needed(sd: float, target: float) -> int:
    return int(np.ceil((sd / target) ** 2))


def power_at(effect: float, se: float, alpha: float = 0.05) -> float:
    """双侧 z 检验的检验力（正态近似）。"""
    from math import erf, sqrt
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    z = abs(effect) / se - 1.959963984540054
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def mode_precision(n_pool: int, seed: int, B: int = 2000) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    rows = []
    for P in P_GROUPS:
        design = build_design(P, T_LEVELS, W_LEVELS, N_REP)
        arrays = design_arrays(design)
        for i in range(n_pool):
            ep = simulate_one(P, rng, design, arrays)
            rows.append({"P": P, "subj": i, **{k: ep[k] for k in
                                               ("drt_med", "d_acc", "slope",
                                                "acc_self", "acc_other", "n_clean")}})
        print(f"  [P={P:5.0f}] {n_pool} 人完成（累计 {time.perf_counter() - t0:.0f} s）")
    df = pd.DataFrame(rows)

    # ---- 逐组 + 全体：SD → 定编
    stat = []
    for lab, sub in [("全体", df)] + [(f"组 P={P:.0f}", df[df.P == P]) for P in P_GROUPS]:
        for m in TARGET:
            x = sub[m].dropna().to_numpy()
            sd = float(x.std(ddof=1))
            stat.append({"group": lab, "metric": m, "n_subj": int(x.size),
                         "mean": float(x.mean()), "sd": sd,
                         "target_se": TARGET[m], "n_need": n_needed(sd, TARGET[m]),
                         "power_at_mean": power_at(abs(float(x.mean())), sd / np.sqrt(max(1, x.size)))})
    stat = pd.DataFrame(stat)

    # ---- SE(N) 实测曲线 + 检验力曲线
    curve = []
    ns = sorted({n for n in (4, 6, 8, 10, 12, 16, 20, 24, 30, 40, 50) if n <= n_pool})
    for lab, sub in [("全体", df)] + [(f"组 P={P:.0f}", df[df.P == P]) for P in P_GROUPS]:
        for m in TARGET:
            x = sub[m].dropna().to_numpy()
            if x.size < 4:
                continue
            mu, sd = float(x.mean()), float(x.std(ddof=1))
            for n in ns:
                se_b, se_n = se_boot(x, n, rng, B), sd / np.sqrt(n)
                curve.append({"group": lab, "metric": m, "N": n,
                              "se_boot": se_b, "se_norm": se_n,
                              "power_boot": power_at(abs(mu), se_b),
                              "power_norm": power_at(abs(mu), se_n)})
    curve = pd.DataFrame(curve)

    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "power_precision_subjects.csv", index=False, encoding="utf-8-sig")
    stat.to_csv(OUT / "power_precision.csv", index=False, encoding="utf-8-sig")
    curve.to_csv(OUT / "power_precision_curve.csv", index=False, encoding="utf-8-sig")

    print("\n[逐组 SD 与定编]")
    print(f"{'组':>10}{'指标':>16}{'n':>5}{'均值':>10}{'SD':>10}{'目标SE':>9}{'需 n':>7}")
    for r in stat.itertuples():
        print(f"{r.group:>10}{METRIC_CN[r.metric]:>16}{r.n_subj:>5}"
              f"{r.mean:>10.3f}{r.sd:>10.4f}{r.target_se:>9.2f}{r.n_need:>7}")
    return {"stat": stat, "curve": curve, "df": df, "seconds": time.perf_counter() - t0}


# ------------------------------------------------------------------ N_区分
def _clamp_init(p, ov: dict):
    """把初值夹进 `bounds_override` 的框内。

    ⚠️ 2026-10-25 的教训：群体初值 ``GROUP_INIT_LIN.t0 = 0.25`` 会**超过**
    ``t0`` 的动态上界 ``min(rt_min − 5 ms, 0.60)``（本数据 rt_min ≈ 0.24 s），
    起点落在可行域之外。scipy 不会报错，而是从一个非法点开始迭代，实测把
    M-T3 的 ℓ 从 −465 拖到 −497（差 32 个对数单位），于是 LRT 变成
    "两个坏拟合之比"（0.85，而 oracle 是 28.1）。修法：拟合前先夹。
    """
    kw = {}
    for name, (lo, hi) in ov.items():
        v = float(getattr(p, name))
        kw[name] = float(min(max(v, lo), hi))
    return p.replace(**kw) if kw else p


def per_subject_lrt(P: float, rho_true: float, rng: np.random.Generator,
                    design: dict, arrays: tuple, dt: float = DT_GEN) -> dict:
    """生成一人数据 → 拟合 M-T3（ρ≡1）与 M-T1（ρ 自由）→ 返回 LRT 与 ρ̂。"""
    p_sub = draw_subject_params(TRUTH_LIN, rng, mode="truncate")
    sim = simulate_euler_subject(design, p_sub, rho_true, rng, dt=dt)
    tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *arrays)
    kept = sim["omission"] == 0
    rt_min = float(np.nanmin(sim["rt"])) if kept.any() else 0.30
    ov = {"t0": (0.05, min(0.60, max(rt_min - 0.005, 0.06)))}
    names = ["d_ref", "beta_T", "beta_S", "beta_ST", "a_ref", "delta_a", "t0", "dz_S"]
    # 两套拟合都从**群体初值**出发（不用真值起跑：真值起跑必落在真值附近，
    # 会把 LRT 抬得过于乐观；这一步是"实战检验力"而非"理想检验力"）。
    init = _clamp_init(GROUP_INIT_LIN, ov)
    # 预算刻意收紧（n_restart=1、maxfun=6000）：n_restart=2 时第二个起点偶尔会落进
    # 坏区域并跑满 maxfun=20000 ⇒ 单人 >25 min。`_probe_rho_fit.py` 已验证四种起点
    # 收敛到同一解，所以单起点够用。
    f3 = fit_mle(tr, names, init, n_restart=1, seed=int(rng.integers(1 << 30)),
                 maxiter=250, maxfun=6000, bounds_override=ov, gtol=1e-7, ftol=1e-12)
    f1 = fit_mle_step(tr, names, f3["params"], rho_init=1.0, n_restart=1,
                      seed=int(rng.integers(1 << 30)), maxiter=250, maxfun=6000,
                      bounds_override=ov, gtol=1e-7, ftol=1e-12, n_x=71)
    lrt = 2.0 * (float(f1["loglik"]) - float(f3["loglik"]))
    acc = float(np.mean(sim["side"][kept & (design["is_match"] == 1)] == 1)) if kept.any() else float("nan")
    return {"P": P, "rho_true": rho_true, "lrt": lrt, "rho_hat": float(f1["rho"]),
            "ll_m3": float(f3["loglik"]), "ll_m1": float(f1["loglik"]),
            "acc": acc, "omit": float(np.mean(sim["omission"]))}


def mode_discriminate(n_subj: int, seed: int, rho_true: float = 0.60,
                      rho_null: float = 1.0, B: int = 4000) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    P = 120.0
    design = build_design(P, T_LEVELS, W_LEVELS, N_REP)
    arrays = design_arrays(design)
    rows = []
    for rho in (rho_null, rho_true):
        for i in range(n_subj):
            r = per_subject_lrt(P, rho, rng, design, arrays)
            r["subj"] = i
            rows.append(r)
            print(f"  [ρ={rho:.2f} s{i:02d}] LRT={r['lrt']:8.3f}  ρ̂={r['rho_hat']:.3f}"
                  f"  acc={r['acc']:.3f}  ({time.perf_counter() - t0:.0f} s)")
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "power_discriminate.csv", index=False, encoding="utf-8-sig")

    alt = df[df.rho_true == rho_true]["lrt"].to_numpy()
    nul = df[df.rho_true == rho_null]["lrt"].to_numpy()
    print(f"\n[ρ={rho_null}] 假阳性率 = {np.mean(nul > CHI2_1_95):.1%}（名义 5%）")
    print(f"[ρ={rho_true}] 单人拒绝率 = {np.mean(alt > CHI2_1_95):.1%}，"
          f"LRT 均值 {alt.mean():.2f} ± {alt.std(ddof=1):.2f}")

    # 合成 N 人：总和分布由自助重抽样近似（独立性成立，因每人一套独立噪声）
    curve = []
    ns = [3, 5, 8, 10, 12, 16, 20, 24, 30, 40, 50, 60]
    for n in ns:
        thr = _chi2_crit(n, 0.95)
        hit = np.array([float(np.sum(rng.choice(alt, size=n))) for _ in range(B)])
        fpr = np.array([float(np.sum(rng.choice(nul, size=n))) for _ in range(B)])
        curve.append({"N": n, "crit_95": thr,
                      "power": float(np.mean(hit > thr)),
                      "type1_emp": float(np.mean(fpr > thr)),
                      "mean_lrt": float(n * alt.mean())})
    curve = pd.DataFrame(curve)
    curve.to_csv(OUT / "power_discriminate_curve.csv", index=False, encoding="utf-8-sig")

    print("\n[区分所需人数]")
    print(f"{'N':>4}{'χ²(0.95) 临界':>16}{'80% 检验力':>12}{'单侧拒绝率':>11}")
    n80 = next((int(r.N) for r in curve.itertuples() if r.power >= 0.80), None)
    for r in curve.itertuples():
        print(f"{r.N:>4}{r.crit_95:>16.2f}{r.power:>12.1%}")
    print(f"\n⇒ 80% 检验力需要约 {n80} 人（ρ_true={rho_true} vs ρ=1）")
    return {"df": df, "curve": curve, "n80": n80, "seconds": time.perf_counter() - t0}


def _chi2_crit(df: int, q: float) -> float:
    """χ²(df) 的 q 分位（Wilson–Hilferty 近似，df ≥ 3 足够准）。"""
    from math import sqrt
    z = 1.6448536269514722 if abs(q - 0.95) < 1e-9 else 1.2815515655446004
    a = 2.0 / (9.0 * df)
    return float(df * (1.0 - a + z * sqrt(a)) ** 3)


# ------------------------------------------------------------------ 图
def _style() -> None:
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.dpi"] = 150
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


COLORS = {0.0: "#c0392b", 8.0: "#e67e22", 32.0: "#27ae60", 120.0: "#2980b9"}


def fig_precision(stat: pd.DataFrame, curve: pd.DataFrame, out: Path) -> None:
    import matplotlib.pyplot as plt
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
    titles = {"drt_med": "① ΔRT 中位：解析定编 vs 模拟", "d_acc": "② Δacc：两条曲线重合吗",
              "slope": "③ 分位斜率：最难估的端点"}
    for ax, m in zip(axes, ("drt_med", "d_acc", "slope")):
        sub = curve[curve.metric == m]
        for P in P_GROUPS:
            s = sub[sub.group == f"组 P={P:.0f}"]
            ax.plot(s.N, s.se_boot, "-o", ms=3, lw=1.2, color=COLORS[P],
                    label=f"P={P:.0f}（实测）")
        s = sub[sub.group == "全体"]
        ax.plot(s.N, s.se_norm, "--", lw=1.6, color="#34495e", label="全体 解析 SD/√N")
        ax.set_xscale("log")
        ax.set_xlabel("每组人数 N（对数）")
        ax.set_ylabel("SE", color="#2c3e50")
        tgt = TARGET[m]
        ax.axhline(tgt, ls=":", lw=1.2, color="#8e44ad")
        ax.text(4.2, tgt * 1.03, f"目标 SE = {tgt:g}", fontsize=8, color="#8e44ad")
        ax.set_title(titles[m])

        ax2 = ax.twinx()
        pw = sub[sub.group == "全体"]
        ax2.plot(pw.N, pw.power_boot, "-.", lw=1.4, color="#16a085", label="全体 检验力")
        ax2.axhline(0.8, ls="--", lw=1.0, color="#16a085", alpha=0.6)
        ax2.set_ylabel("检验力（双侧 α=.05）", color="#16a085")
        ax2.set_ylim(0, 1.02)
        ax2.grid(False)

        r = stat[(stat.group == "全体") & (stat.metric == m)]
        if len(r):
            n_now = int(r.n_need.iloc[0])
            ax.axvline(n_now, ls="--", lw=1.0, color="#7f8c8d")
            ax.text(n_now * 1.05, ax.get_ylim()[1] * 0.55, f"需 {n_now} 人",
                    fontsize=8, color="#7f8c8d")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right")
    fig.suptitle("N_精度：模拟群体（真值 4 个 P 组 × 576 试次）推出的「每组要几人」（D122）",
                 fontsize=11)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] {out}")


def fig_discriminate(df: pd.DataFrame, curve: pd.DataFrame, rho_true: float, out: Path) -> None:
    import matplotlib.pyplot as plt
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3))
    ax = axes[0]
    for i, (rho, col, lab) in enumerate(((1.0, "#7f8c8d", "ρ = 1（M-T3 为真）"),
                                         (rho_true, "#c0392b", f"ρ = {rho_true}（M-T1 为真）"))):
        v = df[df.rho_true == rho]["lrt"].to_numpy()
        jit = (i - 0.5) * 0.25 + np.linspace(-0.09, 0.09, v.size)
        ax.plot(v, jit, "o", ms=8, alpha=0.85, color=col,
                label=f"{lab}，n={v.size}，均值 {v.mean():.1f}")
    ax.axvline(CHI2_1_95, ls="--", color="#2c3e50", lw=1.2)
    ax.text(CHI2_1_95 * 1.03, 0.28, "χ²(1,.95)=3.84", fontsize=8)
    ax.set_xlabel("单人 LRT = 2(ℓ_M1 − ℓ_M3)"); ax.set_ylabel("")
    ax.set_yticks([]); ax.set_ylim(-0.6, 0.6)
    ax.set_title("① 单人似然比：两个真值下的分布（每档 6 人）")
    ax.legend(fontsize=8, loc="upper left")

    ax = axes[1]
    ax.plot(curve.N, curve.power, "-o", ms=4, color="#2980b9")
    ax.axhline(0.8, ls="--", color="#c0392b", lw=1.1)
    n80 = next((int(r.N) for r in curve.itertuples() if r.power >= 0.80), None)
    if n80:
        ax.axvline(n80, ls=":", color="#c0392b")
        ax.text(n80 * 1.06, 0.35, f"80% 需 {n80} 人", fontsize=9, color="#c0392b")
    ax.set_xscale("log")
    ax.set_xticks([3, 5, 10, 20, 30, 60]); ax.set_xticklabels(["3", "5", "10", "20", "30", "60"])
    ax.set_xlabel("被试人数 N（对数轴）"); ax.set_ylabel("区分 M-T1 vs M-T3 的检验力")
    ax.set_ylim(0, 1.02)
    ax.set_title(f"② 区分所需人数（ρ 真值 {rho_true}，合成 N 人总 LRT）")
    fig.suptitle("N_区分：掩蔽是否打断积累（ρ）需要多少人才能判出来（D122）", fontsize=11)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] {out}")


# ------------------------------------------------------------------ 主程序
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="N_精度 与 N_区分 的模拟定编（D122）")
    ap.add_argument("--mode", choices=["precision", "discriminate", "all"], default="precision")
    ap.add_argument("--n-pool", type=int, default=100, help="每组模拟多少人（N_精度）")
    ap.add_argument("--n-subj", type=int, default=8, help="每个 ρ 档拟合多少人（N_区分）")
    ap.add_argument("--rho", type=float, default=0.60, help="N_区分 的备择 ρ 真值")
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--boot", type=int, default=2000)
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"seed": args.seed, "dt": DT_GEN, "trials": TRIALS,
            "P_groups": list(P_GROUPS), "target": TARGET,
            "truth": {k: float(v) for k, v in TRUTH_LIN.as_dict().items()
                      if k in ("d_ref", "beta_P", "tau_P", "beta_T", "beta_S",
                               "beta_SP", "beta_ST", "a_ref", "delta_a", "t0")},
            "subject_sd": {k: float(v) for k, v in SUBJECT_SD.items()},
            "modes": {}}

    if args.mode in ("precision", "all"):
        print("=" * 92)
        print(f"N_精度：每组 {args.n_pool} 人 × {TRIALS} 试次（Euler dt={DT_GEN:g}）")
        print("=" * 92)
        r = mode_precision(args.n_pool, args.seed, B=args.boot)
        if r["curve"].empty:
            print("[skip] 池太小，画不出 SE(N) 曲线（N ≤ n_pool 的格点为空）")
        else:
            fig_precision(r["stat"], r["curve"], FIG_OUT / "fig12_power_precision.png")
        meta["modes"]["precision"] = {"seconds": round(r["seconds"], 1),
                                      "n_pool": args.n_pool}

    if args.mode in ("discriminate", "all"):
        print("\n" + "=" * 92)
        print(f"N_区分：P=120、每档 {args.n_subj} 人（逐人拟合 M-T3 与 M-T1）")
        print("=" * 92)
        rd = mode_discriminate(args.n_subj, args.seed, rho_true=args.rho, B=args.boot * 2)
        fig_discriminate(rd["df"], rd["curve"], args.rho,
                         FIG_OUT / "fig13_power_discriminate.png")
        meta["modes"]["discriminate"] = {"seconds": round(rd["seconds"], 1),
                                         "n_subj": args.n_subj, "rho": args.rho,
                                         "n80": rd["n80"]}

    (OUT / "power_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[meta] {OUT / 'power_meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
