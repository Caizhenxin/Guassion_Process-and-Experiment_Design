# -*- coding: utf-8 -*-
"""
check_lin.py —— 「去掉时标」处方（D18/D19 处方 1）的直接检验
================================================================================
背景
----
Stage 4 已确认：带自由时标的 ``Q(X,τ) = 1 − exp(−X/τ)`` 在本设计上**不可识别** ——
``tau_a`` 在两个独立设计里都被推到上界（x_hat = 4.9998 ≈ 5.0，误差 +4.30），
``tau_T`` 自由估计时在 D4 给 0.0050、在 low6 给 0.1728（**方向相反**，纯噪声）。
且实测否证了「钉住 ``tau_T`` 即可解锁 ``beta_T``/``beta_ST``」这一处方（D19）。

本脚本检验**真正的处方**：把形状函数换成**无时标**的线性形式
``d = d_ref + β_T·(T − T_ref)``、``a = a_ref + δa·(W − W_ref)``（``shape_model="lin"``）。

两问
----
* **A. 这个限制有代价吗？** 用 **exp 真值**生成数据，分别用 exp 模型（9 自由）
  与 lin 模型（7 自由）拟合，比较对数似然/BIC，并对比二者推出的 ``d(T)``、``a(W)``
  剖面与 exp 真值的差距。若 Δll 很小 ⇒ 线性限制不损失现象。
* **B. 去掉时标后参数可识别了吗？** 用 **lin 真值**生成数据，对 7 个参数做
  条件曲率（SE）＋剖面 2 单位区间判决 ＋ 联合 MLE 偏差。若全部「含真值」且
  相对 SE 合理 ⇒ 处方成立，且这就是可以写进论文的参数化。

用法
----
    python check_lin.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from design_fim import P_SINGLE, TRUTH  # noqa: E402
from likelihood import (_bounds_for, fit_mle, log_likelihood,  # noqa: E402
                        profile_se, trials_from_arrays)
from mapping import (WITHIN_FREE, WITHIN_FREE_LIN, MappingParams,  # noqa: E402
                     boundary_a, drift_magnitude)
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

T_L = [0.0333, 0.0833, 0.14999, 0.24998]
W_L = [0.79998, 1.19990, 1.79990]
REP = 12
SEED = 7

#: 线性真值。选得使效应量明显但合理：d 在 T 轴上约 0.57–1.00，a 在 W 轴上约 1.88–2.18。
LIN_TRUTH = MappingParams(
    P_ref=P_SINGLE, T_ref=0.10, W_ref=1.20, shape_model="lin",
    d_ref=0.70, beta_P=0.35, tau_P=30.0,
    beta_T=2.00, tau_T=0.080,
    beta_S=0.16, beta_SP=0.0, beta_ST=0.30,
    w_model="W1", a_ref=2.00, delta_a=0.30, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)

#: 在 exp 数据上拟合 lin 模型时的起点：β_T/δa 用最小二乘匹配 exp 形态后的量级
LIN_INIT_ON_EXP = TRUTH.replace(shape_model="lin", beta_T=1.279, delta_a=0.226,
                                beta_ST=0.233)


# ----------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------
def make(truth, seed, t_levels=None, w_levels=None):
    design = build_design(P_SINGLE, t_levels or T_L, w_levels or W_L, REP)
    sim = simulate_subject(design, truth, np.random.default_rng(seed))
    trial = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *design_arrays(design))
    return trial, sim, design


def curv(tr, names, p, which, steps=(1e-2, 3e-3, 1e-3, 3e-4, 1e-4)):
    """参数单位下的条件二阶导 d²ll/dθ²（其余参数钉在 p）。返回 (值, 相对 SE)。"""
    lo, hi = _bounds_for(names)
    k = names.index(which)
    x0 = p.vector(names)
    out = []
    for rel in steps:
        h = max(rel * (hi[k] - lo[k]), 1e-7)
        xp, xm = x0.copy(), x0.copy()
        xp[k] += h
        xm[k] -= h
        lp, lm = log_likelihood(p.with_vector(names, xp), tr), log_likelihood(p.with_vector(names, xm), tr)
        if not np.isfinite(lp) or not np.isfinite(lm):
            continue
        c = (lp - 2.0 * log_likelihood(p, tr) + lm) / (h * h)
        out.append(c)
    if not out:
        return np.nan, np.nan
    c = out[-1]                        # 最小步长（已收敛的那个）
    se = 1.0 / np.sqrt(abs(c)) if c < 0 else np.inf
    return c, se


def verdict(r):
    if r["lo"] is None or r["hi"] is None:
        return "不可识别"
    return "含真值" if r["lo"] <= float(r["truth"]) <= r["hi"] else "有偏"


def bic(ll, k, n):
    return -2.0 * ll + k * np.log(n)


# ----------------------------------------------------------------------
def main():
    t_start = time.time()
    tr_exp, sim_exp, des_exp = make(TRUTH, SEED)
    tr_lin, sim_lin, des_lin = make(LIN_TRUTH, SEED)
    n = len(tr_exp["rt"])
    print("=" * 100)
    print("check_lin.py —— 无时标（lin）参数化检验")
    print("=" * 100)
    print(f"  设计 {len(T_L)}T × {len(W_L)}W × {REP}rep = {n} 试次；seed={SEED}；P={P_SINGLE}")
    print(f"  exp 真值：d_ref={TRUTH.d_ref}  beta_T={TRUTH.beta_T}  tau_T={TRUTH.tau_T}"
          f"  beta_ST={TRUTH.beta_ST}  a_ref={TRUTH.a_ref}  delta_a={TRUTH.delta_a}  tau_a={TRUTH.tau_a}")
    print(f"  lin 真值：d_ref={LIN_TRUTH.d_ref}  beta_T={LIN_TRUTH.beta_T}（drift/秒）"
          f"  beta_ST={LIN_TRUTH.beta_ST}  a_ref={LIN_TRUTH.a_ref}  delta_a={LIN_TRUTH.delta_a}（a/秒）")

    # --- 行为量级合理性 ---
    print("\n" + "-" * 100)
    print("【0】行为量级（两种真值生成的模拟数据）")
    print("-" * 100)
    for lab, sim, ts, des in (("exp 真值", sim_exp, TRUTH, des_exp),
                              ("lin 真值", sim_lin, LIN_TRUTH, des_lin)):
        # ⚠️ omission 是 int 数组，必须 `== 0` 取逻辑掩码；`~om` 是**按位取反**（0→−1），
        # 会把 `side[~om]` 变成 `side[[-1,-2,...]]`（只取末尾几个元素）→ 正确率虚高为 1.000。
        keep = sim["omission"] == 0
        is_match = design_arrays(des)[4]
        acc = float(np.mean(sim["side"][keep] == is_match[keep]))
        dd = drift_magnitude(P_SINGLE, np.array(T_L), 0, ts)
        aa = boundary_a(np.array(W_L), ts)
        print(f"  {lab}: 遗漏率 {sim['omission'].mean():.3f}  正确率 {acc:.3f}"
              f"  平均RT {sim['rt'][keep].mean()*1000:.0f} ms  |"
              f" d(T)={np.round(dd,3)}  a(W)={np.round(aa,3)}")

    # ==================================================================
    # A. 线性限制的代价（用 exp 数据拟合两个模型）
    # ==================================================================
    print("\n" + "=" * 100)
    print("【A】线性限制的代价：exp 数据，分别用 exp 模型(9 自由) 与 lin 模型(7 自由) 拟合")
    print("=" * 100)
    ll_truth = log_likelihood(TRUTH, tr_exp)
    fit_e = fit_mle(tr_exp, WITHIN_FREE, TRUTH, n_restart=12, seed=0,
                    gtol=1e-10, ftol=1e-14, maxfun=40000)
    fit_l = fit_mle(tr_exp, WITHIN_FREE_LIN, LIN_INIT_ON_EXP, n_restart=12, seed=0,
                    gtol=1e-10, ftol=1e-14, maxfun=40000)
    ll_e, ll_l = float(fit_e["loglik"]), float(fit_l["loglik"])
    print(f"  ll(exp 真值)      = {ll_truth:.4f}")
    print(f"  ll(exp MLE, k=9)  = {ll_e:.4f}   （真值→MLE 增益 {ll_e - ll_truth:+.4f}）")
    print(f"  ll(lin MLE, k=7)  = {ll_l:.4f}   （比 exp MLE 低 {ll_e - ll_l:.4f}）")
    print(f"  BIC: exp {bic(ll_e, 9, n):.2f}   lin {bic(ll_l, 7, n):.2f}"
          f"   → {'lin 更优' if bic(ll_l, 7, n) < bic(ll_e, 9, n) else 'exp 更优'}"
          f"（ΔBIC={bic(ll_e,9,n)-bic(ll_l,7,n):+.2f}，|Δ|<2 视为无差别）")

    print("\n  exp 真值 与 两个模型 MLE 推出的剖面（关键：线性能否重现形态）")
    d_true = drift_magnitude(P_SINGLE, np.array(T_L), 0, TRUTH)
    a_true = boundary_a(np.array(W_L), TRUTH)
    d_lin = drift_magnitude(P_SINGLE, np.array(T_L), 0, fit_l["params"])
    a_lin = boundary_a(np.array(W_L), fit_l["params"])
    print(f"    d(T)  真值 {np.round(d_true,4)}   linMLE {np.round(d_lin,4)}"
          f"   最大偏差 {np.max(np.abs(d_lin-d_true)):.4f}")
    print(f"    a(W)  真值 {np.round(a_true,4)}   linMLE {np.round(a_lin,4)}"
          f"   最大偏差 {np.max(np.abs(a_lin-a_true)):.4f}")
    print(f"    exp MLE 的 tau_T={fit_e['params'].tau_T:.4f}（真值 {TRUTH.tau_T}）"
          f"  tau_a={fit_e['params'].tau_a:.4f}（真值 {TRUTH.tau_a}）")
    print(f"    lin MLE 的 beta_T={fit_l['params'].beta_T:.4f}  delta_a={fit_l['params'].delta_a:.4f}"
          f"  beta_ST={fit_l['params'].beta_ST:.4f}")

    # ==================================================================
    # B. lin 参数化的可识别性（用 lin 数据）
    # ==================================================================
    print("\n" + "=" * 100)
    print("【B】lin 参数化的可识别性：用 lin 真值生成，7 个参数的条件曲率 / 剖面 / 联合 MLE")
    print("=" * 100)
    x_true = LIN_TRUTH.vector(WITHIN_FREE_LIN)
    print("  条件曲率（其余参数钉在真值；rel=1e-4）：")
    print(f"    {'参数':10s} {'d²ll/dθ²':>12s} {'条件SE':>9s} {'真值':>9s} {'相对SE':>8s} {'n=30 组层z':>10s}")
    print("    " + "-" * 62)
    ses = {}
    for nm in WITHIN_FREE_LIN:
        c, se = curv(tr_lin, WITHIN_FREE_LIN, LIN_TRUTH, nm)
        ses[nm] = se
        k = WITHIN_FREE_LIN.index(nm)
        tv = x_true[k]
        rel = se / abs(tv) if tv != 0 else np.inf
        z = abs(tv) / (se / np.sqrt(30.0)) if np.isfinite(se) else 0.0
        print(f"    {nm:10s} {c:12.4f} {se:9.4f} {tv:9.4f} {rel:8.1%} {z:10.1f}")

    print("\n  剖面 95% 区间判决（n_grid=21，其余参数自由重优化）：")
    print(f"    {'参数':10s} {'x_hat':>10s} {'95%CI':>26s} {'宽度':>8s} {'判决':>8s}")
    print("    " + "-" * 68)
    tally = {"含真值": 0, "有偏": 0, "不可识别": 0}
    for nm in ("beta_T", "beta_ST", "delta_a", "d_ref", "a_ref", "t0", "beta_S"):
        r = profile_se(tr_lin, WITHIN_FREE_LIN, LIN_TRUTH, nm, n_grid=21)
        v = verdict(r)
        tally[v] += 1
        ci = "未闭合" if (r["lo"] is None or r["hi"] is None) else f"[{r['lo']:+.4f},{r['hi']:+.4f}]"
        w = "—" if (r["lo"] is None or r["hi"] is None) else f"{r['hi']-r['lo']:.4f}"
        print(f"    {nm:10s} {r['x_hat']:+10.4f} {ci:>26s} {w:>8s} {v:>8s}")
    print(f"    → 汇总 {tally}")

    print("\n  联合 MLE（7 自由，gtol=1e-10, ftol=1e-14, 12 起点）：")
    fit_j = fit_mle(tr_lin, WITHIN_FREE_LIN, LIN_TRUTH, n_restart=12, seed=0,
                    gtol=1e-10, ftol=1e-14, maxfun=40000)
    print(f"    success={fit_j['success']}  n_starts_ok={fit_j['n_starts_ok']}"
          f"  nfev={fit_j['nfev']}  ll={float(fit_j['loglik']):.4f}"
          f"（真值 {log_likelihood(LIN_TRUTH, tr_lin):.4f}）")
    best = fit_j["params"]
    print(f"    {'参数':10s} {'x_hat':>10s} {'真值':>9s} {'偏差':>10s} {'偏差/条件SE':>12s}")
    print("    " + "-" * 54)
    for nm in WITHIN_FREE_LIN:
        xh = float(getattr(best, nm))
        tv = float(getattr(LIN_TRUTH, nm))
        r = (xh - tv) / ses[nm] if np.isfinite(ses[nm]) else np.nan
        print(f"    {nm:10s} {xh:+10.4f} {tv:+9.4f} {xh-tv:+10.4f} {r:+12.2f}")

    # ==================================================================
    print("\n" + "=" * 100)
    print("读法")
    print("=" * 100)
    print("  * 【A】Δll 若远小于 9 参数的普通过拟合量级 p/2=4.5，且 ΔBIC<2 ⇒ 线性限制几乎不损失现象，")
    print("    可以放心用无时标参数化；若 Δll 很大 ⇒ 理论上的『指数趋近』叙事不能丢，需回到方案 2/3。")
    print("  * 【B】7 个参数若全部『含真值』且相对 SE 明显优于 exp 模型的 330%/254% ⇒ 处方成立。")
    print("  * 『偏差/条件SE』用来判断是否真收敛：该列应在 ±2 内。")
    print(f"\n  总耗时 {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
