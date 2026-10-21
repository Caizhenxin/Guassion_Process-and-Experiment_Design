# -*- coding: utf-8 -*-
"""列出 preview HTML 里所有 h3 id（用于定位插图锚点）。"""
import re
from pathlib import Path

p = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design/5_Reference/06_进展与汇报/项目全景预览_v1.html")
s = p.read_text(encoding="utf-8")
for m in re.finditer(r'<h3 id="([^"]+)">(.{0,40})', s):
    print(m.group(1), "|", re.sub(r"<[^>]+>", "", m.group(2)))
