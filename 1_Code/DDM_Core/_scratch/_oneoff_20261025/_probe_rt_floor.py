"""为「RT 下限 0.15 → 0.20 + 剔除掉帧试次」找读数依据。

① 各 RT 带的正确率与占比（0.12–0.15 / 0.15–0.20 / 0.20–0.25 / 0.25–0.30 / >0.30）
② 掉帧试次（|dev|>1 帧）在各 RT 带的分布
③ 逐被试：两种口径下的 min(RT) 与 t0 上界（现状 0.15 / 拟改 0.20+去掉帧）
④ 被剔试次总量（占已响应比例）
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
KEEP = ["1-1", "1-2", "1-3", "1-4", "1-5", "2-1", "2-2", "2-3", "2-4", "2-5",
        "3-2", "3-3", "3-4", "3-5", "4-1", "4-2", "4-4", "4-5"]
pd.set_option("display.width", 200)


def main() -> None:
    raw = R.load_files(sorted(DATA.glob("Condition */*.csv")))
    d = raw[raw["is_formal"]].copy()
    d = d[(d.responded == 1) & (d.rt_ms > 0)]
    d["dev_abs"] = d.dur_dev_ms.abs()
    d["dev_bad"] = d.dev_abs > 16.7

    print("== ① 各 RT 带的正确率（全体已响应）==")
    edges = [120, 150, 200, 250, 300, 400, 1e9]
    d["band"] = pd.cut(d.rt_ms, edges, right=False,
                       labels=["120-150", "150-200", "200-250", "250-300", "300-400", ">400"])
    t = d.groupby("band", observed=False).agg(n=("correct", "size"),
                                              acc=("correct", "mean"),
                                              dev_bad=("dev_bad", "sum"))
    t["pct"] = (t.n / t.n.sum() * 100).round(2)
    t["dev_bad_pct"] = (t.dev_bad / t.n * 100).round(1)
    print(t.round(3).to_string())

    print("\n== ② 掉帧试次在各带的分布 ==")
    bad = d[d.dev_bad]
    print(f"|dev|>1 帧共 {len(bad)} 行；RT 分位 q10 {float(bad.rt_ms.quantile(.1)):.0f} "
          f"/ q50 {float(bad.rt_ms.median()):.0f} / q90 {float(bad.rt_ms.quantile(.9)):.0f}")

    print("\n== ③ 逐被试 min(RT) / t0 上界：现状 vs 拟改 ==")
    rows = []
    for sid in KEEP:
        g = d[d.subject_id == sid]
        if not len(g):
            continue
        cur = g[g.rt_ms >= 150]
        new = g[(g.rt_ms >= 200) & (~g.dev_bad)]
        rows.append({"sid": sid, "n_resp": len(g),
                     "min_cur": cur.rt_ms.min(), "min_new": new.rt_ms.min(),
                     "cap_cur": cur.rt_ms.min() / 1000 - 0.02,
                     "cap_new": new.rt_ms.min() / 1000 - 0.02,
                     "n_drop_cur": int((g.rt_ms < 150).sum()),
                     "n_drop_new": int(((g.rt_ms < 200) | g.dev_bad).sum())})
    t = pd.DataFrame(rows).set_index("sid")
    t["gain_ms"] = (t.cap_new - t.cap_cur) * 1000
    print(t.round(3).to_string())
    print(f"\ncap<0.10 的被试数：现状 {int((t.cap_cur < 0.10).sum())} / {len(t)}，"
          f"拟改 {int((t.cap_new < 0.10).sum())} / {len(t)}")

    print("\n== ④ 剔除量 ==")
    tot = len(d)
    print(f"现状（rt<150）：{int((d.rt_ms < 150).sum())} / {tot} = "
          f"{float((d.rt_ms < 150).mean())*100:.2f}%")
    print(f"拟改（rt<200 或掉帧）：{int(((d.rt_ms < 200) | d.dev_bad).sum())} / {tot} = "
          f"{float(((d.rt_ms < 200) | d.dev_bad).mean())*100:.2f}%")


if __name__ == "__main__":
    main()
