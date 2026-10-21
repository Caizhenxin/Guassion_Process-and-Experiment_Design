# -*- coding: utf-8 -*-
"""探针：drift_magnitude 与 trial_params 给出的 v 为什么符号不一致。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CORE = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design/1_Code/DDM_Core")
sys.path.insert(0, str(CORE))

import numpy as np
from mapping import MappingParams, drift_magnitude, trial_params
from simulate import build_design

T = MappingParams(P_ref=30.0, T_ref=0.10, W_ref=1.20, d_ref=0.70, beta_P=0.35, tau_P=30.0,
                  beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_ST=0.10, beta_SP=0.0,
                  w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70, t0=0.22, z_ratio=0.50)
print("shape_model:", T.shape_model)
for P in (0.0, 8.0, 32.0, 120.0):
    d = float(drift_magnitude(np.array([P]), np.array([0.0333]), 0, T)[0])
    print(f"P={P:6.1f} T=33ms drift_magnitude = {d:+.4f}")

design = build_design(0.0, [0.0333], [0.79998], 1)
tp = trial_params(design, T)
print("trial_params v (P=0,T=33):", np.round(tp["v"], 4), "a:", np.round(tp["a"], 4))
print("design is_match:", design["is_match"], "is_self:", design["is_self"])
