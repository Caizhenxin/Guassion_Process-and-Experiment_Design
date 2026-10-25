# -*- coding: utf-8 -*-
"""_read_power.py —— 把 N_精度 的两个 CSV 压成一张对照表（供写文档取数）。"""
import pandas as pd

p = r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Generate_Data\_power"
stat = pd.read_csv(p + r"\power_precision.csv", encoding="utf-8-sig")
curve = pd.read_csv(p + r"\power_precision_curve.csv", encoding="utf-8-sig")
subj = pd.read_csv(p + r"\power_precision_subjects.csv", encoding="utf-8-sig")

print("=== 全体：SD / 均值 / 定编 ===")
t = stat[stat.group == "全体"]
print(t[["metric", "n_subj", "mean", "sd", "target_se", "n_need"]].to_string(index=False))

print("\n=== 逐组定编（ΔRT / Δacc / slope）===")
piv = stat[stat.group != "全体"].pivot_table(index="group", columns="metric", values="n_need")
print(piv.to_string())
print("四组合计（取每组三指标最大值）=", int(piv.max(axis=1).sum()))

print("\n=== 解析 SD/√N vs 自助实测 SE(N)（全体）===")
c = curve[curve.group == "全体"]
for m in ("drt_med", "d_acc", "slope"):
    s = c[c.metric == m]
    for n in (10, 20, 40, 50):
        r = s[s.N == n]
        if len(r):
            r = r.iloc[0]
            print(f"  {m:8s} N={n:3d}  解析 {r.se_norm:7.4f}  自助 {r.se_boot:7.4f}  "
                  f"差 {100*(r.se_boot/r.se_norm-1):+5.1f}%   检验力 {r.power_boot:.2f}")

print("\n=== 与真实数据（D120）对照 ===")
real = {"drt_med": (38.8, 32.6, 10.0), "d_acc": (0.052, 0.112, 0.03),
        "slope": (44.0, 89.1, 30.0)}
for m, (mu_r, sd_r, tgt) in real.items():
    s = t[t.metric == m].iloc[0]
    print(f"  {m:8s} 模拟 均值 {s['mean']:8.3f} SD {s.sd:7.3f} n={int(s.n_need):3d} | "
          f"真实 均值 {mu_r:8.3f} SD {sd_r:7.3f} n={int(-(-(sd_r/tgt)**2//1)):3d}")

print("\n=== 真实效应量下、各 N 的检验力（正态近似）===")
from math import erf, sqrt
def pw(e, se):
    z = abs(e)/se - 1.959963984540054
    return 0.5*(1+erf(z/sqrt(2)))
for m, (mu_r, sd_r, _) in real.items():
    row = " ".join(f"N={n}:{pw(mu_r, sd_r/sqrt(n)):.2f}" for n in (5, 10, 15, 20, 30, 40))
    print(f"  {m:8s} {row}")
