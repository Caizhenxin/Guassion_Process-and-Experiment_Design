"""t0 位移的自检：同样漂移/边界，只把 t0 减 20 ms，中位 RT 应该正好降 20 ms。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
import spe_locus as S  # noqa: E402

rng = np.random.default_rng(7)
for t0 in (0.19, 0.17):
    rt, side, om = S.simulate(800, 0.9, 1.566, t0, rng)
    ok = ~np.isnan(rt)
    print(f"t0={t0:.3f}s  n={ok.sum():4d}  med {np.median(rt[ok])*1000:6.1f} ms  "
          f"p10 {np.quantile(rt[ok],0.1)*1000:6.1f}  p90 {np.quantile(rt[ok],0.9)*1000:6.1f}  "
          f"遗漏 {om:.3f}  acc {(side[ok]==1).mean():.3f}")
