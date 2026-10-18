# -*- coding: utf-8 -*-
"""check_full_session.py 的 docstring 同步到 29 项（D84 加了 B27–B29）。"""
import io
import sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8", newline="").read()

reps = [
    ("  B\x20驱动侧（run_full_session 的 B20–B23 判据、桩目录完整、日志走 UTF-8）",
     "  B 驱动侧（run_full_session 的 B20–B23 判据、桩目录完整、日志走 UTF-8、D84 的 tFloor 契约测试 B27–B29）"),
    ("本脚本只负责「三条防线都还在、产物也真的被读通过」，秒级、可进 CI。",
     "本脚本只负责「四条防线都还在、产物也真的被读通过」，秒级、可进 CI（共 29 项）。"),
]
for old, new in reps:
    if src.count(old) != 1:
        print("skip（命中 %d 次）：%s" % (src.count(old), old[:30]))
        continue
    src = src.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(src)
print("done")
