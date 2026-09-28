"""S5：从 1 维升到 3 维 —— 在设计空间里"切一刀"。

叙事作用：把 GP 从"一条曲线"推广到三维设计空间，并引入截面视角：
固定 W，就得到一张 (P, T) 平面。同时点出关键困难——这一刀上几乎没有观测点。
时长约 42 秒。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from manim import *  # noqa: E402

from common import (  # noqa: E402
    BG,
    C_BLUE,
    C_DIM,
    C_ORANGE,
    C_PURPLE,
    C_TEXT,
    C_YELLOW,
    FONT,
    P_RANGE,
    PLANE_P_RANGE,
    PLANE_T_RANGE,
    T_RANGE,
    W_RANGE,
    load_real_conditions,
    plane_axes,
)

W_SLICE = 800.0


class S5HigherDimension(ThreeDScene):
    def construct(self):
        self.camera.background_color = BG
        self.set_camera_orientation(phi=66 * DEGREES, theta=-48 * DEGREES, zoom=1.02)

        # ---------------- 三维设计空间（与 S1 一致） ----------------
        axes = ThreeDAxes(
            x_range=[P_RANGE[0], P_RANGE[1], 40],
            y_range=[T_RANGE[0], T_RANGE[1], 100],
            z_range=[W_RANGE[0], W_RANGE[1], 500],
            x_length=3.9,
            y_length=3.9,
            z_length=3.9,
            x_axis_config={"color": C_BLUE, "stroke_width": 2.5, "include_tip": False},
            y_axis_config={"color": C_YELLOW, "stroke_width": 2.5, "include_tip": False},
            z_axis_config={"color": C_PURPLE, "stroke_width": 2.5, "include_tip": False},
            axis_config={"include_ticks": False},
        )
        axes.move_to(np.array([-0.15, 0.0, 0.15]))

        conditions = load_real_conditions()
        dots = VGroup(
            *[
                Dot3D(
                    point=axes.coords_to_point(c["P"], c["T"], c["W"]),
                    radius=0.085,
                    color=C_ORANGE,
                )
                for c in conditions
            ]
        )

        legend = VGroup(
            Text("P  练习次数", font=FONT, font_size=20, color=C_BLUE),
            Text("T  刺激呈现时间 (ms)", font=FONT, font_size=20, color=C_YELLOW),
            Text("W  反应窗口 (ms)", font=FONT, font_size=20, color=C_PURPLE),
        ).arrange(RIGHT, buff=0.7)
        legend.to_edge(DOWN, buff=0.35)

        self.play(Create(axes), run_time=1.5)
        self.play(
            LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.35),
            run_time=4.0,
        )
        self.add_fixed_in_frame_mobjects(legend)
        self.play(FadeIn(legend), run_time=0.8)

        note_1 = Text(
            "把 GP 从一条曲线，推广到三维设计空间",
            font=FONT,
            font_size=26,
            color=C_TEXT,
        )
        note_1.to_edge(UP, buff=0.45)
        self.add_fixed_in_frame_mobjects(note_1)
        self.play(FadeIn(note_1, shift=DOWN * 0.2), run_time=1.4)
        self.wait(1.5)

        # ---------------- 切出一张 (P, T) 截面 ----------------
        corners = [
            axes.coords_to_point(p, t, W_SLICE)
            for p, t in [
                (P_RANGE[0], T_RANGE[0]),
                (P_RANGE[1], T_RANGE[0]),
                (P_RANGE[1], T_RANGE[1]),
                (P_RANGE[0], T_RANGE[1]),
            ]
        ]
        slice_plane = Polygon(
            *corners,
            fill_color=C_TEXT,
            fill_opacity=0.10,
            stroke_color=C_TEXT,
            stroke_width=1.5,
            stroke_opacity=0.75,
        )

        note_2 = Text(
            "固定 W = 800 ms，切出一张 (P, T) 截面",
            font=FONT,
            font_size=26,
            color=C_TEXT,
        )
        note_2.move_to(note_1)
        self.add_fixed_in_frame_mobjects(note_2)

        on_slice = [c for c in conditions if abs(c["W"] - W_SLICE) < 1.0]
        slice_dots = VGroup(
            *[
                Dot3D(
                    point=axes.coords_to_point(c["P"], c["T"], W_SLICE),
                    radius=0.11,
                    color=C_TEXT,
                )
                for c in on_slice
            ]
        )

        self.play(FadeOut(note_1), FadeIn(note_2), run_time=1.2)
        self.play(FadeIn(slice_plane), run_time=1.6)
        self.play(*[GrowFromCenter(d) for d in slice_dots], run_time=1.2)
        self.wait(1.2)

        # 视角转向截面，准备"潜入"
        self.move_camera(phi=40 * DEGREES, theta=-72 * DEGREES, run_time=4.0)
        self.wait(0.8)

        # ---------------- 潜入截面：切换成二维视图 ----------------
        axes_2d = plane_axes()
        dots_2d = VGroup(
            *[
                Dot(axes_2d.c2p(c["P"], c["T"]), radius=0.11, color=C_ORANGE)
                for c in on_slice
            ]
        )
        for c, dot in zip(on_slice, dots_2d):
            tag = Text(
                f"G{c['group_id']}", font=FONT, font_size=20, color=C_ORANGE
            ).next_to(dot, LEFT, buff=0.18)
            dots_2d.add(tag)

        self.add_fixed_in_frame_mobjects(axes_2d)
        x_lab = Text("P  练习次数", font=FONT, font_size=21, color=C_BLUE)
        x_lab.next_to(axes_2d.c2p(60, PLANE_T_RANGE[0]), DOWN, buff=0.3)
        y_lab = Text("T  刺激呈现时间 (ms)", font=FONT, font_size=21, color=C_YELLOW)
        y_lab.rotate(90 * DEGREES)
        y_lab.next_to(axes_2d.c2p(PLANE_P_RANGE[0], 265), LEFT, buff=0.25)
        self.add_fixed_in_frame_mobjects(x_lab, y_lab)

        self.play(
            FadeOut(axes),
            FadeOut(dots),
            FadeOut(slice_plane),
            FadeOut(slice_dots),
            FadeOut(legend),
            FadeOut(note_2),
            FadeIn(axes_2d),
            FadeIn(x_lab),
            FadeIn(y_lab),
            FadeIn(dots_2d),
            run_time=2.5,
        )
        self.wait(1.0)

        # ---------------- 关键困难：这一刀上几乎没有观测点 ----------------
        note_3 = Text(
            "整片三维空间里只有 6 个观测点，这一刀上只剩 2 个",
            font=FONT,
            font_size=26,
            color=C_ORANGE,
        )
        note_3.to_edge(UP, buff=0.45)
        note_4 = Text(
            "另外 4 个条件分别落在 W = 600 / 1100 / 1500 的平面上",
            font=FONT,
            font_size=21,
            color=C_DIM,
        )
        note_4.next_to(note_3, DOWN, buff=0.22)

        self.add_fixed_in_frame_mobjects(note_3, note_4)
        self.play(FadeIn(note_3, shift=DOWN * 0.2), run_time=1.4)
        self.play(FadeIn(note_4), run_time=1.0)
        self.wait(6.0)