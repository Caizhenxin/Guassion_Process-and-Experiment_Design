# -*- coding: utf-8 -*-
"""_patch_d77_manual.py —— 手册从 v2.0（328 行）升到 v2.1（349 行，补 §3.2 本机自测三条），
把四份文档里 D77 段落中的版本号/行数一并对齐（幂等）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = [
    ROOT / "5_Reference/08_工作流/工作流_主计划.md",
    ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md",
    ROOT / "1_Code/DDM_Core/README.md",
    ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md",
]
SUBS = [
    ("（v2.0，328 行）", "（v2.1，349 行）"),
    ("`主试培训手册_Exp_Design_Formal.md`（v2.0，328 行）", "`主试培训手册_Exp_Design_Formal.md`（v2.1，349 行）"),
    ("（**328 行**）", "（**349 行**）"),
    ("手册 v2.0 + Word 重生成", "手册 v2.1（补 §3.2「本机自测三条」）+ Word 重生成（14317 B）"),
    ("手册重写为 **v2.0**（328 行，D4 口径", "手册重写为 **v2.1**（349 行，D4 口径；v2.1 增 §3.2「本机自测三条」"),
    ("Word 版重生成（13627 B）", "Word 版重生成（14317 B）"),
    ("`.docx` 用 `automation/md_to_docx.py` 重生成（13627 B）",
     "`.docx` 用 `automation/md_to_docx.py` 重生成（14317 B）"),
    ("`主试培训手册_Exp_Design_Formal.md` 重写为 **v2.0**",
     "`主试培训手册_Exp_Design_Formal.md` 重写为 **v2.1**"),
]

for p in FILES:
    t = p.read_text(encoding="utf-8")
    before = t
    n = 0
    for a, b in SUBS:
        n += t.count(a)
        t = t.replace(a, b)
    if t != before:
        p.write_text(t, encoding="utf-8", newline="\n")
        print(f"{p.name:38s} 替换 {n} 处")
    else:
        print(f"{p.name:38s} 无变化")
