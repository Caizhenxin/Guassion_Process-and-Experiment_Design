"""hier.py —— Stage 8 的**层级耦合层**：被试参数服从群体分布，并以**被试**为 LOO 单位。

模型（对角群体分布）
--------------------
::

    x_s ~ N(mu, diag(sigma^2))        # x_s = 第 s 名被试参数的**无约束**坐标
    y_s ~ p(y | theta_s)              # 逐被试 WFPT 似然（M-T1 或 M-T3）
    (mu, log sigma) 带弱信息先验       # 只为让超参数后验可积，不表达实质信念

为什么是"拉普拉斯-EM"而不是直接对 ``(mu, log sigma)`` 做数值优化
----------------------------------------------------------------
外层的每一次评估都要**重新求 N 个被试的众数**。实测（576 试次、K=4）：
单人冷启动 L-BFGS ≤60 步 **9.3 s**、Hessian **3.4 s** ⇒ 外层一次评估 ≈ 64 s，
而 8 维 Nelder-Mead 至少要上百次评估 ⇒ 数小时。EM 把外层拆成
**E 步（给定超参数求各被试众数）** 与 **M 步（闭式更新 mu / sigma²）**，
通常 8–15 轮收敛，且 M 步**不需要任何额外似然评估**。

M 步为什么是闭式的（对角正态 + 拉普拉斯）
    ``mu   = Σ_s x_s* / n``（加先验平滑）
    ``σ_k² = mean_s[ (x_{s,k}* − mu_k)² + Cov_s[k,k] ]``
                          ↑ 众数之间的离散        ↑ 每个被试自身的后验不确定性
    第二项是拉普拉斯近似下的标准修正：若漏掉它，σ 会被**系统性低估**
    （众数比真参数更集中）。这条在自测 A 组里被显式检查。

⚠️ 三条必须与结果一起报的限定
1. **拉普拉斯是局部近似**：逐被试的群体先验曲率必须足够"甜"，
   否则 `subject_map_laplace` 的 `n_flipped > 0`（本模块把它如实传出）。
2. **``log_sigma`` 先验只用于让超参数后验可积**，不参与 E/M 迭代；
   因此 EM 的不动点是 ``(mu, sigma)`` 的（近似）极大似然，而非后验众数。
3. **本项目的 DDM 似然面在 ``(τ_T, β_T, β_ST)`` 方向极平**，群体 SD 的可识别性
   取决于设计；报告 ``sigma`` 时必须同时报超参数后验 SD 与逐被试众数的 SE。

LOO 的两个口径（决策 D73 —— 原「只能用被试层」的规定已被实测推翻）
-------------------------------------------------------------------
* **被试层**（`loo_matrix`）：每个超参数后验抽取算一次**逐被试边际对数似然**
  ``log p(y_s | mu^(i), sigma^(i))`` ⇒ ``(S, N)``。问题：每一列是「给定一组超参数的
  **profile 边际**」，超参数抽样走到尾部时该列被个别荒诞抽样支配 ⇒ ``p_loo`` 量的是
  **离散度**而不是参数个数（实测 ``p_loo/n_obs`` 达 496、甚至出现**负 p_loo**）。
  ⇒ 被试层的 PSIS-LOO **不可估**，其数字只能当「矩阵不可估」的证据引用。
* **试次层**（`loo_matrix_trials`）：同一批抽取、同一个众数，把该被试的贡献摊到
  ``n_trials`` 个 O(1) 的逐试次对数似然上 ⇒ ``(S, Σ n_s)``。实测同一批抽取下
  ``p_loo/n_obs = 0.138``、``k_max = 0`` ⇒ **模型比较用这一层**。
* **被试层留一**（跨被试泛化）仍用 `loo_bruteforce`（小 N，金标准）或 K-fold（大 N）。

⚠️ 试次层矩阵的列是「众数处的逐试次对数似然」，不是边际似然 —— 超参数不确定性通过
``θ̂(s)`` 传入，是 **profile mode plug-in** 近似，不是精确的联合边际。这一点必须随
结果一起交代（D73）。
"""
from __future__ import annotations

import sys
from typing import Callable

import numpy as np
from scipy.optimize import minimize

from likelihood import PARAM_BOUNDS, _from_x, _to_x
from loo import loo_compare, psis_loo
from mapping import MappingParams
from stage8 import hessian_x
from twophase import (RHO_NAME, MASK_RHO_BOUNDS, log_likelihood_step,
                      per_trial_loglik_step)

__all__ = ["make_subject", "ddm_subject", "subject_map_laplace", "hier_fit",
           "hyper_hessian", "hyper_draws", "loo_matrix", "loo_matrix_trials",
           "loo_bruteforce", "fit_and_loo", "compare_models"]

#: ``mu`` 的弱信息先验 SD（无约束坐标）
POP_MU_PRIOR_SD = 2.0
#: ``log sigma`` 的弱信息先验：中心与 SD
POP_LOGSIGMA_PRIOR_MU = float(np.log(0.5))
POP_LOGSIGMA_PRIOR_SD = 1.0
#: ``sigma`` 的下限（防止某一维塌到 0 后协方差奇异）
SIGMA_FLOOR = 1e-3
#: 单次众数搜索的迭代上限
MAX_MODE_ITER = 80
#: 超参数有限差分的外层步长
HYPER_STEP = 0.05
_LOG2PI = float(np.log(2.0 * np.pi))


