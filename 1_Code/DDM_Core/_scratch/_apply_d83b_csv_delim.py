#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_apply_d83b_csv_delim.py —— 让 `check_stage1_acceptance.py` 同时接受 CSV（逗号）与 txt（制表符）。

起因（D83）：主试交回的是 `EXP_data_group1_1.csv`（MATLAB `cell2table` 快照，逗号分隔），
而检查器 `load_rows()` 写死 `split("\\t")` ⇒ 整行被当成 1 列，于是打印
「这批文件的表头不是 v4.1 的 25 列（EXP_data_group1_1.csv（1 列））」——
**判据本身没错，是解析器只认一种分隔符**。README/Stage1 两处都写着"交 CSV 或 txt 都行"，
所以这是文档与实现漂移。

本补丁：按首行自动嗅探分隔符（有制表符 ⇒ `\\t`；否则若含逗号 ⇒ `,`，用 csv.reader 处理引号）。
"""
from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path(
    r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
    r"\1_Code\Experiment\exp_Check\check_stage1_acceptance.py"
)

OLD_IMPORT = "import argparse\n"
NEW_IMPORT = "import argparse\nimport csv\n"

OLD_LOAD = '''def load_rows(path: Path) -> tuple[list[str], list[dict], bytes]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header = lines[0].split("\\t")
    rows = []
    for ln in lines[1:]:
        cells = ln.split("\\t")
        row = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(header)}
        rows.append(row)
    return header, rows, raw
'''

NEW_LOAD = '''def sniff_delimiter(header_line: str) -> str:
    """按首行嗅探分隔符：有制表符按 txt 处理，否则若含逗号按 CSV 处理。

    MATLAB 侧两条通道并存：逐试次 `fopen` 写的是 **制表符** txt，
    `cell2table` 快照写的是 **逗号** CSV。检查器两种都必须吃（D83）。
    """
    if "\\t" in header_line:
        return "\\t"
    if "," in header_line:
        return ","
    return "\\t"


def split_line(line: str, delim: str) -> list[str]:
    if delim == ",":
        return next(csv.reader([line]))
    return line.split(delim)


def load_rows(path: Path) -> tuple[list[str], list[dict], bytes]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    delim = sniff_delimiter(lines[0])
    header = split_line(lines[0], delim)
    rows = []
    for ln in lines[1:]:
        cells = split_line(ln, delim)
        row = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(header)}
        rows.append(row)
    return header, rows, raw
'''


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")

    if "def sniff_delimiter(" in src:
        print("[SKIP] 已含 sniff_delimiter")
        return 0

    assert OLD_LOAD in src, "load_rows 原文未命中（文件已被改动过？）"
    assert OLD_IMPORT in src, "import 块未命中"

    src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    src = src.replace(OLD_LOAD, NEW_LOAD, 1)
    TARGET.write_text(src, encoding="utf-8", newline="\n")
    print("[OK] 已加入分隔符嗅探（CSV/txt 双通道）")
    print(f"     行数：{len(src.splitlines())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
