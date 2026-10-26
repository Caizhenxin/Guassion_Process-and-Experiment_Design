"""修正版 RT 分带正确率：只统计 **17 名在册被试、stage8 实际保留** 的响应试次。

原 `_probe_bimodal.py` 用 `trial_clean.csv` 全表（8,355 正式响应行）⇒ 混入
① 未进入分析的另外 3 名被试、② 抢按/刺激期内按键（stage8 明确剔除）。
两者把「≤400 ms 快带」从 4.9% 夸大到 11.1%，并让它的正确率看起来贴近机会。
本脚本用 `stage8_run.collect` 的保留试次重算，correct = (side == is_match)。
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))
import stage8_run as S            # noqa: E402
from mapping import MappingParams  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))

rt, corr, is_self = [], [], []
for p in people:
    tr = p["tr"]
    om = tr["omission"] == 0
    side = np.asarray(tr["side"])[om]
    match = np.asarray(tr["is_match"])[om]
    rt.append(np.asarray(tr["rt"])[om])
    corr.append((side == 1) == (match == 1))
    is_self.append(np.asarray(tr["is_self"])[om])
rt = np.concatenate(rt)
corr = np.concatenate(corr)
is_self = np.concatenate(is_self)
print(f"在册 {len(people)} 人、保留响应试次 {rt.size}、总体 acc {corr.mean():.3f}")
print(f"RT 中位 {np.median(rt) * 1000:.0f} ms、p10 {np.percentile(rt, 10) * 1000:.0f}、"
      f"p90 {np.percentile(rt, 90) * 1000:.0f}")

edges = [0.0, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.8, 10.0]
print(f"\n{'RT 带(ms)':>12s}{'n':>7s}{'acc':>7s}{'95%CI':>18s}{'占比':>7s}")
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (rt >= lo) & (rt < hi)
    n = int(m.sum())
    if n == 0:
        continue
    a = corr[m].mean()
    se = np.sqrt(a * (1 - a) / n)
    print(f"{f'{lo*1000:.0f}–{hi*1000:.0f}':>12s}{n:>7d}{a:>7.3f}"
          f"   [{a - 1.96 * se:.3f}, {a + 1.96 * se:.3f}]{n / rt.size * 100:>6.1f}%")

fast = rt <= 0.40
print(f"\n≤400 ms：n={int(fast.sum())}（{fast.mean() * 100:.1f}%）"
      f"acc={corr[fast].mean():.3f}  |  >400 ms：n={int((~fast).sum())}"
      f"（{(~fast).mean() * 100:.1f}%）acc={corr[~fast].mean():.3f}")
for tag, m in (("自我", is_self == 1), ("他人", is_self == 0)):
    print(f"  {tag}：≤400 ms acc={corr[fast & m].mean():.3f}"
          f"（n={int((fast & m).sum())}）、>400 ms acc={corr[(~fast) & m].mean():.3f}")

per = sorted(((int(p["group"]), int(p["subject"]),
               float(np.mean(np.asarray(p["tr"]["rt"])[np.asarray(p["tr"]["omission"]) == 0] <= 0.40)))
              for p in people), key=lambda r: -r[2])
print("\n快带占比最高的 5 人：")
for g, s, f in per[:5]:
    print(f"  {g}-{s}: {f * 100:.1f}%")
