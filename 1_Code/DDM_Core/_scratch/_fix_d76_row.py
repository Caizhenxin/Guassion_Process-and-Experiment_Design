# -*- coding: utf-8 -*-
"""主计划 §8 的 D76 文件行：把多出来的日期单元格并回说明格（#8 表只有两列）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
mp = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
t = mp.read_text(encoding="utf-8")
old = "判词一致 | 2026-10-17（D76） |"
new = "判词一致（**D76**，2026-10-17） |"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)
mp.write_text(t, encoding="utf-8", newline="\n")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("已修：主计划 §8 D76 文件行 → 2 列")
