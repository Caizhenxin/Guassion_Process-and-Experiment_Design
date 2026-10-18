# -*- coding: utf-8 -*-
"""_patch_d77_manual2.py —— 补完剩余的 v2.0/328 行 遗留（手册已升 v2.1/349 行，Word 14317 B）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUBS = [
    ("手册重写为 v2.0（D4 口径）+ Word 重生成",
     "手册重写为 v2.1（349 行；v2.1 补 §3.2「本机自测三条」）+ Word 重生成（14317 B）"),
    ("**手册 v2.0 重写**为 D4 口径", "**手册 v2.1 重写**为 D4 口径"),
    ("`主试培训手册_Exp_Design_Formal.md`（v2.0，**328 行**）",
     "`主试培训手册_Exp_Design_Formal.md`（v2.1，**349 行**）"),
]
for name in ["1_Code/DDM_Core/README.md", "5_Reference/08_工作流/工作流_主计划.md"]:
    p = ROOT / name
    t = p.read_text(encoding="utf-8")
    n = 0
    for a, b in SUBS:
        n += t.count(a)
        t = t.replace(a, b)
    p.write_text(t, encoding="utf-8", newline="\n")
    print(f"{p.name:24s} 替换 {n} 处")
