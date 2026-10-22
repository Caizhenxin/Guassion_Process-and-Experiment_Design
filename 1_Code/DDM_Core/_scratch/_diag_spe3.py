"""决定性检验：同一 (a, z, t0)，只把漂移从 0.76 提到 1.08，RT 差到底该多大？

同时对比两种实现：解析平均 DT 与 Euler 模拟。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import twophase  # noqa: E402
from mapping import MappingParams  # noqa: E402

A = 1.566
T0 = 0.19
N = 3000


def run(v: float, seed: int) -> dict:
    """直接给定漂移的 Euler 模拟（绕过映射方程）。"""
    rng = np.random.default_rng(seed)
    dt = 5e-5
    T = 0.15
    W = 1.8
    t = np.arange(0.0, W + dt, dt)
    # 两阶段：t<=T 用 v，之后用 rho*v（与 M-T1 一致，rho=0.8）
    step = np.where(t <= T, v, 0.8 * v)
    rts, sides, omit = [], [], []
    for _ in range(N):
        x = 0.5 * A
        rt = np.nan
        side = 0
        noise = rng.normal(0.0, 1.0, t.size) * np.sqrt(dt)
        xs = x + np.cumsum(step * dt + noise)
        hit = np.nonzero((xs >= A) | (xs <= 0.0))[0]
        if hit.size:
            rt = t[hit[0]] + T0
            side = 1 if xs[hit[0]] >= A else -1
        rts.append(rt)
        sides.append(side)
    rt_arr = np.array(rts, float)
    om = ~np.isfinite(rt_arr)
    return {"rt": rt_arr[~om], "omission": float(om.mean())}


def mean_dt(v, a=A):
    return (a / (2 * v)) * np.tanh(a * v / 2.0)


for v in (0.76, 1.08):
    r = run(v, 11)
    print(f"v={v:.2f}  解析 DT {mean_dt(v)*1000:6.0f} ms | Euler 中位 "
          f"{np.median(r['rt'])*1000:6.0f} ms  均值 {r['rt'].mean()*1000:6.0f} ms  "
          f"遗漏 {r['omission']:.3f}  n={r['rt'].size}")

r1, r2 = run(0.76, 11), run(1.08, 11)
print(f"\nΔRT（他人−自我）：中位 {1000*(np.median(r1['rt'])-np.median(r2['rt'])):+.0f} ms；"
      f"均值 {1000*(r1['rt'].mean()-r2['rt'].mean()):+.0f} ms")
print(f"解析预期 ΔDT = {1000*(mean_dt(0.76)-mean_dt(1.08)):+.0f} ms")
