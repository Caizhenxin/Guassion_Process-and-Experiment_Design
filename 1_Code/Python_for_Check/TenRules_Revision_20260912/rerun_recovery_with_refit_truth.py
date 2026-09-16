# -*- coding: utf-8 -*-
"""
rerun_recovery_with_refit_truth.py —— 用修正配置参数作真值，重跑参数恢复（2026-09-13）
====================================================================================
背景：§6.3.3 的参数恢复以**历史（未收敛）参数**为真值；配置 C（p_outlier=0、4 链 8k）已修正参数，
故需重跑恢复与遗漏率–偏倚曲线，使表 6-2/6-3 与图 6-3~6-5 与新口径一致。

实现：直接复用 param_recovery_frozen6.py 的全部流程，仅在运行时替换
      ① 真值表（sim_utils.FROZEN6_TABLE → refit/input_conditions_g3g8_refit.csv）
      ② 输出根目录（PR_ROOT → param_recovery_refit）
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import sim_utils  # noqa: E402
import param_recovery_frozen6 as PR  # noqa: E402

REFIT_TABLE = sim_utils.OUT_DATA_DIR / "refit" / "input_conditions_g3g8_refit.csv"
NEW_ROOT = sim_utils.OUT_DATA_DIR / "param_recovery_refit"

assert REFIT_TABLE.exists(), f"缺少修正真值表：{REFIT_TABLE}"

# ① 替换真值与输出位置
sim_utils.FROZEN6_TABLE = REFIT_TABLE
PR.PR_ROOT = NEW_ROOT
PR.PREPARED = NEW_ROOT / "prepared"
PR.FITS = NEW_ROOT / "fits"
PR.JOBS_JSON = NEW_ROOT / "jobs.json"

truth = sim_utils.load_frozen_truth(REFIT_TABLE)
print(f"[refit-recovery] 真值来源：{REFIT_TABLE.name}")
print(truth[["group_id", "v_self", "v_stranger", "a", "t", "z", "n_subjects"]].round(3).to_string(index=False))

SCHEMES = ["censor", "drop"]

# ② 条件恢复（6 条件 × 3 重复 × 2 方案 = 36）+ 遗漏率–偏倚曲线（8 水平 × 2 重复 × 2 = 32）
jobs = PR._jobs_for_datasets(truth, 3, SCHEMES, None, sim_utils.TRIALS_PER_IDENTITY, None, 42, kind="condition")
PR.write_prepared(jobs, append=False)

levels = [float(x) for x in "0.05,0.10,0.15,0.20,0.25,0.35,0.50,0.70".split(",")]
curve_truth = {"v_self": float(truth.v_self.mean()), "v_stranger": float(truth.v_stranger.mean()),
               "a": float(truth.a.mean()), "t": float(truth.t.mean()), "z": float(truth.z.mean())}
jobs_curve = PR._jobs_for_datasets(truth, 2, SCHEMES, None, sim_utils.TRIALS_PER_IDENTITY, None, 42,
                                   kind="curve", curve_levels=levels, curve_truth=curve_truth)
PR.write_prepared(jobs_curve, append=True)

all_jobs = __import__("json").loads(PR.JOBS_JSON.read_text(encoding="utf-8"))
print(f"[refit-recovery] 共 {len(all_jobs)} 个作业待拟合")

# ③ 并行拟合 + 汇总
PR.run_docker(all_jobs, PR.DEFAULT_IMAGE, PR.DEFAULT_MOUNT, dry_run=False,
              skip_existing=True, parallel=4)
PR.collect(all_jobs)
print("[refit-recovery] 完成 →", NEW_ROOT)
