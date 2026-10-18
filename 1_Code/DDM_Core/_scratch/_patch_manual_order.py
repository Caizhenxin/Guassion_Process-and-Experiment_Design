# -*- coding: utf-8 -*-
"""把手册里的 §6.6 移到 §6.5 之后（顺序修正；幂等）。"""
from pathlib import Path

M = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\主试培训手册_Exp_Design_Formal.md")
t = M.read_text(encoding="utf-8")

i66 = t.find("### 6.6 跑到某一试次突然崩")
i65 = t.find("### 6.5 被试中途不适")
if i66 < 0 or i65 < 0:
    raise SystemExit("找不到 §6.5/§6.6")
if i66 > i65:
    print("顺序已经正确")
else:
    # 6.6 块：从 i66 到 i65（不含）
    blk66 = t[i66:i65]
    # 6.5 块：从 i65 到下一个 "\n---\n"
    nxt = t.find("\n---\n", i65)
    blk65 = t[i65:nxt]
    t = t[:i66] + blk65 + blk66.rstrip("\n") + "\n" + t[nxt:]
    M.write_text(t, encoding="utf-8", newline="\n")
    print("已交换：6.5 → 6.6")
print(f"行数 = {t.count(chr(10)) + 1}")
