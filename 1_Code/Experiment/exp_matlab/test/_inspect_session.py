# -*- coding: utf-8 -*-
"""_inspect_session.py —— 数一数冒烟产物里各条分支各走到多少行（D79 自检用）"""
import csv
import sys
from pathlib import Path

p = Path(sys.argv[1])
rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
n = len(rows)
form = [r for r in rows if r["stage"] == "formal"]


def f(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError):
        return float("nan")


prem = [r for r in form if r["premature_press"] == "1"]
na = [r for r in form if r["Response"] == "NA"]
rt_lt_T = [r for r in form if r["Response"] != "NA" and f(r, "RT") < f(r, "T")]
trunc = [r for r in form if f(r, "stimulus_dur_actual") < f(r, "T") - 0.005]
print(f"文件 {p.name}：总 {n} 行、formal {len(form)} 行")
print(f"  premature_press=1 : {len(prem)}")
print(f"  Response=NA       : {len(na)}")
print(f"  已响应且 RT < T   : {len(rt_lt_T)}")
print(f"  stimulus_dur < T  : {len(trunc)}")
if trunc:
    d = [f(r, "stimulus_dur_actual") for r in trunc]
    rt = [f(r, "RT") for r in trunc]
    print(f"  截断行：dur {min(d):.3f}–{max(d):.3f} s，RT 全距 {min(rt):.3f}–{max(rt):.3f} s")
    bad = [r for r in trunc if abs(f(r, "stimulus_dur_actual") - f(r, "RT")) > 0.02]
    print(f"  其中 |dur − RT| > 20 ms 的行：{len(bad)}")
print(f"  T 档：{sorted({round(f(r,'T'),3) for r in form})}")
print(f"  W 档：{sorted({round(f(r,'W'),3) for r in form})}")
print(f"  block：{sorted({r['block'] for r in rows})}")
