# -*- coding: utf-8 -*-
"""check_mt2_window.py —— Stage 5：M-T2（斜坡）支腿的**前置问题**

**为什么要先问这个，而不是直接实现 M-T2**
`twophase.py` 的 docstring（L13）与 `正式采集_候选设计.md` §1 把 M-T2 写成
``d(t) = d₀ + β_T(1 − e^{−t/τ_T})``（``t ≤ T``），并说它的**可观测签名**是
「即使 ``RT < T``，RT 分布也随 T 变化（斜坡被截断）」。M-T1 的签名则是
「``RT < T`` 的试次，其 RT 分布与 T 无关」。

⇒ **两个模型的干净签名都只在 ``RT < T`` 的试次上。** 所以在写任何新似然之前，
必须先问一个**纯算术**问题：**D4 里到底有多少 ``RT < T`` 的试次？**
若这个数字接近 0，M-T2 支腿再怎么写也无法识别——缺口应当用**论证**关闭，
而不是用代码关闭。

★★ 钟点约定：本项目已被这个坑绊过一次（D33 记录过 ``P(RT<T)`` 与 ``P(τ<T)`` 的混同）。
   * ``twophase.per_trial_loglik_step`` 用 ``t = rt − t0`` 与 ``T`` 比较 ⇒
     模型内部**相位切换发生在决策时间 ``τ = T``**，相位项**不含** ``t0``。
   * 但实验里**可观测**的是「刺激呈现期内按键」，其条件是 ``RT < T``。因为
     ``RT = τ + t0``，这等于 ``τ < T − t0`` ⇒ **比相位切换早整整一个 ``t0``**。
   本脚本对每个 T 水平同时打印这两个量，并给出**两个读数**：
     * **读数 A（模型现状）**：相位窗口 = ``T``，可观测窗口 = ``T − t0``；
     * **读数 B（实验字面）**：掩蔽在绝对时刻 ``T`` 落下 ⇒ 相位窗口 = ``T − t0``，
       可观测窗口 = ``T − 2·t0``。
   两个读数下「可观测的刺激期内按键」都极少，但读数 B 更糟：三个低 T 水平下
   ``T − t0 < 0``，即**掩蔽早于累积开始**，T 操作在物理上塌缩。

用到的全部是**已验收**的解析机器（`wfpt.survival_series` / `wfpt.survival_step`），
**不引入任何新模型**。

判据（**运行前写死**，事后不得改）：
  * 若 ``E[#(RT < T)]`` 每人 **≥ 40 试次**（≈7%）⇒ M-T2 有足够原始试次，
    值得实现完整似然；
  * **10–40** ⇒ 只值得做 M-T1 vs M-T2 的**单侧**版本；
  * **< 10** ⇒ M-T2 在 D4 下**不可识别**，缺口应写进论文而不是靠代码关闭。

并回答一个**可操作**的追问：要让 ``E[#(RT < T)]`` 达到 40 / 10，T 至少要多大？

用法：``python _scratch/check_mt2_window.py [输出路径]``
      给了输出路径就由脚本自己以 UTF-8 写日志（避免 PowerShell ``>`` 的 UTF-16LE 陷阱）。
"""
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


if len(sys.argv) > 1:
    _out = Path(sys.argv[1])
    if not _out.is_absolute():
        _out = _HERE.parent / _out
    _out.parent.mkdir(parents=True, exist_ok=True)
    _fh = open(_out, "w", encoding="utf-8", newline="\n")
    sys.stdout = _Tee(sys.stdout, _fh)

from mapping import MappingParams, match_lin_to_exp, trial_params
from simulate import build_design, design_arrays
from wfpt import survival_series, survival_step

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
P_LEVELS = [0.0, 8.0, 32.0, 120.0]

#: 与 `check_rho_power.py` / `recover_group.py` 完全相同的真值族
TRUTH_EXP = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70, t0=0.22,
    z_ratio=0.50, shape_model="exp")
TRUTH_LIN, _ = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)

RHO_LIST = [0.0, 0.5, 1.0]

#: 运行前写死的判据阈值（每人 RT<T 的期望试次数）
CUT_IMPLEMENT = 40.0
CUT_ONE_SIDED = 10.0

#: T 扫描上界（找「要让 RT<T 变得可观测，T 需要多大」）
T_SCAN = np.linspace(0.05, 2.50, 246)

print("=" * 104)
print("Stage 5｜M-T2（斜坡）支腿的前置问题：D4 里有多少「刺激呈现期内按键」的试次？")
print("=" * 104)
print("M-T1 的签名 = 「RT<T 的试次，RT 分布与 T 无关」")
print("M-T2 的签名 = 「即使 RT<T，RT 分布也随 T 变化（斜坡被截断）」")
print("⇒ 两个签名都只在 **RT < T** 的试次上 ⇒ 先数这类试次有多少。")
print()
print("钟点约定：模型相位切换在 τ = T（`t = rt − t0` 与 T 比较）；")
print("          可观测按键的条件是 RT < T ⟺ τ < T − t0 ⇒ 差一个 t0。")
print()

