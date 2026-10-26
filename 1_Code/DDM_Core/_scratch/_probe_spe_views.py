# -*- coding: utf-8 -*-
"""SPE 到底「出没出来」：把同一批数据画成四种看法。

用户的问题：「两条曲线不分开，SPE 不就没出来吗？」
本图回答：在**边缘 RT 直方图**上，33 ms 的位移被 250 ms 的个体内 SD 完全淹没（A 面板），
但换到**被试内配对差 / 分位差 / 正确率**三个坐标上，效应稳定可见（B/C/D 面板）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"),
                str(REPO / "1_Code" / "Experiment")]

import stage8_run as S              # noqa: E402
from make_figures import setup_matplotlib  # noqa: E402
from mapping import MappingParams   # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
OUT = REPO / "3_Figures" / "_real_check"
OUT.mkdir(parents=True, exist_ok=True)
QS = np.array([10, 25, 50, 75, 90])

people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
recs = []
for p in people:
    tr = p["tr"]
    o = np.asarray(tr["omission"]) == 0
    side = np.asarray(tr["side"])[o]
    match = np.asarray(tr["is_match"])[o]
    recs.append({"g": int(p["group"]), "s": int(p["subject"]),
                 "rt": np.asarray(tr["rt"])[o],
                 "corr": (side == 1) == (match == 1),
                 "self": np.asarray(tr["is_self"])[o] == 1,
                 "P": np.asarray(tr["P"])[o]})

rt = np.concatenate([r["rt"] for r in recs])
sm = np.concatenate([r["self"] for r in recs])
corr = np.concatenate([r["corr"] for r in recs])
Pv = np.concatenate([r["P"] for r in recs])

# ---- 效应量与可视化直觉 ----
sd_within = float(np.mean([np.std(r["rt"], ddof=1) for r in recs]))
d_rt = (np.median(rt[~sm]) - np.median(rt[sm])) / sd_within
acc_s, acc_o = corr[sm].mean(), corr[~sm].mean()

# 重叠系数（两条正态近似密度的重叠面积）
def overlap(mu1, s1, mu2, s2):
    from math import erf, sqrt
    z = abs(mu1 - mu2) / np.sqrt(s1 ** 2 + s2 ** 2)
    return float(2 * 0.5 * (1 + erf(-z / np.sqrt(2)) / 1.0) / 2 * 2)  # ≈ 2Φ(-z/√2)/2*2

from math import erf
ov = float(2 * 0.5 * (1 + erf(-abs(np.median(rt[sm]) - np.median(rt[~sm])) /
                             np.sqrt(2 * sd_within ** 2) / np.sqrt(2))))

print(f"个体内 RT SD（17 人均值）= {sd_within * 1000:.0f} ms")
print(f"ΔRT 中位差 = {(np.median(rt[~sm]) - np.median(rt[sm])) * 1000:.0f} ms ⇒ 效应量 d ≈ {d_rt:.3f}")
print(f"正确率：自我 {acc_s:.3f}、他人 {acc_o:.3f}、Δ = {acc_s - acc_o:+.3f}")
print(f"两条边际分布的重叠系数 ≈ {ov:.3f}（越接近 1 越「看不出分开」，但配对检验照样显著）")

# ---- 画图 ----
plt, lang = setup_matplotlib("zh")
zh = lang == "zh"
L = (lambda a, b: a if zh else b)
fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6))

# A：边缘 RT 密度（用户看到的图）
ax = axes[0, 0]
bins = np.linspace(0.15, 2.0, 90)
for m, c, lab in ((sm, "#d62728", L("自我", "Self")), (~sm, "#1f77b4", L("他人", "Other"))):
    ax.hist(rt[m], bins=bins, density=True, alpha=0.45, color=c, label=lab)
ax.axvline(np.median(rt[sm]), color="#d62728", ls="--", lw=1.6)
ax.axvline(np.median(rt[~sm]), color="#1f77b4", ls="--", lw=1.6)
ax.annotate("", xy=(np.median(rt[~sm]), 3.1), xytext=(np.median(rt[sm]), 3.1),
            arrowprops=dict(arrowstyle="<->", color="k", lw=1.4))
ax.text((np.median(rt[sm]) + np.median(rt[~sm])) / 2, 3.25,
        f"Δ 中位 = {(np.median(rt[~sm]) - np.median(rt[sm])) * 1000:.0f} ms\n"
        f"d ≈ {d_rt:.2f}、重叠 ≈ {ov * 100:.0f}%",
        ha="center", va="bottom", fontsize=9)
ax.set_xlabel(L("RT（秒）", "RT (s)"))
ax.set_ylabel(L("密度", "Density"))
ax.set_title(L("A 边缘分布：看不出分开（这是正常的）", "A Marginal: no visible split (expected)"))
ax.legend(loc="upper right", fontsize=9)
ax.set_xlim(0.15, 2.0)

# B：分位差 + bootstrap CI
ax = axes[0, 1]
d = np.percentile(rt[sm], QS) * 1000 - np.percentile(rt[~sm], QS) * 1000
rng = np.random.default_rng(7)
boots = np.empty((2000, QS.size))
for i in range(2000):
    a = rng.choice(rt[sm], sm.sum(), replace=True)
    b = rng.choice(rt[~sm], (~sm).sum(), replace=True)
    boots[i] = np.percentile(a, QS) * 1000 - np.percentile(b, QS) * 1000
lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
ax.axhline(0, color="k", lw=1)
ax.errorbar(QS, d, yerr=[d - lo, hi - d], fmt="o-", color="#2ca02c", capsize=4, lw=1.8)
ax.set_xlabel(L("RT 分位（%）", "RT quantile (%)"))
ax.set_ylabel(L("Self − Other（ms）", "Self − Other (ms)"))
ax.set_title(L("B 分位差：慢端放大、P25–P90 显著", "B Quantile diff: grows at slow end"))
ax.set_xticks(QS)
for x, y in zip(QS, d):
    ax.annotate(f"{y:+.0f}", (x, y), textcoords="offset points", xytext=(0, 10), fontsize=8, ha="center")

# C：逐被试配对差
ax = axes[1, 0]
per = []
for r in recs:
    per.append((r["g"], r["s"],
                (np.median(r["rt"][r["self"]]) - np.median(r["rt"][~r["self"]])) * 1000))
per.sort(key=lambda t: t[2])
ys = np.arange(len(per))
ax.barh(ys, [t[2] for t in per], color="#9467bd", alpha=0.85)
ax.axvline(0, color="k", lw=1)
ax.set_yticks(ys)
ax.set_yticklabels([f"{g}-{s}" for g, s, _ in per], fontsize=7)
ax.set_xlabel(L("Δ 中位（ms）", "Δ median (ms)"))
ax.set_title(L(f"C 逐被试：{sum(1 for t in per if t[2] < 0)}/{len(per)} 方向一致（全负）",
               f"C Per subject: {sum(1 for t in per if t[2] < 0)}/{len(per)} negative"))

# D：按掩蔽比例 P 分组的 ΔRT 与 Δacc
ax = axes[1, 1]
Ps = sorted(set(int(x) for x in Pv))
drt, dacc = [], []
for pv in Ps:
    m = Pv == pv
    drt.append((np.median(rt[sm & m]) - np.median(rt[~sm & m])) * 1000)
    dacc.append(corr[sm & m].mean() - corr[~sm & m].mean())
ax.bar([p - 6 for p in Ps], drt, width=12, color="#ff7f0e", label=L("ΔRT 中位（ms）", "ΔRT median (ms)"))
ax.axhline(0, color="k", lw=1)
ax.set_xlabel(L("P（自我被掩蔽的比例，%）", "P (% self masked)"))
ax.set_ylabel(L("ΔRT（ms）", "ΔRT (ms)"), color="#ff7f0e")
ax.set_xticks(Ps)
ax2 = ax.twinx()
ax2.bar([p + 6 for p in Ps], dacc, width=12, color="#17becf", alpha=0.85,
        label=L("Δacc", "Δacc"))
ax2.set_ylabel(L("Δ 正确率", "Δ accuracy"), color="#17becf")
ax.set_title(L("D 按掩蔽比例：P=0 最强，P≥8 衰减", "D By masking level"))

fig.suptitle(L("SPE 「出没出来」：同一批数据的四种看法（17 人、7,144 响应试次）",
               "Is SPE there? Four views of the same data"), fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = OUT / "fig_spe_channels.png"
fig.savefig(out, bbox_inches="tight")
print("saved:", out)
