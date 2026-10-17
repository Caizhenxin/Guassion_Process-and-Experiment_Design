# -*- coding: utf-8 -*-
"""D71 的一处口径收紧（合成真值的正确率只有 0.577，门槛 0.55 ⇒ 边际性）。

用法：python -X utf8 -u _patch_d71_margin.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S6 = REPO / "5_Reference" / "08_工作流" / "Stage6_Pilot方案.md"
S7 = REPO / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

MARGIN = (
    "（补注（D71 收紧）：该合成真值的**组层正确率只有 0.577**，而门槛是 0.55 —— 差值 0.027 ≈ **1.3 个逐被试 SE**"
    "（二项 SE ≈ 0.021，n ≈ 570 反应试次）。所以「约一半被试落在门下」是**阈值边际性**的可预期后果，"
    "不是判据错；真实数据若正确率约 0.7，触发率会显著更低。本条要钉的是「复核 ≠ 剔除」的**语义**，"
    "以及不得为了让复核名单好看而放宽阈值。）"
)

JOBS = [
    (MP, "P4/P5 静态（两分支不共用累加器；S6-2c 仍与 S6-2 分开判）。 |", MARGIN),
    (S6, "机器断言见 `1_Code/Experiment/exp_Check/check_pilot_ready.py`（9/9）。", MARGIN),
    (S7, "现场不得把「待复核」当剔除用，也不得为了让复核人数好看而放宽阈值。", MARGIN),
    (RD, "把「待复核」当人工复核信号，报告里报「复核率」而非「剔除率」。", MARGIN),
]


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}")
    for path, anchor, add in JOBS:
        text = path.read_text(encoding="utf-8")
        assert "\r" not in text, f"{path.name} 含 CRLF"
        if add[:12] in text:
            print(f"  [跳过] {path.name}（已收紧）")
            continue
        n = text.count(anchor)
        assert n == 1, f"{path.name}：锚点命中 {n} 处"
        text = text.replace(anchor, anchor + add)
        if APPLY:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"  [写入] {path.name}")
        else:
            print(f"  [干跑] {path.name}：+{len(add)} 字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
