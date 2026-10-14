# -*- coding: utf-8 -*-
"""check_twophase_lik.py —— M-T1 似然接入自检（嵌套一致性 + Euler 生成器标定 + 计时）

判据：
  A. ``rho = 1`` 时 M-T1 逐试次对数似然**逐位等于**单阶段（嵌套成立）；
  B. **Euler 生成器在 rho=1 下必须复现解析单阶段生成器的行为量**
     （遗漏率/正确率/平均 RT）——否则整条 Stage 5 的生成器不可信；
  C. ``rho`` 扫描下的行为量（确认阶跃模型确实改变可观测行为）；
  D. 一次 M-T1 似然求值的耗时（决定功率研究的可行规模）；
  E. ``rho`` 方向上的有限差分曲率（可识别性的第一眼）。
"""
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))   # DDM_Core 本体

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from likelihood import log_likelihood, per_trial_loglik, trials_from_arrays
from mapping import MappingParams, match_lin_to_exp
from simulate import build_design, design_arrays, simulate_subject
from twophase import (log_likelihood_step, per_trial_loglik_step,
                      simulate_euler_subject)

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12

TRUTH_EXP = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70, t0=0.22,
    z_ratio=0.50, shape_model="exp")
TRUTH_LIN, _ = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)

design = build_design(120.0, T_LEVELS, W_LEVELS, N_REP)
n_trials = design["T"].size
print(f"design: {n_trials} trials,  T={sorted(set(design['T']))},  "
      f"W={sorted(set(design['W']))}")


def behaviour(sim, design):
    """(遗漏率, 条件正确率, 平均 RT[ms], RT<T 比例)。"""
    kept = sim["omission"] == 0
    om = float(np.mean(sim["omission"]))
    m = kept & (design["is_match"] == 1)
    acc = float(np.mean(sim["side"][m] == 1)) if np.any(m) else np.nan
    rt = sim["rt"][kept]
    mean_rt = float(np.mean(rt)) * 1000 if rt.size else np.nan
    lt = float(np.mean(rt - 0.22 < design["T"][kept])) if rt.size else np.nan
    return om, acc, mean_rt, lt


# ---------------- A. 嵌套一致性（M-T3 数据） ----------------
rng = np.random.default_rng(7)
sim3 = simulate_subject(design, TRUTH_LIN, rng)
tr3 = trials_from_arrays(sim3["rt"], sim3["side"], sim3["omission"],
                         *design_arrays(design))
pt3 = per_trial_loglik(TRUTH_LIN, tr3)
pt1 = per_trial_loglik_step(TRUTH_LIN, tr3, 1.0)
ll3 = float(np.sum(pt3))
ll1 = log_likelihood_step(TRUTH_LIN, tr3, 1.0)
dmax = float(np.max(np.abs(pt1 - pt3)))
drel = float(np.max(np.abs(pt1 - pt3) / np.maximum(np.abs(pt3), 1e-300)))
print(f"\n[A] rho=1 嵌套一致性（单阶段数据）")
print(f"    ll_single      = {ll3:.6f}")
print(f"    ll_step(rho=1) = {ll1:.6f}   diff = {ll1 - ll3:+.3e}")
print(f"    max|Δ log 密度| = {dmax:.3e}   max 相对 = {drel:.3e}")
print(f"    A_VERDICT = {'PASS' if drel < 1e-6 else 'FAIL'}")

# ---------------- B. Euler 生成器标定 ----------------
print(f"\n[B] Euler 生成器标定（rho=1 必须复现解析单阶段）")
print(f"    {'source':<26}{'omission':>10}{'accuracy':>10}{'meanRT(ms)':>12}{'P(RT<T)':>9}")
# 解析单阶段，多次重复取均值以压低抽样噪声
accs, oms, rts = [], [], []
for rep in range(4):
    s = simulate_subject(design, TRUTH_LIN, np.random.default_rng(100 + rep))
    o, ac, rt, _ = behaviour(s, design)
    oms.append(o); accs.append(ac); rts.append(rt)
print(f"    {'analytic single-phase':<26}{np.mean(oms):>10.4f}{np.mean(accs):>10.4f}"
      f"{np.mean(rts):>12.2f}{'-':>9}")
for rep in range(4):
    s = simulate_euler_subject(design, TRUTH_LIN, 1.0,
                               np.random.default_rng(100 + rep))
    o, ac, rt, lt = behaviour(s, design)
    oms.append(o); accs.append(ac); rts.append(rt)
print(f"    {'Euler rho=1':<26}{np.mean(oms[-4:]):>10.4f}"
      f"{np.mean(accs[-4:]):>10.4f}{np.mean(rts[-4:]):>12.2f}{'-':>9}")
d_om = abs(np.mean(oms[-4:]) - np.mean(oms[:4]))
d_ac = abs(np.mean(accs[-4:]) - np.mean(accs[:4]))
d_rt = abs(np.mean(rts[-4:]) - np.mean(rts[:4]))
print(f"    |Δ| vs analytic: omission {d_om:.4f}  accuracy {d_ac:.4f}  RT {d_rt:.1f} ms")
print(f"    B_VERDICT = {'PASS' if (d_om < 0.02 and d_ac < 0.02 and d_rt < 15) else 'FAIL'}")

# ---------------- C. rho 扫描的行为量 ----------------
print(f"\n[C] rho 扫描（Euler 生成，每档 4 次重复的均值）")
print(f"    {'rho':>6}{'omission':>10}{'accuracy':>10}{'meanRT(ms)':>12}{'P(RT<T)':>9}")
for rho in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
    rows = [behaviour(simulate_euler_subject(design, TRUTH_LIN, rho,
                                             np.random.default_rng(200 + r)),
                      design) for r in range(4)]
    a = np.array(rows)
    print(f"    {rho:>6.2f}{a[:, 0].mean():>10.4f}{a[:, 1].mean():>10.4f}"
          f"{a[:, 2].mean():>12.2f}{a[:, 3].mean():>9.4f}")

# ---------------- D. 计时 ----------------
t0 = time.perf_counter()
_ = log_likelihood_step(TRUTH_LIN, tr3, 1.0)
dt1 = time.perf_counter() - t0
t0 = time.perf_counter()
_ = log_likelihood(TRUTH_LIN, tr3)
dt3 = time.perf_counter() - t0
t0 = time.perf_counter()
_ = simulate_euler_subject(design, TRUTH_LIN, 1.0, np.random.default_rng(1))
dtg = time.perf_counter() - t0
print(f"\n[D] 计时：一次 M-T1 似然 {dt1 * 1000:.1f} ms   "
      f"一次 M-T3 似然 {dt3 * 1000:.2f} ms   Euler 生成一名被试 {dtg:.2f} s")

# ---------------- E. rho 方向上的有限差分 ----------------
print(f"\n[E] ll 对 rho 的有限差分（其余参数固定在真值）")
for h in (0.02, 0.05, 0.10):
    lp = log_likelihood_step(TRUTH_LIN, tr3, 1.0 + h)
    lm = log_likelihood_step(TRUTH_LIN, tr3, 1.0 - h)
    l0 = log_likelihood_step(TRUTH_LIN, tr3, 1.0)
    curv = (lp - 2 * l0 + lm) / (h * h)
    print(f"    h={h:.2f}  ll+={lp:.4f}  ll0={l0:.4f}  ll-={lm:.4f}  "
          f"dll/drho={(lp - lm) / (2 * h):+.4f}  d2ll/drho2={curv:+.1f}")
