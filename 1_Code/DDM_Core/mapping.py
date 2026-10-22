# -*- coding: utf-8 -*-
"""
mapping.py —— 实验设计 (P, T, W, 身份, 匹配性) → DDM 参数（Stage 3）
=====================================================================
第一版映射，采用研究计划 §9/§11 的建议结构，并做了**参考点锚定**重参数化。

映射
----
    f_P(P) = 1 − exp(−P/τ_P)                        练习饱和（P=0 → 0）
    Q_T(X) = 1 − exp(−X/τ)                          时间饱和

    d(P,T) = d_ref + β_P·[f_P(P) − f_P(P_ref)]
                   + β_T·[Q_T(T) − Q_T(T_ref)]
                   + I_self·{ β_S + β_SP·[f_P(P)−f_P(P_ref)]
                                  + β_ST·[Q_T(T)−Q_T(T_ref)] }

    a(W)   = a_ref + Δa·[Q_T(W) − Q_T(W_ref)]       （W1 静态指数边界）
    a(W)   = a_ref                                   （W0 固定边界）

    v = +d（匹配试次，正确答案 = Match = 上边界）
    v = −d（不匹配试次，正确答案 = Nonmatch = 下边界）
    z = (z_ratio + I_self·dz_S) · a                 起点（判据通道，2026-10-22）

⚠️ **为什么必须做参考点锚定**（2026-10-13 的实测教训）
-----------------------------------------------------
初版把参数写成 ``d0``（T→0 处的漂移）与 ``A_min``（W→0 处的边界）。但设计的
T ∈ [33, 250] ms、W ∈ [800, 1800] ms，**数据从不接近 T=0 或 W=0**，于是这两个
"截距"参数是**纯外推**，MLE 直接把它们推到边界上，并带偏其余参数
（实测：`d0` 估计 0.05 vs 真值 0.80；`A_min` 估计 0.30 vs 真值 0.90；`tau_T` 0.025 vs 0.080）。

改为在**设计范围内的参考点**（`P_ref, T_ref, W_ref`）上锚定后，
`d_ref / a_ref / β_S` 都是**可直接解释的域内量**，不再外推。

⚠️ **为什么是加法而不是旧代码的 `v_P × v_T × (1+α)`**（见工作流主计划 §5 D4 D9 的推导）
1. 乘法结构所有分量 ∈ (0,1)，**产生不了负 drift**；实测 `v_base` 从 −1.81 到 +2.68；
2. 乘法结构下似然里只有比值 `(1+α₁)/(1+α₂)` 进入，**α 与 v_P 混叠不可识别**
   （反推逐条件所需 α₁−α₂ 在 −0.16 ~ +0.69 之间变化，而模型要求它是常数）。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, fields, replace

import numpy as np

__all__ = [
    "MappingParams", "W_MODELS", "SHAPE_MODELS", "WITHIN_FREE", "WITHIN_FREE_LIN",
    "BETWEEN_FREE", "PARAM_BOUNDS",
    "f_P", "Q_T", "drift_magnitude", "boundary_a", "trial_params",
    "match_lin_to_exp",
]

W_MODELS = ("W0", "W1")

#: T 通路（以及 W 通路）的形状函数族：
#:  * ``"exp"`` —— ``1 − exp(−X/τ)``，带**自由时标** τ（原实现）；
#:  * ``"lin"`` —— ``X − X_ref``，**无时标**，斜率即 ``beta_T`` / ``delta_a``。
#: 见 D18/D19：``tau_T``/``tau_a`` 在本设计上不可识别（``tau_a`` 被推到上界、
#: ``tau_T`` 跨数据集方向相反），因此需要一个不含时标的可选参数化。
SHAPE_MODELS = ("exp", "lin")

# 被试**内**可识别的参数（T、W 被试内变化；P 固定）
#: 2026-10-22 增加 ``dz_S``（起点通道的自我偏移，见 `MappingParams.dz_S`）：
#: exp 形状下 9 → 10 个，lin 形状下 7 → 8 个。``dz_S`` 是**被试内**对比
#: （同一被试的自我 vs 他人试次），因此进被试层，不进 `BETWEEN_FREE`。
WITHIN_FREE = ["d_ref", "beta_T", "tau_T", "beta_S", "beta_ST",
               "a_ref", "delta_a", "tau_a", "t0", "dz_S"]

# ``shape_model="lin"`` 时的被试内自由参数：**τ_T 与 τ_a 不复存在**（8 个）。
WITHIN_FREE_LIN = ["d_ref", "beta_T", "beta_S", "beta_ST",
                   "a_ref", "delta_a", "t0", "dz_S"]

# 只有**跨被试**（P 的被试间变化）才能识别的参数
BETWEEN_FREE = ["beta_P", "tau_P", "beta_SP"]

PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "d_ref":     (0.20, 6.0),
    "beta_P":    (-6.0, 8.0),
    "tau_P":     (1.0, 200.0),
    "beta_T":    (-6.0, 8.0),
    "tau_T":     (0.005, 0.60),
    "beta_S":    (-2.0, 2.0),
    "beta_SP":   (-4.0, 4.0),
    "beta_ST":   (-4.0, 4.0),
    "a_ref":     (0.30, 5.0),
    "delta_a":   (-3.0, 3.0),
    "tau_a":     (0.05, 5.0),
    "t0":        (0.05, 0.60),
    #: 起点相对偏移（以 ``a`` 为单位）。上下限 ±0.45 与 ``z_ratio = 0.50`` 配合，
    #: 保证 ``z_self/a ∈ [0.05, 0.95]``，即起点永远严格落在两边界之间。
    "dz_S":      (-0.45, 0.45),
}


@dataclass
class MappingParams:
    """映射参数。默认值只用于初始化，**不代表真值**。"""

    # --- 参考点（域内锚定，不参与优化；由设计决定）---
    P_ref: float = 30.0        # 练习参考点（次）
    T_ref: float = 0.10        # 刺激呈现参考点（秒）
    W_ref: float = 1.20        # 期限参考点（秒）

    # --- P/T → drift 幅度 ---
    d_ref: float = 1.60        # 在 (P_ref, T_ref) 处的 drift 幅度
    beta_P: float = 1.50
    tau_P: float = 30.0
    beta_T: float = 1.20
    tau_T: float = 0.080

    #: 形状函数族。``"exp"`` 用 ``1 − exp(−X/τ)``（带自由时标，原实现）；
    #: ``"lin"`` 用 ``X − X_ref``（**无时标**，D18/D19 的处方）。
    #: ``"lin"`` 时 ``tau_T`` / ``tau_a`` 被忽略，自由参数集改用 `WITHIN_FREE_LIN`。
    shape_model: str = "exp"

    # --- 身份（自我）加性项（β_S 为参考点处的自我效应）---
    beta_S: float = 0.35
    beta_SP: float = 0.0
    beta_ST: float = 0.25

    # --- W → 边界 ---
    w_model: str = "W1"
    a_ref: float = 1.80        # 在 W_ref 处的边界间距
    delta_a: float = 0.30      # W 对边界的函数幅度（可正可负）
    tau_a: float = 0.70

    # --- 其他 ---
    t0: float = 0.22

    #: 起点 ``z`` 的位置，以边界间距 ``a`` 为单位（``z = z_ratio·a``）。锚定在
    #: ``0.5``（无偏起点），**不估计**——只有它的自我偏移 ``dz_S`` 是自由参数，
    #: 否则 ``z_ratio`` 与 ``dz_S`` 的公共平移不可识别（同 α₁/α₂ 与 base_scale
    #: 的教训，见 `理论假设稳固性审查与W重定义_20260925.md`）。
    z_ratio: float = 0.50

    #: **SPE 的起点（判据）通道**：自我条件相对起点的偏移，以 ``a`` 为单位。
    #: ``z_self = (z_ratio + dz_S)·a``；他人条件恒为 ``z_ratio·a``。
    #:
    #: 方向：``z`` 从**下边界**量起，``is_match=1`` 时上边界 = 正确答案 = Match
    #: 键（`trial_params` 的 ``sign``），故 ``dz_S > 0`` ⇒ 自我条件下起点离上边界
    #: 更近 ⇒ 更快更易做 Match 反应 ⇒ SDT 判据 ``c`` 更负（更"敢说一样"），而
    #: ``d′`` 基本不动。这正是 SDT 拆解结果要求的形态：Self 比 Other
    #: ``Δd′ = +0.410``（= 张开，走 ``beta_S``）与 ``Δc = −0.239``（= 上移，
    #: 走 ``dz_S``）。依据见 `5_Reference/02_方法学审查/生成模型编码约定审查_20260930.md:81-83`。
    #:
    #: 量纲：无量纲（``/a``），因此跨 W 层次可比、可跨被试做层次模型；改为绝对
    #: 偏移（``Δz`` 秒）会把 ``a`` 的量纲混进被试间方差，故不采用。
    #: 默认 ``0.0`` ⇒ ``z = 0.5·a`` 与加入前**逐位相同**（可作回归测试）。
    dz_S: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)

    def replace(self, **kw) -> "MappingParams":
        d = self.as_dict()
        unknown = set(kw) - {f.name for f in fields(self)}
        if unknown:
            raise KeyError(f"未知参数：{sorted(unknown)}")
        d.update(kw)
        return MappingParams(**d)

    def vector(self, names: list[str]) -> np.ndarray:
        return np.array([getattr(self, n) for n in names], dtype=float)

    def with_vector(self, names: list[str], x) -> "MappingParams":
        return self.replace(**{n: float(xi) for n, xi in zip(names, np.atleast_1d(x))})


# ------------------------------------------------------------------
# 机制函数
# ------------------------------------------------------------------
def f_P(P, tau_P: float):
    """练习饱和：P=0 → 0；P→∞ → 1。"""
    return 1.0 - np.exp(-np.asarray(P, dtype=float) / float(tau_P))


def Q_T(T, tau):
    """时间饱和：T=0 → 0；T→∞ → 1。T 单位为**秒**。"""
    return 1.0 - np.exp(-np.asarray(T, dtype=float) / float(tau))


def drift_magnitude(P, T, is_self, p: MappingParams):
    """证据强度（幅度，恒正）。身份效应为**加性**偏移，锚定在参考点。"""
    P = np.asarray(P, dtype=float)
    T = np.asarray(T, dtype=float)
    is_self = np.asarray(is_self, dtype=float)

    dfp = f_P(P, p.tau_P) - f_P(p.P_ref, p.tau_P)
    if p.shape_model == "lin":
        # 无时标线性形式：beta_T 的单位是 drift/秒，T_ref 处取 d_ref
        dqt = T - p.T_ref
    elif p.shape_model == "exp":
        dqt = Q_T(T, p.tau_T) - Q_T(p.T_ref, p.tau_T)
    else:
        raise ValueError(f"未知 shape_model：{p.shape_model}（可选 {SHAPE_MODELS}）")

    d = p.d_ref + p.beta_P * dfp + p.beta_T * dqt
    d = d + is_self * (p.beta_S + p.beta_SP * dfp + p.beta_ST * dqt)
    return np.maximum(d, 1e-6)


def boundary_a(W, p: MappingParams):
    """W（onset-to-deadline，秒）→ 边界间距 a。"""
    W = np.asarray(W, dtype=float)
    if p.w_model == "W0":
        return np.full_like(W, float(p.a_ref))
    if p.w_model == "W1":
        if p.shape_model == "lin":
            dq = W - p.W_ref
        elif p.shape_model == "exp":
            dq = Q_T(W, p.tau_a) - Q_T(p.W_ref, p.tau_a)
        else:
            raise ValueError(f"未知 shape_model：{p.shape_model}（可选 {SHAPE_MODELS}）")
        return np.maximum(p.a_ref + p.delta_a * dq, 1e-3)
    raise ValueError(f"未知 w_model：{p.w_model}（可选 {W_MODELS}）")


def _ls_free_intercept(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """最小二乘 ``y ≈ 截距 + 斜率·x``，返回 ``(斜率, 截距)``。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    A = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(coef[1]), float(coef[0])


