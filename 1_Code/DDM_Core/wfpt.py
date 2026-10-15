# -*- coding: utf-8 -*-
"""
wfpt.py —— Wiener 首次通过时间（WFPT）密度、存活函数与抽样
==========================================================
Stage 2 的核心数值模块。不依赖 pyddm / hddm（本机未安装），自实现并**自验证**。

模型约定（与 `Exp_Design_Formal.m` 及研究计划一致）
--------------------------------------------------
    dX_t = v·dt + dB_t,        X_0 = z,        0 < z < a

* ``v``  ：有符号漂移率（σ = 1 固定，即设定模型尺度）
* ``a``  ：上下边界间距（下边界 0、上边界 a）
* ``z``  ：**绝对**起点（0 < z < a）。中心起点 = a/2（研究计划第一版约定）
* 反应编码：上边界 = Match，下边界 = Nonmatch
* 观测 RT = 首次通过时间 τ + 非决策时间 t0

密度公式（由 Fokker–Planck 通量导出，见 `validate_wfpt.py` 的数值验证）
--------------------------------------------------------------------
    令 d = a − z（到上边界的距离），
    f_upper(t) = (π/a²)·exp(+v·d − v²t/2)·Σ_{k≥1} k·sin(kπd/a)·exp(−k²π²t/(2a²))
    令 d = z（到下边界的距离），把 v 换成 −v：
    f_lower(t) = (π/a²)·exp(−v·z − v²t/2)·Σ_{k≥1} k·sin(kπz/a)·exp(−k²π²t/(2a²))

两条式子结构相同，故实现为一个 ``_flux(d, v, a, t)``。

**独立校验**（不依赖本式）：吸收概率有闭式解
    P(上边界) = (1 − e^{−2vz}) / (1 − e^{−2va})
``validate_wfpt.py`` 用它检查 ∫f_upper dt 是否等于该值——这是一条与本公式
相互独立的判据（推导路径不同），能抓住符号/系数错误。

数值注意（2026-10-14 修正）
--------------------------
正弦级数在 **t 很小** 时不仅收敛慢（需要 k ≈ a/(π√t) 项），而且**灾难性相消**：
级数各项幅值 O(k)，而 t→0 时真值指数级小 ⇒ 真值一旦落到相消地板（≈ kmax·eps）
以下，返回值就是双精度噪声、**符号随机**（实测 −7.77e−14 / +6.01e−16 / −8.23e−15），
而 `likelihood.per_trial_loglik` 的 `np.any(f <= 0)` 守卫会因此把**整份**数据判成 None。

因此 `flux` 现在有**两条互为对偶**的级数，按 t 选分支：
正弦级数（大 t）与**镜像/反射级数**（小 t，由同一特征函数展开经 Poisson 求和互换得到）。
小 t 一侧现在是**正数且准确**的，不再需要绕开 t 的小值。

⚠️ 仍然存在的两处"绕开小 t"的**遗留**工作区（本次未改，见 README §9 第 29 项）：
`_T_FLOOR`（数值积分网格下端）与 `_S_FLOOR`（两阶段模型在 t ∈ (T, T+1e-3] 用阶段 1
公式替代）。它们是在只有正弦级数时打的补丁，现在**具备了重新论证的条件**，
但改动会影响已验收的两阶段/ρ 检验力结果，必须作为独立的、带回归验证的改动来做。
"""
from __future__ import annotations

import numpy as np

__all__ = ["flux", "density", "p_upper", "survival", "survival_series",
           "wfpt_cdf_grid", "sample_wfpt", "simulate",
           "green", "density_step", "survival_step", "p_upper_step", "sample_step"]

_TOL = 1e-15
_KMAX_HARD = 4000

#: 镜像级数（`_flux_dual`）的指数截断：exp(−x) 在 x ≳ 700 时下溢为 0，
#: 故只需保留满足 (d+2na)²/(2t) ≤ _LOG_CUT 的镜像项。
_LOG_CUT = 700.0

