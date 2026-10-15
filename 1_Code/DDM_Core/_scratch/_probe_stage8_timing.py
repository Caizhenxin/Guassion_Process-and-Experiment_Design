"""_probe_stage8_timing.py —— Stage 8 层级件的成本探测（**一次性**）。

问：一次 `log_likelihood_step`、一次 Hessian(K 维)、一次 L-BFGS 众数搜索各要多久？
据此决定层级自测（5 名被试 × 若干次外层评估）的规模。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from likelihood import _bounds_for, _from_x, _to_x         # noqa: E402
from mapping import MappingParams                          # noqa: E402
from simulate import build_design                          # noqa: E402
from stage8 import hessian_x                               # noqa: E402
from twophase import log_likelihood_step, simulate_euler_subject  # noqa: E402

NAMES = ["d_ref", "beta_T", "beta_S", "beta_ST"]
TRUTH = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                      shape_model="lin")

for tag, T_lv, W_lv, rep in (
        ("576 试次", [0.03333, 0.08333, 0.14999, 0.24998], [0.79998, 1.19990, 1.79990], 12),
        ("192 试次", [0.03333, 0.14999], [0.79998, 1.79990], 12),
        ("96 试次", [0.03333, 0.14999], [0.79998, 1.79990], 6)):
    design = build_design(30.0, T_lv, W_lv, rep)
    n = design["T"].size
    rng = np.random.default_rng(7)
    t0 = time.perf_counter()
    sim = simulate_euler_subject(design, TRUTH, 0.6, rng, dt=5e-5)
    t_gen = time.perf_counter() - t0
    tr = dict(design)
    tr.update({k: np.asarray(v) for k, v in sim.items()})

    t0 = time.perf_counter()
    ll = log_likelihood_step(TRUTH, tr, 0.6)
    t_ll = time.perf_counter() - t0

    lo, hi = _bounds_for(NAMES, None)
    x0 = _to_x(TRUTH.vector(NAMES), lo, hi)

    def g(x):
        return log_likelihood_step(TRUTH.with_vector(NAMES, _from_x(x, lo, hi)), tr, 0.6)

    t0 = time.perf_counter()
    hessian_x(g, x0)
    t_h = time.perf_counter() - t0
    t0 = time.perf_counter()
    minimize(lambda x: -g(x), x0, method="L-BFGS-B", options={"maxiter": 60})
    t_mode = time.perf_counter() - t0
    print(f"{tag}: 生成 {t_gen:5.2f}s | 单次 ll {t_ll * 1000:7.2f} ms | "
          f"Hessian(K=4) {t_h:6.2f}s | L-BFGS(≤60) {t_mode:6.2f}s | ll = {ll:9.3f}")
    print(f"          外层 1 次评估（5 人，含 Hessian）≈ "
          f"{5 * (t_mode + t_h):6.1f}s；10 次外层 ≈ {5 * 10 * (t_mode + t_h):7.1f}s")
