# -*- coding: utf-8 -*-
"""把 D84 的失败记录追加进 INDEX.md（第 17 条）。"""
import io
import sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8", newline="").read()
row = ("| 2026-10-18 | 契约测试把桩目录加在 PTB 之后，自己制造了 5 条假红 | "
       "`#MATLAB` `#Psychtoolbox` `#测试替身` `#path顺序` `#同名函数抢占` `#假绿` `#契约测试` `#KbName` | "
       "[2026-10-18_契约测试把桩目录加在PTB之后导致假红.md](./2026-10-18_契约测试把桩目录加在PTB之后导致假红.md) |")
assert row not in src
anchor = "| [2026-10-18_onset之前的按键被当成反应.md](./2026-10-18_onset之前的按键被当成反应.md) |"
assert src.count(anchor) == 1
lines = src.split("\n")
i = next(k for k, ln in enumerate(lines) if anchor in ln)
lines.insert(i + 1, row)
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("index +1")
