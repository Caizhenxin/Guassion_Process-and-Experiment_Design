# -*- coding: utf-8 -*-
"""把主计划里的 D92 产出文件行补成两列（该表是「文件 | 用途」两列表）。"""
from pathlib import Path

PLAN = Path("5_Reference/08_工作流/工作流_主计划.md")
lines = PLAN.read_text(encoding="utf-8").split("\n")
i = next(k for k, ln in enumerate(lines)
         if ln.startswith("| `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.7 →"))
row = lines[i]
assert row.count("|") == 2, f"本行竖线数 {row.count('|')}，预期 2"
body = row.strip().strip("|").strip()
lines[i] = (f"| {body} "
            f"| **D92**：路径可移植（`progDir` + 10 张 PNG 启动自检 + `run_selftest.bat` + `check_portability.m` 6/6） |")
PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("D92 产出文件行已补成两列")
