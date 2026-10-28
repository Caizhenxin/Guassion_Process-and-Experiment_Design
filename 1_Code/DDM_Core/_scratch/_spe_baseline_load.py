"""SPE 真实分布基准 · 步骤 1：统一读数层（D134）

三个来源，同一套指标定义：
  A 文献库  D:\\GitHub_programe\\GitHub\\SPE_Database\\1_Data\\**\\*_Clean*.csv
            口径 = 沿用 SPE_Database 既有流程（matching 试次、ACC==1、RT 150–3000 ms、
            被试内 MAD 3.5 修剪、每单元 >=5 试次、身份取 Shape_Standardized_Identity）
  A2 文献库的 practice-vs-main 轴（practice_effect_workflow.PRACTICE_AXIS_SPECS）
  B 本项目旧数据  2_Data/Real_Data/UnExtact/raw/EXP_data_group*.csv（87 人，8 组设计）
            口径 = 该范式是"自我/他人"二选判断，身份取 Label；RT 有效 = Correct==1 且
            150 ms <= RT <= T+W；仅展示、不进基准
  C 多天练习  Hu_YQ_2026_ChinaSciData_Exp3 的 phase 轴（00_practice … 09_formal）

统一输出列（长表，被试级）：
  source, dataset, level, subject, other_identity,
  n_rt_self, n_rt_other, RT_self, RT_other, dRT, dRT_med,
  n_acc_self, n_acc_other, ACC_self, ACC_other, dACC,
  omit_rate, design, note
  dRT = other - self（正值 = 自我更快，即通常所说的 SPE 方向）
  dACC = self - other

用法： python -X utf8 _spe_baseline_load.py [--only lit|old|practice|all]
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
DB = Path(r"D:\GitHub_programe\GitHub\SPE_Database")
PE_FILE = DB / "Datasets" / "11_Practice-Effect" / "practice_effect_workflow.py"
OUT = ROOT / "2_Data" / "Real_Data" / "_spe_baseline"

# 文献库口径常量（与 practice_effect_workflow.py 一致）
MIN_RT_MS, MAX_RT_MS = 150.0, 3000.0
MAD_Z = 3.5
MIN_CELL = 5

IDENTITY_ORDER = ["Self", "Close", "Acquaintance", "Celebrity", "Stranger", "NonPerson"]


# --------------------------------------------------------------------------
# 文献库：复用 11_Practice-Effect 的既有流程
# --------------------------------------------------------------------------
def load_pe():
    if not PE_FILE.exists():
        raise FileNotFoundError(PE_FILE)
    spec = importlib.util.spec_from_file_location("pew", PE_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def subject_spe_wrap(pew, d: pd.DataFrame, level_col: str, min_cell: int = MIN_CELL):
    """compute_subject_level_spe 的薄封装：补上缺失的水平列，捕获异常。"""
    try:
        return pew.compute_subject_level_spe(d, level_col=level_col, min_cell=min_cell)
    except Exception as exc:  # noqa: BLE001
        print(f"    ! compute_subject_level_spe 失败: {exc}")
        return pd.DataFrame()


def lit_rows(pew) -> list[dict]:
    groups = pew.find_logical_datasets()
    print(f"[lit] 逻辑数据集 {len(groups)} 个")
    rows: list[dict] = []
    skipped: list[str] = []
    for lid, paths in groups.items():
        try:
            raw = pew.read_clean(paths)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{lid}: read {exc}")
            continue
        need = {"Subject", "Matching", "Shape_Standardized_Identity", "RT_ms", "ACC"}
        miss = need - set(raw.columns)
        if miss:
            skipped.append(f"{lid}: 缺列 {sorted(miss)}")
            continue
        try:
            d = pew.prep_trials(raw)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{lid}: prep {exc}")
            continue
        d["Level"] = "all"
        spe = subject_spe_wrap(pew, d, "Level")
        if spe.empty:
            skipped.append(f"{lid}: 无 Self 或有效单元")
            continue
        n_subj = d["Subject"].nunique()
        n_trial = len(d)
        for rec in spe.itertuples(index=False):
            rows.append(dict(
                source="lit", dataset=lid, level="all", subject=rec.Subject,
                other_identity=rec.comparison_identity,
                n_rt_self=rec.n_rt_self, n_rt_other=rec.n_rt_other,
                RT_self=rec.RT_mean_self, RT_other=rec.RT_mean_other,
                dRT=(rec.RT_mean_other - rec.RT_mean_self),
                dRT_med=np.nan,
                n_acc_self=rec.n_acc_self, n_acc_other=rec.n_acc_other,
                ACC_self=rec.ACC_mean_self, ACC_other=rec.ACC_mean_other,
                dACC=(rec.ACC_mean_self - rec.ACC_mean_other),
                omit_rate=np.nan, design="", note=f"n_subj={n_subj};n_trial={n_trial}",
            ))
    print(f"[lit] 纳入 {len(rows)} 被试×身份行；跳过 {len(skipped)} 个数据集")
    for s in skipped:
        print("    -", s)
    return rows


def practice_axis_rows(pew) -> list[dict]:
    """文献库中带 practice 主效应的数据集：practice vs main 两个水平。"""
    groups = pew.find_logical_datasets()
    rows: list[dict] = []
    specs = pew.PRACTICE_AXIS_SPECS
    for lid, paths in groups.items():
        spec = specs.get(lid)
        if not spec:
            continue
        col, mapping = spec
        try:
            raw = pew.read_clean(paths)
        except Exception as exc:  # noqa: BLE001
            print(f"    ! {lid} read {exc}")
            continue
        need = {"Subject", "Matching", "Shape_Standardized_Identity", "RT_ms", "ACC", col}
        if need - set(raw.columns):
            print(f"    ! {lid} 缺列 {sorted(need - set(raw.columns))}")
            continue
        raw["Level"] = raw[col].astype(str).str.strip().str.lower().map(mapping)
        raw = raw[raw["Level"].notna()]
        if raw["Level"].nunique() < 2:
            continue
        d = pew.prep_trials(raw)
        spe = subject_spe_wrap(pew, d, "Level")
        if spe.empty:
            continue
        for rec in spe.itertuples(index=False):
            rows.append(dict(
                source="lit_practice", dataset=lid, level=rec.Level, subject=rec.Subject,
                other_identity=rec.comparison_identity,
                n_rt_self=rec.n_rt_self, n_rt_other=rec.n_rt_other,
                RT_self=rec.RT_mean_self, RT_other=rec.RT_mean_other,
                dRT=(rec.RT_mean_other - rec.RT_mean_self), dRT_med=np.nan,
                n_acc_self=rec.n_acc_self, n_acc_other=rec.n_acc_other,
                ACC_self=rec.ACC_mean_self, ACC_other=rec.ACC_mean_other,
                dACC=(rec.ACC_mean_self - rec.ACC_mean_other),
                omit_rate=np.nan, design="", note=f"axis={col}",
            ))
    print(f"[lit_practice] 纳入 {len(rows)} 行")
    return rows


# --------------------------------------------------------------------------
# B 本项目旧数据（87 人 / 8 组设计）
# --------------------------------------------------------------------------
DESIGN_LABEL = {
    (0, 30, 300): "D1", (0, 30, 600): "D2", (120, 30, 600): "D3a",
    (120, 80, 600): "D4a", (8, 100, 1100): "D5", (120, 500, 1500): "D6",
    (120, 30, 800): "D3b", (120, 80, 800): "D4b",
}


def old_rows() -> list[dict]:
    fs = sorted((ROOT / "2_Data" / "Real_Data" / "UnExtact" / "raw").glob("EXP_data_group*.csv"))
    print(f"[old] 文件 {len(fs)}")
    rows: list[dict] = []
    skipped_old: list[str] = []
    for f in fs:
        d = pd.read_csv(f)
        if d.empty:
            continue
        d["Label"] = d["Label"].astype(str).str.strip().str.lower()
        d["Correct"] = pd.to_numeric(d["Correct"], errors="coerce")
        d["RT_ms"] = pd.to_numeric(d["RT"], errors="coerce") * 1000.0
        # 注意：这些文件里 P 已经是 ms（计数），T/W 是秒
        p = int(round(float(d["P"].iloc[0])))
        t = int(round(float(d["T"].iloc[0]) * 1000))
        w = int(round(float(d["W"].iloc[0]) * 1000))
        design = DESIGN_LABEL.get((p, t, w), f"P{p}T{t}W{w}")
        rt = d[(d["Correct"] == 1) & d["RT_ms"].between(MIN_RT_MS, t + w)]
        acc = d[d["Correct"].isin([0, 1])]
        n_timeout = int((d["Correct"] == 0).sum())
        gid, sid = int(d["groupID"].iloc[0]), int(d["subjectID"].iloc[0])
        subj = f"g{gid}s{sid}"
        rs, ro = rt[rt["Label"] == "self"], rt[rt["Label"] == "stranger"]
        as_, ao = acc[acc["Label"] == "self"], acc[acc["Label"] == "stranger"]
        if len(rs) < MIN_CELL or len(ro) < MIN_CELL:
            skipped_old.append(f"{subj} {design}: 自我 {len(rs)} / 他人 {len(ro)} 试次不足")
            continue
        rows.append(dict(
            source="old", dataset=design, level="all", subject=subj,
            other_identity="Stranger",
            n_rt_self=len(rs), n_rt_other=len(ro),
            RT_self=float(rs["RT_ms"].mean()), RT_other=float(ro["RT_ms"].mean()),
            dRT=float(ro["RT_ms"].mean() - rs["RT_ms"].mean()),
            dRT_med=float(ro["RT_ms"].median() - rs["RT_ms"].median()),
            n_acc_self=len(as_), n_acc_other=len(ao),
            ACC_self=float(as_["Correct"].mean()) if len(as_) else np.nan,
            ACC_other=float(ao["Correct"].mean()) if len(ao) else np.nan,
            dACC=(float(as_["Correct"].mean() - ao["Correct"].mean())
                  if len(as_) and len(ao) else np.nan),
            omit_rate=n_timeout / max(len(d), 1), design=f"P{p}/T{t}/W{w}",
            note=f"n_trial={len(d)};n_timeout={n_timeout}",
        ))
    print(f"[old] 纳入 {len(rows)} 被试；跳过 {len(skipped_old)} 个")
    for s in skipped_old[:10]:
        print("    -", s)
    return rows


# --------------------------------------------------------------------------
# C 多天练习（Hu_YQ_2026_ChinaSciData Exp3 phase 轴）
# --------------------------------------------------------------------------
def practice_exp3_rows(pew) -> list[dict]:
    f = DB / "1_Data" / "Hu_YQ_2026_ChinaSciData" / "Exp3" / "Hu_YQ_2026_ChinaSciData_Exp3_Clean.csv"
    if not f.exists():
        print(f"[practice] 缺文件 {f}")
        return []
    raw = pew.read_clean([f])
    if "Phase" not in raw.columns:
        print("[practice] 无 Phase 列")
        return []
    d = pew.prep_trials(raw)
    spe = subject_spe_wrap(pew, d, "Phase")
    if spe.empty:
        return []
    rows = []
    for rec in spe.itertuples(index=False):
        rows.append(dict(
            source="practice", dataset="Hu_YQ_2026_ChinaSciData_Exp3", level=rec.Level,
            subject=rec.Subject, other_identity=rec.comparison_identity,
            n_rt_self=rec.n_rt_self, n_rt_other=rec.n_rt_other,
            RT_self=rec.RT_mean_self, RT_other=rec.RT_mean_other,
            dRT=(rec.RT_mean_other - rec.RT_mean_self), dRT_med=np.nan,
            n_acc_self=rec.n_acc_self, n_acc_other=rec.n_acc_other,
            ACC_self=rec.ACC_mean_self, ACC_other=rec.ACC_mean_other,
            dACC=(rec.ACC_mean_self - rec.ACC_mean_other),
            omit_rate=np.nan, design="", note="exp3_phase",
        ))
    print(f"[practice] 纳入 {len(rows)} 行，phase {sorted(spe['Level'].unique())}")
    return rows


# --------------------------------------------------------------------------
# 汇总
# --------------------------------------------------------------------------
def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """数据集×水平×对比身份 的分布摘要（被试级均值的汇总量）。"""
    out = []
    key = ["source", "dataset", "level", "other_identity"]
    for k, g in df.groupby(key, dropna=False):
        x = pd.to_numeric(g["dRT"], errors="coerce").dropna()
        y = pd.to_numeric(g["dACC"], errors="coerce").dropna()
        rec = dict(zip(key, k))
        rec.update(n_subj=int(len(g)),
                   n_dRT=int(len(x)),
                   dRT_mean=float(x.mean()) if len(x) else np.nan,
                   dRT_sd=float(x.std(ddof=1)) if len(x) > 1 else np.nan,
                   dRT_med=float(x.median()) if len(x) else np.nan,
                   dRT_dz=float(x.mean() / x.std(ddof=1)) if len(x) > 1 and x.std(ddof=1) > 0 else np.nan,
                   dACC_mean=float(y.mean()) if len(y) else np.nan,
                   dACC_dz=float(y.mean() / y.std(ddof=1)) if len(y) > 1 and y.std(ddof=1) > 0 else np.nan)
        if len(x) > 2:
            t, p = stats_ttest(x)
            rec["dRT_t"] = t
            rec["dRT_p"] = p
        else:
            rec["dRT_t"] = np.nan
            rec["dRT_p"] = np.nan
        out.append(rec)
    res = pd.DataFrame(out)
    return res.sort_values(["source", "dataset", "level", "other_identity"])


def stats_ttest(x):
    from scipy import stats
    t, p = stats.ttest_1samp(np.asarray(x, float), 0.0)
    return float(t), float(p)


def main() -> None:
    only = "all"
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            only = sys.argv[i + 1]
    OUT.mkdir(parents=True, exist_ok=True)
    pew = load_pe()
    rows: list[dict] = []
    if only in ("lit", "all"):
        rows += lit_rows(pew)
    if only in ("practice", "all"):
        rows += practice_axis_rows(pew)
        rows += practice_exp3_rows(pew)
    if only in ("old", "all"):
        rows += old_rows()
    if not rows:
        print("没有产出任何行")
        return
    df = pd.DataFrame(rows)
    cols = ["source", "dataset", "level", "subject", "other_identity",
            "n_rt_self", "n_rt_other", "RT_self", "RT_other", "dRT", "dRT_med",
            "n_acc_self", "n_acc_other", "ACC_self", "ACC_other", "dACC",
            "omit_rate", "design", "note"]
    df = df[cols]
    p_subj = OUT / ("spe_subject_level.csv" if only == "all" else f"spe_subject_level_{only}.csv")
    df.to_csv(p_subj, index=False, encoding="utf-8-sig")
    print(f"saved {p_subj}  ({len(df)} 行, {df['dataset'].nunique()} 数据集)")

    if only != "old":
        summ = summarize(df[df["source"] != "old"])
        p_sum = OUT / ("spe_level_summary.csv" if only == "all" else f"spe_level_summary_{only}.csv")
        summ.to_csv(p_sum, index=False, encoding="utf-8-sig")
        print(f"saved {p_sum}  ({len(summ)} 行)")
        # 控制台要点：Stranger 对比的总体分布
        s = summ[summ["other_identity"] == "Stranger"]
        if len(s):
            print("\n== Stranger 对比（数据集级）dRT 分布 ==")
            print(s["dRT_mean"].describe().round(1).to_string())
            print(f"  正号（自我更快）占比: {(s['dRT_mean'] > 0).mean():.1%}"
                  f"  ({int((s['dRT_mean'] > 0).sum())}/{len(s)})")
            print("\n== dACC 分布 ==")
            print(s["dACC_mean"].describe().round(4).to_string())
            print(f"  正号占比: {(s['dACC_mean'] > 0).mean():.1%}")


if __name__ == "__main__":
    main()
