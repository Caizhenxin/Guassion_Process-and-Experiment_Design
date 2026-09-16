# -*- coding: utf-8 -*-
"""
refit_downstream_update.py —— 用重跑（4 链 8k）参数更新下游全链（2026-09-13）
==========================================================================
重跑后的参数与历史单链拟合实质不同（例：G3 的 SPE_v 由 −0.16 变为 +0.00，G6 由 0.65 降为 0.19，
G8 的 a 由 2.42 降为 1.30；且 6 个条件全部达到 R̂ ≤ 1.000、ESS ≥ 9,400）。本脚本据此更新：

    ① 被试层 SPE_v（由多链迹线计算）→ 研究一的 ANOVA / BF / G*Power（新 vs 旧对照）
    ② 研究三：Sigmoid 校准 + GP + LOCV + 行为验证 + 候选点（重跑，输出 GP_Sigmoid_Frozen6b）
    ③ 后验预测检验（PPC）：用重跑的被试层后验重新计算覆盖率

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/refit/
    subject_spe_refit.csv         被试层 SPE_v（新）
    spe_v_test_old_vs_new.csv     ANOVA / BF / G*Power 新旧对照
    ppc_refit_by_identity.csv     PPC（新）
    ppc_refit_coverage.csv        PPC 覆盖率（新）
2_Data/Generate_Data/GP_Sigmoid_Frozen6b/   研究三重跑产物（step4~step6）
3_Figures/TenRules_Revision_20260912/ppc_refit_*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import (  # noqa: E402
    FROZEN_GROUPS, OUT_DATA_DIR, OUT_FIG_DIR, TRIALS_PER_IDENTITY, behavior_stats,
    build_trial_params, load_frozen_truth, simulate_trials, setup_cjk_font,
)

REFIT_FITS = OUT_DATA_DIR / "refit" / "fits"
REFIT_TABLE = OUT_DATA_DIR / "refit" / "input_conditions_g3g8_refit.csv"
OLD_TRACES = BASE / "2_Data" / "Real_Data" / "HDDM_Traces"
GP_DIR = BASE / "1_Code" / "Python_HDDM" / "GP+Sigmoid"
BF_DIR = BASE / "1_Code" / "Python_for_Check" / "Basic_Hypothesis"


# ------------------------------------------------------------------
def subject_spe_from_refit(gid: int) -> pd.DataFrame:
    """从重跑多链迹线计算被试层 SPE_v = v_self − v_stranger（每被试取后验均值）。"""
    z = np.load(REFIT_FITS / f"g{gid}_refit_chains.npz")
    idx = sorted({int(k.rsplit(".", 1)[-1]) for k in z.files if k.startswith("v_subj(1).")})
    rows = []
    for i in idx:
        vs = float(np.mean(z[f"v_subj(1).{i}"]))
        vg = float(np.mean(z[f"v_subj(0).{i}"]))
        rows.append({"group_id": gid, "subj_idx": i, "v_self": vs, "v_stranger": vg, "SPE_v": vs - vg})
    return pd.DataFrame(rows)


def subject_spe_from_old(gid: int) -> pd.DataFrame:
    """历史单链迹线（用于新旧对照）。"""
    f = list(OLD_TRACES.glob(f"hddm_data_group{gid}_*_traces.npz"))
    if not f:
        return pd.DataFrame()
    z = np.load(f[0])
    def pick(prefix):
        idx = sorted({int(k.rsplit(".", 1)[-1]) for k in z.files if k.startswith(prefix)})
        return {i: float(np.mean(z[f"{prefix}{i}"])) for i in idx}
    vs = pick("v_subj(1).")
    vg = pick("v_subj(0).")
    return pd.DataFrame([{"group_id": gid, "subj_idx": i, "v_self": vs[i], "v_stranger": vg[i],
                          "SPE_v": vs[i] - vg[i]} for i in sorted(set(vs) & set(vg))])


def run_spe_tests():
    new = pd.concat([subject_spe_from_refit(g) for g in FROZEN_GROUPS], ignore_index=True)
    new.to_csv(OUT_DATA_DIR / "refit" / "subject_spe_refit.csv", index=False)
    old = pd.concat([d for d in (subject_spe_from_old(g) for g in FROZEN_GROUPS) if len(d)],
                    ignore_index=True)

    sys.path.insert(0, str(BF_DIR))
    import BF_freeze_20260902 as BF  # noqa: E402

    rows = []
    for label, df in [("历史单链（3k）", old), ("重跑（4 链 8k）", new)]:
        if df.empty:
            continue
        a = BF.anova_oneshot(df, dv="SPE_v", grp="group_id")
        bf05 = BF.bf_anova_jzs(df, r=0.5, dv="SPE_v", grp="group_id")
        bf10 = BF.bf_anova_jzs(df, r=1.0, dv="SPE_v", grp="group_id")
        N = len(df); k = df.group_id.nunique()
        fmin = BF.gpower_min_f(k, N)
        # 观察效应量 f
        grand = df.SPE_v.mean()
        ss_between = sum(len(g) * (g.SPE_v.mean() - grand) ** 2 for _, g in df.groupby("group_id"))
        ss_total = ((df.SPE_v - grand) ** 2).sum()
        f_obs = float(np.sqrt((ss_between / (k - 1)) / ((ss_total - ss_between) / (N - k)))) if ss_total > ss_between else np.nan
        rows.append({"version": label, "N": N, "k": k,
                     "F": a.get("F"), "df1": a.get("df1"), "df2": a.get("df2"),
                     "p": a.get("p"), "eta_sq": a.get("eta_sq"),
                     "BF10_r0.5": bf05, "BF10_r1.0": bf10,
                     "f_obs": f_obs, "f_min_80power": fmin,
                     "SPE_v_mean": df.SPE_v.mean(), "SPE_v_sd": df.SPE_v.std(ddof=1)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DATA_DIR / "refit" / "spe_v_test_old_vs_new.csv", index=False)
    print("\n[① SPE_v 检验：新 vs 旧]")
    print(out.round(4).to_string(index=False))
    return new


def run_gp_pipeline():
    sys.path.insert(0, str(GP_DIR))
    import run_cleaned_validation_pipeline as P  # noqa: E402
    out_data = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6b"
    out_fig = BASE / "3_Figures" / "GP_Sigmoid_Frozen6b"
    out_data.mkdir(parents=True, exist_ok=True)
    out_fig.mkdir(parents=True, exist_ok=True)
    P.OUT_DATA_DIR = out_data
    P.OUT_FIG_DIR = out_fig

    df6 = pd.read_csv(REFIT_TABLE)
    df6["_gid"] = df6["source_group_ids"].astype(int)
    df6 = df6[df6["_gid"].isin(FROZEN_GROUPS)].reset_index(drop=True)
    cfg = P.PipelineConfig(seed=42)
    print("\n[② 研究三重跑] Sigmoid 校准 + GP（6 条件）…")
    model, params, pred_df, train_metrics = P.train_gp_sigmoid(df6, cfg, label="frozen6b")
    locv_df, locv_metrics = P.run_locv(df6, cfg)

    # 与旧结果对照
    old_p = pd.read_csv(BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6" /
                        "step4_sigmoid_calibrated_params_frozen6.csv")
    cmp_rows = []
    keys = ["alaph1", "alaph2", "beta1", "beta2", "gamma", "base_scale_v", "base_scale_a", "final_rmse"]
    for k in keys:
        if k in old_p.columns and k in params:
            cmp_rows.append({"param": k, "old": float(old_p[k].iloc[0]), "new": float(params[k]),
                             "delta": float(params[k]) - float(old_p[k].iloc[0])})
    cmp_df = pd.DataFrame(cmp_rows)
    cmp_df.to_csv(OUT_DATA_DIR / "refit" / "sigmoid_params_old_vs_new.csv", index=False)
    print(cmp_df.round(3).to_string(index=False))
    print("\n[② LOCV（新）]")
    print(locv_metrics.round(3).to_string(index=False))
    return params, locv_metrics


def run_ppc_refit(n_draws: int = 200, seed: int = 42):
    truth = load_frozen_truth().set_index("group_id")
    rng = np.random.default_rng(seed)
    rows = []
    for gid in FROZEN_GROUPS:
        z = np.load(REFIT_FITS / f"g{gid}_refit_chains.npz")
        idx = sorted({int(k.rsplit(".", 1)[-1]) for k in z.files if k.startswith("v_subj(1).")})
        n_subj = len(idx)
        vs = np.column_stack([z[f"v_subj(1).{i}"].reshape(-1) for i in idx])   # (4*6000, n)
        vg = np.column_stack([z[f"v_subj(0).{i}"].reshape(-1) for i in idx])
        aa = np.column_stack([z[f"a_subj.{i}"].reshape(-1) for i in idx])
        tt = np.column_stack([z[f"t_subj.{i}"].reshape(-1) for i in idx])
        zz = np.column_stack([z[f"z_subj_trans.{i}"].reshape(-1) for i in idx]) if f"z_subj_trans.0" in z.files \
            else np.column_stack([z[f"z_subj.{i}"].reshape(-1) for i in idx])
        from scipy.stats import norm
        zz = norm.cdf(zz)
        sel = rng.choice(vs.shape[0], size=min(n_draws, vs.shape[0]), replace=False)
        deadline = float((truth.loc[gid, "T_ms"] + truth.loc[gid, "W_ms"]) / 1000.0)
        obs_files = list((BASE / "2_Data" / "Real_Data" / "HDDM_Ready").glob(f"hddm_data_group{gid}_*.csv"))
        raw = pd.read_csv(obs_files[0])
        obs = {"all": behavior_stats(raw, rt_unit="sec")}
        for ident, nm in [(1, "self"), (0, "stranger")]:
            obs[nm] = behavior_stats(raw[raw["identity"] == ident], rt_unit="sec")
        pred = {"all": [], "self": [], "stranger": []}
        for d in sel:
            tp = build_trial_params(vs[d], vg[d], aa[d], tt[d], zz[d], TRIALS_PER_IDENTITY)
            sim = simulate_trials(tp["v"], tp["a"], tp["t"], tp["z"], deadline, len(tp["v"]), rng)
            df = pd.DataFrame({"rt": sim["rt"], "response": sim["response"],
                               "omission": sim["omission"], "identity": tp["identity"]})
            pred["all"].append(behavior_stats(df, rt_unit="sec"))
            for ident, nm in [(1, "self"), (0, "stranger")]:
                pred[nm].append(behavior_stats(df[df.identity == ident], rt_unit="sec"))
        for name in ["all", "self", "stranger"]:
            for stat in ["acc_all", "omission_rate", "correct_rt_mean_ms", "correct_rt_q50_ms"]:
                vals = np.array([p[stat] for p in pred[name]], float)
                o = obs[name][stat]
                lo, hi = np.percentile(vals, [2.5, 97.5])
                rows.append({"group_id": gid, "identity": name, "stat": stat, "observed": o,
                             "pred_median": float(np.median(vals)), "pred_lo95": float(lo),
                             "pred_hi95": float(hi), "inside95": int(lo <= o <= hi)})
    by_id = pd.DataFrame(rows)
    by_id.to_csv(OUT_DATA_DIR / "refit" / "ppc_refit_by_identity.csv", index=False)
    cov = by_id.groupby("stat").agg(n_cells=("inside95", "size"),
                                    coverage_95=("inside95", "mean")).reset_index()
    cov.to_csv(OUT_DATA_DIR / "refit" / "ppc_refit_coverage.csv", index=False)
    print("\n[③ PPC（重跑后）覆盖率]")
    print(cov.round(3).to_string(index=False))
    return cov


def main():
    run_spe_tests()
    run_gp_pipeline()
    run_ppc_refit()
    print("\n完成。产物目录：", OUT_DATA_DIR / "refit")


if __name__ == "__main__":
    main()
