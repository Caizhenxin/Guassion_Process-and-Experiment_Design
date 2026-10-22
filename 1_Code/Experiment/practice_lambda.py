#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""λ 天花板机制：SPE 随练习的轨迹 + λ/τ_P 的可辨识性（敏感性分析，不改主模型）。

背景
----
SPE_Database 的 `Datasets/11_Practice-Effect/Mapping_Sensitivity_Report.md`（2026-09-29）
已经给出 self 天花板族的解析判据：

    f_self(P) = 1 − λ·(1 − f_other(P))，  λ* = (1+α₂)/(1+α₁) = 0.663（v 口径）/

    0.475（RT 口径，sigmoid/exp）/ 0.433（延迟指数）

即「SPE 随练习收缩」只在 λ < λ* 成立。**但那是旧 GP 模型的乘性参数化**；本项目是加法
（`d_self − d_other = β_S + β_SP·f_P`），所以要换算成本项目口径重算一遍：

    v_other(P) = v_other0 + g_P·f_P                     f_P = 1 − e^{−P/τ_P}
    v_self(P)  = v_other(P) + Δ_S·[λ + (1−λ)·f_P]

- λ = 1 → SPE 恒定（等价于现行 `β_SP = 0`）；
- λ = 0 → self 已到天花板，SPE 随 f_P 衰减到 0（严格等于 `β_SP = −β_S`、τ 与 β_P 共享）；
- 0 < λ < 1 → 部分饱和，SPE 收敛到 λ·Δ_S。

本脚本做两件事（都只读主模型、不改它）：
1. **轨迹**：λ ∈ {1, .75, .5, .25, 0} × P ∈ {0, 8, 32, 120} 模拟 SPE_RT / SPE_ACC，和
   HuYQ Exp3 的归一化实测曲线并排（不同横轴，只做方向对照）。
2. **可辨识性**：4 个组间剂量点上 (λ, τ_P) 的 Fisher 信息 ⇒ SE(λ) 随每组人数怎么变。
   若 SE(λ) 跨不过 1，就只能报「方向不定」，不能报「支持天花板假说」。

产物
----
- `2_Data/Generate_Data/_practice/practice_lambda.csv`（逐格读数）
- `2_Data/Generate_Data/_practice/practice_lambda_ident.csv`（SE(λ) / SE(τ_P) 表）
- `2_Data/Generate_Data/_practice/practice_lambda_meta.json`
- `3_Figures/_practice/fig9_practice_lambda.png`

跑法：`python 1_Code/Experiment/practice_lambda.py`
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

from make_figures import setup_matplotlib          # noqa: E402
from spe_locus import simulate                     # noqa: E402

plt, _LANG = setup_matplotlib("zh")

DATA = ROOT / "2_Data" / "Generate_Data" / "_practice"
FIG = ROOT / "3_Figures" / "_practice"

# 与 gen_model_data.GEN_TRUTH 同口径的基线（只在 P 维上加练习）
V_OTHER0 = 0.80          # P 趋于 0 时的他人漂移
GAIN_P = 0.35            # 练习能带来的漂移增益上限（≈ beta_P）
DELTA_S = 0.30           # 自我相对他人的漂移优势（≈ beta_S）
A_REF = 1.566
T0 = 0.19
P_LEVELS = (0, 8, 32, 120)      # 主实验的四档（组间）
TAU_P = 30.0                    # 练习饱和常数（≈ GEN_TRUTH.tau_P）
LAMBDAS = (1.0, 0.75, 0.5, 0.25, 0.0)

# HuYQ Exp3 实测（01_HuYQ_Exp3/exp3_summary_spe.csv，overall，归一化到 baseline）
HUYQ_RT = {"Prac": 25.4, "Base": 25.4, "T1": 35.9, "T2": 26.9, "T3": 25.4,
           "T4": 30.1, "T5": 12.9, "T6": 4.9, "T7": 13.4, "Formal": 7.6}


def f_practice(p: float, tau_p: float) -> float:
    return 1.0 - np.exp(-float(p) / tau_p)


def drift_pair(p: float, lam: float, tau_p: float = TAU_P) -> tuple[float, float]:
    """返回 (v_other, v_self)。

    SPE 的**初始优势**是 Δ_S；练习把差距按 f_P 侵蚀，残留比例为 λ：

        v_self − v_other = Δ_S·[1 − (1−λ)·f_P]

    λ = 1 ⇒ 差距恒定（等价现行 β_SP = 0）；λ = 0 ⇒ 差距被练习完全吃掉。
    ⚠️ 注意别写成 Δ_S[λ+(1−λ)f_P]——那会让差距随练习**变大**，方向正好反了
    （第一版就是这么错的，跑出「λ 越小 SPE 越涨」的自相矛盾结果）。
    """
    f = f_practice(p, tau_p)
    v_o = V_OTHER0 + GAIN_P * f
    v_s = v_o + DELTA_S * (1.0 - (1.0 - lam) * f)
    return v_o, v_s


