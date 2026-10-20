# -*- coding: utf-8 -*-
"""探针：各 P 水平下 simulate_subject 的实际行为与漂移真值。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))

import numpy as np
from design_fim import TRUTH, NAMES
from mapping import drift_magnitude
from simulate import build_design, simulate_subject

print("TRUTH 参数：")
for k, v in TRUTH.as_dict().items():
    if isinstance(v, (int, float)):
        print(f"  {k} = {round(float(v), 4)}")
print("NAMES:", NAMES)

T = [0.0333, 0.0833, 0.14999, 0.24998]
W = [0.79998, 1.19990, 1.79990]
for P in (0.0, 8.0, 32.0, 120.0):
    design = build_design(P, T, W, 12)
    sim = simulate_subject(design, TRUTH, np.random.default_rng(1))
    d_truth = float(drift_magnitude(np.array([P]), TRUTH.T_ref, 0, TRUTH)[0])
    resp = sim["omission"] == 0
    is_match = np.asarray(design["is_match"]) == 1
    ok = np.where(is_match, sim["side"] == 1, sim["side"] == 0)
    acc = float(np.mean(ok[resp])) if resp.any() else float("nan")
    print(f"P={P:6.1f}  drift={d_truth:+.4f}  acc={acc:.3f}  "
          f"om={float(sim['omission'].mean()):.3f}  rt={float(np.nanmean(sim['rt'])*1000):.0f}ms")
