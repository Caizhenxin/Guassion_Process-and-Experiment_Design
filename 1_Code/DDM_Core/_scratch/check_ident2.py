# -*- coding: utf-8 -*-
"""
check_ident2.py —— 在参数空间直接求观测信息矩阵 → 一次拿到"可识别组合"
========================================================================
为什么可以这么做
----------------
`check_profile2.py` Q1 已**证明 `log_likelihood` 光滑**：
    d²ll/dβ_T² = −18.8366 在 h = 1e-1 … 1e-4 三个数量级上稳定到 4 位小数；
    密集采样的相邻增量无跳变（max/median = 1.2×）。
因此二阶中心差分是合法的。之前 `numerical_hessian` 出垃圾，原因是
(a) 在**跑到边界的错点**上求导，(b) 在 logit 坐标用 h≈1–3 的超大步长。
本脚本改为**直接在参数空间**求导，步长按各参数边界宽度取 1e-3，并做两项自检。

输出（论文可直接引用）
----------------------
1. `I = −H` 的特征分解。**最小特征值的特征向量 = 最不可识别的组合**；
   `1/√λ` 是该方向的"标准误"，用参数自身单位表示。
2. 条件 SE（其余参数固定）vs 边缘 SE（其余自由）。两者差距大就是不可识别的证据。
3. 多数据集复核：全局 MLE 是否**每次**都跑到同一个角？

用法
----
    python check_ident2.py
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
from design_fim import TRUTH  # noqa: E402
from likelihood import _bounds_for, fit_mle, log_likelihood  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402

NAMES = list(WITHIN_FREE)
TOL = dict(gtol=1e-10, ftol=1e-14)


def hessian_params(tr, p, names, h_rel=1e-3):
    """参数空间里的观测信息矩阵（二阶中心差分）。"""
    lo, hi = _bounds_for(names)
    theta = p.vector(names)
    h = np.maximum(h_rel * (hi - lo), 1e-5)
    n = len(names)
    f0 = log_likelihood(p, tr)
    H = np.zeros((n, n))
    # 对角
    for i in range(n):
        d = np.zeros(n); d[i] = h[i]
        lp = log_likelihood(p.with_vector(names, theta + d), tr)
        lm = log_likelihood(p.with_vector(names, theta - d), tr)
        H[i, i] = (lp - 2 * f0 + lm) / h[i] ** 2
    # 非对角（4 点公式）
    for i in range(n):
        for j in range(i + 1, n):
            di = np.zeros(n); di[i] = h[i]
            dj = np.zeros(n); dj[j] = h[j]
            v = (log_likelihood(p.with_vector(names, theta + di + dj), tr)
                 - log_likelihood(p.with_vector(names, theta + di - dj), tr)
                 - log_likelihood(p.with_vector(names, theta - di + dj), tr)
                 + log_likelihood(p.with_vector(names, theta - di - dj), tr))
            H[i, j] = H[j, i] = v / (4 * h[i] * h[j])
    return H, h, f0


def report(tr, tag, p=TRUTH):
    print("=" * 104)
    print(f"观测信息矩阵 I = −H（{tag}）   —— 直接在参数空间求导，h = 1e-3 × 边界宽度")
    print("=" * 104)
    H, h, f0 = hessian_params(tr, p, NAMES)
    I = -H
    print(f"  ll = {f0:.4f}")
    print(f"  自检① I 的对角元应 > 0（凹）：{np.all(np.diag(I) > 0)}")
    ev = np.linalg.eigvalsh(I)
    print(f"  自检② λ_min = {ev.min():.4f}（>0 则 I 正定）；"
          f"条件数 = {ev.max()/max(ev.min(),1e-300):.3e}")
    print(f"  自检③ 与剖面独立测得的 d²ll/dβ_T² = −18.8366 对比："
          f"H[β_T,β_T] = {H[NAMES.index('beta_T'), NAMES.index('beta_T')]:.4f}")
    print()

    print("  每参数：条件 SE（其余固定）vs 边缘 SE（其余自由，= 剖面 SE 的近似）")
    try:
        Iinv = np.linalg.inv(I)
        edge = np.sqrt(np.maximum(np.diag(Iinv), 0))
    except np.linalg.LinAlgError:
        edge = np.full(len(NAMES), np.inf)
    cond = 1.0 / np.sqrt(np.diag(I))
    print(f"    {'参数':10s} {'真值':>9s} {'条件SE':>10s} {'边缘SE':>11s} {'边缘/条件':>10s}")
    for k, nm in enumerate(NAMES):
        ratio = edge[k] / cond[k] if cond[k] > 0 else np.inf
        flag = "  ← 不可识别" if ratio > 3 else ""
        print(f"    {nm:10s} {p.vector(NAMES)[k]:9.4f} {cond[k]:10.4f} "
              f"{edge[k]:11.4f} {ratio:10.2f}×{flag}")

    print("\n  参数相关矩阵（|r|→1 = 互相补偿）")
    sd = np.sqrt(np.maximum(np.diag(Iinv), 1e-300))
    C = Iinv / np.outer(sd, sd)
    print("             " + " ".join(f"{n[:8]:>9s}" for n in NAMES))
    for k, nm in enumerate(NAMES):
        print(f"    {nm:8s} " + " ".join(f"{C[k, m]:9.2f}" for m in range(len(NAMES))))

    print("\n  ★ 特征分解：最平坦的方向 = 最不可识别的组合")
    w, V = np.linalg.eigh(I)          # 升序
    print(f"    {'λ':>12s} {'1/√λ':>12s}   特征向量（参数单位；只列 |分量|>0.15 的）")
    for k in range(min(4, len(NAMES))):
        comp = "  ".join(f"{NAMES[m]}={V[m,k]:+.2f}"
                         for m in np.argsort(-np.abs(V[:, k]))[:4])
        print(f"    {w[k]:12.4f} {1/np.sqrt(max(w[k],1e-300)):12.3f}   {comp}")
    return I, ev


def main():
    t0 = time.time()
    design, sim, tr = make_trials(seed=7)
    print(f"D4 数据集 seed=7：{int(tr['rt'].size)} 试次，遗漏 {float(sim['omission'].mean()):.3f}\n")
    I, ev = report(tr, "在真值处求导")

    # ---------------- 多数据集复核：MLE 是否每次跑到同一个角 ----------------
    print("\n" + "=" * 104)
    print("多数据集复核：全局 MLE（12 个覆盖全域的起点，紧容差）")
    print("   目的：判断上一份数据的'跑到边界'是**模型结构**还是**单次抽样**")
    print("=" * 104)
    print(f"  {'seed':>5s} {'遗漏率':>8s} {'ll(真值)':>11s} {'ll(MLE)':>11s} {'Δ':>7s} "
          f"{'d_ref':>7s} {'b_T':>8s} {'tau_T':>7s} {'b_ST':>7s} {'d_a':>7s} {'tau_a':>7s}")
    base = []
    for seed in (7, 11, 23, 41):
        if seed == 7:
            _, s_, t_ = design, sim, tr
        else:
            _, s_, t_ = make_trials(seed=seed)
        llt = log_likelihood(TRUTH, t_)
        f = fit_mle(t_, NAMES, TRUTH, n_restart=12, maxfun=40000, maxiter=2000, **TOL)
        v = f["params"].vector(NAMES)
        g = {n: v[NAMES.index(n)] for n in
             ("d_ref", "beta_T", "tau_T", "beta_ST", "delta_a", "tau_a")}
        print(f"  {seed:5d} {float(s_['omission'].mean()):8.3f} {llt:11.3f} "
              f"{f['loglik']:11.3f} {f['loglik']-llt:+7.2f} "
              f"{g['d_ref']:7.3f} {g['beta_T']:8.3f} {g['tau_T']:7.4f} "
              f"{g['beta_ST']:7.3f} {g['delta_a']:7.3f} {g['tau_a']:7.3f}")
        base.append((f["loglik"] - llt, g))

    d = np.array([b[0] for b in base])
    print(f"\n  Δll 范围：{d.min():+.2f} … {d.max():+.2f}（均值 {d.mean():+.2f}）")
    bT = np.array([b[1]["beta_T"] for b in base])
    ta = np.array([b[1]["tau_T"] for b in base])
    ta_ = np.array([b[1]["tau_a"] for b in base])
    print(f"  β_T  ：{np.round(bT,2)}  （真值 0.55）")
    print(f"  τ_T  ：{np.round(ta,4)}  （真值 0.0800）")
    print(f"  τ_a  ：{np.round(ta_,3)}  （真值 0.700，上界 5.0）")
    if (bT > 2.0).all() and (ta_ > 3.0).all():
        print("  ⇒ **每个数据集都跑到同一个角**（β_T 巨大、τ_a 撞上界）："
              "这是**模型结构性问题**，不是抽样噪声。")
    elif (bT > 2.0).any():
        print("  ⇒ 部分数据集跑到角：结构脆弱 + 抽样噪声共同作用。")
    else:
        print("  ⇒ 未复现：上一份数据是单次抽样特例。")

    print(f"\n总耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