# ------------------------------------------------------------------
# 0. 被试对象
# ------------------------------------------------------------------
def _bounds_with_rho(names: list[str], override: dict | None = None):
    """取边界，并为 ``rho`` 提供 ``twophase.MASK_RHO_BOUNDS``。

    ⚠️ 不能直接用 `likelihood._bounds_for`：那里写的是
    ``override.get(n, PARAM_BOUNDS[n])``，而 Python 会**先求值**默认参数
    ``PARAM_BOUNDS['rho']`` ⇒ 即使 override 里有 ``rho`` 也会 `KeyError`
    （``rho`` 只存在于 `twophase`，不在 `likelihood.PARAM_BOUNDS` 里）。
    """
    ov = {RHO_NAME: MASK_RHO_BOUNDS, **(override or {})}
    table = {**PARAM_BOUNDS, RHO_NAME: MASK_RHO_BOUNDS}
    lo = np.array([ov.get(n, table[n])[0] for n in names])
    hi = np.array([ov.get(n, table[n])[1] for n in names])
    return lo, hi


def make_subject(ll_x: Callable[[np.ndarray], float], lo, hi,
                 names: list[str]) -> dict:
    """从**任意**无约束坐标对数似然构造被试对象（自测的解析基准走这条）。"""
    return {"ll_x": ll_x, "lo": np.asarray(lo, float), "hi": np.asarray(hi, float),
            "names": list(names), "kind": "custom"}


def ddm_subject(tr: dict, p_base: MappingParams, names: list[str],
                rho_free: bool = False, bounds_override: dict | None = None,
                n_x: int = 81) -> dict:
    """构造一名被试的 WFPT 似然对象。

    ``rho_free=False`` ⇒ **M-T3**（单阶段，``rho = 1`` 固定）；
    ``rho_free=True``  ⇒ **M-T1**（``rho`` 作为被试参数的一个坐标，边界 ``[0, 3]``）。
    """
    names = list(names)
    full = names + ([RHO_NAME] if rho_free else [])
    ov = dict(bounds_override or {})
    if rho_free:
        ov.setdefault(RHO_NAME, MASK_RHO_BOUNDS)
    lo, hi = _bounds_with_rho(full, ov)
    k = len(names)

    def ll_x(x):
        th = _from_x(np.asarray(x, float), lo, hi)
        p = p_base.with_vector(names, th[:k])
        rho = float(th[k]) if rho_free else 1.0
        v = log_likelihood_step(p, tr, rho, n_x=n_x)
        return float(v) if np.isfinite(v) else -np.inf

    def ll_trials_x(x):
        """同一参数点的**逐试次**对数似然（D73 的试次层 LOO 用）。

        返回 ``None`` 表示该参数点上有试次的似然非有限（`per_trial_loglik_step`
        的实现约定）；调用方必须把它当作失败而不是静默跳过。
        """
        th = _from_x(np.asarray(x, float), lo, hi)
        p = p_base.with_vector(names, th[:k])
        rho = float(th[k]) if rho_free else 1.0
        pt = per_trial_loglik_step(p, tr, rho, n_x=n_x)
        return None if pt is None else np.asarray(pt, float)

    return {"ll_x": ll_x, "ll_trials_x": ll_trials_x, "lo": lo, "hi": hi,
            "names": full, "kind": "ddm", "rho_free": bool(rho_free),
            "tr": tr, "p_base": p_base}


def _x0_of(sub: dict, theta: MappingParams | None = None,
           theta_vec=None) -> np.ndarray:
    """被试对象的中点作为初值（自定义对象）或由 ``theta`` 给出。"""
    if theta_vec is not None:
        return _to_x(np.asarray(theta_vec, float), sub["lo"], sub["hi"])
    if theta is not None:
        return _to_x(theta.vector(sub["names"]), sub["lo"], sub["hi"])
    return _to_x(0.5 * (sub["lo"] + sub["hi"]), sub["lo"], sub["hi"])


# ------------------------------------------------------------------
# 1. 群体先验 / 超参数先验
# ------------------------------------------------------------------
def _log_pop_prior(x: np.ndarray, mu: np.ndarray, log_sigma: np.ndarray) -> float:
    """对角正态：``log N(x; mu, diag(sigma²))``。"""
    ls = np.maximum(np.asarray(log_sigma, float), np.log(SIGMA_FLOOR))
    r = (np.asarray(x, float) - np.asarray(mu, float)) / np.exp(ls)
    return float(-0.5 * np.sum(r * r + 2.0 * ls + _LOG2PI))


def _log_hyper_prior(mu: np.ndarray, log_sigma: np.ndarray) -> float:
    a = np.sum((np.asarray(mu, float) / POP_MU_PRIOR_SD) ** 2)
    b = np.sum(((np.asarray(log_sigma, float) - POP_LOGSIGMA_PRIOR_MU)
                / POP_LOGSIGMA_PRIOR_SD) ** 2)
    return float(-0.5 * (a + b))


