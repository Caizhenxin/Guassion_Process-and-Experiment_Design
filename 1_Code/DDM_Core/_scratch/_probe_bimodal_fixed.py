"""双峰结论的修正版：剔掉抢按（premature）后重算 RT 分带正确率。

原 `_probe_bimodal.py` 用 trial_clean.csv 全部正式段响应行（8,355），其中
包含 1,211 个抢按/预按试次 —— 它们 RT 短（121–400 ms）且正确率接近机会，
于是制造出「11.1% 试次在 400 ms 内、正确率 0.544」的假双峰。stage8 的似然
本来就剔掉这些试次（只剩 7,144），所以那些短 RT **不在模型要解释的数据里**。
"""
import numpy as np
import pandas as pd

D = r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
d = pd.read_csv(f"{D}\\2_Data\\Generate_Data\\_real_check\\trial_clean.csv",
                encoding="utf-8-sig")
d = d[d["is_formal"].astype(bool)]
print(f"正式段 {len(d)} 行；responded={int(d['responded'].sum())}、"
      f"premature={int(d['premature'].sum())}")

prem = d[d["premature"].astype(bool)]
print(f"抢按试次：n={len(prem)}，RT 中位 {prem['rt_ms'].median():.0f} ms、"
      f"min {prem['rt_ms'].min():.0f}、max {prem['rt_ms'].max():.0f}；"
      f"acc={prem['correct'].mean():.3f}")

clean = d[d["responded"] & ~d["premature"].astype(bool)]
print(f"\n剔抢按后的响应试次：{len(clean)}（RT 中位 {clean['rt_ms'].median():.0f} ms）")

edges = [0.0, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.8, 10.0]
for label, frame in (("剔抢按", clean), ("原口径（含抢按）", d[d["responded"]])):
    print(f"\n=== {label}：n={len(frame)} ===")
    print(f"{'RT 带(ms)':>12s}{'n':>7s}{'acc':>7s}{'95%CI':>18s}{'占比':>7s}")
    b = frame.assign(band=pd.cut(frame["rt_ms"], [e * 1000 for e in edges],
                                 right=False))
    for band, g in b.groupby("band", observed=True):
        n = len(g)
        if n == 0:
            continue
        acc = g["correct"].mean()
        se = np.sqrt(acc * (1 - acc) / n)
        print(f"{str(band):>12s}{n:>7d}{acc:>7.3f}"
              f"   [{acc - 1.96 * se:.3f}, {acc + 1.96 * se:.3f}]{n / len(frame) * 100:>6.1f}%")
    f = frame[frame["rt_ms"] <= 400]
    s = frame[frame["rt_ms"] > 400]
    print(f"RT<=400：n={len(f)}（{len(f) / len(frame) * 100:.1f}%）acc={f['correct'].mean():.3f}"
          f"  |  >400：n={len(s)}（{len(s) / len(frame) * 100:.1f}%）acc={s['correct'].mean():.3f}")
