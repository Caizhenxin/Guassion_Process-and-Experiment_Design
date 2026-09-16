# -*- coding: utf-8 -*-
"""
spe_database_analysis_v2.py —— 直接用 SPE 数据库本体做 §8 分析（2026-09-13）
==========================================================================
与 v1 的差别：v1 只用项目内的一份旧快照（2_Data/Real_Data/SPE_Database/*_SP.csv，63 个数据集），
本版直接读数据库项目本体：
    D:/GitHub_programe/GitHub/SPE_Database/1_Data/Dataset_inf.csv   ← 主索引（权威元数据）
    D:/GitHub_programe/GitHub/SPE_Database/1_Data/<Study>/...*_Clean.csv ← 清洗后试次级数据
并据此报告：数据库当前规模、**本文实际可分析子集**的精确规模、跨研究 SPE 分布、
以及设计变量（练习量/试次数）的探索性调节效应与敏感性分析。

清洗规则（与 v1 一致，便于对照）
    仅匹配试次；身份仅 Self / Stranger；ACC ∈ {0,1}；RT ∈ [150, 3000] ms；
    被试需在两种身份各有 ≥5 个正确试次；数据集需 ≥10 名有效被试。

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/spe_database_v2/
    T8-1b_dataset_level.csv      逐数据集（含索引元数据、实际规模、SPE、设计参数）
    T8-2b_pooled.csv             汇总（cluster bootstrap）
    T8-3b_moderators.csv         调节效应（练习量、试次数；bootstrap CI）
    T8-4b_sensitivity.csv        敏感性分析（身份口径 / 任务口径 / RT 窗口）
    excluded_datasets.csv        排除清单与原因
3_Figures/Thesis_v3_20260912/F8-4_spe_database.png（覆盖更新）
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import OUT_DATA_DIR, OUT_FIG_DIR, setup_cjk_font  # noqa: E402

warnings.filterwarnings("ignore")

DB = Path("D:/GitHub_programe/GitHub/SPE_Database")
INDEX = DB / "1_Data" / "Dataset_inf.csv"
OUT = OUT_DATA_DIR / "spe_database_v2"
OUT.mkdir(parents=True, exist_ok=True)

USECOLS_HINT = ["Subject", "Matching", "RT_ms", "RT_sec", "ACC",
                "Label_Standardized_Identity", "Shape_Standardized_Identity",
                "P_trials", "T_ms", "W_ms", "Block", "Trial", "Response", "Identity"]
NEED = {"Subject", "ACC"}


def find_clean_csv(folder: str, exp) -> Path | None:
    d = DB / "1_Data" / folder
    if not d.exists():
        return None
    cands = sorted(d.glob("*_Clean.csv"))
    if not cands:
        return None
    if exp is not None and not pd.isna(exp):
        e = int(exp)
        hit = [c for c in cands if f"Exp{e}" in c.name or f"exp{e}" in c.name]
        if hit:
            return hit[0]
    return cands[0] if len(cands) == 1 else None


def load_clean(path: Path) -> pd.DataFrame | None:
    try:
        head = pd.read_csv(path, nrows=0)
    except Exception:
        return None
    use = [c for c in head.columns if c in USECOLS_HINT]
    if not NEED.issubset(set(head.columns)):
        return None
    return pd.read_csv(path, usecols=use, low_memory=False)


def dataset_spe(df: pd.DataFrame, rt_lo=150.0, rt_hi=3000.0, id_pref="label",
                identity_set=("Self", "Stranger"), min_cell=5, min_subj=10):
    cols = set(df.columns)
    id_col = None
    if id_pref == "label" and "Label_Standardized_Identity" in cols:
        id_col = "Label_Standardized_Identity"
    elif "Shape_Standardized_Identity" in cols:
        id_col = "Shape_Standardized_Identity"
    elif "Label_Standardized_Identity" in cols:
        id_col = "Label_Standardized_Identity"
    if id_col is None or "Subject" not in cols or "ACC" not in cols:
        return None, "缺少身份/被试/ACC 列"

    d = df.copy()
    if "Matching" in cols:
        m = d["Matching"].astype(str).str.lower()
        d = d[m.str.contains("match") & ~m.str.contains("non")]
    d = d[d[id_col].isin(list(identity_set))]
    d["ACC"] = pd.to_numeric(d["ACC"], errors="coerce")
    d = d[d["ACC"].isin([0, 1])]
    if "RT_ms" in cols:
        rt = pd.to_numeric(d["RT_ms"], errors="coerce")
    elif "RT_sec" in cols:
        rt = pd.to_numeric(d["RT_sec"], errors="coerce") * 1000
    else:
        return None, "缺少 RT 列"
    d["rt_ms"] = rt
    d = d[d["rt_ms"].between(rt_lo, rt_hi)]
    if d.empty:
        return None, "清洗后无有效试次"

    rows = []
    for subj, g in d.groupby("Subject"):
        s = g[g[id_col] == "Self"]; t = g[g[id_col] == "Stranger"]
        sc, tc = s[s.ACC == 1], t[t.ACC == 1]
        if len(sc) < min_cell or len(tc) < min_cell:
            continue
        rows.append({"Subject": subj, "SPE_RT": sc.rt_ms.mean() - tc.rt_ms.mean(),
                     "SPE_ACC": s.ACC.mean() - t.ACC.mean()})
    sub = pd.DataFrame(rows)
    if len(sub) < min_subj:
        return None, f"有效被试不足（{len(sub)}<{min_subj}）"
    se = sub.SPE_RT.std(ddof=1) / np.sqrt(len(sub))
    crit = stats.t.ppf(0.975, len(sub) - 1)
    return {"n_subjects_used": len(sub), "n_trials_used": int(len(d)),
            "SPE_RT_mean": sub.SPE_RT.mean(), "SPE_RT_se": se,
            "SPE_RT_lo": sub.SPE_RT.mean() - crit * se, "SPE_RT_hi": sub.SPE_RT.mean() + crit * se,
            "SPE_ACC_mean": sub.SPE_ACC.mean(),
            "pct_subj_self_faster": float((sub.SPE_RT < 0).mean()),
            "identity_source": id_col}, ""


def main():
    idx = pd.read_csv(INDEX, encoding="utf-8-sig")
    print(f"[db] 主索引：{len(idx)} 行 / {idx.Folder_Name.nunique()} 个研究")
    print(f"[db] 索引口径的合计有效被试：{int(idx.Valid_Subj.fillna(0).sum())}")

    rows, excluded = [], []
    for _, r in idx.iterrows():
        csv = find_clean_csv(str(r.Folder_Name), r.get("Exp"))
        if csv is None:
            excluded.append({"folder": r.Folder_Name, "exp": r.get("Exp"), "reason": "未找到唯一 Clean CSV"})
            continue
        df = load_clean(csv)
        if df is None:
            excluded.append({"folder": r.Folder_Name, "exp": r.get("Exp"), "reason": "缺少必要列"})
            continue
        rec, why = dataset_spe(df)
        if rec is None:
            excluded.append({"folder": r.Folder_Name, "exp": r.get("Exp"), "reason": why})
            continue
        rec.update({"study": r.Folder_Name, "exp": r.get("Exp"), "subj_group": r.get("subj_Group"),
                    "file": csv.name,
                    "index_sample_size": r.get("Sample_Size"), "index_valid_subj": r.get("Valid_Subj"),
                    "practice_trial": pd.to_numeric(r.get("Practice_Trial"), errors="coerce"),
                    "num_trials": pd.to_numeric(str(r.get("numTrials")).split(" ")[0], errors="coerce"),
                    "self_cat": r.get("Self"), "others_cat": r.get("Others"),
                    "stim_type": r.get("Stim_Type"), "design": r.get("Design")})
        rows.append(rec)

    ds = pd.DataFrame(rows)
    ds.to_csv(OUT / "T8-1b_dataset_level.csv", index=False)
    pd.DataFrame(excluded).to_csv(OUT / "excluded_datasets.csv", index=False)
    print(f"\n[db] 可分析子集：{len(ds)} 个数据集 / {int(ds.n_subjects_used.sum())} 名被试 / "
          f"{int(ds.n_trials_used.sum()):,} 试次")

    # 汇总（cluster bootstrap）
    rng = np.random.default_rng(42)
    boot_mean = np.array([ds.iloc[rng.choice(len(ds), len(ds), True)].SPE_RT_mean.mean() for _ in range(1000)])
    pooled = pd.DataFrame([{
        "n_datasets": len(ds), "n_studies": ds.study.nunique(),
        "n_subjects": int(ds.n_subjects_used.sum()), "n_trials": int(ds.n_trials_used.sum()),
        "SPE_RT_mean": ds.SPE_RT_mean.mean(),
        "SPE_RT_ci_lo": np.percentile(boot_mean, 2.5), "SPE_RT_ci_hi": np.percentile(boot_mean, 97.5),
        "SPE_RT_median": ds.SPE_RT_mean.median(),
        "between_dataset_sd": ds.SPE_RT_mean.std(ddof=1),
        "pct_datasets_self_faster": float((ds.SPE_RT_mean < 0).mean()),
        "SPE_ACC_mean": ds.SPE_ACC_mean.mean(),
    }])
    pooled.to_csv(OUT / "T8-2b_pooled.csv", index=False)
    print(pooled.round(3).to_string(index=False))

    # 调节效应
    mods = []
    for col, label in [("practice_trial", "练习试次数 P"), ("num_trials", "总试次数")]:
        v = ds[[col, "SPE_RT_mean"]].dropna()
        if len(v) >= 5:
            rho, p = stats.spearmanr(v[col], v.SPE_RT_mean)
            bs = []
            for _ in range(1000):
                s = v.iloc[rng.choice(len(v), len(v), True)]
                bs.append(stats.spearmanr(s[col], s.SPE_RT_mean)[0] if s[col].nunique() > 1 else np.nan)
            mods.append({"moderator": col, "label": label, "k": len(v), "spearman_rho": rho, "p": p,
                         "ci_lo": np.nanpercentile(bs, 2.5), "ci_hi": np.nanpercentile(bs, 97.5)})
    mod_df = pd.DataFrame(mods)
    mod_df.to_csv(OUT / "T8-3b_moderators.csv", index=False)
    print("\n[db] 调节效应（探索性）：")
    print(mod_df.round(3).to_string(index=False) if len(mod_df) else "  （样本不足）")

    # 敏感性分析
    sens = []
    variants = [("基准（Label 身份，Self vs Stranger）", dict()),
                ("仅 Shape 身份", dict(id_pref="shape")),
                ("RT 窗口 200–1500 ms", dict(rt_lo=200, rt_hi=1500)),
                ("要求 ≥20 名被试的数据集", dict(min_subj=20)),
                ("每被试需 ≥10 个正确试次", dict(min_cell=10))]
    for name, kw in variants:
        rs = []
        for _, r in idx.iterrows():
            csv = find_clean_csv(str(r.Folder_Name), r.get("Exp"))
            if csv is None:
                continue
            df = load_clean(csv)
            if df is None:
                continue
            rec, _ = dataset_spe(df, **kw)
            if rec:
                rs.append(rec["SPE_RT_mean"])
        if rs:
            sens.append({"variant": name, "k_datasets": len(rs), "mean_SPE_RT": float(np.mean(rs)),
                         "median_SPE_RT": float(np.median(rs))})
    sens_df = pd.DataFrame(sens)
    sens_df.to_csv(OUT / "T8-4b_sensitivity.csv", index=False)
    print("\n[db] 敏感性分析：")
    print(sens_df.round(2).to_string(index=False))

    # 图（覆盖 v1 版本）
    setup_cjk_font()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.0))
    order = ds.sort_values("SPE_RT_mean").reset_index(drop=True)
    y = np.arange(len(order))
    axes[0].errorbar(order.SPE_RT_mean, y,
                     xerr=[order.SPE_RT_mean - order.SPE_RT_lo, order.SPE_RT_hi - order.SPE_RT_mean],
                     fmt="o", ms=4, lw=.8, color="#2a6f97")
    axes[0].axvline(0, color="k", ls="--", lw=.8)
    axes[0].axvline(pooled.SPE_RT_mean[0], color="r", ls=":", lw=1.2,
                    label=f"合并均值 {pooled.SPE_RT_mean[0]:.1f} ms")
    axes[0].set_yticks(y[::2]); axes[0].set_yticklabels(order.study[::2], fontsize=6)
    axes[0].set_xlabel("数据集层面 SPE_RT (ms)"); axes[0].legend(fontsize=8)
    axes[0].set_title(f"(A) 逐数据集森林图（k={len(ds)}, {int(ds.n_subjects_used.sum())} 人）")
    for ax, col, lab in [(axes[1], "practice_trial", "练习试次数 P"), (axes[2], "num_trials", "总试次数")]:
        v = ds[[col, "SPE_RT_mean", "n_subjects_used"]].dropna()
        ax.scatter(v[col], v.SPE_RT_mean, s=np.clip(v.n_subjects_used, 5, 300), color="#e76f51",
                   alpha=.7, edgecolor="k", linewidth=.4)
        ax.axhline(0, color="k", ls="--", lw=.8)
        if col == "num_trials":
            ax.set_xscale("log")
        row = mod_df[mod_df.moderator == col]
        ttl = f"(B) SPE ~ {lab}" if col == "practice_trial" else f"(C) SPE ~ {lab}（对数轴）"
        if len(row):
            ax.set_title(f"{ttl}\nρ = {row.spearman_rho.iloc[0]:.2f}（95% CI "
                         f"{row.ci_lo.iloc[0]:.2f} ~ {row.ci_hi.iloc[0]:.2f}, k={int(row.k.iloc[0])}）")
        else:
            ax.set_title(ttl)
        ax.set_xlabel(lab); ax.set_ylabel("数据集层面 SPE_RT (ms)")
    fig.suptitle("图8-4 SPE 数据库（本体最新版）跨研究分布与设计变量关系（探索性）")
    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "F8-4_spe_database.png", dpi=300)
    plt.close(fig)
    print(f"\n[db] 产物 → {OUT}\n[db] 图 → {OUT_FIG_DIR / 'F8-4_spe_database.png'}")


if __name__ == "__main__":
    main()
