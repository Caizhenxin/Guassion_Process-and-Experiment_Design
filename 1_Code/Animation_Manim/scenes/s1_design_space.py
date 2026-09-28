"""S1：把问题变成函数 —— 三维设计空间中只有 6 个观测点。

叙事作用：让听众直观看到 (P, T, W) 设计空间的"数据荒芜"，
为下一幕引入 GP（用不确定性表达未知）做铺垫。
时长约 26 秒。
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
    T_RANGE,
    W_RANGE,
    load_real_conditions,
)

# 未测量区域的示意位置（位于 T 的中段 × 低练习量，是 6 个条件都没覆盖到的地方）
GAP_MARK = (30.0, 350.0, 800.0)


class S1DesignSpace(ThreeDScene):
    def construct(self):
        self.camera.background_color = BG
        self.set_camera_orientation(phi=66 * DEGREES, theta=-48 * DEGREES, zoom=1.02)

        # ---------------- 坐标系 ----------------
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
        axes.move_to(np.array([-0.75, 0.0, 0.15]))

        letters = VGroup(
            Text("P", font=FONT, font_size=26, color=C_BLUE).move_to(
                axes.coords_to_point(P_RANGE[1] * 1.1, T_RANGE[0], W_RANGE[0])
            ),
            Text("T", font=FONT, font_size=26, color=C_YELLOW).move_to(
                axes.coords_to_point(P_RANGE[0], T_RANGE[1] * 1.1, W_RANGE[0])
            ),
            Text("W", font=FONT, font_size=26, color=C_PURPLE).move_to(
                axes.coords_to_point(P_RANGE[0], T_RANGE[0], W_RANGE[1] * 1.08)
            ),
        )

        legend = VGroup(
            Text("P  练习次数", font=FONT, font_size=20, color=C_BLUE),
            Text("T  刺激呈现时间 (ms)", font=FONT, font_size=20, color=C_YELLOW),
            Text("W  反应窗口 (ms)", font=FONT, font_size=20, color=C_PURPLE),
        ).arrange(RIGHT, buff=0.7)
        legend.to_edge(DOWN, buff=0.35)

        # ---------------- 6 个真实条件的速查表 ----------------
        conditions = load_real_conditions()
        rows = [["条件", "P", "T(ms)", "W(ms)"]]
        for c in conditions:
            rows.append(
                [f"G{c['group_id']}", f"{c['P']:.0f}", f"{c['T']:.0f}", f"{c['W']:.0f}"]
            )

        col_x = [0.0, 0.62, 1.30, 2.12]
        row_h = 0.30
        table = VGroup()
        for r, row in enumerate(rows):
            for col, cell in enumerate(row):
                t = Text(
                    cell,
                    font=FONT,
                    font_size=16,
                    color=C_DIM if r == 0 else C_TEXT,
                )
                t.move_to(np.array([0.0, -r * row_h, 0.0]))
                t.align_to(np.array([col_x[col], 0.0, 0.0]), LEFT)
                table.add(t)
        table.move_to(np.array([4.05, 0.55, 0.0]))

        self.play(Create(axes), run_time=2.0)
        for letter in letters:
            self.add_fixed_orientation_mobjects(letter)
        self.play(FadeIn(letters), run_time=0.8)
        self.add_fixed_in_frame_mobjects(legend, table)
        self.play(FadeIn(legend), FadeIn(table, shift=LEFT * 0.2), run_time=1.2)

        # ---------------- 6 个观测点依次落位 ----------------
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
        self.play(
            LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.55),
            run_time=10.0,
        )
        self.wait(0.6)

        # ---------------- 标题 ----------------
        title = Text("6 个观测点  ·  3 维设计空间", font=FONT, font_size=26, color=C_TEXT)
        title.to_edge(UP, buff=0.4)
        self.add_fixed_in_frame_mobjects(title)
        self.play(FadeIn(title), run_time=1.0)
        self.wait(0.5)

        # ---------------- 标出未测量区域 ----------------
        gap_pos = axes.coords_to_point(*GAP_MARK)
        ring = Dot3D(point=gap_pos, radius=0.1, color=C_TEXT, fill_opacity=0.0)
        ring.set_stroke(C_TEXT, width=2.2, opacity=0.9)

        tag_pos = axes.coords_to_point(GAP_MARK[0] + 35, GAP_MARK[1] - 330, GAP_MARK[2] + 420)
        ring_tag = Text("未测量区域", font=FONT, font_size=19, color=C_TEXT)
        ring_tag.move_to(tag_pos)
        ring_leader = Line3D(
            start=gap_pos + (tag_pos - gap_pos) * 0.08,
            end=tag_pos + (gap_pos - tag_pos) * 0.3,
            color=C_TEXT,
            thickness=0.005,
        )
        self.add_fixed_orientation_mobjects(ring_tag)

        self.play(Create(ring), run_time=1.2)
        self.play(Create(ring_leader), FadeIn(ring_tag), run_time=1.2)

        gap_note = Text(
            "T 在 200–500 ms、P < 60 的整片区域，从未被测量",
            font=FONT,
            font_size=22,
            color=C_ORANGE,
        )
        gap_note.next_to(title, DOWN, buff=0.25)
        self.add_fixed_in_frame_mobjects(gap_note)
        self.play(FadeIn(gap_note, shift=UP * 0.2), run_time=1.5)
        self.wait(5.0)