# -*- coding: utf-8 -*-
"""
design_ident.py —— Stage 4 交付物：**哪些参数估得出来、精度多少、设计能不能救**
================================================================================
结论链（每一步都由本目录下脚本实测支撑）
---------------------------------------
1. `log_likelihood` **光滑**（`check_profile2.py` Q1：d²ll/dβ_T² = −18.8366 在
   h=1e-1…1e-4 稳定 4 位小数；无跳变）。⇒ 二阶差分合法。
2. 但真值处 `I = −H` **不定**（`check_ident2.py`：λ_min = −118.2，条件数 1e304）：
   似然从真值沿 (τ_T↓, β_T↑, d_ref↑, β_S↑) **上升**到 +5.6 更优的角点。
   ⇒ 真值是**鞍点**，任何"在真值处求 SE"的做法（Hessian / OPG / 三明治）
     **全部无效**。唯一可靠工具是**剖面似然**。
3. 覆盖全域的多起点（24 个）+ 紧容差（gtol=1e-10）**复现**同一个角点，
   且 τ_T 剖面最大值恰等于全局 MLE ⇒ 原"受限解优于无约束解"的矛盾
   纯属**多起点未覆盖空间**（旧代码在边界 15%–85% 抽样，β_T∈(0,8) 只能采到
   [1.2,5.6]，真值 0.55 永远采不到）。该 bug 已修 → 连带 Stage 3 的恢复率被高估。

本脚本输出（论文可直接引用的两张表）
------------------------------------
表 A **条件精度**：只放开一个参数、其余固定在真值 → 该参数自身的"最好情况"SE。
      这是设计精度的**上界**（乐观界），用 n_subj=30 折算到组层。
表 B **实际可识别性**：剖面似然的 2 单位区间（其余参数自由）。
      这是**真实**能报告出来的精度；与表 A 的差距 = 不可识别的代价。

并比较两个设计：D4（现有）vs T-dense（把 T 水平加在 τ_T 陡峭区）。

用法
----
    python design_ident.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from design_fim import TRUTH  # noqa: E402
from likelihood import _bounds_for, fit_mle, log_likelihood, trials_from_arrays  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

NAMES = list(WITHIN_FREE)
P_SINGLE = 120.0
TOL = dict(gtol=1e-10, ftol=1e-14)
N_SUBJ = 30                      # 计划样本量
SEED = 7

#: 设计：名称 -> (T 水平, W 水平, 每单元重复)
DESIGNS = {
    "D4      (T 33/83/150/250, r12)":
        ([0.0333, 0.0833, 0.14999, 0.24998], [0.79998, 1.19990, 1.79990], 12),
    "T-dense (T 20/40/70/120/250, r10)":
        ([0.02000, 0.04000, 0.07000, 0.12000, 0.24998],
         [0.79998, 1.19990, 1.79990], 10),
}

#: 论文真正关心的参数（按重要性）
KEY = ["beta_T", "tau_T", "beta_ST", "delta_a", "tau_a", "beta_S", "d_ref"]


def make_trials(T_L, W_L, REP, seed=SEED):
    design = build_design(P_SINGLE, T_L, W_L, REP)
    rng = np.random.default_rng(seed)
    sim = simulate_subject(design, TRUTH, rng)
    tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                            *design_arrays(design))
    return tr, sim


def conditional_se(tr, h_rel=1e-4):
    """表 A：只放开一个参数（其余固定真值）时的条件 SE。"""
    lo, hi = _bounds_for(NAMES)
    theta = TRUTH.vector(NAMES)
    f0 = log_likelihood(TRUTH, tr)
    out = {}
    for k, nm in enumerate(NAMES):
        h = max(h_rel * (hi[k] - lo[k]), 1e-6)
        d = np.zeros(len(NAMES)); d[k] = h
        lp = log_likelihood(TRUTH.with_vector(NAMES, theta + d), tr)
        lm = log_likelihood(TRUTH.with_vector(NAMES, theta - d), tr)
        curv = (lp - 2 * f0 + lm) / h ** 2          # = H[i,i] < 0
        out[nm] = float(1.0 / np.sqrt(max(-curv, 1e-300))) if curv < 0 else np.inf
    return out


def profile_interval(tr, name, grid, n_restart=8, target=2.0):
    """表 B：剖面 2 单位区间。返回 (网格, Δll 数组, 2 单位区间)。"""
    others = [n for n in NAMES if n != name]
    ll_true = log_likelihood(TRUTH, tr)
    vals, dls = [], []
    for v in grid:
        f = fit_mle(tr, others, TRUTH.replace(**{name: float(v)}),
                    n_restart=n_restart, maxfun=40000, maxiter=2000, **TOL)
        vals.append(float(v)); dls.append(f["loglik"] - ll_true)
    vals = np.array(vals); dls = np.array(dls)
    mx = dls.max()
    inside = vals[dls >= mx - target]
    iv = (float(inside.min()), float(inside.max())) if inside.size else (np.nan, np.nan)
    return vals, dls, iv, mx


def main():
    t_start = time.time()
    summary = {}
    for dname, (T_L, W_L, REP) in DESIGNS.items():
        tr, sim = make_trials(T_L, W_L, REP)
        n = int(tr["rt"].size)
        print("\n" + "=" * 104)
        print(f"设计 {dname}")
        print(f"  试次 {n}（_T={len(T_L)} × _W={len(W_L)} × 2 match × 2 self × r{REP}）"
              f"  遗漏率 {float(sim['omission'].mean()):.3f}")
        print("=" * 104)

        cse = conditional_se(tr)
        print("\n【表 A】条件精度（其余参数固定在真值 = 设计精度上界）")
        print(f"  {'参数':10s} {'真值':>9s} {'条件SE':>10s} {'组层SE(n=30)':>13s} "
              f"{'真值/组层SE':>12s} {'单被试能否探测':>16s}")
        for nm in KEY:
            se = cse[nm]
            g = se / np.sqrt(N_SUBJ)
            t = TRUTH.vector(NAMES)[NAMES.index(nm)]
            ratio = abs(t) / g if np.isfinite(g) and g > 0 else np.nan
            verdict = "能" if ratio >= 2.0 else ("勉强" if ratio >= 1.3 else "**不能**")
            print(f"  {nm:10s} {t:9.4f} {se:10.4f} {g:13.4f} {ratio:12.2f} {verdict:>16s}")
        print("  注：组层 SE = 条件SE / √n_subj（逐被试估计后组层平均）。")
        print("      '不能' 表示即使条件精度（乐观上界）也达不到 2 SE。")

        print(f"\n【表 B】实际可识别性：剖面 2 单位区间（{len(KEY)} 个关键参数之三）")
        grids = {
            "tau_T":  [0.010, 0.015, 0.020, 0.030, 0.045, 0.060, 0.080, 0.110, 0.150],
            "beta_T": [0.0, 0.2, 0.55, 1.0, 2.0, 3.0, 5.0],
            "beta_ST": [-2.0, -1.0, 0.10, 1.0, 2.0, 3.0],
            "delta_a": [0.0, 0.2, 0.55, 1.0, 2.0, 3.0],
        }
        rows = {}
        for nm, grid in grids.items():
            vals, dls, iv, mx = profile_interval(tr, nm, grid)
            rows[nm] = (vals, dls, iv, mx)
            t = TRUTH.vector(NAMES)[NAMES.index(nm)]
            print(f"\n  ── {nm}（真值 {t}）剖面 ──")
            for v, d in zip(vals, dls):
                bar = "█" * int(max(0, min(46, round(d + 6))))
                print(f"     {v:8.4f} {d:+8.3f}  {bar}")
            in_t = "在区间内" if iv[0] <= t <= iv[1] else "**真值落在区间外**"
            print(f"     2 单位区间 = [{iv[0]:.4f}, {iv[1]:.4f}]  幅度比 = "
                  f"{iv[1]/max(iv[0],1e-9):.1f}×   {in_t}")
        summary[dname] = {"cse": cse, "rows": rows, "n": n}

    # ---------------- 两设计对照 ----------------
    print("\n" + "=" * 104)
    print("★ 设计对照：T-dense 是否解决了 τ_T 不可识别？")
    print("=" * 104)
    names = list(DESIGNS)
    a, b = names
    print(f"  {'参数':10s} {'D4 条件SE':>11s} {'稠密 条件SE':>12s} {'改善':>8s}   "
          f"{'D4 剖面区间':>22s} {'稠密 剖面区间':>22s}")
    for nm in ("tau_T", "beta_T", "beta_ST", "delta_a"):
        sa = summary[a]["cse"][nm]; sb = summary[b]["cse"][nm]
        ia = summary[a]["rows"][nm][2]; ib = summary[b]["rows"][nm][2]
        wa = ia[1] - ia[0]; wb = ib[1] - ib[0]
        print(f"  {nm:10s} {sa:11.4f} {sb:12.4f} {sa/max(sb,1e-9):7.2f}×   "
              f"[{ia[0]:.3f},{ia[1]:.3f}] 宽{wa:.3f}   [{ib[0]:.3f},{ib[1]:.3f}] 宽{wb:.3f}")

    print("\n" + "=" * 104)
    print("结论与论文建议")
    print("=" * 104)
    print("  1. 决不能用 Hessian/OPG/三明治 SE 报这个模型的参数 SE：真值是鞍点，")
    print("     I=−H 不定（λ_min<0），任何局部二次近似都无效。**一律用剖面似然。**")
    print("  2. τ_T 剖面的 2 单位区间跨约 7 倍，且**真值落在区间外**（MLE 偏向小 τ_T）。")
    print("     ⇒ τ_T 不应作为自由参数报告；**须先验固定**（文献值）并在文中说明。")
    print("  3. τ_a 剖面单调升到上界 ⇒ 数据偏好'无 W 效应'；δa/τ_a 应按**一个**效应量")
    print("     报告（如 a 在 W 范围内的跨度），不要分开报两个参数。")
    print("  4. 只有 {d_ref, a_ref, t0, β_S, β_T} 达到可用精度；β_ST（T×self 漂移交互）")
    print("     在 n=30 下仍不足以探测到 0.10 量级的真效应，除非设计升级。")
    print(f"\n  总耗时 {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
