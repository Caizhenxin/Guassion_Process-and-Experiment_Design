"""S8：收尾 —— GP 在项目里的确切位置。

叙事作用：把整片的落点收成一句可复述的话，并给出混合模型的架构图，
让听众离开时能记住"理论 + 数据驱动修正"这条主线。
时长约 24 秒。
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
)

BOX_W, BOX_H = 2.75, 1.25
BOX_Y = 1.3
GAP = 0.65


def make_box(label, sublabel, color):
    rect = RoundedRectangle(
        corner_radius=0.12,
        width=BOX_W,
        height=BOX_H,
        stroke_color=color,
        stroke_width=2,
        fill_color=color,
        fill_opacity=0.10,
    )
    text = Text(label, font=FONT, font_size=21, color=color)
    if sublabel:
        sub = Text(sublabel, font=FONT, font_size=17, color=C_DIM)
        body = VGroup(text, sub).arrange(DOWN, buff=0.12)
    else:
        body = VGroup(text)
    body.move_to(rect.get_center())
    return VGroup(rect, body)


class S8Closing(Scene):
    def construct(self):
        self.camera.background_color = BG

        labels = [
            ("(P, T, W)", "设计空间", C_BLUE),
            ("Sigmoid", "理论先验", C_ORANGE),
            ("GP", "残差修正", C_YELLOW),
            ("DDM 参数", "→ 行为数据", C_TEXT),
        ]

        boxes = VGroup(*[make_box(a, b, c) for a, b, c in labels])
        boxes.arrange(RIGHT, buff=GAP)
        boxes.move_to([0, BOX_Y, 0])

        arrows = VGroup(
            *[
                Arrow(
                    boxes[i].get_right(),
                    boxes[i + 1].get_left(),
                    buff=0.1,
                    stroke_color=C_DIM,
                    stroke_width=2.5,
                    max_tip_length_to_length_ratio=0.3,
                )
                for i in range(len(boxes) - 1)
            ]
        )

        title = Text(
            "GP 在项目里的位置",
            font=FONT,
            font_size=28,
            color=C_TEXT,
        )
        title.to_edge(UP, buff=0.6)

        self.play(FadeIn(title, shift=DOWN * 0.2), run_time=1.2)
        self.play(
            LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in boxes], lag_ratio=0.25),
            run_time=2.5,
        )
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.3), run_time=1.5)
        self.wait(1.5)

        # ---------------- 一句话落点 ----------------
        takeaway = VGroup(
            Text(
                "理论负责给出「应该是什么样」",
                font=FONT,
                font_size=26,
                color=C_ORANGE,
            ),
            Text(
                "GP 负责指出「哪里还不知道」",
                font=FONT,
                font_size=26,
                color=C_YELLOW,
            ),
        ).arrange(DOWN, buff=0.3)
        takeaway.move_to([0, -0.6, 0])

        self.play(FadeIn(takeaway, shift=UP * 0.2), run_time=1.6)
        self.wait(3.0)

        # ---------------- 结束卡 ----------------
        end_card = VGroup(
            Text(
                "自我优势效应的实验设计空间优化",
                font=FONT,
                font_size=30,
                color=C_TEXT,
            ),
            Text(
                "高斯过程（Gaussian Process）原理演示",
                font=FONT,
                font_size=21,
                color=C_DIM,
            ),
        ).arrange(DOWN, buff=0.25)
        end_card.move_to([0, -2.55, 0])

        self.play(FadeIn(end_card, shift=UP * 0.2), run_time=1.6)
        self.wait(6.0)