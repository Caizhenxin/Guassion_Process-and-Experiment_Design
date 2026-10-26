"""论文 9.5 用的组层参数表：M-T3 的组均值 + delta 法 SE；M-T1 只取 rho。

`hyper["theta"]` 是 (n_em, 2k) 的 EM 轨迹，最后一行为定稿；前 k 个是 μ
（x 空间组均值）、后 k 个是 log σ。`hyper["cov"]` 是 (2k, 2k) 的超参
Hessian 逆 ⇒ μ 的边际 SE = sqrt(diag(cov)[:k])。
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
import hier                                  # noqa: E402
from recover_group import WITHIN_FREE_LIN     # noqa: E402

P = REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "stage8_d123" / "stage8_results.json"
d = json.loads(P.read_text(encoding="utf-8"))
base = list(WITHIN_FREE_LIN)
print("自由参数：", base)

for gid in ("1", "2", "3", "4"):
    print(f"\n=== 组 {gid} ===")
    for mname in ("M-T1", "M-T3"):
        m = d["groups"][gid][mname]
        hy = m["hyper"]
        names = base + ([hier.RHO_NAME] if mname == "M-T1" else [])
        k = len(names)
        tr = np.asarray(hy["theta"], float)
        mu_x = tr[-1, :k]
        cov = np.asarray(hy["cov"], float)[:k, :k]
        sg = np.exp(tr[-1, k:2 * k])
        lo, hi = hier._bounds_with_rho(names)
        val = hier._from_x(mu_x, lo, hi)
        eps = 1e-6
        J = np.zeros((k, k))
        for j in range(k):
            tp, tm = mu_x.copy(), mu_x.copy()
            tp[j] += eps
            tm[j] -= eps
            J[:, j] = (hier._from_x(tp, lo, hi) - hier._from_x(tm, lo, hi)) / (2 * eps)
        sd = np.sqrt(np.clip(np.einsum("ij,jk,ik->i", J, cov, J), 0, None))
        loo = m["loo"]
        print(f"  [{mname}] n_flipped={m['fit']['n_flipped']} "
              f"ELPD={loo['elpd_loo']:.1f}±{loo['se']:.1f} "
              f"p_loo/n={loo['p_loo'] / loo['n_obs']:.5f} k_max={loo['k_max']:.3f}")
        for nm, v, s, g in zip(names, val, sd, sg):
            print(f"      {nm:<8s}{v:>10.4f} ± {s:>7.4f}   (σ={g:.3f})")
