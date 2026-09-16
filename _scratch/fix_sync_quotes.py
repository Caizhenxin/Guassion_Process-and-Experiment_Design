# -*- coding: utf-8 -*-
"""临时：修掉 sync_refit_to_abstract.py 中的引号问题。"""
import ast
from pathlib import Path

p = Path(__file__).resolve().parent / "sync_refit_to_abstract.py"
s = p.read_text(encoding="utf-8")
bad = '而"自我 vs 陌生人"的'
good = '而「自我 vs 陌生人」的'
print("命中:", s.count(bad))
s = s.replace(bad, good)
try:
    ast.parse(s)
    print("语法 OK")
except SyntaxError as e:
    print("仍有错误 行", e.lineno, e.msg)
    lines = s.splitlines()
    for i in range(max(0, e.lineno - 4), min(len(lines), e.lineno + 2)):
        print(f"  {i+1}: {lines[i][:150]}")
p.write_text(s, encoding="utf-8")
