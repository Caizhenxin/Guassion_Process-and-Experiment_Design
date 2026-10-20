# -*- coding: utf-8 -*-
"""探针：rel SE(beta_T) 是否随试次数按 1/sqrt(n) 收缩；以及 2T×2W 为何爆炸。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(_ROOT / "1_Code"))

import numpy as np
from design_search import subject_se, rel_se
from design_fim import TRUTH

T4 = [0.0333, 0.0833, 0.14999, 0.24998]
W3 = [0.79998, 1.19990, 1.79990]

for r in (3, 6, 12, 24):
    for P in (0.0, 120.0):
        se = subject_se(P, T4, W3, r, n_fim=3)
        rl = rel_se(se)
        print(f"r={r:3d} 试次={len(T4)*len(W3)*r:4d} P={P:5.1f} "
              f"rel_beta_T={rl['beta_T']:.4f} rel_d={rl['d_ref']:.4f} "
              f"rel_tau_T={rl['tau_T']:.4f} rel_a={rl['a_ref']:.4f}")

print()
for name, T, W, r in [("2T×2W r36", [0.0333, 0.24998], [0.79998, 1.79990], 36),
                      ("4T×2W r18", T4, [0.79998, 1.79990], 18)]:
    for P in (0.0, 120.0):
        se = subject_se(P, T, W, r, n_fim=3)
        rl = rel_se(se)
        print(f"{name} P={P:5.1f} rel_beta_T={rl['beta_T']:.4e} "
              f"rel_d={rl['d_ref']:.4f} rel_tau_T={rl['tau_T']:.4f} "
              f"rel_a={rl['a_ref']:.4e} rel_t0={rl['t0']:.4f}")
        print("   se:", {k: round(v, 6) for k, v in se.items()})
