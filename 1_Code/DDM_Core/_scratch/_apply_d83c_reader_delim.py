#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_apply_d83c_reader_delim.py —— `read_formal_data.read_rows()` 同时接受 txt（制表符）与 CSV（逗号）。

起因（D83b 的同一类漂移）：`load_rows()` 只有 `split("\\t")`。Stage 7 收的是 txt，
但主试手上最常用的是 MATLAB 的 `cell2table` 快照 `EXP_data_group1_1.csv`（逗号分隔），
直接喂进去会得到「表头 1 列（非 v4.1）」⇒ 576 个试次静默变成 0 行。

本补丁按首行嗅探分隔符，并用 `csv.reader` 处理引号；txt 路径行为不变。
"""
from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path(
    r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
    r"\1_Code\Experiment\read_formal_data.py"
)

OLD_IMPORT = "from pathlib import Path\n"
NEW_IMPORT = "import csv\nfrom pathlib import Path\n"

OLD = '''    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], "空文件"
    head = [h.strip() for h in lines[0].split("\\t")]
    n_col = len(head)
    where = "表头匹配 25 列" if tuple(head) == HEADER25 else f"表头 {n_col} 列（非 v4.1）"
    rows = []
    for ln in lines[1:]:
        parts = ln.split("\\t")
        if len(parts) != n_col:
            continue
        rows.append(dict(zip(head, parts)))
    return rows, where
'''

NEW = '''    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], "空文件"
    delim = _sniff_delimiter(lines[0])
    head = [h.strip() for h in _split_line(lines[0], delim)]
    n_col = len(head)
    where = "表头匹配 25 列" if tuple(head) == HEADER25 else f"表头 {n_col} 列（非 v4.1）"
    rows = []
    for ln in lines[1:]:
        parts = _split_line(ln, delim)
        if len(parts) != n_col:
            continue
        rows.append(dict(zip(head, parts)))
    return rows, where
'''

HELPERS = '''def _sniff_delimiter(header_line: str) -> str:
    """按首行嗅探分隔符：有制表符 ⇒ txt（逐试次 `fopen` 写出的通道）；
    否则若含逗号 ⇒ `,`（`cell2table` 快照 CSV，用 `csv.reader` 以正确处理引号）。
    """
    if "\\t" in header_line:
        return "\\t"
    if "," in header_line:
        return ","
    return "\\t"


def _split_line(line: str, delim: str) -> list[str]:
    if delim == ",":
        return next(csv.reader([line]))
    return line.split(delim)


def read_rows('''


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")

    if "_sniff_delimiter" in src:
        print("[SKIP] 已含 _sniff_delimiter")
        return 0

    assert OLD in src, "read_rows 原文未命中"
    assert OLD_IMPORT in src, "import 块未命中"
    assert "def read_rows(" in src

    src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    src = src.replace("def read_rows(", HELPERS, 1)
    src = src.replace(OLD, NEW, 1)
    TARGET.write_text(src, encoding="utf-8", newline="\n")
    print("[OK] read_formal_data.read_rows 已支持 CSV/txt 双通道")
    print(f"     行数：{len(src.splitlines())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
