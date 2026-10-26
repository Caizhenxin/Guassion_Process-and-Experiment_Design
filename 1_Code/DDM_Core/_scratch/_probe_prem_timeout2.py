# -*- coding: utf-8 -*-
"""复核：S6-6 抢按与 W=800 超时的 +0.774 相关是否**机械**（同一批试次被两边计数）。

判据：把抢按试次从分母里剔掉再看相关；再看抢按行本身的 responded 标记。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
STAGE = ROOT / "2_Data/Real_Data/New_Design/_stage6_in"
SNAP = ROOT / "4_Reports/筛查_New_Design_20261024.json"

rows, overlap = [], []
for p in sorted(STAGE.glob("EXP_data_group*.csv")):
    df = pd.read_csv(p, encoding="utf-8-sig")
    df["gid"] = pd.to_numeric(df["groupID"], errors="coerce").astype("Int64")
    df["sid"] = pd.to_numeric(df["subjectID"], errors="coerce").astype("Int64")
    df = df[(df["gid"].notna()) & (df["sid"].notna())]
    g, s = int(df["gid"].iloc[0]), int(df["sid"].iloc[0])
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    keep = {(r["group"], r["subject"]) for r in snap["sessions"] if r["verdict"] == "KEEP"}
    if (g, s) not in keep:
        continue
    df = df[df["stage"].astype(str).str.lower().str.strip() == "formal"].copy()
    df["W_ms"] = pd.to_numeric(df["W"], errors="coerce") * 1000.0
    df["resp"] = pd.to_numeric(df["responded_by_deadline"], errors="coerce").fillna(0).astype(int)
    df["prem"] = pd.to_numeric(df["premature_press"], errors="coerce").fillna(0).astype(int)
    overlap.append({"id": f"{g}-{s}",
                    "prem_n": int(df["prem"].sum()),
                    "prem_and_timeout": int(((df["prem"] == 1) & (df["resp"] == 0)).sum())})
    w = df[df["W_ms"].round() == 800]
    clean = w[w["prem"] == 0]
    rows.append({"id": f"{g}-{s}", "prem": float(df["prem"].mean()),
                 "to800": float(1 - w["resp"].mean()),
                 "to800_noprem": float(1 - clean["resp"].mean()) if len(clean) else np.nan})
d = pd.DataFrame(rows)
o = pd.DataFrame(overlap)
print("抢按试次里同时被判 timeout 的比例：")
o["frac"] = o["prem_and_timeout"] / o["prem_n"].replace(0, np.nan)
print(o.round(3).to_string(index=False))
print("\n合计：抢按 %d 个，其中 timeout 标记 %d 个"
      % (o["prem_n"].sum(), o["prem_and_timeout"].sum()))
print("\n相关（原口径 vs 剔除抢按试次后）：")
for b in ("to800", "to800_noprem"):
    rho, p = stats.spearmanr(d["prem"], d[b])
    print(f"  prem vs {b:<12s} = {rho:+.3f}  p = {p:.4f}")
print(d.round(3).to_string(index=False))
