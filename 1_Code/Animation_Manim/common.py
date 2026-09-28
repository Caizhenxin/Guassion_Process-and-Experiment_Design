"""Manim 动画共享模块：配色、字体、真实数据加载、GP 数学工具。

设计要点：
- 配色采用 3Blue1Brown 风格的深色底 + 高饱和强调色。
- 真实实验数据直接从项目 CSV 读取，不在动画里硬编码数值。
- GP 数学部分用 numpy 手写（RBF 核 + Cholesky），不依赖 sklearn，
  保证渲染时可复现且无需额外依赖。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# 路径
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL4_CSV = (
    PROJECT_ROOT
    / "2_Data"
    / "Generate_Data"
    / "GP_Sigmoid_Canonical4"
    / "input_conditions_g3g8_canonical4.csv"
)
CANONICAL4_SUMMARY = (
    PROJECT_ROOT
    / "2_Data"
    / "Generate_Data"
    / "GP_Sigmoid_Canonical4"
    / "canonical4_summary.json"
)

# --------------------------------------------------------------------------
# 配色（3b1b 风格）
# --------------------------------------------------------------------------
BG = "#0E1116"
C_TEXT = "#ECECEC"
C_DIM = "#7A8391"
C_BLUE = "#58C4DD"      # 主色：样本函数 / P 轴
C_YELLOW = "#FFD166"    # 强调：不确定度带 / T 轴
C_PURPLE = "#9A72AC"    # W 轴
C_GREEN = "#83C167"     # 正面标注（如 σ→0）
C_ORANGE = "#FF862F"    # 真实观测点 / 关键结论

FONT = "Microsoft YaHei"  # 中文字体，避免 CJK 渲染成方块


# --------------------------------------------------------------------------
# 真实数据
# --------------------------------------------------------------------------
def load_real_conditions():
    """读取 canonical4（G3-G8，6 个可用条件）。

    返回 dict 列表，每个元素形如::

        {"group_id": 5, "P": 8.0, "T": 100.0, "W": 1100.0,
         "M": 1200.0, "SPE_v": 0.72}

    注意：G1/G2 因遗漏率过高已被排除在主线分析之外。
    """
    import csv

    rows = []
    with CANONICAL4_CSV.open(encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                {
                    "group_id": int(raw["group_id"]),
                    "P": float(raw["P"]),
                    "T": float(raw["T_ms"]),
                    "W": float(raw["W_ms"]),
                    "M": float(raw["M_ms"]),
                    "SPE_v": float(raw["SPE_v"]),
                    "v_self": float(raw["v_self_mean"]),
                    "v_stranger": float(raw["v_stranger_mean"]),
                }
            )
    rows.sort(key=lambda r: r["group_id"])
    return rows


# 设计空间的取值边界（与 GP 归一化范围一致）
P_RANGE = (0.0, 120.0)
T_RANGE = (30.0, 500.0)
W_RANGE = (300.0, 1500.0)


def canonical4_locv(target="SPE_v"):
    """读取 canonical4 的留一条件交叉验证指标（真实结果，不硬编码）。"""
    import json

    data = json.loads(CANONICAL4_SUMMARY.read_text(encoding="utf-8"))
    for metric in data["locv_metrics"]:
        if metric["target"] == target:
            return metric
    raise KeyError(f"LOCV 指标里没有 {target}")


# --------------------------------------------------------------------------
# GP 数学：RBF 核 + Cholesky 采样
# --------------------------------------------------------------------------
def rbf_kernel(x1, x2, length_scale=0.8, variance=1.0):
    """RBF（平方指数）核矩阵。"""
    a = np.asarray(x1, dtype=float).reshape(-1, 1)
    b = np.asarray(x2, dtype=float).reshape(-1, 1)
    sq_dist = (a - b.T) ** 2
    return variance * np.exp(-0.5 * sq_dist / (length_scale**2))


def gp_prior_samples(x, n_samples=6, length_scale=0.8, variance=1.0, seed=7):
    """从零均值 GP 先验中采样函数曲线。

    Returns
    -------
    ndarray, shape (len(x), n_samples)
        每一列是一条先验函数在 x 上的取值。
    """
    x = np.asarray(x, dtype=float)
    K = rbf_kernel(x, x, length_scale, variance)
    K += 1e-10 * np.eye(len(x))  # 数值抖动，保证 Cholesky 可分解
    chol = np.linalg.cholesky(K)

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((len(x), n_samples))
    return chol @ z


def gp_posterior(x, x_obs, y_obs, length_scale=0.8, variance=1.0, noise=0.02):
    """计算后验均值与标准差（不含采样）。

    Returns
    -------
    (mu, sigma) : 两个长度等于 len(x) 的数组
    """
    x = np.asarray(x, dtype=float)
    x_obs = np.asarray(x_obs, dtype=float)
    y_obs = np.asarray(y_obs, dtype=float)

    K = rbf_kernel(x_obs, x_obs, length_scale, variance)
    K += (noise**2 + 1e-10) * np.eye(len(x_obs))
    K_s = rbf_kernel(x_obs, x, length_scale, variance)
    K_ss = rbf_kernel(x, x, length_scale, variance)

    K_inv = np.linalg.inv(K)
    mu = K_s.T @ K_inv @ y_obs
    cov = K_ss - K_s.T @ K_inv @ K_s
    sigma = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    return mu, sigma


def gp_posterior_samples(
    x, x_obs, y_obs, n_samples=6, length_scale=0.8, variance=1.0, noise=0.02, seed=7
):
    """从后验中采样函数曲线。

    为了动画中"先验 → 后验"的形变看起来连贯，这里复用同一组标准正态
    随机数 z：先验用 ``L_prior @ z``，后验用 ``mu + L_post @ z``。
    """
    x = np.asarray(x, dtype=float)
    x_obs = np.asarray(x_obs, dtype=float)
    y_obs = np.asarray(y_obs, dtype=float)

    K = rbf_kernel(x_obs, x_obs, length_scale, variance)
    K += (noise**2 + 1e-10) * np.eye(len(x_obs))
    K_s = rbf_kernel(x_obs, x, length_scale, variance)
    K_ss = rbf_kernel(x, x, length_scale, variance)

    K_inv = np.linalg.inv(K)
    mu = K_s.T @ K_inv @ y_obs
    cov = K_ss - K_s.T @ K_inv @ K_s
    cov += 1e-10 * np.eye(len(x))

    # 用特征分解代替 Cholesky，避免后验协方差非正定导致崩溃
    eigvals, eigvecs = np.linalg.eigh(cov)
    eigvals = np.clip(eigvals, 0.0, None)
    chol_post = eigvecs @ np.diag(np.sqrt(eigvals))

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((len(x), n_samples))
    return mu[:, None] + chol_post @ z


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------
OBS_X = np.array([-1.25, 0.85])      # S3 演示用的观测点横坐标
OBS_Y = np.array([0.85, -0.55])      # 对应纵坐标（示意，非真实数据）


def gp_demo_grid(n=400, lo=-3.2, hi=3.2):
    return np.linspace(lo, hi, n)


# 项目里 5 个残差 GP 实际拟合出的 length_scale（归一化空间，[-1,1] 上）
# 来源：2_Data/Generate_Data/GP_Sigmoid_Canonical4/step4_gp_sigmoid_model_canonical4.pkl
#   v_self=0.162  v_stranger=0.220  a=0.194  t=1.78  z=0.774
FITTED_LENGTH_SCALES = [0.162, 0.220, 0.194, 1.78, 0.774]
FITTED_LS_RANGE = (min(FITTED_LENGTH_SCALES), max(FITTED_LENGTH_SCALES))


# --------------------------------------------------------------------------
# 设计空间上的 GP：以真实 SPE_v 为观测值
# --------------------------------------------------------------------------
# 说明：仅用于动画演示「GP 如何填充设计空间」。
# 项目正式的 GP 作用在 Sigmoid 预测的残差上，而非直接拟合 SPE_v。
SPE_GP_LENGTH_SCALE = 0.45
SPE_GP_NOISE = 0.08


def normalize_ptw(P, T, W):
    """把 (P, T, W) 归一化到 [-1, 1]（与项目 normalize_PTW 一致）。"""
    P = np.asarray(P, dtype=float)
    T = np.asarray(T, dtype=float)
    W = np.asarray(W, dtype=float)

    def _n(v, rng):
        return (v - (rng[0] + rng[1]) / 2) / ((rng[1] - rng[0]) / 2)

    return np.column_stack(
        [_n(P, P_RANGE), _n(T, T_RANGE), _n(W, W_RANGE)]
    )


def rbf_kernel_nd(X1, X2, length_scale, variance=1.0):
    """多维 RBF 核矩阵（各维共用同一个 length_scale，即各向同性）。"""
    X1 = np.atleast_2d(np.asarray(X1, dtype=float))
    X2 = np.atleast_2d(np.asarray(X2, dtype=float))
    sq = ((X1[:, None, :] - X2[None, :, :]) ** 2).sum(axis=-1)
    return variance * np.exp(-0.5 * sq / length_scale**2)


def spe_gp_predict(
    X_query,
    X_obs,
    y_obs,
    length_scale=SPE_GP_LENGTH_SCALE,
    variance=1.0,
    noise=SPE_GP_NOISE,
):
    """在设计空间上做 GP 回归，返回 (均值, 标准差)。"""
    X_query = np.atleast_2d(np.asarray(X_query, dtype=float))

    K = rbf_kernel_nd(X_obs, X_obs, length_scale, variance)
    K += (noise**2 + 1e-10) * np.eye(len(X_obs))
    K_s = rbf_kernel_nd(X_obs, X_query, length_scale, variance)
    K_ss = np.diag(rbf_kernel_nd(X_query, X_query, length_scale, variance))

    K_inv = np.linalg.inv(K)
    mu = K_s.T @ K_inv @ y_obs
    cov = K_ss - np.einsum("ij,ji->i", K_s.T @ K_inv, K_s)
    return mu, np.sqrt(np.clip(cov, 0.0, None))


def spe_observations(rows):
    """把 6 个真实条件转成 GP 的训练集 (X, y)。"""
    X = normalize_ptw(
        [r["P"] for r in rows], [r["T"] for r in rows], [r["W"] for r in rows]
    )
    y = np.array([r["SPE_v"] for r in rows], dtype=float)
    return X, y


def plane_grid(P_vals, T_vals, W_fix):
    """在固定 W 的 (P, T) 平面上生成查询网格。

    返回 (Pg, Tg, Xq)，其中 Pg/Tg 形状为 (len(T_vals), len(P_vals))，
    可以直接喂给 matplotlib.contour 或 ImageMobject。
    """
    Pg, Tg = np.meshgrid(np.asarray(P_vals, float), np.asarray(T_vals, float))
    Xq = normalize_ptw(Pg.ravel(), Tg.ravel(), np.full(Pg.size, W_fix))
    return Pg, Tg, Xq


def diverging_rgba(values, vmin, vmax, low="#3B7DD8", mid_color="#17222B", high="#FF862F"):
    """把标量场映射为 RGBA 图像：低=蓝，中（默认 0）=近背景暗色，高=橙。"""
    values = np.clip(np.asarray(values, dtype=float), vmin, vmax)
    lo = np.array([int(low[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
    mc = np.array([int(mid_color[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
    hi = np.array([int(high[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)

    mid = 0.0
    rgb = np.zeros(values.shape + (3,), dtype=float)
    below = values <= mid
    a = (values[below] - vmin) / (mid - vmin)
    rgb[below] = lo + (mc - lo) * a[..., None]
    a2 = (values[~below] - mid) / (vmax - mid)
    rgb[~below] = mc + (hi - mc) * a2[..., None]

    rgba = np.zeros(values.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = 255
    return rgba


# --------------------------------------------------------------------------
# Manim 绘图工具
# --------------------------------------------------------------------------
from manim import (  # noqa: E402  —— 放在文件末尾是为了让上面的纯数学部分可独立导入
    Axes,
    ImageMobject,
    Polygon,
    VMobject,
    VGroup,
)


def make_curve(axes, x, y, color, stroke_width=5, opacity=1.0):
    """把采样点连成一条可被 Create() 动画描绘的曲线。"""
    pts = [axes.c2p(xi, yi) for xi, yi in zip(x, y)]
    vm = VMobject(stroke_color=color, stroke_width=stroke_width, stroke_opacity=opacity)
    vm.set_points_as_corners(pts)
    return vm


def make_band(axes, x, mu, sigma, k=2.0, color=None, opacity=0.20):
    """构造 μ ± kσ 的不确定度带（填充多边形）。"""
    if color is None:
        color = C_BLUE
    top = [axes.c2p(xi, mi + k * si) for xi, mi, si in zip(x, mu, sigma)]
    bot = [axes.c2p(xi, mi - k * si) for xi, mi, si in zip(x, mu, sigma)]
    return Polygon(
        *top,
        *list(reversed(bot)),
        fill_color=color,
        fill_opacity=opacity,
        stroke_width=0,
    )


def demo_axes(x_length=10.5, y_length=4.2, y_max=2.4):
    """S2/S3 共用的二维演示坐标系（两幕需完全一致以保证拼接连贯）。"""
    axes = Axes(
        x_range=[-3.2, 3.2, 1],
        y_range=[-y_max, y_max, 1],
        x_length=x_length,
        y_length=y_length,
        axis_config={
            "color": C_DIM,
            "stroke_width": 2,
            "include_ticks": False,
            "include_tip": False,
        },
        x_axis_config={"include_numbers": False},
        y_axis_config={"include_numbers": False},
    )
    # 坐标轴移到画面中偏上位置，给下方的 σ 插图留空间
    axes.move_to([0, 0.6, 0])
    return axes


PLANE_P_RANGE = (-4.0, 128.0)   # 截面显示范围（比真实取值范围略留边距）
PLANE_T_RANGE = (10.0, 520.0)


def plane_axes(p_length=9.2, t_length=4.2):
    """S5-S7 共用的 (P, T) 截面坐标系。"""
    axes = Axes(
        x_range=[PLANE_P_RANGE[0], PLANE_P_RANGE[1], 40],
        y_range=[PLANE_T_RANGE[0], PLANE_T_RANGE[1], 100],
        x_length=p_length,
        y_length=t_length,
        axis_config={
            "color": C_DIM,
            "stroke_width": 2,
            "include_ticks": False,
            "include_tip": False,
        },
    )
    axes.move_to([0, 0.35, 0])
    return axes


def _fill_axes(axes, rgba):
    """把一张 RGBA 图铺满坐标系。"""
    img = ImageMobject(rgba)
    img.stretch_to_fit_width(axes.x_axis.get_length())
    img.stretch_to_fit_height(axes.y_axis.get_length())
    img.move_to([axes.x_axis.get_center()[0], axes.y_axis.get_center()[1], 0])
    return img


def field_image(axes, field, vmin, vmax, **kwargs):
    """把二维标量场做成铺在坐标系上的热力图。

    field 的行对应 T、列对应 P，且第 0 行是 T 的最大值（图像上方）。

    注意：ImageMobject 的 ``width`` / ``height`` 属性是等比缩放，
    必须用 ``stretch_to_fit_*`` 才能分别对齐两个方向。
    """
    return _fill_axes(axes, diverging_rgba(np.flipud(field), vmin, vmax, **kwargs))


def sigma_fog(axes, sigma, vmax, vmin=None, color=None, alpha_max=0.40, gamma=2.6):
    """把 σ 场画成一层"不确定度雾"，越不确定越亮。

    与 S2/S3 的 ±2σ 带同色（黄），保持"黄色 = 不确定度"的视觉一致性。
    默认按该截面上 σ 的实际最小/最大值归一化，以获得最大对比度。
    """
    sigma = np.asarray(sigma, dtype=float)
    if vmin is None:
        vmin = float(sigma.min())
    if color is None:
        color = C_YELLOW
    rgb = np.array([int(color[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
    a = np.clip((sigma - vmin) / max(vmax - vmin, 1e-9), 0.0, 1.0) ** gamma * alpha_max

    rgba = np.zeros(a.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = rgb.astype(np.uint8)
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return _fill_axes(axes, np.flipud(rgba))


def colorbar(vmin, vmax, height, width=0.32, n=120):
    """构造一支与热力图同色标的色条。"""
    grad = np.linspace(vmax, vmin, n).reshape(-1, 1)
    bar = ImageMobject(diverging_rgba(grad, vmin, vmax))
    bar.stretch_to_fit_width(width)
    bar.stretch_to_fit_height(height)
    return bar


def contour_lines(axes, Pg, Tg, field, levels, color, stroke_width=2.0, opacity=0.85):
    """用 matplotlib 提取等值线，再转成 Manim 的曲线对象。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    cs = ax.contour(Pg, Tg, field, levels=levels)
    segments = [seg for level_segs in cs.allsegs for seg in level_segs if len(seg) >= 2]
    plt.close(fig)

    paths = VGroup()
    for seg in segments:
        vm = VMobject(stroke_color=color, stroke_width=stroke_width, stroke_opacity=opacity)
        vm.set_points_as_corners([axes.c2p(x, y) for x, y in seg])
        paths.add(vm)
    return paths