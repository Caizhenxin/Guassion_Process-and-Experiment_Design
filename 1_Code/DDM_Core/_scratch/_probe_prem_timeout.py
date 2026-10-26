# -*- coding: utf-8 -*-
"""回答结果章 9.1/9.3 的遗留疑问：S6-6（注视期抢按 10.84%）与 W=800 超时 45.5%
是不是同一个「急」的两种表现。

做法：逐被试算 prem 率、W=800 / 1200 / 1800 的超时率、以及 W=800 下响应试次的
RT 中位，做 Spearman 相关（17 人）。若两者同源，应见到显著正相关且 RT 更快的
被试 prem 更高。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
STAGE = ROOT / "2_Data/Real_Data/New_Design/_stage6_in"
SNAP = ROOT / "4_Reports/筛查_New_Design_20261024.json"
W_LEVELS = (800.0, 1200.0, 1800.0)


def nearest(v: float, levels) -> float:
    return min(levels, key=lambda x: abs(x - v))


def main() -> int:
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    keep = {(r["group"], r["subject"]) for r in snap["sessions"] if r["verdict"] == "KEEP"}
    rows = []
    for p in sorted(STAGE.glob("EXP_data_group*.csv")):
        df = pd.read_csv(p, encoding="utf-8-sig")
        df["gid"] = pd.to_numeric(df["groupID"], errors="coerce").astype("Int64")
        df["sid"] = pd.to_numeric(df["subjectID"], errors="coerce").astype("Int64")
        df = df[(df["gid"].notna()) & (df["sid"].notna())]
        g, s = int(df["gid"].iloc[0]), int(df["sid"].iloc[0])
        if (g, s) not in keep:
            continue
        df = df[df["stage"].astype(str).str.lower().str.strip() == "formal"].copy()
        df["W_lvl"] = [nearest(v * 1000.0, W_LEVELS)
                       for v in pd.to_numeric(df["W"], errors="coerce")]
        df["rt_ms"] = pd.to_numeric(df["RT"], errors="coerce") * 1000.0
        df["responded"] = pd.to_numeric(df["responded_by_deadline"],
                                        errors="coerce").fillna(0).astype(int)
        df["prem"] = pd.to_numeric(df["premature_press"],
                                   errors="coerce").fillna(0).astype(int)
        r = {"id": f"{g}-{s}", "n": len(df), "prem": float(df["prem"].mean()),
             "to_all": float(1 - df["responded"].mean())}
        for w in W_LEVELS:
            sub = df[df["W_lvl"] == w]
            r[f"to_{int(w)}"] = float(1 - sub["responded"].mean()) if len(sub) else np.nan
            ok = sub[sub["responded"] == 1]
            r[f"rt_{int(w)}"] = float(ok["rt_ms"].median()) if len(ok) else np.nan
        rows.append(r)
    d = pd.DataFrame(rows).sort_values("id")
    print(f"n = {len(d)} 人")
    print(d.round(3).to_string(index=False))
    print()
    for a, b in (("prem", "to_800"), ("prem", "to_1200"), ("prem", "to_1800"),
                 ("prem", "to_all"), ("prem", "rt_800"), ("to_800", "rt_800")):
        rho, p = stats.spearmanr(d[a], d[b])
        print(f"Spearman {a:>6s} vs {b:<7s} = {rho:+.3f}  p = {p:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
