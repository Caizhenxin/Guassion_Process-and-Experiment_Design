"""单元均值（cell-mean）参数化：不做函数形式假设的**防御性备选**。

配套脚本：`_scratch/check_cellmean.py`。

## 它为什么存在

`mapping.py` 的 ``lin`` 参数化把 T 通道写成一条直线
``d(T) = d_ref + beta_T * (T - T_ref)``，把 W 通道写成一条直线
``a(W) = a_ref + delta_a * (W - W_ref)``。这两条直线是**建模假设**，
不是数据里必然成立的东西。审稿人完全有理由问：

    "你怎么知道漂移随 T 是线性的？如果不是，你那些可识别性结论还成立吗？"

本模块把这两条直线换成**每个水平一个自由参数**，用来**衡量线性限制的代价**：

* 非自我漂移：``d(T_k) = d_ref + dt[k]``，4 个 T 水平，``dt[0] = 0``（参考水平）
* 自我附加漂移：``+ beta_S + st[k]``，``st[0] = 0``（参考水平）
* 边界：``a(W_j) = a_ref + dw[j]``，3 个 W 水平，``dw[0] = 0``（参考水平）
* P 通道**保持不变**（``f_P`` 是 S 形，`工作流_主计划.md` D31 的 D 段已证明
  不能线性化：无噪声直线拟合会把 ``beta_P`` 压掉 140 倍）
* ``t0``、``beta_P``、``beta_SP`` 与 lin 相同

共 **14** 个自由参数（lin 是 7 个）。参数多一倍，所以**它本身不是"更好的模型"**；
它的唯一用途是回答「线性限制把经验剖面扭曲了多少」。

## 参考点的选择（与 lin 不同，且是刻意的）

``d_ref`` 锚在 **T 水平 0**（``T=0.0333 s``）、``a_ref`` 锚在 **W 水平 0**
（``W=0.79998 s``），而 lin 的 ``d_ref``/``a_ref`` 锚在 ``T_ref=0.10``/``W_ref=1.20``
（都不在水平集里，是外推截距）。锚在水平上可以让 ``d_ref``/``dt`` 全部被数据直接确定，
不需要外推——这正是"单元均值"这个名字的含义。两者比较时**只比水平上的剖面值**，
不比截距。

## 数值

``per_trial_loglik_cell`` 与 `likelihood.per_trial_loglik` 共用同一套
`wfpt.flux` / `wfpt.survival_series` 调用（单阶段 M-T3），只是把
``mapping.trial_params`` 换成 ``trial_params_cell``。这里**复制**而不是抽象，
是为了不动已经过 5/5 验收的 `likelihood.py`。
"""

from __future__ import annotations

from dataclasses import dataclass, replace as _dc_replace

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from mapping import f_P
from wfpt import flux, survival_series

__all__ = [
    "CELL_NAMES",
    "CELL_BOUNDS",
    "CellParams",
    "set_levels",
    "drift_profile",
    "boundary_profile",
    "trial_params_cell",
    "per_trial_loglik_cell",
    "log_likelihood_cell",
    "fit_mle_cell",
    "numerical_hessian_cell",
]

# ------------------------------------------------------------------
# 参数清单与边界
# ------------------------------------------------------------------
CELL_NAMES = [
    "d_ref",                                  # 非自我漂移 @ T 水平 0
    "dt_1", "dt_2", "dt_3",                   # 相对 T 水平 0 的额外漂移（非自我）
    "beta_S",                                 # 自我主效应
    "st_1", "st_2", "st_3",                   # 自我附加漂移随 T 的额外变化
    "a_ref",                                  # 边界 @ W 水平 0
    "dw_1", "dw_2",                           # 相对 W 水平 0 的边界变化
    "beta_P",                                 # P 主效应（与 lin 相同）
    "beta_SP",                                # 自我 × P（与 lin 相同）
    "t0",                                     # 非决策时间
]
N_CELL_FREE = len(CELL_NAMES)

#: 边界取值。``d_ref``/``dt_*``/``beta_S``/``st_*`` 用的是 `mapping.PARAM_BOUNDS`
#: 里对应量的界（`d_ref` 0.20–6.0、`beta_S` −2–2、`beta_T` −6–8 作为水平差的上限）。
CELL_BOUNDS = {
    "d_ref": (0.20, 6.0),
    "dt_1": (-6.0, 8.0),
    "dt_2": (-6.0, 8.0),
    "dt_3": (-6.0, 8.0),
    "beta_S": (-2.0, 2.0),
    "st_1": (-4.0, 4.0),
    "st_2": (-4.0, 4.0),
    "st_3": (-4.0, 4.0),
    "a_ref": (0.30, 5.0),
    "dw_1": (-3.0, 3.0),
    "dw_2": (-3.0, 3.0),
    "beta_P": (-6.0, 8.0),
    "beta_SP": (-4.0, 4.0),
    "t0": (0.05, 0.60),
}

