"""第三轮：掉帧试次是否就是压低 t0 上界的元凶（逐被试 min(RT) 对照）+ 3-1 的快试次画像。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import real_data_check as R  # noqa: E402

DATA = ROOT / "2_Data" / "Real_Data" / "New_Design"
pd.set_option("display.width", 200)

KEEP = ["1-1", "1-2", "1-3", "1-4", "1-5", "2-1", "2-2", "2-3", "2-4", "2-5",
        "3-2", "3-3", "3-4", "3-5", "4-1", "4-2", "4-4", "4-5"]


def main() -> None:
    raw = R.load_files(sorted(DATA.glob("Condition */*.csv")))
    d = raw[raw["is_formal"]].copy()
    d["dev_abs"] = d.dur_dev_ms.abs()
    d["resp"] = (d.responded == 1) & (d.rt_ms > 0)

    print("== RT<200 与掉帧的交叉（全体）==")
    for thr in (1.0, 16.7, 20.0, 50.0):
        bad = d.dev_abs > thr
        print(f"  |dev|>{thr:>4.1f} ms：{int(bad.sum())} 行，其中 RT<200 的 "
              f"{int((bad & (d.rt_ms < 200) & d.resp).sum())} 行")

    print("\n== 逐被试：min(RT) 在「全试次」vs「只干净计时」下的差别 ==")
    rows = []
    for sid, g in d[d.resp].groupby("subject_id"):
        clean = g[g.dev_abs <= 16.7]
        rows.append({"sid": sid, "n": len(g), "n_clean": len(clean),
                     "min_all": g.rt_ms.min(), "min_clean": clean.rt_ms.min(),
                     "cap_all": g.rt_ms.min() / 1000 - 0.02,
                     "cap_clean": clean.rt_ms.min() / 1000 - 0.02,
                     "n_fast": int((g.rt_ms < 200).sum()),
                     "n_fast_clean": int((clean.rt_ms < 200).sum()),
                     "n_drop": int((g.dev_abs > 16.7).sum())})
    t = pd.DataFrame(rows).set_index("sid")
    t["cap_gain_ms"] = ((t.cap_clean - t.cap_all) * 1000).round(0)
    print(t.round(3).to_string())

    print("\n== 3-1 ==")
    s = d[d.subject_id == "3-1"]
    print(f"3-1 快试次 {int((s.rt_ms < 200).sum())}，其中 |dev|>16.7 的 "
          f"{int(((s.rt_ms < 200) & (s.dev_abs > 16.7)).sum())}；"
          f"该场 |dev|>16.7 总行数 {int((s.dev_abs > 16.7).sum())}")
    print(f"3-1 |dev| 分位：q50 {float(s.dev_abs.median()):.1f} / q90 "
          f"{float(s.dev_abs.quantile(.9)):.1f} / max {float(s.dev_abs.max()):.1f}")

    print("\n== 掉帧试次的行为后果（是否该整体剔除）==")
    bad = d[d.dev_abs > 16.7]
    good = d[d.dev_abs <= 16.7]
    print(f"|dev|>16.7：n={len(bad)}，正确率 {bad.correct.mean():.3f}，"
          f"RT 中位 {bad.rt_ms.median():.0f} ms")
    print(f"其余：n={len(good)}，正确率 {good.correct.mean():.3f}，"
          f"RT 中位 {good.rt_ms.median():.0f} ms")


if __name__ == "__main__":
    main()
