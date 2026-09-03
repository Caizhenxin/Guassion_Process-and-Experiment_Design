# -*- coding: utf-8 -*-
"""
GP+Sigmoid 冻结版重跑（6 条件 = G3-G8） — 2026-09-02
====================================================
依据：《冻结规格书_v1_20260902.md》
- 输入：既有 step3_cleaned_hddm_params_main.csv（该表经行为元数据校正，G7 行已是 T30/W800/M830）
- 只保留 G3-G8 六行做：Sigmoid 校准 → GP 训练(in-sample) → LOCV(6折) → 行为验证 → 候选点
- 不覆盖原有 8 条件产物；输出到 2_Data/Generate_Data/GP_Sigmoid_Frozen6 与 3_Figures/GP_Sigmoid_Frozen6
"""
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_cleaned_validation_pipeline as P  # 复用全部函数（模块级 OUT_* 将被 monkeypatch 重定向）

FROZEN_DATA = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6"
FROZEN_FIG = BASE / "3_Figures" / "GP_Sigmoid_Frozen6"
P.OUT_DATA_DIR = FROZEN_DATA
P.OUT_FIG_DIR = FROZEN_FIG
FROZEN_DATA.mkdir(parents=True, exist_ok=True)
FROZEN_FIG.mkdir(parents=True, exist_ok=True)

KEEP = {3, 4, 5, 6, 7, 8}


def main():
    cfg = P.PipelineConfig(seed=42)
    src = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Cleaned" / "step3_cleaned_hddm_params_main.csv"
    clean = pd.read_csv(src)
    clean["_gid"] = clean["source_group_ids"].astype(str)
    df6 = clean[clean["_gid"].isin([str(g) for g in sorted(KEEP)])].reset_index(drop=True).copy()
    ids = sorted(int(x) for x in df6["source_group_ids"])
    print(f"[frozen6] 建模条件 G{ids}, n = {len(df6)}")
    g7 = df6[df6["source_group_ids"].astype(str) == "7"]
    print("[frozen6] G7 行坐标(应为 T30/W800/M830):",
          g7[["P", "T_ms", "W_ms", "M_ms"]].to_dict("records"))
    df6.to_csv(FROZEN_DATA / "input_conditions_g3g8.csv", index=False)

    print("\n[step4] Sigmoid 校准 + GP 训练（6 条件 in-sample）...")
    model, params, pred_df, train_metrics = P.train_gp_sigmoid(df6, cfg, label="frozen6")
    print(params)
    print(train_metrics.round(4).to_string(index=False))

    print("\n[step4] LOCV（6 折 Leave-One-Condition-Out）...")
    locv_df, locv_metrics = P.run_locv(df6, cfg)
    print(locv_metrics.round(4).to_string(index=False))
    P.plot_step4_results(pred_df, locv_df)

    print("\n[step5] 行为验证（模拟 6 条件 vs 真实 6 条件）...")
    real = P.prepare_real_matching_data()
    sim, comp_group, behavior_metrics = P.behavior_validation(model, real, df6, cfg)
    print(behavior_metrics.round(4).to_string(index=False))

    print("\n[step6] 候选实验点（GP 预测不确定性）...")
    candidates = P.find_candidate_design_points(model, df6, cfg)
    print(candidates.head(8).round(4).to_string(index=False))

    summary = {
        "label": "frozen6 (G3-G8)", "source": str(src), "run": "2026-09-02", "seed": cfg.seed,
        "sigmoid_params": params,
        "training_metrics": train_metrics.to_dict("records"),
        "locv_metrics": locv_metrics.to_dict("records"),
        "behavior_metrics": behavior_metrics.to_dict("records"),
        "top_candidates": candidates.head(8).to_dict("records"),
    }
    (FROZEN_DATA / "frozen6_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n完成 ->", FROZEN_DATA)


if __name__ == "__main__":
    main()
