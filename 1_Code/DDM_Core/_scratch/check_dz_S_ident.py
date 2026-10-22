# -*- coding: utf-8 -*-
"""check_dz_S_ident.py —— Δz_S 的识别性、与 β_S 的区分度、以及它对应多少 Δd′/Δc
================================================================================
回答三个问题（2026-10-22，D 新增 Δz_S 之后）：

A. **量级对齐**：给定 DDM 参数，模型隐含的 SDT 统计量是多少？扫 (β_S, dz_S)
   网格，找出能复现实测 ``Δd′ = +0.410``、``Δc = −0.239``（自我 − 他人）的组合。
   这样"要把 Δc 写成 Δz_S 的依据"就有了一张可查的表，而不是一句口头判断。

B. **识别性**：在 D4 设计（4T×3W×2自我×2匹配×12 = 576 试次）上，用 OPG 信息
   矩阵给出 ``dz_S`` 的期望 SE，以及 ``dz_S`` 与 ``β_S`` 的相关系数。若两者相关
   接近 ±1，则"多了一个参数却分不开两条通道"，Δz_S 就没有意义。

C. **恢复**：8 名被试、真值 ``β_S = 0.16 / dz_S = 0.12``，逐被试 MLE 后看
   ``dz_S``、``β_S`` 是否各自回到真值，以及两者误差是否互补（此消彼长 = 混叠）。

⚠️ 口径说明：这里用 ``p_upper``（无穷期限的渐近 P(上界)）算 SDT 统计量，而实测
H/FA 是在**期限内**的响应率（有遗漏）。遗忘会同时压低 H 与 FA，对 ``Δc`` 的影响
一阶相消、对 ``Δd′`` 是整体缩放，因此用于**量级与符号**判断足够，不用于逐位对齐。

运行：``python -X utf8 1_Code/DDM_Core/_scratch/check_dz_S_ident.py``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import ndtri

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))

import mapping as M  # noqa: E402
from likelihood import (fit_mle, fim_diagnostics, log_likelihood,  # noqa: E402
                        opg_information)
from simulate import (SUBJECT_SD, build_design, design_arrays,  # noqa: E402
                      draw_subject_params, simulate_subject)
from wfpt import p_upper  # noqa: E402

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
T_REF, W_REF = 0.10, 1.20
P_SINGLE = 120.0                 # 单被试：P 固定 ⇒ P 通路参数不参与（dfp≡0）

#: 被试层真值（lin 形状；``beta_S``/``dz_S`` 见下方 A 部分的对齐结果）
TRUTH = M.MappingParams(
    P_ref=P_SINGLE, T_ref=T_REF, W_ref=W_REF, shape_model="lin",
    d_ref=0.70, beta_P=0.31, tau_P=30.0,
    beta_T=1.10, beta_S=0.16, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.24, t0=0.22, z_ratio=0.50,
    dz_S=0.12,
)

#: 初始化（故意离真值有距离，模拟真实拟合的起点）
INIT = M.MappingParams(
    P_ref=P_SINGLE, T_ref=T_REF, W_ref=W_REF, shape_model="lin",
    d_ref=0.50, beta_P=0.31, tau_P=30.0,
    beta_T=1.60, beta_S=0.30, beta_ST=0.00,
    w_model="W1", a_ref=1.70, delta_a=0.10, t0=0.25, z_ratio=0.50,
    dz_S=0.00,
)
NAMES = list(M.WITHIN_FREE_LIN)


def sdt(p: M.MappingParams, T: float = T_REF, W: float = W_REF):
    """模型隐含的 SDT 统计量（自我 / 他人各自的 H、FA、d′、c）。"""
    a = float(M.boundary_a([W], p)[0])
    out = {}
    for tag, is_self in (("other", 0.0), ("self", 1.0)):
        one = {"P": np.array([P_SINGLE]), "T": np.array([T]),
               "W": np.array([W]), "is_self": np.array([is_self])}
        d = float(M.trial_params({**one, "is_match": np.array([1])}, p)["d"][0])
        z = float(M.trial_params({**one, "is_match": np.array([1])}, p)["z"][0])
        # H：is_match=1 ⇒ 上界正确 ⇒ v = +d；FA：is_match=0 ⇒ 上界错误 ⇒ v = −d
        H = float(p_upper(d, a, z))
        FA = float(p_upper(-d, a, z))
        zh, zf = ndtri(H), ndtri(FA)
        out[tag] = {"H": H, "FA": FA, "dprime": zh - zf, "c": -0.5 * (zh + zf),
                    "z": z, "a": a, "d": d}
    out["dd"] = out["self"]["dprime"] - out["other"]["dprime"]
    out["dc"] = out["self"]["c"] - out["other"]["c"]
    return out


print("=" * 86)
print("A. 模型隐含的 SDT 量：(β_S, dz_S) 网格 → 自我−他人的 Δd′ / Δc")
print(f"   参考条件 P={P_SINGLE:.0f}, T={T_REF}, W={W_REF}；真值 d_ref={TRUTH.d_ref}, "
      f"a_ref={TRUTH.a_ref}")
print("=" * 86)
base = sdt(TRUTH.replace(beta_S=0.0, beta_ST=0.0, dz_S=0.0))
print(f"   基线（两条身份通道都关）：H={base['other']['H']:.3f} FA={base['other']['FA']:.3f} "
      f"d′={base['other']['dprime']:.3f} c={base['other']['c']:+.3f}")
print(f"\n   {'β_S':>6s} {'dz_S':>6s} {'H_self':>7s} {'FA_self':>8s} "
      f"{'Δd′':>7s} {'Δc':>8s}   备注")
TARGET = (0.410, -0.239)
best = None
for bS in (0.0, 0.10, 0.16, 0.25, 0.35, 0.50):
    for dz in (0.0, 0.06, 0.12, 0.18, 0.24):
        s = sdt(TRUTH.replace(beta_S=bS, beta_ST=0.0, dz_S=dz))
        err = ((s["dd"] - TARGET[0]) / 0.10) ** 2 + ((s["dc"] - TARGET[1]) / 0.05) ** 2
        note = ""
        if best is None or err < best[0]:
            best = (err, bS, dz)
        print(f"   {bS:6.2f} {dz:6.2f} {s['self']['H']:7.3f} {s['self']['FA']:8.3f} "
              f"{s['dd']:+7.3f} {s['dc']:+8.3f}")
print(f"\n   实测目标：Δd′ = {TARGET[0]:+.3f}，Δc = {TARGET[1]:+.3f}"
      f"（`生成模型编码约定审查_20260930.md:81-83`）")
print(f"   粗网格最近点：β_S = {best[1]:.2f}, dz_S = {best[2]:.2f}")

# 细网格：找出能同时对上 (Δd′, Δc) 的 (β_S, dz_S)
fine = None
for bS in np.arange(0.10, 0.30, 0.005):
    for dz in np.arange(0.02, 0.16, 0.005):
        s = sdt(TRUTH.replace(beta_S=float(bS), beta_ST=0.0, dz_S=float(dz)))
        err = ((s["dd"] - TARGET[0]) / 0.05) ** 2 + ((s["dc"] - TARGET[1]) / 0.02) ** 2
        if fine is None or err < fine[0]:
            fine = (err, float(bS), float(dz), s["dd"], s["dc"])
print(f"   细网格最优：β_S = {fine[1]:.3f}, dz_S = {fine[2]:.3f}"
      f" → Δd′ = {fine[3]:+.3f}, Δc = {fine[4]:+.3f}")
print(f"   ⇒ 若实测 (Δd′, Δc) = (+0.410, −0.239) 完全由 (β_S, dz_S) 两条通道解释，"
      f"真值约为 β_S ≈ {fine[1]:.2f}、dz_S ≈ {fine[2]:.2f}。")

# ----------------------------------------------------------------------
print("\n" + "=" * 86)
print("B. 识别性：D4 设计（576 试次）上的 OPG 期望信息")
print("=" * 86)
design = build_design(P_SINGLE, T_LEVELS, W_LEVELS, N_REP)
sim = simulate_subject(design, TRUTH, np.random.default_rng(11))
tr = {**design, **{k: sim[k] for k in ("rt", "side", "omission")}}
_ok = tr["omission"] == 0
print(f"   设计：{len(tr['rt'])} 试次，遗漏率 {tr['omission'].mean():.3f}，"
      f"正确率 {np.mean(tr['side'][_ok] == tr['is_match'][_ok]):.3f}"
      f"（正确侧 = is_match：1 → 上界）")
t0 = time.time()
I, _ = opg_information(tr, NAMES, TRUTH)
diag = fim_diagnostics(I, NAMES)
cov = np.linalg.inv(I)
se = np.sqrt(np.diag(cov))
print(f"   cond(I) = {diag['cond']:.3g}，n_bad = {diag['n_bad']}（0 = 全部方向可识别）"
      f"  耗时 {time.time()-t0:.1f}s")
print(f"\n   {'参数':>10s} {'真值':>8s} {'期望SE':>8s} {'相对SE':>8s}")
for n, v, s in zip(NAMES, TRUTH.vector(NAMES), se):
    print(f"   {n:>10s} {v:8.3f} {s:8.4f} {s/abs(v) if v else np.nan:8.1%}")
corr = cov / np.outer(se, se)
i, j = NAMES.index("beta_S"), NAMES.index("dz_S")
print(f"\n   corr(β_S, dz_S) = {corr[i, j]:+.3f}   "
      f"（|r| 越接近 1 越说明两条通道混叠；<0.8 视为可分开）")
row = np.argsort(-np.abs(corr[j]))
print("   dz_S 的强相关伙伴（|r| > 0.5）：")
for k in row:
    if k != j and abs(corr[j, k]) > 0.5:
        print(f"     {NAMES[k]:>10s}  r = {corr[j, k]:+.3f}")

# ----------------------------------------------------------------------
print("\n" + "=" * 86)
print("C. 恢复：8 名被试逐被试 MLE（lin，8 个自由参数）")
print("=" * 86)
N_SUBJ = 8
rows = []
t0 = time.time()
for s in range(N_SUBJ):
    rng = np.random.default_rng(1000 + s)
    p_sub = draw_subject_params(TRUTH, rng, mode="clip")
    sim_s = simulate_subject(design, p_sub, rng)
    tr_s = {**design, **{k: sim_s[k] for k in ("rt", "side", "omission")}}
    ov = {"t0": (M.PARAM_BOUNDS["t0"][0], float(np.nanmin(tr_s["rt"])) - 1e-3)}
    fit = fit_mle(tr_s, NAMES, INIT, n_restart=4, seed=s, bounds_override=ov,
                  gtol=1e-10, ftol=1e-14)
    if not np.isfinite(fit["loglik"]):
        print(f"   被试 {s}: 拟合失败，跳过")
        continue
    got = fit["params"].vector(NAMES)
    rows.append({"truth": p_sub.vector(NAMES), "est": got,
                 "ll": fit["loglik"], "tr": p_sub})
    d = got[NAMES.index("dz_S")] - p_sub.dz_S
    b = got[NAMES.index("beta_S")] - p_sub.beta_S
    print(f"   被试 {s}: logL={fit['loglik']:9.2f}  dz_S 真值={p_sub.dz_S:+.3f} "
          f"估计={got[NAMES.index('dz_S')]:+.3f} (误差 {d:+.3f})   "
          f"β_S 真值={p_sub.beta_S:+.3f} 估计={got[NAMES.index('beta_S')]:+.3f} "
          f"(误差 {b:+.3f})   起点数={fit['n_starts_ok']}")
print(f"   总耗时 {time.time()-t0:.0f}s")

if rows:
    T = np.array([r["truth"] for r in rows])
    E = np.array([r["est"] for r in rows])
    err = E - T
    for nm in ("beta_S", "dz_S", "d_ref", "beta_T", "a_ref", "delta_a", "t0", "beta_ST"):
        k = NAMES.index(nm)
        print(f"   {nm:>9s}: 平均误差 {err[:, k].mean():+.4f}  "
              f"SD {err[:, k].std(ddof=1):.4f}  相对 {abs(err[:, k].mean())/max(abs(T[:, k].mean()), 1e-9):5.1%}")
    kb, kz = NAMES.index("beta_S"), NAMES.index("dz_S")
    r_hat = np.corrcoef(E[:, kb], E[:, kz])[0, 1]
    r_err = np.corrcoef(err[:, kb], err[:, kz])[0, 1]
    print(f"\n   估计间相关 corr(β̂_S, dẑ_S) = {r_hat:+.3f}；误差间相关 = {r_err:+.3f}")
    print("   （误差间相关若 < −0.5：一个高估必然伴随另一个低估 ⇒ 混叠；"
          "接近 0 ⇒ 两条通道各自独立估计成功）")
    # 用拟合值反算 SDT，看 Δc 是否也回来了
    dd_est, dc_est, dd_tru, dc_tru = [], [], [], []
    for r in rows:
        se_, st_ = sdt(r["tr"].replace(**dict(zip(NAMES, r["est"])))), sdt(r["tr"])
        dd_est.append(se_["dd"]); dc_est.append(se_["dc"])
        dd_tru.append(st_["dd"]); dc_tru.append(st_["dc"])
    print(f"   模型隐含 Δd′：真值 {np.mean(dd_tru):+.3f} → 拟合 {np.mean(dd_est):+.3f}")
    print(f"   模型隐含 Δc ：真值 {np.mean(dc_tru):+.3f} → 拟合 {np.mean(dc_est):+.3f}")
    print(f"   （群体均值：dz_S 真值均值 {T[:, kz].mean():+.3f} ± "
          f"{T[:, kz].std(ddof=1):.3f}，估计均值 {E[:, kz].mean():+.3f} ± "
          f"{E[:, kz].std(ddof=1):.3f}）")

print("\n" + "=" * 86)
print("结论要点")
print("=" * 86)
print("1. A 表给出 β_S 与 dz_S 的联合映射：Δd′ 主要由 β_S 控制，Δc 主要由 dz_S 控制；")
print("   细网格给出能复现实测 (Δd′, Δc) 的 (β_S, dz_S)。")
print("2. B 的 corr(β_S, dz_S) 与 C 的误差相关共同回答『两条通道能不能分开』。")
print("3. 判定阈值：|corr| < 0.8 且相对 SE < 30% ⇒ 该设计足以分别估计两条通道。")

