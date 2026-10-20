# -*- coding: utf-8 -*-
"""D107 的下一问：既然 design 真值下 P<40 全是零漂移，那 P 水平该怎么放？

加三套「中段」方案（全部 ≥40），跑一遍看需人数能不能从 37 再降。
"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\design_search.py")
s = p.read_text(encoding="utf-8")
old = '''        "两级 0/120": [0, 120],'''
new = '''        "两级 0/120": [0, 120],
        # D107 第二轮：design 真值下 P<40 漂移被 max(0,·) 截到 0，中段方案全部 ≥40
        "中段 40/60/90/120": [40, 60, 90, 120],
        "中段+高 40/80/120/180/240": [40, 80, 120, 180, 240],
        "中段密 40/55/70/90/120": [40, 55, 70, 90, 120],'''
assert s.count(old) == 1
s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("ok")
