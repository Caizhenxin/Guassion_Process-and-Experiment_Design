# -*- coding: utf-8 -*-
"""
论文图表生成器 v1（2026-09-02，canonical4 口径）
================================================
产出目录：3_Figures/Thesis_20260902/{tables,figures}
- tables/*.csv（UTF-8-SIG，可直接贴入 Word/Excel）
- figures/*.png（matplotlib，中文字体）
- 现成图（canonical4/OPN/Omission/滑动窗口/Stim-Coding）拷贝为论文编号
运行：python 1_Code/Python_for_Check/make_tables_figures_v1_20260902.py
"""
import json
import os
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import quad
from scipy.stats import ncf, f as fdist

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(r"d:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
OUT_T = ROOT / "3_Figures" / "Thesis_20260902" / "tables"
OUT_F = ROOT / "3_Figures" / "Thesis_20260902" / "figures"
OUT_T.mkdir(parents=True, exist_ok=True)
OUT_F.mkdir(parents=True, exist_ok=True)

REAL = ROOT / "2_Data" / "Real_Data" / "EXP_data_combined.csv"
SUBJ_4 = ROOT / "2_Data" / "Generate_Data" / "HDDM_Diagnostics" / "subject_spe_4chain.csv"
GROUP_4 = ROOT / "2_Data" / "Generate_Data" / "HDDM_Diagnostics" / "all_G3_G8_4chain_group.csv"
DIAG = ROOT / "2_Data" / "Generate_Data" / "HDDM_Diagnostics"
CAN4 = ROOT / "2_Data" / "Generate_Data" / "GP_Sigmoid_Canonical4"
SENS = ROOT / "2_Data" / "Generate_Data" / "Omission_Sensitivity"
OPND = ROOT / "2_Data" / "Generate_Data" / "OPN_Training"
LK = ROOT / "5_Reference" / "lock_BF_ANOVA_4chain_20260902.csv"

DESIGN = {
    1: ("G1", 0, 30, 300, 330, 11, "exclude"),
    2: ("G2", 0, 30, 600, 630, 12, "exclude"),
    3: ("G3", 120, 30, 600, 630, 10, "caution"),
    4: ("G4", 120, 80, 600, 680, 11, "caution"),
    5: ("G5", 8, 100, 1100, 1200, 11, "good"),
    6: ("G6", 120, 500, 1500, 2000, 10, "good"),
    7: ("G7", 120, 30, 800, 830, 12, "good"),
    8: ("G8", 120, 80, 800, 880, 11, "good"),
}
OMI = {1: 71.6, 2: 54.0, 3: 38.0, 4: 39.2, 5: 11.0, 6: 5.3, 7: 15.2, 8: 15.5}


def save(df, name):
    df.to_csv(OUT_T / name, index=False, encoding="utf-8-sig")
    print("表:", name)


def jzs_prior_g(g, r):
    return 0.0 if g <= 0 else (r / np.sqrt(2 * np.pi)) * g ** -1.5 * np.exp(-r ** 2 / (2 * g))


def bf_reg(X, y, r=0.5):
    n = len(y)
    Xc = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    R2 = 1 - ((y - Xc @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    def integ(g):
        if g <= 0:
            return 0.0
        return ((1 + g) ** ((n - X.shape[1] - 1) / 2)
                * (1 + g * (1 - R2)) ** (-(n - 1) / 2) * jzs_prior_g(g, r))

    return quad(integ, 1e-10, np.inf, limit=300)[0], R2


def anova1(y, g):
    gs = [y[g == k] for k in np.unique(g)]
    F, p = stats.f_oneway(*gs)
    ssb = sum(len(x) * (x.mean() - y.mean()) ** 2 for x in gs)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in gs)
    return F, p, ssb / (ssb + ssw), len(np.unique(g)), len(y)


def gpower_min_f(k, N, power=0.80):
    df1, df2 = k - 1, N - k
    fc = fdist.ppf(0.95, df1, df2)
    lo, hi = 1e-3, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if 1 - ncf.cdf(fc, df1, df2, N * mid ** 2) < power:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------- 行为层单元格（RT/ACC） ----------------
dfr = pd.read_csv(REAL)
dfr = dfr[dfr["stage"].astype(str).str.lower().eq("formal")].copy()


def key(cell):
    c = cell.replace("P", "").replace("T", "").replace("W", "")
    return tuple(map(int, c.split("_")))


dfr["DesignCell"] = pd.Categorical(dfr["DesignCell"],
                                   categories=sorted(dfr["DesignCell"].unique(), key=key),
                                   ordered=True)
dfr["Matching"] = dfr["Matching"].astype(str).str.capitalize()
dfr["Identity"] = dfr["Identity"].astype(str).str.capitalize()
rt = dfr[(dfr["ACC"] == 1) & dfr["RT_ms"].notna() & (dfr["RT_ms"] > 0)]
rt_c = rt.groupby(["SubjectUID", "DesignCell", "Matching", "Identity"], observed=True).agg(
    RT=("RT_ms", "mean")).reset_index()
ac_c = dfr.groupby(["SubjectUID", "DesignCell", "Matching", "Identity"], observed=True).agg(
    ACC=("ACC", "mean")).reset_index()


def spe_df(cell_df, col):
    m = cell_df[cell_df["Matching"] == "Matching"]
    pv = m.pivot_table(index=["SubjectUID", "DesignCell"], columns="Identity",
                       values=col, observed=True).reset_index()
    pv["SPE"] = pv["Self"] - pv["Stranger"]
    return pv.dropna(subset=["SPE"])


spe_rt = spe_df(rt_c, "RT")
spe_acc = spe_df(ac_c, "ACC")

cell_rows = []
for dc in sorted(spe_rt["DesignCell"].unique(), key=lambda c: key(str(c))):
    x = spe_rt[spe_rt["DesignCell"] == dc]["SPE"]
    y = spe_acc[spe_acc["DesignCell"] == dc]["SPE"]
    p, t, w = key(str(dc))
    cell_rows.append({"DesignCell": str(dc), "P": p, "T_ms": t, "W_ms": w,
                      "n": len(x), "SPE_RT_mean_ms": x.mean(), "SPE_RT_sd_ms": x.std(),
                      "SPE_ACC_mean": y.mean(), "SPE_ACC_sd": y.std()})
T5_1 = pd.DataFrame(cell_rows)
save(T5_1, "T5-1_spe_cell_means.csv")

beh = []
for tag, dd, name in [("SPE_RT", spe_rt, "RT"), ("SPE_ACC", spe_acc, "ACC")]:
    y, grp = dd["SPE"].values, dd["DesignCell"].values
    F8, p8, e8, k8, n8 = anova1(y, grp)
    excl = {str(c) for c in np.unique(grp) if key(str(c))[0] == 0 and key(str(c))[1] == 30}
    keep = ~np.isin(grp, list(excl))
    F6, p6, e6, k6, n6 = anova1(y[keep], grp[keep])
    beh.append({"指标": tag, "口径": "G1-G8", "F": F8, "df1": k8 - 1, "df2": n8 - k8,
                "p": p8, "eta2": e8, "n": n8})
    beh.append({"指标": tag, "口径": "G3-G8", "F": F6, "df1": k6 - 1, "df2": n6 - k6,
                "p": p6, "eta2": e6, "n": n6})
save(pd.DataFrame(beh), "T5-2_anova_behavior.csv")

# ---------------- 参数层（4 链被试级） ----------------
subj = pd.read_csv(SUBJ_4)
core = subj[subj["group_id"].isin([3, 4, 5, 6, 7, 8])]
g58 = subj[subj["group_id"].isin([5, 6, 7, 8])]
F6, p6, e6, k6, n6 = anova1(core["SPE_v"].values, core["group_id"].values)
Fg, pg, eg, kg, ng = anova1(g58["SPE_v"].values, g58["group_id"].values)
grp = core["group_id"].values
Xd = pd.get_dummies(core["group_id"], drop_first=True).astype(float).values
bf_a, _ = bf_reg(Xd, core["SPE_v"].values, r=0.5)
Xr = core[["P", "T_ms", "W_ms"]].values if "P" in core.columns else None
grp4 = pd.read_csv(GROUP_4)
core4 = grp4.merge(subj, on="group_id", suffixes=("", "_s")) if False else grp4
save(pd.DataFrame([
    {"检验": "ANOVA SPE_v G3-G8", "F": F6, "df1": k6 - 1, "df2": n6 - k6, "p": p6,
     "eta2": e6, "f_obs": np.sqrt(e6 / (1 - e6)),
     "f_min80": gpower_min_f(k6, n6), "BF10_r05": bf_a},
    {"检验": "ANOVA SPE_v G5-G8", "F": Fg, "df1": kg - 1, "df2": ng - kg, "p": pg,
     "eta2": eg, "f_obs": np.sqrt(eg / (1 - eg)),
     "f_min80": gpower_min_f(kg, ng), "BF10_r05": np.nan},
]), "T5-3_anova_param_4chain.csv")

# 回归（用 canonical 被试级参数重算 R2/BF）
can = grp4.set_index("group_id")
subjX = subj.merge(can.reset_index()[["group_id", "P", "T_ms", "W_ms"]], on="group_id", how="left")
cc = subjX[subjX["group_id"].isin([3, 4, 5, 6, 7, 8])]
R2v, bf_r = bf_reg(cc[["P", "T_ms", "W_ms"]].values, cc["SPE_v"].values, r=0.5)
save(pd.DataFrame([{"检验": "回归 SPE_v~P+T+W (G3-G8, G7=T30)", "R2": R2v, "BF10_r05": bf_r, "n": len(cc)}]),
     "T5-4_regression_4chain.csv")

# ---------------- 表4-1 设计条件 ----------------
rows = []
for g, (lab, P, T, W, M, n, q) in DESIGN.items():
    rows.append({"组别": lab, "设计": "P%d_T%d_W%d" % (P, T, W), "P(次)": P, "T(ms)": T, "W(ms)": W,
                 "M=T+W(ms)": M, "被试数": n, "匹配试次/人": 260,
                 "遗漏率%": OMI[g], "质量档": q})
save(pd.DataFrame(rows), "T4-1_design_table.csv")

# ---------------- 表6-1 Censor vs Drop（v_self 与 SPE_v） ----------------
sc = pd.read_csv(SENS / "sensitivity_comparison.csv")
ds = pd.read_csv(SENS / "data_summary.csv") if (SENS / "data_summary.csv").exists() else None
omit = {}
if ds is not None and "group_id" in ds and "omission_rate" in ds:
    omit = {int(r.group_id): r.omission_rate for r in ds.itertuples()}
rows = []
for gi in range(1, 9):
    for par in ["v_self", "SPE_v"]:
        r = sc[(sc["group_id"] == gi) & (sc["parameter"] == par)]
        if not len(r):
            continue
        r = r.iloc[0]
        rows.append({"组别": "G%d" % gi, "遗漏率%": round(omit.get(gi, OMI[gi]), 1),
                     "参数": par, "Censor M": round(r.censor_mean, 3),
                     "Censor 95%CI": "[%.2f, %.2f]" % (r.censor_q025, r.censor_q975),
                     "Drop M": round(r.drop_mean, 3),
                     "Drop 95%CI": "[%.2f, %.2f]" % (r.drop_q025, r.drop_q975),
                     "Δ": round(r.delta, 3), "CI 重叠": r.ci_overlap, "Cohen's d": round(r.cohens_d, 3)})
save(pd.DataFrame(rows), "T6-1_censor_drop.csv")

# ---------------- 表6-2 OPN ----------------
jm = json.load(open(OPND / "opn_metrics.json", encoding="utf-8"))
save(pd.DataFrame([{
    "模式": jm.get("mode"), "训练样本": jm.get("train_n"), "测试样本": jm.get("test_n"),
    "特征数": jm.get("n_features"), "网络结构": "-".join(map(str, jm.get("hidden_layers", []))),
    "训练R²": jm.get("train_r2"), "测试R²": jm.get("test_r2"),
    "训练MAE": jm.get("train_mae"), "测试MAE": jm.get("test_mae")}]), "T6-2_opn_metrics.csv")

# ---------------- 表7-1 HDDM 4链参数（含诊断） ----------------
rows = []
for g in [3, 4, 5, 6, 7, 8]:
    fd = pd.read_csv(DIAG / ("G%d_full_diag.csv" % g)).set_index("param")
    row = {"组别": "G%d" % g}
    for p, label in [("v(0)", "v_stranger"), ("v(1)", "v_self"), ("a", "a"), ("t", "t"), ("z", "z")]:
        r = fd.loc[p]
        row[label + "_M±SD"] = "%.3f±%.3f" % (r["mean"], r["sd"])
        row[label + "_rhat"] = r["r_hat"]
        row[label + "_ESS"] = int(r["ess_bulk"])
    row["SPE_v"] = round(float(fd.loc["v(1)", "mean"]) - float(fd.loc["v(0)", "mean"]), 3)
    rows.append(row)
save(pd.DataFrame(rows), "T7-1_hddm_params_4chain.csv")

# ---------------- 表7-2..7-6（canonical4 产物直接转表） ----------------
save(pd.read_csv(CAN4 / "step4_sigmoid_calibrated_params_canonical4.csv"),
     "T7-2_sigmoid_calib_canonical4.csv")
save(pd.read_csv(CAN4 / "step4_training_metrics_canonical4.csv"), "T7-3_insample_canonical4.csv")
save(pd.read_csv(CAN4 / "step4_locv_metrics_cleaned.csv"), "T7-4_locv_canonical4.csv")
save(pd.read_csv(CAN4 / "step5_behavior_validation_metrics.csv"), "T7-5_behavior_canonical4.csv")
save(pd.read_csv(CAN4 / "step6_candidate_design_points.csv"), "T7-6_candidates_canonical4.csv")

# ================= 图 =================
print("绘图 ...")


def ts(base):
    return os.path.join(OUT_F, base)


# F4-1 设计空间分布
color_q = {"exclude": "#d62728", "caution": "#ff7f0e", "good": "#2ca02c"}
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, (xa, ya, xlab, ylab) in zip(axes,
        [("P", "W", "P (练习次数)", "W (ms)"), ("T", "W", "T (ms)", "W (ms)")]):
    for g, (lab, P, T, W, M, n, q) in DESIGN.items():
        xx = {"P": P, "T": T, "W": W}[xa]
        yy = {"P": P, "T": T, "W": W}[ya]
        ax.scatter(xx, yy, s=130, c=color_q[q], edgecolors="black", zorder=3)
        ax.annotate(lab, (xx, yy), textcoords="offset points", xytext=(6, 4), fontsize=9)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(ts("F4-1_design_space.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("图: F4-1")

# F5-1 被试级 SPE（行为 RT / ACC + 参数 SPE_v）
order = sorted(spe_rt["DesignCell"].unique(), key=lambda c: key(str(c)))
fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
for ax, (dd, ylab, title) in zip(axes, [
        (spe_rt, "SPE_RT (Self-Stranger, ms)", "行为 SPE_RT by 设计单元"),
        (spe_acc, "SPE_ACC", "行为 SPE_ACC by 设计单元")]):
    data = [dd[dd["DesignCell"] == c]["SPE"].values for c in order]
    ax.boxplot(data, showmeans=True,
               meanprops=dict(marker="D", markerfacecolor="red", markersize=4),
               tick_labels=["%s" % c for c in order])
    ax.axhline(0, color="gray", ls="--", lw=1)
    ax.set_ylabel(ylab)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
ax = axes[2]
data = [core[core["group_id"] == g]["SPE_v"].values for g in [3, 4, 5, 6, 7, 8]]
ax.boxplot(data, showmeans=True,
           meanprops=dict(marker="D", markerfacecolor="red", markersize=4),
           tick_labels=["G3", "G4", "G5", "G6", "G7", "G8"])
ax.axhline(0, color="gray", ls="--", lw=1)
ax.set_title("DDM 参数层 SPE_v by 条件（G3-G8, 4链）")
ax.set_ylabel("SPE_v (v_self − v_stranger)")
fig.tight_layout()
fig.savefig(ts("F5-1_spe_subjects.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("图: F5-1")

# F5-2 功效（参数层, 4 链）
fobs6 = np.sqrt(e6 / (1 - e6))
fobsg = np.sqrt(eg / (1 - eg))
fig, ax = plt.subplots(figsize=(7, 4.6))
names = ["G3-G8 (n=65)", "G5-G8 (n=44)"]
fobs = [fobs6, fobsg]
fmin = [gpower_min_f(6, 65), gpower_min_f(4, 44)]
x = np.arange(len(names))
ax.bar(x - 0.18, fobs, 0.34, label="观察效应 f", color="#3498db")
ax.bar(x + 0.18, fmin, 0.34, label="最小可检测 f (80%)", color="#e74c3c")
for i, (a, b) in enumerate(zip(fobs, fmin)):
    ax.text(i - 0.18, a + 0.01, "%.2f" % a, ha="center", fontsize=9)
    ax.text(i + 0.18, b + 0.01, "%.2f" % b, ha="center", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(names)
ax.axhline(0, color="gray", lw=1)
ax.legend()
ax.set_title("参数层 SPE_v：观察效应量 vs 功效门槛（4 链口径）")
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(ts("F5-2_gpower_4chain.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("图: F5-2")

# F5-3 BF 先验敏感性（canonical 被试级）
rs = np.logspace(-1, 0.5, 25)
bv, br = [], []
Xd_ = pd.get_dummies(core["group_id"], drop_first=True).astype(float).values
for r in rs:
    bv.append(bf_reg(Xd_, core["SPE_v"].values, r)[0])
    br.append(bf_reg(cc[["P", "T_ms", "W_ms"]].values, cc["SPE_v"].values, r)[0])
fig, ax = plt.subplots(figsize=(7, 4.4))
ax.semilogx(rs, bv, "o-", label="ANOVA（组别哑变量）")
ax.semilogx(rs, br, "s-", label="回归 SPE_v~P+T+W")
ax.axhline(1, color="gray", ls=":", lw=1)
ax.axhline(3, color="green", ls=":", lw=1)
ax.axhline(1 / 3, color="red", ls=":", lw=1)
ax.set_xlabel("JZS 先验尺度 r")
ax.set_ylabel("BF10")
ax.set_title("贝叶斯因子先验敏感性（G3-G8, 4链）")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(ts("F5-3_bf_prior_sensitivity_4chain.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("图: F5-3")

# 拷贝现成图
CAN4_FIGS = ROOT / "3_Figures" / "GP_Sigmoid_Canonical4"
copy_map = [
    (CAN4_FIGS / "step4_training_fit_cleaned.png", "F7-1_insample_fit.png"),
    (CAN4_FIGS / "step4_locv_fit_cleaned.png", "F7-2_locv_fit.png"),
    (CAN4_FIGS / "step5_behavior_validation_condition_scatter.png", "F7-3_behavior_scatter.png"),
    (CAN4_FIGS / "step6_candidate_design_points.png", "F7-4_candidate_points.png"),
]
figs_opn = list((ROOT / "3_Figures" / "OPN_Training").glob("*.png"))
for f in figs_opn:
    copy_map.append((f, "F6-2_" + f.name))
figs_om = list((ROOT / "3_Figures" / "Omission_Sensitivity").glob("*.png"))
for f in figs_om:
    copy_map.append((f, "F6-1_" + f.name))
sw = ROOT / "1_Code" / "Python_for_Check" / "Visualization" / "V4" / "outputs" / "SPE_sliding_window_analysis.png"
if sw.exists():
    copy_map.append((sw, "F8-1_sliding_window.png"))
scs = list((ROOT / "3_Figures" / "HDDM_Stim-Coding_Simulation").rglob("figure_01_CRF_zbias_main.png"))
for f in scs[:2]:
    copy_map.append((f, "F8-3_" + ("Wiener_" if "Wiener" in str(f) else "HDDM_") + f.name))
for src, dst in copy_map:
    if src.exists():
        shutil.copy2(src, OUT_F / dst)
print("拷贝现成图 %d 张" % len(copy_map))

print("完成 ->", OUT_T.parent)