#: 数值积分网格的**最小时间**（秒）。正弦级数在 t→0 时收敛极慢
#: （需要 k ≈ a/(π√t) 项），若网格从 t=0 起，`_k_max` 会直接撞上硬上限，
#: 使每次网格构建慢 20–30 倍。τ < 0.1 ms 的密度对 RT（= t0 + τ，t0 ≥ 0.05 s）
#: 毫无意义，故把网格下端截到 1e-4 s。
_T_FLOOR = 1e-4


def _time_grid(t_max: float, n_grid: int, power: float, t_floor: float = _T_FLOOR):
    """偏向 0 端的积分网格；``t[0] = 0``，其余自 ``t_floor`` 起。"""
    u = (np.arange(n_grid + 1) / n_grid) ** power
    t = t_floor + (t_max - t_floor) * u
    t[0] = 0.0
    return t


def _k_max(t_min: float, a: float, tol: float = _TOL) -> int:
    """让 exp(−k²π²t/(2a²)) < tol 所需的最小 k（对最小的 t）。"""
    if t_min <= 0:
        return _KMAX_HARD
    lam = (np.pi / a) ** 2 / 2.0
    k = np.sqrt(np.log(1.0 / tol) / (lam * t_min)) + 2.0
    return int(min(max(k, 8), _KMAX_HARD))


def _flux_series(d, v, a, t, tol: float = _TOL):
    """正弦（特征函数）级数分支：``t`` 较大时快且准。见 `flux` 的说明。"""
    a_safe = np.maximum(a, 1e-12)
    kmax = _k_max(float(np.min(t)), float(np.max(a_safe)), tol)
    lam = (np.pi / a_safe) ** 2 / 2.0

    s = np.zeros_like(t)
    for k in range(1, kmax + 1):
        w = np.exp(-(k * k) * lam * t)
        if not np.any(w > tol):
            break
        s += k * np.sin(k * np.pi * d / a_safe) * w

    return (np.pi / a_safe**2) * np.exp(v * d - 0.5 * v * v * t) * s


def _flux_dual(d, v, a, t):
    """镜像（反射）级数分支：``t`` 很小时快且准。见 `flux` 的说明。"""
    a_safe = np.maximum(a, 1e-12)
    # 只需保留 |d + 2na| ≲ sqrt(2·t·_LOG_CUT) 的镜像项，其余 exp 下溢为 0。
    span = np.sqrt(2.0 * t * _LOG_CUT)
    n_max = int(np.max((span + a_safe) / (2.0 * a_safe))) + 1

    s = np.zeros_like(t)
    for n in range(-n_max, n_max + 1):
        img = d + 2.0 * n * a_safe
        e = np.exp(-(img * img) / (2.0 * t))
        if not np.any(e > 0.0):
            continue
        s += img * e

    pre = 1.0 / (np.sqrt(2.0) * np.sqrt(np.pi) * t**1.5)
    return pre * np.exp(v * d - 0.5 * v * v * t) * s


