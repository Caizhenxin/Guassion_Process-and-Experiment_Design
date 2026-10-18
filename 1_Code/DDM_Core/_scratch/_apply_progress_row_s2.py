# -*- coding: utf-8 -*-
"""进度表追加本轮行（文档结构修缮），5 列。"""
import io
from pathlib import Path

P = Path("5_Reference/08_工作流/工作流_主计划.md")
L = io.open(P, encoding="utf-8").read().splitlines()
s = L.index("## 6. 进度表")
e = next(k for k in range(s + 1, len(L)) if L[k].startswith("## "))
last = max(k for k in range(s, e) if L[k].startswith("| 2026-"))
row = ("| 2026-10-18 | **6（文档结构修缮）** | "
       "把 §2 阶段总览从「被压平的无竖线单行」重建为 5 列真表格（Stage 0–9 全部恢复成行，状态与 v4.9 对齐），"
       "顺手修掉 §3 里两个同名「### Stage 3」标题、给 Stage 6 详述补 2026-10-18 状态块（两场均不计入 N=8、D93/D94 已修）。"
       "校验：主计划 **808 行 / 表格行 426 / 三类结构错 0**、`check_traceability.py` **1247 项 0 问题**。 | "
       "`5_Reference/08_工作流/工作流_主计划.md`（798 → **808 行**）；无新增脚本，"
       "补丁留在 `1_Code/DDM_Core/_scratch/_apply_s2_table.py`、`_fix_s2_flatline.py`、`_apply_s3_detail_sync.py` | — |")
L.insert(last + 1, row)
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("ok, lines =", len(L))
