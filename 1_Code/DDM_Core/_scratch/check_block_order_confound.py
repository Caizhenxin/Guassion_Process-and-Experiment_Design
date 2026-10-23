# -*- coding: utf-8 -*-
"""check_block_order_confound.py —— 块序固定（W = 800→1200→1800）能造成多大偏差
================================================================================
问题（用户 2026-10-23）：正式程序的 3 个 block 固定按 W 升序（`Exp_Design_Formal.m:895-898`
`for b = 1:block; Wtrial = W_levels(b);`），所有被试同一顺序，**W 与块序完全共线**。
问：要不要把 W 的顺序在不同被试间平衡？

本脚本量化「不平衡的代价」，即：如果一个**与 W 无关**的会话内趋势（练习、疲劳、
策略漂移）存在，它会被误读成 `a(W)` 的多少？

做法：真值里 **`Δa ≡ 0`**（本来没有 W→a 效应），但让某个参数随 block 单调变化；
用**标准模型**（`a(W)` 线性）拟合，看拟合出的 `Δa = Δa_hat × (W_max − W_min)`
偏离 0 多少，以及这个趋势有没有顺带污染 `β_T / β_S / Δz_S / t0`。

场景（每块 192 试次、3 块 = 576 试次/人，与正式程序完全一致；CRN：同一随机流）：

    baseline        三块参数完全相同                     ← 应给 Δa ≈ 0（噪声底）
    drift +g/块     练习让漂移每块 +g（g = 0.05/0.10/0.15）
    t0   −q/块      疲劳/策略让非决策时间每块 −q（q = 5/10/20 ms）
    a    +h/块      「小心程度」随块上升（h = 0.05/0.10） ← 这就是混淆本身

读法：把「baseline 的 Δa」当作噪声带，比它大的偏离才算「趋势可被误读为 W 效应」；
再把量级和「真正的 `Δa` 能有多大」比（本项目 `a` 在 W∈[0.8,1.8] s 上只变 6.7%，
即 `a_ref≈1.9` 时真 `Δa` 跨度约 0.13）。

运行：``python -X utf8 1_Code/DDM_Core/_scratch/check_block_order_confound.py``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))

import mapping as M  # noqa: E402
from likelihood import fit_mle  # noqa: E402
from simulate import build_design, simulate_subject  # noqa: E402

T_LEVELS = [2 / 60, 5 / 60, 9 / 60, 15 / 60]          # 33.3 / 83.3 / 150 / 250 ms
W_LEVELS = [48 / 60, 72 / 60, 108 / 60]               # 799.98 / 1199.9 / 1799.9 ms
N_REP = 12
N_SUBJ = 3
NAMES = list(M.WITHIN_FREE_LIN)

BASE = dict(P_ref=30.0, T_ref=0.10, W_ref=1.20, shape_model="lin",
            d_ref=0.80, beta_P=0.35, tau_P=30.0,
            beta_T=0.95, beta_S=0.30, beta_ST=0.12,
            w_model="W1", a_ref=1.52, delta_a=0.0,      # ← 真值：没有 W→a 效应
            t0=0.19, z_ratio=0.50, dz_S=0.12)

INIT = M.MappingParams(**BASE).replace(
    d_ref=0.60, beta_T=1.40, a_ref=1.70, t0=0.23, dz_S=0.0)

W_SPAN = W_LEVELS[-1] - W_LEVELS[0]                   # 1.0 s


def block_design(wi: int) -> dict:
    """单个 block：固定一个 W，块内 4 个 T × 4 类刺激 × 12 次。"""
    return build_design(30.0, T_LEVELS, [W_LEVELS[wi]], N_REP)


def make_trials(trend: dict, rng) -> dict:
    """按 ``trend`` 给每个 block 一套参数，拼成 576 试次的观测。"""
    parts = []
    for wi in range(len(W_LEVELS)):
        p = M.MappingParams(**BASE)
        k = wi                                     # block 序号 0/1/2
        kw = {}
        if "drift_per_block" in trend:
            kw["d_ref"] = p.d_ref + trend["drift_per_block"] * k
        if "t0_per_block" in trend:
            kw["t0"] = p.t0 + trend["t0_per_block"] * k
        if "a_per_block" in trend:
            kw["a_ref"] = p.a_ref + trend["a_per_block"] * k
        p = p.replace(**kw) if kw else p
        d = block_design(wi)
        sim = simulate_subject(d, p, rng)
        parts.append({**d, **{k2: sim[k2] for k2 in ("rt", "side", "omission")}})
    return {k: np.concatenate([q[k] for q in parts]) for k in parts[0]}


SCENARIOS = [
    ("baseline（无趋势）", {}),
    ("drift +0.05/块", {"drift_per_block": 0.05}),
    ("drift +0.10/块", {"drift_per_block": 0.10}),
    ("drift +0.15/块", {"drift_per_block": 0.15}),
    ("t0 −5 ms/块", {"t0_per_block": -0.005}),
    ("t0 −10 ms/块", {"t0_per_block": -0.010}),
    ("t0 −20 ms/块", {"t0_per_block": -0.020}),
    ("a +0.05/块", {"a_per_block": 0.05}),
    ("a +0.10/块", {"a_per_block": 0.10}),
]
WATCH = ("d_ref", "beta_T", "beta_S", "a_ref", "delta_a", "t0", "dz_S")

print("=" * 104)
print(f"块序混淆量化：真值 Δa ≡ 0，3 block × 192 试次 = 576，{N_SUBJ} 名伪被试，CRN 同随机流")
print(f"W = {[round(w*1000,1) for w in W_LEVELS]} ms；固定升序 ⇒ W 与块序共线")
print("=" * 104)

rows = {}
t0_ = time.time()
for name, trend in SCENARIOS:
    est = []
    for s in range(N_SUBJ):
        rng = np.random.default_rng(9000 + 17 * s)      # 场景间共用流 ⇒ 可比
        tr = make_trials(trend, rng)
        ov = {"t0": (M.PARAM_BOUNDS["t0"][0], float(np.nanmin(tr["rt"])) - 1e-3)}
        fit = fit_mle(tr, NAMES, INIT, n_restart=3, seed=s,
                      bounds_override=ov, gtol=1e-10, ftol=1e-14)
        if not np.isfinite(fit["loglik"]):
            continue
        est.append(fit["params"].vector(NAMES))
    if not est:
        print(f"{name}: 全部拟合失败")
        continue
    E = np.array(est)
    rows[name] = E.mean(axis=0)
    acc = E[:, NAMES.index("delta_a")].mean() * W_SPAN
    print(f"\n{name}")
    print(f"  拟合 Δa 跨度（W 全距 1.0 s）= {acc:+.4f}"
          f"   （逐被试 {np.round(E[:, NAMES.index('delta_a')] * W_SPAN, 3)}）")
    print("  " + "  ".join(f"{nm}={rows[name][NAMES.index(nm)]:+.3f}" for nm in WATCH))

if "baseline（无趋势）" in rows:
    print("\n" + "=" * 104)
    print("读法表：把每个场景的 Δa 跨度与 baseline 比，看它是否已能与「真的 W 效应」区分")
    print("=" * 104)
    b = rows["baseline（无趋势）"][NAMES.index("delta_a")] * W_SPAN
    print(f"  {'场景':<20s} {'Δa 跨度':>10s} {'相对 baseline':>14s}")
    for name in rows:
        v = rows[name][NAMES.index("delta_a")] * W_SPAN
        print(f"  {name:<20s} {v:+10.4f} {v - b:+14.4f}")

print(f"\n总耗时 {time.time()-t0_:.0f}s")
