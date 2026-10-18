# -*- coding: utf-8 -*-
"""把 §10 第 1 条补注那段的排版修顺（三连空格 → 正常句子连接）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
s8 = ROOT / "5_Reference/08_工作流/Stage8_建模与验证方案.md"
t = s8.read_text(encoding="utf-8")
old = "（D75：正定性在 N=2…6 上非单调）。   拟合完立刻跑 `python"
new = "（D75：正定性在 N=2…6 上非单调）。此外，**拟合完立刻跑** `python"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)

# 落纸脚本同步
ap = ROOT / "1_Code/DDM_Core/_scratch/_apply_d76.py"
s = ap.read_text(encoding="utf-8")
old2 = 'add = ("   拟合完立刻跑 `python -X utf8 1_Code\\\\DDM_Core\\\\stage8_health.py "'
new2 = 'add = ("此外，**拟合完立刻跑** `python -X utf8 1_Code\\\\DDM_Core\\\\stage8_health.py "'
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2)
ap.write_text(s, encoding="utf-8", newline="\n")

s8.write_text(t, encoding="utf-8", newline="\n")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("已修：Stage 8 §10 第 1 条补注排版；落纸脚本同步")
