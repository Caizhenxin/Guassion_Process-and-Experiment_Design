# -*- coding: utf-8 -*-
"""把报告表头的「来源」从硬编码「正式数据」改成真实来源（D70 的对照运行里它是错的）。"""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = Path(__file__).resolve().parents[1] / "stage8_run.py"
t = p.read_text(encoding="utf-8")
old = "        f\"来源：{'合成（干跑）' if args.synthetic else '正式数据'}；\""
new = ("        f\"来源：{'合成（干跑）' if args.synthetic else ('--data ' + "
       "'、'.join(str(x) for x in (args.data or []))[:120])}；\"")
if new in t:
    print("[跳过] 已改过")
else:
    assert t.count(old) == 1, f"锚点命中 {t.count(old)} 次"
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8", newline="\n")
    print("[写入] stage8_run.py 的数据来源标签")

import ast
ast.parse(p.read_text(encoding="utf-8"))
print("ast OK")
