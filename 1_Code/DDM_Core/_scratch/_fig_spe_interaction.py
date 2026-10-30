# -*- coding: utf-8 -*-
"""匹配 × 身份的交互：四面板图（论文 9.x / 研究四）。

数据源：2_Data/Real_Data/New_Design/_pipeline/spe_interaction_20261028.json
（17 名被试 × 四个单元格 self/other × match/nonmatch 的 RT 中位与正确率）
输出：3_Figures/_real_check/fig_spe_interaction.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats as st

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
from make_figures import setup_matplotlib  # noqa: E402

plt, LANG = setup_matplotlib("zh")

SRC = ROOT / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "spe_interaction_20261028.json"
OUT = ROOT / "3_Figures" / "_real_check" / "fig_spe_interaction.png"

recs = json.loads(SRC.read_text(encoding="utf-8"))
n = len(recs)
print(f"被试 {n} 人")

def col(k):
    return np.array([r[k] for r in recs], float)

# 单元格（RT 单位秒 → ms）
sm_rt, sn_rt = col("sm_rt") * 1000, col("sn_rt") * 1000
om_rt, on_rt = col("om_rt") * 1000, col("on_rt") * 1000
sm_ac, sn_ac = col("sm_acc"), col("sn_acc")
om_ac, on_ac = col("om_acc"), col("on_acc")

# Δ = 他人 − 自我（正值 = 自我更快 / 自我更准）
d_rt_m = om_rt - sm_rt
d_rt_n = on_rt - sn_rt
d_ac_m = (sm_ac - om_ac) * 100
d_ac_n = (sn_ac - on_ac) * 100

def tt(a, b=None):
    if b is None:
        t, p = st.ttest_1samp(a, 0.0)
        return t, p
    t, p = st.ttest_rel(a, b)
    return t, p

t_m, p_m = tt(d_rt_m)
t_n, p_n = tt(d_rt_n)
t_int, p_int = tt(d_rt_m, d_rt_n)
ta_m, pa_m = tt(d_ac_m)
ta_n, pa_n = tt(d_ac_n)
ta_int, pa_int = tt(d_ac_m, d_ac_n)

print(f"ΔRT 匹配   {d_rt_m.mean():+.1f} ± {d_rt_m.std(ddof=1)/np.sqrt(n):.1f} ms  t={t_m:.2f} p={p_m:.2g}  "
      f"{(d_rt_m > 0).sum()}/{n} 为正")
print(f"ΔRT 非匹配 {d_rt_n.mean():+.1f} ± {d_rt_n.std(ddof=1)/np.sqrt(n):.1f} ms  t={t_n:.2f} p={p_n:.2g}  "
      f"{(d_rt_n > 0).sum()}/{n} 为正")
print(f"ΔRT 交互   {t_int:.2f} p={p_int:.2g}")
print(f"ΔACC 匹配   {d_ac_m.mean():+.1f} ± {d_ac_m.std(ddof=1)/np.sqrt(n):.1f} pt t={ta_m:.2f} p={pa_m:.2g}  "
      f"{(d_ac_m > 0).sum()}/{n} 为正")
print(f"ΔACC 非匹配 {d_ac_n.mean():+.1f} ± {d_ac_n.std(ddof=1)/np.sqrt(n):.1f} pt t={ta_n:.2f} p={pa_n:.2g}  "
      f"{(d_ac_n > 0).sum()}/{n} 为正")
print(f"ΔACC 交互   {ta_int:.2f} p={pa_int:.2g}")

# 池化中位（论文正文里引用的那组数）
pool = {
    "self_match": sm_rt, "self_nonmatch": sn_rt,
    "other_match": om_rt, "other_nonmatch": on_rt,
}
for k, v in pool.items():
    print(f"  池化 RT 中位 {k}: {np.median(v):.0f} ms")

C_SELF, C_OTHER = "#D1615D", "#4C72B0"

fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6))
fig.suptitle("SPE 的匹配专属性：自我优势只出现在「自我被掩蔽」的匹配判断上（17 人）",
             fontsize=15, y=0.975)

# --- A：ΔRT 两条件 -------------------------------------------------------
ax = axes[0, 0]
data = [d_rt_m, d_rt_n]
bp = ax.boxplot(data, widths=0.42, patch_artist=True, showfliers=False)
for patch, c in zip(bp["boxes"], [C_SELF, C_OTHER]):
    patch.set_facecolor(c)
    patch.set_alpha(0.32)
for med in bp["medians"]:
    med.set_color("#333333")
    med.set_linewidth(2)
rng = np.random.default_rng(7)
for i, (arr, c) in enumerate(zip(data, [C_SELF, C_OTHER]), start=1):
    ax.scatter(i + rng.uniform(-0.11, 0.11, n), arr, s=24, color=c, alpha=0.85,
               edgecolor="white", linewidth=0.5, zorder=3)
ax.axhline(0, color="#888888", lw=1, ls="--")
ax.set_xticks([1, 2])
ax.set_xticklabels([f"匹配试次\n(n={n})", f"非匹配试次\n(n={n})"])
ax.set_ylabel("ΔRT（他人 − 自我，ms）\n正值 = 自我更快")
ax.set_title("A  ΔRT：匹配 +59 ms、非匹配 +16 ms（自我更快）", fontsize=12, loc="left")
ax.annotate(f"交互 t={t_int:.2f}, p={p_int:.3f}",
            xy=(0.5, 0.94), xycoords="axes fraction", ha="center", fontsize=11,
            bbox=dict(boxstyle="round,pad=0.35", fc="#FFF4E5", ec="#E0A458"))

# --- B：ΔACC 两条件 ------------------------------------------------------
ax = axes[0, 1]
data = [d_ac_m, d_ac_n]
bp = ax.boxplot(data, widths=0.42, patch_artist=True, showfliers=False)
for patch, c in zip(bp["boxes"], [C_SELF, C_OTHER]):
    patch.set_facecolor(c)
    patch.set_alpha(0.32)
for med in bp["medians"]:
    med.set_color("#333333")
    med.set_linewidth(2)
for i, (arr, c) in enumerate(zip(data, [C_SELF, C_OTHER]), start=1):
    ax.scatter(i + rng.uniform(-0.11, 0.11, n), arr, s=24, color=c, alpha=0.85,
               edgecolor="white", linewidth=0.5, zorder=3)
ax.axhline(0, color="#888888", lw=1, ls="--")
ax.set_xticks([1, 2])
ax.set_xticklabels(["匹配试次", "非匹配试次"])
ax.set_ylabel("ΔACC（自我 − 他人，百分点）\n正值 = 自我更准")
ax.set_title("B  ΔACC：匹配 +14.4 pt，非匹配 −0.9 pt", fontsize=12, loc="left")
ax.annotate(f"交互 t={ta_int:.2f}, p={pa_int:.4f}",
            xy=(0.5, 0.94), xycoords="axes fraction", ha="center", fontsize=11,
            bbox=dict(boxstyle="round,pad=0.35", fc="#FFF4E5", ec="#E0A458"))

# --- C：2×2 单元格均值折线 ----------------------------------------------
ax = axes[1, 0]
rt_self = [np.mean(sm_rt), np.mean(sn_rt)]
rt_other = [np.mean(om_rt), np.mean(on_rt)]
ac_self = [np.mean(sm_ac) * 100, np.mean(sn_ac) * 100]
ac_other = [np.mean(om_ac) * 100, np.mean(on_ac) * 100]
xs = np.array([0, 1])
ax.plot(xs, rt_self, "o-", color=C_SELF, lw=2.2, ms=9, label="自我")
ax.plot(xs, rt_other, "s--", color=C_OTHER, lw=2.2, ms=9, label="他人")
for x, y, v in [(0, rt_self[0], "自匹配"), (1, rt_self[1], "自非匹配"),
                (0, rt_other[0], "他匹配"), (1, rt_other[1], "他非匹配")]:
    ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, -16),
                ha="center", fontsize=10, color="#444444")
ax.set_xticks(xs)
ax.set_xticklabels(["匹配试次", "非匹配试次"])
ax.set_xlim(-0.35, 1.35)
ax.set_ylabel("RT 均值（ms）")
ax.set_title("C  2×2 单元格：他人两条线近平，自我在匹配格塌陷", fontsize=12, loc="left")
ax.legend(frameon=False, loc="upper left")

# --- D：d′ / c 配对散点 --------------------------------------------------
ax = axes[1, 1]
sd, od = col("self_d"), col("other_d")
sc_, oc_ = col("self_c"), col("other_c")
dprime = [(sd[i], od[i], "d′") for i in range(n)]
ax.scatter(sd, od, s=46, color="#5B8C5A", alpha=0.9, edgecolor="white", label="d′")
ax.scatter(sc_, oc_, s=46, color="#C08552", alpha=0.9, edgecolor="white", marker="^", label="c")
lim = [min(sd.min(), od.min(), sc_.min(), oc_.min()) - 0.25,
       max(sd.max(), od.max(), sc_.max(), oc_.max()) + 0.25]
ax.plot(lim, lim, color="#999999", lw=1, ls=":")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.set_xlabel("自我条件")
ax.set_ylabel("他人条件")
ax.set_title("D  辨别力与判据：d′ 上移、c 下移", fontsize=12, loc="left")
ax.legend(frameon=False, loc="upper left")
td, pd_ = tt(sd, od)
tc, pc_ = tt(sc_, oc_)
ax.annotate(f"Δd′ = {np.mean(sd - od):+.2f}（p={pd_:.3f}）\n"
            f"Δc  = {np.mean(sc_ - oc_):+.2f}（p<.0001）",
            xy=(0.03, 0.62), xycoords="axes fraction", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.35", fc="#F0F5F0", ec="#5B8C5A"))
print(f"Δd′ {np.mean(sd-od):+.3f} t={td:.2f} p={pd_:.2g}  {(sd>od).sum()}/{n}")
print(f"Δc  {np.mean(sc_-oc_):+.3f} t={tc:.2f} p={pc_:.2g}  {(sc_<oc_).sum()}/{n}")
print(f"命中 自我 {np.mean(col('self_hit')):.3f} / 他人 {np.mean(col('other_hit')):.3f}；"
      f"虚报 自我 {np.mean(col('self_fa')):.3f} / 他人 {np.mean(col('other_fa')):.3f}")

for ax in axes.ravel():
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.tight_layout(rect=(0, 0, 1, 0.955))
fig.savefig(OUT, dpi=200)
print("saved:", OUT)
