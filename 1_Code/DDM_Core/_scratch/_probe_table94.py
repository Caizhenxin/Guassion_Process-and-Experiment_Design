"""论文 9.4 / 9.5 用的最终读数表（一次跑完，避免反复读 JSON）。

输出：
  A. 四组 × 两模型：n_subjects / n_obs / ELPD±SE / p_loo/n / k_max /
     fit.n_flipped（被试级 Laplace）/ hyper.n_flipped（超参 Hessian）
  B. M-T3：组均值 ± SE（delta 法）、组间 log σ、被试级中位数
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

print("== A. 模型比较读数 ==")
hdr = ("组", "模型", "n_subj", "n_obs", "ELPD", "SE", "p_loo/n", "k_max",
       "fit.flip", "hyper.flip", "秒")
print("%-3s %-5s %6s %6s %10s %8s %9s %7s %8s %10s %7s" % hdr)
for gid in ("1", "2", "3", "4"):
    for mn in ("M-T1", "M-T3"):
        m = d["groups"][gid][mn]
        loo = m["loo"]
        print("%-3s %-5s %6d %6d %10.1f %8.1f %9.5f %7.3f %8d %10s %7.0f" % (
            gid, mn, loo["n_obs"] // 1 if False else m["n_subjects"], loo["n_obs"],
            loo["elpd_loo"], loo["se"], loo["p_loo"] / loo["n_obs"], loo["k_max"],
            m["fit"]["n_flipped"], m["hyper"].get("n_flipped"), m["seconds"]))

print("\n== B. M-T3 组层参数（delta 法 SE）==")
for gid in ("1", "2", "3", "4"):
    m = d["groups"][gid]["M-T3"]
    hy = m["hyper"]
    k = len(base)
    mu_x = np.asarray(hy["theta"], float)[-1, :k]
    cov = np.asarray(hy["cov"], float)[:k, :k]
    sg = np.exp(np.asarray(hy["theta"], float)[-1, k:2 * k])
    lo, hi = hier._bounds_with_rho(base)
    val = hier._from_x(mu_x, lo, hi)
    eps = 1e-6
    J = np.zeros((k, k))
    for j in range(k):
        tp, tm = mu_x.copy(), mu_x.copy()
        tp[j] += eps
        tm[j] -= eps
        J[:, j] = (hier._from_x(tp, lo, hi) - hier._from_x(tm, lo, hi)) / (2 * eps)
    sd = np.sqrt(np.clip(np.einsum("ij,jk,ik->i", J, cov, J), 0, None))
    sub = hier._from_x(np.asarray(m["fit"]["modes"], float), lo, hi)
    print(f"\n组 {gid}（n={m['n_subjects']}）：")
    for j, nm in enumerate(base):
        print("   %-8s 组均值 %8.4f ± %7.4f   logσ %6.3f   被试中位 %8.4f"
              % (nm, val[j], sd[j], np.log(sg[j]), np.median(sub[:, j])))
