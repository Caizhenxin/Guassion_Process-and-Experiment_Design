# -*- coding: utf-8 -*-
"""探针：被试层 PSIS-LOO 的失效，是不是**超参数抽样数 S 太小**造成的？

背景（D65/D70 的观测）：3–4 名被试时 `p_loo / n_obs` 高达 496–704，`k_max` 撞到 5，
甚至出现**负的 p_loo**（`_s8run_an`：−706 / −2900）。负 p_loo 只可能来自 PSIS 权重病态，
不是"模型过拟合"。

本探针固定**同一批被试、同一次拟合**，只把 `n_draws`（= 喂给 `psis_loo` 的 S）
从 30 提到 480，看三件事：
  1. `p_loo` 是否从"几百"降到 O(k)（k = 被试层自由参数个数）；
  2. `k_max` 是否从 5 降下来；
  3. `p_loo` 是否稳定为正。

判读：若 S=480 时 p_loo 仍 ≫ k、k_max 仍 > 1 ⇒ 不是抽样数问题，而是
「profile 边际似然在超参数抽取间离散度过大」这一结构问题（⇒ 正式数据应换
按被试 K-fold / bruteforce）。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hier                                                     # noqa: E402
import loo                                                      # noqa: E402
import stage8_run as SR                                         # noqa: E402
from likelihood import MappingParams                            # noqa: E402

N_SUB = int(sys.argv[1]) if len(sys.argv) > 1 else 3
N_REP = int(sys.argv[2]) if len(sys.argv) > 2 else 2
N_EM = int(sys.argv[3]) if len(sys.argv) > 3 else 2
DRAWS = [int(x) for x in (sys.argv[4].split(",") if len(sys.argv) > 4 else ["30", "120", "480"])]
SEED = 7


def main() -> int:
    import tempfile
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        SR._synthetic(N_SUB, SEED, 1, Path(td), n_rep=N_REP)
        people, rej = SR.collect([Path(td)], None, MappingParams(shape_model="lin"))
    assert not rej
    n_trials = [int(p["n_trials"]) for p in people]
    print(f"被试 {len(people)} 人；每人试次 {n_trials}；数据生成+收集 {time.time() - t0:.1f}s")

    subs = SR._subjects(people, rho_free=True, n_x=25)
    t1 = time.time()
    fit = hier.hier_fit(subs, n_em=N_EM)
    print(f"层级拟合 {time.time() - t1:.1f}s；k（被试层参数个数）= {fit['k']}")

    for S in DRAWS:
        t2 = time.time()
        hyper = hier.hyper_draws(subs, fit, n_draws=S, seed=SEED, method="analytic")
        stats: dict = {}
        L = hier.loo_matrix(subs, hyper, mode_warm=fit["modes"], stats=stats)
        res = loo.psis_loo(L)
        dt = time.time() - t2
        print(f"\nS = {S:4d}（用时 {dt:.1f}s；LOO 阶段众数搜索 {stats['n_searches']} 次、"
              f"退回初值 {stats['n_fallback']}、目标非有限 {stats['n_nonfinite_g']}）")
        print(f"  elpd_loo = {res['elpd_loo']:.3f} ± {res['se']:.3f}")
        print(f"  p_loo    = {res['p_loo']:.3f}（p_loo/n_obs = {res['p_loo'] / res['n_obs']:.2f}，"
              f"p_loo/k = {res['p_loo'] / max(fit['k'], 1):.2f}）")
        print(f"  k_max    = {res['k_max']:.3f}；n_obs = {res['n_obs']}；"
              f"k>0.7 {res['n_k_gt_bad']}；k>1 {res.get('n_k_gt_unusable', 0)}")
        lspread = float(np.max(L) - np.min(L))
        lsd = float(np.std(L, axis=0).mean())
        print(f"  L 的离散度：全距 {lspread:.1f}、逐列 SD 均值 {lsd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
