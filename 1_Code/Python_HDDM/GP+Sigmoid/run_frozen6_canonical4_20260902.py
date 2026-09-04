# -*- coding: utf-8 -*-
"""
GP+Sigmoid 冻结版重跑（规范 4 链参数，G3–G8）— 2026-09-02
===========================================================
输入：2_Data/Generate_Data/HDDM_Diagnostics/all_G3_G8_4chain_group.csv
      （多链规范参数，替代旧单链 all_groups 来源）
流程：Sigmoid 校准 → GP 训练(in-sample) → LOCV(6折) → 行为验证 → 候选点
输出：2_Data/Generate_Data/GP_Sigmoid_Canonical4/ + 3_Figures/GP_Sigmoid_Canonical4/
"""
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_cleaned_validation_pipeline as P

FROZEN_DATA = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Canonical4"
FROZEN_FIG = BASE / "3_Figures" / "GP_Sigmoid_Canonical4"
P.OUT_DATA_DIR = FROZEN_DATA
P.OUT_FIG_DIR = FROZEN_FIG
FROZEN_DATA.mkdir(parents=True, exist_ok=True)
FROZEN_FIG.mkdir(parents=True, exist_ok=True)

SRC = BASE / "2_Data" / "Generate_Data" / "HDDM_Diagnostics" / "all_G3_G8_4chain_group.csv"


def main():
    cfg = P.PipelineConfig(seed=42)
    t = pd.read_csv(SRC)
    t = t.rename(columns={"v_stranger_mean": "v_stranger_mean",
                          "v_self_mean": "v_self_mean"})
    df6 = t.copy()
    df6["source_group_ids"] = df6["group_id"].astype(str)
    df6["condition_id"] = df6["group_id"].astype(int)
    df6["M_ms"] = df6["T_ms"] + df6["W_ms"]
    df6 = df6.sort_values("group_id").reset_index(drop=True)
    print("[canonical4] 建模条件:", sorted(df6["group_id"].astype(int).tolist()), "n=", len(df6))
    print(df6[["group_id", "P", "T_ms", "W_ms", "v_stranger_mean",
               "v_self_mean", "a_mean", "t_mean", "z_mean", "SPE_v"]].round(3).to_string(index=False))
    df6.to_csv(FROZEN_DATA / "input_conditions_g3g8_canonical4.csv", index=False)

    print("\n[step4] Sigmoid 校准 + GP 训练 ...")
    model, params, pred_df, train_metrics = P.train_gp_sigmoid(df6, cfg, label="canonical4")
    print(params)
    print(train_metrics.round(4).to_string(index=False))

    print("\n[step4] LOCV（6 折）...")
    locv_df, locv_metrics = P.run_locv(df6, cfg)
    print(locv_metrics.round(4).to_string(index=False))
    P.plot_step4_results(pred_df, locv_df)

    print("\n[step5] 行为验证...")
    real = P.prepare_real_matching_data()
    sim, comp_group, behavior_metrics = P.behavior_validation(model, real, df6, cfg)
    # 修正 r：仅保留非空配对格（同冻结版处理）
    rows = []
    comp_id = pd.read_csv(FROZEN_DATA / "step5_behavior_validation_by_identity.csv")
    comp_g = pd.read_csv(FROZEN_DATA / "step5_behavior_validation_by_condition.csv")

    def safe_corr(x, y):
        m = pd.concat([x, y], axis=1).dropna()
        return P.safe_corr(m.iloc[:, 0], m.iloc[:, 1])

    for col in ["acc", "omission_rate", "correct_rt_mean_ms"]:
        rows.append({"level": "identity", "target": col,
                     "rmse": P.rmse(comp_id[col + "_real"], comp_id[col + "_sim"]),
                     "mae": float((comp_id[col + "_sim"] - comp_id[col + "_real"]).abs().mean()),
                     "r": safe_corr(comp_id[col + "_real"], comp_id[col + "_sim"]),
                     "n_pairs": int(pd.concat([comp_id[col + "_real"], comp_id[col + "_sim"]], axis=1).dropna().shape[0])})
    for col in ["acc", "omission_rate", "SPE_RT_ms"]:
        rows.append({"level": "condition", "target": col,
                     "rmse": P.rmse(comp_g[col + "_real"], comp_g[col + "_sim"]),
                     "mae": float((comp_g[col + "_sim"] - comp_g[col + "_real"]).abs().mean()),
                     "r": safe_corr(comp_g[col + "_real"], comp_g[col + "_sim"]),
                     "n_pairs": int(pd.concat([comp_g[col + "_real"], comp_g[col + "_sim"]], axis=1).dropna().shape[0])})
    met = pd.DataFrame(rows)
    met.to_csv(FROZEN_DATA / "step5_behavior_validation_metrics.csv", index=False)
    print(met.round(4).to_string(index=False))

    print("\n[step6] 候选点...")
    candidates = P.find_candidate_design_points(model, df6, cfg)
    print(candidates.head(8).round(4).to_string(index=False))

    summary = {"label": "canonical4 (G3-G8, 4-chain HDDM)", "source": str(SRC), "run": "2026-09-02",
               "seed": cfg.seed, "sigmoid_params": params,
               "training_metrics": train_metrics.to_dict("records"),
               "locv_metrics": locv_metrics.to_dict("records"),
               "behavior_metrics": met.to_dict("records"),
               "top_candidates": candidates.head(8).to_dict("records")}
    (FROZEN_DATA / "canonical4_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n完成 ->", FROZEN_DATA)


if __name__ == "__main__":
    main()
