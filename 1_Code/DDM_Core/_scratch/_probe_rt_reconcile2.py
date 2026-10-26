"""对账 3：逐试次比对 txt 的 RT 与 trial_clean 的 rt_ms（同一被试、同一顺序）。

目的：确定「stage8 保留的响应试次」与 trial_clean 的 8,355 行差在哪，
从而知道 ≤400 ms 快带在**模型实际解释的数据**里到底占多少。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))
import read_formal_data as RF   # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
tc = pd.read_csv(REPO / "2_Data" / "Generate_Data" / "_real_check" / "trial_clean.csv",
                 encoding="utf-8-sig")
tc = tc[tc["is_formal"].astype(bool)]

for g, s in ((2, 5), (1, 1)):
    f = DATA / f"exp_group{g}_subject{s}.txt"
    rec, rep = RF.load_file(f, stage="formal")
    tr_full = RF.to_trials(rec)
    tr, fr = RF.fit_ready(tr_full, rec=rec)
    sub = tc[(tc["groupID"] == g) & (tc["subjectID"] == s)].sort_values("trialID")
    print(f"\n=== {g}-{s} ===")
    print(f"txt 全部试次 {np.asarray(tr_full['rt']).size}、"
          f"fit_ready 保留 {np.asarray(tr['rt']).size}"
          f"（剔 {fr.get('n_dropped')}，其中刺激期内 {fr.get('n_dropped_dev')}）；"
          f"trial_clean 行 {len(sub)}")
    om_full = np.asarray(tr_full["omission"]) == 0
    rt_full_resp = np.asarray(tr_full["rt"])[om_full]
    rt_tc = sub["rt_ms"].to_numpy() / 1000.0
    print(f"txt 响应 {rt_full_resp.size} vs tc {rt_tc.size}"
          f"（差 {rt_full_resp.size - rt_tc.size}）")
    n = min(rt_full_resp.size, rt_tc.size)
    if n:
        diff = np.abs(rt_full_resp[:n] - rt_tc[:n])
        print(f"前 {n} 个逐位比对：完全相等 {int((diff < 1e-9).sum())}、"
              f"不一致 {int((diff >= 1e-9).sum())}、最大差 {diff.max():.4f} s")
        bad = np.where(diff >= 1e-9)[0][:5]
        for i in bad:
            print(f"   #{i}: txt {rt_full_resp[i]:.3f}s  tc {rt_tc[i]:.3f}s")
    print(f"txt 响应里 ≤400 ms {int((rt_full_resp <= 0.40).sum())} 个；"
          f"tc 里 ≤400 ms {int((rt_tc <= 0.40).sum())} 个")
    om = np.asarray(tr["omission"]) == 0
    rt_keep = np.asarray(tr["rt"])[om]
    print(f"fit_ready 保留的响应里 ≤400 ms {int((rt_keep <= 0.40).sum())} 个"
          f"（占保留响应 {rt_keep.size} 的 {np.mean(rt_keep <= 0.40) * 100:.1f}%）")
