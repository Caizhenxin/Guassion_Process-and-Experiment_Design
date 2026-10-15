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

LOO 的单位是**被试**（不是试次）
--------------------------------
`loo_matrix` 给每个超参数后验抽取算一次**逐被试边际对数似然**
``log p(y_s | mu^(i), sigma^(i))`` ⇒ 得到 ``(S, N)`` 矩阵 ⇒ 交给
`loo.psis_loo` 做 Pareto 平滑。**不得**把试次级对数似然矩阵直接喂进去当作
"跨被试泛化"的证据（主计划 §3 Stage 8 明令）。
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
from twophase import RHO_NAME, MASK_RHO_BOUNDS, log_likelihood_step

__all__ = ["make_subject", "ddm_subject", "subject_map_laplace", "hier_fit",
           "hyper_hessian", "hyper_draws", "loo_matrix", "loo_bruteforce",
           "fit_and_loo", "compare_models"]

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

    return {"ll_x": ll_x, "lo": lo, "hi": hi, "names": full,
            "kind": "ddm", "rho_free": bool(rho_free), "tr": tr,
            "p_base": p_base}


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

    def g(x):
        v = sub["ll_x"](x)
        if not np.isfinite(v):
            return -np.inf
        return float(v) + _log_pop_prior(x, mu, log_sigma)

    res = minimize(lambda x: -g(x), x_init, method="L-BFGS-B",
                   options={"maxiter": int(maxiter)})
    xm = np.asarray(res.x, float)
    if not np.isfinite(g(xm)):
        # 优化失败：退回初值，并如实标记
        xm = x_init
    H = hessian_x(g, xm, rel_step=hess_step)
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
          ``log_joint_total``/``n_flipped``/``n_em_used``/``history``。
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
        for s, xi in zip(subjects, x_cur):
            r = subject_map_laplace(s, xi, mu, log_sigma, maxiter=maxiter)
            modes.append(r["mode"]); covs.append(r["cov"])
            lms.append(r["log_marginal"]); flips += r["n_flipped"]
            evals += r["n_evals"]
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
    for s, xi in zip(subjects, x_cur):
        r = subject_map_laplace(s, xi, mu, log_sigma, maxiter=maxiter)
        modes.append(r["mode"]); covs.append(r["cov"])
        lms.append(r["log_marginal"]); flips += r["n_flipped"]
    return {"mu": mu, "log_sigma": log_sigma, "sigma": np.exp(log_sigma),
            "modes": np.array(modes), "covs": covs,
            "log_marginal": np.array(lms),
            "log_joint_total": float(np.sum(lms)) + _log_hyper_prior(mu, log_sigma),
            "n_flipped": int(flips), "n_em_used": len(history),
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


def hyper_draws(subjects: list[dict], fit: dict, n_draws: int = 200,
                seed: int = 0, step: float = HYPER_STEP,
                eig_floor: float = 1e-6) -> dict:
    """超参数后验的拉普拉斯抽样 ⇒ ``(n_draws, 2K)`` 的 ``(mu, log sigma)``。"""
    hh = hyper_hessian(subjects, fit["mu"], fit["log_sigma"], fit["modes"],
                       step=step)
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
    return {"theta": np.atleast_2d(th), "mu": np.atleast_2d(th)[:, :k],
            "log_sigma": np.atleast_2d(th)[:, k:],
            "cov": cov, "eigval": eigval, "n_flipped": n_flipped,
            "theta0": hh["theta0"], "n_evals": hh["n_evals"]}


# ------------------------------------------------------------------
# 5. 以被试为单位的 LOO
# ------------------------------------------------------------------
def loo_matrix(subjects: list[dict], hyper: dict, mode_warm=None,
               maxiter: int = MAX_MODE_ITER) -> np.ndarray:
    """``(S, N)``：第 i 个超参数抽取下**每个被试**的边际对数似然。

    ⚠️ 每个 (抽取, 被试) 都要**重新求众数**（热启动）。不重求而直接沿用
    ``fit["modes"]`` 会让矩阵在所有抽取上几乎常数，PSIS 的 Pareto 诊断就失去意义。
    """
    th = np.atleast_2d(hyper["theta"])
    k = th.shape[1] // 2
    n = len(subjects)
    if mode_warm is None:
        # 没有热启动点时退回"超参数后验中心"处的众数搜索（冷启动，仅小 N 可接受）
        mode_warm = [None] * n
    warm = [(_x0_of(s) if w is None else np.asarray(w, float).ravel())
            for s, w in zip(subjects, mode_warm)]
    out = np.empty((th.shape[0], n))
    for i in range(th.shape[0]):
        mu, ls = th[i, :k], th[i, k:]
        for j, s in enumerate(subjects):
            r = subject_map_laplace(s, warm[j], mu, ls, maxiter=maxiter)
            warm[j] = r["mode"]
            out[i, j] = r["log_marginal"]
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
                verbose: bool = False) -> dict:
    """``hier_fit`` → 超参数抽取 → 被试层 LOO 矩阵 → PSIS-LOO 的一站式入口。"""
    fit = hier_fit(subjects, n_em=n_em, verbose=verbose)
    hyper = hyper_draws(subjects, fit, n_draws=n_draws, seed=seed)
    L = loo_matrix(subjects, hyper, mode_warm=fit["modes"])
    out = {"fit": fit, "hyper": hyper, "log_lik": L,
           "loo": psis_loo(L), "n_subjects": len(subjects), "k": fit["k"]}
    if do_bruteforce:
        bf = loo_bruteforce(subjects, n_em=n_em, verbose=verbose)
        out["bruteforce"] = bf
        out["bruteforce_total"] = float(np.sum(bf))
    return out


def compare_models(results: dict[str, dict]) -> str:
    """用 ``(S, N)`` 矩阵做 PSIS-LOO 模型比较（差值 SE 用配对差，见 `loo.loo_compare`）。

    ⚠️ 两个模型的 ``(S, N)`` 矩阵必须来自**同一批被试**（列对齐），否则配对差没有意义。
    """
    mats = {}
    for name, r in results.items():
        L = np.asarray(r["log_lik"], float)
        if not np.all(np.isfinite(L)):
            print(f"  ⚠️ 模型 {name} 的 LOO 矩阵含非有限值，PSIS 会按失败处理"
                  f"（n_failed 会如实报告）", file=sys.stderr)
        mats[name] = L
    return loo_compare(mats)
