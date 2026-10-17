# -*- coding: utf-8 -*-
"""列出 D73 落纸需要的锚点行。"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mp = (REPO / "5_Reference/08_工作流/工作流_主计划.md").read_text(encoding="utf-8").split("\n")
print("=== 主计划")
for i, ln in enumerate(mp, 1):
    if ln.startswith(("| **D72**", "| **D71**", "| 2026-10-17 | **8**",
                      "| 2026-10-17 | **新增 D72", "| `1_Code/DDM_Core/stage8_run.py`",
                      "## ", "| 版本 |")):
        print(i, ln[:100])

s8 = (REPO / "5_Reference/08_工作流/Stage8_建模与验证方案.md").read_text(encoding="utf-8").split("\n")
print("=== Stage8")
for i, ln in enumerate(s8, 1):
    if ln.startswith(("## ", "| `1_Code/DDM_Core/stage8_run.py`", "1. **", "2. **", "3. **",
                      "4. **", "5. **", "6. **", "7. **", "* v1", "**v1")):
        print(i, ln[:100])

rd = (REPO / "1_Code/DDM_Core/README.md").read_text(encoding="utf-8").split("\n")
print("=== README")
for i, ln in enumerate(rd, 1):
    if ln.startswith(("### 8.4", "## 9. 尚未做", "| 56 |", "| 55 |")):
        print(i, ln[:100])
