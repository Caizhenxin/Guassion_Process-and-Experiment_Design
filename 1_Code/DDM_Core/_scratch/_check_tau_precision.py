# -*- coding: utf-8 -*-
"""交叉校验：tau_P 的解析 Jacobian 精度 vs oracle_power 的蒙特卡洛 precision。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import numpy as np
import oracle_power as OP
from design_search import between_cov, rel_group, GROUP_TRUTH
from recover_group import P_LEVELS, P_COMMON_REF, fit_between, GROUP_FIT_NAMES
from simulate import SUBJECT_SD
from mapping import f_P

print("SUBJECT_SD:", SUBJECT_SD)
print("P_COMMON_REF:", P_COMMON_REF, "P_LEVELS:", P_LEVELS)

# 1) 解析：se_d = 0（纯被试间随机效应）
for n in (12, 20, 40):
    for levels in (P_LEVELS, [0, 8, 24, 64, 120]):
        se0 = np.zeros(len(levels))
        r = rel_group(n, se0, levels)
        print(f"[analytic se_d=0] n={n:3d} levels={levels} -> "
              f"beta_P {r['beta_P']:.3f} tau_P {r['tau_P']:.3f}")

# 2) 蒙特卡洛（同 oracle_power.evaluate）
for n in (12, 20, 40):
    out = OP.evaluate(P_LEVELS, n, n_rep=120)
    print(f"[MC oracle] n={n:3d}  beta_P rmse={out['beta_P']['rmse']:.4f} "
          f"(rel {out['beta_P']['rmse']/0.35:.3f})  "
          f"tau_P rmse={out['tau_P']['rmse']:.2f} (rel {out['tau_P']['rmse']/30.0:.3f})")