def run_point(p: float, lam: float, n_subjects: int, n_trials: int, seed: int,
              tau_p: float = TAU_P, dt: float = 1e-4) -> dict:
    """一个 (P, λ) 格：同一被试两条件共享噪声 ⇒ 差的估计不被抽样噪声淹没。"""
    v_o, v_s = drift_pair(p, lam, tau_p)
    base = np.random.default_rng(seed)
    d_rt, d_acc, rt_s, rt_o = [], [], [], []
    for sid in range(n_subjects):
        sd = base.normal(0.0, 0.10)                    # 被试间漂移差异
        sub_seed = seed * 7919 + sid
        rng = np.random.default_rng(sub_seed)
        rt1, side1, _ = simulate(n_trials, v_s + sd, A_REF, T0, rng, dt=dt)
        rng = np.random.default_rng(sub_seed)          # 同一条噪声流
        rt0, side0, _ = simulate(n_trials, v_o + sd, A_REF, T0, rng, dt=dt)
        ok1, ok0 = ~np.isnan(rt1), ~np.isnan(rt0)
        if ok1.sum() < 20 or ok0.sum() < 20:
            continue
        d_rt.append((np.median(rt0[ok0]) - np.median(rt1[ok1])) * 1000.0)
        d_acc.append((side1[ok1] == 1).mean() - (side0[ok0] == 1).mean())
        rt_s.append(np.median(rt1[ok1]) * 1000.0)
        rt_o.append(np.median(rt0[ok0]) * 1000.0)
    d_rt = np.array(d_rt)
    d_acc = np.array(d_acc)
    n = len(d_rt)
    return {"P": p, "lambda": lam, "tau_P": tau_p, "n_subj": n,
            "spe_rt_ms": float(d_rt.mean()), "se_rt_ms": float(d_rt.std(ddof=1) / np.sqrt(n)),
            "spe_acc": float(d_acc.mean()), "se_acc": float(d_acc.std(ddof=1) / np.sqrt(n)),
            "rt_self_ms": float(np.mean(rt_s)), "rt_other_ms": float(np.mean(rt_o)),
            "v_self": v_s, "v_other": v_o}


def identifiability(rows: pd.DataFrame, n_subjects_grid=(20, 40, 80)) -> pd.DataFrame:
    """4 个剂量点上 (λ, τ_P) 的 Fisher 信息 ⇒ SE。

    用一阶近似：∂SPE_RT/∂θ 由网格差分给出，残差 SD 取被试间 SD（不是均值 SE），
    因为组间设计的观测单位是被试。
    """
    base = rows[(rows["lambda"] == 0.5) & (rows["tau_P"] == TAU_P)].sort_values("P")
    lam_hi = rows[(rows["lambda"] == 0.75) & (rows["tau_P"] == TAU_P)].sort_values("P")
    lam_lo = rows[(rows["lambda"] == 0.25) & (rows["tau_P"] == TAU_P)].sort_values("P")
    tau_hi = rows[(rows["lambda"] == 0.5) & (rows["tau_P"] == 45.0)].sort_values("P")
    if base.empty or lam_hi.empty or tau_hi.empty:
        return pd.DataFrame()

    d_lam = ((lam_hi["spe_rt_ms"].to_numpy() - lam_lo["spe_rt_ms"].to_numpy()) / 0.5)
    d_tau = ((tau_hi["spe_rt_ms"].to_numpy() - base["spe_rt_ms"].to_numpy()) / 15.0)
    sd_subject = float(base["se_rt_ms"].iloc[0] * np.sqrt(base["n_subj"].iloc[0]))
    jac = np.column_stack([d_lam, d_tau])
    out = []
    for n in n_subjects_grid:
        info = (jac.T @ jac) * (n / sd_subject ** 2)
        try:
            cov = np.linalg.inv(info)
            se = np.sqrt(np.clip(np.diag(cov), 0, None))
        except np.linalg.LinAlgError:
            se = np.array([np.nan, np.nan])
        out.append({"n_per_group": n, "se_lambda": float(se[0]), "se_tau_P": float(se[1]),
                    "sd_subject_ms": sd_subject,
                    "cond_jac": float(np.linalg.cond(jac))})
    return pd.DataFrame(out)


