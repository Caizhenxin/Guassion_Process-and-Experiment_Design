# -*- coding: utf-8 -*-
"""check_euler_dt.py —— Euler 生成器的步长收敛性（判断 B 段 0.03 正确率偏差是不是离散化偏差）

若偏差随 dt 以 **O(√dt)** 缩小（首次通过问题的标准弱阶），则它是离散化偏差，
用足够小的 dt 即可压低；若偏差与 dt 无关，则说明生成器有实现错误。

同时对每个 dt 报 P(τ<T) 与 P(RT<T)，明确二者的差别（RT = τ + t0，t0 = 220 ms）。
"""
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from mapping import MappingParams, match_lin_to_exp
from simulate import build_design, simulate_subject
from twophase import simulate_euler_subject

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
T0 = 0.22

TRUTH_EXP = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70, t0=T0,
    z_ratio=0.50, shape_model="exp")
TRUTH_LIN, _ = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)
design = build_design(120.0, T_LEVELS, W_LEVELS, N_REP)

N_REP_EVAL = 6


def stats(sim, design):
    kept = sim["omission"] == 0
    om = float(np.mean(sim["omission"]))
    m = kept & (design["is_match"] == 1)
    acc = float(np.mean(sim["side"][m] == 1))
    rt = sim["rt"][kept]
    Tk = design["T"][kept]
    return (om, acc, float(np.mean(rt)) * 1000,
            float(np.mean(rt - T0 < Tk)),      # P(τ < T)
            float(np.mean(rt < Tk)))           # P(RT < T)


print(f"{'generator':<22}{'omission':>10}{'accuracy':>10}{'meanRT':>9}"
      f"{'P(tau<T)':>10}{'P(RT<T)':>10}{'sec':>7}")
print("-" * 78)

t_start = time.perf_counter()
acc_rows, om_rows, rt_rows, pt_rows, pr_rows = [], [], [], [], []
for r in range(N_REP_EVAL):
    s = simulate_subject(design, TRUTH_LIN, np.random.default_rng(500 + r))
    o, a, rt, pt, pr = stats(s, design)
    om_rows.append(o); acc_rows.append(a); rt_rows.append(rt)
    pt_rows.append(pt); pr_rows.append(pr)
print(f"{'analytic (exact)':<22}{np.mean(om_rows):>10.4f}{np.mean(acc_rows):>10.4f}"
      f"{np.mean(rt_rows):>9.2f}{np.mean(pt_rows):>10.4f}{np.mean(pr_rows):>10.4f}"
      f"{time.perf_counter() - t_start:>7.2f}")

a_ref = np.mean(acc_rows)
o_ref = np.mean(om_rows)
rt_ref = np.mean(rt_rows)

for dt in (2e-4, 1e-4, 5e-5, 2.5e-5):
    t0_ = time.perf_counter()
    acc_rows, om_rows, rt_rows, pt_rows, pr_rows = [], [], [], [], []
    for r in range(N_REP_EVAL):
        s = simulate_euler_subject(design, TRUTH_LIN, 1.0,
                                   np.random.default_rng(500 + r), dt=dt)
        o, a, rt, pt, pr = stats(s, design)
        om_rows.append(o); acc_rows.append(a); rt_rows.append(rt)
        pt_rows.append(pt); pr_rows.append(pr)
    a_e, o_e, rt_e = np.mean(acc_rows), np.mean(om_rows), np.mean(rt_rows)
    print(f"{'Euler dt=' + f'{dt:g}':<22}{o_e:>10.4f}{a_e:>10.4f}"
          f"{rt_e:>9.2f}{np.mean(pt_rows):>10.4f}{np.mean(pr_rows):>10.4f}"
          f"{time.perf_counter() - t0_:>7.2f}   "
          f"|dacc|={abs(a_e - a_ref):.4f} dom={abs(o_e - o_ref):.4f} "
          f"dRT={abs(rt_e - rt_ref):.1f}ms")

print(f"\n参考：dt 减半时 |dacc| 的比值应 ≈ √2 = 1.414（O(√dt) 签名）")