def flux(d, v, a, t, tol: float = _TOL):
    """单个吸收边界的首次通过密度：边界距起点 ``d``，漂移 ``v``，边界间距 ``a``。

    四个参数**均可广播**（``a`` 支持逐试次数组，Stage 3 的似然需要）。
    返回与广播形状一致的数组。

    实现：同一个特征函数展开有**两条互为 Poisson 对偶**的级数，按 ``t`` 选分支 ——

    * ``t ≥ a·d_min/π``（``d_min = min(d, 2a − d)``）→ 正弦级数 `_flux_series`
    * ``t <  a·d_min/π``                            → 镜像级数 `_flux_dual`

    交叉点取两条级数「首项衰减率相等」之处（``π²t/(2a²) = d_min²/(2t)``）：
    两支在该点附近都只有几个有效项、且互相吻合到 ~1e-12
    （`_scratch/check_flux_smallt.py` 的 V1/V2）。镜像级数由
    ``Σ_{k≥1} k·sin(kx)·e^{−k²θ}`` 经 Poisson 求和（对 ``x`` 求导）得到：

        f(t) = e^{v·d − v²t/2} / (√2·√π·t^{3/2}) · Σ_{n∈ℤ} (d + 2na)·e^{−(d+2na)²/(2t)}

    它的独立校验是一条**解析积分恒等式**（``v > 0`` 时逐项积分合法；``v < 0`` 时把
    漂移反号、等价于对另一条边界陈述，故不作逐项求和）：
    ``∫_0^∞ f dt = e^{v·d}·Σ_n sgn(d+2na)·e^{−v|d+2na|} = (1 − e^{−2v(a−d)})/(1 − e^{−2va})``
    （末一步是几何级数求和）``= p_upper(v, a, a−d)`` —— 与正弦级数的积分恒等式
    推导路径不同，故互为独立判据。

    ⚠️ 2026-10-14 修正：此前只有正弦级数一条分支，``t`` 小到真值落进相消地板
    （≈ kmax·eps）以下时返回**符号随机**的双精度噪声（实测 −7.77e−14 /
    +6.01e−16 / −8.23e−15），被 `likelihood.per_trial_loglik` 的
    ``np.any(f <= 0)`` 守卫放大成「**整份**数据判 None」。
    """
    d = np.asarray(d, dtype=float)
    v = np.asarray(v, dtype=float)
    a = np.asarray(a, dtype=float)
    t = np.asarray(t, dtype=float)
    shape = np.broadcast_shapes(d.shape, v.shape, a.shape, t.shape)
    d = np.broadcast_to(d, shape).astype(float)
    v = np.broadcast_to(v, shape).astype(float)
    a = np.broadcast_to(a, shape).astype(float)
    t = np.broadcast_to(t, shape).astype(float)

    out = np.zeros(shape, dtype=float)
    pos = t > 0
    if not np.any(pos):
        return out

    a_safe = np.maximum(a, 1e-12)
    d_min = np.minimum(np.abs(d), np.abs(2.0 * a_safe - d))
    small = np.zeros(shape, dtype=bool)
    small[pos] = t[pos] < (a_safe[pos] * d_min[pos] / np.pi)   # t 太小 ⇒ 镜像级数

    if np.any(small):
        out[small] = _flux_dual(d[small], v[small], a[small], t[small])
    big = pos & ~small
    if np.any(big):
        out[big] = _flux_series(d[big], v[big], a[big], t[big], tol)
    return out


def density(t, v, a, z):
    """返回 ``(f_upper, f_lower)``：上/下边界的首次通过密度。"""
    a = float(a)
    z = np.asarray(z, dtype=float)
    f_up = flux(a - z, v, a, t)
    f_lo = flux(z, -np.asarray(v, dtype=float), a, t)
    return f_up, f_lo


def p_upper(v, a, z):
    """P(先到上边界)——闭式解，与密度公式相互独立。"""
    v = np.asarray(v, dtype=float)
    a = float(a)
    z = np.asarray(z, dtype=float)
    out = np.empty(np.broadcast_shapes(v.shape, z.shape), dtype=float)
    vv, zz = np.broadcast_arrays(v, z)
    small = np.abs(vv) < 1e-9
    out[small] = zz[small] / a                      # v→0 的极限
    big = ~small
    out[big] = (1.0 - np.exp(-2.0 * vv[big] * zz[big])) / (1.0 - np.exp(-2.0 * vv[big] * a))
    return out


