"""诊断：GPD 形状参数 MLE 在「取前 M 个次序统计量」下的偏差。

背景
====
`check_loo.py` 的 B 组发现，对严格 Pareto(α) 的重要性比，拟合出的
`k̂` 系统性偏低（α=3 时 0.303 vs 期望 0.333，α=1.2 时 0.795 vs 0.833）。
本脚本回答：这偏低是**估计量本身**的性质，还是 `psis_one` 的调用方式造成的。

三个对照
--------
* `top_m_random_threshold`：模拟 `psis_one` 的做法——取 S 个 Pareto 样本里
  最大的 M 个，阈值 = 第 M+1 大的值（**数据依赖的随机阈值**）。
* `fixed_threshold`：阈值固定为真值 `t`（使超额数**期望**为 M），
  用全部超额点拟合（点数是随机的）——这是 GPD 的经典设定，理论上无偏。
* `top_m_true_threshold`：取最大的 M 个，但阈值固定为真值 `t`（不随样本变）。

若前者的偏差显著大于后两者 ⇒ 偏差来自"随机阈值 + 固定个数"这个选择机制，
而不是 MLE 本身。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loo import gpd_fit  # noqa: E402

S = 4000
M = int(min(S / 5.0, 3.0 * np.sqrt(S)))
N_REP = 2000


def study(alpha: float, rng) -> None:
    true_k = 1.0 / alpha
    # 阈值取真值：P(r > t) = t^{-alpha} = M / S  ⇒  t = (M/S)^{-1/alpha}
    t = (M / S) ** (-1.0 / alpha)
    out = {k: [] for k in ("top_m_random_threshold", "fixed_threshold", "top_m_true_threshold")}
    for _ in range(N_REP):
        u = rng.random(S)
        r = np.power(1.0 - u, -1.0 / alpha)

        # (1) 与 psis_one 相同：随机阈值
        rs = np.sort(r)[::-1]
        thr = rs[M]
        exc = rs[:M] - thr
        out["top_m_random_threshold"].append(gpd_fit(exc)[0])

        # (2) 固定阈值，用全部超额点
        exc2 = r[r > t] - t
        if exc2.size >= 5:
            out["fixed_threshold"].append(gpd_fit(exc2)[0])

        # (3) 取最大的 M 个，阈值固定为真值
        exc3 = rs[:M] - t
        exc3 = exc3[exc3 > 0]
        if exc3.size >= 5:
            out["top_m_true_threshold"].append(gpd_fit(exc3)[0])

    print("\nα = %.1f（真值 k = 1/α = %.4f），S = %d，M = %d，重复 %d 次"
          % (alpha, true_k, S, M, N_REP))
    for name, vals in out.items():
        v = np.asarray(vals)
        print("   %-26s 均值 = %.4f  中位 = %.4f  偏差 = %+.4f  经验 SE = %.4f  (n=%d)"
              % (name, v.mean(), np.median(v), v.mean() - true_k, v.std(ddof=1) / np.sqrt(v.size), v.size))


if __name__ == "__main__":
    rng = np.random.default_rng(20261014)
    for a in (3.0, 1.2):
        study(a, rng)
