# -*- coding: utf-8 -*-
"""拼装 v4 正文：新写的第一部分 + 沿用 v3.1 的第 5–7 章 + 新写的第 8–11 章 + 沿用参考文献/附录。"""
from __future__ import annotations

import io
from pathlib import Path

BASE = Path(__file__).resolve().parents[3] / "5_Reference" / "03_论文写作"
EXP = BASE / "_v31_export.md"
P1 = BASE / "_v4_part1.md"
P2 = BASE / "_v4_part2.md"
OUT = BASE / "_v4_正文.md"

exp = io.open(EXP, encoding="utf-8").read()
p1 = io.open(P1, encoding="utf-8").read()
p2 = io.open(P2, encoding="utf-8").read()

i5 = exp.index("# 第5章")
i8 = exp.index("# 第8章")
iref = exp.index("# 参考文献")
keep_ch567 = exp[i5:i8].rstrip()
keep_back = exp[iref:].rstrip()

body = "\n\n".join([p1.rstrip(), keep_ch567, p2.rstrip(), keep_back]) + "\n"
OUT.write_text(body, encoding="utf-8")

print(f"总字数 {len(body)}")
print(f"图占位 {body.count('[[FIG:')} 个")
print(f"表 {sum(1 for ln in body.splitlines() if ln.strip().startswith('|---'))} 张")
import re
for h in re.findall(r"(?m)^# 第\d+章.*$", body):
    print(" ", h)
