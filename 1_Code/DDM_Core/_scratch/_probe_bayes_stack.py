# -*- coding: utf-8 -*-
"""D41 探针：用 `D:\\Conda\\envs\\hssm` 里的 ArviZ **独立复核** `1_Code/DDM_Core/loo.py` 的 PSIS-LOO。

只回答三个问题（不改仓库任何东西）：
  1. `az.loo` 能不能吃**我们自己造的** InferenceData（只需 `posterior` 一个占位组）？
  2. 在**同一份**逐点对数似然矩阵上，我们的 `psis_loo`（手写 PSIS + GPD 尾部）与 ArviZ 的
     `elpd_loo` / `p_loo` / `k_max` 差多少？—— 这一条**不需要 C 编译器**，也不需要 MCMC；
  3. `pm.sample` 在本机能不能跑（没有 g++ ⇒ Python 回退，慢但也许能出几十个 draws）？
"""
from __future__ import annotations

import sys
import time

import arviz as az
import numpy as np

sys.path.insert(0, "1_Code/DDM_Core")
import loo as our  # noqa: E402  （被测模块）

t0 = time.time()

# ---------------- 先在记录里钉死「这是哪个解释器、什么版本」 ----------------
import importlib.metadata as _md  # noqa: E402

print("解释器: %s（%s）" % (sys.version.split()[0], sys.executable))
for _mod in ("pymc", "pytensor", "arviz", "hssm", "numpy"):
    try:
        print("  %-9s %s" % (_mod, _md.version(_mod)))
    except Exception:  # noqa: BLE001
        print("  %-9s MISSING" % _mod)

# ---------------- 造一份「有真实后验形状」的逐点对数似然矩阵 ----------------
S, N = 2000, 40
y = np.random.default_rng(7).normal(0.30, 1.0, N)
mu = np.random.default_rng(8).normal(0.30, 0.15, S)         # 后验式抽样（不是点估计）
L = np.log(1.0 / np.sqrt(2 * np.pi)) - 0.5 * (y[None, :] - mu[:, None]) ** 2
L = L + np.random.default_rng(9).normal(0.0, 0.02, L.shape)  # 一点抖动，避免退化

mine = our.psis_loo(L)
print("[ours ] elpd_loo = %.6f  se = %.6f  p_loo = %.6f  k_max = %.4f  k>0.7: %d"
      % (mine["elpd_loo"], mine["se"], mine["p_loo"], mine["k_max"], mine["n_k_gt_bad"]))

# ---------------- 让 ArviZ 吃同一份矩阵（posterior 组只做占位：LOO 只用 log_likelihood） ----------------
idata = az.from_dict(
    posterior={"mu": mu[None, :]},                                   # (chain=1, draw=S)
    log_likelihood={"y": L[None, :, :]},                             # (1, S, N)
    observed_data={"y": y},
    coords={"obs_id": np.arange(N)},
    dims={"y": ["obs_id"]},
)
print("idata 组:", sorted(idata.groups()))
azl = az.loo(idata, pointwise=True)
k_az = np.asarray(azl.pareto_k.values).ravel()
print("[arviz] elpd_loo = %.6f  se = %.6f  p_loo = %.6f  k_max = %.4f  k>0.7: %d"
      % (float(azl.elpd_loo), float(azl.se), float(azl.p_loo), float(k_az.max()),
         int((k_az > 0.7).sum())))

d_elpd = float(azl.elpd_loo) - mine["elpd_loo"]
d_ploo = float(azl.p_loo) - mine["p_loo"]
print("差值（arviz − ours）：elpd_loo %+.6f（相对 %+.2e）、p_loo %+.6f、k_max %+.4f"
      % (d_elpd, d_elpd / abs(mine["elpd_loo"]), d_ploo, float(k_az.max()) - mine["k_max"]))
print("✓ 两套 PSIS 在同一矩阵上一致（容差 1e-3 相对）" if abs(d_elpd) < 1e-3 * abs(mine["elpd_loo"])
      else "✗ 两套 PSIS 在容差外不一致 —— 必须查（ArviZ 的尾部截断/平滑与本实现不同）")

# ---------------- MCMC 冒烟（Python 回退，只为确认整条栈能跑通） ----------------
try:
    import pymc as pm

    with pm.Model() as m:
        mm = pm.Normal("mu", 0, 1)
        pm.Normal("y", mu=mm, sigma=1.0, observed=y)
        tr = pm.sample(50, tune=50, chains=1, cores=1, progressbar=False,
                       random_seed=1, compute_convergence_checks=False, model=m)
    print("pm.sample 可用 ⇒ posterior mean(mu) = %.4f（真值 0.30）" % float(tr.posterior["mu"].mean()))
except Exception as exc:  # noqa: BLE001  （探针：失败也要说清原因）
    print("pm.sample 失败 ⇒", type(exc).__name__, ":", str(exc)[:200])

print("耗时 %.1fs" % (time.time() - t0))
