# -*- coding: utf-8 -*-
"""§6/§7/§8 表头与 README §8.49 / §9 第 58–59 项。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def hdr(path, keys, span=8):
    lines = (ROOT / path).read_text(encoding="utf-8").split("\n")
    for i, ln in enumerate(lines):
        if any(ln.startswith(k) for k in keys):
            print(f"---- {path} @ L{i+1} ----")
            for j in range(i, min(i + span, len(lines))):
                print(f"{j+1:4d} [{lines[j].count('|')}v] {lines[j][:200]}")
            print()


hdr("5_Reference/08_工作流/工作流_主计划.md",
    ["## 6.", "## 7.", "## 8."], span=6)

lines = (ROOT / "1_Code/DDM_Core/README.md").read_text(encoding="utf-8").split("\n")
print("---- README §8.49 起 30 行 ----")
start = next(i for i, ln in enumerate(lines) if ln.startswith("### 8.49"))
for j in range(start, min(start + 30, len(lines))):
    print(f"{j+1:4d} | {lines[j][:200]}")
print("---- README §9 第 58/59 项及附近 ----")
for i, ln in enumerate(lines):
    if ln.startswith("## 9."):
        for j in range(i, min(i + 12, len(lines))):
            print(f"{j+1:4d} | {lines[j][:120]}")
        for j in range(len(lines) - 30, len(lines)):
            pass
print("---- README 尾部 22 行 ----")
for j in range(len(lines) - 22, len(lines)):
    print(f"{j+1:4d} | {lines[j][:200]}")