def wfpt_cdf_grid(v, a, z, t_max: float, n_grid: int = 4000, power: float = 2.0):
    """在 ``[0, t_max]`` 上数值积分密度，返回 (t_grid, F_upper, F_lower)。

    网格偏向 0 端（``t = t_floor + (t_max−t_floor)·u**power``），因为 τ 的密度在
    0 附近变化最快；下端截到 ``_T_FLOOR``，避免正弦级数在 t→0 时收敛极慢。
    """
    a = float(a)
    t = _time_grid(t_max, n_grid, power)
    f_up, f_lo = density(t, v, a, z)
    # 复合梯形（非均匀网格）
    dt = np.diff(t)
    F_up = np.concatenate([[0.0], np.cumsum(0.5 * (f_up[1:] + f_up[:-1]) * dt)])
    F_lo = np.concatenate([[0.0], np.cumsum(0.5 * (f_lo[1:] + f_lo[:-1]) * dt)])
    return t, F_up, F_lo


def survival(t, v, a, z, n_grid: int = 4000, power: float = 2.0):
    """P(τ > t) = 1 − F_upper(t) − F_lower(t)。标量或一维数组的 t 皆可。"""
    t = np.atleast_1d(np.asarray(t, dtype=float))
    out = np.empty_like(t)
    for i, ti in enumerate(t):
        if ti <= 0:
            out[i] = 1.0
            continue
        tg, F_up, F_lo = wfpt_cdf_grid(v, a, z, float(ti), n_grid=n_grid, power=power)
        out[i] = 1.0 - float(F_up[-1] + F_lo[-1])
    return out if out.size > 1 else float(out[0])


def survival_series(v, a, z, t, tol: float = _TOL):
    """**解析**存活函数 P(τ > t)，用于 deadline 未响应项（比数值积分快一个量级）。

    推导：把 killed 转移密度 ``p_v(x,t)`` 对 x 在 [0, a] 上积分，
    利用 ∫_0^a sin(kπx/a)·e^{vx} dx = (kπ/a)·(1 − (−1)^k e^{va}) / (v² + (kπ/a)²)，得

        P(τ>t) = (2/a)·e^{−vz − v²t/2}·Σ_{k≥1} sin(kπz/a)·exp(−k²π²t/(2a²))
                 · (kπ/a)·(1 − (−1)^k·e^{va}) / (v² + (kπ/a)²)

    v = 0 时退化为 (4/π)·Σ_{k 奇} sin(kπz/a)·exp(−k²π²t/(2a²))/k，
    在 t→0, z=a/2 时等于 (4/π)(1−1/3+1/5−…) = 1 ✅（解析自检）。
    `validate_wfpt.py` 的 V6 另用数值积分做独立校验。
    """
    v = np.asarray(v, dtype=float)
    a = np.asarray(a, dtype=float)
    z = np.asarray(z, dtype=float)
    t = np.asarray(t, dtype=float)
    shape = np.broadcast_shapes(v.shape, a.shape, z.shape, t.shape)
    v = np.broadcast_to(v, shape).astype(float)
    a = np.broadcast_to(a, shape).astype(float)
    z = np.broadcast_to(z, shape).astype(float)
    t = np.broadcast_to(t, shape).astype(float)

    out = np.ones(shape, dtype=float)
    pos = t > 0
    if not np.any(pos):
        return out

    t_b, v_b, a_b, z_b = t[pos], v[pos], a[pos], z[pos]
    a_safe = np.maximum(a_b, 1e-12)
    kmax = _k_max(float(np.min(t_b)), float(np.max(a_safe)), tol)
    lam = (np.pi / a_safe) ** 2 / 2.0
    kpi_a = np.pi / a_safe

    s = np.zeros_like(t_b)
    for k in range(1, kmax + 1):
        w = np.exp(-(k * k) * lam * t_b)
        if not np.any(w > tol):
            break
        kk = float(k)
        coef = (kk * kpi_a) * (1.0 - ((-1.0) ** k) * np.exp(v_b * a_safe)) / (
            v_b**2 + (kk * kpi_a) ** 2
        )
        s += np.sin(kk * np.pi * z_b / a_safe) * w * coef

    out[pos] = (2.0 / a_safe) * np.exp(-v_b * z_b - 0.5 * v_b**2 * t_b) * s
    return out


