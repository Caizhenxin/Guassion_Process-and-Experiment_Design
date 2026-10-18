# -*- coding: utf-8 -*-
"""勘查 Stage 8 文档与 README 里 D76 的落纸锚点。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

s8 = ROOT / "5_Reference/08_工作流/Stage8_建模与验证方案.md"
lines = s8.read_text(encoding="utf-8").split("\n")
print(f"==== Stage8 文件共 {len(lines)} 行 ====")
for i, ln in enumerate(lines, 1):
    if any(k in ln for k in ("## ", "D75", "v1.8", "check_stage8.py", "第 19 条", "19. ", "18. ")):
        print(f"{i:4d} | {ln[:150]}")

print("\n==== Stage8 §9 表尾 + §10 + §11 尾部 ====")
for i in range(140, 240):
    if i < len(lines):
        print(f"{i+1:4d} | {lines[i][:150]}")