def match_lin_to_exp(p: MappingParams, T_levels, W_levels):
    """把 exp 形状真值换算成**设计层行为最小二乘匹配**的 lin 形状真值。

    目的：``exp`` 与 ``lin`` 是两套参数化，不能直接比较"同一组真值"。要让两套
    模型**生成同一种可观测行为**，必须显式换算。本函数用一条统一的规则：

      1. 取设计实际使用的 T 层次（``T_levels``）与 W 层次（``W_levels``）；
      2. 对 exp 的**形状偏移** ``ΔQ_T(X) = Q_T(X) − Q_T(X_ref)`` 在幅度
         ``beta_T``（非自我漂移）、``beta_ST``（自我漂移）、``delta_a``（边界）
         上分别做**带自由截距**的最小二乘直线拟合 ``幅度·ΔQ ≈ c + s·(X − X_ref)``；
      3. 斜率 ``s`` 即 lin 的 ``beta_T / beta_ST / delta_a``；
         截距 ``c`` 被吸收进参考点截距：``d_ref += c_T``、``beta_S += c_ST``、
         ``a_ref += c_a``。

    ⚠️ 为什么是**带自由截距**而不是过原点拟合：过原点拟合强制 ``d_ref`` 不变，
    于是 exp 曲线在 T 范围上的整体抬升/压低无法被直线吸收，残余系统偏差可达
    ~0.084 drift（约占 exp 漂移跨度的 25%）。带自由截距后残余降到 ~0.055，
    且 lin 的漂移跨度恢复到 exp 的 **94.8%**（过原点只有 81.8%）。

    ⚠️ 2026-10-14 修正的旧错误：此前 ``design_grid.TRUTH_LIN`` 的手写值
    ``beta_T=1.279, delta_a=0.226`` 换算规则**自相矛盾**——T 斜率乘了 exp 幅度
    ``beta_T=0.55``，W 斜率却用的是**未乘** ``delta_a=0.55`` 的原始比值，导致
    边界效应被夸大约 1.7 倍（lin 跨度 0.226 vs exp 0.133）。本函数统一处理。

    参数
    ----
    p : MappingParams
        必须是 ``shape_model="exp"`` 的真值（否则抛 ``ValueError``）。
    T_levels, W_levels : 序列
        设计实际使用的层次（秒）。**必须是实际设计层次**，因为换算只在这些点上
        追求行为一致，层次之外不保证。

    返回
    ----
    (lin, report) : tuple[MappingParams, dict]
        ``lin`` 是换算后的 lin 真值；``report`` 含 ``d_exp/d_lin/d_resid`` 与
        ``a_exp/a_lin/a_resid`` 等逐层对照，供调用方打印。
    """
    if p.shape_model != "exp":
        raise ValueError(
            f"match_lin_to_exp 需要 shape_model='exp' 的真值，收到 {p.shape_model!r}")

    Tl = np.asarray(list(T_levels), dtype=float)
    Wl = np.asarray(list(W_levels), dtype=float)

    # --- T 通路：ΔQ_T 只依赖 τ_T，与幅度无关 ---
    dqT = Q_T(Tl, p.tau_T) - Q_T(p.T_ref, p.tau_T)
    xT = Tl - float(p.T_ref)
    s_T, c_T = _ls_free_intercept(xT, p.beta_T * dqT)
    s_ST, c_ST = _ls_free_intercept(xT, p.beta_ST * dqT)

    # --- W 通路 ---
    dqW = Q_T(Wl, p.tau_a) - Q_T(p.W_ref, p.tau_a)
    xW = Wl - float(p.W_ref)
    s_a, c_a = _ls_free_intercept(xW, p.delta_a * dqW)

    lin = p.replace(
        shape_model="lin",
        d_ref=float(p.d_ref + c_T),
        beta_T=s_T,
        beta_S=float(p.beta_S + c_ST),
        beta_ST=s_ST,
        a_ref=float(p.a_ref + c_a),
        delta_a=s_a,
    )

    d_exp = float(p.d_ref) + float(p.beta_T) * dqT
    a_exp = float(p.a_ref) + float(p.delta_a) * dqW
    d_lin = float(lin.d_ref) + float(lin.beta_T) * xT
    a_lin = float(lin.a_ref) + float(lin.delta_a) * xW
    report = {
        "T_levels": Tl, "W_levels": Wl,
        "d_exp": d_exp, "d_lin": d_lin, "d_resid": d_lin - d_exp,
        "a_exp": a_exp, "a_lin": a_lin, "a_resid": a_lin - a_exp,
        "d_span_exp": float(np.ptp(d_exp)), "d_span_lin": float(np.ptp(d_lin)),
        "a_span_exp": float(np.ptp(a_exp)), "a_span_lin": float(np.ptp(a_lin)),
    }
    return lin, report