# ===========================================================================
# 两阶段漂移（M-T1）：刺激在 t = T 被掩蔽，漂移由 v1 变为 v2
# ===========================================================================
# 决策 D5 之后的正式模型。关键工具是 **killed 转移密度**（Green 函数）
# G(x, T; z)：漂移 v1、边界 0/a 吸收、起点 z 时，存活到 T 且落在 x 的密度。
# 有了它，两阶段模型的首次通过密度就是一次卷积：
#     f(t) = ∫_0^a G(x, T; z) · f_{v2}(t − T; 从 x 出发) dx        (t ≥ T)
# 存活概率则可解析地写成
#     P(τ > t) = ∫_0^a G(x, T; z) · S_{v2}(t − T; 从 x 出发) dx
# 完全不需要路径模拟 ⇒ 两阶段预测是**精确**的，可直接用于模型判别力比较。

#: x 积分网格距边界的相对留白（避免落在吸收点上）
_X_EPS = 1e-6

#: 阶段 2 的**有效起点下限**（秒）。正弦级数在 ``t < 1e-3`` 会出现灾难性相消
#: （密度本应≈0，截断级数却给出 O(1) 的 Gibbs 振荡），把这类格点积进去会产生
#: **与参数无关的固定质量亏损**（本模块开发期实测：9 个设计里恒定丢 0.0155）。
#: 因此 ``t ∈ (T, T + _S_FLOOR]`` 一律按**阶段 1** 的单阶段公式计算——
#: 掩蔽后 1 ms 内两阶段密度之差是 O(_S_FLOOR)，远低于任何 RT 分辨率。
_S_FLOOR = 1e-3


def _x_grid(a: float, n_x: int):
    return np.linspace(_X_EPS * a, (1.0 - _X_EPS) * a, n_x)


def green(x, T: float, v: float, a: float, z: float, tol: float = _TOL):
    """killed 转移密度 ``G(x, T; z)``（漂移 ``v``、边界 ``0/a`` 吸收）。

        p^{(v)}(x,T|z) = e^{v(x−z) − v²T/2} · p^{(0)}(x,T|z)
        p^{(0)}(x,T|z) = (2/a)·Σ_{k≥1} sin(kπz/a)·sin(kπx/a)·exp(−k²π²T/(2a²))

    漂移项来自 Girsanov（**吸收时刻是路径性质**，不随测度变换改变），
    与 `survival_series` 对 x 积分所用的形式一致——两者是同一密度的
    不同用法，互为校验（`validate_step.py` 的 W3）。

    ``x`` 为数组，其余为标量；返回与 ``x`` 同形状的数组。
    ∫_0^a G dx = P(存活到 T)。

    ``T <= _T_FLOOR`` 时正弦级数在 ``t→0`` 处未收敛（kmax 撞上限、Gibbs 振荡
    使 ``∫G dx`` 偏离 1 数个量级），此时**必须**退化为离散 δ：在 ``z`` 处放
    单位质量，权重用 ``np.gradient`` 使 ``Σ G·grad = 1`` 精确成立（内点放
    ``1/grad``；边界点的 grad 是半格宽，因此会放 ``2/dx``——这正是为了让
    梯形积分归一到 1）。``T→0`` 时过程几乎不动，δ 是 O(T) 精度。
    """
    x = np.asarray(x, dtype=float)
    a = float(a)
    z = float(z)
    v = float(v)
    T = float(T)
    if T <= _T_FLOOR:
        out = np.zeros_like(x)
        w = np.gradient(x)
        # 线性（cloud-in-cell）分配而不是单点 δ：单点 δ 只能落在格点上，
        # 起点 z 偏离最近格点 O(dx) 会让后续密度在**错误的起点**上求值
        # （开发期实测 a=1.5,z=0.4 偏差 4e-3）。把单位质量按插值权重分给相邻
        # 两点可同时精确保持 ∫G dx = 1 与 ∫x·G dx = z，误差降到 O(dx²)。
        j = int(np.clip(np.searchsorted(x, z) - 1, 0, x.size - 2))
        x0, x1 = float(x[j]), float(x[j + 1])
        frac = 0.0 if x1 <= x0 else float(np.clip((z - x0) / (x1 - x0), 0.0, 1.0))
        out[j] = (1.0 - frac) / max(float(w[j]), 1e-12)
        out[j + 1] = frac / max(float(w[j + 1]), 1e-12)
        return out
    a_safe = max(a, 1e-12)
    kmax = _k_max(T, a_safe, tol)
    lam = (np.pi / a_safe) ** 2 / 2.0
    s = np.zeros_like(x)
    for k in range(1, kmax + 1):
        w = float(np.exp(-(k * k) * lam * T))
        if w <= tol:
            break
        s += np.sin(k * np.pi * z / a_safe) * np.sin(k * np.pi * x / a_safe) * w
    return (2.0 / a_safe) * np.exp(v * (x - z) - 0.5 * v * v * T) * s


