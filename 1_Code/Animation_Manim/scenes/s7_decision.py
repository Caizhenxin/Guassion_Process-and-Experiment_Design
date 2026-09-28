"""S7：从拟合到决策 —— σ 告诉我们下一步该测哪里。

叙事作用：这是全片对"研究设计"最有价值的落点。
同一张截面，把底色从预测值换成不确定度，高 σ 区域就自动浮出来；
再标出真实候选推荐点，形成"GP → 下一轮实验"的闭环。
时长约 46 秒。
"""

import csv
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
    PROJECT_ROOT,
    SPE_GP_LENGTH_SCALE,
    colorbar,
    contour_lines,
    field_image,
    load_real_conditions,
    plane_axes,
    plane_grid,
    sigma_fog,
    spe_gp_predict,
    spe_observations,
)

W_SLICE = 800.0
MU_VMIN, MU_VMAX = -0.5, 0.8
SIGMA_VMAX = 1.0
SIGMA_LEVELS = [0.35, 0.65]

CANDIDATE_CSV = (
    PROJECT_ROOT
    / "2_Data"
    / "Generate_Data"
    / "GP_Sigmoid_Canonical4"
    / "step6_candidate_design_points.csv"
)


class S7Decision(Scene):
    def construct(self):
        self.camera.background_color = BG

        conditions = load_real_conditions()
        on_slice = [c for c in conditions if abs(c["W"] - W_SLICE) < 1.0]
        X_obs, y_obs = spe_observations(conditions)

        P_vals = np.linspace(*PLANE_P_RANGE, 72)
        T_vals = np.linspace(*PLANE_T_RANGE, 62)
        Pg, Tg, Xq = plane_grid(P_vals, T_vals, W_SLICE)
        mu, sigma = spe_gp_predict(Xq, X_obs, y_obs, length_scale=SPE_GP_LENGTH_SCALE)
        mu = mu.reshape(Pg.shape)
        sigma = sigma.reshape(Pg.shape)

        # ---------------- 复现 S6 结尾的画面 ----------------
        axes = plane_axes()
        heat = field_image(axes, mu, MU_VMIN, MU_VMAX)

        bar = colorbar(MU_VMIN, MU_VMAX, height=2.5, width=0.3)
        bar.move_to([5.55, 0.55, 0])
        bar_hi = Text(f"+{MU_VMAX:.1f}", font=FONT, font_size=17, color=C_DIM)
        bar_hi.next_to(bar, UP, buff=0.12)
        bar_lo = Text(f"{MU_VMIN:.1f}", font=FONT, font_size=17, color=C_DIM)
        bar_lo.next_to(bar, DOWN, buff=0.12)
        # ImageMobject 不是 VMobject，只能放进 Group
        bars = Group(bar, bar_hi, bar_lo)

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
        bridge.move_to([0.2, -3.3, 0])

        self.add(axes, heat, bars, dots, x_lab, y_lab, title, legend, bridge, demo_note)
        self.wait(1.2)
        self.play(FadeOut(bridge), FadeOut(legend), run_time=1.2)

        # ---------------- 换看 σ ----------------
        title_sigma = Text(
            "同一张截面，换看不确定度 σ",
            font=FONT,
            font_size=26,
            color=C_TEXT,
        )
        title_sigma.to_edge(UP, buff=0.45)

        fog = sigma_fog(axes, sigma, SIGMA_VMAX)
        sigma_legend = Text(
            "底色越亮 = σ 越大 = 越不知道",
            font=FONT,
            font_size=19,
            color=C_DIM,
        )
        sigma_legend.next_to(title_sigma, DOWN, buff=0.22)

        self.play(FadeOut(title), FadeIn(title_sigma), run_time=1.2)
        self.play(FadeOut(heat), FadeOut(bars), FadeIn(fog), FadeIn(sigma_legend), run_time=2.2)
        self.wait(0.8)

        contours = contour_lines(axes, Pg, Tg, sigma, SIGMA_LEVELS, C_TEXT, 1.6, 0.6)
        self.play(Create(contours), run_time=2.5)
        self.wait(1.0)

        # ---------------- 指出高不确定区域 ----------------
        target = axes.c2p(12, 455)
        source = axes.c2p(48, 300)
        arrow = Arrow(
            source,
            target,
            buff=0.2,
            stroke_color=C_TEXT,
            stroke_width=2.5,
            max_tip_length_to_length_ratio=0.12,
        )
        area_note = Text(
            "这里离所有观测点都很远，σ 接近上限",
            font=FONT,
            font_size=21,
            color=C_TEXT,
        )
        area_note.next_to(source, RIGHT, buff=0.25)
        area_box = BackgroundRectangle(
            area_note, color=BG, fill_opacity=0.85, buff=0.14
        )

        self.play(GrowArrow(arrow), run_time=1.5)
        self.play(FadeIn(area_box), FadeIn(area_note, shift=LEFT * 0.15), run_time=1.2)
        self.wait(2.0)

        # ---------------- Top 候选点（真实推荐结果） ----------------
        top = next(iter(csv.DictReader(CANDIDATE_CSV.open(encoding="utf-8"))))
        top_P, top_T, top_W = (float(top[k]) for k in ("P", "T_ms", "W_ms"))
        cand_pt = axes.c2p(top_P, top_T)
        cand_ring = Circle(radius=0.17, stroke_color=C_YELLOW, stroke_width=2.6)
        cand_ring.move_to(cand_pt)

        cand_label = Text(
            f"Top 候选：P={top_P:.0f}, T={top_T:.0f}, W={top_W:.0f}（σ 最大）",
            font=FONT,
            font_size=20,
            color=C_YELLOW,
        )
        cand_label.next_to(cand_ring, RIGHT, buff=0.3).shift(DOWN * 0.05)
        cand_box = BackgroundRectangle(
            cand_label, color=BG, fill_opacity=0.85, buff=0.14
        )

        self.play(Create(cand_ring), run_time=1.2)
        self.play(FadeIn(cand_box), FadeIn(cand_label, shift=LEFT * 0.15), run_time=1.2)
        self.wait(2.5)

        # ---------------- 结论 ----------------
        conclusion = VGroup(
            Text(
                "GP 交给实验设计的不是答案，而是——",
                font=FONT,
                font_size=26,
                color=C_TEXT,
            ),
            Text(
                "下一轮最该往哪里测",
                font=FONT,
                font_size=34,
                color=C_YELLOW,
            ),
        ).arrange(DOWN, buff=0.25)
        conclusion.move_to([0.2, -3.3, 0])

        self.play(
            FadeOut(area_note),
            FadeOut(area_box),
            FadeOut(cand_label),
            FadeOut(cand_box),
            FadeIn(conclusion, shift=UP * 0.15),
            run_time=1.8,
        )
        self.wait(9.0)