@dataclass
class CellParams:
    """单元均值参数化的参数容器（接口与 `mapping.MappingParams` 平行）。"""

    d_ref: float = 0.60
    dt_1: float = 0.00
    dt_2: float = 0.00
    dt_3: float = 0.00
    beta_S: float = 0.15
    st_1: float = 0.00
    st_2: float = 0.00
    st_3: float = 0.00
    a_ref: float = 1.98
    dw_1: float = 0.00
    dw_2: float = 0.00
    beta_P: float = 0.35
    beta_SP: float = 0.00
    t0: float = 0.22
    T_ref: float = 0.10
    P_ref: float = 120.0
    #: P 通道的时标。D31 的处方是**先验固定** ``tau_P``，所以这里不是自由参数；
    #: 默认 30.0 与 `recover_group.py` 的处方值一致。改它会移动 ``beta_P`` 的尺度，
    #: 因此比较 cell-mean 与 lin 时必须用**同一个** ``tau_P``。
    tau_P: float = 30.0

    def as_dict(self) -> dict:
        return {n: float(getattr(self, n)) for n in CELL_NAMES}

    def replace(self, **kw) -> "CellParams":
        for k in kw:
            if not hasattr(self, k):
                raise KeyError(f"未知字段 {k!r}")
        return _dc_replace(self, **kw)

    def vector(self, names=None) -> np.ndarray:
        names = CELL_NAMES if names is None else names
        return np.array([float(getattr(self, n)) for n in names], dtype=float)

    def with_vector(self, names, x) -> "CellParams":
        kw = {n: float(v) for n, v in zip(names, np.asarray(x, dtype=float))}
        return self.replace(**kw)


# ------------------------------------------------------------------
# T / W 水平表（模块级，由调用方设定）
# ------------------------------------------------------------------
_T_LEVELS: np.ndarray | None = None
_W_LEVELS: np.ndarray | None = None


def set_levels(T_levels, W_levels) -> None:
    """登记 T / W 的水平集（必须与生成数据时用的完全一致，顺序无关）。"""
    global _T_LEVELS, _W_LEVELS
    t = np.sort(np.unique(np.asarray(T_levels, dtype=float)))
    w = np.sort(np.unique(np.asarray(W_levels, dtype=float)))
    if t.size < 1 or w.size < 1:
        raise ValueError("水平集不能为空")
    _T_LEVELS, _W_LEVELS = t, w


def _level_index(arr, levels: np.ndarray, what: str) -> np.ndarray:
    """把连续取值映射到水平下标；容差取水平间距的 1e-6。"""
    arr = np.asarray(arr, dtype=float)
    if np.allclose(arr, arr[0]) and arr.size and levels.size == 1:
        return np.zeros(arr.size, dtype=int)
    tol = 1e-6 * max(float(np.max(levels)) if levels.size else 1.0, 1e-3)
    idx = np.searchsorted(levels, arr)
    idx = np.clip(idx, 1, levels.size - 1) if levels.size > 1 else np.zeros(arr.size, int)
    left = np.clip(idx - 1, 0, levels.size - 1)
    # 取左右更近的一个（searchsorted 给出的是插入位）
    idx = np.where(np.abs(levels[left] - arr) <= np.abs(levels[idx] - arr), left, idx)
    if np.any(np.abs(levels[idx] - arr) > tol):
        bad = arr[np.abs(levels[idx] - arr) > tol][0]
        raise ValueError(f"{what}={bad!r} 不在已登记的水平集 {levels.tolist()} 内")
    return idx


def _indices(tr) -> tuple[np.ndarray, np.ndarray]:
    if _T_LEVELS is None or _W_LEVELS is None:
        raise RuntimeError("必须先调用 cellmean.set_levels(T_levels, W_levels)")
    return (_level_index(tr["T"], _T_LEVELS, "T"),
            _level_index(tr["W"], _W_LEVELS, "W"))


def n_t_levels() -> int:
    return int(_T_LEVELS.size if _T_LEVELS is not None else 0)


