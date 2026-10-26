# -*- coding: utf-8 -*-
"""新模型「效应量可以开多大」的轻量扫描（96 试次、n_grid=1200，只为看趋势）。

只回答一件事：在 T=100 ms（beta_ST 项为 0）下，beta_S / dz_S 各取多大，
ΔRT 与 Δacc 会长成什么数；与实测（ΔRT −33 ms、Δacc +0.067）对照。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core")]

import twophase as TP                  # noqa: E402
from mapping import MappingParams      # noqa: E402

N = 192          # 每个 P 档 48 试次
NG = 1200


def design(seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    P = np.tile(np.array([0.0, 8.0, 32.0, 120.0]), N // 4)
    return {"P": P, "T": np.full(N, 0.100), "W": np.full(N, 0.800),
            "is_self": rng.integers(0, 2, N).astype(float),
            "is_match": rng.integers(0, 2, N).astype(float)}


def run(p: MappingParams, d: dict, seed: int = 11):
    out = TP.simulate_step_subject(d, p, 0.8, np.random.default_rng(seed), n_grid=NG)
    rt = np.asarray(out["rt"], float)
    good = (np.asarray(out["omission"]) == 1) == False
    good &= np.isfinite(rt)
    side = np.asarray(out["side"])
    match = np.asarray(d["is_match"])
    sm_all = np.asarray(d["is_self"]) == 1
    corr = (side[good] == 1) == (match[good] == 1)
    sm = sm_all[good]
    return ((np.median(rt[good & sm_all]) - np.median(rt[good & ~sm_all])) * 1000,
            corr[sm].mean() - corr[~sm].mean(),
            float(np.mean(~good)), float(np.median(rt[good]) * 1000))


d = design()
print("beta_S  ΔRT(ms)  Δacc     漏答   RT中位")
t0 = time.time()
for b in (0.0, 0.15, 0.30, 0.60, 1.00):
    drt, dacc, om, med = run(MappingParams(shape_model="lin", beta_S=float(b)), d)
    print(f"{b:5.2f}  {drt:+8.0f}  {dacc:+.3f}  {om:5.1%}  {med:6.0f}   [{time.time()-t0:.0f}s]")

print("\ndz_S    ΔRT(ms)  Δacc     漏答   RT中位")
for z in (0.0, 0.05, 0.10, 0.25):
    drt, dacc, om, med = run(MappingParams(shape_model="lin", beta_S=0.0, dz_S=float(z)), d)
    print(f"{z:5.2f}  {drt:+8.0f}  {dacc:+.3f}  {om:5.1%}  {med:6.0f}   [{time.time()-t0:.0f}s]")

print("\n实测：ΔRT 中位 −33 ms、Δacc +0.067、漏答 27%、RT 中位 692 ms")
