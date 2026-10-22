"""追查：为什么漂移差 0.32 却只有 13 ms 的 RT 差。

两个候选机制：
A. 遗漏截断（censoring）：低漂移的慢试次变成超时，被剔出 RT ⇒ 差被压缩
B. 逐试次漂移变异：RT 离散度远大于位移 ⇒ 视觉与统计上都难分辨
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
import twophase  # noqa: E402

TMP = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "_diag_spe_out"

df = G.load_trials(G.DEFAULT_OUT / "M-T1")

print("=== A. 遗漏率（截断方向）===")
om = df.groupby(["is_self"])["omission"].mean()
print(om.round(4).to_string())
print("按 T：")
print(df.pivot_table(index="T_ms", columns="is_self", values="omission",
                     aggfunc="mean").round(4).to_string())

resp = df[df.omission == 0]
print("\n被截掉的 RT 会有多慢？用「已响应」的最高分位外推：")
for ident, sub in resp.groupby("is_self"):
    q = np.quantile(sub.rt_ms, [0.95, 0.99])
    print(f"  身份 {int(ident)}：p95 {q[0]:.0f} ms / p99 {q[1]:.0f} ms，"
          f"遗漏 {df[df.is_self == ident].omission.mean():.3f}")

print("\n=== B. 关掉漂移变异（drift_sd=0）再生成一次 ===")
res0 = G.generate("M-T1", TMP / "nodrift", n_subjects_per_group=4, rho=0.8,
                  drift_sd=0.0, seed=20261021, verbose=False)
d0 = G.load_trials(TMP / "nodrift")
r0 = d0[d0.omission == 0]
rows = []
for sid, sub in r0.groupby("subject_id"):
    s, o = sub[sub.is_self == 1], sub[sub.is_self == 0]
    rows.append({"d_mean": o.rt_ms.mean() - s.rt_ms.mean(),
                 "d_med": o.rt_ms.median() - s.rt_ms.median(),
                 "d_acc": s.correct.mean() - o.correct.mean()})
rr = pd.DataFrame(rows)


def ci(x):
    x = np.asarray(x, float)
    se = x.std(ddof=1) / np.sqrt(x.size)
    tcrit = 2.131 if x.size == 16 else 1.96
    return x.mean(), x.mean() - tcrit * se, x.mean() + tcrit * se


for col, label in (("d_mean", "ΔRT 均值"), ("d_med", "ΔRT 中位"), ("d_acc", "Δ正确率")):
    m, lo, hi = ci(rr[col])
    print(f"  {label:8s} = {m:+8.2f}  [{lo:+.2f}, {hi:+.2f}]")
print(f"  遗漏率：{d0.omission.mean():.3f}（有 drift_sd 时 {df.omission.mean():.3f}）")
print(f"  RT 标准差：{r0.rt_ms.std():.0f} ms")
print(f"  正确率：{r0.correct.mean():.3f}")

print("\n=== C. 效应量的「信噪比」直觉 ===")
sd = resp.rt_ms.std()
dlt = 13.6
print(f"  RT 分布 SD ≈ {sd:.0f} ms，位移 ≈ {dlt:.0f} ms ⇒ 位移只占 {dlt / sd * 100:.1f}% 宽度"
      f"（d ≈ {dlt / sd:.2f}）")
print(f"  要在密度图上肉眼看出位移，至少需要 d ≳ 0.5（即位移 ≳ {0.5 * sd:.0f} ms）")

print("\n=== D. 分位数上的位移（漂移型 vs 平移型）===")
qs = [0.1, 0.3, 0.5, 0.7, 0.9]
for ident in (0, 1):
    sub = resp[resp.is_self == ident]
    print(f"  身份 {ident}: " + "  ".join(f"p{int(q*100)}={np.quantile(sub.rt_ms, q):.0f}"
                                        for q in qs))
print("  差值（他人−自我）: " + "  ".join(
    f"p{int(q*100)}={np.quantile(resp[resp.is_self==0].rt_ms,q)-np.quantile(resp[resp.is_self==1].rt_ms,q):+.0f}"
    for q in qs))