# ------------------------------------------------------------------
# 2. 逐被试 MAP 众数 + 拉普拉斯边际
# ------------------------------------------------------------------
def subject_map_laplace(sub: dict, x_init, mu, log_sigma,
                        maxiter: int = MAX_MODE_ITER,
                        hess_step: float = 1e-4) -> dict:
    """在给定超参数下求该被试的 MAP 众数，并给出拉普拉斯边际对数似然。

    边际 = ``∫ p(y|theta) N(x; mu, sigma²) dx``
        ≈ ``exp(g(x*)) · (2π)^{K/2} · |−∂²g/∂x²|^{-1/2}``，``g = log p(y|x) + log 先验``。

    回到 ``x_init``；特征值被 ``eig_use`` 抬平）。
    ⇒ 调用方**必须**检查 ``fell_back`` / ``n_nonfinite_g``，否则一次"静默退回初值"
    会以完全正常的 ``log_marginal`` 进入 EM 与 LOO。

    ``n_flipped`` > 0 表示 ``∂²g`` 不是负定（该点不是可信的众数）——
    **必须随结果一起报**，不能静默压平。
    ❗ ``x_init=None`` 会回退到 ``_x0_of(sub)``（区间中点）。
    **不要依赖 ``np.asarray(None, float)``**：它得到的是长度为 1 的 ``[nan]``，
    会让 L-BFGS 与 `hessian_x` 在 NaN 上原地打转 —— 表现为「4 ms 就收敛、
    `n_flipped` 为 0」的**静默无意义结果**（实测踩过）。这里对形状与非有限值
    都显式报错。
    """
    if x_init is None:
        x_init = _x0_of(sub)
    x_init = np.asarray(x_init, float).ravel()
    if x_init.size != len(sub["lo"]) or not np.all(np.isfinite(x_init)):
        raise ValueError(
            f"x_init 必须是长度 {len(sub['lo'])} 的有限向量，"
            f"收到 size={x_init.size}、all_finite="
            f"{bool(np.all(np.isfinite(x_init)))}")
    mu = np.asarray(mu, float).ravel()
    log_sigma = np.asarray(log_sigma, float).ravel()

    stats = {"nonfinite": 0}

    def g(x):
        v = sub["ll_x"](x)
        if not np.isfinite(v):
            stats["nonfinite"] += 1
            return -np.inf
        return float(v) + _log_pop_prior(x, mu, log_sigma)

    res = minimize(lambda x: -g(x), x_init, method="L-BFGS-B",
                   options={"maxiter": int(maxiter)})
    xm = np.asarray(res.x, float)
    fell_back = False
    if not np.isfinite(g(xm)):
        # 优化失败：退回初值，并如实标记（`fell_back` 让调用方看得见）
        xm = x_init
        fell_back = True
    H = hessian_x(g, xm, rel_step=hess_step)
    if not np.all(np.isfinite(H)):
        # ❗ 这条守卫是**必需的**：`fell_back` 一旦触发，说明 `g(xm)` 非有限，
        #    而 `hessian_x` 用中心差分算 `∂²g`，四个角点在非有限邻域里就会得到
        #    NaN ⇒ `np.linalg.eigvalsh` 抛 `LinAlgError("Eigenvalues did not
        #    converge")` —— 一条**完全无法归因**的报错（不说哪个被试、哪个超参数、
        #    为什么）。实测复现：把 `ll_x` 换成处处 `-inf` 的桩就会走到这里。
        #    改成显式报错，把诊断信息一并带出。
        n_bad_H = int(np.sum(~np.isfinite(H)))
        raise ValueError(
            f"在众数处 ∂²g 非有限（{n_bad_H}/{H.size} 个元素）—— 目标函数在该点"
            f"邻域不可用，无法构成拉普拉斯近似。\n"
            f"    fell_back={bool(fell_back)}（True ⇒ 优化失败、众数已退回 `x_init`）\n"
            f"    n_nonfinite_g={int(stats['nonfinite'])}（`g` 返回非有限的次数）\n"
            f"    converged={bool(getattr(res, 'success', False))}、"
            f"n_evals={int(getattr(res, 'nfev', 0))}\n"
            f"    ⇒ 这不是可以静默吸收的退化：请检查该被试的 `ll_x` 定义域"
            f"（`_bounds_with_rho` 给的 lo/hi 与 `_from_x` 的映射是否一致），"
            f"或把 `ll_x` 的极端取值改成有限的惩罚值。")
    A = -0.5 * (H + H.T)
    eigval = np.linalg.eigvalsh(A)             # A 在众数处应正定
    mx = float(np.max(np.abs(eigval))) if eigval.size else 1.0
    floor = max(1e-8 * mx, 1e-12)
    n_flipped = int(np.sum(eigval <= 0.0))
    eig_use = np.maximum(eigval, floor)
    logdet = float(np.sum(np.log(eig_use)))
    k = xm.size
    log_marg = g(xm) + 0.5 * k * _LOG2PI - 0.5 * logdet
    eigvec = np.linalg.eigh(A)[1]
    cov = (eigvec / eig_use) @ eigvec.T
    cov = 0.5 * (cov + cov.T)
    return {"mode": xm, "log_joint": float(g(xm)), "log_marginal": float(log_marg),
            "cov": cov, "eigval": eigval, "n_flipped": n_flipped,
            "n_evals": int(getattr(res, "nfev", 0)),
            "fell_back": bool(fell_back),
            "n_nonfinite_g": int(stats["nonfinite"]),
            "converged": bool(getattr(res, "success", False))}


