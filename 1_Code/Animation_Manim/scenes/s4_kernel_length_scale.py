"""S4：核函数的作用 —— length_scale 控制「假设函数有多光滑」。

叙事作用：GP 的行为不是凭空来的，它由核函数里的 length_scale（ℓ）决定。
滑动 ℓ 可以看到"敢不敢外推"与"能不能抓住细节"之间的权衡。
本幕用的 ℓ 取值区间与项目里 5 个残差 GP 的实际拟合结果一致。
时长约 34 秒。
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
    FITTED_LS_RANGE,
    FONT,
    OBS_X,
    OBS_Y,
    demo_axes,
    gp_demo_grid,
    gp_posterior,
    gp_posterior_samples,
    make_band,
    make_curve,
)

# 与 S2/S3 保持一致的 GP 设置
VARIANCE = 0.55
SEED = 11
N_SAMPLES = 6
NOISE = 0.02
LS_INIT = 0.75

# 演示曲线用较稀的网格：每帧都要重算后验协方差的特征分解
DEMO_N = 180

# 滑杆把 ℓ 映射到屏幕横坐标
LS_LO, LS_HI = 0.25, 2.0
TRACK_X0, TRACK_X1 = -5.6, -0.6
TRACK_Y = -2.0
CAPTION_POS = np.array([0.6, -3.15, 0.0])


def ls_to_x(ls):
    return TRACK_X0 + (ls - LS_LO) / (LS_HI - LS_LO) * (TRACK_X1 - TRACK_X0)


class S4KernelLengthScale(Scene):
    def construct(self):
        self.camera.background_color = BG

        axes = demo_axes()
        x = gp_demo_grid(DEMO_N)
        ls = ValueTracker(LS_INIT)

        def posterior_group():
            """按当前 ℓ 重算后验曲线束、不确定度带与均值线。"""
            length_scale = ls.get_value()
            post = gp_posterior_samples(
                x,
                OBS_X,
                OBS_Y,
                n_samples=N_SAMPLES,
                length_scale=length_scale,
                variance=VARIANCE,
                noise=NOISE,
                seed=SEED,
            )
            mu, sigma = gp_posterior(
                x, OBS_X, OBS_Y, length_scale=length_scale, variance=VARIANCE, noise=NOISE
            )
            band = make_band(axes, x, mu, sigma, k=2.0, color=C_YELLOW, opacity=0.22)
            curves = VGroup(
                *[
                    make_curve(axes, x, post[:, i], C_BLUE, stroke_width=3.5, opacity=0.9)
                    for i in range(N_SAMPLES)
                ]
            )
            mean_line = make_curve(axes, x, mu, C_TEXT, stroke_width=5, opacity=0.95)
            return VGroup(band, curves, mean_line)

        obs_dots = VGroup(
            *[
                Dot(axes.c2p(xi, yi), radius=0.11, color=C_ORANGE)
                for xi, yi in zip(OBS_X, OBS_Y)
            ]
        )

        # 承接 S3 结尾的画面状态
        conclusion = VGroup(
            Text("后验给出的不是「一个答案」，而是", font=FONT, font_size=28, color=C_TEXT),
            Text("每个未测点上的「预测值 + 不确定度」", font=FONT, font_size=32, color=C_YELLOW),
        ).arrange(DOWN, buff=0.3)
        conclusion.to_edge(UP, buff=0.5)

        dynamic = always_redraw(posterior_group)
        self.add(axes, dynamic, obs_dots, conclusion)
        self.wait(0.8)
        self.play(FadeOut(conclusion), run_time=1.0)

        # ---------------- 引入 length_scale ----------------
        title = Text(
            "GP 的行为由一个关键假设决定：length_scale ℓ",
            font=FONT,
            font_size=28,
            color=C_TEXT,
        )
        title.to_edge(UP, buff=0.45)
        self.play(FadeIn(title, shift=DOWN * 0.2), run_time=1.5)

        track = Line(
            [TRACK_X0, TRACK_Y, 0], [TRACK_X1, TRACK_Y, 0],
            stroke_color=C_DIM, stroke_width=3,
        )
        track_lo = Text("0.25", font=FONT, font_size=18, color=C_DIM).next_to(
            [TRACK_X0, TRACK_Y, 0], DOWN, buff=0.15
        )
        track_hi = Text("2.0", font=FONT, font_size=18, color=C_DIM).next_to(
            [TRACK_X1, TRACK_Y, 0], DOWN, buff=0.15
        )
        knob = always_redraw(
            lambda: Dot(
                [ls_to_x(ls.get_value()), TRACK_Y, 0], radius=0.13, color=C_YELLOW
            )
        )
        ls_label = always_redraw(
            lambda: Text(
                f"ℓ = {ls.get_value():.2f}",
                font=FONT,
                font_size=26,
                color=C_YELLOW,
            ).next_to([TRACK_X1, TRACK_Y, 0], RIGHT, buff=0.35)
        )
        slider_hint = Text(
            "← 假设函数变化剧烈        假设函数平缓 →",
            font=FONT,
            font_size=18,
            color=C_DIM,
        )
        slider_hint.next_to([(TRACK_X0 + TRACK_X1) / 2, TRACK_Y, 0], DOWN, buff=0.45)

        self.play(
            Create(track),
            FadeIn(track_lo),
            FadeIn(track_hi),
            FadeIn(knob),
            FadeIn(ls_label),
            FadeIn(slider_hint),
            run_time=1.5,
        )
        self.wait(0.6)

        # ---------------- ℓ 变小：假设变化剧烈 ----------------
        cap_small = Text(
            "ℓ 小：只敢相信数据附近，\n离开观测点很快就不确定",
            font=FONT,
            font_size=22,
            color=C_ORANGE,
            line_spacing=0.75,
        )
        cap_small.move_to([2.9, -2.35, 0])

        self.play(ls.animate.set_value(0.30), run_time=4.5, rate_func=smooth)
        self.play(FadeIn(cap_small, shift=UP * 0.2), run_time=1.3)
        self.wait(2.2)

        # ---------------- ℓ 变大：假设平缓 ----------------
        cap_large = Text(
            "ℓ 大：外推更远，\n但细节会被抹平",
            font=FONT,
            font_size=22,
            color=C_ORANGE,
            line_spacing=0.75,
        )
        cap_large.move_to([2.9, -2.35, 0])

        self.play(
            FadeOut(cap_small),
            ls.animate.set_value(1.80),
            run_time=5.5,
            rate_func=smooth,
        )
        self.play(FadeIn(cap_large, shift=UP * 0.2), run_time=1.3)
        self.wait(2.2)

        # ---------------- 回到项目实际取值 ----------------
        self.play(
            FadeOut(cap_large),
            ls.animate.set_value(LS_INIT),
            run_time=3.5,
            rate_func=smooth,
        )

        footer = Text(
            f"项目里 5 个 GP 的 ℓ 由边际似然自动优化：{FITTED_LS_RANGE[0]:.2f} ~ {FITTED_LS_RANGE[1]:.2f}"
            "（归一化空间）",
            font=FONT,
            font_size=21,
            color=C_DIM,
        )
        footer.move_to([2.9, -2.35, 0])
        self.play(FadeIn(footer, shift=UP * 0.2), run_time=1.5)
        self.wait(4.0)