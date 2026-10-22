"""SPE 该建模在哪一层？——自我优势效应（SPE）三种作用位点的敏感性分析。

动机：当前模型把 SPE 全部放在**漂移**上（`beta_S` 加在 `d_stim` 上）。本文的模拟显示，
这样做的结果是「正确率差很大（+8 pp）、RT 差很小（约 +10–25 ms）」，而且 RT 差在两阶段模型
里还被掩蔽后的 `ρ` 二次衰减——因为在 `t > T` 之后自我/他人的漂移差被乘上同样的 ρ。
于是出现一个必须回答的设计问题：

    如果文献里的 SPE 是「RT 整体前移 20–40 ms、各分位大致均匀」，
    那么漂移型 SPE 根本生不出这个形状，模型选错了作用位点。

本脚本把三种位点摆在一起比较（同一群人、同一真值，只改 SPE 的落点）：

| 位点 | 实现 | 可预期签名 |
|---|---|---|
| `drift` | `v_self = v + 0.30` | 正确率明显上升；RT 差**随分位放大**（慢试次受益更多） |
| `boundary` | `a_self = 0.93·a` | 正确率上升＋RT 前移；RT 差**也随分位放大**，但幅度更大 |
| `t0` | `t0_self = t0 − 20 ms` | RT **各分位近似等量前移**；正确率**不变**（这一步是关键判别点） |

判据（写进论文方法章）：
- 若观测到「RT 差各分位近似相等、正确率差≈0」⇒ 支持 `t0`；
- 若「RT 差随分位放大、正确率差明显」⇒ 支持 `drift` 或 `boundary`；
- `drift` 与 `boundary` 靠 **CRF（条件正确率函数）斜率** 区分：降边界会同时抬高快慢试次的正确率，
  提漂移主要抬高慢试次的正确率。

产物：`3_Figures/_compare/fig8_spe_locus.png` + `spe_locus.csv`
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

from make_figures import setup_matplotlib  # noqa: E402

OUT = ROOT / "2_Data" / "Generate_Data" / "_compare"
FIG_OUT = ROOT / "3_Figures" / "_compare"

# 真值（与 gen_model_data.GEN_TRUTH 同一口径；这里只取需要的几个）
V_OTHER = 0.90          # 他人试次在 T=150 ms、W=1800 ms 处的漂移
A_REF = 1.566
T0 = 0.19
RHO = 0.8
T_STIM = 0.15
W_DEADLINE = 1.8
Z_RATIO = 0.5

LOCI = {
    "drift": {"dv": 0.30, "da": 1.0, "dt0": 0.0},
    "boundary": {"dv": 0.0, "da": 0.93, "dt0": 0.0},
    "t0": {"dv": 0.0, "da": 1.0, "dt0": -0.020},
    "drift+t0": {"dv": 0.18, "da": 1.0, "dt0": -0.012},
}


def simulate(n_trials: int, v: float, a: float, t0: float, rng,
             dt: float = 5e-5, chunk: int = 200) -> tuple[np.ndarray, np.ndarray, float]:
    """两阶段阶跃 Euler 模拟；返回 (RT 秒, 选择侧 +1/-1/0, 遗漏率)。"""
    n_steps = int(round(W_DEADLINE / dt)) + 1
    t = np.arange(n_steps) * dt
    step = np.where(t <= T_STIM, v, RHO * v)
    out = np.full(n_trials, np.nan)
    side = np.zeros(n_trials, int)
    sqrt_dt = np.sqrt(dt)
    for s in range(0, n_trials, chunk):
        m = min(chunk, n_trials - s)
        noise = rng.normal(0.0, sqrt_dt, size=(m, n_steps))
        xs = Z_RATIO * a + np.cumsum(step[None, :] * dt + noise, axis=1)
        up = xs >= a
        dn = xs <= 0.0
        hit = up | dn
        any_hit = hit.any(axis=1)
        idx = np.argmax(hit, axis=1)
        rows = np.arange(m)
        rt = np.where(any_hit, t[idx] + t0, np.nan)
        out[s:s + m] = rt
        side[s:s + m] = np.where(any_hit, np.where(up[rows, idx], 1, -1), 0)
    return out, side, float(np.isnan(out).mean())


def run_cell(locus: str, n_subjects: int, n_trials: int, seed: int) -> pd.DataFrame:
    """每个被试的两个条件用**同一条噪声流**（共同随机数）⇒ 差的估计不再被抽样噪声淹没。"""
    spec = LOCI[locus]
    base = np.random.default_rng(seed)
    rows = []
    for sid in range(n_subjects):
        v_sd = base.normal(0.0, 0.10)
        a_sd = base.normal(0.0, 0.06)
        sub_seed = seed * 10000 + sid
        for ident in (0, 1):
            v = V_OTHER + v_sd + (spec["dv"] if ident else 0.0)
            a = A_REF * (spec["da"] if ident else 1.0) + a_sd
            t0 = T0 + (spec["dt0"] if ident else 0.0)
            rng = np.random.default_rng(sub_seed)          # 同一被试两条件同一噪声
            rt, side, _ = simulate(n_trials, v, a, t0, rng)
            ok = ~np.isnan(rt)
            rows.append(pd.DataFrame({
                "subject": f"{locus}-{sid}", "locus": locus, "is_self": ident,
                "rt_ms": rt[ok] * 1000.0,
                "correct": (side[ok] == 1).astype(int),
            }))
    return pd.concat(rows, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    qs = (0.1, 0.3, 0.5, 0.7, 0.9)
    rows = []
    for locus, sub in df.groupby("locus", sort=False):
        rec = {"locus": locus}
        for q in qs:
            o = np.quantile(sub[sub.is_self == 0].rt_ms, q)
            s = np.quantile(sub[sub.is_self == 1].rt_ms, q)
            rec[f"d_rt_p{int(q * 100)}"] = o - s
        rec["d_acc"] = (sub[sub.is_self == 1].correct.mean()
                        - sub[sub.is_self == 0].correct.mean())
        rec["rt_med_other"] = float(np.median(sub[sub.is_self == 0].rt_ms))
        rec["rt_med_self"] = float(np.median(sub[sub.is_self == 1].rt_ms))
        rec["d_rt_med"] = rec["rt_med_other"] - rec["rt_med_self"]
        rows.append(rec)
    return pd.DataFrame(rows)


def make_figure(summary: pd.DataFrame, df: pd.DataFrame, path: Path) -> None:
    import matplotlib.pyplot as plt

    plt, _ = setup_matplotlib("zh")
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.0))
    colors = {"drift": "#1f77b4", "boundary": "#e4772a", "t0": "#2ca02c",
              "drift+t0": "#9467bd"}
    labels = {"drift": "漂移（当前模型）", "boundary": "边界", "t0": "非决策时间",
              "drift+t0": "漂移 + 非决策时间（混合）"}
    qs = [0.1, 0.3, 0.5, 0.7, 0.9]
    ax = axes[0]
    for _, rec in summary.iterrows():
        ax.plot([int(q * 100) for q in qs], [rec[f"d_rt_p{int(q*100)}"] for q in qs],
                marker="o", lw=1.8, color=colors[rec["locus"]],
                label=f"{labels[rec['locus']]}（Δacc {rec['d_acc']:+.3f}）")
    ax.axhline(0, color="0.6", lw=0.8)
    ax.set_xlabel("RT 分位")
    ax.set_ylabel("ΔRT 他人 − 自我（ms）")
    ax.set_title("① ΔRT 的分位形状：漂移会放大尾巴，非决策时间是整体平移")
    ax.legend(fontsize=7.5, frameon=False)

    # ② 签名空间：横轴 = ΔRT 随分位的斜率（尾部 vs 首部），纵轴 = Δ正确率
    ax = axes[1]
    offs = {"drift": (8, -14), "boundary": (-46, 10), "t0": (8, 8), "drift+t0": (8, 8)}
    for _, rec in summary.iterrows():
        slope = rec["d_rt_p90"] - rec["d_rt_p10"]
        ax.scatter(slope, rec["d_acc"], s=90, color=colors[rec["locus"]],
                   edgecolor="white", zorder=3)
        ax.annotate(labels[rec["locus"]], (slope, rec["d_acc"]),
                    textcoords="offset points", xytext=offs.get(rec["locus"], (7, 6)),
                    fontsize=8)
    ax.set_ylim(-0.03, max(0.09, summary["d_acc"].max() * 1.35))
    ax.set_xlim(-6, max(80, (summary["d_rt_p90"] - summary["d_rt_p10"]).max() * 1.12))
    ax.axhline(0, color="0.6", lw=0.8)
    ax.axvline(30, color="0.85", lw=0.8, ls=":")
    ax.set_xlabel("ΔRT 的分位斜率 = p90 − p10（ms）")
    ax.set_ylabel("Δ正确率（自我 − 他人）")
    ax.set_title("② 签名空间：只有漂移型能同时给出「正 Δacc + 陡斜率」")
    ax.text(0.02, 0.02, "右下角 = 更快但更易错（边界型）；左下或中下 = 只快不准（t0 型）",
            transform=ax.transAxes, fontsize=7.2, color="0.35")
    fig.suptitle("SPE 该放在哪一层：位点不同，签名就不同（模拟，非人类被试）", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-subjects", type=int, default=8)
    ap.add_argument("--n-trials", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261024)
    args = ap.parse_args()

    t0 = time.time()
    frames = [run_cell(k, args.n_subjects, args.n_trials, args.seed + i)
              for i, k in enumerate(LOCI)]
    df = pd.concat(frames, ignore_index=True)
    summary = summarize(df)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "spe_locus.csv", index=False, encoding="utf-8-sig")
    make_figure(summary, df, FIG_OUT / "fig8_spe_locus.png")
    print(summary.round(2).to_string(index=False))
    print(f"\n[ok] {FIG_OUT / 'fig8_spe_locus.png'}（{time.time() - t0:.0f} s；"
          f"{args.n_subjects} 人 × {args.n_trials} 试次/条件/位点）")
    (OUT / "spe_locus_meta.json").write_text(
        json.dumps({"n_subjects": args.n_subjects, "n_trials": args.n_trials,
                    "v_other": V_OTHER, "a_ref": A_REF, "t0": T0, "rho": RHO,
                    "T_stim": T_STIM, "W_deadline": W_DEADLINE,
                    "loci": LOCI}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