def density_step(t, v1: float, v2: float, a: float, z: float, T: float,
                 n_x: int = 161, tol: float = _TOL):
    """两阶段漂移的首次通过密度 ``(f_upper, f_lower)``。

    阶段 1（``0 ≤ s < T``）：漂移 ``v1``；阶段 2（``s ≥ T``）：漂移 ``v2``。
    边界与起点在两阶段中保持恒定。

    * ``t ≤ T + _S_FLOOR`` 直接退化为单阶段 ``flux``（密度在 ``T`` 处连续）；
    * ``t > T + _S_FLOOR`` 用 Green 卷积。

    ⚠️ 阶段 2 的积分区间**必须**从 ``_S_FLOOR``（1 ms）起算，不能从 ``_T_FLOOR``
    起算：``s ≲ 1e-3`` 时截断正弦级数因灾难性相消给出 O(1) 的假密度，被梯形
    权重积进去会制造**与参数无关的固定质量亏损**（开发期实测恒定 0.0155，
    见 `validate_step.py` 的 W4）。改用阶段 1 公式的代价是 O(1 ms) 的密度误差，
    远低于任何 RT 分辨率。
    """
    t = np.atleast_1d(np.asarray(t, dtype=float))
    a = float(a)
    z = float(z)
    T = float(T)
    f_up = np.zeros_like(t)
    f_lo = np.zeros_like(t)

    pre = t <= T + _S_FLOOR
    if np.any(pre):
        tp = t[pre]
        f_up[pre] = flux(a - z, v1, a, tp)
        f_lo[pre] = flux(z, -v1, a, tp)

    post = ~pre
    if np.any(post):
        s = np.maximum(t[post] - T, _S_FLOOR)
        xs = _x_grid(a, n_x)
        G = green(xs, T, v1, a, z, tol)
        w = np.gradient(xs)
        # 上边界：起点 x 到 a 的距离 = a − x，等效漂移 v2
        FU = flux(a - xs[None, :], v2, a, s[:, None])
        # 下边界：起点 x 到 0 的距离 = x，等效漂移 −v2
        FL = flux(xs[None, :], -v2, a, s[:, None])
        g = (G * w)[None, :]
        f_up[post] = np.sum(FU * g, axis=1)
        f_lo[post] = np.sum(FL * g, axis=1)
    return f_up, f_lo