def trial_params(trials: dict, p: MappingParams) -> dict:
    """把逐试次设计表映射为逐试次 DDM 参数。

    ``trials`` 需含：``P``（次）、``T``（秒）、``W``（秒）、
    ``is_self``（0/1）、``is_match``（0/1，1 = 正确答案为 Match = 上边界）。

    身份进入**两个**通道：

    * 漂移 ``v`` —— 幅度经 `drift_magnitude`，幅度随 P、T、身份变化；
    * 起点 ``z`` —— 仅自我条件整体偏移 ``dz_S·a``（判据通道，见 `MappingParams.dz_S`）。
    """
    d = drift_magnitude(trials["P"], trials["T"], trials["is_self"], p)
    sign = np.where(np.asarray(trials["is_match"]) == 1, 1.0, -1.0)
    a = boundary_a(trials["W"], p)
    is_self = np.asarray(trials["is_self"], dtype=float)
    # 起点比例：他人恒 z_ratio，自我为 z_ratio + dz_S。夹到 (0,1) 内侧 1e-4，
    # 仅为数值兜底（dz_S 的界已保证 z/a ∈ [0.05, 0.95]），不参与梯度。
    zf = np.clip(p.z_ratio + is_self * p.dz_S, 1e-4, 1.0 - 1e-4)
    return {
        "v": sign * d, "a": a, "z": zf * a,
        "t0": float(p.t0), "d": d,
    }