def fig_practice(rows: pd.DataFrame, ident: pd.DataFrame, out: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0))
    colors = {1.0: "#2c6fbb", 0.75: "#55a868", 0.5: "#dd8452", 0.25: "#c44e52", 0.0: "#7f7f7f"}

    ax = axes[0]
    for lam in sorted(LAMBDAS, reverse=True):
        s = rows[(rows["lambda"] == lam) & (rows["tau_P"] == TAU_P)].sort_values("P")
        if s.empty:
            continue
        ax.errorbar(s["P"], s["spe_rt_ms"], yerr=s["se_rt_ms"], marker="o", ms=4,
                    lw=1.6, capsize=3, color=colors[lam], label=f"λ = {lam:g}")
    ax.axhline(0, color="0.6", lw=0.8, ls=":")
    ax.set_xlabel("练习试次数 P（组间剂量）")
    ax.set_ylabel("SPE_RT = 他人 − 自我（ms）")
    ax.set_title("① 模型侧：λ 决定 SPE 随练习的方向")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    for lam in sorted(LAMBDAS, reverse=True):
        s = rows[(rows["lambda"] == lam) & (rows["tau_P"] == TAU_P)].sort_values("P")
        if s.empty:
            continue
        ax.errorbar(s["P"], s["spe_acc"], yerr=s["se_acc"], marker="o", ms=4,
                    lw=1.6, capsize=3, color=colors[lam], label=f"λ = {lam:g}")
    ax.axhline(0, color="0.6", lw=0.8, ls=":")
    ax.set_xlabel("练习试次数 P（组间剂量）")
    ax.set_ylabel("SPE_ACC = 自我 − 他人")
    ax.set_title("② 正确率侧的同一族轨迹")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2]
    names = list(HUYQ_RT)
    vals = np.array([HUYQ_RT[k] for k in names])
    base = vals[names.index("Base")]
    ax.plot(range(len(names)), vals / base, marker="o", color="#8e44ad", lw=1.6,
            label="HuYQ Exp3 实测（归一化到 Base）")
    s = rows[(rows["lambda"] == 0.0) & (rows["tau_P"] == TAU_P)].sort_values("P")
    if not s.empty:
        v = s["spe_rt_ms"].to_numpy()
        v = v / v[0] if v[0] != 0 else v
        ax.plot(np.linspace(0, len(names) - 1, len(v)), v, marker="s", ls="--",
                color="#c44e52", lw=1.4, label="模型 λ=0（归一化到 P=0，横轴为示意对齐）")
    ax.axhline(1.0, color="0.7", lw=0.8, ls=":")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, fontsize=7)
    ax.set_ylabel("SPE_RT（相对 Base）")
    ax.set_title("③ 与实测对照：只比方向，不比剂量轴")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)

    fig.suptitle("λ 天花板机制：练习 × SPE 的方向判据（模拟，非人类被试）", fontsize=12)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="λ 天花板机制敏感性分析")
    ap.add_argument("--n-subjects", type=int, default=15)
    ap.add_argument("--n-trials", type=int, default=288)
    ap.add_argument("--seed", type=int, default=20261024)
    a = ap.parse_args(argv)

    t0 = time.time()
    DATA.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    rows = []
    print("[1/3] 主网格：λ × P …")
    for lam in LAMBDAS:
        for p in P_LEVELS:
            r = run_point(p, lam, a.n_subjects, a.n_trials, a.seed)
            rows.append(r)
            print(f"  λ={lam:<5g} P={p:<4d} SPE_RT={r['spe_rt_ms']:+6.1f}±{r['se_rt_ms']:4.1f} ms "
                  f"SPE_ACC={r['spe_acc']:+.3f}")
    print("[2/3] τ_P 方向（λ=0.5）…")
    for tau in (20.0, 45.0):
        for p in P_LEVELS:
            r = run_point(p, 0.5, a.n_subjects, a.n_trials, a.seed, tau_p=tau)
            rows.append(r)

    df = pd.DataFrame(rows)
    df.to_csv(DATA / "practice_lambda.csv", index=False, encoding="utf-8-sig")

    print("[3/3] 可辨识性 …")
    ident = identifiability(df)
    if not ident.empty:
        ident.to_csv(DATA / "practice_lambda_ident.csv", index=False, encoding="utf-8-sig")
        print(ident.round(3).to_string(index=False))

    fig = fig_practice(df, ident, FIG / "fig9_practice_lambda.png")
    (DATA / "practice_lambda_meta.json").write_text(json.dumps({
        "v_other0": V_OTHER0, "gain_p": GAIN_P, "delta_s": DELTA_S, "a_ref": A_REF,
        "t0": T0, "P_levels": list(P_LEVELS), "tau_P": TAU_P,
        "lambdas": list(LAMBDAS), "n_subjects": a.n_subjects, "n_trials": a.n_trials,
        "seed": a.seed, "dt": 1e-4, "huYQ_rt": HUYQ_RT,
        "note": "λ 族只改练习维的自我增益；λ=1 等价现行 β_SP=0。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] {fig}（{time.time() - t0:.0f} s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
