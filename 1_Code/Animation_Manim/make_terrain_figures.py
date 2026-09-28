"""生成三维地形响应面的静态配图（4K，可直接用于 PPT / 论文插图）。

曲面定义（与视频 S6/S7 一致，均为教学示范设定）：
    底面 = (P, T)，固定 W 取一个截面；高度 = GP 预测的 SPE_v。
    σ 透明度调制：面片不透明度随该处 σ 升高而降低，
    因此"没有数据支撑"的区域会淡出成幽灵 —— 避免让观众误以为
    GP 已经学会了整片设计空间。

用法（在 1_Code/Animation_Manim 目录下）：

    ..\\..\\.venv-manim\\Scripts\\python.exe -m manim -qk -s make_terrain_figures.py Fig01TerrainMain
    ..\\..\\.venv-manim\\Scripts\\python.exe -m manim -qk -s make_terrain_figures.py Fig02TerrainSigma

输出为 media/images/make_terrain_figures/*.png（4K）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from manim import *  # noqa: E402
from scipy.interpolate import RegularGridInterpolator

from common import (  # noqa: E402
    BG,
    C_BLUE,
    C_DIM,
    C_TEXT,
    C_YELLOW,
    FONT,
    PLANE_P_RANGE,
    PLANE_T_RANGE,
    load_real_conditions,
    plane_grid,
    spe_gp_predict,
    spe_observations,
)

# 高度轴范围与配色（深蓝谷地 → 青 → 绿 → 黄 → 橙山峰）
Z_MIN, Z_MAX = -0.7, 1.4
COLOR_SCALE = [
    (ManimColor("#123A63"), Z_MIN),
    (ManimColor("#1F7FA8"), -0.15),
    (ManimColor("#4FB07A"), 0.35),
    (ManimColor("#C9D65B"), 0.80),
    (ManimColor("#FFD166"), 1.10),
    (ManimColor("#FF862F"), Z_MAX),
]

GRID = (64, 52)


def sample_color_scale(values, n_rows=None):
    """按 (颜色, 数值) 断点线性插值，生成色标的 RGBA 图像数组。"""
    values = np.atleast_1d(np.asarray(values, dtype=float))
    stop_rgb = np.array(
        [np.array(ManimColor(c[0]).to_rgb()) * 255.0 for c in COLOR_SCALE]
    )
    stop_val = np.array([c[1] for c in COLOR_SCALE], dtype=float)

    out = np.zeros((len(values), 1, 4), dtype=np.uint8)
    for i, z in enumerate(values):
        idx = int(np.clip(np.searchsorted(stop_val, z) - 1, 0, len(stop_val) - 2))
        z0, z1 = stop_val[idx], stop_val[idx + 1]
        a = 0.0 if z1 == z0 else (z - z0) / (z1 - z0)
        rgb = stop_rgb[idx] + (stop_rgb[idx + 1] - stop_rgb[idx]) * a
        out[i, 0, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[i, 0, 3] = 255
    return out


def bbox_wireframe(axes, z_min, z_max):
    """在设计空间外沿画一个包围盒线框，让 P / T 的量程在曲面前方仍可读。"""
    P0, P1 = PLANE_P_RANGE
    T0, T1 = PLANE_T_RANGE

    def rect(z):
        pts = [
            axes.coords_to_point(p, t, z)
            for p, t in [(P0, T0), (P1, T0), (P1, T1), (P0, T1)]
        ]
        return VGroup(
            *[
                Line3D(pts[i], pts[(i + 1) % 4], color=C_DIM, thickness=0.0032)
                for i in range(4)
            ]
        )

    box = VGroup(rect(z_min), rect(z_max))
    for p, t in [(P0, T0), (P1, T0), (P1, T1), (P0, T1)]:
        box.add(
            Line3D(
                axes.coords_to_point(p, t, z_min),
                axes.coords_to_point(p, t, z_max),
                color=C_DIM,
                thickness=0.0032,
            )
        )
    box.set_stroke(opacity=0.55)
    return box


class _TerrainFigure(ThreeDScene):
    """地形配图的公共骨架，子类只需覆盖类属性。"""

    W_SLICE = 600.0
    LENGTH_SCALE = 0.45
    FADE_BY_SIGMA = False
    PHI = 50.0
    THETA = -62.0
    ZOOM = 1.06
    TITLE = ""
    SUBTITLE = ""
    SHOW_COLORBAR = True
    SHOW_OBS = True
    LABEL_OBS = False
    ANNOTATE_SIGMA = False
    SAVE_AS = ""

    def construct(self):
        self.camera.background_color = BG
        self.set_camera_orientation(
            phi=self.PHI * DEGREES, theta=self.THETA * DEGREES, zoom=self.ZOOM
        )

        rows = load_real_conditions()
        X_obs, y_obs = spe_observations(rows)

        n_p, n_t = GRID
        P_vals = np.linspace(*PLANE_P_RANGE, n_p)
        T_vals = np.linspace(*PLANE_T_RANGE, n_t)
        Pg, Tg, Xq = plane_grid(P_vals, T_vals, self.W_SLICE)
        mu, sigma = spe_gp_predict(Xq, X_obs, y_obs, length_scale=self.LENGTH_SCALE)
        mu = mu.reshape(Pg.shape)
        sigma = sigma.reshape(Pg.shape)
        print(
            f"    ℓ={self.LENGTH_SCALE:.2f} W={self.W_SLICE:.0f}: "
            f"μ {mu.min():+.2f}..{mu.max():+.2f} 起伏 {np.ptp(mu):.2f} | "
            f"σ {sigma.min():.2f}..{sigma.max():.2f}"
        )

        interp_mu = RegularGridInterpolator(
            (T_vals, P_vals), mu, bounds_error=False, fill_value=0.0
        )
        interp_sg = RegularGridInterpolator(
            (T_vals, P_vals), sigma, bounds_error=False, fill_value=1.0
        )

        def sample(interp, u, v):
            return float(
                interp(
                    (
                        np.clip(v, T_vals[0], T_vals[-1]),
                        np.clip(u, P_vals[0], P_vals[-1]),
                    )
                )
            )

        axes = ThreeDAxes(
            x_range=[0, 120, 40],
            y_range=[30, 500, 100],
            z_range=[Z_MIN, Z_MAX, 0.5],
            x_length=3.9,
            y_length=3.9,
            z_length=2.5,
            x_axis_config={"color": C_BLUE, "stroke_width": 2.2, "include_tip": False},
            y_axis_config={"color": C_YELLOW, "stroke_width": 2.2, "include_tip": False},
            z_axis_config={"color": C_DIM, "stroke_width": 2.2, "include_tip": False},
            axis_config={"include_ticks": False},
        )
        axes.move_to([0.0, -0.15, -0.30])

        surface = Surface(
            lambda u, v: axes.c2p(u, v, sample(interp_mu, u, v)),
            u_range=[PLANE_P_RANGE[0], PLANE_P_RANGE[1]],
            v_range=[PLANE_T_RANGE[0], PLANE_T_RANGE[1]],
            resolution=GRID,
            fill_opacity=1.0,
            stroke_width=0.0,
        )
        surface.set_fill_by_value(axes=axes, colorscale=COLOR_SCALE, axis=2)
        surface.set_shade_in_3d(True)

        if self.FADE_BY_SIGMA:
            # σ 越大越透明：数据支撑强的地方鲜艳，没数据的区域沉入雾中
            for face in surface:
                p, t, _ = axes.p2c(face.get_center())
                sg = sample(interp_sg, p, t)
                face.set_fill(opacity=float(np.clip(1.30 - 1.20 * sg, 0.05, 1.0)))
                face.set_stroke(width=0)

        # 只把曲面画出来；坐标轴本身会被曲面遮住，改用外沿包围盒线框 + 底面刻度
        self.add(surface)

        # 包围盒线框，让 P / T 的量程在曲面前方仍可读
        self.add(bbox_wireframe(axes, Z_MIN, Z_MAX))

        # ---------------- 观测点 ----------------
        if self.SHOW_OBS:
            on_slice = [r for r in rows if abs(r["W"] - self.W_SLICE) < 1.0]
            for r in on_slice:
                pt = axes.coords_to_point(r["P"], r["T"], r["SPE_v"])
                self.add(Dot3D(point=pt, radius=0.10, color=C_TEXT))
                if self.LABEL_OBS:
                    tag = Text(
                        f"G{r['group_id']}  SPE_v = {r['SPE_v']:+.2f}",
                        font=FONT,
                        font_size=19,
                        color=C_TEXT,
                    )
                    tag.move_to(pt + np.array([-0.9, -0.1, 0.55]))
                    self.add_fixed_orientation_mobjects(tag)
                    self.add(tag)

        # ---------------- 标注：高不确定区域 ----------------
        if self.ANNOTATE_SIGMA:
            tip = axes.coords_to_point(70, 380, float(np.max(mu)))
            note = Text(
                "σ 接近上限：这里没有数据",
                font=FONT,
                font_size=20,
                color=C_YELLOW,
            )
            note.move_to(tip + np.array([-0.2, -0.4, 0.85]))
            self.add_fixed_orientation_mobjects(note)
            arrow = Line3D(
                start=note.get_center(),
                end=tip,
                color=C_YELLOW,
                thickness=0.006,
            )
            self.add(arrow, note)

        # ---------------- 标题与坐标轴说明 ----------------
        title = Text(self.TITLE, font=FONT, font_size=27, color=C_TEXT)
        title.to_edge(UP, buff=0.42)
        self.add_fixed_in_frame_mobjects(title)

        if self.SUBTITLE:
            sub = Text(self.SUBTITLE, font=FONT, font_size=20, color=C_DIM)
            sub.next_to(title, DOWN, buff=0.18)
            self.add_fixed_in_frame_mobjects(sub)

        axis_legend = Text(
            "P 练习次数 0 – 120（→）      T 刺激呈现时间 30 – 500 ms（↑）      "
            "Z 轴 = GP 预测的 SPE_v",
            font=FONT,
            font_size=19,
            color=C_DIM,
        )
        axis_legend.to_edge(DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(axis_legend)

        if self.SHOW_COLORBAR:
            bar = ImageMobject(sample_color_scale(np.linspace(Z_MAX, Z_MIN, 160)))
            bar.stretch_to_fit_width(0.34)
            bar.stretch_to_fit_height(2.3)
            bar.move_to([5.65, 0.15, 0])
            bar_hi = Text(f"{Z_MAX:.1f}", font=FONT, font_size=17, color=C_DIM)
            bar_hi.next_to(bar, UP, buff=0.14)
            bar_lo = Text(f"{Z_MIN:.1f}", font=FONT, font_size=17, color=C_DIM)
            bar_lo.next_to(bar, DOWN, buff=0.14)
            bar_lab = Text("SPE_v", font=FONT, font_size=18, color=C_DIM)
            bar_lab.next_to(bar_hi, UP, buff=0.12)
            self.add_fixed_in_frame_mobjects(bar, bar_hi, bar_lo, bar_lab)

        self.wait(0.1)


# --------------------------------------------------------------------------
# 各张配图
# --------------------------------------------------------------------------
class Fig01TerrainMain(_TerrainFigure):
    """主图：W = 600 ms 截面，纯地形。"""

    W_SLICE = 600.0
    LENGTH_SCALE = 0.45
    TITLE = "三维响应曲面：W = 600 ms 截面"
    SUBTITLE = "高度 = GP 预测的 SPE_v；两个白点是该截面上的真实条件 G3 / G4"


class Fig02TerrainSigma(_TerrainFigure):
    """主图 + σ 透明度调制。"""

    W_SLICE = 600.0
    LENGTH_SCALE = 0.45
    FADE_BY_SIGMA = True
    TITLE = "叠加不确定度 σ 后：没数据的地方沉入雾中"
    SUBTITLE = "面片不透明度随 σ 升高而降低，所见起伏只存在于有数据支撑的位置"


class Fig03TerrainW800(_TerrainFigure):
    """对比：现有视频使用的 W = 800 ms 截面。"""

    W_SLICE = 800.0
    LENGTH_SCALE = 0.45
    FADE_BY_SIGMA = True
    TITLE = "对比：W = 800 ms 截面（起伏仅 0.42）"
    SUBTITLE = "该截面上只有两个同号观测点，曲面在数学上就几乎不可能起伏"


class Fig04TerrainRealLS(_TerrainFigure):
    """ℓ 取项目真实拟合值附近（v_stranger = 0.22）。"""

    W_SLICE = 600.0
    LENGTH_SCALE = 0.22
    FADE_BY_SIGMA = True
    TITLE = "ℓ = 0.22（项目真实拟合值附近，v_stranger）"
    SUBTITLE = "小 ℓ 下大片平坦高原 + 陡峭孤峰：平坦不是因为那里真的平，而是因为没测过"


class Fig05TerrainAnnotated(_TerrainFigure):
    """带观测点标签与高不确定区标注。"""

    W_SLICE = 600.0
    LENGTH_SCALE = 0.45
    FADE_BY_SIGMA = True
    LABEL_OBS = True
    ANNOTATE_SIGMA = True
    TITLE = "标注版：观测条件与高不确定区域"
    SUBTITLE = "起伏集中在 G3 / G4 所在的陡壁；其余大片区域 σ 接近上限"


class Fig06TerrainSide(_TerrainFigure):
    """侧视角：突出起伏轮廓。"""

    W_SLICE = 600.0
    LENGTH_SCALE = 0.45
    FADE_BY_SIGMA = True
    PHI = 16.0
    THETA = -78.0
    ZOOM = 1.10
    TITLE = "侧视：起伏轮廓"
    SUBTITLE = "低视角下更容易读出峰谷的陡缓与高度差"