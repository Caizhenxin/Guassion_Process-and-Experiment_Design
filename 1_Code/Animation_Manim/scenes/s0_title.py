"""S0：开场标题 —— 提出问题。

叙事作用：用一句话把听众的注意力引到"未被测量区域"这个核心矛盾上。
时长约 15 秒。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manim import *  # noqa: E402

from common import (  # noqa: E402
    BG,
    C_BLUE,
    C_DIM,
    C_ORANGE,
    C_TEXT,
    FONT,
    load_real_conditions,
)


class S0Title(Scene):
    def construct(self):
        self.camera.background_color = BG

        title = Text(
            "自我优势效应的实验设计空间优化",
            font=FONT,
            font_size=46,
            color=C_TEXT,
        )
        title.move_to(UP * 2.0)

        subtitle = Text(
            "高斯过程（Gaussian Process）原理演示",
            font=FONT,
            font_size=28,
            color=C_BLUE,
        )
        subtitle.next_to(title, DOWN, buff=0.55)

        # 6 个真实条件的小圆点，暗示"我们只有这么几个观测点"
        conditions = load_real_conditions()
        dots = VGroup(
            *[
                Dot(radius=0.11, color=C_ORANGE, fill_opacity=0.95)
                for _ in conditions
            ]
        ).arrange(RIGHT, buff=0.55)
        dots.move_to(DOWN * 1.35)

        dots_caption = Text(
            "6 个已完成的实验条件",
            font=FONT,
            font_size=22,
            color=C_DIM,
        )
        dots_caption.next_to(dots, DOWN, buff=0.35)

        question = Text(
            "没测过的设计点，会是什么样？",
            font=FONT,
            font_size=34,
            color=C_ORANGE,
        )
        question.move_to(DOWN * 2.9)

        underline = Line(
            question.get_corner(DL) + DOWN * 0.12,
            question.get_corner(DR) + DOWN * 0.12,
            stroke_color=C_ORANGE,
            stroke_width=2,
        )

        self.play(Write(title), run_time=2.4)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=1.4)
        self.wait(0.8)

        self.play(
            LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.18),
            run_time=2.2,
        )
        self.play(FadeIn(dots_caption), run_time=1.0)
        self.wait(0.8)

        self.play(FadeIn(question, shift=UP * 0.25), run_time=1.5)
        self.play(Create(underline), run_time=0.8)
        self.wait(3.5)