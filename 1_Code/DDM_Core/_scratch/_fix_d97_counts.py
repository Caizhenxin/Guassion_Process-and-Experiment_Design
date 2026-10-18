# -*- coding: utf-8 -*-
"""D97 行数口径修正：定稿实测 381 行（落纸时写的 366 是估算值）。三处替换。"""
from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
a = P.read_text(encoding="utf-8").split("\n")

pairs = [
    ("**354 → 366 行**", "**354 → 381 行**"),
    ("定稿文档 354 → 366 行", "定稿文档 354 → 381 行"),
    ("**v2.7 定稿**，366 行", "**v2.7 定稿**，381 行"),
]
done = []
for i, l in enumerate(a):
    for old, new in pairs:
        if old in l:
            a[i] = l.replace(old, new)
            done.append((i + 1, old))
assert len(done) == 3, done
P.write_text("\n".join(a), encoding="utf-8", newline="\n")
print("[ok]", done, "lines", len(a))
