# -*- coding: utf-8 -*-
"""确认 patch_row 定位到的是哪一行（诊断用）。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\5_Reference\08_工作流\Stage1_技术验证记录.md")
lines = p.read_text(encoding="utf-8").split("\n")
pfx = "5. **实机证据空缺**"
hits = [i for i, ln in enumerate(lines) if ln.startswith(pfx)]
print("命中 0-based 下标:", hits, "| 总数:", len(lines))
for i in hits:
    print(f"  L{i + 1}: {lines[i][:70]}")
