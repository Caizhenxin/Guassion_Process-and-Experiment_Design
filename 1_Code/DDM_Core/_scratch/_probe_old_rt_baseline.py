# -*- coding: utf-8 -*-
"""把 S6-5 / S6-6 的阈值锚在历史真人数据上。

问题来源：第一场真实场次（60 Hz，v4.5）跑出来 S6-5 / S6-6 双双 FAIL
（正确率 0.485、RT 中位 0.069 s、过快 56.2%、注视期抢按 74.8%）。
要判断这到底是「判据太严」还是「这一场是主试自己按键试跑」，必须知道
**真人在同类任务上的行为长什么样**。于是拿 2_Data/Real_Data/UnExtact/emp_data
里 87 份历史逐被试 CSV（旧 16 列口径）当参照。

输出：逐文件 RT 中位/正确率/漏答率/过快率，以及跨文件的分布（min/median/max）。
"""
from __future__ import annotations

import csv
import statistics as st
import sys
from pathlib import Path

D = Path(sys.argv[1])
files = sorted(D.glob("*.csv"))
print("文件数：%d" % len(files))

FAST = 0.15          # S6-5 的「过快」口径
rows_all = []
per_file = []
for f in files:
    with f.open(encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("stage") or "").strip() == "formal"]
    if not rows:
        continue
    rt, correct, timeout = [], 0, 0
    for r in rows:
        resp = (r.get("Response") or "").strip()
        c = (r.get("Correct") or "").strip()
        try:
            v = float(r.get("RT"))
        except (TypeError, ValueError):
            v = float("nan")
        if not resp or v != v:
            timeout += 1
            continue
        rt.append(v)
        if c in ("0", "1"):
            correct += int(float(c))
        rows_all.append((f.name, v))
    if not rt:
        continue
    acc = correct / len(rt)
    fast = sum(1 for v in rt if v < FAST) / len(rt)
    per_file.append({
        "file": f.name,
        "n": len(rows),
        "n_rt": len(rt),
        "rt_med": st.median(rt),
        "acc": acc,
        "fast": fast,
        "timeout": timeout / len(rows),
    })


def summ(key: str) -> tuple[float, float, float]:
    vals = sorted(p[key] for p in per_file)
    return vals[0], st.median(vals), vals[-1]


print("\n## 跨 %d 份逐被试文件（仅正式段、仅已响应试次）" % len(per_file))
for key, name, unit in [
    ("rt_med", "RT 中位数", "s"),
    ("acc", "正确率（已响应内）", ""),
    ("fast", "过快比例（RT < 0.15 s）", ""),
    ("timeout", "漏答率（占全部正式试次）", ""),
]:
    lo, md, hi = summ(key)
    fmt = "%.3f" if unit else "%.3f"
    print("  %-26s min %s / median %s / max %s" % (name, fmt % lo, fmt % md, fmt % hi))

print("\n## 最慢/最快的 5 份")
for p in sorted(per_file, key=lambda x: x["rt_med"])[:5]:
    print("  %-28s RT中位 %.3f  acc %.3f  过快 %.3f  漏答 %.3f" %
          (p["file"], p["rt_med"], p["acc"], p["fast"], p["timeout"]))
print("  ...")
for p in sorted(per_file, key=lambda x: -x["rt_med"])[:5]:
    print("  %-28s RT中位 %.3f  acc %.3f  过快 %.3f  漏答 %.3f" %
          (p["file"], p["rt_med"], p["acc"], p["fast"], p["timeout"]))

n_below55 = sum(1 for p in per_file if p["acc"] < 0.55)
n_fast10 = sum(1 for p in per_file if p["fast"] > 0.10)
n_rt_lo = sum(1 for p in per_file if p["rt_med"] < 0.30)
print("\n## 对照 S6-5 三条阈值（正确率 ≥0.55 / RT 中位 ≥0.30 s / 过快 ≤10%%）")
print("  正确率 <0.55 的文件：%d / %d" % (n_below55, len(per_file)))
print("  RT 中位 <0.30 s 的文件：%d / %d" % (n_rt_lo, len(per_file)))
print("  过快 >10%% 的文件：%d / %d" % (n_fast10, len(per_file)))
print("  全部文件 RT 中位最小 %.3f s ⇒ 真人从未接近 0.069 s" % summ("rt_med")[0])
