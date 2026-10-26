"""快反应带的正确率：判断「是不是双峰（猜测 + 真决策）」。

用逐试次级清洗表（正式段、responded=1），按 RT 分箱算正确率与二项 95% CI。
"""
import numpy as np
import pandas as pd

D = r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
d = pd.read_csv(f"{D}\\2_Data\\Generate_Data\\_real_check\\trial_clean.csv",
                encoding="utf-8-sig")
print("列：", list(d.columns))
if "is_formal" in d.columns:
    d = d[d["is_formal"].astype(bool)]
print(f"正式段响应试次 {len(d)}")

edges = [0.0, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.80, 10.0]
d = d.assign(band=pd.cut(d["rt_ms"], [e * 1000 for e in edges], right=False))
print(f"\n{'RT 带(ms)':>14s}{'n':>7s}{'acc':>7s}{'95%CI':>16s}{'占比':>7s}")
for band, g in d.groupby("band", observed=True):
    n = len(g)
    acc = g["correct"].mean()
    se = np.sqrt(acc * (1 - acc) / max(n, 1))
    print(f"{str(band):>14s}{n:>7d}{acc:>7.3f}"
          f"   [{acc - 1.96 * se:.3f}, {acc + 1.96 * se:.3f}]{n / len(d) * 100:>6.1f}%")

fast = d[d["rt_ms"] <= 400]
print(f"\nRT<=400 ms：n={len(fast)}（{len(fast) / len(d) * 100:.1f}%），"
      f"acc={fast['correct'].mean():.3f}")
slow = d[d["rt_ms"] > 400]
print(f"RT>400 ms：n={len(slow)}（{len(slow) / len(d) * 100:.1f}%），"
      f"acc={slow['correct'].mean():.3f}")
for key in ("is_self", "P"):
    if key in d.columns:
        t = d.assign(grp=(d["rt_ms"] <= 400)).pivot_table(
            index=key, columns="grp", values="correct", aggfunc="mean")
        print(f"\n正确率（按 {key}，列 False=慢 True=快）：")
        print(t.round(3))
