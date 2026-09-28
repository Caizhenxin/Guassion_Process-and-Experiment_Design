"""S3：条件化 —— 数据进来之后，GP 变成后验。

叙事作用：本幕是整个演示的核心。让听众看到三件事同时发生：
  1. 曲线束被观测点"钉住"；
  2. 不确定度带在数据附近收窄、在远处张开；
  3. σ(x) 曲线在观测点处下探到 0。
这正是 GP 能回答"没测过的点会怎样"的机制来源。
时长约 60 秒。
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
    C_GREEN,
    C_ORANGE,
    C_TEXT,
    C_YELLOW,
    FONT,
    OBS_X,
    OBS_Y,
    demo_axes,
    gp_demo_grid,
    gp_posterior,
    gp_posterior_samples,
    gp_prior_samples,
    make_band,
    make_curve,
)

# 必须与 s2_gp_prior.py 保持一致
LENGTH_SCALE = 0.75
VARIANCE = 0.55
SEED = 11
N_SAMPLES = 6
NOISE = 0.02


class S3GPPosterior(Scene):
    def construct(self):
        self.camera.background_color = BG

        axes = demo_axes()
        x = gp_demo_grid()

        prior = gp_prior_samples(
            x, n_samples=N_SAMPLES, length_scale=LENGTH_SCALE, variance=VARIANCE, seed=SEED
        )
        post = gp_posterior_samples(
            x,
            OBS_X,
            OBS_Y,
            n_samples=N_SAMPLES,
            length_scale=LENGTH_SCALE,
            variance=VARIANCE,
            noise=NOISE,
            seed=SEED,
        )
        mu_post, sigma_post = gp_posterior(
            x, OBS_X, OBS_Y, length_scale=LENGTH_SCALE, variance=VARIANCE, noise=NOISE
        )

        sigma_prior = np.sqrt(VARIANCE)
        zeros = np.zeros_like(x)

        # ---------------- 与 S2 结尾完全一致的起始画面 ----------------
        curves = VGroup(
            *[
                make_curve(axes, x, prior[:, i], C_BLUE, stroke_width=3.5, opacity=0.9)
                for i in range(N_SAMPLES)
            ]
        )
        band = make_band(axes, x, zeros, np.full_like(x, sigma_prior), k=2.0,
                         color=C_YELLOW, opacity=0.14)
        mu_line = make_curve(axes, x, zeros, C_TEXT, stroke_width=5, opacity=0.9)

        hint_next = Text(
            "现在，把真实观测到的数据放进去",
            font=FONT,
            font_size=26,
            color=C_ORANGE,
        )
        hint_next.to_edge(DOWN, buff=0.6)

        self.add(axes, band, curves, mu_line, hint_next)
        self.wait(1.0)
        self.play(FadeOut(hint_next), run_time=0.8)

        # ---------------- 观测点落入 ----------------
        for xi, yi in zip(OBS_X, OBS_Y):
            pt = axes.c2p(xi, yi)
            dot = Dot(pt, radius=0.11, color=C_ORANGE)
            ring = Circle(radius=0.35, stroke_color=C_ORANGE, stroke_width=2.5).move_to(pt)
            self.play(GrowFromCenter(dot), Create(ring), run_time=0.55)
            self.play(FadeOut(ring), run_time=0.35)
        self.wait(0.4)

        obs_note = Text(
            "两个点已被观测：函数必须穿过它们",
            font=FONT,
            font_size=24,
            color=C_ORANGE,
        )
        obs_note.to_edge(DOWN, buff=0.6)
        self.play(FadeIn(obs_note, shift=UP * 0.2), run_time=1.2)
        self.wait(1.6)

        # ---------------- 先验曲线 → 后验曲线 ----------------
        post_curves = [
            make_curve(axes, x, post[:, i], C_BLUE, stroke_width=3.5, opacity=0.9)
            for i in range(N_SAMPLES)
        ]
        self.play(
            *[Transform(c, pc) for c, pc in zip(curves, post_curves)],
            run_time=11.0,
        )
        self.wait(0.8)

        # ---------------- 不确定度带的收窄与张开 ----------------
        post_band = make_band(axes, x, mu_post, sigma_post, k=2.0, color=C_YELLOW, opacity=0.22)
        post_mu = make_curve(axes, x, mu_post, C_TEXT, stroke_width=5, opacity=0.95)

        self.play(
            Transform(band, post_band),
            Transform(mu_line, post_mu),
            run_time=6.0,
        )
        self.wait(0.8)

        # ---------------- σ(x) 插图 ----------------
        sigma_norm = sigma_post / sigma_prior
        inset = Axes(
            x_range=[-3.2, 3.2, 1],
            y_range=[0, 1.15, 0.5],
            x_length=4.4,
            y_length=1.15,
            axis_config={
                "color": C_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        inset.move_to([2.85, -2.35, 0])

        sigma_curve = make_curve(inset, x, sigma_norm, C_YELLOW, stroke_width=3, opacity=1.0)
        sigma_title = Text("不确定度 σ(x)", font=FONT, font_size=19, color=C_YELLOW)
        sigma_title.next_to(inset, UP, buff=0.12)

        sigma_marks = VGroup(
            *[
                DashedLine(
                    inset.c2p(xi, 0),
                    inset.c2p(xi, 1.15),
                    dash_length=0.06,
                    stroke_color=C_ORANGE,
                    stroke_width=1.6,
                )
                for xi in OBS_X
            ]
        )

        self.play(
            FadeIn(inset),
            FadeIn(sigma_title),
            run_time=1.5,
        )
        self.play(Create(sigma_curve), run_time=2.2)
        self.play(FadeIn(sigma_marks), run_time=1.0)
        self.wait(0.6)

        # ---------------- 标注关键位置 ----------------
        left_mark = axes.c2p(OBS_X[0], OBS_Y[0])
        right_mark = axes.c2p(OBS_X[1], OBS_Y[1])

        label_center = Text(
            "数据附近\nσ → 0",
            font=FONT,
            font_size=19,
            color=C_GREEN,
            line_spacing=0.7,
        )
        label_center.next_to(left_mark, UP, buff=0.35)

        label_far = Text(
            "远离数据\nσ 张开",
            font=FONT,
            font_size=19,
            color=C_ORANGE,
            line_spacing=0.7,
        )
        label_far.next_to(axes.c2p(-3.05, 0.0), UP, buff=1.75)

        self.play(FadeIn(label_center, shift=DOWN * 0.15), run_time=1.0)
        self.play(FadeIn(label_far, shift=DOWN * 0.15), run_time=1.0)
        self.wait(1.5)

        # ---------------- 结论 ----------------
        conclusion = VGroup(
            Text(
                "后验给出的不是「一个答案」，而是",
                font=FONT,
                font_size=28,
                color=C_TEXT,
            ),
            Text(
                "每个未测点上的「预测值 + 不确定度」",
                font=FONT,
                font_size=32,
                color=C_YELLOW,
            ),
        ).arrange(DOWN, buff=0.3)
        conclusion.to_edge(UP, buff=0.5)

        self.play(
            FadeOut(obs_note),
            FadeOut(label_far),
            FadeOut(label_center),
            FadeOut(inset),
            FadeOut(sigma_title),
            FadeOut(sigma_curve),
            FadeOut(sigma_marks),
            FadeIn(conclusion, shift=DOWN * 0.2),
            run_time=1.8,
        )
        self.wait(10.0)