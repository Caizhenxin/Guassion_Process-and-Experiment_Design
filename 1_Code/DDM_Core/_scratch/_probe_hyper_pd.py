# -*- coding: utf-8 -*-
"""探针：`_probe_loo_level.py` 那次「试次层 p_loo/n_obs = 0.138」的拟合，超参数 Hessian 是否正定？

动机（本轮的关键分叉）：试次层 LOO 在 2 人 × 93 试次的小配置上仍然越界（`p_loo/n_obs = 8.57`），
而该配置的 `hyper.eigval` 有 2 个负值、`theta` 逐维 SD 高达 134。若探针那次拟合的 Hessian 是正定的，
则结论应当是「**层不是充分条件，Hessian 正定才是**」，而不是「换试次层就可用」。

本探针只做「拟合 + hyper_draws」，不做 LOO 循环（省掉 ~25 min），只报：
  * `eigval` 的最小值 / 负特征值个数 / `n_flipped`；
  * `theta` 逐维 SD 与 |θ| 最大值（荒诞抽样的直接证据）。

用法：python -X utf8 -u _probe_hyper_pd.py [n_sub] [n_rep] [n_em] [S] [n_x]
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
import stage8_run as SR                                          # noqa: E402
from likelihood import MappingParams                             # noqa: E402

N_SUB = int(sys.argv[1]) if len(sys.argv) > 1 else 3
N_REP = int(sys.argv[2]) if len(sys.argv) > 2 else 1
N_EM = int(sys.argv[3]) if len(sys.argv) > 3 else 2
S = int(sys.argv[4]) if len(sys.argv) > 4 else 20
N_X = int(sys.argv[5]) if len(sys.argv) > 5 else 21
SEED = 7


def main() -> int:
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        SR._synthetic(N_SUB, SEED, 1, Path(td), n_rep=N_REP)
        people, rej = SR.collect([Path(td)], None, MappingParams(shape_model="lin"))
    assert not rej
    print(f"被试 {len(people)} 人；每人试次 {[p['n_trials'] for p in people]}")

    subs = SR._subjects(people, rho_free=True, n_x=N_X)
    t1 = time.time()
    fit = hier.hier_fit(subs, n_em=N_EM)
    print(f"层级拟合 {time.time() - t1:.1f}s；k = {fit['k']}")

    hyper = hier.hyper_draws(subs, fit, n_draws=S, seed=SEED, method="analytic")
    ev = np.asarray(hyper["eigval"], float)
    th = np.atleast_2d(hyper["theta"])
    print(f"超参数 Hessian：min eig = {ev.min():.6f}、max eig = {ev.max():.3f}、"
          f"负特征值 {int((ev <= 0).sum())}/{ev.size}、n_flipped = {hyper['n_flipped']}")
    print(f"theta 逐维 SD：" + " ".join(f"{x:.3g}" for x in th.std(axis=0)))
    print(f"theta |θ| 最大 = {float(np.abs(th).max()):.3f}；总耗时 {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
