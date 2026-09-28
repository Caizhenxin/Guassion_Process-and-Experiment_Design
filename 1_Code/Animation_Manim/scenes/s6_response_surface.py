"""S6：真实数据接入 —— GP 学到的响应面，以及一个诚实的限制。

叙事作用：把 6 个真实条件的 SPE_v 作为观测值喂给 GP，展示它填出来的响应面；
同时明确说出"6 个点撑不起三维空间"这一限制，并交代替换方案
（项目里 GP 实际拟合的是 Sigmoid 预测的残差）。
时长约 44 秒。
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
    C_TEXT,
    C_YELLOW,
    FONT,
    PLANE_P_RANGE,
    PLANE_T_RANGE,
    SPE_GP_LENGTH_SCALE,
    canonical4_locv,
    colorbar,
    field_image,
    load_real_conditions,
    plane_axes,
    plane_grid,
    spe_gp_predict,
    spe_observations,
)

W_SLICE = 800.0
MU_VMIN, MU_VMAX = -0.5, 0.8


class S6ResponseSurface(Scene):
    def construct(self):
        self.camera.background_color = BG

        conditions = load_real_conditions()
        on_slice = [c for c in conditions if abs(c["W"] - W_SLICE) < 1.0]
        X_obs, y_obs = spe_observations(conditions)

        axes = plane_axes()
        dots = VGroup()
        for c in on_slice:
            pt = axes.c2p(c["P"], c["T"])
            dots.add(Dot(pt, radius=0.11, color=C_ORANGE))
            dots.add(
                Text(f"G{c['group_id']}", font=FONT, font_size=20, color=C_ORANGE)
                .next_to(pt, LEFT, buff=0.18)
            )

        x_lab = Text("P  练习次数", font=FONT, font_size=21, color=C_BLUE)
        x_lab.next_to(axes.c2p(60, PLANE_T_RANGE[0]), DOWN, buff=0.3)
        y_lab = Text("T  刺激呈现时间 (ms)", font=FONT, font_size=21, color=C_YELLOW)
        y_lab.rotate(90 * DEGREES)
        y_lab.next_to(axes.c2p(PLANE_P_RANGE[0], 265), LEFT, buff=0.25)

        # 承接 S5 结尾状态
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

        self.add(axes, dots, x_lab, y_lab, note_3, note_4)
        self.wait(1.0)


        # ---------------- 喂给 GP，得到响应面 ----------------
        title = Text(
            "把这 6 个真实 SPE_v 当作观测值喂给 GP",
            font=FONT,
            font_size=26,
            color=C_TEXT,
        )
        title.to_edge(UP, buff=0.45)
        legend = Text(
            "底色 = GP 预测的 SPE_v（蓝 ←→ 橙）    GP 在完整 (P, T, W) 上拟合，此处显示 W = 800 ms 截面",
            font=FONT,
            font_size=19,
            color=C_DIM,
        )
        legend.next_to(title, DOWN, buff=0.22)

        P_vals = np.linspace(*PLANE_P_RANGE, 72)
        T_vals = np.linspace(*PLANE_T_RANGE, 62)
        Pg, Tg, Xq = plane_grid(P_vals, T_vals, W_SLICE)
        mu, _ = spe_gp_predict(Xq, X_obs, y_obs, length_scale=SPE_GP_LENGTH_SCALE)
        heat = field_image(axes, mu.reshape(Pg.shape), MU_VMIN, MU_VMAX)

        bar = colorbar(MU_VMIN, MU_VMAX, height=2.5, width=0.3)
        bar.move_to([5.55, 0.55, 0])
        bar_hi = Text(f"+{MU_VMAX:.1f}", font=FONT, font_size=17, color=C_DIM)
        bar_hi.next_to(bar, UP, buff=0.12)
        bar_lo = Text(f"{MU_VMIN:.1f}", font=FONT, font_size=17, color=C_DIM)
        bar_lo.next_to(bar, DOWN, buff=0.12)

        # 学术诚信脚注：说清这张图是示范设定，而不是项目的正式模型
        demo_note = Text(
            f"※ 教学示范：以 SPE_v 直接建模，ℓ = {SPE_GP_LENGTH_SCALE:.2f}\n"
            "项目正式模型拟合 Sigmoid 残差",
            font=FONT,
            font_size=16,
            color=C_DIM,
            line_spacing=0.8,
        )
        demo_note.move_to([7.0, -2.25, 0])
        demo_note.align_to(np.array([7.0, 0.0, 0.0]), RIGHT)

        self.play(
            FadeOut(note_3),
            FadeOut(note_4),
            FadeIn(title, shift=DOWN * 0.15),
            FadeIn(legend),
            run_time=1.5,
        )
        self.play(FadeIn(heat), run_time=2.5)
        self.play(
            FadeIn(bar), FadeIn(bar_hi), FadeIn(bar_lo), FadeIn(demo_note), run_time=1.0
        )
        self.wait(1.5)

        # ---------------- 6 个真实取值 ----------------
        values = VGroup()
        for c in conditions:
            label = Text(f"G{c['group_id']}", font=FONT, font_size=17, color=C_DIM)
            value = Text(
                f"{c['SPE_v']:+.2f}",
                font=FONT,
                font_size=22,
                color=C_ORANGE if c["SPE_v"] > 0 else C_BLUE,
            )
            values.add(VGroup(label, value).arrange(DOWN, buff=0.06))
        values.arrange(RIGHT, buff=0.55)
        values.move_to([0.2, -2.9, 0])

        values_cap = Text("真实观测值", font=FONT, font_size=19, color=C_DIM)
        values_cap.next_to(values, LEFT, buff=0.4)

        self.play(FadeIn(values_cap), FadeIn(values, shift=UP * 0.15), run_time=1.5)
        self.wait(2.5)

        # ---------------- 诚实的限制 ----------------
        locv = canonical4_locv("SPE_v")
        caution = VGroup(
            Text(
                f"但这 6 个点撑不起三维空间：留一条件交叉验证 r ≈ {locv['r']:.2f}",
                font=FONT,
                font_size=23,
                color=C_ORANGE,
            ),
            Text(
                "G1 / G2 因遗漏率超过 50% 已被排除；要泛化必须补新的实验条件",
                font=FONT,
                font_size=20,
                color=C_DIM,
            ),
        ).arrange(DOWN, buff=0.2)
        caution.move_to([0.2, -3.3, 0])

        self.play(
            FadeOut(values),
            FadeOut(values_cap),
            FadeIn(caution, shift=UP * 0.15),
            run_time=1.6,
        )
        self.wait(3.0)

        # ---------------- 交代替换方案 ----------------
        bridge = VGroup(
            Text(
                "所以项目里 GP 不直接拟合 SPE_v，而是拟合 Sigmoid 预测的残差",
                font=FONT,
                font_size=23,
                color=C_TEXT,
            ),
            Text(
                "Sigmoid 提供理论先验，GP 负责修正理论解释不了的那部分偏差",
                font=FONT,
                font_size=20,
                color=C_YELLOW,
            ),
        ).arrange(DOWN, buff=0.2)
        bridge.move_to(caution)

        self.play(FadeOut(caution), FadeIn(bridge, shift=UP * 0.15), run_time=1.6)
        self.wait(7.0)