# ------------------------------------------------------------------
# 3. 拉普拉斯-EM 拟合
# ------------------------------------------------------------------
def hier_fit(subjects: list[dict], x_init: list | None = None,
             mu_init=None, log_sigma_init=float(np.log(0.4)),
             n_em: int = 12, tol: float = 1e-4, maxiter: int = MAX_MODE_ITER,
             verbose: bool = False) -> dict:
    """拉普拉斯-EM 拟合群体分布，返回超参数与逐被试众数。

    Returns
    -------
    dict: ``mu``/``log_sigma``/``sigma``/``modes``/``covs``/``log_marginal``/
          ``log_joint_total``/``n_flipped``/``n_fallback``/``n_nonfinite_g``/
          ``n_em_used``/``history``。

    ``n_fallback`` 与 ``n_nonfinite_g`` 是**退化计数**，必须随结果一起报：
    前者是"某次众数搜索优化失败、退回 `x_init`"的次数（该被试的众数其实是起点），
    后者是"目标函数在某个扰动点非有限"的次数（会让 L-BFGS-B 的数值梯度失效）。
    两者都会被 `subject_map_laplace` 静默吸收（见主计划 D51）。
    """
    n = len(subjects)
    k = len(subjects[0]["names"])
    for s in subjects:
        if len(s["names"]) != k:
            raise ValueError("所有被试的参数维数必须一致")

    if x_init is None:
        x_init = [_x0_of(s) for s in subjects]
    x_cur = [np.asarray(v, float).ravel() for v in x_init]
    mu = (np.mean(np.array(x_cur), axis=0) if mu_init is None
          else np.asarray(mu_init, float).ravel())
    log_sigma = np.full(k, float(log_sigma_init))
    history = []

    for it in range(int(n_em)):
        modes, covs, lms, flips, evals = [], [], [], 0, 0
        fbs, nfg = 0, 0
        for s, xi in zip(subjects, x_cur):
            r = subject_map_laplace(s, xi, mu, log_sigma, maxiter=maxiter)
            modes.append(r["mode"]); covs.append(r["cov"])
            lms.append(r["log_marginal"]); flips += r["n_flipped"]
            evals += r["n_evals"]
            fbs += int(r["fell_back"]); nfg += r["n_nonfinite_g"]
        M = np.array(modes)
        # ---- M 步（闭式）----
        mu_new = (M.sum(axis=0) + 0.0 / POP_MU_PRIOR_SD ** 2) / (n + 1.0 / POP_MU_PRIOR_SD ** 2)
        var = np.mean((M - mu_new) ** 2
                      + np.array([np.diag(c) for c in covs]), axis=0)
        sigma_new = np.sqrt(np.maximum(var, SIGMA_FLOOR ** 2))
        log_sigma_new = np.log(sigma_new)
        step = max(float(np.max(np.abs(mu_new - mu))),
                   float(np.max(np.abs(log_sigma_new - log_sigma))))
        history.append({"it": it, "step": step, "mu": mu_new.copy(),
                        "log_sigma": log_sigma_new.copy(),
                        "log_marginal_sum": float(np.sum(lms))})
        mu, log_sigma = mu_new, log_sigma_new
        x_cur = modes
        if verbose:
            print(f"  EM {it:2d}: step={step:.5f}  logΣmarg={np.sum(lms):.4f}  "
                  f"sigma={np.exp(log_sigma)}")
        if step < tol:
            break

    # 用收敛后的超参数重算一次，保证 modes/covs 与 mu/log_sigma 自洽
    modes, covs, lms, flips = [], [], [], 0
    fbs, nfg = 0, 0
    for s, xi in zip(subjects, x_cur):
        r = subject_map_laplace(s, xi, mu, log_sigma, maxiter=maxiter)
        modes.append(r["mode"]); covs.append(r["cov"])
        lms.append(r["log_marginal"]); flips += r["n_flipped"]
        fbs += int(r["fell_back"]); nfg += r["n_nonfinite_g"]
    return {"mu": mu, "log_sigma": log_sigma, "sigma": np.exp(log_sigma),
            "modes": np.array(modes), "covs": covs,
            "log_marginal": np.array(lms),
            "log_joint_total": float(np.sum(lms)) + _log_hyper_prior(mu, log_sigma),
            "n_flipped": int(flips), "n_em_used": len(history),
            "n_fallback": int(fbs), "n_nonfinite_g": int(nfg),
            "history": history, "k": k, "n_subjects": n}


# ------------------------------------------------------------------
# 4. 超参数后验（拉普拉斯）与抽样
# ------------------------------------------------------------------
def hyper_hessian(subjects: list[dict], mu, log_sigma, x_warm,
                  step: float = HYPER_STEP,
                  maxiter: int = MAX_MODE_ITER) -> dict:
    """对 ``(mu, log sigma)`` 的**边际目标**做中心差分 Hessian。

    目标 = ``Σ_s log p(y_s | mu, sigma) + log 先验(mu, log sigma)``。
    每次评估都用上一次的众数**热启动**（冷启动太贵，见模块 docstring）。
    """
    mu = np.asarray(mu, float).ravel()
    log_sigma = np.asarray(log_sigma, float).ravel()
    k = mu.size
    x_warm = [np.asarray(v, float).ravel() for v in x_warm]

    def obj(theta):
        m = theta[:k]; ls = theta[k:]
        tot = _log_hyper_prior(m, ls)
        for i, s in enumerate(subjects):
            r = subject_map_laplace(s, x_warm[i], m, ls, maxiter=maxiter)
            x_warm[i] = r["mode"]
            tot += r["log_marginal"]
        return float(tot)

    theta0 = np.concatenate([mu, log_sigma])
    n = theta0.size
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            tp, tm = theta0.copy(), theta0.copy()
            tp[i] += step; tp[j] += step
            tm[i] -= step; tm[j] -= step
            a = obj(tp); b = obj(tm)
            tp2, tm2 = theta0.copy(), theta0.copy()
            tp2[i] += step; tp2[j] -= step
            tm2[i] -= step; tm2[j] += step
            c = obj(tp2); d = obj(tm2)
            H[i, j] = H[j, i] = (a - c - d + b) / (4.0 * step * step)
    return {"H": H, "theta0": theta0, "n_evals": 4 * n * (n + 1) // 2,
            "x_warm": x_warm}


