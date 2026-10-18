# -*- coding: utf-8 -*-
"""修 D97 落纸时被 PowerShell here-string 吃掉的反引号（定稿 L6 的 `正式采集_候选设计.md`）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\正式采集_候选设计_v2_定稿.md")
a = p.read_text(encoding="utf-8").split("\n")
bt = chr(96)
tgt = "正式采集_候选设计.md"
i = 5
assert a[i].startswith("> 权威性"), a[i][:40]
assert bt + tgt + bt not in a[i]
a[i] = a[i].replace(tgt, bt + tgt + bt)
p.write_text("\n".join(a), encoding="utf-8", newline="\n")
print(a[i])
