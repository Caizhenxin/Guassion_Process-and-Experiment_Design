# -*- coding: utf-8 -*-
"""_probe_rho_fit.py —— ρ 的**实战**可辨识性：拟合从哪个初值出发才收敛？

承接 `_probe_rho_oracle.py`：oracle LRT（ρ=0.6，单人）= 28.1，说明设计有信息。
但实跑拟合给出 ρ̂=0.84、LRT=0.85 ⇒ 大概率是**优化器**问题而非设计问题。
本探针把同一份模拟数据用四个起点各拟一遍，定位是哪一个环节丢的。
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

from likelihood import fit_mle, trials_from_arrays                  # noqa: E402
from mapping import match_lin_to_exp                                # noqa: E402
from recover_group import GROUP_INIT_LIN, GROUP_TRUTH_EXP           # noqa: E402
from simulate import build_design, design_arrays, draw_subject_params  # noqa: E402
from twophase import (fit_mle_step, log_likelihood_step,            # noqa: E402
                      simulate_euler_subject)

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
TRUTH_LIN, _ = match_lin_to_exp(GROUP_TRUTH_EXP, T_LEVELS, W_LEVELS)
DESIGN = build_design(120.0, T_LEVELS, W_LEVELS, 12)
ARRAYS = design_arrays(DESIGN)
NAMES = ["d_ref", "beta_T", "beta_S", "beta_ST", "a_ref", "delta_a", "t0", "dz_S"]

RHO_TRUE = 0.60
rng = np.random.default_rng(4242)
p_sub = draw_subject_params(TRUTH_LIN, rng, mode="truncate")
sim = simulate_euler_subject(DESIGN, p_sub, RHO_TRUE, rng, dt=1e-4)
tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *ARRAYS)
rt_min = float(np.nanmin(sim["rt"]))
ov = {"t0": (0.05, min(0.60, max(rt_min - 0.005, 0.06)))}

print(f"真值 ρ={RHO_TRUE}；oracle ℓ(ρ_true)={log_likelihood_step(p_sub, tr, RHO_TRUE, n_x=201):.3f}")
print(f"oracle ℓ(ρ=1)={log_likelihood_step(p_sub, tr, 1.0, n_x=201):.3f}；t0 界={ov['t0']}")
print(f"真值参数：{ {n: round(float(getattr(p_sub, n)), 3) for n in NAMES} }")
print()

for tag, init in (("群体初值", GROUP_INIT_LIN), ("真值起跑", p_sub)):
    for restart in (1, 4):
        f3 = fit_mle(tr, NAMES, init, n_restart=restart, seed=7, maxiter=400,
                     maxfun=20000, bounds_override=ov, gtol=1e-9, ftol=1e-13)
        f1 = fit_mle_step(tr, NAMES, f3["params"], rho_init=RHO_TRUE, n_restart=2,
                          seed=8, maxiter=400, maxfun=20000, bounds_override=ov,
                          gtol=1e-9, ftol=1e-13, n_x=201)
        est = {n: round(float(getattr(f1["params"], n)), 3) for n in NAMES}
        print(f"[{tag} restart={restart}] ℓ3={f3['loglik']:.2f} ℓ1={f1['loglik']:.2f} "
              f"LRT={2 * (f1['loglik'] - f3['loglik']):.2f} ρ̂={f1['rho']:.3f}")
        print(f"        估参：{est}")