def hyper_hessian_analytic(modes, covs, mu, log_sigma,
                           with_prior: bool = True) -> dict:
    """超参数 Hessian 的**解析**版本（Louis 恒等式）—— **零次额外众数搜索**。

    动机（主计划 D46）：``hyper_hessian`` 的有限差分要调
    ``4·nh(nh+1)/2`` 次目标，而**每次目标都对全部 N 人各做一次温启动众数搜索**
    ⇒ 正式规模（40 人、M-T1）**38 560 次搜索 ≈ 145 h**，占单组总时长的一半以上。
    但那些搜索是**不必要**的：EM 的最后一步已经把每个被试的众数 ``x*_s`` 与
    拉普拉斯协方差 ``C_s`` 算出来了，而它们就足以给出超参数 Hessian。

    推导
    ----
    拉普拉斯近似下 ``x | y_s, θ ~ N(x*_s, C_s)``。记
    ``A_k = (x_k − mu_k)/sigma_k``、``B_k = A_k²``、``ls_k = log sigma_k``，则

        ∂ log N/∂mu_k = A_k / sigma_k          ∂ log N/∂ls_k = B_k − 1
        ∂²log N/∂mu_k²     = −1/sigma_k²
        ∂²log N/∂mu_k∂ls_k = −2 A_k / sigma_k
        ∂²log N/∂ls_k²     = −2 B_k

    对 ``φ_s(θ) = log ∫ p(y_s|x) N(x; θ) dx`` 用 Louis 恒等式
    ``∂²φ/∂θ² = E[∂²log N/∂θ²] + Cov[∂log N/∂θ, ∂log N/∂θ]``。
    记 ``m_k = E[A_k]``、``s_kl = Cov[A_k, A_l] = C_kl/(sigma_k sigma_l)``，
    对联合正态展开四阶矩（``Cov[A_k, A_l²] = 2 m_l s_kl``、
    ``Cov[A_k², A_l²] = 4 m_k m_l s_kl + 2 s_kl²``）得到

        ∂²φ_s/∂mu_k∂mu_l = −δ_kl/sigma_k² + s_kl/(sigma_k sigma_l)
        ∂²φ_s/∂mu_k∂ls_l = −2 δ_kl m_k/sigma_k + 2 m_l s_kl/sigma_k
        ∂²φ_s/∂ls_k∂ls_l = −2 δ_kl E[B_k] + 4 m_k m_l s_kl + 2 s_kl²

    其中 ``E[B_k] = s_kk + m_k²``。
    ❗ **``4 m_k m_l s_kl`` 不能省**：它只在 ``m = 0``（众数恰在 mu 处）时才消失。
    漏掉它会让 ``ls`` 块相对误差达 **23%**（`check_hyper_hess.py` A1 实测抓到的）。

    ❗ **它算的是"真边际"的 Hessian，而 ``hyper_hessian`` 算的是"拉普拉斯边际"
    的 Hessian。** 两者只在**内层拉普拉斯近似精确**时才逐位相同：
    - 闭式高斯层级（``y ~ N(theta, 1)``）里内层精确 ⇒ 两者应吻合到机器精度
      （`_scratch/check_hyper_hess.py` 的 A 组就是这条判据）；
    - 真实 DDM 上两者**允许有差**，差值就是内层拉普拉斯误差，必须**如实测量并报告**
      （B 组），不得当作"实现错误"，也不得声称两者等价。

    Returns
    -------
    dict: ``H``（``(2K, 2K)``，与 ``hyper_hessian`` 同约定）、``n_evals = 0``、
          ``n_subjects``、``k``、``mean_cov_diag``（供核对 ``C`` 确实被用上）。
    """
    modes = np.atleast_2d(np.asarray(modes, float))
    mu = np.asarray(mu, float).ravel()
    log_sigma = np.asarray(log_sigma, float).ravel()
    k = mu.size
    if modes.shape[1] != k:
        raise ValueError(f"modes 的第 2 维必须等于 mu 的维数 {k}，"
                         f"收到 {modes.shape[1]}")
    if len(covs) != modes.shape[0]:
        raise ValueError(f"covs 有 {len(covs)} 个而 modes 有 {modes.shape[0]} 行")
    sigma = np.exp(log_sigma)
    sigma2 = np.exp(2.0 * log_sigma)
    n = 2 * k
    H = np.zeros((n, n))
    diag_cov = []
    for x, C in zip(modes, covs):
        C = np.asarray(C, float)
        if C.shape != (k, k):
            raise ValueError(f"每个 cov 必须是 ({k}, {k})，收到 {C.shape}")
        C = 0.5 * (C + C.T)
        EA = (np.asarray(x, float) - mu) / sigma
        CB = C / np.outer(sigma, sigma)          # Cov[A_k, A_l] = s_kl
        EB = np.diag(C) / sigma2 + EA * EA       # E[B_k] = s_kk + m_k²
        diag_cov.append(float(np.sum(np.diag(C))))
        H[:k, :k] += -np.diag(1.0 / sigma2) + C / np.outer(sigma2, sigma2)
        H_ml = (-2.0 * np.diag(EA / sigma)
                + 2.0 * (C / np.outer(sigma2, sigma)) * EA[None, :])
        H[:k, k:] += H_ml
        H[k:, :k] += H_ml.T
        H[k:, k:] += (-2.0 * np.diag(EB)
                      + 4.0 * np.outer(EA, EA) * CB + 2.0 * (CB * CB))
    if with_prior:
        d = np.empty(n)
        d[:k] = -1.0 / POP_MU_PRIOR_SD ** 2
        d[k:] = -1.0 / POP_LOGSIGMA_PRIOR_SD ** 2
        H += np.diag(d)
    return {"H": H, "theta0": np.concatenate([mu, log_sigma]),
            "n_evals": 0, "n_subjects": int(modes.shape[0]), "k": k,
            "mean_cov_diag": float(np.mean(diag_cov)) if diag_cov else 0.0}


