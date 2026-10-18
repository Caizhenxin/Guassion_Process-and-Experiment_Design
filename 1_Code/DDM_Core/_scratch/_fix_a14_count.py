# -*- coding: utf-8 -*-
"""修正 A14 的期望计数：fullfile(progDir, f) 实际 3 处（1 处自检 + 2 处列表）。"""
from pathlib import Path

F = Path("1_Code/Experiment/exp_matlab/test/check_full_session.py")
src = F.read_text(encoding="utf-8")
old = '      and code.count("fullfile(progDir, f)") == 2\n'
new = '      and code.count("fullfile(progDir, f)") == 3   # 1 处 PNG 自检 + 2 处纹理列表\n'
assert src.count(old) == 1, f"命中 {src.count(old)} 次"
F.write_text(src.replace(old, new), encoding="utf-8", newline="\n")
print("A14 期望计数已改为 3")
