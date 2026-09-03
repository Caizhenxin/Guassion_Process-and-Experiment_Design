# -*- coding: utf-8 -*-
"""
BF/ANOVA 冻结版重跑脚本 (2026-09-02)
====================================
依据：《冻结规格书_v1_20260902.md》§2 权威设计表
冻结规则：
  1. 设计参数 (P,T,W,M) 一律查 DESIGN 表，绝不从文件名解析（G7 文件名仍为旧 T80 命名）；
  2. 主口径 = G3-G8（6 条件）；G1/G2 仅作敏感性参照；G5-G8 作稳健性子集；
  3. 输出 S03-S05 锁定数字并保存 CSV，供《数字锁定表》回填。

对照基准（旧报告 Basic_Hypothesis/SPE_BF_Analysis_Report.md）：
  Core G3-G8: F(5,59)=2.95, p=.019, η²=.200, BF10(r=.5)=2.83, BF10(r=1)=3.29
  Regression SPE~P+T+W (Clean): R²=.055, BF10=.76（旧值把 G7 当 T=80，冻结版改为 T=30）
"""
import os
import re
import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import quad

PROJ_ROOT = r"d:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
STATS_DIR = os.path.join(PROJ_ROOT, "2_Data", "Real_Data", "HDDM_Traces")
OUT_DIR = os.path.join(PROJ_ROOT, "5_Reference")

# ---- 权威设计表（冻结规格书 §2）----
DESIGN = {
    1: {"P": 0,   "T_ms": 30,  "W_ms": 300,  "M_ms": 330,  "Label": "G1 | P0_T30_W300"},
    2: {"P": 0,   "T_ms": 30,  "W_ms": 600,  "M_ms": 630,  "Label": "G2 | P0_T30_W600"},
    3: {"P": 120, "T_ms": 30,  "W_ms": 600,  "M_ms": 630,  "Label": "G3 | P120_T30_W600"},
    4: {"P": 120, "T_ms": 80,  "W_ms": 600,  "M_ms": 680,  "Label": "G4 | P120_T80_W600"},
    5: {"P": 8,   "T_ms": 100, "W_ms": 1100, "M_ms": 1200, "Label": "G5 | P8_T100_W1100"},
    6: {"P": 120, "T_ms": 500, "W_ms": 1500, "M_ms": 2000, "Label": "G6 | P120_T500_W1500"},
    7: {"P": 120, "T_ms": 30,  "W_ms": 800,  "M_ms": 830,  "Label": "G7 | P120_T30_W800"},   # 2026-09-02 冻结：T=30
    8: {"P": 120, "T_ms": 80,  "W_ms": 800,  "M_ms": 880,  "Label": "G8 | P120_T80_W800"},
}


def extract_subject_spe(stats_dir):
    """从 *_stats.csv 提取被试级 SPE_v。group_id 从文件名解析；P/T/W 一律查 DESIGN。"""
    records = []
    files = sorted(f for f in os.listdir(stats_dir) if f.endswith("_stats.csv"))
    for fname in files:
        m = re.match(r"hddm_data_group(\d+)_P\d+_T\d+_W\d+_stats\.csv", fname)
        if not m:
            print(f"  SKIP(无法解析): {fname}")
            continue
        gid = int(m.group(1))
        df = pd.read_csv(os.path.join(stats_dir, fname), index_col=0)
        v0 = sorted(c for c in df.index if c.startswith("v_subj(0)."))
        v1 = sorted(c for c in df.index if c.startswith("v_subj(1)."))
        if not v0 or not v1:
            print(f"  SKIP(无被试级 v): {fname}")
            continue
        for a, b in zip(v0, v1):
            subj = int(a.split(".")[1])
            records.append({
                "group_id": gid, "subject": subj,
                "P": DESIGN[gid]["P"], "T_ms": DESIGN[gid]["T_ms"],
                "W_ms": DESIGN[gid]["W_ms"], "M_ms": DESIGN[gid]["M_ms"],
                "v_stranger": df.loc[a, "mean"], "v_self": df.loc[b, "mean"],
                "SPE_v": df.loc[b, "mean"] - df.loc[a, "mean"],
            })
        print(f"  group {gid} {DESIGN[gid]['Label']}: {len(v0)} 名被试")
    return pd.DataFrame(records)


