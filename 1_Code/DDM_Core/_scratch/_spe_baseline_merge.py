"""SPE 基线 · 步骤 1b：合并三源 + 定位本项目与文献分布的相对位置（D134）

输入（由 _spe_baseline_load.py 生成）：
  spe_subject_level_lit.csv / _practice.csv / spe_subject_level.csv（old，源内命名）
输出：
  spe_subject_level_all.csv    三源合并（被试级）
  spe_level_summary_all.csv    数据集×水平×身份 汇总
  spe_position.csv             本项目各口径在文献分布中的分位
控制台打印一张「文献 vs 我们」的对照表。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
D = ROOT / "2_Data" / "Real_Data" / "_spe_baseline"


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    key = ["source", "dataset", "level", "other_identity"]
    for k, g in df.groupby(key, dropna=False):
        x = pd.to_numeric(g["dRT"], errors="coerce").dropna()
        y = pd.to_numeric(g["dACC"], errors="coerce").dropna()
        rec = dict(zip(key, k))
        rec.update(n_subj=int(g["subject"].nunique()), n_dRT=int(len(x)),
                   dRT_mean=float(x.mean()) if len(x) else np.nan,
                   dRT_sd=float(x.std(ddof=1)) if len(x) > 1 else np.nan,
                   dRT_med=float(x.median()) if len(x) else np.nan,
                   dRT_dz=float(x.mean() / x.std(ddof=1)) if len(x) > 1 and x.std(ddof=1) > 0 else np.nan,
                   dACC_mean=float(y.mean()) if len(y) else np.nan,
                   dACC_dz=float(y.mean() / y.std(ddof=1)) if len(y) > 1 and y.std(ddof=1) > 0 else np.nan)
        out.append(rec)
    return pd.DataFrame(out)


def pct_rank(dist, v):
    dist = np.asarray(dist, float)
    dist = dist[~np.isnan(dist)]
    if len(dist) == 0 or np.isnan(v):
        return np.nan
    return float((dist < v).mean() * 100)


def main() -> None:
    lit_f = D / "spe_subject_level_lit.csv"
    pra_f = D / "spe_subject_level_practice.csv"
    old_f = D / "spe_subject_level_old.csv"
    frames = []
    for f, src in ((lit_f, "lit"), (pra_f, "practice"), (old_f, "old")):
        if not f.exists():
            print(f"缺 {f}")
            continue
        d = pd.read_csv(f, encoding="utf-8-sig")
        d["source"] = src if src != "old" else "old"
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(D / "spe_subject_level_all.csv", index=False, encoding="utf-8-sig")
    summ = summarize(df)
    summ.to_csv(D / "spe_level_summary_all.csv", index=False, encoding="utf-8-sig")
    print(f"合并 {len(df)} 行 / {df['dataset'].nunique()} 数据集 → spe_subject_level_all.csv")

    lit = summ[(summ.source == "lit") & (summ.other_identity == "Stranger")]
    lit_rt = lit["dRT_mean"].dropna()
    lit_acc = lit["dACC_mean"].dropna()

    # 本项目口径：新设计 17 人（已实测）、生成模型两版
    ours = [
        dict(name="本项目新设计 17 人（实测）", dRT=33.0, dACC=0.067),
        dict(name="生成模型 TRUTH_LIN", dRT=8.0, dACC=0.054),
        dict(name="生成模型 校准真值", dRT=33.0, dACC=0.067),
        dict(name="生成模型 旧 v2.4", dRT=221.0, dACC=0.258),
    ]
    rows = []
    for o in ours:
        rows.append(dict(name=o["name"], dRT=o["dRT"], dACC=o["dACC"],
                         dRT_pct=pct_rank(lit_rt, o["dRT"]),
                         dACC_pct=pct_rank(lit_acc, o["dACC"])))
    pos = pd.DataFrame(rows)
    pos.to_csv(D / "spe_position.csv", index=False, encoding="utf-8-sig")

    print("\n== 文献分布（Stranger 对比，71 个数据集级效应） ==")
    print(f"  dRT  : mean {lit_rt.mean():.1f}  median {lit_rt.median():.1f}  "
          f"IQR [{lit_rt.quantile(.25):.1f}, {lit_rt.quantile(.75):.1f}]  "
          f"range [{lit_rt.min():.1f}, {lit_rt.max():.1f}]")
    print(f"  dACC : mean {lit_acc.mean():.3f}  median {lit_acc.median():.3f}  "
          f"IQR [{lit_acc.quantile(.25):.3f}, {lit_acc.quantile(.75):.3f}]")
    print("\n== 本项目各口径的位置 ==")
    print(pos.round(3).to_string(index=False))

    print("\n== 身份梯度（文献，中位 dRT） ==")
    g = (summ[summ.source == "lit"]
         .groupby("other_identity")
         .agg(n_datasets=("dataset", "nunique"),
              dRT_med=("dRT_mean", "median"), dACC_med=("dACC_mean", "median"))
         .sort_values("dRT_med", ascending=False))
    print(g.round(2).to_string())

    print("\n== 练习效应（practice 轴，dataset×level） ==")
    p = summ[summ.source == "practice"]
    for (ds, lv), gg in p.groupby(["dataset", "level"]):
        x = gg[gg.other_identity == "Stranger"]
        if len(x) == 0:
            continue
        print(f"  {ds:42s} {lv:10s} dRT {x.dRT_mean.iloc[0]:8.1f}  "
              f"n={int(x.n_subj.iloc[0]):3d}  dACC {x.dACC_mean.iloc[0]:+.3f}")

    print("\n== 旧数据（87 人，按设计，仅展示） ==")
    o = summ[summ.source == "old"]
    print(o[["dataset", "n_subj", "dRT_mean", "dACC_mean"]]
          .sort_values("dataset").round(2).to_string(index=False))


if __name__ == "__main__":
    main()
