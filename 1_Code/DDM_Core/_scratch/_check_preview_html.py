# -*- coding: utf-8 -*-
"""检查 preview HTML 的结构（标题、表格、公式、图）。"""
import re
from pathlib import Path

p = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design/5_Reference/06_进展与汇报/项目全景预览_v1.html")
s = p.read_text(encoding="utf-8")
print("size", len(s), "bytes")
print("tables", s.count("<table>"), "| eq cards", s.count('class="eq"'),
      "| img", s.count("<img"), "| h2", s.count("<h2"), "| h3", s.count("<h3"))
print("latex fallback", s.count('class="latex"'))
for m in re.finditer(r'<h2 id="([^"]+)"><span class="sn">(\d+)</span>([^<]+)', s):
    print("  ", m.group(2), m.group(3)[:44], "->", m.group(1))
print("broken hrefs (no matching id):")
ids = set(re.findall(r'id="([^"]+)"', s))
for h in set(re.findall(r'href="#([^"]+)"', s)):
    if h not in ids:
        print("   MISSING", h)
