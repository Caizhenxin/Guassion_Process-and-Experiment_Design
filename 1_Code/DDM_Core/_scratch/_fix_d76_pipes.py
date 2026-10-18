# -*- coding: utf-8 -*-
"""修主计划 §8 的 D76 文件行：#8 表只有两列，我多写了一个日期单元格。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mp = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
t = mp.read_text(encoding="utf-8")
old = "与两次报告里的判词一致 | 2026-10-17（D76） |"
new = "与两次报告里的判词一致（**D76**，2026-10-17） |"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)

# 同步落纸脚本，保证复跑仍是 2 列
ap = ROOT / "1_Code/DDM_Core/_scratch/_apply_d76.py"
s = ap.read_text(encoding="utf-8")
old2 = '"与两次报告里的判词一致 "\n    "| 2026-10-17（D76） |"'
new2 = '"与两次报告里的判词一致（**D76**，2026-10-17） |"'
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2)
ap.write_text(s, encoding="utf-8", newline="\n")

mp.write_text(t, encoding="utf-8", newline="\n")
print("已修：主计划 §8 D76 文件行改为 2 列（日期并入说明格），落纸脚本同步")
