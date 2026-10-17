# -*- coding: utf-8 -*-
"""修 D74 落纸的两个竖线：表格单元里写了裸 `|θ|`，把 5 列表格撑成 10 列。

用法：python -X utf8 -u _fix_d74_pipes.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

TARGETS = [
    REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md",
    REPO / "1_Code" / "DDM_Core" / "README.md",
]
OLD = "|θ|"
NEW = r"\|θ\|"

for f in TARGETS:
    t = f.read_text(encoding="utf-8")
    n = t.count(OLD)
    if not n:
        print(f"  [跳过] {f.name}（无裸 `|θ|`）")
        continue
    t = t.replace(OLD, NEW)
    if APPLY:
        f.write_text(t, encoding="utf-8", newline="\n")
    print(f"  [{'写入' if APPLY else '干跑'}] {f.name}：替换 {n} 处")