def survival_step(v1: float, v2: float, a: float, z: float, T: float, t,
                  n_x: int = 161, tol: float = _TOL):
    """两阶段漂移的存活概率 ``P(τ > t)``——**解析**，无时间积分。

    * ``t ≤ T + _S_FLOOR``：``survival_series(v1, a, z, t)``；
    * ``t > T + _S_FLOOR``：``∫_0^a G(x,T;z,v1)·survival_series(v2, a, x, t−T) dx``。

    ``t`` 可为标量或一维数组。该式用于 deadline 未响应项，是 M-T1 似然的核心。
    ``_S_FLOOR`` 的取值理由同 `density_step`（避开 ``s→0`` 的级数相消区）。
    """
    t = np.atleast_1d(np.asarray(t, dtype=float))
    a = float(a)
    z = float(z)
    T = float(T)
    out = np.ones_like(t)

    pre = (t > 0) & (t <= T + _S_FLOOR)
    if np.any(pre):
        out[pre] = survival_series(v1, a, z, t[pre])

    post = t > T + _S_FLOOR
    if np.any(post):
        s = np.maximum(t[post] - T, _S_FLOOR)
        xs = _x_grid(a, n_x)
        G = green(xs, T, v1, a, z, tol)
        w = np.gradient(xs)
        # (n_t, n_x)：从每个 x 出发、漂移 v2、剩余时间 s 的存活概率
        S = survival_series(v2, a, xs[None, :], s[:, None])
        out[post] = np.sum(S * (G * w)[None, :], axis=1)
    return out if out.size > 1 else float(out[0])


def p_upper_step(v1: float, v2: float, a: float, z: float, T: float,
                 n_x: int = 161, tol: float = _TOL) -> float:
    """两阶段漂移下**最终**到达上边界（Match）的概率。

    推导：``P(上) = P(v1 下在 T 前到上) + ∫_0^a G(x,T)·P_{v2}(上|x) dx``，
    而 ``P(v1 下在 T 前到上) = p_upper(v1,a,z) − ∫_0^a G(x,T)·P_{v1}(上|x) dx``，
    两式相消得

        P(上) = p_upper(v1, a, z) + ∫_0^a G(x,T;z,v1)·[P_{v2}(上|x) − P_{v1}(上|x)] dx

    ``v1 == v2`` 时退化为闭式 ``p_upper``（`validate_step.py` 的 W1）。
    """
    if T <= 0:
        return float(p_upper(v2, a, z))
    a = float(a)
    z = float(z)
    xs = _x_grid(a, n_x)
    G = green(xs, T, v1, a, z, tol)
    w = np.gradient(xs)
    d = p_upper(v2, a, xs) - p_upper(v1, a, xs)
    return float(p_upper(v1, a, z) + np.sum(G * d * w))


def sample_step(v1: float, v2: float, a: float, z: float, T: float,
                n: int, rng: np.random.Generator,
                t_max: float | None = None, n_grid: int = 3000):
    """从**两阶段漂移**（``t ≤ T`` 用 ``v1``，``t > T`` 用 ``v2``）抽 ``n`` 个 (τ, boundary)。

    与 `sample_wfpt` 同构：先用 `p_upper_step` 抽边界，再对该边界的**条件 CDF**
    做逆变换；条件 CDF 由 `density_step` 在时间网格上积分得到。
    超出 ``t_max`` 的样本以 ``tau = inf`` 返回。

    ⚠️ 时间网格用**均匀**细网格而非 `_time_grid` 的幂网格：密度在 ``t = T`` 处
    有折点，幂网格会在低 t 端过疏、跨过折点。建议显式传 ``t_max``
    （= 实验 deadline + 余量），否则自动值可能到 24 s 使 dt 粗到 4 ms。
    """
    a = float(a)
    z = float(z)
    T = float(T)
    if t_max is None:
        rate = max(abs(float(v1)), abs(float(v2)), 1e-3)
        t_max = float(min(max(6.0 * a * a, 8.0 * a / rate), 120.0))
    t_max = float(t_max)

    if T <= 0:                                   # 退化：单阶段，直接交给闭式抽样
        return sample_wfpt(v2, a, z, n, rng, t_max=t_max)

    p_up = float(p_upper_step(v1, v2, a, z, T))
    b = (rng.random(n) < p_up).astype(int)
    out_tau = np.full(n, np.inf)

    n_grid = max(int(n_grid), 2)
    dt = t_max / n_grid
    tg = np.arange(1, n_grid + 1) * dt
    f_up, f_lo = density_step(tg, v1, v2, a, z, T)

    for is_upper in (True, False):
        idx = np.flatnonzero(b == 1) if is_upper else np.flatnonzero(b == 0)
        if idx.size == 0:
            continue
        p_side = p_up if is_upper else (1.0 - p_up)
        f = f_up if is_upper else f_lo
        # 累积梯形（f(0) = 0，故首项为 0.5·f[0]·t[0]）
        dtg = np.diff(tg, prepend=0.0)
        F = np.cumsum(0.5 * (f + np.concatenate([[0.0], f[:-1]])) * dtg)
        F_cond = F / max(p_side, 1e-300)
        reach = float(F_cond[-1])
        u = rng.random(idx.size)
        tau = np.interp(np.minimum(u, reach), F_cond, tg)
        tau[u > reach] = np.inf
        out_tau[idx] = tau
    return out_tau, b


