"""核实：|dev| 大的试次，是不是「在刺激期内就按了键、程序把刺激截到下一帧」的合法签名。

若成立，则 `stimulus_dur_actual ≈ rt + 一帧`，且 dev 的符号为**负**（dur < T）。
"""
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


def main() -> None:
    raw = R.load_files(sorted(DATA.glob("Condition */*.csv")))
    d = raw[raw["is_formal"]].copy()
    d = d[(d.responded == 1) & (d.rt_ms > 0)]
    d["dev"] = d.dur_dev_ms            # 带符号：dur − T
    d["dev_abs"] = d.dev.abs()
    bad = d[d.dev_abs > 16.7].copy()

    print(f"|dev|>16.7 的已响应试次：{len(bad)}")
    print(f"  dev 为负（stimulus 被截短）占 {float((bad.dev < 0).mean())*100:.1f}%；"
          f"为正（刺激更长）占 {float((bad.dev > 0).mean())*100:.1f}%")
    print(f"  RT < T 的占比 {float((bad.rt_ms < bad.T_ms).mean())*100:.1f}%"
          f"（全体已响应里 {float((d.rt_ms < d.T_ms).mean())*100:.2f}%）")

    print("\n== dur 与 rt 的关系（负 dev 组）==")
    neg = bad[bad.dev < 0].copy()
    neg["dur_ms"] = neg.T_ms + neg.dev
    neg["gap_ms"] = neg.dur_ms - neg.rt_ms
    print(f"n={len(neg)}；dur − rt 分位：q10 {float(neg.gap_ms.quantile(.1)):.0f} / "
          f"q50 {float(neg.gap_ms.median()):.0f} / q90 {float(neg.gap_ms.quantile(.9)):.0f} ms")
    print("（若 q50 ≈ 一帧 16.7 ms 或更小，即『按键后下一帧』签名）")

    print("\n== 正 dev 组（刺激比设定更长＝真掉帧）==")
    pos = bad[bad.dev > 0]
    print(f"n={len(pos)}；dev 分位 q50 {float(pos.dev.median()):.0f} / max {float(pos.dev.max()):.0f} ms；"
          f"RT 分位 q50 {float(pos.rt_ms.median()):.0f} ms")

    print("\n== 交叉：RT<200 的试次里，有多少是 RT<T（刺激被截短）==")
    fast = d[d.rt_ms < 200]
    print(f"RT<200 共 {len(fast)}；其中 RT<T {int((fast.rt_ms < fast.T_ms).sum())}"
          f"（{float((fast.rt_ms < fast.T_ms).mean())*100:.1f}%）、"
          f"|dev|>16.7 {int((fast.dev.abs() > 16.7).sum())}")
    print("按 T 档看 RT<T 的快试次："
          + str(fast[fast.rt_ms < fast.T_ms].T_lvl.value_counts().sort_index().to_dict()))


if __name__ == "__main__":
    main()
