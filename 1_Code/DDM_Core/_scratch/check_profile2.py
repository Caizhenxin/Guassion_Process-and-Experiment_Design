# -*- coding: utf-8 -*-
"""
check_profile2.py —— 修好多起点后重做剖面，并给 τ_T 的可识别性下结论
====================================================================
要回答三个问题
--------------
Q1. `log_likelihood` 光滑吗？（决定"曲率类方法"能不能用）
    二阶中心差分 (ll₊ − 2ll₀ + ll₋)/h² 若随 h↓ 发散 ⇒ 似然是**分段光滑**
    （survival_series 截断项在参数变化时跳变），则 Hessian / OPG **全部**作废。
Q2. `profile_se` 报出的"8 参数受限解 ll=−441.9 优于 9 参数无约束解 ll=−456.0"
    到底是不是 bug？
    受限解不可能更优。修好多起点（原实现只在边界 15%–85% 采样，几乎不覆盖空间）
    后重跑：若全局 MLE 达到 ≥ −441.9，则剖面**是对的**、之前两个拟合都欠收敛；
    若仍然停在 −456.0，则剖面实现有 bug。
Q3.（**最关键**）τ_T 到底能不能估出来？
    直接做 τ_T 的剖面（其余 8 参数自由、多起点全局搜）。若整条曲线在
    [0.015, 0.30]（20 倍跨度）内只变 2–3 个 log 单位，则 τ_T 在**本设计下不可估**，
    必须**先验固定**或从模型里去掉——这是可以直接写进论文的结论。

用法
----
    python check_profile2.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from check_tpath import make_trials  # noqa: E402
from likelihood import fit_mle, log_likelihood  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402
from design_fim import TRUTH  # noqa: E402

NAMES = list(WITHIN_FREE)
TIGHT = dict(n_restart=12, maxfun=40000, maxiter=2000)
TOL = dict(gtol=1e-10, ftol=1e-14)


def curvature(tr, name, x0):
    """Q1：二阶中心差分随步长的收敛性。"""
    l0 = log_likelihood(TRUTH.replace(**{name: x0}), tr)
    print(f"  基线 ll = {l0:.6f}   （{name} = {x0}）")
    print(f"  {'h':>9s} {'ll(+h)−ll₀':>13s} {'ll(−h)−ll₀':>13s} {'d²ll/dθ²':>14s}")
    prev = None
    for h in (1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4):
        lp = log_likelihood(TRUTH.replace(**{name: x0 + h}), tr)
        lm = log_likelihood(TRUTH.replace(**{name: x0 - h}), tr)
        d2 = (lp - 2 * l0 + lm) / h ** 2
        tag = ""
        if prev is not None and abs(d2 - prev) > 0.5 * max(abs(prev), 1e-9):
            tag = "  ← 不收敛"
        print(f"  {h:9.0e} {lp-l0:13.6f} {lm-l0:13.6f} {d2:14.4f}{tag}")
        prev = d2


def jump_test(tr, name, x0, lo, hi, n=4001):
    """Q1b：在窄区间上密集采样，看相邻点增量有没有离群跳变。"""
    xs = np.linspace(lo, hi, n)
    lls = np.array([log_likelihood(TRUTH.replace(**{name: float(x)}), tr) for x in xs])
    d = np.diff(lls)
    step = (hi - lo) / (n - 1)
    med = float(np.median(np.abs(d)))
    mx = float(np.max(np.abs(d)))
    print(f"  区间 [{lo}, {hi}] 采 {n} 点（步长 {step:.2e}）")
    print(f"    |Δll| 中位数 = {med:.3e}   最大 = {mx:.3e}   比值 = {mx/max(med,1e-300):.1f}×")
    print(f"    ⇒ {'**存在跳变（似然分段光滑）**' if mx > 40*max(med,1e-300) else '无异常跳变（似然光滑）'}")
    return mx > 40 * max(med, 1e-300)


def profile(tr, name, grid, ll_ref, n_restart=12, label=""):
    """对 name 做剖面：其余参数自由 + 全局多起点。"""
    others = [n for n in NAMES if n != name]
    rows = []
    t0 = time.time()
    for v in grid:
        p_fix = TRUTH.replace(**{name: float(v)})
        f = fit_mle(tr, others, p_fix, **TIGHT, **TOL)
        rows.append((float(v), f["loglik"], f["nfev"]))
    print(f"  剖面 {name}（{label}，{len(grid)} 点，{time.time()-t0:.1f}s）")
    print(f"    {'值':>10s} {'ll':>12s} {'Δll':>9s} {'nfev':>7s}   {'bar'}")
    best = max(r[1] for r in rows)
    for v, ll, nf in rows:
        d = ll - ll_ref
        bar = "█" * int(max(0, min(40, round(d + 22)))) if d > -22 else ""
        print(f"    {v:10.4f} {ll:12.4f} {d:+9.3f} {nf:7d}   {bar}")
    return rows, best


def main():
    t_start = time.time()
    # check_tpath 用 seed=7 的那一份 D4 数据
    design, sim, tr = make_trials(seed=7)
    ll_true = log_likelihood(TRUTH, tr)
    print("=" * 100)
    print("Q1. 似然的光滑性 —— 决定曲率类方法（Hessian / OPG / 剖面 SE）是否可用")
    print("=" * 100)
    curvature(tr, "beta_T", TRUTH.beta_T)
    print()
    jump_test(tr, "beta_T", TRUTH.beta_T, 0.54, 0.56)

    print("\n" + "=" * 100)
    print("Q2. 全局 MLE（24 个覆盖整个参数空间的起点，紧容差）")
    print("=" * 100)
    t0 = time.time()
    g = fit_mle(tr, NAMES, TRUTH, n_restart=24, maxfun=60000, maxiter=3000, **TOL)
    print(f"  ll(真值) = {ll_true:.4f}")
    print(f"  ll(全局) = {g['loglik']:.4f}   Δ = {g['loglik']-ll_true:+.4f}   "
          f"n_starts_ok={g['n_starts_ok']}/{24}   ({time.time()-t0:.1f}s)")
    for nm, v, t in zip(NAMES, g["params"].vector(NAMES), TRUTH.vector(NAMES)):
        print(f"    {nm:9s} {v:9.4f}  (真值 {t:8.4f})")
    print(f"  ⚠️ 之前松容差 + 窄起点得 −456.0075；若现在 ≥ −441.9，则剖面是对的、"
          f"之前是**欠收敛**。")

    print("\n" + "=" * 100)
    print("Q3. **τ_T 能不能估出来**（其余 8 参数自由，全局多起点）")
    print("=" * 100)
    taus = [0.015, 0.020, 0.030, 0.045, 0.060, 0.080, 0.110, 0.150, 0.220, 0.300]
    rows_t, best_t = profile(tr, "tau_T", taus, ll_true, label="τ_T")
    spread = max(r[1] for r in rows_t) - min(r[1] for r in rows_t)
    print(f"\n  ★ τ_T 从 0.015 到 0.300（**20 倍**）整条剖面的 ll 极差 = {spread:.2f} 个 log 单位")
    if spread < 4.0:
        print("    ⇒ **τ_T 在本设计下实质不可识别**：数据几乎不在乎 τ_T 是 15 ms 还是 300 ms。")
        print("       结论：τ_T 必须**先验固定**（文献值），或把模型简化为不含 τ_T 的形式；")
        print("       报告 β_T 时必须写明\"条件于 τ_T = 固定值\"。")
    else:
        print("    ⇒ τ_T 有一定可识别性；可估，但 SE 会很宽。")

    print("\n" + "=" * 100)
    print("Q4. 复核 τ_a（解决 −441.9 矛盾）与 δa")
    print("=" * 100)
    grid_a = [0.2, 0.4, 0.7, 1.2, 2.0, 3.5, 5.0]
    rows_a, _ = profile(tr, "tau_a", grid_a, ll_true, label="τ_a")
    print(f"\n  旧实现曾在此报 Δ=+19.73（即 ll=−441.9 > 全局 MLE）。现在全局 ll={g['loglik']:.4f}。")
    worst = max(r[1] for r in rows_a)
    print(f"  新剖面最大值 ll = {worst:.4f}  →  "
          f"{'仍超过全局 MLE ⇒ 剖面实现有 bug' if worst > g['loglik'] + 1e-6 else '不再超过全局 MLE ⇒ 原矛盾已消除（是欠收敛）'}")

    grid_d = [0.0, 0.2, 0.55, 1.0, 2.0, 3.0]
    profile(tr, "delta_a", grid_d, ll_true, label="δa")

    print("\n" + "=" * 100)
    print("总结")
    print("=" * 100)
    print(f"  1. 似然光滑性：见 Q1。")
    print(f"  2. 全局 MLE = {g['loglik']:.4f}（Δ={g['loglik']-ll_true:+.2f} 相对真值）。")
    print(f"  3. τ_T 剖面极差 = {spread:.2f} log 单位 ⇒ "
          f"{'不可识别（需先验固定）' if spread < 4 else '弱可识别'}。")
    print(f"  4. 总耗时 {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
