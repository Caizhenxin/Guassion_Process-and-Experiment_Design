# -*- coding: utf-8 -*-
"""
likelihood.py —— WFPT 对数似然与逐被试 MLE（Stage 3）
=====================================================
对数似然（含 deadline 未响应项）：

    log L = Σ_{已反应} log f_side(RT_i − t0 ; v_i, a_i, z_i)
          + Σ_{未响应} log P(τ > W_i − t0 ; v_i, a_i, z_i)

* 密度用 `wfpt.flux`（已由 V1/V2 验证到 2e−4）；
* 存活用 `wfpt.survival_series`（已由 V6 验证到 3.5e−4，**解析级数，无需积分**）；
* 逐试次 ``v`` 由 `mapping.trial_params` 给出（含加性身份项与反应编码符号）。

⚠️ **识别性提醒（本模块的 `WITHIN_FREE` / `BETWEEN_FREE` 之分）**：
P 是**被试间**因子，单个被试的 P 不变 → `β_P`、`τ_P`、`β_SP` 在**单被试内不可识别**，
只有跨被试（多个 P 组）才能估计。逐被试拟合只能覆盖 `mapping.WITHIN_FREE`。
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from mapping import PARAM_BOUNDS, MappingParams, trial_params
from wfpt import flux, survival_series

__all__ = ["trials_from_arrays", "log_likelihood", "per_trial_loglik", "fit_mle",
           "numerical_hessian", "opg_information", "profile_se", "fim_diagnostics"]

_NEG_BIG = 1e12


# ------------------------------------------------------------------
# 数据容器
# ------------------------------------------------------------------
def trials_from_arrays(rt, side, omission, P, T, W, is_self, is_match) -> dict:
    """把逐试次数组打包为似然接口所需的 dict（全部 float ndarray）。"""
    return {
        "rt": np.asarray(rt, dtype=float),
        "side": np.asarray(side, dtype=int),          # 1 = 上边界(Match)，0 = 下边界
        "omission": np.asarray(omission, dtype=int),
        "P": np.asarray(P, dtype=float),
        "T": np.asarray(T, dtype=float),
        "W": np.asarray(W, dtype=float),
        "is_self": np.asarray(is_self, dtype=float),
        "is_match": np.asarray(is_match, dtype=int),
    }


# ------------------------------------------------------------------
# 对数似然
# ------------------------------------------------------------------
def per_trial_loglik(p: MappingParams, tr: dict):
    """逐试次对数似然贡献（长度 = 试次数）；参数非法或数值异常时返回 ``None``。

    与 `log_likelihood` 共用同一段计算：后者只是它的求和。拆出来是为了
    `opg_information` 需要**逐试次得分**（score），而逐试次量级 O(1)，
    在差分里比总和量级 O(n) 的噪声小得多。
    """
    tp = trial_params(tr, p)
    v, a, z, t0 = tp["v"], tp["a"], tp["z"], tp["t0"]

    if not (np.all(np.isfinite(v)) and np.all(a > 0) and np.all(z > 0)
            and np.all(z < a) and t0 > 0):
        return None

    omission = tr["omission"]
    responded = omission == 0
    out = np.empty(tr["rt"].size, dtype=float)

    # --- 已反应：边界各自的首次通过密度 ---
    if np.any(responded):
        t = tr["rt"][responded] - t0
        if np.any(t <= 0):
            return None
        side = tr["side"][responded]
        a_r, z_r, v_r = a[responded], z[responded], v[responded]
        d = np.where(side == 1, a_r - z_r, z_r)          # 到目标边界的距离
        vv = np.where(side == 1, v_r, -v_r)              # 该边界的等效漂移
        f = flux(d, vv, a_r, t)
        if not np.all(np.isfinite(f)) or np.any(f <= 0):
            return None
        out[responded] = np.log(f)

    # --- 未响应：deadline 存活概率 ---
    if np.any(~responded):
        t_max = tr["W"][~responded] - t0
        if np.any(t_max <= 0):
            return None
        s = survival_series(v[~responded], a[~responded], z[~responded], t_max)
        if not np.all(np.isfinite(s)) or np.any(s <= 0):
            return None
        out[~responded] = np.log(s)

    return out


def log_likelihood(p: MappingParams, tr: dict) -> float:
    """返回对数似然；参数非法或数值异常时返回 ``-inf``。"""
    pt = per_trial_loglik(p, tr)
    return -np.inf if pt is None else float(np.sum(pt))


# ------------------------------------------------------------------
# 有界 ↔ 无约束重参数化（优化器用）
# ------------------------------------------------------------------
def _to_x(theta, lo, hi):
    u = np.clip((theta - lo) / (hi - lo), 1e-6, 1 - 1e-6)
    return np.log(u / (1 - u))


def _from_x(x, lo, hi):
    """无约束 → 有界。用 ``expit`` 而非 ``1/(1+exp(-x))``：后者在 x 很负时溢出。"""
    return lo + (hi - lo) * expit(x)


def _x_bounds(names):
    return np.array([_to_x((PARAM_BOUNDS[n][0] + PARAM_BOUNDS[n][1]) / 2,
                           *PARAM_BOUNDS[n]) for n in names])


# ------------------------------------------------------------------
# 逐被试 MLE
# ------------------------------------------------------------------
def _bounds_for(names, override: dict | None = None):
    """取参数边界；``override`` 用于逐被试收窄（如 t0 必须小于最小 RT）。"""
    override = override or {}
    lo = np.array([override.get(n, PARAM_BOUNDS[n])[0] for n in names])
    hi = np.array([override.get(n, PARAM_BOUNDS[n])[1] for n in names])
    return lo, hi


def fit_mle(tr: dict, free_names: list[str], p_init: MappingParams,
            n_restart: int = 3, seed: int = 0, maxiter: int = 400,
            maxfun: int = 20000, bounds_override: dict | None = None,
            gtol: float = 1e-5, ftol: float = 1e-9):
    """最大似然拟合（L-BFGS-B，多起点）。

    ``maxfun`` 是安全阀：若真值/设计使某些单元退化（例如漂移被压到 0），
    似然面会变平，优化器可能一直游走。此时应下调 ``maxfun`` 并检查设计诊断，
    而不是放任它跑满。

    ⚠️ **``gtol`` 必须能收紧**（2026-10-13 教训）：本模型的似然面在
    ``(τ_T, β_T, β_ST)`` 与 ``(τ_a, δ_a)`` 方向极平（Q_T 饱和导致）。
    L-BFGS-B 默认 ``gtol=1e-5`` 会在**梯度还没到零**时判停，于是：
    * 9 参数联合 MLE 停在 ``β_T=4.96, β_ST=−4.00``（撞边界）、ll=−456.0；
    * 同一份数据上 8 参数受限拟合却达到 ll=−441.9 —— **受限解优于无约束解**，
      这在数学上不可能，只能说明优化器没收敛。
    因此凡是要报告点估计的场合，都用 ``gtol=1e-10, ftol=1e-14``。

    ``bounds_override``：逐被试收窄边界。**实践中至少要给 `t0` 设上界
    `min(rt) − ε`**——否则优化器会把 t0 推到大于最小 RT，使 `rt − t0 ≤ 0`，
    整个似然变成 −inf，拟合直接失败（开发期在 24 名被试里出现过 4 次）。
    """
    names = list(free_names)
    lo, hi = _bounds_for(names, bounds_override)
    rng = np.random.default_rng(seed)

    def negll(x):
        theta = _from_x(x, lo, hi)
        ll = log_likelihood(p_init.with_vector(names, theta), tr)
        return -ll if np.isfinite(ll) else _NEG_BIG

    starts = [_to_x(p_init.vector(names), lo, hi)]
    for _ in range(max(0, n_restart - 1)):
        # ⚠️ 不能写成 `u = rng.uniform(0.15, 0.85); x0 = log(u/(1-u))`。
        # 那是**概率空间**均匀 ⇒ x0 ∈ [−1.74, +1.74] ⇒ 参数只落在边界的 15%–85%
        # 的**中段**。对 β_T ∈ (0,8) 就是 [1.2, 5.6]，而真值 0.55 **永远采不到**。
        # 后果：多起点完全不覆盖空间，"从真值出发"实际上是**单起点**拟合，
        # 于是 Stage 3 的恢复率被系统性高估。
        # 正确做法：在 x 上大幅均匀采样（覆盖 σ ≈ 0.018–0.982 ≈ 边界的 2%–98%）。
        starts.append(rng.uniform(-4.0, 4.0, size=len(names)))

    best = None
    n_ok = 0
    for x0 in starts:
        res = minimize(negll, x0, method="L-BFGS-B",
                       options={"maxiter": maxiter, "maxfun": maxfun,
                                "gtol": gtol, "ftol": ftol})
        if np.isfinite(res.fun) and res.fun < _NEG_BIG / 2:
            n_ok += 1
            if best is None or res.fun < best.fun:
                best = res
    if best is None:
        return {"params": p_init, "loglik": -np.inf, "x": None, "success": False,
                "n_free": len(names), "names": names, "n_starts_ok": 0,
                "nfev": 0}

    theta = _from_x(best.x, lo, hi)
    return {
        "params": p_init.with_vector(names, theta),
        "loglik": float(-best.fun),
        "x": best.x, "success": bool(best.success),
        "n_free": len(names), "names": names, "n_starts_ok": n_ok,
        "nfev": int(getattr(best, "nfev", -1)),
    }


def numerical_hessian(tr: dict, names: list[str], p: MappingParams,
                      rel_step: float = 1e-4, bounds_override: dict | None = None):
    """在 ``p`` 处对**无约束坐标**做中心差分，返回 Hessian（用于标准误）。"""
    lo, hi = _bounds_for(names, bounds_override)
    x0 = _to_x(p.vector(names), lo, hi)
    n = len(names)
    h = np.maximum(np.abs(x0) * rel_step, 1e-4)

    def f(x):
        ll = log_likelihood(p.with_vector(names, _from_x(x, lo, hi)), tr)
        return -ll if np.isfinite(ll) else _NEG_BIG

    H = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            xpp, xpm, xmp, xmm = x0.copy(), x0.copy(), x0.copy(), x0.copy()
            xpp[i] += h[i]; xpp[j] += h[j]
            xpm[i] += h[i]; xpm[j] -= h[j]
            xmp[i] -= h[i]; xmp[j] += h[j]
            xmm[i] -= h[i]; xmm[j] -= h[j]
            H[i, j] = H[j, i] = (f(xpp) - f(xpm) - f(xmp) + f(xmm)) / (4 * h[i] * h[j])
    return H, x0, lo, hi


# ------------------------------------------------------------------
# 期望信息量（设计比较用）与剖面似然
# ------------------------------------------------------------------
#: χ²(1) 的 95% 分位 / 2 —— 剖面似然区间的 ΔlogL 门槛
CHI2_1_95_HALF = 3.841458820694124 / 2      # = 1.92073


def opg_information(tr: dict, names: list[str], p: MappingParams,
                    rel_step: float = 1e-3, bounds_override: dict | None = None):
    """BHHH / OPG **期望信息量**：``I = Σ_t s_t s_tᵀ``，``s_t = ∂log L_t/∂θ``。

    为什么不用 `numerical_hessian`
    ------------------------------
    二阶中心差分里，浮点噪声（``~1e−13``，577 试次对数似然量级）**直接**与信号
    ``C·h²`` 竞争；当曲率 C 很小时（本例 δa 只让 a 变 6.7%）信号落到噪声底下，
    取逆后输出 ``1e113`` 这种垃圾。OPG 里噪声以**平方**进入
    （``(1e−14)²=1e−28`` vs 信号 ``(1e−3)²=1e−6``），因此稳健得多。
    它同时天然半正定，不会给出负方差。

    差分在**自然参数尺度**上做（步长 = 边界宽度 × ``rel_step``），
    于是返回的协方差可直接开方得到参数自身单位的 SE，无需 Jacobian 修正。

    返回 ``(I, G)``：``I`` 为 n×n 信息矩阵，``G`` 为 ``n_trials × n`` 的逐试次得分。
    """
    lo, hi = _bounds_for(names, bounds_override)
    theta0 = p.vector(names)
    h = rel_step * (hi - lo)
    n = len(names)
    G = np.zeros((tr["rt"].size, n))
    for i in range(n):
        d = np.zeros(n)
        d[i] = h[i]
        pt_p = per_trial_loglik(p.with_vector(names, theta0 + d), tr)
        pt_m = per_trial_loglik(p.with_vector(names, theta0 - d), tr)
        if pt_p is None or pt_m is None:
            raise ValueError(
                f"opg_information: 参数 {names[i]} 在步长 {h[i]:g} 处越界；"
                f"请调小 rel_step 或检查真值是否贴近边界")
        G[:, i] = (pt_p - pt_m) / (2.0 * h[i])
    return G.T @ G, G


def fim_diagnostics(I: np.ndarray, names: list[str]) -> dict:
    """信息矩阵的病态度量。``cond`` 越大、``n_bad`` 越多，说明越多方向不可识别。"""
    ev = np.linalg.eigvalsh((I + I.T) / 2.0)
    ev_pos = ev[ev > 0]
    ev_max = float(ev_pos[-1]) if ev_pos.size else 0.0
    # 与最大特征值相差超过 1e8 倍的方向视为数值上不可识别
    n_bad = int(np.sum(ev < max(ev_max * 1e-8, 1e-300)))
    return {
        "eigvals": ev,
        "cond": float(ev_max / ev_pos[0]) if ev_pos.size else np.inf,
        "n_bad": n_bad,
    }


def profile_se(tr: dict, names: list[str], p: MappingParams, which: str,
               target: float = CHI2_1_95_HALF, n_grid: int = 33,
               span_frac: float = 0.25, bounds_override: dict | None = None,
               maxfun: int = 3000) -> dict:
    """**剖面似然**：固定 ``which`` 扫一格、其余参数重新优化，找 ΔlogL = target 的边界。

    这是不需要任何导数、也不假设正态的识别性判据。返回

    * ``se``   —— 由区间半宽换算的等效标准误 ``(hi-lo)/(2·1.96)``；
    * ``lo``/``hi`` —— 95% 区间端点；``None`` 表示该侧在参数边界内**未闭合**
      （即该侧不可识别 → ``se = inf``）；
    * ``xs``/``dll`` —— 剖面曲线，供画图/诊断；
    * ``x_hat`` —— **剖面的极大值位置**（= 该参数的约束 MLE），``bias = x_hat - truth``。

    ⚠️ 区间的参考点是 ``x_hat`` 而非真值：这是似然比区间的标准定义，也意味着
    ``[lo, hi]`` 不包含真值时应读作**估计有偏**（极值点被推走了），
    而不是「真值不可识别」。看是否可识别请读 ``se``/``unbounded``。
    """
    if which not in names:
        raise ValueError(f"profile_se: {which} 不在自由参数 {names} 中")
    ik = names.index(which)
    others = [n_ for n_ in names if n_ != which]
    lo, hi = _bounds_for(names, bounds_override)
    th0 = p.vector(names)

    span = span_frac * (hi[ik] - lo[ik])
    xs = np.linspace(max(lo[ik] + 1e-9, th0[ik] - span),
                     min(hi[ik] - 1e-9, th0[ik] + span), n_grid)

    prof = np.empty(n_grid)
    cur = th0.copy()
    for gi in range(n_grid):
        cur[ik] = xs[gi]
        p_fix = p.with_vector(names, cur)
        if others:
            fit = fit_mle(tr, others, p_fix, n_restart=1, maxfun=maxfun,
                          bounds_override=bounds_override)
            ll = fit["loglik"]
            if np.isfinite(ll):
                cur = fit["params"].vector(names)
                cur[ik] = xs[gi]            # 固定住被剖面的参数
        else:
            ll = log_likelihood(p_fix, tr)
        prof[gi] = ll if np.isfinite(ll) else -np.inf

    if not np.any(np.isfinite(prof)):
        return {"se": np.inf, "lo": None, "hi": None, "xs": xs, "dll": prof,
                "unbounded": "both", "which": which}

    ll_max = float(np.max(prof))
    dll = prof - ll_max                          # ≤ 0
    thr = -abs(target)
    # ⚠️ 穿越搜索必须从**剖面自身的极大值**出发，不能从真值出发。
    # 若从真值出发：当极大值远离真值时 dll[真值格点] 本身已低于阈值，
    # `_cross` 会在第一次迭代（gi == 真值格点）就判为"已穿越"，
    # 返回 lo == hi == 真值格点的零宽区间（2026-10-13 发现的假象）。
    imax = int(np.argmax(prof))
    x_hat = float(xs[imax])

    def _cross(order):
        prev = imax
        for gi in order:
            if not np.isfinite(dll[gi]):
                continue
            if dll[gi] <= thr:
                x1, y1 = xs[prev], dll[prev]
                x2, y2 = xs[gi], dll[gi]
                if y1 == y2:
                    return float(x2)
                f = (thr - y1) / (y2 - y1)
                return float(x1 + f * (x2 - x1))
            prev = gi
        return None

    lo_b = _cross(range(imax, -1, -1))
    hi_b = _cross(range(imax, n_grid))
    unbounded = []
    if lo_b is None:
        unbounded.append("lower")
    if hi_b is None:
        unbounded.append("upper")
    se = (np.inf if unbounded
          else float((hi_b - lo_b) / (2.0 * 1.959963984540054)))
    return {"se": se, "lo": lo_b, "hi": hi_b, "xs": xs, "dll": dll,
            "unbounded": "+".join(unbounded) if unbounded else None,
            "which": which, "ll_max": ll_max, "n_others": len(others),
            "x_hat": x_hat, "bias": x_hat - float(th0[ik]),
            "truth": float(th0[ik])}