DESIGN = build_design(120.0, T_LEVELS, W_LEVELS, N_REP)
N_TOTAL = int(DESIGN["T"].size)
ARRAYS = design_arrays(DESIGN)


def _counts(tp, T_col, W_col, rho, need_mean_rt=True):
    """返回 (E[#(τ<T)], E[#(RT<T)], E[#作答], 平均RT, 逐试次 S 信息)。"""
    v = np.asarray(tp["v"], dtype=float)
    a = np.asarray(tp["a"], dtype=float)
    z = np.asarray(tp["z"], dtype=float)
    t0 = np.asarray(tp["t0"], dtype=float)
    t0s = float(np.mean(t0))

    # --- 模型内部的相位窗口：P(τ < T) = 1 − S(T) ---
    p_tau = 1.0 - survival_series(v, a, z, T_col)

    # --- 可观测的刺激期内按键：P(RT < T) = P(τ < T − t0) ---
    x_obs = T_col - t0
    s_obs = np.where(x_obs > 0, survival_series(v, a, z, np.maximum(x_obs, 1e-9)), 1.0)
    p_obs = np.where(x_obs > 0, 1.0 - s_obs, 0.0)

    # --- 作答概率（M-T1 两阶段存活），逐 (v,a,z,T,W) 组 ---
    key = np.column_stack([v, a, z, T_col, W_col])
    uniq = np.unique(np.round(key, 10), axis=0)
    p_respond = np.zeros(N_TOTAL)
    mean_rt = np.full(N_TOTAL, np.nan)
    grid = np.linspace(1e-4, float(np.max(W_col)), 3000)
    for row in uniq:
        vv, aa, zz, tT, ww = (float(x) for x in row)
        m = (np.abs(v - vv) < 1e-9) & (np.abs(a - aa) < 1e-9) & \
            (np.abs(z - zz) < 1e-9) & (np.abs(T_col - tT) < 1e-12) & \
            (np.abs(W_col - ww) < 1e-12)
        tm = ww - t0s
        if tm <= 0:
            p_respond[m] = 0.0
            continue
        p_respond[m] = 1.0 - float(survival_step(vv, rho * vv, aa, zz, tT, tm))
        if need_mean_rt:
            g = grid[grid <= tm]
            S = survival_step(vv, rho * vv, aa, zz, tT, g, n_x=81)
            mean_rt[m] = t0s + float(np.trapezoid(np.atleast_1d(S), g))
    return p_tau, p_obs, p_respond, mean_rt, t0s