def hyper_draws(subjects: list[dict], fit: dict, n_draws: int = 200,
                seed: int = 0, step: float = HYPER_STEP,
                eig_floor: float = 1e-6, method: str = "fd") -> dict:
    """超参数后验的拉普拉斯抽样 ⇒ ``(n_draws, 2K)`` 的 ``(mu, log sigma)``。

    ``method``：``"fd"``（默认，有限差分，与历史结果可比）或 ``"analytic"``
    （``hyper_hessian_analytic``，**零次额外众数搜索**）。两者在有内层拉普拉斯
    误差时**不相等**——切换必须连同实测差值一起交代，不得静默替换。
    """
    if method == "analytic":
        hh = hyper_hessian_analytic(fit["modes"], fit["covs"],
                                    fit["mu"], fit["log_sigma"])
    elif method == "fd":
        hh = hyper_hessian(subjects, fit["mu"], fit["log_sigma"], fit["modes"],
                           step=step)
    else:
        raise ValueError(f"method 只能是 'fd' 或 'analytic'，收到 {method!r}")
    A = -0.5 * (hh["H"] + hh["H"].T)
    eigval, eigvec = np.linalg.eigh(A)
    mx = float(np.max(np.abs(eigval))) if eigval.size else 1.0
    floor = max(eig_floor * mx, 1e-12)
    n_flipped = int(np.sum(eigval <= 0.0))
    eig_use = np.maximum(eigval, floor)
    cov = (eigvec / eig_use) @ eigvec.T
    cov = 0.5 * (cov + cov.T)
    rng = np.random.default_rng(seed)
    try:
        th = rng.multivariate_normal(hh["theta0"], cov, size=n_draws,
                                     method="cholesky")
    except np.linalg.LinAlgError:
        z = rng.standard_normal((n_draws, eigval.size))
        th = hh["theta0"] + (z * np.sqrt(eig_use)) @ eigvec.T
    k = hh["theta0"].size // 2
    th2 = np.atleast_2d(th)
    # ❗ D75：`n_flipped` 是**符号**判据（`λ ≤ 0`），而实测里失败的拟合 `λ_min` 常常只到
    #    −0.005（相对 `λ_max` 约 1e-5）——符号翻了、但幅度近零，单看符号说不清"有多坏"。
    #    真正与之同步恶化的是**抽样本身跑到了哪**：`max_abs_theta`（本次抽样 |θ| 的最大值）。
    #    扫描实测（n_em=2、n_x=21、S=2、seed=7）：正定的四个拟合 `max|θ|` ≤ 7.3，
    #    非正定的三个 33.6 / 62.8 / 97.9（2 人 S=15 那次 303）⇒ 两者同向、分离 5–40 倍。
    #    所以把 `max_abs_theta` 一并传出，让报告能同时印"符号"与"跑多远"。
    return {"theta": th2, "mu": th2[:, :k],
            "log_sigma": th2[:, k:],
            "cov": cov, "eigval": eigval, "n_flipped": n_flipped,
            "max_abs_theta": float(np.max(np.abs(th2))),
            "theta0": hh["theta0"], "n_evals": hh["n_evals"]}


# ------------------------------------------------------------------
# 5. 以被试为单位的 LOO
# ------------------------------------------------------------------
def loo_matrix(subjects: list[dict], hyper: dict, mode_warm=None,
               maxiter: int = MAX_MODE_ITER,
               stats: dict | None = None) -> np.ndarray:
    """``(S, N)``：第 i 个超参数抽取下**每个被试**的边际对数似然。

    ⚠️ 每个 (抽取, 被试) 都要**重新求众数**（热启动）。不重求而直接沿用
    ``fit["modes"]`` 会让矩阵在所有抽取上几乎常数，PSIS 的 Pareto 诊断就失去意义。

    传入 ``stats``（一个空 dict）会得到这份矩阵的**退化计数**：
    ``n_searches`` / ``n_fallback`` / ``n_nonfinite_g``。
    ❗ 这三个数**必须随 LOO 结果一起报**：``subject_map_laplace`` 会把
    "优化失败后退回初值"和"目标函数在某处非有限"都**静默吸收**，
    ``n_nonfinite_loglik`` 看不见它们（见主计划 D51）。
    """
    th = np.atleast_2d(hyper["theta"])
    k = th.shape[1] // 2
    n = len(subjects)
    if mode_warm is None:
        # 没有热启动点时退回"超参数后验中心"处的众数搜索（冷启动，仅小 N 可接受）
        mode_warm = [None] * n
    warm = [(_x0_of(s) if w is None else np.asarray(w, float).ravel())
            for s, w in zip(subjects, mode_warm)]
    if stats is not None:
        stats.clear()
        stats.update({"n_searches": 0, "n_fallback": 0, "n_nonfinite_g": 0,
                      "n_hessian_fail": 0})
    out = np.empty((th.shape[0], n))
    for i in range(th.shape[0]):
        mu, ls = th[i, :k], th[i, k:]
        for j, s in enumerate(subjects):
            # ❗ 单个 (抽取, 被试) 的拉普拉斯 Hessian 非有限时**不许中断整轮**：
            #    长跑里这是 40 小时作业在第 39 小时被一个病态抽样杀掉的典型死法。
            #    记成 −inf 让 `psis_loo` 把它算作该观测的失败（`n_failed`），
            #    并计入 `n_hessian_fail` —— 失效必须**可归因**，不能静默。
            try:
                r = subject_map_laplace(s, warm[j], mu, ls, maxiter=maxiter)
            except ValueError:
                out[i, j] = -np.inf
                if stats is not None:
                    stats["n_hessian_fail"] += 1
                continue
            warm[j] = r["mode"]
            out[i, j] = r["log_marginal"]
            if stats is not None:
                stats["n_searches"] += 1
                stats["n_fallback"] += int(r["fell_back"])
                stats["n_nonfinite_g"] += r["n_nonfinite_g"]
    if stats is not None and stats.get("n_hessian_fail"):
        print(f"  ⚠️ LOO 矩阵：{stats['n_hessian_fail']} 个 (抽取, 被试) 的众数处 "
              f"∂²g 非有限 ⇒ 该格记 −inf（PSIS 计为失败），未中断整轮", flush=True)
    return out


