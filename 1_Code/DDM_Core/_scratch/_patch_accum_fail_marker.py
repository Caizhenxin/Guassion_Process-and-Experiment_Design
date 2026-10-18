# -*- coding: utf-8 -*-
"""给 check_data_accum.m 的失败分支加 ASCII 'FAIL' 标记（GBK 控制台下 ✅/❌ 会变 '?'）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\test\check_data_accum.m")
t = p.read_text(encoding="utf-8")
old = "fprintf('  \u274c %s \uff5c %s\\n', name, detail);"
new = "fprintf('  FAIL %s \uff5c %s\\n', name, detail);"
if new in t:
    print("已打过")
elif old in t:
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8", newline="\n")
    print("patched")
else:
    print("MISS")
