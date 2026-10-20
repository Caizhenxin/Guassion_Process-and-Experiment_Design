# -*- coding: utf-8 -*-
"""诊断：现行设计下各 P 水平的 se_d，以及 tau_P 判据被谁卡住。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import numpy as np
from design_search import subject_se, rel_se, rel_group, between_cov, JUDGE

T4 = [0.0333, 0.0833, 0.14999, 0.24998]
W3 = [0.79998, 1.19990, 1.79990]
levels = [0, 8, 32, 120]

print("各 P 水平的被试层 SE（4T×3W r12、n_fim=2）：")
se = {}
for p in levels:
    s = subject_se(p, T4, W3, 12, n_fim=2)
    se[p] = s
    print(f"  P={p:4d}  se_d={s['d_ref']:.4f}  se_betaT={s['beta_T']:.4f}  "
          f"se_tauT={s['tau_T']:.4f}  se_a={s['a_ref']:.4f}")

for used in ([8, 32, 120], [32, 120], [0, 32, 120]):
    se_ds = np.array([se[p]["d_ref"] for p in used])
    print(f"\n用水平 {used}（se_d={np.round(se_ds,3)}）:")
    for n in (12, 20, 40, 80, 161):
        r = rel_group(n, se_ds, np.array(used, float))
        print(f"  n={n:4d}  rel_d={r['d_ref']:.3f}  rel_beta_P={r['beta_P']:.3f}  "
              f"rel_tau_P={r['tau_P']:.3f}")
