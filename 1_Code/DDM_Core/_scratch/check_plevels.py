# -*- coding: utf-8 -*-
"""Stage 3b 组层天花板到底由什么决定：每组人数 n，还是 P 的水平数？

动机
----
`recover_group.py` 的 oracle（喂**真值**被试层参数）在 n=10/组、4 个 P 水平下
`tau_P` 偏 −12.4%、回归残差 RMS 0.1044。我此前把它解释成「设计天花板」。
但这个解释**没有验证过**：oracle 用的既然是真值，误差就只可能来自
① 被试层抽样噪声、② 组层回归的识别性、③ 优化器。

本探针把 ① 单独控制住（重复 200 次，看 bias 是否随重复数收敛、看 SD 怎么随 n 缩），
再用**无噪声 oracle**（直接喂组模型值，不带被试噪声）检验 ②。

判读
----
* 无噪声 oracle 若精确返回真值 ⇒ 组模型在给定水平集下**完全可识别** ⇒
  此前记的「天花板只允许 13%」是**抽样噪声**，提高 n 就能降 ⇒ 我写错了，必须更正。
* 无噪声 oracle 若也偏 ⇒ 才是真的水平集天花板，与 n 无关。

用法： python _scratch/check_plevels.py [重复次数]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mapping import f_P                                    # noqa: E402
from recover_group import (BASE_SEED, GROUP_FIT_NAMES,     # noqa: E402
                          GROUP_INIT_LIN, GROUP_TRUTH_LIN, P_COMMON_REF,
                          fit_between, make_subject_truth)

TRUTH = GROUP_TRUTH_LIN
INIT = GROUP_INIT_LIN

# 现行水平集（与 recover_group.py 一致）
LEVELS4 = [0.0, 8.0, 32.0, 120.0]
# 候选：加更多中间水平，看 tau_P 是否变得可识别
LEVELS7 = [0.0, 4.0, 8.0, 16.0, 32.0, 64.0, 120.0]
LEVELS9 = [0.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 90.0, 120.0]

N_PER_GRID = [10, 20, 40, 80, 160]


def draw_true(P_levels, n_per, rep):
    """抽出一批被试的**真值**被试层参数（与 recover_group.py 同一种子方案 + 重复号）。"""
    P_sub, d_true, s_true = [], [], []
    for P in P_levels:
        for s in range(n_per):
            seed = BASE_SEED + rep * 100000 + int(P) * 1000 + s
            rng = np.random.default_rng(seed)
            st, _ = make_subject_truth(TRUTH, P, P_COMMON_REF, rng)
            P_sub.append(P)
            d_true.append(st.d_ref)
            s_true.append(st.beta_S)
    return np.array(P_sub), np.array(d_true), np.array(s_true)


def noise_free(P_levels):
    """无噪声 oracle：直接喂组模型在各级上的期望值（每组等人数）。"""
    P_levels = np.asarray(P_levels, float)
    reg = f_P(P_levels, TRUTH.tau_P) - f_P(P_COMMON_REF, TRUTH.tau_P)
    d = TRUTH.d_ref + TRUTH.beta_P * reg
    s = TRUTH.beta_S + TRUTH.beta_SP * reg
    return P_levels.copy(), d, s


def summarise(vals, truth):
    v = np.asarray(vals, float)
    ok = np.isfinite(v)
    if not ok.any():
        return dict(mean=np.nan, sd=np.nan, bias=np.nan, rmse=np.nan, n_ok=0)
    v = v[ok]
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                bias=float(v.mean() - truth), rmse=float(np.sqrt(np.mean((v - truth) ** 2))),
                n_ok=int(v.size))


def main():
    n_rep = int(sys.argv[1]) if len(sys.argv) > 1 else 200

    print("=" * 96)
    print("A. 无噪声 oracle —— 组层回归本身是否可识别？（没有任何被试抽样噪声）")
    print("=" * 96)
    print(f"{'水平集':>26s} {'tau_P':>10s} {'beta_P':>10s} {'d_ref':>10s} "
          f"{'beta_S':>10s} {'beta_SP':>10s} {'残差RMS':>10s}")
    for label, lv in (("L4 (现行 0/8/32/120)", LEVELS4),
                      ("L7 (+4/16/64)", LEVELS7),
                      ("L9 (+2/90)", LEVELS9)):
        P, d, s = noise_free(lv)
        fit, rms = fit_between(P, d, s, P_COMMON_REF, INIT.vector(GROUP_FIT_NAMES))
        print(f"{label:>26s} {fit['tau_P']:10.4f} {fit['beta_P']:10.4f} "
              f"{fit['d_ref']:10.4f} {fit['beta_S']:10.4f} {fit['beta_SP']:10.4f} "
              f"{rms:10.2e}")
    print(f"{'真值':>26s} {TRUTH.tau_P:10.4f} {TRUTH.beta_P:10.4f} "
          f"{TRUTH.d_ref:10.4f} {TRUTH.beta_S:10.4f} {TRUTH.beta_SP:10.4f}")

    print()
    print("=" * 96)
    print(f"B. 有噪声 oracle，{n_rep} 次重复 —— 误差随每组人数 n 怎么缩？")
    print("=" * 96)
    for label, lv in (("L4 (现行 0/8/32/120)", LEVELS4),
                      ("L7 (+4/16/64)", LEVELS7),
                      ("L9 (+2/90)", LEVELS9)):
        print(f"\n--- {label} ---")
        print(f"{'n/组':>6s} {'N':>5s} {'tau_P 均值':>12s} {'Bias':>10s} {'SD':>10s} "
              f"{'RMSE':>10s} | {'beta_P Bias':>12s} {'SD':>9s} | {'d_ref Bias':>11s} "
              f"{'SD':>9s} | {'beta_SP Bias':>12s} {'SD':>9s}")
        for n_per in N_PER_GRID:
            taus, bps, drefs, bss, bsps = [], [], [], [], []
            for rep in range(n_rep):
                P, d, s = draw_true(lv, n_per, rep)
                fit, _ = fit_between(P, d, s, P_COMMON_REF, INIT.vector(GROUP_FIT_NAMES))
                taus.append(fit["tau_P"]); bps.append(fit["beta_P"])
                drefs.append(fit["d_ref"]); bss.append(fit["beta_S"])
                bsps.append(fit["beta_SP"])
            T = summarise(taus, TRUTH.tau_P); B = summarise(bps, TRUTH.beta_P)
            D = summarise(drefs, TRUTH.d_ref); S = summarise(bss, TRUTH.beta_S)
            SP = summarise(bsps, TRUTH.beta_SP)
            print(f"{n_per:6d} {n_per*len(lv):5d} {T['mean']:12.4f} {T['bias']:10.4f} "
                  f"{T['sd']:10.4f} {T['rmse']:10.4f} | {B['bias']:12.4f} {B['sd']:9.4f} | "
                  f"{D['bias']:11.4f} {D['sd']:9.4f} | {SP['bias']:12.4f} {SP['sd']:9.4f}")

    print()
    print("=" * 96)
    print("C. tau_P 估计量的**分布**（是不是靠撞界在撑 SD？）")
    print("=" * 96)
    for n_per in (10, 40, 160):
        taus = []
        for rep in range(n_rep):
            P, d, s = draw_true(LEVELS4, n_per, rep)
            fit, _ = fit_between(P, d, s, P_COMMON_REF, INIT.vector(GROUP_FIT_NAMES))
            taus.append(fit["tau_P"])
        v = np.asarray(taus, float)
        q = np.percentile(v, [0, 10, 50, 90, 100])
        pct_lo = 100.0 * float(np.mean(v <= 1.0 + 1e-6))
        pct_hi = 100.0 * float(np.mean(v >= 200.0 - 1e-6))
        pct_band = 100.0 * float(np.mean(np.abs(v / TRUTH.tau_P - 1.0) <= 0.25))
        print(f"n={n_per:3d} (N={n_per*4:4d})  min {q[0]:8.2f}  q10 {q[1]:8.2f}  "
              f"median {q[2]:8.2f}  q90 {q[3]:8.2f}  max {q[4]:8.2f} │ "
              f"撞下界 {pct_lo:5.1f}%  撞上界 {pct_hi:5.1f}%  "
              f"│误差≤25% {pct_band:5.1f}%")
    print(f"          真值 tau_P = {TRUTH.tau_P:.2f}")

    print()
    print("=" * 96)
    print("D. 备选：**去掉 tau_P，P 通道改线性**（与 D22 对 T 的处理同一招）")
    print("=" * 96)

    def fit_linear(P_sub, d_hat, s_hat, P_ref):
        x = np.asarray(P_sub, float) - float(P_ref)
        A = np.column_stack([np.ones_like(x), x])
        cd, *_ = np.linalg.lstsq(A, np.asarray(d_hat, float), rcond=None)
        cs, *_ = np.linalg.lstsq(A, np.asarray(s_hat, float), rcond=None)
        return dict(d_ref=float(cd[0]), beta_P=float(cd[1]),
                    beta_S=float(cs[0]), beta_SP=float(cs[1]))

    # D0：无噪声自检
    Pn = np.asarray(LEVELS4, float)
    regn = f_P(Pn, TRUTH.tau_P) - f_P(P_COMMON_REF, TRUTH.tau_P)
    fn = fit_linear(Pn, TRUTH.d_ref + TRUTH.beta_P * regn,
                    TRUTH.beta_S + TRUTH.beta_SP * regn, P_COMMON_REF)
    print(f"无噪声自检（**有**形式失配，因为真值是 exp 形状而拟合是直线）：")
    print(f"  beta_P {fn['beta_P']:8.4f}  d_ref {fn['d_ref']:8.4f}  "
          f"beta_S {fn['beta_S']:8.4f}  beta_SP {fn['beta_SP']:8.4f}")
    print(f"  真值   {TRUTH.beta_P:8.4f}          {TRUTH.d_ref:8.4f}          "
          f"{TRUTH.beta_S:8.4f}          {TRUTH.beta_SP:8.4f}")
    print(f"  ⇒ 线性 P 通道的最小二乘解就是「exp 曲线在 4 个水平上的最佳直线」，")
    print(f"    形式失配表现为 beta_P/d_ref 偏离真值，而不是估计量方差。")

    print()
    print(f"{'n/组':>6s} {'N':>5s} | {'beta_P 均值':>12s} {'Bias':>10s} {'SD':>9s} | "
          f"{'d_ref Bias':>11s} {'SD':>9s} | {'beta_S Bias':>12s} {'SD':>9s} | "
          f"{'beta_SP Bias':>12s} {'SD':>9s}")

    # 线性拟合的“真值”用 D0 的无噪声解，这样 Bias 只反映抽样噪声
    for n_per in N_PER_GRID:
        bps, drefs, bss, bsps = [], [], [], []
        for rep in range(n_rep):
            P, d, s = draw_true(LEVELS4, n_per, rep)
            f = fit_linear(P, d, s, P_COMMON_REF)
            bps.append(f["beta_P"]); drefs.append(f["d_ref"])
            bss.append(f["beta_S"]); bsps.append(f["beta_SP"])
        B = summarise(bps, fn["beta_P"]); D = summarise(drefs, fn["d_ref"])
        S = summarise(bss, fn["beta_S"]); SP = summarise(bsps, fn["beta_SP"])
        print(f"{n_per:6d} {n_per*4:5d} | {B['mean']:12.4f} {B['bias']:10.4f} "
              f"{B['sd']:9.4f} | {D['bias']:11.4f} {D['sd']:9.4f} | "
              f"{S['bias']:12.4f} {S['sd']:9.4f} | {SP['bias']:12.4f} {SP['sd']:9.4f}")

    print()
    print("=" * 96)
    print("E. 处方候选：**把 tau_P 先验固定在真值**，只估 beta_P（与 D18/D19 同一招）")
    print("=" * 96)

    def fit_fixed_tau(P_sub, d_hat, s_hat, P_ref, tau_fix):
        x = f_P(np.asarray(P_sub, float), tau_fix) - f_P(float(P_ref), tau_fix)
        A = np.column_stack([np.ones_like(x), x])
        cd, *_ = np.linalg.lstsq(A, np.asarray(d_hat, float), rcond=None)
        cs, *_ = np.linalg.lstsq(A, np.asarray(s_hat, float), rcond=None)
        return dict(d_ref=float(cd[0]), beta_P=float(cd[1]),
                    beta_S=float(cs[0]), beta_SP=float(cs[1]))

    print(f"{'n/组':>6s} {'N':>5s} | {'beta_P Bias':>12s} {'SD':>9s} {'相对SD':>9s} | "
          f"{'d_ref Bias':>11s} {'SD':>9s} | {'beta_SP Bias':>12s} {'SD':>9s} "
          f"{'相对SD':>9s}")
    for n_per in N_PER_GRID:
        bps, drefs, bss, bsps = [], [], [], []
        for rep in range(n_rep):
            P, d, s = draw_true(LEVELS4, n_per, rep)
            f = fit_fixed_tau(P, d, s, P_COMMON_REF, TRUTH.tau_P)
            bps.append(f["beta_P"]); drefs.append(f["d_ref"])
            bss.append(f["beta_S"]); bsps.append(f["beta_SP"])
        B = summarise(bps, TRUTH.beta_P); D = summarise(drefs, TRUTH.d_ref)
        SP = summarise(bsps, TRUTH.beta_SP)
        print(f"{n_per:6d} {n_per*4:5d} | {B['bias']:12.4f} {B['sd']:9.4f} "
              f"{B['sd']/abs(TRUTH.beta_P):8.1%} | {D['bias']:11.4f} {D['sd']:9.4f} | "
              f"{SP['bias']:12.4f} {SP['sd']:9.4f} {SP['sd']/abs(TRUTH.beta_SP):8.1%}")
    print("  ⇒ 固定 tau_P 后 beta_P 的**抽样噪声**下降多少，就是「先验固定」买到的东西。")

    print()
    print("=" * 96)
    print("F. 有没有别的水平集能让 tau_P 可识别？（n=10 与 n=40）")
    print("=" * 96)
    CANDIDATES = [
        ("L4 现行 0/8/32/120", [0.0, 8.0, 32.0, 120.0]),
        ("L5 上升段 0/5/10/20/40", [0.0, 5.0, 10.0, 20.0, 40.0]),
        ("L5 宽带 0/10/30/60/120", [0.0, 10.0, 30.0, 60.0, 120.0]),
        ("L6 0/4/8/16/32/64", [0.0, 4.0, 8.0, 16.0, 32.0, 64.0]),
        ("L8 0/2/4/8/16/32/64/120", [0.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 120.0]),
    ]
    print(f"{'水平集':>26s} | {'n=10 tau_P 相对SD':>18s} {'误差≤25%':>10s} | "
          f"{'n=40 tau_P 相对SD':>18s} {'误差≤25%':>10s}")
    for label, lv in CANDIDATES:
        cells = []
        for n_per in (10, 40):
            taus = []
            for rep in range(n_rep):
                P, d, s = draw_true(lv, n_per, rep)
                fit, _ = fit_between(P, d, s, P_COMMON_REF, INIT.vector(GROUP_FIT_NAMES))
                taus.append(fit["tau_P"])
            v = np.asarray(taus, float)
            rel = float(np.std(v, ddof=1) / TRUTH.tau_P)
            band = 100.0 * float(np.mean(np.abs(v / TRUTH.tau_P - 1.0) <= 0.25))
            cells.append((rel, band))
        print(f"{label:>26s} | {cells[0][0]:18.1%} {cells[0][1]:9.1f}% | "
              f"{cells[1][0]:18.1%} {cells[1][1]:9.1f}%")
    print("  ⇒ 若所有候选在 n=10 都在 100% 上下，就说明**这是被试间方差的问题，")
    print("     不是水平集选择的问题**——换水平集救不了 tau_P。")

    print()
    print("=" * 96)
    print("读法")
    print("=" * 96)
    print(" A 段若无噪声 oracle 精确返回真值 ⇒ 组模型在 4 个水平下完全可识别，")
    print(" 则 B 段的 oracle 误差纯粹是被试抽样噪声，随 n 以 1/sqrt(n) 下降 ⇒")
    print(" 「天花板只允许 13%」的说法是**抽样噪声**，不是设计限制。")
    print(" 反之，无噪声 oracle 也偏 ⇒ 才是真正的水平集天花板，且加 n 无用。")


if __name__ == "__main__":
    main()
