# -*- coding: utf-8 -*-
"""
recover_single.py —— 逐被试参数恢复（Stage 3 的第一块验收）
==========================================================
回答的问题：**给定设计 D4 的一个被试（P 固定），哪些被试内参数能被恢复？**

⚠️ P 是**被试间**因子，单被试的 P 不变，故 `β_P / τ_P / β_SP` 在单被试内**不可识别**，
本脚本只恢复被试内自由参数（`exp` 下是 `mapping.WITHIN_FREE` 的 9 个，
`lin` 下是 `mapping.WITHIN_FREE_LIN` 的 7 个），并在报告里说明这一点。

流程（每个重复）：
  1. 用真值参数按设计生成一个被试的观测数据（`simulate.simulate_subject`）；
  2. 用**与生成同一套映射**的似然做 MLE（`likelihood.fit_mle`，多起点）；
  3. 数值 Hessian → 标准误 → 覆盖率；
  4. 汇总 Bias / RMSE / 覆盖率 / 符号恢复率。

用法
----
    python recover_single.py [重复次数] [exp|lin]

    python recover_single.py                # 默认 4 次重复，exp 参数化（9 个自由参数）
    python recover_single.py 20 exp         # 20 次重复（覆盖率在此规模下才有意义）
    python recover_single.py 20 lin         # lin 参数化（7 个自由参数，D22 的处方）

⚠️ exp 与 lin 是**两套不同参数化**，不能用同一组真值直接比较。本脚本用
`mapping.match_lin_to_exp` 把 exp 真值**按设计层行为最小二乘匹配**换算成 lin 真值，
使两者描述的**可观测行为**尽可能一致（用本文件的 T/W 水平时，漂移跨度恢复
**94.8%**、边界跨度恢复 **97.7%**），从而让"参数可恢复"这一结论不依赖于参数化选择。

⚠️ 20 次重复是 2026-10-14 的正式规模（`_scratch/recover_single_lin20_u8.txt`、
`_scratch/recover_single_exp20_u8.txt`）。4 次重复只够流程验收：4 次的 SE 与
20 次几乎相同，但**偏差**会被单次抽样的噪声吞掉（例如 lin 的 `beta_T` 4 次时
偏差 −0.54，20 次时只有 +0.07——同一份代码、同一批种子）。结论必须看 20 次。

拟合健康判定（D30，2026-10-14）
--------------------------------
**问题**：汇总里只要 `SE` 是有限值就会被纳入，于是 `SE = 0` 的**退化拟合**
（数值 Hessian 已失效，点估计无意义）与正常拟合**同等加权**。lin 组层残差
0.4942 里的绝大部分就是**一个**这样的被试造成的。

**判决是三值的**（见 `fit_diagnostics.py`，共用于本脚本与 `recover_group.py`）：

* `degenerate` —— `SE ≤ 0 / 非有限 / 相对过小`，或拟合失败 ⇒ 起点数 ×4
  （2 → 8 → 32）重试，仍退化才**剔除**；
* `bound` —— 参数**贴界**但 SE 健康 ⇒ **保留，只报告**（真值可能就在界上，
  见 `recover_group.py` 文件头与 `_scratch/check_bounds.py`）；
* `ok` —— 两者皆无。

**汇总同时给「含退化（旧口径）」与「剔除后（推荐口径）」两套表**，逐条列出原因。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from fit_diagnostics import fit_with_retry, is_excludable  # noqa: E402
from likelihood import trials_from_arrays  # noqa: E402
from mapping import (SHAPE_MODELS, WITHIN_FREE, WITHIN_FREE_LIN,  # noqa: E402
                     MappingParams, match_lin_to_exp)
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

# ------------------------------------------------------------------
# 真值（只用于生成；拟合不读它）
# ------------------------------------------------------------------
# P 在本设计里是**被试间**因子 → 把 P_ref 设为该被试的 P，使 P 相关项恒为 0，
# β_P / τ_P 自动退出单被试似然（它们只能靠跨被试的 P 组间变异估计）。
P_FIXED = 120.0
T_REF = 0.10
W_REF = 1.20

TRUTH_EXP = MappingParams(
    P_ref=P_FIXED, T_ref=T_REF, W_ref=W_REF, shape_model="exp",
    # 真值已按**实测正确率区间（约 0.73–0.86）**校准，而不是贴在正确率天花板上
    d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080,
    beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)

# 拟合起点：**故意不用真值**
INIT_EXP = MappingParams(
    P_ref=P_FIXED, T_ref=T_REF, W_ref=W_REF, shape_model="exp",
    d_ref=0.50, beta_P=1.50, tau_P=30.0,
    beta_T=0.90, tau_T=0.150,
    beta_S=0.30, beta_SP=0.0, beta_ST=0.00,
    w_model="W1", a_ref=1.60, delta_a=0.10, tau_a=0.50,
    t0=0.25, z_ratio=0.50,
)

# 设计 D4 的被试内部分（T × W 全交叉；P 由被试间决定）
T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12                     # 每单元重复次数 → 4×3×4×12 = 576 试次

N_REPLICATION = 4
N_RESTART = 2
MAXITER = 250
BASE_SEED = 20261013

# ------------------------------------------------------------------
# lin 真值与起点：由 exp 真值**按设计层行为最小二乘匹配**换算得到
# ------------------------------------------------------------------
# 换算规则见 `mapping.match_lin_to_exp` 的 docstring。这样做的意义：让 exp 与 lin
# 两套参数化生成**同一种可观测行为**，于是"参数能否恢复"的结论不是参数化的产物。
# 换算出的 lin 真值：d_ref≈0.6481, beta_T≈1.4810, beta_S≈0.1506, beta_ST≈0.2693,
#                    a_ref≈1.9849, delta_a≈0.1303, t0=0.2200
TRUTH_LIN, LIN_REPORT = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)
INIT_LIN, _ = match_lin_to_exp(INIT_EXP, T_LEVELS, W_LEVELS)

TRUTHS: dict[str, MappingParams] = {"exp": TRUTH_EXP, "lin": TRUTH_LIN}
INITS: dict[str, MappingParams] = {"exp": INIT_EXP, "lin": INIT_LIN}
NAMES: dict[str, list[str]] = {"exp": list(WITHIN_FREE),
                               "lin": list(WITHIN_FREE_LIN)}


def true_accuracy(sim, design):
    """正确率：匹配试次看是否选了上边界，不匹配试次看是否选了下边界。"""
    responded = sim["omission"] == 0
    is_match = np.asarray(design["is_match"]) == 1
    resp_correct = np.where(is_match, sim["side"] == 1, sim["side"] == 0)
    return float(np.mean(resp_correct[responded]))


def print_design_diagnostics(design, p, T_levels, W_levels):
    """打印真值在设计范围内**实际变化了多少** —— 识别性首先取决于此。"""
    from mapping import trial_params as _tp
    from wfpt import p_upper

    print("\n" + "=" * 100)
    print("设计诊断：真值参数在各条件下的取值（识别性首先取决于此）")
    print("=" * 100)
    print(f"{'T(ms)':>7s} {'W(ms)':>7s} {'a':>7s} {'d_other':>9s} {'d_self':>8s} "
          f"{'P(corr|other)':>14s} {'P(corr|self)':>13s}")
    rows = []
    for T in T_levels:
        for W in W_levels:
            one = {"P": np.array([p.P_ref]), "T": np.array([T]), "W": np.array([W]),
                   "is_match": np.array([1])}
            d_other = float(_tp({**one, "is_self": np.array([0.0])}, p)["d"][0])
            d_self = float(_tp({**one, "is_self": np.array([1.0])}, p)["d"][0])
            a = float(_tp({**one, "is_self": np.array([0.0])}, p)["a"][0])
            rows.append((T, W, a, d_other, d_self,
                         float(p_upper(d_other, a, 0.5 * a)),
                         float(p_upper(d_self, a, 0.5 * a))))
            print(f"{T*1000:7.1f} {W*1000:7.1f} {a:7.4f} {d_other:9.4f} {d_self:8.4f} "
                  f"{rows[-1][5]:14.4f} {rows[-1][6]:13.4f}")
    arr = np.array(rows)
    ptp_a = float(np.ptp(arr[:, 2]))
    ptp_d = float(np.ptp(arr[:, 3]))
    print(f"\n  a  的范围：{arr[:,2].min():.4f} – {arr[:,2].max():.4f}"
          f"（跨度 {ptp_a:.4f}，占均值 {100*ptp_a/arr[:,2].mean():.1f}%）")
    print(f"  d  的范围：{arr[:,3].min():.4f} – {arr[:,3].max():.4f}"
          f"（跨度 {ptp_d:.4f}，占均值 {100*ptp_d/arr[:,3].mean():.1f}%）")
    self_eff = arr[:, 4] - arr[:, 3]
    print(f"  自我效应 d_self−d_other：{self_eff.min():.4f} – {self_eff.max():.4f}")
    print(f"  正确率范围：{arr[:,5].min():.3f} – {arr[:,6].max():.3f}"
          f"   ⚠️ 实测 SMT 正确率约 0.33–0.89，贴天花板会削弱识别性")
    print("  ⚠️ 若某个维度在设计范围内几乎不变，其形状参数（τ、Δ）就**不可识别**，")
    print("     这与估计器好坏无关，是**设计**的问题 —— 正是 Stage 4 要优化的对象。")


def main():
    n_rep_total = int(sys.argv[1]) if len(sys.argv) > 1 else N_REPLICATION
    shape = sys.argv[2] if len(sys.argv) > 2 else "exp"
    if shape not in SHAPE_MODELS:
        raise SystemExit(f"未知参数化 {shape!r}；可选 {SHAPE_MODELS}")

    truth = TRUTHS[shape]
    init = INITS[shape]
    names = NAMES[shape]

    design = build_design(P_FIXED, T_LEVELS, W_LEVELS, N_REP)
    n_trials = design["T"].size
    print("=" * 100)
    print(f"Stage 3 · 逐被试参数恢复   （shape_model = {shape}）")
    print("=" * 100)
    print(f"  设计：P 固定 = {P_FIXED:g}；T ∈ {[round(x*1000,2) for x in T_LEVELS]} ms；"
          f"W ∈ {[round(x*1000,1) for x in W_LEVELS]} ms")
    print(f"  单元数 = {len(T_LEVELS)}×{len(W_LEVELS)} = {len(T_LEVELS)*len(W_LEVELS)}；"
          f"每单元 4 类刺激 × {N_REP} 次 → **每人 {n_trials} 试次**")
    print(f"  重复 {n_rep_total} 次；拟合参数 {len(names)} 个：{names}")

    if shape == "lin":
        r = LIN_REPORT
        print("\n  --- exp → lin 换算（行为最小二乘匹配，见 mapping.match_lin_to_exp）---")
        print(f"  真值：d_ref={truth.d_ref:.4f} beta_T={truth.beta_T:.4f} "
              f"beta_S={truth.beta_S:.4f} beta_ST={truth.beta_ST:.4f} "
              f"a_ref={truth.a_ref:.4f} delta_a={truth.delta_a:.4f} t0={truth.t0:.4f}")
        print(f"  起点：d_ref={init.d_ref:.4f} beta_T={init.beta_T:.4f} "
              f"beta_S={init.beta_S:.4f} beta_ST={init.beta_ST:.4f} "
              f"a_ref={init.a_ref:.4f} delta_a={init.delta_a:.4f} t0={init.t0:.4f}")
        print(f"  行为恢复度：漂移跨度 {100*r['d_span_lin']/r['d_span_exp']:.1f}%"
              f"（max|残差| {np.abs(r['d_resid']).max():.4f}）；"
              f"边界跨度 {100*r['a_span_lin']/r['a_span_exp']:.1f}%"
              f"（max|残差| {np.abs(r['a_resid']).max():.4f}）")
        print("  ⚠️ lin 下 tau_T / tau_a 不存在，故自由参数从 9 个降到 7 个。")

    print_design_diagnostics(design, truth, T_LEVELS, W_LEVELS)

    true_vec = truth.vector(names)
    est = np.full((n_rep_total, len(names)), np.nan)
    ses = np.full((n_rep_total, len(names)), np.nan)
    bad = np.zeros(n_rep_total, dtype=bool)
    bad_reasons: list[list[str]] = [[] for _ in range(n_rep_total)]
    bounds_only: list[tuple[int, str]] = []
    n_start_used = np.zeros(n_rep_total, dtype=int)
    t_start = time.time()

    header = f"{'rep':>4s} {'logL':>9s} {'成功':>5s} {'耗时':>7s}"
    print("\n" + header)
    for r in range(n_rep_total):
        rng = np.random.default_rng(BASE_SEED + r)
        sim = simulate_subject(design, truth, rng)
        tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                *design_arrays(design))
        t0s = time.time()
        fit, theta, se, verdict, reasons, n_used = fit_with_retry(
            tr, names, init, BASE_SEED + r,
            n_restart0=N_RESTART, maxiter=MAXITER)
        dt_fit = time.time() - t0s
        est[r] = theta
        ses[r] = se
        bad[r] = is_excludable(verdict)
        bad_reasons[r] = reasons
        n_start_used[r] = n_used
        if verdict == "bound":
            bounds_only.append((r, "; ".join(reasons)))
        mark = ("   ⚠️剔除(退化)" if bad[r]
                else ("   ·贴界(保留)" if verdict == "bound" else ""))
        print(f"{r:4d} {fit['loglik']:9.2f} {str(fit['success']):>5s} {dt_fit:6.1f}s"
              f"   遗漏率={sim['omission'].mean():.3f}  "
              f"正确率={true_accuracy(sim, design):.3f}  "
              f"平均RT={np.nanmean(sim['rt'])*1000:.0f}ms{mark}")

    # ---------------- 汇总 ----------------
    print("\n" + "=" * 100)
    print("拟合健康报告（判据见 fit_diagnostics.py）")
    print("=" * 100)
    print(f"  共 {n_rep_total} 次重复")
    print(f"  * Hessian 退化、**剔除** {int(bad.sum())} 次"
          f"（起点数 2 → 8 → 32 重试后仍退化）")
    if bad.any():
        for r in np.flatnonzero(bad):
            print(f"      rep{r}: " + "; ".join(bad_reasons[r]))
    else:
        print("      （无）")
    print(f"  * 参数**贴界、但保留** {len(bounds_only)} 次"
          f"（估计可信，只是落在箱体边缘）")
    for (r, why) in bounds_only:
        print(f"      rep{r}: {why}")
    if not bounds_only:
        print("      （无）")
    if (n_start_used > N_RESTART).any():
        n_hi = int(np.sum(n_start_used > N_RESTART))
        print(f"  * 另有 {n_hi} 次重复靠**提高起点数**才通过"
              f"（最多用到 {int(n_start_used.max())} 个起点）。")
    if bad.any():
        print("  ⚠️ 下表**同时给出两套结果**：含退化（旧口径）与剔除后（推荐口径）。")
    else:
        print("  ✅ 无退化重复，两套口径相同。")

    def report(mask, label):
        print("\n" + "=" * 100)
        print(f"恢复精度 · {label}（n = {int(mask.sum())}）")
        print("=" * 100)
        print(f"{'参数':>10s} {'真值':>10s} {'估计均值':>11s} {'Bias':>10s} "
              f"{'RMSE':>10s} {'平均SE':>10s} {'覆盖率':>8s}")
        for j, nm in enumerate(names):
            tv = true_vec[j]
            ok = mask & np.isfinite(est[:, j]) & np.isfinite(ses[:, j])
            if not np.any(ok):
                print(f"{nm:>10s} {tv:10.4f}   —— 全部失败/SE 不可用 ——")
                continue
            e = est[ok, j]
            se_j = ses[ok, j]
            bias = float(np.mean(e - tv))
            rmse = float(np.sqrt(np.mean((e - tv) ** 2)))
            cov = float(np.mean((e - 1.96 * se_j <= tv) & (tv <= e + 1.96 * se_j)))
            print(f"{nm:>10s} {tv:10.4f} {np.mean(e):11.4f} {bias:10.4f} "
                  f"{rmse:10.4f} {np.mean(se_j):10.4f} {cov:8.2f}")

    report(np.ones(n_rep_total, dtype=bool), "含退化重复（旧口径）")
    if bad.any():
        report(~bad, "剔除退化重复（推荐口径）")

    print(f"\n  总耗时 {time.time() - t_start:.1f} s（{n_rep_total} 次重复）")
    if n_rep_total < 20:
        print(f"\n  注：{n_rep_total} 次重复下覆盖率没有统计意义，此处只作流程验收；")
        print("      覆盖率要有意义至少需要 20 次重复（Stage 4 已按 20 次运行）。")
    else:
        print(f"\n  注：覆盖率 = 95% Wald 区间包含真值的比例（{n_rep_total} 次重复），")
        print("      名义值 0.95。覆盖率低于 ~0.85 说明该参数的 SE 被系统性低估，")
        print("      即该参数在当前参数化下不可靠 —— 这正是 exp/lin 对比的关键指标。")
    print("      另：β_P / τ_P / β_SP 在**单被试内不可识别**（P 为被试间因子），")
    print("          必须靠跨被试的 P 组间变异估计 —— 这是设计层面的结论。")
    print("      另：若「含退化」与「剔除后」两张表差异很大，说明该轮由**退化拟合**主导，")
    print("          旧口径数字不可用。")
    print("      另：参数**贴界**不再算失败——`Simulate.draw_subject_params` 会把真值")
    print("          `np.clip` 进箱体，真值可能恰好等于界值（见 `_scratch/check_bounds.py`）。")


if __name__ == "__main__":
    main()
