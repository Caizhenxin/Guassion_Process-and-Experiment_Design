# -*- coding: utf-8 -*-
"""把 D68 的「机制断言 C1–C4」补进已落纸的三处（另加主计划决策行）。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

EDITS = [
    # (文件, 说明, 旧片段, 新片段)
    (S8, "§9 hier.py 行补 C 组",
     "`_scratch/check_hier.py` **0 项未通过**（总耗时 388.2 s）",
     "`_scratch/check_hier.py` **0 项未通过**（D68 加 C 组 4 项机制断言：`cov` 该方向 = `1/floor`"
     "、`n_flipped` 如实记账、边际有限、负曲率方向众数发散；总耗时 388.2 s → 见自测日志）"),
    (S8, "§12 v1.4 补 C 组",
     "（A11/A12）；§11 第 13 条补",
     "（A11/A12）、`check_hier.py` 加 C 组 4 项机制断言（`cov` 该方向 = `1/floor`、负曲率方向众数发散）；"
     "§11 第 13 条补"),
    (MP, "决策行补机制断言",
     "与 **A12**（正定 ⇒ 只许报「正定」），**23/23 → 25/25**。",
     "与 **A12**（正定 ⇒ 只许报「正定」），**23/23 → 25/25**；"
     "机制断言 `1_Code/DDM_Core/_scratch/check_hier.py` 加 **C1–C4**（纯二次 `ll_x` 把 Hessian 造死 ⇒ "
     "`cov` 该方向 = `1/floor`，比值 **1.000000**；且负曲率方向上众数搜索发散，众数模长 ≈ 1e9 ⇒ 该点不是众数）。"),
]

#: 段落插入（README §8.43 §四的 C 组条目）
RM_ANCHOR = "**不得**出现「不得解读」（防止一刀切把健康情形也污名化）。"
RM_ADD = (
    "* **C1–C4**（`_scratch/check_hier.py` 的 C 组，D68）：用**纯二次**的 `ll_x` 把 Hessian 造死"
    "（`g = −½(λ1 x1² + λ2 x2²)`、`λ1 = 10`、`λ2 = −5` ⇒ `A = −H = diag(10, −5)`），"
    "断言：`n_flipped` = 1、`cov` 被抬方向 = **`1/floor`**（比值 1.000000）、边际有限、"
    "且负曲率方向上 L-BFGS **发散**（`|mode|` ≈ 1e9 ⇒ 该点根本不是众数）。"
    "这一条把「σ 不可解读」从措辞变成**可复现的机制**。"
)

bad = 0
for path, what, old, new in EDITS:
    txt = path.read_text(encoding="utf-8")
    if new in txt:
        print(f"[跳过] {path.name}：{what}（已补）")
        continue
    n = txt.count(old)
    if n != 1:
        print(f"❌ {path.name}：{what} 的锚点命中 {n} 次")
        bad += 1
        continue
    if APPLY:
        path.write_text(txt.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")

txt = RD.read_text(encoding="utf-8")
if RM_ADD.split("（")[0] in txt:
    print(f"[跳过] {RD.name}：§8.43 C 组条目（已补）")
else:
    n = txt.count(RM_ANCHOR)
    if n != 1:
        print(f"❌ {RD.name}：§8.43 锚点命中 {n} 次")
        bad += 1
    else:
        if APPLY:
            RD.write_text(txt.replace(RM_ANCHOR, RM_ANCHOR + "\n" + RM_ADD),
                          encoding="utf-8", newline="\n")
        print(f"[{'写入' if APPLY else '干跑'}] {RD.name}：§8.43 C 组条目")

sys.exit(1 if bad else 0)
