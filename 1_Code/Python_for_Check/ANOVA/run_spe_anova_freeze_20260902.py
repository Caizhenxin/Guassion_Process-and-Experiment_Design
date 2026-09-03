# -*- coding: utf-8 -*-
"""
行为层 SPE 单因素 ANOVA 冻结版（S01/S02）— 2026-09-02
=====================================================
口径复刻 `run_spe_anova.py`：
- 数据：EXP_data_combined.csv，仅 formal 试次
- RT：ACC==1 且 RT_ms>0 的正确试次；按 (被试×条件×Matching×Identity) 求平均 RT
      → Matching 下 SPE_RT_ms = Self − Stranger（被试级）
- ACC：全部 formal 试次（omission 计入错误）；SPE_ACC = Self − Stranger（被试级）
- 检验：SPE ~ C(DesignCell) 的单因素 ANOVA（被试间，Type-II 与 f_oneway 一致）
输出：S01(S02) 锁定数字 → 5_Reference/lock_S01_S02_20260902.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "2_Data" / "Real_Data" / "EXP_data_combined.csv"
OUT_LOCK = BASE / "5_Reference" / "lock_S01_S02_20260902.csv"


def design_key(cell: str) -> tuple:
    clean = cell.replace("P", "").replace("T", "").replace("W", "")
    return tuple(map(int, clean.split("_")))


def anova_oneway(y, groups):
    """单因素 ANOVA（纯 scipy），返回 F/p/df/SS/eta2。"""
    gs = [y[groups == g] for g in np.unique(groups)]
    F, p = stats.f_oneway(*gs)
    N = len(y)
    grand = y.mean()
    ss_b = sum(len(g) * (g.mean() - grand) ** 2 for g in gs)
    ss_w = sum(((g - g.mean()) ** 2).sum() for g in gs)
    k = len(gs)
    return {"F": float(F), "p": float(p), "df1": k - 1, "df2": N - k,
            "N": N, "k": k, "ss_b": float(ss_b), "ss_w": float(ss_w),
            "eta2": float(ss_b / (ss_b + ss_w))}


def main():
    df = pd.read_csv(DATA)
    df = df[df["stage"].astype(str).str.lower().eq("formal")].copy()
    df["DesignCell"] = pd.Categorical(
        df["DesignCell"], categories=sorted(df["DesignCell"].unique(), key=design_key), ordered=True)
    df["Matching"] = df["Matching"].astype(str).str.capitalize()
    df["Identity"] = df["Identity"].astype(str).str.capitalize()
    df["ACC"] = df["ACC"].astype(int)

    rt_trials = df[(df["ACC"] == 1) & df["RT_ms"].notna() & (df["RT_ms"] > 0)].copy()
    rt_cell = (rt_trials.groupby(
        ["SubjectUID", "DesignCell", "Matching", "Identity"], observed=True)
        .agg(RT_ms=("RT_ms", "mean")).reset_index())
    acc_cell = (df.groupby(
        ["SubjectUID", "DesignCell", "Matching", "Identity"], observed=True)
        .agg(ACC=("ACC", "mean")).reset_index())

    def spe_from(cell_df, col):
        m = cell_df[cell_df["Matching"] == "Matching"].copy()
        piv = m.pivot_table(index=["SubjectUID", "DesignCell"],
                            columns="Identity", values=col, observed=True).reset_index()
        piv["SPE"] = piv["Self"] - piv["Stranger"]
        return piv.dropna(subset=["SPE"])

    spe_rt = spe_from(rt_cell, "RT_ms")
    spe_acc = spe_from(acc_cell, "ACC")

    rows = []
    print("=" * 70)
    for tag, name, subj_df in [("S01", "SPE_RT (ms)", spe_rt), ("S02", "SPE_ACC", spe_acc)]:
        y = subj_df["SPE"].values
        grp = subj_df["DesignCell"].values
        # 主口径：全部 8 个设计单元
        r8 = anova_oneway(y, grp)
        # 稳健口径：仅 G3-G8 单元（按 DesignCell 名称含 T=30..；用单元格人数前 6?）
        # 精确筛选：保留包含 group 3-8 的单元 —— 通过单元格内被试与已知组人数对照不直接；
        # 直接用 DesignCell 中 P/T/W：G3-G8 即排除 P0_T30_W300 与 P0_T30_W600
        excl = {c for c in np.unique(grp) if design_key(str(c))[0] == 0 and design_key(str(c))[1] == 30}
        keep = ~np.isin(grp, list(excl))
        r6 = anova_oneway(y[keep], grp[keep]) if keep.sum() > 2 else None
        per_cell = subj_df.groupby("DesignCell", observed=True)["SPE"].agg(["mean", "std", "count"])
        print(f"\n[{tag}] {name} —— 全部 8 单元:")
        print(f"  F({r8['df1']},{r8['df2']})={r8['F']:.3f}, p={r8['p']:.4f}, "
              f"eta2={r8['eta2']:.3f}  (N={r8['N']}, SS_b={r8['ss_b']:.1f}, SS_w={r8['ss_w']:.1f})")
        print(f"  —— G3-G8（6 单元, N={int(keep.sum())}）: "
              + (f"F({r6['df1']},{r6['df2']})={r6['F']:.3f}, p={r6['p']:.4f}, eta2={r6['eta2']:.3f}"
                 if r6 else "n/a"))
        print(per_cell.round(3).to_string())
        rows.append({"stat": f"{tag} {name} 8-cell", "F": r8["F"], "df1": r8["df1"], "df2": r8["df2"],
                     "p": r8["p"], "eta2": r8["eta2"], "N": r8["N"], "ss_b": r8["ss_b"], "ss_w": r8["ss_w"]})
        if r6:
            rows.append({"stat": f"{tag} {name} 6-cell(G3-G8)", "F": r6["F"], "df1": r6["df1"],
                         "df2": r6["df2"], "p": r6["p"], "eta2": r6["eta2"], "N": r6["N"],
                         "ss_b": r6["ss_b"], "ss_w": r6["ss_w"]})

    lock = pd.DataFrame(rows)
    lock.to_csv(OUT_LOCK, index=False, encoding="utf-8-sig")
    print(f"\n已保存: {OUT_LOCK}")


if __name__ == "__main__":
    main()
