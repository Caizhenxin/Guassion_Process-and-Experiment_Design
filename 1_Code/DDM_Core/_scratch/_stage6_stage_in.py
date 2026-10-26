# -*- coding: utf-8 -*-
"""把 New_Design 的 20 场 csv+txt 硬链接成扁平目录，供 stage6_report / find_sessions 用。

用法：python -X utf8 1_Code/DDM_Core/_scratch/_stage6_stage_in.py
输出：2_Data/Real_Data/New_Design/_stage6_in/（20 csv + 20 txt）
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
DATA = ROOT / "2_Data/Real_Data/New_Design"
OUT = DATA / "_stage6_in"

CSV_RE = re.compile(r"^EXP_data_group(\d+)_(\d+)\.csv$", re.I)
TXT_RE = re.compile(r"^exp_group(\d+)_subject(\d+)\.txt$", re.I)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    n_csv = n_txt = 0
    for p in sorted(DATA.glob("Condition */*")):
        m = CSV_RE.match(p.name) or TXT_RE.match(p.name)
        if not m:
            continue
        dst = OUT / p.name
        if dst.exists():
            dst.unlink()
        os.link(p, dst)
        if p.suffix.lower() == ".csv":
            n_csv += 1
        else:
            n_txt += 1
    print(f"[ok] {OUT}")
    print(f"     csv {n_csv} 份、txt {n_txt} 份")
    return 0


if __name__ == "__main__":
    sys.exit(main())
