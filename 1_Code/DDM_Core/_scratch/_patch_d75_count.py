# -*- coding: utf-8 -*-
"""把 D75 落纸里的 checker 计数从 36/36 更新为 37/37（新增 A14：不得印 `****`）。幂等。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

TARGETS = [
    REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md",
    REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md",
    REPO / "1_Code" / "DDM_Core" / "README.md",
]
SUBS = [
    ("`check_stage8_run.py` **34 → 36/36**（A13/A13b）", "`check_stage8_run.py` **34 → 37/37**（A13/A13b/A14）"),
    ("（36/36，A13/A13b）", "（37/37，A13/A13b/A14）"),
    ("`check_stage8_run.py` 34 → 36/36。", "`check_stage8_run.py` 34 → 37/37（A14 补「不得印空粗体 `****`」）。"),
    ("（**36/36**，A13/A13b）", "（**37/37**，A13/A13b/A14）"),
    ("34 → **36/36**（A13/A13b）", "34 → **37/37**（A13/A13b/A14）"),
    ("**34 → 36/36**（A13 必须印、A13b 不得静默省略）",
     "**34 → 37/37**（A13 必须印、A13b 不得静默省略、A14 不得印空粗体 `****`）"),
    ("**34 → 36/36**（A13/A13b）", "**34 → 37/37**（A13/A13b/A14）"),
]

for p in TARGETS:
    t = p.read_text(encoding="utf-8")
    n = 0
    for old, new in SUBS:
        if old in t:
            t = t.replace(old, new)
            n += 1
    print(f"{'[写入]' if APPLY and n else '[跳过]' if not n else '[干跑]'} {p.name}：命中 {n}/{len(SUBS)} 条替换")
    if APPLY and n:
        p.write_text(t, encoding="utf-8", newline="\n")
