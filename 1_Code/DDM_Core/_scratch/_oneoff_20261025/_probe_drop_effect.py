"""剔除「刺激期内按键」试次，对 SPE 端点本身有多大影响？

只回答一个问题：丢掉这 1.8% 的试次，ΔRT / Δacc / 分位斜率会不会变。
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
QS = (0.1, 0.3, 0.5, 0.7, 0.9)


def endpoints(d: pd.DataFrame) -> dict:
    out = {}
    for sid, g in d.groupby("subject_id"):
        s, o = g[g.is_self == 1], g[g.is_self == 0]
        if not len(s) or not len(o):
            continue
        out[sid] = {
            "d_acc": float(s.correct.mean() - o.correct.mean()),
            "drt": float(np.median(o.rt_ms) - np.median(s.rt_ms)),
            "slope": float(np.mean([np.percentile(o.rt_ms, q * 100) - np.percentile(s.rt_ms, q * 100)
                                    for q in QS])),
        }
    return out


def summarize(name: str, ep: dict) -> None:
    t = pd.DataFrame(ep).T
    print(f"\n== {name}（{len(t)} 人）==")
    for k, unit in (("d_acc", "pp*100"), ("drt", "ms"), ("slope", "ms")):
        v = t[k].astype(float)
        mean = v.mean()
        se = v.std(ddof=1) / np.sqrt(len(v))
        print(f"  {k:6s} 均值 {mean:8.4f} {unit:6s} SE {se:7.4f}  "
              f"95% CI [{mean - 1.96 * se:8.4f}, {mean + 1.96 * se:8.4f}]")


def main() -> None:
    raw = R.load_files(sorted(DATA.glob("Condition */*.csv")))
    d = raw[raw["is_formal"]].copy()
    d = d[(d.responded == 1) & (d.rt_ms > 0) & d.subject_id.isin(KEEP)]

    a = endpoints(d)
    drop = (d.rt_ms < 200) | (d.dur_dev_ms.abs() > 16.7)
    print(f"拟剔除 {int(drop.sum())}/{len(d)} = {float(drop.mean()) * 100:.2f}%")
    b = endpoints(d[~drop])

    summarize("全部已响应试次（含快试次）", a)
    summarize("剔除快试次与刺激期内按键后", b)

    ta, tb = pd.DataFrame(a).T, pd.DataFrame(b).T
    diff = tb - ta
    print("\n== 逐人变化（剔后 − 剔前）==")
    for k in ("d_acc", "drt", "slope"):
        dd = diff[k].astype(float)
        print(f"  {k:6s} 均值变化 {dd.mean():+8.4f}  最大 |变化| {dd.abs().max():8.4f}")


if __name__ == "__main__":
    main()
