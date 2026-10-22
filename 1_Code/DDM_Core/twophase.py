# -*- coding: utf-8 -*-
"""
twophase.py —— M-T1（两阶段漂移 / 阶跃）的似然、抽样与模型比较
================================================================
M-T1 把漂移在**刺激呈现期间**设为定值，掩蔽之后（``t > T``）降为 ``rho`` 倍：

    d(t) = d_stim(T),         0 ≤ t ≤ T
    d(t) = rho · d_stim(T),   t > T

它相对 M-T3（"d = d_T(T) 恒定，T 只作可用性上界"）的**可观测差别**是：
对 **RT < T** 的试次，M-T1 下整个积累过程都在刺激期内 ⇒ RT 分布**与 T 无关**；
M-T3 下漂移是 ``d_T(T)``，不同 T 的单元连 RT<T 的试次也会不同。
M-T2（斜坡）则是第三条：``d(t) = d₀ + β_T(1 − e^{−t/τ_T})``，``t ≤ T``。

★ **关键结构性事实：M-T3 是 M-T1 的严格嵌套特例。**
``rho = 1`` 时两阶段退化为单阶段，逐位等于 `likelihood.per_trial_loglik`
（`wfpt.validate_step` 的 W1 已把 ``∫G dx == survival_series`` 验到 2e-5）。
因此 Q1（"4 个 T 水平能否区分 M-T1 与 M-T3"）不需要另建拟合器：
**同一套 lin 参数化 + 一个额外参数 ``rho``**，用 ``rho`` 是否显著偏离 1
（似然比 / ΔBIC）即可回答。

⚠️ 参数边界：``rho ∈ [0, 3]``。下界 0 = 掩蔽后**完全停止**积累（最极端的
"证据被打断"假设）；上界 3 留出"掩蔽后反而加速"的余地。``rho = 1`` 恰好内点。
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from likelihood import _NEG_BIG, _bounds_for, _from_x, _to_x
from mapping import MappingParams, trial_params
from wfpt import density_step, sample_step, survival_step

__all__ = ["RHO_NAME", "MASK_RHO_BOUNDS", "trial_groups", "per_trial_loglik_step",
           "log_likelihood_step", "simulate_step_subject", "fit_mle_step", "bic"]

#: 自由参数向量里 ``rho`` 的名字（用于报告与诊断）
RHO_NAME = "rho"
#: ``rho`` 的边界：0 = 掩蔽后停止积累，1 = 无影响（= M-T3），>1 = 掩蔽后加速
MASK_RHO_BOUNDS = (0.0, 3.0)


def trial_groups(tr: dict):
    """把试次按 ``(P, T, W, is_self, is_match)`` 分组。

    同一组内 ``(v, a, z, T)`` **完全相同**（因为 ``trial_params`` 只依赖这五列），
    因此 `wfpt.density_step` / `survival_step` 需要的标量 ``a``/``z``/``T``/``v``
    可以在组内一次取定。返回布尔掩膜列表。
    """
    keys = np.column_stack([np.asarray(tr[k], dtype=float)
                            for k in ("P", "T", "W", "is_self", "is_match")])
    # ⚠️ 必须 np.all(..., axis=1)：直接 `keys == k`（k 为长度 5 的 tuple）
    # 会按列广播成 (n,5) 的逐元素布尔，而不是行掩膜。
    return [np.all(keys == k, axis=1) for k in {tuple(r) for r in keys}]


# ------------------------------------------------------------------
# 对数似然
# ------------------------------------------------------------------
def per_trial_loglik_step(p: MappingParams, tr: dict, rho: float,
                          n_x: int = 81):
    """M-T1 的逐试次对数似然（长度 = 试次数）；非法/数值异常返回 ``None``。

    ``rho = 1`` 时应**逐位等于** `likelihood.per_trial_loglik`
    （两阶段退化为单阶段）——这是接入时的自检。
    """
    tp = trial_params(tr, p)
    v, a, z, t0 = tp["v"], tp["a"], tp["z"], tp["t0"]
    if not (np.all(np.isfinite(v)) and np.all(a > 0) and np.all(z > 0)
            and np.all(z < a) and t0 > 0
            and np.isfinite(rho) and rho >= 0.0):
        return None

    rt = np.asarray(tr["rt"], dtype=float)
    omission = np.asarray(tr["omission"], dtype=int)
    side = np.asarray(tr["side"], dtype=int)
    W = np.asarray(tr["W"], dtype=float)
    TT = np.asarray(tr["T"], dtype=float)
    responded = omission == 0
    out = np.empty(rt.size, dtype=float)

    for m in trial_groups(tr):
        ii = np.flatnonzero(m)
        vv = float(v[ii[0]])
        aa = float(a[ii[0]])
        zz = float(z[ii[0]])
        tT = float(TT[ii[0]])
        v2 = float(rho) * vv

        m_r = m & responded                      # --- 已反应：首次通过密度 ---
        if np.any(m_r):
            t = rt[m_r] - t0
            if np.any(t <= 0):
                return None
            fu, fl = density_step(t, vv, v2, aa, zz, tT, n_x=n_x)
            val = np.where(side[m_r] == 1, fu, fl)
            if not np.all(np.isfinite(val)) or np.any(val <= 0):
                return None
            out[m_r] = np.log(val)

        m_o = m & ~responded                     # --- 未响应：deadline 存活 ---
        if np.any(m_o):
            tm = W[m_o] - t0
            if np.any(tm <= 0):
                return None
            s = np.atleast_1d(np.asarray(
                survival_step(vv, v2, aa, zz, tT, tm, n_x=n_x), dtype=float))
            if not np.all(np.isfinite(s)) or np.any(s <= 0):
                return None
            out[m_o] = np.log(s)

    return out


def log_likelihood_step(p: MappingParams, tr: dict, rho: float,
                        n_x: int = 81) -> float:
    """M-T1 对数似然；参数非法或数值异常返回 ``-inf``。"""
    pt = per_trial_loglik_step(p, tr, rho, n_x=n_x)
    return -np.inf if pt is None else float(np.sum(pt))


# ------------------------------------------------------------------
# 数据生成
# ------------------------------------------------------------------
def simulate_step_subject(design: dict, p: MappingParams, rho: float,
                          rng: np.random.Generator, t_max: float | None = None,
                          n_grid: int = 3000) -> dict:
    """按 M-T1 生成一名被试的观测数据。

    接口与 `simulate.simulate_subject` 一致（``rt``/``side``/``omission``/``truth``），
    便于与 M-T3 共用下游的 `trials_from_arrays` 与恢复管线。
    """
    tp = trial_params(design, p)
    v, a, z, t0 = tp["v"], tp["a"], tp["z"], tp["t0"]
    W = np.asarray(design["W"], dtype=float)
    TT = np.asarray(design["T"], dtype=float)
    n = v.size
    if t_max is None:
        # 抽样网格要覆盖到 deadline 之外一点：超出 deadline 的样本按遗漏处理
        t_max = float(np.max(W)) + 3.0

    rt = np.full(n, np.nan)
    side = np.zeros(n, dtype=int)
    omission = np.zeros(n, dtype=int)

    # 同一 (v, a, z, T) 组批量抽样（两阶段密度需要标量 T）
    key = np.column_stack([v, a, z, TT])
    uniq, inv = np.unique(np.round(key, 10), axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()

    for gi in range(uniq.shape[0]):
        idx = np.flatnonzero(inv == gi)
        if idx.size == 0:
            continue
        vv, aa, zz, tT = (float(x) for x in uniq[gi])
        tau, b = sample_step(vv, float(rho) * vv, aa, zz, tT, idx.size, rng,
                             t_max=t_max, n_grid=n_grid)
        rt_g = tau + t0
        om = (~np.isfinite(rt_g)) | (rt_g > W[idx])
        rt[idx] = np.where(om, np.nan, rt_g)
        side[idx] = np.where(om, 0, b)
        omission[idx] = om.astype(int)

    return {
        "rt": rt, "side": side, "omission": omission,
        "truth": {"v": v, "a": a, "z": z, "t0": np.full(n, t0)},
    }


# ------------------------------------------------------------------
# 数据生成（Euler 路径模拟——实用生成器）
# ------------------------------------------------------------------
def simulate_euler_subject(design: dict, p: MappingParams, rho: float,
                           rng: np.random.Generator, dt: float = 5e-5,
                           t_max: float | None = None,
                           drift_sd: float = 0.0) -> dict:
    """用 **Euler-Maruyama 路径模拟**生成一名被试的 M-T1 数据。

    为什么不用 `simulate_step_subject`（解析逆 CDF）
    ------------------------------------------------
    解析抽样要对整条时间网格求 `density_step`，而 `wfpt.flux` 的级数项数
    ``k_max`` 由**批次内最小的 t** 决定。均匀细网格（dt≈1.6 ms）会把 kmax
    顶到 ~167，于是单次抽样要算 ``n_grid × n_x × k_max ≈ 483k × 167`` 次运算，
    一组就要数十秒——实测 576 试次需要 **70 s/被试**（6 次重复 70.5 s）。
    Euler 在 dt=5e-5 下只要 **6 s/被试**，快一个数量级；代价是首次通过时刻被
    量化到 ``dt``。

    ⚠️ **dt 必须标定过**（`_scratch/check_euler_dt.py`）。首次通过问题的
    Euler 弱阶低于常说的 1 阶：以解析单阶段生成器为基准（6 次重复均值，
    正确率 0.8254、遗漏 0.3197、RT 759.2 ms），实测

        dt=2e-4   |Δacc| 0.0174   1.6 s/被试
        dt=1e-4   |Δacc| 0.0046   3.1 s
        dt=5e-5   |Δacc| 0.0022   6.1 s   ← 默认
        dt=2.5e-5 |Δacc| 0.0003  12.4 s

    偏差单调收敛到解析值 ⇒ 是离散化偏差而非实现错误。默认 ``dt=5e-5``
    在 0.002 的正确率精度与 6 s/被试 之间取平衡。

    ⚠️ **两个常被混淆的比例**（本设计实测，t0 = 220 ms、T ≤ 250 ms）：
    ``P(RT < T) = 0.0000``（响应发生在刺激结束前——D5「按键即结束」是否触发），
    而 ``P(τ < T) = 0.052``（**积累过程**在刺激期内结束）。二者不同是因为
    ``RT = τ + t0``。M-T1 的掩蔽阶段影响的是 ``τ > T`` 的那 **~95%** 试次。

    步进规则：``d(t) = d(T)``（``t ≤ T``），``rho·d(T)``（``t > T``）；
    位置越过边界即判为在该步内吸收。

    接口与 `simulate.simulate_subject` 一致，可直接接入恢复管线。
    """
    tp = trial_params(design, p)
    v = np.asarray(tp["v"], dtype=float)
    if drift_sd and drift_sd > 0:
        # 逐试次漂移变异（lognormal，均值为 1）：真实数据的 CAF 上升靠的就是它
        v = v * np.exp(rng.normal(0.0, float(drift_sd), v.size))
    a = np.asarray(tp["a"], dtype=float)
    z = np.asarray(tp["z"], dtype=float)
    t0 = tp["t0"]
    W = np.asarray(design["W"], dtype=float)
    TT = np.asarray(design["T"], dtype=float)
    n = v.size
    if t_max is None:
        t_max = float(np.max(W))
    n_steps = int(np.ceil(t_max / dt))
    sq = np.sqrt(dt)

    x = z.astype(float).copy()
    alive = np.ones(n, dtype=bool)
    tau = np.full(n, np.inf)
    side = np.zeros(n, dtype=int)

    for i in range(n_steps):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        s = i * dt
        vv = np.where(s <= TT[idx], v[idx], float(rho) * v[idx])
        x[idx] += vv * dt + sq * rng.standard_normal(idx.size)
        hit_u = idx[x[idx] >= a[idx]]
        hit_l = idx[x[idx] <= 0.0]
        if hit_u.size:
            tau[hit_u] = s + dt
            side[hit_u] = 1
            alive[hit_u] = False
        if hit_l.size:
            tau[hit_l] = s + dt
            side[hit_l] = 0
            alive[hit_l] = False

    rt = tau + float(t0)
    omission = (~np.isfinite(rt)) | (rt > W)
    rt = np.where(omission, np.nan, rt)
    side = np.where(omission, 0, side)
    return {
        "rt": rt, "side": side.astype(int), "omission": omission.astype(int),
        "truth": {"v": v, "a": a, "z": z, "t0": np.full(n, t0)},
    }


# ------------------------------------------------------------------
# 逐被试 MLE（多一个参数 rho）
# ------------------------------------------------------------------
def fit_mle_step(tr: dict, free_names: list[str], p_init: MappingParams,
                 rho_init: float = 1.0, n_restart: int = 1, seed: int = 0,
                 maxiter: int = 250, maxfun: int = 6000,
                 bounds_override: dict | None = None,
                 gtol: float = 1e-8, ftol: float = 1e-12,
                 rho_fixed: float | None = None, n_x: int = 81):
    """M-T1 的逐被试 MLE（L-BFGS-B，多起点）。

    ``rho_fixed`` 非 None 时把 ``rho`` 钉死（``rho_fixed=1.0`` 即 M-T3），
    用于**嵌套检验**：同一优化器、同一初值，唯一差别是 rho 自由与否。

    警告与 ``likelihood.fit_mle`` 相同：似然面在饱和方向上极平，报告点估计
    时须用 ``gtol≈1e-8`` 或更紧；``maxfun`` 是安全阀。
    """
    names = list(free_names)
    lo, hi = _bounds_for(names, bounds_override)
    free_rho = rho_fixed is None
    if free_rho:
        lo = np.append(lo, MASK_RHO_BOUNDS[0])
        hi = np.append(hi, MASK_RHO_BOUNDS[1])
    k = len(names)
    rng = np.random.default_rng(seed)

    def unpack(x):
        th = _from_x(x, lo, hi)
        pp = p_init.with_vector(names, th[:k])
        rr = float(th[k]) if free_rho else float(rho_fixed)
        return pp, rr

    def negll(x):
        pp, rr = unpack(x)
        ll = log_likelihood_step(pp, tr, rr, n_x=n_x)
        return -ll if np.isfinite(ll) else _NEG_BIG

    x0 = _to_x(p_init.vector(names), lo[:k], hi[:k])
    if free_rho:
        x0 = np.append(x0, _to_x(np.array([rho_init]), lo[k:], hi[k:]))
    starts = [x0]
    for _ in range(max(0, n_restart - 1)):
        # 与 likelihood.fit_mle 同一约定：在 x 上大幅均匀采样（覆盖边界 2%–98%）
        starts.append(rng.uniform(-4.0, 4.0, size=lo.size))

    best = None
    n_ok = 0
    for s0 in starts:
        res = minimize(negll, s0, method="L-BFGS-B",
                       options={"maxiter": maxiter, "maxfun": maxfun,
                                "gtol": gtol, "ftol": ftol})
        if np.isfinite(res.fun) and res.fun < _NEG_BIG / 2:
            n_ok += 1
            if best is None or res.fun < best.fun:
                best = res

    rep_names = names + ([RHO_NAME] if free_rho else [])
    if best is None:
        return {"params": p_init, "rho": float(1.0 if free_rho else rho_fixed),
                "loglik": -np.inf, "x": None, "success": False,
                "n_free": lo.size, "names": rep_names, "n_starts_ok": 0, "nfev": 0}

    pp, rr = unpack(best.x)
    return {"params": pp, "rho": rr, "loglik": float(-best.fun), "x": best.x,
            "success": bool(best.success), "n_free": int(lo.size),
            "names": rep_names, "n_starts_ok": n_ok,
            "nfev": int(getattr(best, "nfev", -1))}


def bic(loglik: float, n_free: int, n_obs: int) -> float:
    """``BIC = −2·logL + k·ln(n)``；``n_obs`` 用**试次数**（每试次一个观测）。"""
    return -2.0 * float(loglik) + float(n_free) * np.log(float(n_obs))
