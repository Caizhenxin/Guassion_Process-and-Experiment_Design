# -*- coding: utf-8 -*-
"""固定总人数下的分配：把多的被试放到 32/120 两组是否更划算。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import numpy as np

import design_search as DS
from mapping import f_P
from simulate import SUBJECT_SD

T4 = [0.0333, 0.0833, 0.14999, 0.24998]
W3 = [0.79998, 1.19990, 1.79990]
se120 = DS.subject_se(120.0, T4, W3, 12, n_fim=2)["d_ref"]
se32 = DS.subject_se(32.0, T4, W3, 12, n_fim=2)["d_ref"]
tau, ref = DS.GROUP_TRUTH["tau_P"], DS.GROUP_P_REF
P = np.array([32.0, 120.0])
b = f_P(P, tau) - f_P(ref, tau)
J = np.column_stack([np.ones_like(b), b])


def sd_bp(n32, n120):
    v = np.array([(SUBJECT_SD["d_ref"] ** 2 + se32 ** 2) / n32,
                  (SUBJECT_SD["d_ref"] ** 2 + se120 ** 2) / n120])
    cov = np.linalg.pinv(J.T @ (J / v[:, None]))
    return float(np.sqrt(np.diag(cov))[1])


print("beta_P 只用 {32,120} 两组时，总人数 48 的不同分配（真值 1.5）")
for n32, n120 in ((10, 10), (12, 12), (8, 16), (6, 18), (16, 16), (15, 15), (20, 20)):
    sd = sd_bp(n32, n120)
    print(f"  32 组={n32:3d}  120 组={n120:3d}  合计={n32 + n120:3d}  "
          f"sd={sd:.4f}  相对={sd / 1.5:.3f}  95%CI=±{1.96 * sd:.3f}")
