# -*- coding: utf-8 -*-
"""_probe_rho_oracle.py —— ρ 的**理想**（oracle）可辨识性：不做拟合，直接在真值处比似然。

目的：把「ρ 估不出来」分成两种原因——
  (a) 设计本身信息不足（oracle LRT 就很小）；
  (b) 优化器没跑到真值（oracle LRT 大，但拟合的 ρ̂ 偏）。
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

from likelihood import log_likelihood, trials_from_arrays        # noqa: E402
from mapping import match_lin_to_exp                             # noqa: E402
from recover_group import GROUP_TRUTH_EXP                        # noqa: E402
from simulate import build_design, design_arrays, draw_subject_params  # noqa: E402
from twophase import log_likelihood_step, simulate_euler_subject  # noqa: E402

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
TRUTH_LIN, _ = match_lin_to_exp(GROUP_TRUTH_EXP, T_LEVELS, W_LEVELS)
DESIGN = build_design(120.0, T_LEVELS, W_LEVELS, 12)
ARRAYS = design_arrays(DESIGN)

print(f"{'ρ_true':>7}{'ρ̂_oracle':>12}{'ℓ(ρ_true)':>12}{'ℓ(ρ=1)':>11}{'LRT':>9}{'acc':>7}{'omit':>7}")
for rho in (0.0, 0.4, 0.6, 0.8, 1.0, 1.2):
    rng = np.random.default_rng(4242)
    p_sub = draw_subject_params(TRUTH_LIN, rng, mode="truncate")
    sim = simulate_euler_subject(DESIGN, p_sub, rho, rng, dt=1e-4)
    tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *ARRAYS)
    ll_true = log_likelihood_step(p_sub, tr, rho, n_x=201)
    ll_one = log_likelihood_step(p_sub, tr, 1.0, n_x=201)
    # 网格扫 ρ（其余参数固定为真值）⇒ 只看 ρ 这一维的信息量
    grid = np.linspace(0.0, 2.0, 21)
    lls = np.array([log_likelihood_step(p_sub, tr, float(r), n_x=201) for r in grid])
    kept = sim["omission"] == 0
    acc = float(np.mean(sim["side"][kept & (DESIGN["is_match"] == 1)] == 1))
    print(f"{rho:>7.2f}{grid[int(np.argmax(lls))]:>12.2f}{ll_true:>12.2f}"
          f"{ll_one:>11.2f}{2 * (ll_true - ll_one):>9.2f}{acc:>7.3f}"
          f"{np.mean(sim['omission']):>7.3f}")