def _flux_cdf(d, v, a, t_max: float, n_grid: int = 4000, power: float = 2.0):
    """直接对 ``flux(d, v, a, ·)`` 积分得到 CDF（网格偏向 0 端）。

    ⚠️ 不要用 `wfpt_cdf_grid` 代替：后者的参数是 (v, a, z)，内部会做
    ``z → a−z`` 的映射；在抽样里我们手里拿的已经是**距离** d，混用会导致
    上边界用了错误的距离（本模块开发期踩过一次）。
    """
    t = _time_grid(t_max, n_grid, power)
    f = flux(d, v, a, t)
    dt = np.diff(t)
    F = np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * dt)])
    return t, F


def sample_wfpt(v, a, z, n: int, rng: np.random.Generator,
                t_max: float | None = None, n_grid: int = 8000):
    """从 WFPT 抽样 ``n`` 个 (τ, boundary)。

    boundary = 1（上边界/Match）或 0（下边界/Nonmatch）。
    做法：先用闭式解抽边界，再对**该边界的条件 CDF** 做逆变换。

    返回 (tau, boundary)；超出 ``t_max`` 的样本以 ``tau = inf`` 返回。
    """
    a = float(a)
    if t_max is None:
        rate = max(abs(float(v)), 1e-3)
        t_max = float(min(max(6.0 * a * a, 8.0 * a / rate), 120.0))

    p_up = float(p_upper(v, a, z))
    b = (rng.random(n) < p_up).astype(int)
    out_tau = np.full(n, np.inf)

    for is_upper in (True, False):
        idx = np.flatnonzero(b == 1) if is_upper else np.flatnonzero(b == 0)
        if idx.size == 0:
            continue
        d = (a - z) if is_upper else z          # 到目标边界的距离
        vv = v if is_upper else -v              # 该边界的等效漂移
        p_side = p_up if is_upper else (1.0 - p_up)
        tg, F_raw = _flux_cdf(d, vv, a, t_max, n_grid=n_grid)
        F_cond = F_raw / max(p_side, 1e-300)    # 条件 CDF（总质量 → 1）
        reach = float(F_cond[-1])               # 网格截断处已覆盖的条件概率
        u = rng.random(idx.size)
        tau = np.interp(np.minimum(u, reach), F_cond, tg)
        tau[u > reach] = np.inf                 # 超出 t_max 的尾巴
        out_tau[idx] = tau
    return out_tau, b


def simulate(v, a, z, t0, deadline, n_trials: int, rng: np.random.Generator,
             t_max: float | None = None):
    """生成一批试次的观测数据（含 deadline 未响应）。

    Returns
    -------
    dict: rt（秒，未响应为 NaN）、response（1 上 / 0 下）、omission（0/1）
    """
    tau, b = sample_wfpt(v, a, z, n_trials, rng, t_max=t_max)
    rt = tau + float(t0)
    omission = (~np.isfinite(rt)) | (rt > deadline)
    rt = np.where(omission, np.nan, rt)
    response = np.where(omission, 0, b)
    return {"rt": rt, "response": response.astype(int), "omission": omission.astype(int)}
