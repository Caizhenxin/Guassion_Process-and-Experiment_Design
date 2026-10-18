# -*- coding: utf-8 -*-
"""把 D76 要用的每一条锚点原文打印出来（含竖线数，便于核对列数）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def show(path, ranges):
    p = ROOT / path
    lines = p.read_text(encoding="utf-8").split("\n")
    print(f"\n######## {path}（{len(lines)} 行）########")
    for a, b in ranges:
        print(f"---- L{a}–L{b} ----")
        for i in range(a - 1, min(b, len(lines))):
            ln = lines[i]
            print(f"{i+1:4d} [{ln.count('|')}v] {ln[:240]}")


show("5_Reference/08_工作流/工作流_主计划.md",
     [(499, 502), (564, 568), (632, 636), (725, 730)])
show("5_Reference/08_工作流/Stage8_建模与验证方案.md", [(190, 238)])
