# -*- coding: utf-8 -*-
"""结果章 9.1/9.3 需要的数字：人口学构成 + 按 P 的行为层（17 KEEP，正式段）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
STAGE = ROOT / "2_Data/Real_Data/New_Design/_stage6_in"
SNAP = ROOT / "4_Reports/筛查_New_Design_20261024.json"


def main() -> int:
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    keep = {(r["group"], r["subject"]) for r in snap["sessions"] if r["verdict"] == "KEEP"}
    rows, demo = [], {}
    for p in sorted(STAGE.glob("EXP_data_group*.csv")):
        df = pd.read_csv(p, encoding="utf-8-sig")
        g = int(pd.to_numeric(df["groupID"], errors="coerce").dropna().iloc[0])
        s = int(pd.to_numeric(df["subjectID"], errors="coerce").dropna().iloc[0])
        if (g, s) not in keep:
            continue
        d = df[df["stage"].astype(str).str.lower().str.strip() == "formal"].copy()
        d["responded"] = pd.to_numeric(d["responded_by_deadline"], errors="coerce").fillna(0).astype(int)
        d["correct"] = pd.to_numeric(d["Correct"], errors="coerce").fillna(0).astype(int)
        d["rt_ms"] = pd.to_numeric(d["RT"], errors="coerce") * 1000.0
        d["P"] = pd.to_numeric(d["P"], errors="coerce").astype(int)
        rows.append(d[["P", "responded", "correct", "rt_ms"]])
        demo[(g, s)] = {
            "gender": df["gender"].dropna().astype(str).iloc[0],
            "age": pd.to_numeric(df["age"], errors="coerce").dropna().mean(),
            "hand": df["handedness"].dropna().astype(str).iloc[0],
        }
    d = pd.concat(rows, ignore_index=True)
    resp = d[d["responded"] == 1]
    print(f"计入 {len(demo)} 人 / {len(d)} 试次（正式段）")
    print()
    print(f"性别：{pd.Series([v['gender'] for v in demo.values()]).value_counts().to_dict()}")
    ages = [v["age"] for v in demo.values() if v["age"] == v["age"]]
    print(f"年龄：M={sum(ages)/len(ages):.1f}，范围 {min(ages):.0f}–{max(ages):.0f}（n={len(ages)}）")
    print(f"利手：{pd.Series([v['hand'] for v in demo.values()]).value_counts().to_dict()}")
    print()
    t = d.groupby("P").apply(lambda x: pd.Series({
        "n_subj": len(x) / 576,
        "n_trial": len(x),
        "acc_resp": x.loc[x["responded"] == 1, "correct"].mean(),
        "acc_all": x["correct"].mean(),
        "timeout": 1 - x["responded"].mean(),
        "rt_med": x.loc[x["responded"] == 1, "rt_ms"].median(),
    }), include_groups=False).round(3)
    print(t.to_string())
    print()
    print("自我/他人（按 P，响应试次）：")
    for p, grp in [("P", d)]:
        pass
    for p in sorted(d["P"].unique()):
        sub = d[d["P"] == p]
        s_sub = sub  # 无身份列在此表里；用 separate script 时的结果
        print(f"  P={p}: n={len(sub)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