def anova_oneshot(df, dv="SPE_v", grp="group_id"):
    """单因素 ANOVA + 效应量（不依赖 statsmodels）"""
    gs = [df[df[grp] == g][dv].values for g in sorted(df[grp].unique())]
    k, N = len(gs), len(df)
    ss_b = sum(len(g) * (g.mean() - df[dv].mean()) ** 2 for g in gs)
    ss_w = sum(((g - g.mean()) ** 2).sum() for g in gs)
    ss_t = ss_b + ss_w
    F, p = stats.f_oneway(*gs)
    eta2 = ss_b / ss_t
    f_obs = np.sqrt(eta2 / (1 - eta2)) if eta2 < 1 else np.inf
    return {"k": k, "N": N, "F": F, "df1": k - 1, "df2": N - k, "p": p,
            "eta2": eta2, "f_obs": f_obs}


def gpower_min_f(k, N, alpha=0.05, power=0.80):
    """G*Power 敏感性：80% power 下可检测的最小 f（非中心 F）"""
    df1, df2 = k - 1, N - k
    fcrit = stats.f.ppf(1 - alpha, df1, df2)

    def pw(f):
        return 1 - stats.ncf.cdf(fcrit, df1, df2, N * f ** 2)

    lo, hi = 1e-3, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if pw(mid) < power:
            lo = mid
        else:
            hi = mid
    f_min = (lo + hi) / 2
    return {"f_min": f_min, "eta2_min": f_min ** 2 / (1 + f_min ** 2),
            "df1": df1, "df2": df2, "verified_power": pw(f_min)}


def jzs_prior_g(g, r):
    if g <= 0:
        return 0.0
    return (r / np.sqrt(2 * np.pi)) * g ** -1.5 * np.exp(-r ** 2 / (2 * g))


