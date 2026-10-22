"""按期限 W 拆开看 ΔRT / Δacc / 遗漏率——检验「截断压掉了 RT 效应」的假设。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))
import gen_model_data as G  # noqa: E402

for model in ("M-T1", "M-T3"):
    df = G.load_trials(G.DEFAULT_OUT / model)
    resp = df[df.omission == 0]
    print(f"\n########## {model} ##########")
    hdr = f"{'W':>6} {'遗漏_他人':>9} {'遗漏_自我':>9} {'ΔRT中位':>9} {'ΔRT均值':>9} {'Δacc':>7} {'n/格':>6}"
    print(hdr)
    for W, sub in resp.groupby("W_ms"):
        s, o = sub[sub.is_self == 1], sub[sub.is_self == 0]
        om_s = df[(df.W_ms == W) & (df.is_self == 1)].omission.mean()
        om_o = df[(df.W_ms == W) & (df.is_self == 0)].omission.mean()
        print(f"{W:6.0f} {om_o:9.3f} {om_s:9.3f} "
              f"{o.rt_ms.median() - s.rt_ms.median():+9.1f} "
              f"{o.rt_ms.mean() - s.rt_ms.mean():+9.1f} "
              f"{s.correct.mean() - o.correct.mean():+7.3f} "
              f"{len(sub) // 2:6d}")

    print("\n只看 W=1800（不截断）的 ΔRT，按分位：")
    sub = resp[(resp.W_ms == 1800)]
    for q in (0.1, 0.3, 0.5, 0.7, 0.9):
        a = np.quantile(sub[sub.is_self == 0].rt_ms, q)
        b = np.quantile(sub[sub.is_self == 1].rt_ms, q)
        print(f"   p{int(q*100)}: 他人 {a:6.0f} / 自我 {b:6.0f} ⇒ Δ {a-b:+6.0f} ms")

    print("\n「自我优势」在尾部是否更强（W=1800，p75 以上）：")
    sub = resp[(resp.W_ms == 1800)]
    for lo, hi in ((0, 0.75), (0.75, 1.0)):
        o = sub[sub.is_self == 0].rt_ms
        s = sub[sub.is_self == 1].rt_ms
        oq = np.quantile(o, [lo, hi])
        sq = np.quantile(s, [lo, hi])
        om = o[(o >= oq[0]) & (o <= oq[1])].mean()
        sm = s[(s >= sq[0]) & (s <= sq[1])].mean()
        print(f"   分位 {lo:.2f}–{hi:.2f}: 他人 {om:.0f} / 自我 {sm:.0f} ⇒ Δ {om-sm:+.0f} ms")
