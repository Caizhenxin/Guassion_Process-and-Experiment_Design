# -*- coding: utf-8 -*-
"""精确量新模型真值下的 SPE：直接对每个设计格调 `sample_step` 抽 8000 个试次。

为什么另起一个：
  - `simulate_step_subject` 按被试整份模拟，288 试次就要 80 s，且 median 的 SE ~26 ms，
    分不清「真值 SPE 是 0 还是 −100 ms」；
  - 这里对**单个 (P,T,W) 格**一次性抽 8000 个样本，SE ~3 ms，且同格 self/other 用
    同一随机流，配对比较，噪声几乎抵消。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core")]

import design_grid as DG                  # noqa: E402
import twophase as TP                    # noqa: E402
from mapping import MappingParams        # noqa: E402

CELLS = [(p, t, w) for p in (0.0, 8.0, 32.0, 120.0)
         for t, w in ((0.100, 0.800), (0.150, 1.200), (0.250, 1.800))]
N = 8000


def cell_stats(p: MappingParams, P: float, T: float, W: float, n: int = N):
    out = {}
    for is_self in (1.0, 0.0):
        d = {"P": np.array([P]), "T": np.array([T]), "W": np.array([W]),
             "is_self": np.array([is_self]), "is_match": np.array([1.0])}
        tp = TP.trial_params(d, p)
        v, a, z = float(tp["v"][0]), float(tp["a"][0]), float(tp["z"][0])
        t0 = float(tp["t0"]) if np.ndim(tp["t0"]) == 0 else float(tp["t0"][0])
        tau, b = TP.sample_step(v, 0.8 * v, a, z, T, n,
                                np.random.default_rng(2026), n_grid=4000)
        rt = tau + t0
        ok = np.isfinite(rt) & (rt <= W)
        out[is_self] = dict(d=v, a=a, z=z, med=float(np.median(rt[ok])) * 1000,
                            acc=float(np.mean(b[ok] == 1)), om=float(1 - ok.mean()))
    return out


def sweep(label: str, p: MappingParams):
    rows = []
    for P, T, W in CELLS:
        r = cell_stats(p, P, T, W)
        rows.append((P, T, W, r[1.0]["d"], r[0.0]["d"],
                     r[1.0]["med"] - r[0.0]["med"], r[1.0]["acc"] - r[0.0]["acc"],
                     r[1.0]["om"], r[0.0]["om"]))
    arr = np.array(rows)
    print(f"\n=== {label} ===")
    print("  P     T(ms)  W(ms)  d(Self) d(Other)  ΔRT(ms)  Δacc    漏答(S/O)")
    for P, T, W, ds, do, drt, dacc, oms, omo in rows:
        print(f"  {P:5.1f}  {T*1000:5.0f}  {W*1000:5.0f}  {ds:6.3f}  {do:7.3f}  "
              f"{drt:+7.0f}  {dacc:+.3f}  {oms:4.1%}/{omo:4.1%}")
    print(f"  格均值：ΔRT {arr[:, 5].mean():+.0f} ms、Δacc {arr[:, 6].mean():+.3f}"
          f"（等权 12 格；实测对应 ΔRT −33 ms、Δacc +0.067）")


if __name__ == "__main__":
    sweep("TRUTH_LIN（当前真值：beta_S=0.148、beta_ST=0.345）", DG.TRUTH_LIN)
    for f in (2.0, 4.0, 8.0):
        p = MappingParams(**{**DG.TRUTH_LIN.__dict__, "beta_S": DG.TRUTH_LIN.beta_S * f})
        sweep(f"beta_S ×{f:g} = {DG.TRUTH_LIN.beta_S * f:.2f}", p)
