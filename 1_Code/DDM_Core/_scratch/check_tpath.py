# -*- coding: utf-8 -*-
"""
check_tpath.py —— T 通路（τ_T, β_T, β_ST）到底是"真不可识别"还是"优化器没收敛"
================================================================================
背景
----
`check_fim.py` 报出两个**数学上不可能**的结果：
  * 9 参数联合 MLE 停在 β_T=4.9615, β_ST=−4.0000（都贴边界），ll=−456.0075；
  * 同一份数据上，**8 参数受限**剖面却达到 ll=−441.9。
受限解不可能优于无约束解 ⇒ 优化器没收敛（L-BFGS-B 默认 gtol=1e-5 在极平的
似然面上提前判停）。所以：

  **任何基于"优化器 + 局部曲率"的结论（Hessian / OPG / 剖面）在这一段都不可信。**

本脚本用两种都不依赖优化器的办法把问题钉死
--------------------------------------------
A. **直接似然面**：固定其余参数在真值，只让 (τ_T, β_T) 或 (τ_T, β_ST) 自由，
   在网格上直接算 ΔlogL。若存在明显的平脊 / 多个最优 → 真不可识别；
   若只有一个陡谷 → 之前是优化器问题。
B. **收紧容差的联合 MLE**：gtol=1e-12, ftol=1e-15, 多起点，看能否回到真值。

为什么是这两个参数
------------------
映射为
    dqt = Q_T(T, τ_T) − Q_T(T_ref, τ_T),  Q_T(X, τ) = 1 − exp(−X/τ)
    d   = d_ref + β_P·dfp + β_T·dqt + I_self·(β_S + β_SP·dfp + β_ST·dqt)
τ_T 只通过 dqt **整体缩放** T 通路：给定 τ_T，dqt 是被 Q_T 饱和性限定的形状；
β_T 与 β_ST 再线性缩放它。三者因此在 Q_T 饱和区互相补偿。

用法
----
    python check_tpath.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))  # DDM_Core 本体

from design_fim import DESIGNS, P_SINGLE, TRUTH  # noqa: E402
from likelihood import fit_mle, log_likelihood, trials_from_arrays  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

NAMES = list(WITHIN_FREE)
KEY = "D4        (4T×3W, r12)"


def make_trials(seed=7):
    T_L, W_L, REP = DESIGNS[KEY]
    design = build_design(P_SINGLE, T_L, W_L, REP)
    rng = np.random.default_rng(seed)
    sim = simulate_subject(design, TRUTH, rng)
    tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                            *design_arrays(design))
    return design, sim, tr


def surface(tr, x_name, xs, y_name, ys, ll0):
    """固定其余参数在真值，返回 ΔlogL 网格（行=x，列=y）及最优格点。"""
    G = np.full((len(xs), len(ys)), np.nan)
    for i, xv in enumerate(xs):
        for j, yv in enumerate(ys):
            ll = log_likelihood(TRUTH.replace(**{x_name: float(xv),
                                                 y_name: float(yv)}), tr)
            G[i, j] = ll - ll0
    return G


def show(G, xs, ys):
    best = np.unravel_index(np.nanargmax(G), G.shape)
    print("      " + " ".join(f"{v:7.3f}" for v in ys))
    for i, xv in enumerate(xs):
        mark = " <<<" if i == best[0] else ""
        print(f"{xv:7.3f} " + " ".join(f"{G[i, j]:7.2f}" for j in range(len(ys))) + mark)
    print(f"  网格最优：{xs[best[0]]:.4f} × {ys[best[1]]:.4f} → ΔlogL = {G[best]:+.2f}")
    return best


def main():
    t_start = time.time()
    design, sim, tr = make_trials()
    ll0 = log_likelihood(TRUTH, tr)
    n = int(tr["rt"].size)
    print("=" * 100)
    print("T 通路可识别性诊断（D4 = 4T×3W×r12，P=120 固定）")
    print("=" * 100)
    print(f"  试次 {n}  遗漏率 {float(sim['omission'].mean()):.3f}  "
          f"真值 τ_T={TRUTH.tau_T} β_T={TRUTH.beta_T} β_ST={TRUTH.beta_ST}")
    print(f"  **基线 ll(真值) = {ll0:.4f}（以下全部是 ΔlogL，>0 表示比真值更好）**")
    print(f"  τ_T=0.08 时各 T 的 dqt = ", end="")
    W_L = DESIGNS[KEY][1]
    for T in DESIGNS[KEY][0]:
        q = 1 - np.exp(-T / TRUTH.tau_T)
        qr = 1 - np.exp(-0.10 / TRUTH.tau_T)
        print(f"T={T*1000:.0f}:{q-qr:+.3f} ", end="")
    print(f"\n  （|dqt| 最大仅 ~0.37，且 T=150/250 已饱和 → τ_T 的杠杆很小）\n")

    # ---------------- A1: (τ_T, β_T) ----------------
    print("-" * 100)
    print("A1. 直接似然面 ①：(τ_T, β_T)，其余参数钉在真值")
    print("-" * 100)
    xs = np.concatenate([[TRUTH.tau_T], np.geomspace(0.015, 0.30, 12)])
    ys = np.array([0.0, 0.2, 0.4, 0.55, 0.8, 1.2, 2.0, 3.0, 4.5, 6.0])
    G1 = surface(tr, "tau_T", xs, "beta_T", ys, ll0)
    show(G1, xs, ys)

    # ---------------- A2: (τ_T, β_ST) ----------------
    print("\n" + "-" * 100)
    print("A2. 直接似然面 ②：(τ_T, β_ST)，其余参数钉在真值")
    print("-" * 100)
    ys2 = np.array([-1.0, -0.5, 0.0, 0.10, 0.3, 0.6, 1.0, 1.6, 2.4])
    G2 = surface(tr, "tau_T", xs, "beta_ST", ys2, ll0)
    show(G2, xs, ys2)

    # ---------------- A3: (β_T, β_ST) 固定真 τ_T ----------------
    print("\n" + "-" * 100)
    print("A3. 直接似然面 ③：(β_T, β_ST)，τ_T 钉在真值 0.08")
    print("-" * 100)
    xs3 = np.array([0.0, 0.2, 0.4, 0.55, 0.8, 1.2, 2.0, 3.0, 4.5, 6.0])
    G3 = surface(tr, "beta_T", xs3, "beta_ST", ys2, ll0)
    show(G3, xs3, ys2)

    # ---------------- B: 收紧容差的联合 MLE ----------------
    print("\n" + "=" * 100)
    print("B. 联合 9 参数 MLE：容差的影响（同一份数据）")
    print("=" * 100)

    def run(tag, **kw):
        t0 = time.time()
        f = fit_mle(tr, NAMES, TRUTH, **kw)
        dt = time.time() - t0
        print(f"\n  [{tag}]  ll={f['loglik']:.4f} (Δ={f['loglik']-ll0:+.3f})  "
              f"success={f['success']}  nfev={f['nfev']}  {dt:.1f}s")
        vec = f["params"].vector(NAMES)
        tru = TRUTH.vector(NAMES)
        for nm, v, t in zip(NAMES, vec, tru):
            flag = "  ← 贴边界/严重偏离" if abs(v - t) > max(0.5 * abs(t), 0.3) else ""
            print(f"      {nm:9s} 拟合={v:9.4f}  真值={t:8.4f}  差={v-t:+9.4f}{flag}")
        return f

    f_loose = run("松容差 gtol=1e-5（之前的默认）", n_restart=4, maxfun=8000)
    f_tight = run("紧容差 gtol=1e-12, ftol=1e-15", n_restart=6, maxfun=40000,
                  maxiter=2000, gtol=1e-12, ftol=1e-15)

    print("\n" + "=" * 100)
    print("判读")
    print("=" * 100)
    print(f"  ① 松容差 ll = {f_loose['loglik']:.4f}；紧容差 ll = {f_tight['loglik']:.4f}")
    print(f"     差值 = {f_tight['loglik']-f_loose['loglik']:+.4f}")
    if f_tight["loglik"] > f_loose["loglik"] + 1.0:
        print("     ⇒ **松容差确实没收敛**：之前的点估计与局部曲率结论全部作废。")
    else:
        print("     ⇒ 两者一致，之前的点估计是收敛的（那不可识别性就是真的）。")
    print("  ② 若 A1/A2 出现**宽阔平脊**（多个格点 ΔlogL ≈ 0），则 τ_T 与 β_T/β_ST")
    print("     的联合确实不可识别 —— 这是**设计问题**，不是估计问题。")
    print("  ③ 若 A1/A2 只有一个明确谷点且紧容差 MLE 回到真值，则问题只在优化器。")
    print(f"\n  总耗时 {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