def loo_matrix_trials(subjects: list[dict], hyper: dict, mode_warm=None,
                      maxiter: int = MAX_MODE_ITER,
                      stats: dict | None = None) -> np.ndarray:
    """``(S, Σ n_s)``：第 i 个超参数抽取下**每个试次**的对数似然（D73 的模型比较口径）。

    与 `loo_matrix` 的差别只在「把贡献摊到哪里」：同一批抽取、同一个众数
    ``x*_s(mu^(i), sigma^(i))``，这里取该点的**逐试次**对数似然
    ``log p(y_sj | theta_hat_s)`` 而不是整人的 profile 边际。所以

    * 列数 = 总试次（``n_obs`` 是试次数，不再是人数）；
    * 每列是 O(1) 量级 ⇒ 一个荒诞的超参数抽取**不会**再支配整列，
      ``p_loo`` 才回到「有效参数数」的量纲（实测 ``p_loo/n_obs = 0.138``、``k_max = 0``）。

    ⚠️ **这不是精确的联合边际**：超参数不确定性只通过 ``theta_hat_s`` 进入
    （profile mode plug-in，与 `loo_matrix` 同一近似层级）。引用时必须写明。

    ``subjects`` 必须是 `ddm_subject` 构造的对象（自带 ``ll_trials_x``）；
    `make_subject` 的解析基准对象没有逐试次似然，会直接报错而不是静默降级。
    """
    th = np.atleast_2d(hyper["theta"])
    k = th.shape[1] // 2
    bad = [s.get("kind") for s in subjects if "ll_trials_x" not in s]
    if bad:
        raise ValueError(
            f"loo_matrix_trials 需要 ddm_subject 构造的被试对象（含 ll_trials_x），"
            f"收到 kind={bad[:3]}…；解析基准对象请继续用 loo_matrix")
    n_trials = [int(np.asarray(s["tr"]["rt"]).size) for s in subjects]
    total = int(np.sum(n_trials))
    if mode_warm is None:
        mode_warm = [None] * len(subjects)
    warm = [(_x0_of(s) if w is None else np.asarray(w, float).ravel())
            for s, w in zip(subjects, mode_warm)]
    if stats is not None:
        stats.clear()
        stats.update({"n_searches": 0, "n_fallback": 0, "n_nonfinite_g": 0,
                      "n_hessian_fail": 0, "n_trial_ll_fail": 0})
    out = np.empty((th.shape[0], total))
    for i in range(th.shape[0]):
        mu, ls = th[i, :k], th[i, k:]
        off = 0
        for j, s in enumerate(subjects):
            nj = n_trials[j]
            sl = slice(off, off + nj)
            off += nj
            try:
                r = subject_map_laplace(s, warm[j], mu, ls, maxiter=maxiter)
            except ValueError:
                out[i, sl] = -np.inf
                if stats is not None:
                    stats["n_hessian_fail"] += 1
                continue
            warm[j] = r["mode"]
            pt = s["ll_trials_x"](r["mode"])
            if pt is None or not np.all(np.isfinite(pt)):
                out[i, sl] = -np.inf
                if stats is not None:
                    stats["n_trial_ll_fail"] += 1
                continue
            out[i, sl] = pt
            if stats is not None:
                stats["n_searches"] += 1
                stats["n_fallback"] += int(r["fell_back"])
                stats["n_nonfinite_g"] += int(r["n_nonfinite_g"])
    if stats is not None and (stats.get("n_hessian_fail")
                              or stats.get("n_trial_ll_fail")):
        print(f"  ⚠️ 试次层 LOO 矩阵：{stats['n_hessian_fail']} 个 (抽取, 被试) 的众数处 "
              f"∂²g 非有限、{stats['n_trial_ll_fail']} 个逐试次似然非有限 ⇒ 对应试次记 "
              f"−inf（PSIS 计为失败），未中断整轮", flush=True)
    return out


def loo_bruteforce(subjects: list[dict], n_em: int = 12, verbose: bool = False,
                   **fit_kw) -> np.ndarray:
    """**真** leave-one-participant-out：对每个被试，用其余 N−1 人重拟合群体分布，
    再算被留出者的边际对数似然。

    这是 `loo_matrix` + `psis_loo` 的基准（主计划要求 LOO 单位 = 被试）。
    """
    n = len(subjects)
    out = np.empty(n)
    for j in range(n):
        rest = [subjects[i] for i in range(n) if i != j]
        fit = hier_fit(rest, n_em=n_em, **fit_kw)
        r = subject_map_laplace(subjects[j], fit["modes"][0],
                                fit["mu"], fit["log_sigma"])
        out[j] = r["log_marginal"]
        if verbose:
            print(f"  留出被试 {j}: 用 {n - 1} 人拟合 ⇒ 留出者 log p = {out[j]:.3f}")
    return out


