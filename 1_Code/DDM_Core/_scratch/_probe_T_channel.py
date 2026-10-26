"""T 通道诊断（二）：把漂移网格下探到实测正确率带（0.65–0.77），量「acc→RT」的斜率。"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))

from mapping import MappingParams          # noqa: E402
import twophase as TP                      # noqa: E402

N = 6000


def run(d_ref, a_ref=1.9, t0=0.22, seed=20261026):
    rng = np.random.default_rng(seed)
    p = MappingParams(shape_model="lin", d_ref=d_ref, a_ref=a_ref, t0=t0,
                      z_ratio=0.5, beta_S=0.16, beta_SP=0.06, beta_ST=0.05)
    design = {"P": np.full(N, 30.0), "T": np.full(N, 0.10),
              "W": np.full(N, 1.20), "is_self": np.zeros(N, bool),
              "is_match": np.zeros(N, bool)}
    s = TP.simulate_step_subject(design, p, 1.0, rng)
    om = s["omission"] == 1
    rt = np.asarray(s["rt"])[~om]
    side = np.asarray(s["side"])[~om]
    return float(np.mean(side == 0)), float(np.median(rt)) * 1000.0, float(om.mean())


print(f"{'d_ref':>6s}{'acc':>8s}{'RT中位(ms)':>12s}{'漏答':>7s}")
rows = []
for d in (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50):
    a, r, o = run(d)
    rows.append((d, a, r, o))
    print(f"{d:>6.1f}{a:>8.3f}{r:>12.0f}{o:>7.3f}")

# 在 0.654–0.770 内线性插值出两点，再算斜率
xs = [r[1] for r in rows]
if max(xs) > 0.77 and min(xs) < 0.65:
    def at(target):
        for i in range(len(rows) - 1):
            a0, a1 = rows[i][1], rows[i + 1][1]
            if a0 <= target <= a1:
                w = (target - a0) / (a1 - a0)
                return (rows[i][0] + w * (rows[i + 1][0] - rows[i][0]),
                        rows[i][2] + w * (rows[i + 1][2] - rows[i][2]))
        return None
    lo, hi = at(0.654), at(0.770)
    print(f"\nacc 0.654 ⇒ d_ref≈{lo[0]:.2f}, RT≈{lo[1]:.0f} ms")
    print(f"acc 0.770 ⇒ d_ref≈{hi[0]:.2f}, RT≈{hi[1]:.0f} ms")
    print(f"只调漂移：Δacc=+0.116 时 DDM 给出 ΔRT={hi[1] - lo[1]:+.0f} ms；实测 ΔRT=+12 ms。")
    print(f"⇒ 缺口 {abs(hi[1] - lo[1]) - 12:.0f} ms 需第二条通道（边界 a 上升 / t0 上升）抵消。")
else:
    print(f"\nacc 覆盖区间 [{min(xs):.3f}, {max(xs):.3f}]，不足以夹住 0.654–0.770。")
