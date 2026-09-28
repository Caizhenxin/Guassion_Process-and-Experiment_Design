"""S2：高斯过程是什么 —— 从先验中采样"一族函数"。

叙事作用：建立核心观念——GP 给出的不是一个点估计，而是函数的分布。
时长约 45 秒。
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
    demo_axes,
    gp_demo_grid,
    gp_prior_samples,
    make_band,
    make_curve,
)

# S2 / S3 必须使用完全相同的 GP 超参数与随机种子，保证两幕画面能无缝衔接
LENGTH_SCALE = 0.75
VARIANCE = 0.55
SEED = 11
N_SAMPLES = 6


class S2GPPrior(Scene):
    def construct(self):
        self.camera.background_color = BG

        axes = demo_axes()
        x = gp_demo_grid()
        samples = gp_prior_samples(
            x, n_samples=N_SAMPLES, length_scale=LENGTH_SCALE, variance=VARIANCE, seed=SEED
        )

        title = Text(
            "高斯过程：不是拟合一条曲线，而是给出一族曲线",
            font=FONT,
            font_size=30,
            color=C_TEXT,
        )
        title.to_edge(UP, buff=0.55)

        x_hint = Text(
            "设计变量（例如 T：刺激呈现时间）",
            font=FONT,
            font_size=20,
            color=C_DIM,
        )
        x_hint.next_to(axes.c2p(0, 0), DOWN, buff=1.35).shift(RIGHT * 2.1)

        y_hint = Text(
            "效果\n（例如 SPE_v）",
            font=FONT,
            font_size=20,
            color=C_DIM,
            line_spacing=0.7,
        )
        y_hint.next_to(axes.c2p(0, 0), LEFT, buff=0.25).shift(UP * 1.55)

        self.play(Create(axes), run_time=1.5)
        self.play(Write(title), run_time=1.6)
        self.play(FadeIn(x_hint), FadeIn(y_hint), run_time=1.2)

        # ---------------- 先验采样 ----------------
        curves = VGroup(
            *[
                make_curve(axes, x, samples[:, i], C_BLUE, stroke_width=3.5, opacity=0.9)
                for i in range(N_SAMPLES)
            ]
        )

        prior_note = Text(
            "先验：还没看到任何数据时，我们认为函数可能长什么样",
            font=FONT,
            font_size=24,
            color=C_BLUE,
        )
        prior_note.to_edge(DOWN, buff=0.6)

        self.play(
            LaggedStart(*[Create(c) for c in curves], lag_ratio=0.4),
            run_time=13.0,
        )
        self.play(FadeIn(prior_note, shift=UP * 0.2), run_time=1.4)
        self.wait(1.5)

        # ---------------- 先验的均值和不确定度 ----------------
        mu_prior = np.zeros_like(x)
        sigma_prior = np.full_like(x, np.sqrt(VARIANCE))

        band = make_band(axes, x, mu_prior, sigma_prior, k=2.0, color=C_YELLOW, opacity=0.14)
        mu_line = make_curve(axes, x, mu_prior, C_TEXT, stroke_width=5, opacity=0.95)
        mu_line.set_stroke(opacity=0.9)

        band_note = Text(
            "μ(x) = 0，±2σ 处处相同 —— 这就是「先验」的全部内容",
            font=FONT,
            font_size=22,
            color=C_YELLOW,
        )
        band_note.next_to(prior_note, UP, buff=0.25)

        self.play(FadeIn(band), run_time=2.2)
        self.play(Create(mu_line), run_time=1.6)
        self.play(FadeIn(band_note), run_time=1.2)
        self.wait(2.0)

        # ---------------- 收束到下一幕 ----------------
        # 注意：S3 的起始画面会精确复现这里留下的状态，
        # 因此本幕收尾必须把标题、轴标注等全部清掉，只留下
        # 坐标系 / 曲线束 / 不确定度带 / 均值线 / hint_next。
        hint_next = Text(
            "现在，把真实观测到的数据放进去",
            font=FONT,
            font_size=26,
            color=C_ORANGE,
        )
        hint_next.to_edge(DOWN, buff=0.6)

        self.play(
            FadeOut(title),
            FadeOut(band_note),
            FadeOut(prior_note),
            FadeOut(x_hint),
            FadeOut(y_hint),
            FadeIn(hint_next),
            run_time=1.5,
        )
        self.wait(8.0)