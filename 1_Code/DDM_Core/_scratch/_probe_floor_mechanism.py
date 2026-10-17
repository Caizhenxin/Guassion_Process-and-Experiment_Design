# -*- coding: utf-8 -*-
"""验证「非正特征值 ⇒ cov 该方向 = 1/floor」的机制，并挑一个数值稳定的 maxiter。"""
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from hier import subject_map_laplace                                 # noqa: E402

lam1, lam2 = 10.0, -5.0


def ll_x(x):
    x = np.asarray(x, float)
    return -0.5 * (lam1 * x[0] ** 2 + lam2 * x[1] ** 2)


sub = {"ll_x": ll_x, "lo": np.array([-1.0, -1.0]), "hi": np.array([1.0, 1.0])}
big = float(np.log(1e9))
floor = max(1e-8 * lam1, 1e-12)
for mi in (2, 3, 5, 10):
    r = subject_map_laplace(sub, np.array([0.1, 0.1]), np.array([0.0, 0.0]),
                            np.array([big, big]), maxiter=mi)
    print(f"maxiter={mi:2d} n_flipped={r['n_flipped']} eig={np.round(r['eigval'], 4)} "
          f"cov11*floor={r['cov'][1, 1] * floor:.6f} mode={np.round(r['mode'], 3)} "
          f"logmarg={r['log_marginal']:.3e}")
