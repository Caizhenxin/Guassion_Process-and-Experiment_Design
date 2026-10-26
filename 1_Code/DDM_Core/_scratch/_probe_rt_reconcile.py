"""对账 2：为什么 trial_clean 有 8,355 正式响应试次，stage8 只用 7,144？

并给出**同一口径**（stage8 保留的试次）下的 RT 分带正确率 —— 这是「快带
是不是猜测通道」唯一站得住的证据基础。原 `_probe_bimodal.py` 用 trial_clean
全量（含 stage8 明确剔掉的抢按/刺激期内按键），会系统性夸大快带规模。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))

import stage8_run as S            # noqa: E402
from mapping import MappingParams  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
tc = pd.read_csv(REPO / "2_Data" / "Generate_Data" / "_real_check" / "trial_clean.csv",
                 encoding="utf-8-sig")
tc = tc[tc["is_formal"].astype(bool)]

people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
print(f"\n{'被试':>10s}{'trial_clean':>12s}{'stage8保留':>11s}{'剔':>6s}"
      f"{'tc≤0.4s':>9s}{'保≤0.4s':>9s}")
tot_tc = tot_keep = 0
for p in people:
    g, s = p["group"], p["subject"]
    sub = tc[(tc["groupID"] == g) & (tc["subjectID"] == s)]
    keep = p["n_trials"]
    tot_tc += len(sub)
    tot_keep += keep
    print(f"{g}-{s:<8d}{len(sub):>12d}{keep:>11d}{len(sub) - keep:>6d}"
          f"{int((sub['rt_ms'] <= 400).sum()):>9d}")
print(f"{'合计':>10s}{tot_tc:>12d}{tot_keep:>11d}{tot_tc - tot_keep:>6d}")

# --- 同一口径：把 trial_clean 限制到 stage8 会保留的试次 ---
print("\n推断剔除规则：trial_clean 的哪一列能解释差值？")
for col in ("premature", "timeout", "responded_by_deadline", "is_self"):
    if col in tc.columns:
        print(f"  {col}: 非零 {int(tc[col].astype(bool).sum())}")
if "dur_dev_ms" in tc.columns:
    dev = tc["dur_dev_ms"].abs()
    print(f"  |dur_dev|>一帧(16.7): {int((dev > 16.7).sum())}、"
          f">33.3: {int((dev > 33.3).sum())}")
