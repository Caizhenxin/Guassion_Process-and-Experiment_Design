#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_fix_d82_d83_cells.py —— 补上 D82/D83 决策行与进度行缺失的后两列（涉及文件 / 结论）。

起因：`_apply_d82_docs.py` / `_apply_d83_docs.py` 插入的行只写了 3 个单元格，
而这两张表是 5 列 ⇒ `check_table_integrity.py` 判 mangled（4 竖线 vs 表头 6 竖线）。
本脚本幂等：若该行已是 6 条竖线则跳过。
"""
from __future__ import annotations

import sys
from pathlib import Path

PLAN = Path(
    r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md"
)

# key = 行首锚点；value = (涉及文件单元格, 结论/备注单元格)
TAIL_CELLS = {
    "| **D82** | 2026-10-18 |": (
        "`5_Reference/08_工作流/Stage6_被试招募与知情同意包.md`（**新建**，166 行）+ "
        "`1_Code/Experiment/exp_Check/check_consent_pack.py`（**新建**，零依赖，28/28、自测 5/5）+ "
        "`1_Code/DDM_Core/_scratch/_apply_d82_docs.py`（**新建**）+ `Stage6_Pilot方案.md` §9 第 9 条 + "
        "`Stage7_数据采集执行与质控方案.md` §6 工具链",
        "判据只保证材料**没被改坏**；批号、报酬、单位信息必须由研究者与伦理委员会填写（占位符 `【】` 不得由 AI 代填）",
    ),
    "| **D83** | 2026-10-18 |": (
        "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.5 → **v4.6**，1425 行） + "
        "`1_Code/Experiment/exp_matlab/test/check_full_session.py`（24 → **26/26**，新增 A8b/A11/A12） + "
        "`5_Reference/08_工作流/Stage1_技术验证记录.md`（§6 回填 + 6-C 加「v4.6 已修」说明） + "
        "`主试培训手册_Exp_Design_Formal.md`（v2.4 → **v2.5**，395 行，§7.y） + "
        "`PTB免费版配置说明.md`（139 → 163 行）",
        "5/576 行**保留为「v4.5 已知缺陷」**、由 v4.6 修复；不放宽 6-C 判据去迁就既有数据",
    ),
    "| 2026-10-18 | **6**（被试材料 → D82） |": (
        "`Stage6_被试招募与知情同意包.md`（166 行）+ `1_Code/Experiment/exp_Check/check_consent_pack.py`（28/28）",
        "所有机构相关项留 `【】` 占位，待研究者/伦理委员会人工填写",
    ),
    "| 2026-10-18 | **6**（实机回放抓缝 → D83） |": (
        "`Exp_Design_Formal.m` v4.6（1425 行）+ `test/check_full_session.py`（26/26）+ 手册 v2.5（395 行）+ Stage1 §6 回填",
        "Stage 1 §6 已回填：6-B 3/3、6-D 5/5；6-C 核心一项注明「v4.5 已知缺陷、v4.6 已修」；6-A 待启动回显、6-E 待协议核对",
    ),
}


def main() -> int:
    text = PLAN.read_text(encoding="utf-8")
    lines = text.split("\n")
    fixed = 0

    for i, line in enumerate(lines):
        for anchor, (files_cell, note_cell) in TAIL_CELLS.items():
            if not line.startswith(anchor):
                continue
            if line.count("|") >= 6:
                print(f"[SKIP] L{i + 1}：已是 5 列")
                continue
            body = line.rstrip()
            assert body.endswith("|"), f"L{i + 1} 行尾不是竖线"
            body = body[:-1].rstrip()  # 去掉末尾 " |"
            lines[i] = f"{body} | {files_cell} | {note_cell} |"
            print(f"[OK] L{i + 1}：补齐后两列（竖线 {line.count('|')} → {lines[i].count('|')}）")
            fixed += 1

    if fixed:
        PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"\n共修正 {fixed} 行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
