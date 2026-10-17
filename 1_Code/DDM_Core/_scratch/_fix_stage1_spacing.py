# -*- coding: utf-8 -*-
"""修正 Stage1 §6 指引段的空行（上多一行、下缺一行）。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\5_Reference\08_工作流\Stage1_技术验证记录.md")
lines = p.read_text(encoding="utf-8").split("\n")
# 1) 连续两个空行 → 一个
out = []
for ln in lines:
    if ln == "" and out and out[-1] == "":
        continue
    out.append(ln)
# 2) blockquote 段紧接 `### 6-A` 时补一个空行
for i in range(len(out) - 1):
    if out[i].startswith(">") and out[i + 1].startswith("### 6-A"):
        out.insert(i + 1, "")
        break
p.write_text("\n".join(out), encoding="utf-8", newline="\n")
print("行数:", len(out))
