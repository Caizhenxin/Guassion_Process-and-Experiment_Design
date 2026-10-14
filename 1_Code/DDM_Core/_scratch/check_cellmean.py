"""单元均值（cell-mean）参数化的敏感性分析：线性限制值多少代价？

用法：``python _scratch/check_cellmean.py [被试数]``（默认 24）
日志：``_scratch/check_cellmean_u8.txt``

## 为什么做这个

`Stage4_识别性结论与设计处方.md` §4.1 第 2 条把「单元均值参数化」列为**防御性备选**：
若审稿人质疑「你凭什么假设漂移随 T 线性、边界随 W 线性」，
就用一个**不做函数形式假设**的参数化重做一遍。本脚本就是执行这件事。

## 两个臂，而且第二个才是关键

⚠️ **第一版只跑了臂 A，那是个循环论证**：臂 A 的数据是用 `lin` 真值生成的，
再用 `lin` 去拟合当然拟合得最好。所以必须加臂 B。

* **臂 A：数据由 `lin` 真值生成。**（循环，但仍有信息）
  答案预设为「自由形式不必要」。作为对照，它量化了「在真值真的线性时，
  多花 7 个自由度能买到多少拟合」——答案是几乎买不到。
* **臂 B：数据由 `exp` 真值生成。**（**非循环，这是真正的问题**）
  `exp` 的 T 通道是饱和曲线、W 通道也是曲线，**不是直线**。
  这正是审稿人担心的情形：真值弯曲，而我们强行拟合直线。
  - `cell` 是**饱和**参数化（每个 T 水平一个自由漂移、每个 W 水平一个自由边界），
    所以它**能精确表示 exp 真值**——它的估计就是「经验剖面」本身。
  - `lin` 被限制成直线，偏差 = exp 剖面相对自己最佳直线的残差。
  - 判据：`lin` 的偏差相对于**组层 SE** 有多大。若 ≲ 1 SE，
    线性近似就是「在噪声内无法区分」，可以照用。

## 判据汇总

1. **自检**：``cell_from_lin(TRUTH)`` 与 ``TRUTH`` 必须逐试次同似然（两种写法）。
2. **剖面**：真值 vs `lin` 隐含 vs `cell` 直接估计，逐水平比较，带组层 SE。
3. **拟合优度**：逐被试 BIC（`lin` k=7、`cell` k=14）。`cell` 参数多一倍，
   「拟合更好」是默认预期，只有 BIC 仍偏向它才算证据。
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cellmean as cm
from likelihood import fit_mle, per_trial_loglik, trials_from_arrays
from mapping import (PARAM_BOUNDS, WITHIN_FREE_LIN, boundary_a,
                     drift_magnitude, match_lin_to_exp)
from simulate import build_design, design_arrays, simulate_subject
from twophase import bic
import mapping as _mp

P_FIXED = 120.0
T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
T_REF = 0.10
W_REF = 1.20
TAU_P_PRIOR = 30.0
T0_EPS = 0.005
BASE_SEED = 20261013

TRUTH_EXP = _mp.MappingParams(
    P_ref=P_FIXED, T_ref=T_REF, W_ref=W_REF, shape_model="exp",
    d_ref=0.70, beta_P=0.35, tau_P=TAU_P_PRIOR,
    beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)
TRUTH_LIN, LIN_REPORT = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)
TRUTH_LIN = TRUTH_LIN.replace(tau_P=TAU_P_PRIOR)

INIT_EXP = _mp.MappingParams(
    P_ref=P_FIXED, T_ref=T_REF, W_ref=W_REF, shape_model="exp",
    d_ref=0.50, beta_P=0.35, tau_P=TAU_P_PRIOR,
    beta_T=0.90, tau_T=0.150, beta_S=0.30, beta_SP=0.0, beta_ST=0.00,
    w_model="W1", a_ref=1.60, delta_a=0.10, tau_a=0.50,
    t0=0.25, z_ratio=0.50,
)
INIT_LIN, _ = match_lin_to_exp(INIT_EXP, T_LEVELS, W_LEVELS)
INIT_LIN = INIT_LIN.replace(tau_P=TAU_P_PRIOR)

cm.set_levels(T_LEVELS, W_LEVELS)

LOG_LINES: list[str] = []


def out(s: str = "") -> None:
    print(s, flush=True)
    LOG_LINES.append(s)


# ------------------------------------------------------------------
# 两种写法之间的精确换算
# ------------------------------------------------------------------
def cell_from_lin(p) -> cm.CellParams:
    """把任意形状参数严格重写成（参考水平编码的）单元均值参数。

    ⚠️ **参考水平的约定**（2026-10-14 被自检抓到过一次错）：``beta_S`` 定义为
    **T 水平 0 处的自我效应** ``self(T_0) − other(T_0)``，而不是原参数的
    ``beta_S``。理由：``dt_0 = st_0 = 0`` 是参考水平编码的**记法**约定，
    它要求参考单元的整体水平由 ``d_ref``/``beta_S`` 吸收；若直接把原
    ``beta_S`` 搬过来，参考单元的自我效应就丢掉了
    ``beta_ST·(T_0 − T_ref)``（此处 = 0.2693 × (−0.0667) = −0.0180），
    自检立刻报出 1.8e-2 的偏差。
    """
    d0 = float(drift_magnitude([P_FIXED], [T_LEVELS[0]], [0.0], p)[0])
    s0 = float(drift_magnitude([P_FIXED], [T_LEVELS[0]], [1.0], p)[0])
    a0 = float(boundary_a([W_LEVELS[0]], p)[0])

    beta_s_ref = s0 - d0
    kw = dict(d_ref=d0, a_ref=a0, beta_S=beta_s_ref,
              beta_P=float(p.beta_P), beta_SP=float(p.beta_SP),
              t0=float(p.t0), T_ref=float(p.T_ref), P_ref=float(p.P_ref),
              tau_P=float(getattr(p, "tau_P", TAU_P_PRIOR)))
    for i in range(1, len(T_LEVELS)):
        di = float(drift_magnitude([P_FIXED], [T_LEVELS[i]], [0.0], p)[0])
        si = float(drift_magnitude([P_FIXED], [T_LEVELS[i]], [1.0], p)[0])
        kw[f"dt_{i}"] = di - d0
        kw[f"st_{i}"] = (si - di) - beta_s_ref
    for j in range(1, len(W_LEVELS)):
        aj = float(boundary_a([W_LEVELS[j]], p)[0])
        kw[f"dw_{j}"] = aj - a0
    return cm.CellParams(**kw)


def lin_profile(p, self_flag: float) -> np.ndarray:
    return np.array([float(drift_magnitude([P_FIXED], [t], [self_flag], p)[0])
                     for t in T_LEVELS])


def lin_aprof(p) -> np.ndarray:
    return np.array([float(boundary_a([w], p)[0]) for w in W_LEVELS])


def best_line_resid(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    coef = np.polyfit(x, y, 1)
    r = y - np.polyval(coef, x)
    return float(coef[0]), float(np.max(np.abs(r)))


# ------------------------------------------------------------------
def run_arm(label: str, truth, n_subj: int, design) -> dict:
    """一个臂：用 ``truth`` 生成数据，分别用 lin 与 cell-mean 拟合。"""
    P_arr, T_arr, W_arr, is_self, is_match = design_arrays(design)
    n_trials = int(P_arr.size)

    t_other, t_self, t_a = (lin_profile(truth, 0.0), lin_profile(truth, 1.0),
                            lin_aprof(truth))
    xT = np.array(T_LEVELS) - T_REF
    xW = np.array(W_LEVELS) - W_REF
    _, r_other = best_line_resid(xT, t_other)
    _, r_a = best_line_resid(xW, t_a)

    out("=" * 104)
    out(f"臂 {label}")
    out("=" * 104)
    out(f"生成真值形状：{truth.shape_model}；被试数 n = {n_subj}；D4 = {n_trials} 试次/被试")
    out(f"真值剖面自身的非线性程度（相对自己最佳直线的最大残差）："
        f"非自我 d(T) {r_other:.4f}（占跨度的 "
        f"{r_other / (t_other.max() - t_other.min()):.1%}）、"
        f"边界 a(W) {r_a:.4f}（占跨度的 {r_a / (t_a.max() - t_a.min()):.1%}）")
    out()

    rows = []
    for s in range(n_subj):
        rng = np.random.default_rng(BASE_SEED + s)
        sim = simulate_subject(design, truth, rng)
        tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                *design_arrays(design))
        t0_cap = float(np.nanmin(sim["rt"])) - T0_EPS
        ov = {"t0": (PARAM_BOUNDS["t0"][0],
                     min(PARAM_BOUNDS["t0"][1], max(t0_cap, 0.06)))}
        ov_cell = {"t0": (cm.CELL_BOUNDS["t0"][0],
                          min(cm.CELL_BOUNDS["t0"][1], max(t0_cap, 0.06)))}

        t_a0 = time.time()
        f_lin = fit_mle(tr, list(WITHIN_FREE_LIN), INIT_LIN, n_restart=2,
                        seed=1000 + s, maxiter=250, maxfun=6000,
                        bounds_override=ov, gtol=1e-8, ftol=1e-12)
        dt_lin = time.time() - t_a0
        t_a0 = time.time()
        f_cell = cm.fit_mle_cell(tr, cell_from_lin(INIT_LIN), n_restart=2,
                                 seed=2000 + s, maxiter=250, maxfun=8000,
                                 bounds_override=ov_cell, gtol=1e-8, ftol=1e-12)
        dt_cell = time.time() - t_a0

        rows.append(dict(
            llin=f_lin["loglik"], lcell=f_cell["loglik"],
            lin_other=lin_profile(f_lin["params"], 0.0),
            lin_self=lin_profile(f_lin["params"], 1.0),
            lin_a=lin_aprof(f_lin["params"]),
            cell_other=cm.drift_profile(f_cell["params"])[0],
            cell_self=cm.drift_profile(f_cell["params"])[1],
            cell_a=cm.boundary_profile(f_cell["params"]),
            beta_T=float(f_lin["params"].beta_T),
            delta_a=float(f_lin["params"].delta_a),
            sec_lin=dt_lin, sec_cell=dt_cell,
            ok=bool(f_lin["x"] is not None and f_cell["x"] is not None),
        ))

    def stack(key):
        return np.array([r[key] for r in rows], dtype=float)

    # ---------- 剖面对照 ----------
    out("-" * 104)
    out("经验剖面：真值 vs lin 隐含 vs cell-mean 直接估计（组层均值 ± 组层 SE = 组间 SD/√n）")
    out("-" * 104)
    se_cache = {}
    for title, kl, kc, truth_v, lvls, scale in (
        ("非自我漂移 d(T)", "lin_other", "cell_other", t_other, T_LEVELS, 1000.0),
        ("自我漂移   d(T)", "lin_self", "cell_self", t_self, T_LEVELS, 1000.0),
        ("边界       a(W)", "lin_a", "cell_a", t_a, W_LEVELS, 1.0),
    ):
        A, B = stack(kl), stack(kc)
        seA = A.std(ddof=1, axis=0) / np.sqrt(n_subj)
        seB = B.std(ddof=1, axis=0) / np.sqrt(n_subj)
        se_cache[title] = (A.mean(axis=0), seA, B.mean(axis=0), seB, truth_v)
        out()
        out(f"  {title}")
        out(f"     {'水平':>9s} {'真值':>9s} {'lin':>9s} {'±SE':>7s} {'cell':>9s} "
            f"{'±SE':>7s} {'lin-cell':>9s} {'/SE':>5s} {'lin-真值':>9s} {'cell-真值':>10s}")
        for i in range(len(lvls)):
            lv = lvls[i] * scale
            comb = np.sqrt(seA[i] ** 2 + seB[i] ** 2)
            out(f"     {lv:>9.2f} {truth_v[i]:>9.4f} {A[:, i].mean():>9.4f} "
                f"{seA[i]:>7.4f} {B[:, i].mean():>9.4f} {seB[i]:>7.4f} "
                f"{A[:, i].mean() - B[:, i].mean():>+9.4f} "
                f"{abs(A[:, i].mean() - B[:, i].mean()) / comb:>5.1f} "
                f"{A[:, i].mean() - truth_v[i]:>+9.4f} {B[:, i].mean() - truth_v[i]:>+10.4f}")
    out()

    # ---------- 线性限制的代价 ----------
    lin_bT = float(np.mean([r["beta_T"] for r in rows]))
    lin_da = float(np.mean([r["delta_a"] for r in rows]))
    cell_other_m = stack("cell_other").mean(axis=0)
    cell_a_m = stack("cell_a").mean(axis=0)
    bt_free, res_T = best_line_resid(xT, cell_other_m)
    da_free, res_W = best_line_resid(xW, cell_a_m)

    out("-" * 104)
    out("线性限制的代价")
    out("-" * 104)
    out(f"   beta_T ：lin 估计 {lin_bT:>8.4f}   真值 {truth.beta_T if truth.shape_model == 'lin' else float('nan'):>8.4f}   "
        f"自由剖面等效斜率 {bt_free:>8.4f}   |lin − 自由| = {abs(lin_bT - bt_free):.4f}"
        f"（{abs(lin_bT - bt_free) / abs(bt_free):.1%}）")
    out(f"   delta_a：lin 估计 {lin_da:>8.4f}   真值 {truth.delta_a:>8.4f}   "
        f"自由剖面等效斜率 {da_free:>8.4f}   |lin − 自由| = {abs(lin_da - da_free):.4f}"
        f"（{abs(lin_da - da_free) / abs(da_free):.1%}）")
    out(f"   自由剖面偏离自身最佳直线的最大残差：T 通道 {res_T:.4f}"
        f"（占漂移跨度的 {res_T / (cell_other_m.max() - cell_other_m.min()):.1%}）、"
        f"W 通道 {res_W:.4f}（占边界跨度的 {res_W / (cell_a_m.max() - cell_a_m.min()):.1%}）")
    out()

    # ---------- 拟合优度 ----------
    ll_l = np.array([r["llin"] for r in rows])
    ll_c = np.array([r["lcell"] for r in rows])
    bic_l = np.array([bic(v, 7, n_trials) for v in ll_l])
    bic_c = np.array([bic(v, cm.N_CELL_FREE, n_trials) for v in ll_c])
    out("-" * 104)
    out(f"拟合优度（逐被试，n = {n_trials} 试次）")
    out("-" * 104)
    out(f"   lin  k=7 ：Σll = {ll_l.sum():>12.3f}   BIC 均值 = {bic_l.mean():>10.3f}")
    out(f"   cell k={cm.N_CELL_FREE:>2d}：Σll = {ll_c.sum():>12.3f}   BIC 均值 = {bic_c.mean():>10.3f}")
    out(f"   Δll（cell − lin）= {ll_c.sum() - ll_l.sum():+.3f}（每被试平均 "
        f"{np.mean(ll_c - ll_l):+.3f}）；ΔBIC = {bic_c.mean() - bic_l.mean():+.3f}"
        f"（自由度惩罚 {(cm.N_CELL_FREE - 7) * np.log(n_trials):.1f}）")
    out(f"   cell-mean 按 BIC 胜出被试数 = {int(np.sum(bic_c < bic_l))} / {n_subj}")
    out(f"   平均耗时：lin {np.mean([r['sec_lin'] for r in rows]):.2f} s、"
        f"cell {np.mean([r['sec_cell'] for r in rows]):.2f} s")
    out()

    return dict(label=label, rows=rows, se=se_cache,
                truth=(t_other, t_self, t_a), bic_l=bic_l, bic_c=bic_c,
                ll_l=ll_l, ll_c=ll_c, n_subj=n_subj, n_trials=n_trials)


# ------------------------------------------------------------------
def main() -> int:
    n_subj = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    design = build_design(P_FIXED, T_LEVELS, W_LEVELS, N_REP)

    out("=" * 104)
    out("单元均值（cell-mean）参数化的敏感性分析")
    out("=" * 104)
    out(f"设计 D4：{len(T_LEVELS)} T × {len(W_LEVELS)} W × 2 self × 2 match × {N_REP} rep "
        f"= {int(design_arrays(design)[0].size)} 试次/被试；被试数 n = {n_subj}")
    out(f"tau_P 先验固定为 {TAU_P_PRIOR}（D31）；lin k=7，cell-mean k={cm.N_CELL_FREE}")
    out(f"lin→exp 行为匹配质量：漂移跨度恢复 "
        f"{LIN_REPORT['d_span_lin'] / LIN_REPORT['d_span_exp']:.3%}、"
        f"边界跨度恢复 {LIN_REPORT['a_span_lin'] / LIN_REPORT['a_span_exp']:.3%}")
    out()

    # ---------- 0. 自检 ----------
    rng0 = np.random.default_rng(12345)
    sim0 = simulate_subject(design, TRUTH_LIN, rng0)
    tr0 = trials_from_arrays(sim0["rt"], sim0["side"], sim0["omission"],
                             *design_arrays(design))
    ll_lin = per_trial_loglik(TRUTH_LIN, tr0)
    ll_cell = cm.per_trial_loglik_cell(cell_from_lin(TRUTH_LIN), tr0)
    ok = ll_lin is not None and ll_cell is not None
    dmax = float(np.max(np.abs(ll_lin - ll_cell))) if ok else float("nan")
    out("-" * 104)
    out("0. 自检：cell_from_lin(TRUTH) 与 TRUTH 是否逐试次同似然（两种写法必须等价）")
    out("-" * 104)
    out(f"   逐试次对数似然最大绝对差 = {dmax:.3e}   "
        f"（判据 < 1e-9；{'✅ 通过' if ok and dmax < 1e-9 else '❌ 未通过'}）")
    if not (ok and dmax < 1e-9):
        out("   ❌ 实现不一致，后续数字不可用。")
        return 1
    out()

    armA = run_arm("A：数据由 lin 真值生成（循环对照）", TRUTH_LIN, n_subj, design)
    armB = run_arm("B：数据由 exp 真值生成（非循环，关键臂）", TRUTH_EXP, n_subj, design)

    # ---------- 汇总读法 ----------
    out("=" * 104)
    out("汇总读法")
    out("=" * 104)
    for arm in (armA, armB):
        t_other = arm["truth"][0]
        A, seA, B, seB, _ = arm["se"]["非自我漂移 d(T)"]
        dev = np.abs(A - t_other) / seA
        out(f"   * 臂 {arm['label'][0]}（真值形状 {'lin' if arm is armA else 'exp'}）："
            f"lin 隐含的非自我 d(T) 相对真值的偏差 = "
            f"{np.array2string(A - t_other, precision=4)}，"
            f"折合 {np.array2string(dev, precision=2)} × SE（最大 {dev.max():.1f} SE）；"
            f"BIC 偏向 lin 的被试数 = {int(np.sum(arm['bic_l'] < arm['bic_c']))}/{arm['n_subj']}")
    out()
    out("   判据：")
    out("   * 自检通过 ⇒ cellmean.py 与 lin 是同一剖面的两种写法，剖面差异来自数据与估计。")
    out("   * 臂 A：真值本来就线性，自由形式按 BIC 胜出 0 次 ⇒ **线性限制买不到拟合**，")
    out("     这是「不需要更复杂模型」的对照证据（但它循环，不能单独用）。")
    out("   * 臂 B：真值确实弯曲（见臂 B 开头的非线性程度）。若 lin 隐含剖面的偏差")
    out("     **≲ 1–2 × 组层 SE**，则线性近似在噪声内无法与饱和曲线区分 ⇒")
    out("     §4.1 的可识别性结论与 D22 可以照写，论文只需在稳健性小节列出臂 B 的这张表。")
    out("   * ⚠️ 这是**模拟数据**结论：真值是已知的 `exp`/`lin` 形状。")
    out("     真实数据的剖面形状若偏离这两个家族，本节的保证不自动延伸。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
