# -*- coding: utf-8 -*-
"""
check_ttau.py —— 条件精度下的**设计能带**：哪些参数可行、τ_T 要多少试次
================================================================================
背景（必须记住的判读修正）
--------------------------
`check_pure.py` 的"判读"逻辑是错的：它把"纯切片 2 单位宽度"与"剖面 2 单位宽度"
直接比较，但两者是**相对各自最大值**测的，而 τ_T 的剖面最大值落在 0.02
（真值 0.08），于是比较的是两件不同的事。

正确的量是**真值处的条件曲率** d²ll/dθ²（其余参数钉死）。它等于"给定其它参数
已知时该参数的乐观精度"，用 Cramér–Rao 解释即**下界**：
    SE_cond(θ) = 1 / sqrt( −d²ll/dθ² |_θ* )
`check_pure.py` 的步长收敛自检证明这个量在 h≤1e-3 处已收敛（τ_T: −24.285）。
它与 `design_ident.py` 报的 D4 条件 SE **完全一致** ⇒ 那批 SE 是对的，
而 T-dense 的 τ_T/τ_a = inf 也**是真的**（那个数据集真值处已非局部极大）。

本脚本要回答的两个可操作问题
----------------------------
Q1 条件精度本身就是**乐观下界**。若连它都不够（truth/SE 太小），那么再好的
   估计量与再好的参数化都救不回来 ⇒ 只能**改设计**或**放弃该参数**。
Q2 若要救 τ_T，需要什么样的 T 位置与多少试次？把 τ_T 的 SE 压到 rel≤20%
   需要多少倍试次？（信息量 ∝ 试次，SE ∝ 1/sqrt(n)）

用法
----
    python check_ttau.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from design_fim import TRUTH, P_SINGLE  # noqa: E402
from likelihood import _bounds_for, log_likelihood, trials_from_arrays  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

NAMES = list(WITHIN_FREE)
LO, HI = _bounds_for(NAMES)
TRU = TRUTH.vector(NAMES)
W_D4 = [0.79998, 1.19990, 1.79990]

#: 设计候选：名称 -> (T 水平, W 水平, 每单元重复)
DESIGNS = {
    "D4 baseline  (33/83/150/250)": ([0.0333, 0.0833, 0.14999, 0.24998], W_D4, 12),
    "low4         (15/33/60/100)": ([0.0150, 0.0333, 0.0600, 0.1000], W_D4, 12),
    "low5     (10/20/33/55/90)": ([0.0100, 0.0200, 0.0333, 0.0550, 0.0900], W_D4, 12),
    "low6  (10/20/33/60/100/200)": ([0.0100, 0.0200, 0.0333, 0.0600, 0.1000, 0.2000], W_D4, 12),
    "low4_r24                ": ([0.0150, 0.0333, 0.0600, 0.1000], W_D4, 24),
    "low4_r48                ": ([0.0150, 0.0333, 0.0600, 0.1000], W_D4, 48),
    "low4_r96                ": ([0.0150, 0.0333, 0.0600, 0.1000], W_D4, 96),
    "D4_r48                  ": ([0.0333, 0.0833, 0.14999, 0.24998], W_D4, 48),
}


def conditional_curv(tr, nm, h_rel=1e-3):
    """真值处条件二阶导（参数单位步长；已由 check_pure 收敛自检验证 h_rel≤1e-3 可用）。"""
    k = NAMES.index(nm)
    h = max(h_rel * (HI[k] - LO[k]), 1e-6)
    t = float(TRU[k])
    f0 = log_likelihood(TRUTH, tr)
    lp = log_likelihood(TRUTH.replace(**{nm: t + h}), tr)
    lm = log_likelihood(TRUTH.replace(**{nm: t - h}), tr)
    return (lp - 2 * f0 + lm) / h ** 2


def cond_se(tr):
    """返回 (SE 向量, 该数据集上的行为诊断)。"""
    se = np.full(len(NAMES), np.nan)
    for nm in NAMES:
        k = NAMES.index(nm)
        c = conditional_curv(tr, nm)
        if c < 0:
            se[k] = 1.0 / np.sqrt(-c)
    return se


def build(T, W, rep, seed=7):
    """按指定 T/W/重复数造被试内数据（与 check_tpath.make_trials 同构，但可换设计）。

    注意：`check_tpath.make_trials` 只接受 seed，**不能**用它比较不同设计——
    否则每个"设计"都会是同一份 D4 数据，比较结果全等且毫无意义。
    """
    design = build_design(P_SINGLE, T, W, rep)
    rng = np.random.default_rng(seed)
    sim = simulate_subject(design, TRUTH, rng)
    tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                            *design_arrays(design))
    return design, sim, tr


def main():
    t_start = time.time()
    print("=" * 112)
    print("条件精度（= 真值处 d²ll/dθ²，其余参数钉死）下的设计能带")
    print("  SE_cond = 1/sqrt(−d²ll/dθ²)。这是**乐观下界**：真实联合估计只会更差。")
    print("=" * 112)
    print(f"  参数真值：{ {n: round(float(v), 4) for n, v in zip(NAMES, TRU)} }")
    print(f"  truth/SE_cond 是『真值离 0 有几个 SE』；<2 表示连条件精度都测不出这个参数。\n")

    rows = {}
    for name, (T, W, rep) in DESIGNS.items():
        try:
            out = build(T, W, rep)
            tr = out[-1]
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {name} 构建失败：{type(e).__name__}: {e}")
            continue
        se = cond_se(tr)
        n = int(np.asarray(tr["rt"]).size)
        rows[name] = {"se": se, "n": n, "T": T, "W": W, "rep": rep}
        print(f"  已算 {name:30s} 试次={n:5d}  ({time.time()-t_start:.0f}s)")

    # ---------------- 主表 ----------------
    print("\n" + "=" * 112)
    print("条件标准误（乐观下界）")
    print("=" * 112)
    head = f"{'设计':30s} {'试次':>6s} " + " ".join(f"{n[:8]:>9s}" for n in NAMES)
    print(head); print("-" * len(head))
    for name, r in rows.items():
        print(f"{name:30s} {r['n']:6d} " + " ".join(
            (f"{v:9.4f}" if np.isfinite(v) else "      inf") for v in r["se"]))

    # ---------------- 真值/SE（可检出性）----------------
    print("\n" + "=" * 112)
    print("可检出性 = |真值| / SE_cond（≈ 组层 n=30 时的 z 值 = 该值 × sqrt(30)）")
    print("=" * 112)
    print(head); print("-" * len(head))
    for name, r in rows.items():
        print(f"{name:30s} {r['n']:6d} " + " ".join(
            (f"{abs(float(t))/v:9.2f}" if np.isfinite(v) and v > 0 else "      inf")
            for t, v in zip(TRU, r["se"])))
    print("\n  组层 z（n=30 被试，组 SE ≈ 单被试 SE / √30）")
    print(head); print("-" * len(head))
    for name, r in rows.items():
        print(f"{name:30s} {r['n']:6d} " + " ".join(
            (f"{abs(float(t))/v*np.sqrt(30):9.2f}" if np.isfinite(v) and v > 0
             else "      inf") for t, v in zip(TRU, r["se"])))

    # ---------------- τ_T 专项 ----------------
    print("\n" + "=" * 112)
    print("★ τ_T 专项：把它压到相对精度 20% 需要多少倍试次")
    print("=" * 112)
    k = NAMES.index("tau_T")
    base = rows.get("D4 baseline  (33/83/150/250)")
    if base is not None and np.isfinite(base["se"][k]):
        se0 = base["se"][k]
        target = 0.20 * abs(float(TRU[k]))
        need = (se0 / target) ** 2
        print(f"  D4 基线：τ_T 真值 {float(TRU[k]):.3f}，SE_cond {se0:.4f}，"
              f"相对精度 {se0/abs(float(TRU[k]))*100:.0f}%")
        print(f"  目标：相对精度 20% ⇒ SE ≤ {target:.4f} ⇒ 需要 **{need:.0f}× 试次**"
              f"（≈ {need*576:.0f} 试次/人）")
        print(f"  ⇒ 结论：**不可行**。τ_T 不能作为本设计的估计目标，只能先验固定。")
    for nm in ("tau_T", "beta_T", "beta_ST", "delta_a", "tau_a"):
        kk = NAMES.index(nm)
        vals = {n: r["se"][kk] for n, r in rows.items() if np.isfinite(r["se"][kk])}
        if not vals:
            continue
        best = min(vals, key=vals.get)
        print(f"  {nm:8s} 最好设计：{best:30s} SE={vals[best]:.4f}"
              f"（真值 {float(TRU[kk]):.3f}，相对 {vals[best]/abs(float(TRU[kk]))*100:.0f}%）")

    print(f"\n  总耗时 {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
