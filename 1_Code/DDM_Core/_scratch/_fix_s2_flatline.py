# -*- coding: utf-8 -*-
"""删掉 §2 里残留的被压平旧行，并补齐表前的空行。"""
import io
from pathlib import Path

P = Path("5_Reference/08_工作流/工作流_主计划.md")
L = io.open(P, encoding="utf-8").read().splitlines()

drops = [k for k, x in enumerate(L) if x.startswith("Stage名称谁做状态阻塞")]
assert len(drops) == 1, drops
k = drops[0]
L.pop(k)

# 表头前必须有一个空行
hdr = next(j for j, x in enumerate(L) if x.startswith("| 阶段 | 名称 | 谁做 | 状态 |"))
assert L[hdr].startswith("| 阶段 |")
if L[hdr - 1] != "":
    L.insert(hdr, "")

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("ok, lines =", len(L))
