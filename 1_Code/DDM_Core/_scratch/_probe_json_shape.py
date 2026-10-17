# -*- coding: utf-8 -*-
"""打印 stage8_results.json 的层级键结构（D68 素材，只读）。"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\DDM_Core\_scratch\stage8_synth3_dryrun\stage8_results.json")
d = json.loads(p.read_text(encoding="utf-8"))
g = d["groups"]
print("groups 类型:", type(g).__name__)
if isinstance(g, list):
    for i, x in enumerate(g):
        print(f"  [{i}] 键 = {sorted(x)}")
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, dict):
                    print(f"      {k}: 子键 = {sorted(v)[:12]}")
        if i >= 1:
            break
else:
    print(" 键 =", sorted(g))
    first = next(iter(g.values()))
    print(" 首个值的键 =", sorted(first))
