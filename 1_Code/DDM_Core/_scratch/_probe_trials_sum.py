# -*- coding: utf-8 -*-
"""D73 探针：`hier.loo_matrix_trials` 的正确性（逐试次之和 == 整人似然）。

1. 形状 = ``(S, Σ n_s)``；
2. 同一众数处 `ll_trials_x(mode)` 之和 == `log_likelihood_step`（相对误差 < 1e-10）；
3. `n_trial_ll_fail` / `n_hessian_fail` 在健康输入上为 0；
4. `make_subject` 构造的解析对象调用它会**报错**（不静默降级）。

用法：python -X utf8 -u _probe_trials_sum.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hier                                                      # noqa: E402
import stage8_run as SR                                          # noqa: E402
from likelihood import MappingParams, _from_x                    # noqa: E402
from twophase import log_likelihood_step                          # noqa: E402

N_SUB, N_REP, N_X, S = 2, 1, 11, 2


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        SR._synthetic(N_SUB, 7, 1, Path(td), n_rep=N_REP)
        people, rej = SR.collect([Path(td)], None, MappingParams(shape_model="lin"))
        assert not rej, rej
    n_trials = [int(p["n_trials"]) for p in people]
    print(f"被试 {len(people)}；每人试次 {n_trials}；合计 {sum(n_trials)}")

    subs = SR._subjects(people, rho_free=True, n_x=N_X)
    fit = hier.hier_fit(subs, n_em=1)
    hyper = hier.hyper_draws(subs, fit, n_draws=S, seed=7, method="analytic")

    st: dict = {}
    Lt = hier.loo_matrix_trials(subs, hyper, mode_warm=fit["modes"], stats=st)
    print(f"矩阵形状 {Lt.shape}（期望 ({S}, {sum(n_trials)})）；stats = {st}")
    assert Lt.shape == (S, sum(n_trials)), Lt.shape
    assert st["n_hessian_fail"] == 0 and st["n_trial_ll_fail"] == 0, st

    # 逐 (抽取, 被试) 复核：和 == 整人似然。
    # ⚠️ 必须**复刻热启动链**：`loo_matrix_trials` 让 warm[j] 随抽取滚动更新，
    #    若这里每次都从 `fit["modes"][j]` 冷启动，落在不同的众数上，
    #    比较的就是"两个不同的点"（首版 probe 正是踩了这个坑，相对误差 2.6）。
    th_all = np.atleast_2d(hyper["theta"])
    k = th_all.shape[1] // 2
    warm = [np.asarray(m, float).ravel() for m in fit["modes"]]
    worst = 0.0
    for s in range(S):
        mu, ls = th_all[s, :k], th_all[s, k:]
        off = 0
        for j, sub in enumerate(subs):
            nj = n_trials[j]
            r = hier.subject_map_laplace(sub, warm[j], mu, ls)
            warm[j] = r["mode"]
            thv = _from_x(r["mode"], sub["lo"], sub["hi"])
            kn = len(sub["names"]) - 1
            p = sub["p_base"].with_vector(sub["names"][:kn], thv[:kn])
            tot = log_likelihood_step(p, sub["tr"], float(thv[kn]), n_x=N_X)
            d = abs(float(np.sum(Lt[s, off:off + nj])) - float(tot))
            worst = max(worst, d / max(1.0, abs(float(tot))))
            off += nj
    print(f"逐试次之和 vs 整人似然：最大相对误差 {worst:.3e}")
    assert worst < 1e-10, worst

    # 解析基准对象必须报错
    sub0 = hier.make_subject(lambda x: -0.5 * float(np.sum(np.asarray(x) ** 2)),
                             np.array([-3.0, -3.0]), np.array([3.0, 3.0]),
                             ["mu", "logsigma"])
    try:
        hier.loo_matrix_trials([sub0, sub0], hyper)
    except ValueError as e:
        print(f"解析对象报错 ✅ {e}")
    else:
        raise AssertionError("make_subject 对象竟然被接受了")

    print("\n✅ 4/4 通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
