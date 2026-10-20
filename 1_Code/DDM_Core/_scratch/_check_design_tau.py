# -*- coding: utf-8 -*-
"""核对 design 口径下 τP 为何只需 8 人：打印各水平 se_d 与 rel。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import numpy as np
import design_search as DS

DS.use_truth("design")
T4 = [0.0333, 0.0833, 0.14999, 0.24998]
W = [0.79998, 1.19990, 1.79990]
print("WITHIN_TRUTH beta_P/P_ref:", DS.WITHIN_TRUTH.beta_P, DS.WITHIN_TRUTH.P_ref)
for lv in ([0, 8, 32, 120], [0, 8, 24, 64, 120]):
    ses = []
    for p in lv:
        s = DS.subject_se(float(p), T4, W, 12, n_fim=2)
        ses.append(s["d_ref"])
        print(f"  P={p:4d} se_d={s['d_ref']:.4f}")
    used = [p for p, s in zip(lv, ses) if 1e-9 < s < 1.0]
    se_used = np.array([s for s in ses if 1e-9 < s < 1.0])
    print(f"  有效水平 {used} se={np.round(se_used,3)}")
    if len(used) >= 2:
        for n in (8, 20, 40, 160):
            r = DS.rel_group(n, se_used, np.array(used, float))
            print(f"    n={n:4d} beta_P={r['beta_P']:.3f} tau_P={r['tau_P']:.3f}")