def fit_and_loo(subjects: list[dict], n_draws: int = 200, seed: int = 0,
                n_em: int = 12, do_bruteforce: bool = False,
                verbose: bool = False, hyper_method: str = "fd",
                loo_level: str = "participant") -> dict:
    """``hier_fit`` → 超参数抽取 → LOO 矩阵 → PSIS-LOO 的一站式入口。

    ``hyper_method`` 透传给 `hyper_draws` 的 ``method``：
    ``"fd"``（默认，有限差分，历史口径）或 ``"analytic"``（Louis 恒等式，**零次额外
    众数搜索** —— 正式规模下这是唯一可行的选择，见主计划 D46/D47）。

    ``loo_level``（**D73**）：
    * ``"participant"``（默认，历史口径）：``(S, N)`` 被试层矩阵。⚠️ 该层 PSIS 的
      ``p_loo`` 量的是 profile 边际在抽取间的离散度，**不可估**；结果里的
      ``loo["level"]`` 会标出来，引用时只能当「矩阵不可估」的证据。
    * ``"trial"``：``(S, Σ n_s)`` 试次层矩阵（`loo_matrix_trials`），**模型比较用这一层**。
    """
    if loo_level not in ("participant", "trial"):
        raise ValueError(f"loo_level 只能是 'participant' 或 'trial'，收到 {loo_level!r}")
    fit = hier_fit(subjects, n_em=n_em, verbose=verbose)
    hyper = hyper_draws(subjects, fit, n_draws=n_draws, seed=seed,
                        method=hyper_method)
    loo_stats: dict = {}
    if loo_level == "trial":
        L = loo_matrix_trials(subjects, hyper, mode_warm=fit["modes"],
                              stats=loo_stats)
    else:
        L = loo_matrix(subjects, hyper, mode_warm=fit["modes"], stats=loo_stats)
    loo_res = psis_loo(L)
    loo_res["level"] = loo_level
    out = {"fit": fit, "hyper": hyper, "log_lik": L,
           "loo": loo_res, "n_subjects": len(subjects), "k": fit["k"],
           "hyper_method": hyper_method, "loo_level": loo_level,
           # ⚠️ 极端超参数抽取处 `log_marginal` 可能非有限（σ 抽到荒诞区间）
           #    ⇒ PSIS 会把该观测判为失败、`k_max` 变 NaN。这个计数让失效**可归因**，
           #    而不是只在报告里看到一个 nan。
           "n_nonfinite_loglik": int(np.sum(~np.isfinite(L))),
           # ❗ 上面那个计数器**看不见**被 `subject_map_laplace` 静默吸收的退化：
           #    (a) 优化失败后退回 `x_init`，(b) 目标函数在某处非有限。
           #    (a) 会让该被试的"众数"其实是起点，(b) 会让 L-BFGS-B 的数值梯度变 nan
           #    而优化器照旧继续。两者都必须随结果一起报（主计划 D51）。
           "loo_stats": loo_stats,
           "n_fallback_fit": int(fit.get("n_fallback", 0)),
           "n_nonfinite_g_fit": int(fit.get("n_nonfinite_g", 0))}
    if do_bruteforce:
        bf = loo_bruteforce(subjects, n_em=n_em, verbose=verbose)
        out["bruteforce"] = bf
        out["bruteforce_total"] = float(np.sum(bf))
    return out


def compare_models(results: dict[str, dict]) -> str:
    """用 PSIS-LOO 矩阵做模型比较（差值 SE 用配对差，见 `loo.loo_compare`）。

    ⚠️ 两个模型的矩阵必须来自**同一批被试**（列对齐），否则配对差没有意义。
    列对齐的**前提**是两个矩阵的列数相同 —— 这里显式检查，因为「一个模型被试层、
    另一个试次层」或「少收了几个试次」会让 ``loo_compare`` 在静默错位上给出一个
    看上去很正常的 ΔELPD（D73 之后试次层矩阵的列数 = 总试次，更容易撞上）。

    推理口径（D73）：应当传**试次层**矩阵（``loo_level="trial"``）；传被试层矩阵
    会让 ``ΔELPD`` 建立在「不可估」的 ``p_loo`` 上。
    """
    mats = {}
    levels = {r.get("loo_level") for r in results.values() if "loo_level" in r}
    if len(levels) > 1:
        raise ValueError(f"参与比较的模型用了不同的 LOO 口径：{sorted(map(str, levels))}")
    if levels == {"participant"}:
        print("  ⚠️ 用**被试层** LOO 矩阵做模型比较：该层「p_loo」不可估（D73），"
              "ΔELPD 不应作为证据；请改用 loo_level='trial'", file=sys.stderr)
    shapes = {}
    for name, r in results.items():
        L = np.asarray(r["log_lik"], float)
        if not np.all(np.isfinite(L)):
            print(f"  ⚠️ 模型 {name} 的 LOO 矩阵含非有限值，PSIS 会按失败处理"
                  f"（n_failed 会如实报告）", file=sys.stderr)
        shapes[name] = L.shape
        mats[name] = L
    if len(set(shapes.values())) > 1:
        raise ValueError(f"参与比较的模型列数不一致（列必须逐位对齐）：{shapes}")
    return loo_compare(mats)
