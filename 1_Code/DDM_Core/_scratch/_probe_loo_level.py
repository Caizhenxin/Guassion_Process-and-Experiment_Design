# -*- coding: utf-8 -*-
"""探针：同一批超参数抽取下，**被试层** PSIS-LOO 与**试次层** PSIS-LOO 的差别。

动机（D65/D70 的异常）：被试层 `elpd_loo = -1643 ± 588`、`p_loo = 1489`、`k_max` 撞到 5，
`_s8run_an` 里甚至出现**负 p_loo**（-706 / -2900）。负 p_loo 只能来自 PSIS 权重病态。

机理假设：`loo_matrix` 的每一列是「给定一组超参数的**profile 边际似然**」，而超参数后验的
拉普拉斯抽样在尾部会给出荒诞的 σ ⇒ 该列的边际似然跌到 -1e9 量级 ⇒ 整列被一个抽样支配
⇒ PSIS 的 k 直接撞到 5。试次层则把同样的信息摊到 n_trials 个 O(1) 的贡献上，离散度被摊薄。

本探针在**完全相同的抽取**上同时算两层，输出两套 p_loo / k_max，用来判断：
  * 若试次层 k_max < 0.7 而 p_loo 合理 ⇒ 「被试层 LOO 不可估」是**口径问题**，
    正式数据应把 PSIS-LOO 放在试次层，被试层留一另用 bruteforce / K-fold；
  * 若两层都崩 ⇒ 是超参数抽样本身（尾部荒诞）的问题，必须先截断抽样。

用法：python -X utf8 -u _probe_loo_level.py [n_sub] [n_rep] [n_em] [S] [n_x]
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hier                                                      # noqa: E402
import loo                                                       # noqa: E402
import stage8_run as SR                                          # noqa: E402
import twophase                                                  # noqa: E402
from likelihood import MappingParams                             # noqa: E402

N_SUB = int(sys.argv[1]) if len(sys.argv) > 1 else 3
N_REP = int(sys.argv[2]) if len(sys.argv) > 2 else 1
N_EM = int(sys.argv[3]) if len(sys.argv) > 3 else 2
S = int(sys.argv[4]) if len(sys.argv) > 4 else 30
N_X = int(sys.argv[5]) if len(sys.argv) > 5 else 25
SEED = 7


def main() -> int:
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        SR._synthetic(N_SUB, SEED, 1, Path(td), n_rep=N_REP)
        people, rej = SR.collect([Path(td)], None, MappingParams(shape_model="lin"))
    assert not rej
    print(f"被试 {len(people)} 人；每人试次 {[p['n_trials'] for p in people]}；"
          f"生成+收集 {time.time() - t0:.1f}s")

    subs = SR._subjects(people, rho_free=True, n_x=N_X)
    t1 = time.time()
    fit = hier.hier_fit(subs, n_em=N_EM)
    print(f"层级拟合 {time.time() - t1:.1f}s；k = {fit['k']}")

    hyper = hier.hyper_draws(subs, fit, n_draws=S, seed=SEED, method="analytic")
    th_all = np.atleast_2d(hyper["theta"])
    k = th_all.shape[1] // 2

    n_trials = [int(p["n_trials"]) for p in people]
    L_part = np.empty((th_all.shape[0], len(subs)))
    L_trial = np.full((th_all.shape[0], int(np.sum(n_trials))), np.nan)
    warm = [np.asarray(m, float).ravel() for m in fit["modes"]]
    n_fail = 0
    t2 = time.time()

    for s in range(th_all.shape[0]):
        mu, ls = th_all[s, :k], th_all[s, k:]
        off = 0
        for j, sub in enumerate(subs):
            try:
                r = hier.subject_map_laplace(sub, warm[j], mu, ls)
            except ValueError:
                L_part[s, j] = -np.inf
                n_fail += 1
                off += n_trials[j]
                continue
            L_part[s, j] = r["log_marginal"]
            nj = n_trials[j]
            # 同一众数处摊到试次：θ → 逐试次对数似然
            thv = hier._from_x(r["mode"], sub["lo"], sub["hi"])
            kn = len(sub["names"]) - 1
            p = sub["p_base"].with_vector(sub["names"][:kn], thv[:kn])
            pt = twophase.per_trial_loglik_step(p, sub["tr"], float(thv[kn]), n_x=N_X)
            if pt is not None:
                L_trial[s, off:off + nj] = pt
            off += nj
    print(f"抽取 {th_all.shape[0]} × 被试 {len(subs)}：{time.time() - t2:.1f}s，"
          f"失败（Hessian 非有限）{n_fail} 个 (draw, 被试)")

    res_p = loo.psis_loo(L_part)
    print("\n--- 被试层（当前 Stage 8 口径）---")
    print(f"  elpd_loo = {res_p['elpd_loo']:.3f} ± {res_p['se']:.3f}；"
          f"p_loo = {res_p['p_loo']:.3f}；n_obs = {res_p['n_obs']}")
    print(f"  k_max = {res_p['k_max']:.3f}；k>0.7 {res_p['n_k_gt_bad']}；"
          f"k>1 {res_p.get('n_k_gt_unusable', 0)}")

    Lt = np.where(np.isfinite(L_trial), L_trial, -np.inf)
    res_t = loo.psis_loo(Lt)
    print("\n--- 试次层（同一批抽取）---")
    print(f"  elpd_loo = {res_t['elpd_loo']:.3f} ± {res_t['se']:.3f}；"
          f"p_loo = {res_t['p_loo']:.3f}（p_loo/n_obs = "
          f"{res_t['p_loo'] / res_t['n_obs']:.3f}）；n_obs = {res_t['n_obs']}")
    print(f"  k_max = {res_t['k_max']:.3f}；k>0.7 {res_t['n_k_gt_bad']}；"
          f"k>1 {res_t.get('n_k_gt_unusable', 0)}；失败 {res_t.get('n_failed', 0)}")

    print("\n--- 离散度（解释为什么被试层会崩）---")
    print(f"  被试层 L：全距 {np.nanmax(L_part) - np.nanmin(L_part):.1f}、"
          f"逐列 SD 均值 {np.nanstd(L_part, axis=0).mean():.1f}")
    print(f"  试次层 L：全距 {np.nanmax(Lt) - np.nanmin(Lt):.1f}、"
          f"逐列 SD 均值 {np.nanstd(Lt, axis=0).mean():.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
