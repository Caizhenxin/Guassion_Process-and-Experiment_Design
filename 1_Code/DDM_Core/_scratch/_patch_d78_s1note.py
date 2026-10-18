# -*- coding: utf-8 -*-
"""_patch_d78_s1note.py —— 在 Stage 1 的「权威性」行后插入行号口径说明（幂等）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S1 = ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md"

BLOCK = [
    "",
    "> **行号口径（2026-10-18，D78）**：§2–§5 里的 `L…` 是按 **v4（1313 行）** 记的。现行程序是 **v4.4（1357 行）**——v4.2/v4.3 把「弹窗 + 校验 + 主试确认」抽成",
    "> `exp_ask_subject_info.m`，v4.4 把逐试次容器从 `table()` 换成 cell（`exp_new_data.m` / `exp_data_table.m`），行号整体后移 40 余行。",
    "> 因此**不要拿本文件的 `L…` 去数现行文件的行**：每处引用都附了原文代码串，用该串搜；行为判据以 `test/check_ask_info`、`test/check_data_accum`、",
    "> `test/check_input_validation`、`test/check_manual_d4.py` 四条自测为准（见 §6 第 0 步）。",
]

t = S1.read_text(encoding="utf-8")
if "行号口径（2026-10-18，D78）" in t:
    print("[跳过] S1 行号口径")
else:
    lines = t.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith("权威性：本文件是 Stage 1 的唯一验证记录")]
    if len(hits) != 1:
        raise SystemExit(f"❌ 锚点命中 {len(hits)} 行")
    i = hits[0]
    lines[i + 1:i + 1] = BLOCK
    S1.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[插入] S1 行号口径（锚点 L{i + 1}）")
