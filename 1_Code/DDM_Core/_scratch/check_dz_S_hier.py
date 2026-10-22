# -*- coding: utf-8 -*-
"""check_dz_S_hier.py —— Δz_S 在**层级（hier_fit）**路径上是否可用
================================================================================
前面的 `check_dz_S.py` / `check_dz_S_ident.py` / `check_dz_S_power.py` 都走
**逐被试 MLE**（`likelihood.fit_mle`）。但论文主分析走的是 `hier.hier_fit`
（拉普拉斯-EM 层级模型，D100 之后是组层推断的唯一入口）。因此必须确认：

1. `ddm_subject(..., names=WITHIN_FREE_LIN)` 能接受多了 `dz_S` 的 8 维参数；
2. `hier_fit` 能在 `dz_S` 上给出 `mu`/`sigma`（即 `dz_S` 进了 `sigma` 的随机效应）；
3. 不做任何开关时，`free=WITHIN_FREE_LIN` 与 `free=WITHIN_FREE_LIN[:-1]` 都跑得通，
   且**去掉 dz_S 的那次与旧口径一致**（后者是回归保护）。

规模刻意压到最小（3 名被试、`n_em=2`）：这是**通路检查**，不是结果。
真实规模见 `stage8_run.py`（8 人 quick 已实测 3.2 h）。

运行：``python -X utf8 1_Code/DDM_Core/_scratch/check_dz_S_hier.py``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))

import mapping as M  # noqa: E402
from hier import ddm_subject, hier_fit  # noqa: E402
from simulate import (SUBJECT_SD, build_design, draw_subject_params,  # noqa: E402
                      simulate_subject)

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP, N_SUBJ = 12, 3
BASE = dict(P_ref=120.0, T_ref=0.10, W_ref=1.20, shape_model="lin",
            d_ref=0.70, beta_P=0.31, tau_P=30.0, beta_T=1.10, beta_ST=0.10,
            w_model="W1", a_ref=2.00, delta_a=0.24, t0=0.22, z_ratio=0.50)
TRUTH = M.MappingParams(**BASE, beta_S=0.19, dz_S=0.085)
INIT = M.MappingParams(**BASE, beta_S=0.0, dz_S=0.0).replace(
    d_ref=0.60, beta_T=1.40, a_ref=1.90, delta_a=0.20, t0=0.23)

design = build_design(120.0, T_LEVELS, W_LEVELS, N_REP)
trials, truths, t0_bounds = [], [], []
for s in range(N_SUBJ):
    rng = np.random.default_rng(4242 + 31 * s)
    p_sub = draw_subject_params(TRUTH, rng, mode="clip")
    sim = simulate_subject(design, p_sub, rng)
    tr = {**design, **{k: sim[k] for k in ("rt", "side", "omission")}}
    trials.append(tr)
    truths.append(p_sub)
    # ⚠️ 与 `stage8_run._load_people` 同口径：t0 上界必须小于最小 RT，
    # 否则 hier 的众数搜索会把 t0 推过 min(rt) ⇒ 似然 −inf ⇒ ∂²g 全非有限
    # （第一版漏了这一步，报 "64/64 个元素非有限、n_nonfinite_g=334"）。
    t0_bounds.append((M.PARAM_BOUNDS["t0"][0],
                      float(np.nanmin(tr["rt"])) - 1e-3))

print("=" * 88)
print(f"层级路径检查：{N_SUBJ} 名被试 × {len(design['T'])} 试次，n_em=2（通路检查，非结果）")
print("=" * 88)

for tag, names in (("含 dz_S（8 维）", list(M.WITHIN_FREE_LIN)),
                   ("不含 dz_S（7 维，旧口径）", list(M.WITHIN_FREE_LIN[:-1]))):
    subs = [ddm_subject(tr, INIT, names, bounds_override={"t0": tb})
            for tr, tb in zip(trials, t0_bounds)]
    t0_ = time.time()
    fit = hier_fit(subs, n_em=2, verbose=False)
    mu, sg = np.asarray(fit["mu"]), np.asarray(fit["sigma"])
    print(f"\n{tag}：耗时 {time.time()-t0_:.1f}s  维数 k={len(names)}  "
          f"n_flipped={fit['n_flipped']} n_fallback={fit['n_fallback']} "
          f"n_nonfinite_g={fit['n_nonfinite_g']}")
    print(f"  log_marginal = {float(np.sum(fit['log_marginal'])):.3f}"
          f"（逐被试 {np.round(np.asarray(fit['log_marginal'], float), 2)}）")
    for i, nm in enumerate(names):
        tvals = np.array([getattr(p, nm) for p in truths])
        print(f"  {nm:>9s}: mu={mu[i]:+.4f}  sigma={sg[i]:.4f}  "
              f"（真值均值 {tvals.mean():+.4f} ± SD {tvals.std(ddof=1):.4f}）")

# 逐被试众数里 dz_S 是否真的被移动（若恒等于起点 0，说明该维被冻住）
names = list(M.WITHIN_FREE_LIN)
subs = [ddm_subject(tr, INIT, names, bounds_override={"t0": tb})
        for tr, tb in zip(trials, t0_bounds)]
fit = hier_fit(subs, n_em=2, verbose=False)
i = names.index("dz_S")
print("\n  逐被试 dz_S 众数：", [f"{float(np.asarray(m).ravel()[i]):+.4f}" for m in fit["modes"]],
      "（真值：", [f"{p.dz_S:+.4f}" for p in truths], "）")

print("\n" + "=" * 88)
print("判据：① 两次都跑通、无异常；② 含 dz_S 时 k=8 且 dz_S 的 mu/sigma 都是有限数；")
print("      ③ 众数里的 dz_S 不等于起点 0（否则该维没被激活）。")
print("=" * 88)
