# -*- coding: utf-8 -*-
"""D85b：analyze_pilot.py 也是写死制表符的（D83b/D83c 的同一个 bug 的第三处）。

现象：`python 1_Code/Experiment/analyze_pilot.py 1_Code/Experiment/exp_matlab/EXP_data_group1_1.csv`
      报「跳过 1 个旧版（16 列，无 Stage 1 时间戳列）文件」+「没有任何 25 列数据文件」。
根因：`analyze_pilot.py:86` `rows = [ln.split("\\t") ...]` ⇒ 逗号 CSV 整行成 1 列 ⇒ 表头退化成
      `col1` ⇒ 行宽 1 < V1_NCOL(16) ⇒ 判「旧版 16 列」。
修法：与 D83b/D83c 同口径——首行嗅探分隔符，逗号走 `csv.reader`。

幂等；每处 old 串必须命中恰好 1 次。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TARGET = REPO / "1_Code" / "Experiment" / "analyze_pilot.py"

OLD_IMPORT = "import argparse\nimport re\nimport sys\n"
NEW_IMPORT = "import argparse\nimport csv\nimport re\nimport sys\n"

OLD_HELPERS_ANCHOR = 'MISSING = {"", "na", "nan", "n/a", "-", "[]"}\n'
NEW_HELPERS_ANCHOR = '''MISSING = {"", "na", "nan", "n/a", "-", "[]"}


def _sniff_delimiter(head: str) -> str:
    """按首行嗅探分隔符：有制表符 ⇒ 制表符；否则有逗号 ⇒ 逗号（D83b/D83c/D85b 同一个坑）。"""
    if "\\t" in head:
        return "\\t"
    if "," in head:
        return ","
    return "\\t"


def _split_line(line: str, delim: str) -> list[str]:
    if delim == "\\t":
        return line.rstrip("\\n").split("\\t")
    return next(csv.reader([line]))
'''

OLD_PARSE = ('    raw = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()\n'
             '    rows = [ln.rstrip("\\n").split("\\t") for ln in raw if ln.strip()]\n')
NEW_PARSE = ('    raw = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()\n'
             '    body = [ln for ln in raw if ln.strip()]\n'
             '    delim = _sniff_delimiter(body[0] if body else "")\n'
             '    rows = [_split_line(ln, delim) for ln in body]\n')


def apply(old: str, new: str, tag: str) -> None:
    text = TARGET.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        sys.exit(f"[FAIL] {tag}: 命中 {n} 次（应为 1）")
    TARGET.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[OK] {tag}")


def main() -> int:
    apply(OLD_IMPORT, NEW_IMPORT, "import csv")
    apply(OLD_HELPERS_ANCHOR, NEW_HELPERS_ANCHOR, "sniff/split 辅助函数")
    apply(OLD_PARSE, NEW_PARSE, "parse 去写死制表符")
    print(f"[DONE] analyze_pilot.py = {len(TARGET.read_text(encoding='utf-8').splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
