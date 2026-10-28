"""SPE 基线 · 步骤 2：三联图（D134）

A 文献数据集级 ΔRT 森林图（Stranger 对比）+ 本项目四条竖线
B 身份层级梯度（数据集级 ΔRT 分布）
C 本项目旧 87 人：ΔRT 随反应窗 W 的单调变化（附超时率）

输入 2_Data/Real_Data/_spe_baseline/spe_level_summary_all.csv
     spe_subject_level_all.csv
输出 3_Figures/_real_check/fig_spe_baseline.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
D = ROOT / "2_Data" / "Real_Data" / "_spe_baseline"
FIG = ROOT / "3_Figures" / "_real_check" / "fig_spe_baseline.png"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    summ = pd.read_csv(D / "spe_level_summary_all.csv", encoding="utf-8-sig")
    subj = pd.read_csv(D / "spe_subject_level_all.csv", encoding="utf-8-sig")

    lit = summ[(summ.source == "lit") & (summ.other_identity == "Stranger")].dropna(subset=["dRT_mean"])
    lit = lit.sort_values("dRT_mean").reset_index(drop=True)

    fig = plt.figure(figsize=(15.5, 10.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], hspace=0.34, wspace=0.24)

    # ---------------- A 森林图 ----------------
    axA = fig.add_subplot(gs[0, :])
    y = np.arange(len(lit))
    axA.scatter(lit["dRT_mean"], y, s=np.clip(lit["n_subj"], 8, 120) * 0.9,
                c="#4C72B0", alpha=0.75, edgecolor="white", linewidth=0.6, zorder=3)
    axA.axvline(0, color="k", lw=0.8)
    refs = [(33.0, "#C44E52", "本项目新设计 17 人 +33"),
            (8.0, "#DD8452", "TRUTH_LIN +8"),
            (221.0, "#8172B3", "旧 v2.4 +221")]
    for v, c, lab in refs:
        axA.axvline(v, color=c, ls="--", lw=1.4)
        axA.text(v, len(lit) * 0.985, lab, color=c, fontsize=9, rotation=90,
                 va="top", ha="right")
    axA.set_yticks([])
    axA.set_xlabel("ΔRT = RT(他人) − RT(自我)，ms　正值 = 自我更快（SPE 常规方向）")
    axA.set_title(f"A 文献数据集级 SPE（Stranger 对比，{len(lit)} 个数据集；点面积∝被试数）"
                  f"　中位 {lit['dRT_mean'].median():.1f} ms", fontsize=11)
    axA.set_xlim(-130, 260)
    axA.grid(axis="x", ls=":", alpha=0.5)

    # ---------------- B 身份梯度 ----------------
    axB = fig.add_subplot(gs[1, 0])
    order = ["Acquaintance", "Close", "NonPerson", "Stranger", "Celebrity"]
    data, labels = [], []
    for k in order:
        vals = summ[(summ.source == "lit") & (summ.other_identity == k)]["dRT_mean"].dropna()
        if len(vals):
            data.append(vals.to_numpy())
            labels.append(f"{k}\n(n={len(vals)})")
    bp = axB.boxplot(data, labels=labels, widths=0.55, patch_artist=True,
                     medianprops=dict(color="#C44E52", lw=1.6), showfliers=False)
    for p in bp["boxes"]:
        p.set_facecolor("#B8CCE4")
        p.set_edgecolor("#4C72B0")
    rng = np.random.default_rng(0)
    for i, vals in enumerate(data, start=1):
        axB.scatter(i + rng.uniform(-0.13, 0.13, len(vals)), vals, s=12,
                    color="#4C72B0", alpha=0.45, zorder=3)
    axB.axhline(33.0, color="#C44E52", ls="--", lw=1.2)
    axB.text(0.55, 36, "本项目 17 人 +33", color="#C44E52", fontsize=8.5)
    axB.axhline(0, color="k", lw=0.8)
    axB.set_ylabel("数据集级 ΔRT（ms）")
    axB.set_title("B 身份层级：文献里 Close 的 SPE 反而小于 Stranger", fontsize=11)
    axB.grid(axis="y", ls=":", alpha=0.5)

    # ---------------- C 旧 87 人按设计 ----------------
    axC = fig.add_subplot(gs[1, 1])
    old = summ[summ.source == "old"].copy()
    old["W"] = old["dataset"].map({"D1": 300, "D2": 600, "D3a": 600, "D3b": 800,
                                   "D4a": 600, "D4b": 800, "D5": 1100, "D6": 1500})
    old = old.sort_values(["W", "dataset"])
    olds = subj[subj.source == "old"]
    agg = (olds.groupby("dataset")
           .agg(dRT=("dRT", "mean"), sem=("dRT", lambda s: s.std(ddof=1) / np.sqrt(len(s))),
                omit=("omit_rate", "mean"))
           .reset_index())
    agg["W"] = agg["dataset"].map(old.drop_duplicates("dataset").set_index("dataset")["W"])
    agg = agg.sort_values(["W", "dataset"]).reset_index(drop=True)
    # 同一 W 档有多个设计时横向错开，避免折线竖着折返
    offs, seen = [], {}
    for w in agg["W"]:
        k = seen.get(w, 0)
        seen[w] = k + 1
        offs.append(k)
    n_per = agg.groupby("W")["W"].transform("size").to_numpy()
    agg["x"] = agg["W"] + np.array([(o - (n - 1) / 2) * 35 for o, n in zip(offs, n_per)])
    axC.errorbar(agg["x"], agg["dRT"], yerr=agg["sem"], fmt="o-", color="#4C72B0",
                 capsize=4, lw=1.6, ms=7, label="ΔRT（均值 ± SEM）")
    for _, r in agg.iterrows():
        axC.annotate(r["dataset"], (r["x"], r["dRT"]), textcoords="offset points",
                     xytext=(0, 9), fontsize=8, ha="center")
    axC.axhline(0, color="k", lw=0.8)
    axC.set_xlabel("反应窗 W（ms）")
    axC.set_ylabel("ΔRT（ms）", color="#4C72B0")
    axC.tick_params(axis="y", labelcolor="#4C72B0")
    axC.set_title("C 旧 87 人：W 越短 SPE 越小（被截断）", fontsize=11)
    ax2 = axC.twinx()
    ax2.plot(agg["W"], agg["omit"] * 100, "s--", color="#C44E52", lw=1.3, ms=6,
             label="超时率")
    ax2.set_ylabel("超时率（%）", color="#C44E52")
    ax2.tick_params(axis="y", labelcolor="#C44E52")
    ax2.set_ylim(0, 95)
    for _, r in agg.iterrows():
        ax2.annotate(f"{r['omit']*100:.0f}%", (r["W"], r["omit"] * 100),
                     textcoords="offset points", xytext=(6, -12), fontsize=8,
                     color="#C44E52")
    axC.grid(axis="y", ls=":", alpha=0.5)

    fig.suptitle("SPE 真实分布基准：文献 71 个数据集 vs 本项目", fontsize=13, y=0.985)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=170, bbox_inches="tight")
    print(f"saved: {FIG}")

    print("\n== 旧 87 人按 W 汇总 ==")
    print(agg[["dataset", "W", "dRT", "sem", "omit"]].round(3).to_string(index=False))
    print("\n== 文献 Stranger 分位 ==")
    q = lit["dRT_mean"].quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    print(q.round(1).to_string())


if __name__ == "__main__":
    main()
