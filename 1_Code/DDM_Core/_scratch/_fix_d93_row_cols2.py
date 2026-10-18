# -*- coding: utf-8 -*-
"""决策表 5 列、进度表 5 列：给 D93/D94/首场回归三行补第 4 列「落地件」。"""
import io
from pathlib import Path

P = Path("5_Reference/08_工作流/工作流_主计划.md")
lines = io.open(P, encoding="utf-8").read().split("\n")

FIX = {
    "| **D93**": (
        "`Exp_Design_Formal.m`（v4.8 → **v4.9**，1494 行）+ `test/run_full_session.m`"
        "（`nPracExpected`/B17）+ `test/check_full_session.py`（**34/34**，+A15/B31）"
        "+ `_scratch/_apply_d93_practice_floor.py` / `_apply_d93_driver.py` / `_apply_d93_b17.py`（补丁）"
    ),
    "| **D94**": (
        "`1_Code/Experiment/qc_group.py`（**466 行**：`(stage, trialID)` 去重、`n_dropped`、"
        "汇总表「去重行」列）+ `_scratch/_apply_d94_qc_dedupe.py`（补丁）"
    ),
    "| 2026-10-18 | **6（首场真实数据回归）**": (
        "`Exp_Design_Formal.m` **v4.9**、`qc_group.py` **466 行**、"
        "`test/check_full_session.py` **34/34**、冒烟组 1/组 2 各 **27/27**"
    ),
}

done = 0
for i, ln in enumerate(lines):
    for key, cell in FIX.items():
        if ln.startswith(key):
            body = ln.rstrip()
            assert body.endswith("|"), body[-40:]
            cells = [c.strip() for c in body.strip().strip("|").split("|")]
            assert len(cells) == 4, (key, len(cells))
            cells.insert(3, cell)
            lines[i] = "| " + " | ".join(cells) + " |"
            done += 1

assert done == 3, done
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("ok, patched", done)
