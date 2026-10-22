# -*- coding: utf-8 -*-
"""check_dz_S_power.py —— 「SPE 能否显著区分 Self 与 Other」的直接回答
================================================================================
用户问题（2026-10-22）：「加入 Δz_S 之后，看一下 SPE 是否能显著区别 Self 和 Other」。

做法：**似然比检验（LRT）**，不是看误差大小。对每名被试拟合四个模型（同一份数据）：

    模型 A  自由 = 8 个（含 `beta_S` 与 `dz_S`）        ← 完整模型
    模型 B  自由 = 7 个（`dz_S` 固定为 0）              ← 去掉判据通道
    模型 C  自由 = 7 个（`beta_S` 固定为 0）            ← 去掉漂移通道
    模型 D  自由 = 6 个（两条身份通道都固定为 0）        ← 无 SPE 的零模型

于是有三个检验（嵌套，均用 χ²）：

    (i)  联合：`2(ll_A − ll_D)` ~ χ²(2)     → 「有没有 SPE（任一通道）」
    (ii) 漂移：`2(ll_A − ll_C)` ~ χ²(1)     → `β_S` 是否显著（`dz_S` 在 A、C 中都自由）
    (iii)判据：`2(ll_A − ll_B)` ~ χ²(1)     → `dz_S` 是否显著（`β_S` 在 A、B 中都自由）

⚠️ **易错点（第一版写反了，已改）**：`A − B` 检验的是被 B 固定住的那个参数，即
`dz_S`；`A − C` 检验的是 `β_S`。写反会把「某通道重要」误读成「另一通道重要」。

⚠️ **另一个易错点（第一版踩过）**：`draw_subject_params` 会按 `SUBJECT_SD` 给**每名
被试**加随机偏移，`truth` 只决定**群体均值**。因此"真值 dz_S = 0"的组里，个体仍可能
拿到 dz_S ≈ ±0.06，于是"假阳性检查"根本不干净。凡是要某通道严格为零，必须把该通道的
个体 SD 也置 0（`sd={**SUBJECT_SD, "dz_S": 0.0}`，`s <= 0` 的键会被跳过）。

组层：被试间独立 ⇒ `Σ_i LR_i ~ χ²(Σ df)`。这是**固定效应**的组层检验（与
`stage8` 的层级模型给出的 `mu` 后验区间是两套口径，但结论方向应当一致）。

三个场景（各 10 名被试）：

    S1 双通道   `beta_S = 0.19, dz_S = 0.085`   ← 能复现实测 (Δd′, Δc) = (+0.41, −0.24)
    S2 纯漂移   `beta_S = 0.19, dz_S = 0`（个体 SD 也置 0） ← 判据检验不应显著
    S3 纯判据   `beta_S = 0,    dz_S = 0.085`（个体 SD 也置 0） ← 漂移检验不应显著

⚠️ 陷阱记录：`dz_S` 固定为 0 的做法是**把它从 `free_names` 里去掉**，同时把
`p_init.dz_S` 置 0；不能靠 `bounds_override` 把上下界压成一点（x→θ 的变换会退化）。

运行：``python -X utf8 1_Code/DDM_Core/_scratch/check_dz_S_power.py``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import chi2

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))

import mapping as M  # noqa: E402
from likelihood import fit_mle  # noqa: E402
from simulate import (SUBJECT_SD, build_design, draw_subject_params,  # noqa: E402
                      simulate_subject)

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
P_SINGLE, T_REF, W_REF = 120.0, 0.10, 1.20
N_SUBJ = 10

FULL = ["d_ref", "beta_T", "beta_S", "beta_ST", "a_ref", "delta_a", "t0", "dz_S"]
NO_Z = [n for n in FULL if n != "dz_S"]          # dz_S = 0
NO_S = [n for n in FULL if n != "beta_S"]        # beta_S = 0
NEITHER = [n for n in NO_Z if n != "beta_S"]     # 两条都 = 0

SD_BOTH = dict(SUBJECT_SD)                                  # 两条通道都有个体差异
SD_NO_Z = {**SUBJECT_SD, "dz_S": 0.0}                       # 判据通道严格为零
SD_NO_S = {**SUBJECT_SD, "beta_S": 0.0}                     # 漂移通道严格为零

BASE = dict(P_ref=P_SINGLE, T_ref=T_REF, W_ref=W_REF, shape_model="lin",
            d_ref=0.70, beta_P=0.31, tau_P=30.0, beta_T=1.10, beta_ST=0.10,
            w_model="W1", a_ref=2.00, delta_a=0.24, t0=0.22, z_ratio=0.50)


def make(beta_S: float, dz_S: float) -> M.MappingParams:
    return M.MappingParams(**BASE, beta_S=beta_S, dz_S=dz_S)


INIT = M.MappingParams(**BASE, beta_S=0.0, dz_S=0.0).replace(
    d_ref=0.50, beta_T=1.60, a_ref=1.70, delta_a=0.10, t0=0.25)

SCENARIOS = [("S1 双通道", 0.19, 0.085, SD_BOTH),
             ("S2 纯漂移", 0.19, 0.000, SD_NO_Z),
             ("S3 纯判据", 0.00, 0.085, SD_NO_S)]

design = build_design(P_SINGLE, T_LEVELS, W_LEVELS, N_REP)
print("=" * 92)
print(f"LRT：「SPE 能否显著区分 Self 与 Other」  设计 D4：{len(design['T'])} 试次/人，"
      f"每组 {N_SUBJ} 人")
print("=" * 92)

all_rows: dict[str, list] = {}
t_all = time.time()
for name, bs, dz, sd in SCENARIOS:
    print("\n" + "-" * 92)
    print(f"{name}：群体真值 beta_S = {bs:.3f}, dz_S = {dz:.3f}；"
          f"个体 SD beta_S = {sd['beta_S']:.3f}, dz_S = {sd['dz_S']:.3f}")
    print(f"  {'被试':>4s} {'ll_A':>9s} {'ll_B':>9s} {'ll_C':>9s} {'ll_D':>9s} "
          f"{'LR_joint':>9s} {'LR_betaS':>9s} {'LR_dzS':>9s}")
    truth = make(bs, dz)
    rows = []
    t0_ = time.time()
    for s in range(N_SUBJ):
        rng = np.random.default_rng(7000 + 137 * s)   # 场景间共用噪声流 ⇒ 可比
        p_sub = draw_subject_params(truth, rng, sd=sd, mode="clip")
        sim = simulate_subject(design, p_sub, rng)
        tr = {**design, **{k: sim[k] for k in ("rt", "side", "omission")}}
        ov = {"t0": (M.PARAM_BOUNDS["t0"][0], float(np.nanmin(tr["rt"])) - 1e-3)}
        kw = dict(n_restart=3, seed=s, bounds_override=ov, gtol=1e-10, ftol=1e-14)
        ll = {}
        for tag, names, init in (("A", FULL, INIT),
                                 ("B", NO_Z, INIT.replace(dz_S=0.0)),
                                 ("C", NO_S, INIT.replace(beta_S=0.0)),
                                 ("D", NEITHER, INIT.replace(beta_S=0.0, dz_S=0.0))):
            f = fit_mle(tr, names, init, **kw)
            ll[tag] = f["loglik"]
        lr_j = 2.0 * (ll["A"] - ll["D"])
        lr_b = 2.0 * (ll["A"] - ll["C"])
        lr_z = 2.0 * (ll["A"] - ll["B"])
        rows.append((lr_j, lr_b, lr_z))
        print(f"  {s:4d} {ll['A']:9.2f} {ll['B']:9.2f} {ll['C']:9.2f} {ll['D']:9.2f} "
              f"{lr_j:9.2f} {lr_b:9.2f} {lr_z:9.2f}")
    all_rows[name] = rows
    R = np.clip(np.array(rows), 0.0, None)           # 数值噪声可能给出 −0.00x
    print(f"  耗时 {time.time()-t0_:.0f}s")
    print(f"  {'':>12s} {'逐被试拒绝率(α=.05)':>20s} {'组层 ΣLR':>10s} {'组层 p':>9s} {'f²≈':>8s}")
    for tag, col, df_, label in (("joint", 0, 2, "联合 Δχ²(2)"),
                                 ("betaS", 1, 1, "漂移 β_S"),
                                 ("dzS", 2, 1, "判据 dz_S")):
        rej = np.mean(R[:, col] > chi2.ppf(0.95, df_))
        sumlr = float(R[:, col].sum())
        p = chi2.sf(sumlr, df_ * N_SUBJ)
        f2 = max(0.0, (sumlr - df_ * N_SUBJ) / N_SUBJ)
        print(f"  {label:>12s} {rej:20.0%} {sumlr:10.2f} {p:9.2e} {f2:8.3f}")

print("\n" + "=" * 92)
print("读法")
print("=" * 92)
print("1. S1：联合检验应高，且 `β_S` 与 `dz_S` **各自**有可能显著 ⇒ 「双通道 SPE」可判。")
print("   注意两条通道的**检验力不同**：`dz_S`（SE 0.015）远好于 `β_S`（SE 0.12），")
print("   所以 S1 里更常见的读法是「判据显著 + 漂移方向一致但区间宽」。")
print("2. S2/S3 是**假阳性检查**：对应检验的拒绝率应 ≈ 5%（个体），组层 p 应 > .05。")
print("3. 组层 p 按 ΣLR ~ χ²(Σdf) 计算（固定效应）；真实数据以 stage8 的层级后验区间为准。")
print(f"\n总耗时 {time.time()-t_all:.0f}s")
