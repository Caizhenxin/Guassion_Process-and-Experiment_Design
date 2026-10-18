# -*- coding: utf-8 -*-
"""_bump_accum_counts.py —— check_data_accum 由 24 项扩到 33 项（并入 F 组）后，同步所有计数

只改「提到 check_data_accum / 数据累积 / 数据写入防线」的行，避免误伤其他自测的 24/24。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = [
    ROOT / "5_Reference/08_工作流/工作流_主计划.md",
    ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md",
    ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md",
    ROOT / "1_Code/DDM_Core/README.md",
    ROOT / "1_Code/Experiment/exp_matlab/PTB免费版配置说明.md",
    ROOT / "1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md",
    ROOT / "1_Code/Experiment/exp_matlab/test/check_data_accum.m",
]
MARKERS = ("check_data_accum", "数据累积", "数据写入防线", "数据写入")
PAIRS = [
    ("24/24", "33/33"),
    ("通过 24 / 未通过 0", "通过 33 / 未通过 0"),
    ("24 项", "33 项"),
]

total = 0
for p in FILES:
    t = p.read_text(encoding="utf-8")
    out = []
    changed = 0
    for ln in t.split("\n"):
        if any(m in ln for m in MARKERS):
            new = ln
            for old, rep in PAIRS:
                if old in new:
                    new = new.replace(old, rep)
                    changed += 1
            out.append(new)
        else:
            out.append(ln)
    if changed:
        p.write_text("\n".join(out), encoding="utf-8", newline="\n")
        print(f"{p.name}: {changed} 处")
        total += changed
print("合计", total)
