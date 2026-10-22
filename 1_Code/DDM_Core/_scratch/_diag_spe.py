"""诊断：自我 vs 他人 的 RT / 正确率到底差多少，是否与漂移差匹配。

检查三件事：
1. 真值漂移 `d_stim` 在 self/other 上的差（机制有没有进去）
2. 观测 RT（均值/中位/分位）与正确率的差，逐被试配对
3. 按 DDM 解析式反推「这么大的漂移差应该产生多大的 RT 差」
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import gen_model_data as G  # noqa: E402

OUT = G.DEFAULT_OUT / "M-T1"
df = G.load_trials(OUT)
d = df[df.omission == 0].copy()

print("=== 1. 真值漂移（机制是否进入）===")
t = df.groupby("is_self")["d_stim"].agg(["mean", "std", "count"])
print(t.round(4).to_string())
print(f"Δd_stim（自我 − 他人）= {t.loc[1, 'mean'] - t.loc[0, 'mean']:.4f}")

print("\n=== 2. 逐被试配对差（RT 与正确率）===")
rows = []
for sid, sub in d.groupby("subject_id"):
    s = sub[sub.is_self == 1]
    o = sub[sub.is_self == 0]
    rows.append({
        "subject": sid,
        "rt_mean_self": s.rt_ms.mean(), "rt_mean_other": o.rt_ms.mean(),
        "rt_med_self": s.rt_ms.median(), "rt_med_other": o.rt_ms.median(),
        "acc_self": s.correct.mean(), "acc_other": o.correct.mean(),
    })
r = pd.DataFrame(rows)
r["d_mean"] = r.rt_mean_other - r.rt_mean_self      # 正 = 自我更快
r["d_med"] = r.rt_med_other - r.rt_med_self
r["d_acc"] = r.acc_self - r.acc_other               # 正 = 自我更准


def ci(x):
    x = np.asarray(x, float)
    se = x.std(ddof=1) / np.sqrt(x.size)
    tcrit = 2.131 if x.size == 16 else 1.96
    return x.mean(), x.mean() - tcrit * se, x.mean() + tcrit * se


for col, label in (("d_mean", "ΔRT 均值 (他人−自我, ms)"),
                   ("d_med", "ΔRT 中位 (他人−自我, ms)"),
                   ("d_acc", "Δ正确率 (自我−他人)")):
    m, lo, hi = ci(r[col])
    print(f"{label:26s} = {m:+8.2f}  [{lo:+.2f}, {hi:+.2f}]   "
          f"{'不含0 ✅' if (lo > 0) == (hi > 0) else '含0 ❌'}")

print("\n前 6 名被试：")
print(r.head(6).round(3).to_string(index=False))

print("\n=== 3. 解析预期：这么大的漂移差该产生多大 RT 差 ===")


def mean_dt(v, a):
    """无偏起点、无变异时的平均决策时间（s）。"""
    v = np.asarray(v, float)
    av = a * v
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.abs(av) < 1e-6, a * a / 4.0,
                        (a / (2 * v)) * np.tanh(av / 2.0))


def p_correct(v, a, z=0.5):
    return 1.0 / (1.0 + np.exp(-2.0 * a * v * (z - 0.0) * 0 + 0)) * 0 + \
        1.0 / (1.0 + np.exp(-a * v))


d_other = float(df[df.is_self == 0].d_stim.mean())
d_self = float(df[df.is_self == 1].d_stim.mean())
a = float(df.a.mean())
print(f"平均漂移：他人 {d_other:.3f} / 自我 {d_self:.3f}；平均边界 a = {a:.3f}，t0 = {df.t0_ms.mean():.1f} ms")
print(f"解析平均 DT：他人 {mean_dt(d_other, a)*1000:.0f} ms / 自我 {mean_dt(d_self, a)*1000:.0f} ms "
      f"⇒ 预期 ΔRT ≈ {1000*(mean_dt(d_other, a)-mean_dt(d_self, a)):+.0f} ms")
print(f"解析正确率：他人 {p_correct(d_other, a):.3f} / 自我 {p_correct(d_self, a):.3f} "
      f"⇒ 预期 Δacc ≈ {100*p_correct(d_self, a)-100*p_correct(d_other, a):+.1f} pp")
print(f"实测正确率：他人 {d[d.is_self==0].correct.mean():.3f} / 自我 {d[d.is_self==1].correct.mean():.3f}")

print("\n=== 4. 各 T 水平上的 ΔRT / Δacc（看效应是否被 T 稀释）===")
for T, sub in d.groupby("T_ms"):
    s, o = sub[sub.is_self == 1], sub[sub.is_self == 0]
    print(f"T={T:5.1f} ms  ΔRT中位 {o.rt_ms.median()-s.rt_ms.median():+7.1f} ms   "
          f"Δacc {s.correct.mean()-o.correct.mean():+.3f}   "
          f"drift 他人 {o.d_stim.mean():.3f} / 自我 {s.d_stim.mean():.3f}")
