"""_trace_em.py —— 一次性：看 EM 前几轮到底发生了什么。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hier import hier_fit, make_subject  # noqa: E402

rng = np.random.default_rng(20261014)
n_sub, n_obs, sd_true = 40, 20, 0.5
ys = [rng.normal(0.3, sd_true, size=n_obs) for _ in range(n_sub)]
print("样本内 ȳ 的 SD =", round(float(np.std([y.mean() for y in ys])), 4))


def gauss_subject(y):
    y = np.asarray(y, float)
    n = y.size
    const = -0.5 * n * np.log(2 * np.pi)

    def ll_x(x):
        th = float(np.asarray(x).ravel()[0])
        return const - 0.5 * float(np.sum((y - th) ** 2))

    return make_subject(ll_x, [-100.0], [100.0], ["theta"])


subs = [gauss_subject(y) for y in ys]
fit = hier_fit(subs, n_em=8, tol=1e-9, verbose=True)
print("modes SD =", round(float(np.std(fit["modes"][:, 0])), 4),
      " 均值 =", round(float(np.mean(fit["modes"][:, 0])), 4))
print("平均后验方差 =", round(float(np.mean([c[0, 0] for c in fit["covs"]])), 5))
