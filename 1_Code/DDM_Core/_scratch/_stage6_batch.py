# -*- coding: utf-8 -*-
"""Stage 6 判据的**批层**口径（方案 S6-1 的「整体 / 最差单元」是批层语言）。

输入：`2_Data/Real_Data/New_Design/_stage6_in/*.csv` + intake 快照里的 KEEP 名单。
输出：批层 timeout / 正确率 / premature / RT<T / 0.15<=RT<T / 过快，以及最差 (T,W) 单元。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
STAGE = ROOT / "2_Data/Real_Data/New_Design/_stage6_in"
SNAP = ROOT / "4_Reports/筛查_New_Design_20261024.json"
T_LEVELS = (33.3, 83.3, 150.0, 250.0)
W_LEVELS = (800.0, 1200.0, 1800.0)


def nearest(v: float, levels) -> float:
    return min(levels, key=lambda x: abs(x - v))


def main() -> int:
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    keep = {(r["group"], r["subject"]) for r in snap["sessions"] if r["verdict"] == "KEEP"}
    frames = []
    for p in sorted(STAGE.glob("EXP_data_group*.csv")):
        df = pd.read_csv(p, encoding="utf-8-sig")
        df["gid"] = pd.to_numeric(df["groupID"], errors="coerce").astype("Int64")
        df["sid"] = pd.to_numeric(df["subjectID"], errors="coerce").astype("Int64")
        df = df[(df["gid"].notna()) & (df["sid"].notna())]
        g, s = int(df["gid"].iloc[0]), int(df["sid"].iloc[0])
        if (g, s) not in keep:
            continue
        df = df[df["stage"].astype(str).str.lower().str.strip() == "formal"].copy()
        df["T_ms"] = pd.to_numeric(df["T"], errors="coerce") * 1000.0
        df["W_ms"] = pd.to_numeric(df["W"], errors="coerce") * 1000.0
        df["T_lvl"] = [nearest(v, T_LEVELS) for v in df["T_ms"]]
        df["W_lvl"] = [nearest(v, W_LEVELS) for v in df["W_ms"]]
        df["rt_ms"] = pd.to_numeric(df["RT"], errors="coerce") * 1000.0
        df["responded"] = pd.to_numeric(df["responded_by_deadline"], errors="coerce").fillna(0).astype(int)
        df["correct"] = pd.to_numeric(df["Correct"], errors="coerce").fillna(0).astype(int)
        df["prem"] = pd.to_numeric(df["premature_press"], errors="coerce").fillna(0).astype(int)
        frames.append(df)
    d = pd.concat(frames, ignore_index=True)
    n = len(d)
    resp = d[d["responded"] == 1]
    print(f"批层：{len(frames)} 人 / {n} 试次（正式段）")
    print()
    to = 1 - d["responded"].mean()
    print(f"S6-1  timeout 整体 = {to:.1%}（阈值 ≤20%）")
    cell = d.groupby(["T_lvl", "W_lvl"])["responded"].agg(["mean", "size"])
    cell["timeout"] = 1 - cell["mean"]
    worst = cell.loc[cell["timeout"].idxmax()]
    print(f"      最差单元 timeout = {worst['timeout']:.1%}（阈值 ≤40%）@ T={cell['timeout'].idxmax()[0]} ms, "
          f"W={cell['timeout'].idxmax()[1]} ms, n={int(worst['size'])}")
    print()
    acc = resp["correct"].mean()
    print(f"S6-5  正确率（响应试次）= {acc:.3f}（PASS 带 0.55–0.98）")
    print(f"      RT 中位 = {resp['rt_ms'].median():.0f} ms（PASS 带 ≥300 ms）")
    post = resp[resp["rt_ms"] >= resp["T_ms"]]
    print(f"      过快（RT≥T 的分母 {len(post)}）= {(post['rt_ms'] < 150).mean():.2%}（阈值 ≤10%）")
    print()
    rtt = (resp["rt_ms"] < resp["T_ms"]).mean()
    inner = ((resp["rt_ms"] >= 150) & (resp["rt_ms"] < resp["T_ms"])).mean()
    print(f"S6-2  RT < T 总比例 = {rtt:.2%}（≤20% PASS）")
    print(f"S6-2c 0.15 ≤ RT < T = {inner:.2%}（≤20% PASS ⇒ Stage 8 用静态输入）")
    print()
    print(f"S6-6  注视期抢按 = {d['prem'].mean():.2%}（阈值 ≤10%）")
    print()
    print("按 T 档：")
    print(d.groupby("T_lvl").apply(
        lambda x: pd.Series({
            "n": len(x),
            "timeout": 1 - x["responded"].mean(),
            "acc": x.loc[x["responded"] == 1, "correct"].mean(),
            "rt_med": x.loc[x["responded"] == 1, "rt_ms"].median(),
        }), include_groups=False).round(3).to_string())
    print()
    print("按 W 档：")
    print(d.groupby("W_lvl").apply(
        lambda x: pd.Series({
            "n": len(x),
            "timeout": 1 - x["responded"].mean(),
            "acc": x.loc[x["responded"] == 1, "correct"].mean(),
            "rt_med": x.loc[x["responded"] == 1, "rt_ms"].median(),
        }), include_groups=False).round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