for p_name, TRUTH in (("lin 真值", TRUTH_LIN), ("exp 真值", TRUTH_EXP)):
    tp = trial_params(DESIGN, TRUTH)
    v = np.asarray(tp["v"], dtype=float)
    a = np.asarray(tp["a"], dtype=float)
    z = np.asarray(tp["z"], dtype=float)
    t0s = float(np.mean(np.asarray(tp["t0"], dtype=float)))
    T_col = np.asarray(DESIGN["T"], dtype=float)
    W_col = np.asarray(DESIGN["W"], dtype=float)

    print("=" * 104)
    print(f"【{p_name}】t0 = {1000 * t0s:.1f} ms ｜ 每人 {N_TOTAL} 试次 ｜ "
          f"T ∈ {[round(1000 * x, 2) for x in T_LEVELS]} ms")
    print("=" * 104)

    for rho in RHO_LIST:
        p_tau, p_obs, p_respond, mean_rt, _ = _counts(tp, T_col, W_col, rho)
        n_tau = float(np.sum(p_tau))
        n_obs = float(np.sum(p_obs))
        n_resp = float(np.sum(p_respond))
        fin = mean_rt[np.isfinite(mean_rt)]
        print()
        print(f"  ρ = {rho:.2f}")
        print(f"    E[#(τ < T)]   = {n_tau:7.2f}  ({100 * n_tau / N_TOTAL:5.2f}%)"
              f"   ← 模型内部相位在窗口内完成（读 A 的相位项）")
        print(f"    E[#(RT < T)]  = {n_obs:7.2f}  ({100 * n_obs / N_TOTAL:5.2f}%)"
              f"   ← ★**实验里可观测**的刺激期内按键")
        print(f"    E[#(作答)]    = {n_resp:7.2f}  ({100 * n_resp / N_TOTAL:5.2f}%)"
              f"   遗漏率 = {1 - n_resp / N_TOTAL:.3f}")
        if fin.size:
            print(f"    平均RT（逐格解析积分）= {1000 * float(np.mean(fin)):.1f} ms"
                  f"  （最小 {1000 * float(np.min(fin)):.1f} / 最大 {1000 * float(np.max(fin)):.1f}）")

    # ---- 逐 T 水平分解（ρ=1；两项都与 ρ 无关，ρ 只影响 deadline 项） ----
    print()
    print("  逐 T 水平分解（ρ=1）")
    print(f"    {'T(ms)':>8}{'t0(ms)':>8}{'T−t0':>9}{'T−2t0':>9}"
          f"{'P(τ<T)':>10}{'P(RT<T)':>10}{'E[#RT<T]':>10}{'n(T)':>7}")
    for tT in T_LEVELS:
        m = np.abs(T_col - tT) < 1e-12
        x1 = tT
        x2 = tT - t0s
        q1 = 1.0 - float(survival_series(float(v[m][0]), float(a[m][0]),
                                         float(z[m][0]), x1))
        q2 = (1.0 - float(survival_series(float(v[m][0]), float(a[m][0]),
                                          float(z[m][0]), x2))) if x2 > 0 else 0.0
        print(f"    {1000 * tT:8.2f}{1000 * t0s:8.1f}{1000 * x2:9.1f}"
              f"{1000 * (x2 - t0s):9.1f}{q1:10.4f}{q2:10.4f}"
              f"{q2 * float(m.sum()):10.2f}{int(m.sum()):7d}")

    # ---- 读数 B（实验字面）：相位窗口 = T − t0 ----------------
    print()
    print("  读数 B（实验字面：掩蔽在绝对时刻 T 落下 ⇒ 相位窗口 = T − t0）")
    xB = T_col - t0s
    validB = xB > 0
    pB_phase = np.where(validB, 1.0 - survival_series(v, a, z, np.maximum(xB, 1e-9)), 0.0)
    print(f"    E[#(相位窗口为正)] = {float(np.sum(validB)):.0f}/{N_TOTAL}"
          f"   ⇒ 塌缩为 0 的 T 水平："
          f"{[round(1000 * x, 2) for x in T_LEVELS if x - t0s <= 0]} ms")
    print(f"    E[#(τ < T − t0)]   = {float(np.sum(pB_phase)):.2f}"
          f"  （读数 A 同口径 = {float(np.sum(1.0 - survival_series(v, a, z, T_col))):.2f}）")

    # ---- 可操作追问：T 要多大会让 RT<T 变得可观测？ ----------------
    print()
    print("  【可操作追问】固定 W 剖面与 P 剖面，扫描 T，问 E[#(RT<T)] 何时达到阈值")
    print(f"    {'T(ms)':>9}{'E[#(RT<T)]':>13}{'占比':>9}")
    prev = None
    cross = {}
    for tT in T_SCAN:
        _, p_obs_s, _, _, _ = _counts(tp, np.full(N_TOTAL, tT), W_col, 1.0,
                                      need_mean_rt=False)
        n = float(np.sum(p_obs_s))
        if prev is not None:
            for cut, tag in ((CUT_ONE_SIDED, "10"), (CUT_IMPLEMENT, "40")):
                if tag not in cross and prev < cut <= n:
                    cross[tag] = (1000 * tT, n)
        prev = n
        if abs(tT * 1000 - 250) < 5 or abs(tT * 1000 - 500) < 5 or \
           abs(tT * 1000 - 1000) < 5 or abs(tT * 1000 - 1500) < 5 or \
           abs(tT * 1000 - 2000) < 5 or tT >= T_SCAN[-1] - 1e-9:
            print(f"    {1000 * tT:9.1f}{n:13.2f}{100 * n / N_TOTAL:8.2f}%")
    for tag, cut in (("10", CUT_ONE_SIDED), ("40", CUT_IMPLEMENT)):
        if tag in cross:
            print(f"    ⇒ 达到 E[#(RT<T)] = {cut:.0f} 需要 T ≈ {cross[tag][0]:.0f} ms"
                  f"（该处 E = {cross[tag][1]:.2f}）")
        else:
            print(f"    ⇒ 在 T ≤ {1000 * T_SCAN[-1]:.0f} ms 内**从未**达到 E[#(RT<T)] = {cut:.0f}")

# ---- 判据 ---------------------------------------------------------------
print()
print("=" * 104)
print("判据（运行前写死）")
print("=" * 104)
print(f"  E[#(RT<T)] ≥ {CUT_IMPLEMENT:.0f}  ⇒ 值得实现 M-T2 完整似然")
print(f"  {CUT_ONE_SIDED:.0f}–{CUT_IMPLEMENT:.0f}          ⇒ 只做 M-T1 vs M-T2 的单侧版本")
print(f"  < {CUT_ONE_SIDED:.0f}          ⇒ M-T2 在 D4 下不可识别，缺口写进论文而不是靠代码关闭")
print()
print("⚠️ 本脚本只回答「有没有数据」，不实现 M-T2。")
print("⚠️ 若 E[#(RT<T)] 极小，还说明「D5 的科学机会」（min(T, RT)）在**当前 T 取值范围**上")
print("   是空的——那是设计问题而非实现问题，必须先与导师确认 T 的钟点约定：")
print("   「T 从刺激起始算」（读数 B）还是「T 从累积起始算」（读数 A），两者相差一个 t0。")
