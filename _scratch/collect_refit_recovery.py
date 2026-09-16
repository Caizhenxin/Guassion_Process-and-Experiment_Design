# -*- coding: utf-8 -*-
"""临时：汇总"以修正参数为真值"的参数恢复结果（拟合产物实际落在 param_recovery/fits）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PKG = BASE / "1_Code" / "Python_for_Check" / "TenRules_Revision_20260912"
sys.path.insert(0, str(PKG))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import param_recovery_frozen6 as PR  # noqa: E402
import sim_utils  # noqa: E402

OUT = sim_utils.OUT_DATA_DIR
# 拟合产物实际位置（脚本内硬编码为 param_recovery/fits）
PR.FITS = OUT / "param_recovery" / "fits"
# 汇总与图输出到 refit 专用目录
PR.PR_ROOT = OUT / "param_recovery_refit"
PR.PR_ROOT.mkdir(parents=True, exist_ok=True)
PR.JOBS_JSON = PR.PR_ROOT / "jobs.json"

jobs = json.loads(PR.JOBS_JSON.read_text(encoding="utf-8"))
print(f"[collect] 作业 {len(jobs)} 个；拟合目录 {PR.FITS}")
print("  真值示例:", jobs[0]["truth"], "| 条件", jobs[0]["group_id"])

by_job = PR.collect(jobs)
print("\n[collect] 完成")
