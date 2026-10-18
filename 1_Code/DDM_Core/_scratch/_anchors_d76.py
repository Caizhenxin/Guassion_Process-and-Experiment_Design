# -*- coding: utf-8 -*-
"""勘查 D76 与 Stage 8 状态段的锚点。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
mp = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
lines = mp.read_text(encoding="utf-8").split("\n")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("==== D75 / health 相关行 ====")
for i, ln in enumerate(lines, 1):
    if any(k in ln for k in ("D75", "stage8_health", "长跑可恢复", "新增 D7")):
        print(f"{i:4d} | {ln[:160]}")

print("\n==== Stage 8 状态段（L325-350）====")
for i in range(324, 350):
    print(f"{i+1:4d} | {lines[i][:190]}")
