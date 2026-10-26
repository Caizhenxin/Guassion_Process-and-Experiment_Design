"""对账：stage8 的 tr["rt"] 与 trial_clean.csv 的 rt_ms 是不是同一口径。

上一轮双峰探针用 trial_clean.csv（RT≤400 ms 占 11.1%），而窄窗 λ 剖面用
stage8 的 tr["rt"]（每名被试 ≤400 ms 只有 11–13 个，约 2%）。两者差 5 倍，
必须先弄清差在哪，否则「快带」的规模会被误报。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))

import stage8_run as S            # noqa: E402
from mapping import MappingParams  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
d = pd.read_csv(REPO / "2_Data" / "Generate_Data" / "_real_check" / "trial_clean.csv",
                encoding="utf-8-sig")
print("trial_clean 列：", list(d.columns))
if "is_formal" in d.columns:
    d = d[d["is_formal"].astype(bool)]
print(f"trial_clean 正式段 {len(d)} 行；RT 中位 {d['rt_ms'].median():.0f} ms，"
      f"min {d['rt_ms'].min():.0f}，≤400 ms {int((d['rt_ms'] <= 400).sum())} 个")

people, rejected = S.collect([DATA], None, MappingParams(shape_model="lin"))
rows = []
tot = tot_fast = 0
for p in people:
    tr = p["tr"]
    om = tr["omission"] == 0
    rt = tr["rt"][om]
    tot += rt.size
    tot_fast += int((rt <= 0.40).sum())
    rows.append((p["group"], p["subject"], rt.size, int((rt <= 0.40).sum()),
                 float(np.median(rt)), float(rt.min()), float(tr["W"].max())))
print(f"\nstage8 汇总：响应试次 {tot}，≤400 ms {tot_fast} 个"
      f"（{tot_fast / tot * 100:.1f}%）")
print(f"{'组':>3s}{'被试':>5s}{'n':>6s}{'≤0.4s':>7s}{'中位':>7s}{'min':>7s}{'Wmax':>6s}")
for g, s, n, f, med, mn, wm in rows:
    print(f"{g:>3d}{s:>5d}{n:>6d}{f:>7d}{med:>7.3f}{mn:>7.3f}{wm:>6.2f}")

# 同一名被试：csv 的行与 txt 的试次是否都 ≤400 ms
print("\n按被试对比 trial_clean 与 stage8（前 5 人）：")
key = [c for c in ("group", "subject", "subj", "gid", "sid") if c in d.columns]
print("  csv 分组列：", key)