def n_w_levels() -> int:
    return int(_W_LEVELS.size if _W_LEVELS is not None else 0)


# ------------------------------------------------------------------
# 单试次参数
# ------------------------------------------------------------------
def _st_vec(p: CellParams, k: int) -> np.ndarray:
    """自我附加漂移随 T 的额外项 ``st[k]``（``st[0] = 0``）。"""
    if k == 0:
        return np.zeros_like(np.asarray(k, dtype=float))
    return np.full_like(np.asarray(k, dtype=float), getattr(p, f"st_{k}"))


def _dummy_column(ki: np.ndarray, p: CellParams, prefix: str, n_levels: int) -> np.ndarray:
    """把水平下标摊成参考水平编码的哑变量列（水平 0 为参考，恒为 0）。"""
    col = np.zeros(ki.size, dtype=float)
    for i in range(1, n_levels):
        col = np.where(ki == i, getattr(p, f"{prefix}_{i}"), col)
    return col


def drift_profile(p: CellParams, dfp: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """返回 ``(非自我漂移剖面, 自我漂移剖面)``，各长度 = T 水平数。"""
    k = n_t_levels()
    base = p.d_ref + p.beta_P * dfp
    dts = np.array([0.0] + [getattr(p, f"dt_{i}") for i in range(1, k)])
    sts = np.array([0.0] + [getattr(p, f"st_{i}") for i in range(1, k)])
    other = base + dts
    self_ = base + dts + p.beta_S + p.beta_SP * dfp + sts
    return other, self_


def boundary_profile(p: CellParams) -> np.ndarray:
    """返回边界剖面，长度 = W 水平数。"""
    j = n_w_levels()
    dws = np.array([0.0] + [getattr(p, f"dw_{i}") for i in range(1, j)])
    return p.a_ref + dws


def dfp_of(p: CellParams, P) -> np.ndarray:
    """P 通道的 ``f_P(P, tau_P) - f_P(P_ref, tau_P)``（与 lin 完全同一公式）。"""
    return f_P(P, p.tau_P) - f_P(p.P_ref, p.tau_P)


def trial_params_cell(tr: dict, p: CellParams) -> dict:
    """与 `mapping.trial_params` 同接口，但 T/W 通道用单元均值。"""
    ki, ji = _indices(tr)
    dfp = dfp_of(p, tr["P"])

    dt = _dummy_column(ki, p, "dt", n_t_levels())
    st = _dummy_column(ki, p, "st", n_t_levels())
    dw = _dummy_column(ji, p, "dw", n_w_levels())

    d = (p.d_ref + p.beta_P * dfp + dt
         + tr["is_self"] * (p.beta_S + p.beta_SP * dfp + st))
    a = p.a_ref + dw

    is_match = np.asarray(tr["is_match"], dtype=float)
    sign = np.where(is_match == 1, 1.0, -1.0)
    return {
        "v": sign * np.maximum(d, 1e-6),
        "a": np.maximum(a, 1e-3),
        "z": 0.5 * np.maximum(a, 1e-3),
        "t0": float(p.t0),
        "d": d,
    }


# ------------------------------------------------------------------
# 对数似然
# ------------------------------------------------------------------
def per_trial_loglik_cell(p: CellParams, tr: dict):
    """逐试次对数似然；参数非法或数值异常时返回 ``None``。"""
    try:
        tp = trial_params_cell(tr, p)
    except ValueError:
        return None
    v, a, z, t0 = tp["v"], tp["a"], tp["z"], tp["t0"]

    if not (np.all(np.isfinite(v)) and np.all(a > 0) and np.all(z > 0)
            and np.all(z < a) and t0 > 0):
        return None

    omission = tr["omission"]
    responded = omission == 0
    out = np.empty(tr["rt"].size, dtype=float)

    if np.any(responded):
        t = tr["rt"][responded] - t0
        if np.any(t <= 0):
            return None
        side = tr["side"][responded]
        a_r, z_r, v_r = a[responded], z[responded], v[responded]
        d = np.where(side == 1, a_r - z_r, z_r)
        vv = np.where(side == 1, v_r, -v_r)
        f = flux(d, vv, a_r, t)
        if not np.all(np.isfinite(f)) or np.any(f <= 0):
            return None
        out[responded] = np.log(f)

    if np.any(~responded):
        t_max = tr["W"][~responded] - t0
        if np.any(t_max <= 0):
            return None
        s = survival_series(v[~responded], a[~responded], z[~responded], t_max)
        if not np.all(np.isfinite(s)) or np.any(s <= 0):
            return None
        out[~responded] = np.log(s)

    return out


def log_likelihood_cell(p: CellParams, tr: dict) -> float:
    pt = per_trial_loglik_cell(p, tr)
    return -np.inf if pt is None else float(np.sum(pt))


# ------------------------------------------------------------------
# 拟合
# ------------------------------------------------------------------
def _x_bounds(names):
    return np.array([_to_x((CELL_BOUNDS[n][0] + CELL_BOUNDS[n][1]) / 2.0, *CELL_BOUNDS[n])
                     for n in names])


def _to_x(theta, lo, hi):
    u = np.clip((theta - lo) / (hi - lo), 1e-6, 1 - 1e-6)
    return np.log(u / (1 - u))


def _from_x(x, lo, hi):
    return lo + (hi - lo) * expit(x)


def _bounds_for(names, override=None):
    override = override or {}
    lo = np.array([override.get(n, CELL_BOUNDS[n])[0] for n in names])
    hi = np.array([override.get(n, CELL_BOUNDS[n])[1] for n in names])
    return lo, hi


def fit_mle_cell(tr: dict, p_init: CellParams, free_names=None,
                 n_restart: int = 2, seed: int = 0, maxiter: int = 250,
                 maxfun: int = 6000, bounds_override: dict | None = None,
                 gtol: float = 1e-8, ftol: float = 1e-12) -> dict:
    """多起点 L-BFGS-B MLE，签名与 `likelihood.fit_mle` 平行。"""
    names = list(CELL_NAMES if free_names is None else free_names)
    lo, hi = _bounds_for(names, bounds_override)
    theta0 = p_init.vector(names)

    def negll(x):
        th = _from_x(x, lo, hi)
        lp = p_init.with_vector(names, th)
        pt = per_trial_loglik_cell(lp, tr)
        if pt is None:
            return 1e12
        val = -float(np.sum(pt))
        return val if np.isfinite(val) else 1e12

    best = None
    n_ok = 0
    rng = np.random.default_rng(seed)
    for k in range(max(1, n_restart)):
        if k == 0:
            x0 = _to_x(theta0, lo, hi)
        else:
            x0 = _x_bounds(names) + rng.uniform(-1.5, 1.5, size=len(names))
        res = minimize(negll, x0, method="L-BFGS-B",
                       options={"maxiter": maxiter, "maxfun": maxfun,
                                "gtol": gtol, "ftol": ftol})
        if np.isfinite(res.fun):
            n_ok += 1
            if best is None or res.fun < best.fun:
                best = res

    if best is None:
        return {"params": p_init, "loglik": -np.inf, "x": None,
                "success": False, "nfev": 0, "n_starts_ok": 0, "names": names}

    th = _from_x(best.x, lo, hi)
    out = p_init.with_vector(names, th)
    return {"params": out, "loglik": -float(best.fun), "x": best.x,
            "success": bool(-best.fun < 1e11), "nfev": int(best.nfev),
            "n_starts_ok": int(n_ok), "names": names}


def numerical_hessian_cell(tr: dict, names, p: CellParams,
                           bounds_override: dict | None = None,
                           rel_step: float = 1e-3):
    """参数坐标下的数值 Hessian（logit 化后再变回参数坐标）。"""
    names = list(names)
    lo, hi = _bounds_for(names, bounds_override)
    x0 = _to_x(p.vector(names), lo, hi)
    n = x0.size

    def f(x):
        lp = p.with_vector(names, _from_x(x, lo, hi))
        pt = per_trial_loglik_cell(lp, tr)
        return 1e12 if pt is None else -float(np.sum(pt))

    h = rel_step * np.maximum(np.abs(x0), 1.0)
    H = np.zeros((n, n))
    f0 = f(x0)
    for i in range(n):
        for j in range(i, n):
            xpp = x0.copy(); xpp[i] += h[i]; xpp[j] += h[j]
            xpm = x0.copy(); xpm[i] += h[i]; xpm[j] -= h[j]
            xmp = x0.copy(); xmp[i] -= h[i]; xmp[j] += h[j]
            xmm = x0.copy(); xmm[i] -= h[i]; xmm[j] -= h[j]
            H[i, j] = H[j, i] = (f(xpp) - f(xpm) - f(xmp) + f(xmm)) / (4 * h[i] * h[j])
    return H, x0, lo, hi, f0