def bf_anova_jzs(df, r=0.5, dv="SPE_v", grp="group_id"):
    """单因素 ANOVA 的 JZS BF10（组别→哑变量的固定效应回归形式，Liang et al. 2008）。

    说明：notebook 原 'bf_oneway_anova_jzs' 积分式经复算存在缺陷（对强效应也返回≈0），
    旧报告数字 (Core 2.83/3.29, All 3.02/3.39) 与本回归形式完全一致，故冻结版采用本实现。
    """
    y = df[dv].values
    X = pd.get_dummies(df[grp], prefix=grp, drop_first=True).astype(float).values
    n, p = len(y), X.shape[1]
    Xc = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    R2 = 1 - ((y - Xc @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    def integrand(g):
        if g <= 0:
            return 0.0
        return ((1 + g) ** ((n - p - 1) / 2)
                * (1 + g * (1 - R2)) ** (-(n - 1) / 2) * jzs_prior_g(g, r))

    bf10, _ = quad(integrand, 1e-10, np.inf, limit=300)
    return {"BF10": bf10, "R2": R2, "a": p + 1, "N": n}


def bf_reg_jzs(X, y, r=0.5):
    """Rouder & Morey JZS 回归 BF10（复刻 notebook 实现）"""
    n, p = len(y), X.shape[1]
    Xc = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    yhat = Xc @ beta
    R2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    def integrand(g):
        if g <= 0:
            return 0.0
        return ((1 + g) ** ((n - p - 1) / 2)
                * (1 + g * (1 - R2)) ** (-(n - 1) / 2) * jzs_prior_g(g, r))

    bf10, _ = quad(integrand, 1e-10, np.inf, limit=200)
    return {"BF10": bf10, "R2": R2, "n": n, "p": p}


def main():
    print("=" * 78)
    print("冻结版 BF/ANOVA 重跑  2026-09-02   （设计参数来自冻结表，G7=T30）")
    print("=" * 78)
    df_subj = extract_subject_spe(STATS_DIR)
    print(f"\n被试级记录总数: {len(df_subj)}")
    print(df_subj.groupby("group_id").size())

    df_all = df_subj.copy()
    df_core = df_subj[~df_subj["group_id"].isin([1, 2])].copy()
    df_clean = df_core[np.abs(df_core["SPE_v"]) <= 30].copy()
    df_g58 = df_subj[df_subj["group_id"].isin([5, 6, 7, 8])].copy()

    rows = []
    print("\n" + "-" * 78)
    print("A. 单因素 ANOVA（SPE_v ~ group）+ G*Power 敏感性")
    print("-" * 78)
    for label, df in [("All  G1-G8", df_all), ("Core G3-G8", df_core),
                      ("Clean G3-G8", df_clean), ("G5-G8 稳健子集", df_g58)]:
        a = anova_oneshot(df)
        g = gpower_min_f(a["k"], a["N"])
        ok = "YES" if a["f_obs"] >= g["f_min"] else "NO"
        print(f"{label:>12}: F({a['df1']},{a['df2']})={a['F']:.3f}, p={a['p']:.4f}, "
              f"eta2={a['eta2']:.3f}, f_obs={a['f_obs']:.3f} | f_min(80%)={g['f_min']:.3f} [{ok}]")
        rows.append({"stat": f"ANOVA {label}", "F": a["F"], "df1": a["df1"], "df2": a["df2"],
                     "p": a["p"], "eta2": a["eta2"], "f_obs": a["f_obs"],
                     "f_min80": g["f_min"], "N": a["N"]})

    print("\n" + "-" * 78)
    print("B. JZS ANOVA 贝叶斯因子 BF10（r=0.5 / 1.0 / sqrt2）")
    print("-" * 78)
    for label, df in [("All  G1-G8", df_all), ("Core G3-G8", df_core), ("Clean G3-G8", df_clean)]:
        vals = [bf_anova_jzs(df, r=rr) for rr in (0.5, 1.0, np.sqrt(2))]
        print(f"{label:>12}: BF10 = " + " / ".join(f"{v['BF10']:.3f}" for v in vals)
              + f"   (R²={vals[0]['R2']:.3f}, N={vals[0]['N']})")
        rows.append({"stat": f"BF ANOVA {label} r=0.5", "value": vals[0]["BF10"]})

    print("\n" + "-" * 78)
    print("C. 回归 SPE_v ~ P + T + W（JZS BF，r=0.5；冻结口径 G7=T30）")
    print("-" * 78)
    for label, df in [("Clean G3-G8", df_clean), ("Core G3-G8", df_core), ("G5-G8", df_g58)]:
        X = df[["P", "T_ms", "W_ms"]].values
        y = df["SPE_v"].values
        r = bf_reg_jzs(X, y, r=0.5)
        print(f"{label:>12}: R²={r['R2']:.4f}, BF10={r['BF10']:.4f}  (n={r['n']}, p={r['p']})")
        rows.append({"stat": f"Regress {label}", "R2": r["R2"], "BF10": r["BF10"], "n": r["n"]})

    print("\n" + "-" * 78)
    print("D. 对比：回归 R² 在 G7=T30（冻结）vs G7=T80（旧错标）下的差异（Clean G3-G8）")
    print("-" * 78)
    df_t80 = df_clean.copy()
    df_t80.loc[df_t80["group_id"] == 7, "T_ms"] = 80
    df_t80.loc[df_t80["group_id"] == 7, "M_ms"] = 880
    for nm, d in [("G7=T30 (冻结)", df_clean), ("G7=T80 (旧)", df_t80)]:
        X = d[["P", "T_ms", "W_ms"]].values
        y = d["SPE_v"].values
        Xc = np.column_stack([np.ones(len(y)), X])
        beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
        yhat = Xc @ beta
        R2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        print(f"  {nm}: 回归 R² = {R2:.4f}")

    # 保存锁定表（S03-S05 用）
    lock = pd.DataFrame(rows)
    out_csv = os.path.join(OUT_DIR, "lock_BF_ANOVA_20260902.csv")
    lock.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n已保存锁定表: {out_csv}")


if __name__ == "__main__":
    main()
