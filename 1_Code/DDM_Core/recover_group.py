# -*- coding: utf-8 -*-
"""
recover_group.py —— 跨被试 P 参数恢复（Stage 3b）
=================================================
回答的问题：**P 的映射参数（β_P、τ_P、β_SP）能不能被这个设计识别？**

为什么必须单独做：**P 是被试间因子**，单个被试的 P 不变，所以
`β_P / τ_P / β_SP` 在单被试似然里完全退出（`recover_single.py` 把 `P_ref` 设为该
被试的 P 使 P 相关项恒为 0）。它们**只能靠跨被试的 P 组间变异**估计。

方法：两阶段（two-stage）
------------------------
1. **被试内拟合**：把 `P_ref` 固定在**公共参考点** `P_COMMON_REF`，逐被试估计
   `d_ref_s`（该被试在 (P_ref, T_ref) 处的漂移幅度）与 `beta_S_s`（其自我主效应）。
2. **组间回归**：对跨被试的斜率参数做非线性最小二乘

       d_ref_s  = d_ref  + β_P ·[f_P(P_s) − f_P(P_ref)] + e_s
       beta_S_s = beta_S + β_SP·[f_P(P_s) − f_P(P_ref)] + u_s

   其中 `τ_P` 是两条方程**共用**的非线性参数。

同时报告 **oracle**（用真值的被试层参数做同一回归）：
* oracle 能恢复、而估计版不能 → 瓶颈在**被试内估计噪声**；
* oracle 也恢复不了 → 瓶颈在 **P 的水平设置**（水平太少/太窄）。

拟合健康判定（D30，2026-10-14）
--------------------------------
**背景**：lin 的组层回归残差 0.4942 几乎全部来自**一个**被试（P=8/subj7：
`d_ref = 4.8009` 撞上界 6.0、`SE = 0.0000`、logL −3530.5）。`SE = 0` 意味着**该点的
数值 Hessian 已退化**，参数估计无意义，却以同等权重进入组间最小二乘并主导回归。

**判决是三值的，不是布尔**（`fit_diagnostics.pathology()`）：

* `degenerate` —— `SE ≤ 0 / 非有限 / < 1e-4×max(|x|,1)`，或拟合本身失败。
  ⇒ 起点数 ×4 重试（2 → 8 → 32）；仍退化则**标记剔除**。
* `bound` —— 参数距边界 < 0.1% 界宽，但 SE 健康。⇒ **保留，只报告**。
* `ok` —— 两者皆无。

**为什么「贴界」不能当失败**：`simulate.draw_subject_params` 用
`np.clip(..., lo, hi)` 把被试层真值截断进箱体，抽到界外时真值**恰好等于界值**。
`_scratch/check_bounds.py` 重放真值后确认 `P=0/subj0` 的**真值就是 0.2000 = 下界**，
于是拟合落在 0.2000 **是答对了**。第一版规则把它当病态剔除，等于删掉一个合法的
低漂移锚点、反而引入偏差。**绝不允许** `SE = 0` 的点默默进入回归，但**允许**一个
SE 健康的点停在界上。

组间回归**同时给两套结果**（含退化 vs 剔除后），由读者判断影响。

用法
----
    python recover_group.py [每组人数] [exp|lin] [free|τ_P 固定值]

    python recover_group.py            # 每 P 组 10 人，exp，τ_P 自由
    python recover_group.py 10 lin     # 每 P 组 10 人，lin 参数化（D18/D19 的处方）
    python recover_group.py 40 lin 30  # **D31 处方**：τ_P 先验固定为 30、每组 40 人

第三个参数（2026-10-14 新增，D31）
--------------------------------
- `free`（缺省）：5 个参数一起估，含 `tau_P`。
- 数值：**`tau_P` 视为已知常数**，只估 `d_ref`/`beta_P`/`beta_S`/`beta_SP`。

依据：`_scratch/check_plevels.py`（200 次重复）证明**组层不存在「4 个水平」的信息
天花板**——无噪声 oracle 精确到 1e-15，有噪声时误差按 1/√n 缩。真正的限制量是
**每组人数**：n=10/组 时 `tau_P` 的相对 SD ≈ **99%**（真值 30.0，SD 29.77），
任何 P 水平集都救不了它（集中在上升段反而恶化到 257.8%）。所以应当像 D18/D19
对待 `tau_T`/`tau_a` 那样，**把 `tau_P` 从自由参数里去掉**，只留斜率 `beta_P`。
`beta_P` 要从 25% 降到 10% 需要 **~40 人/组**。

⚠️ **P 通道与 T/W 通道不同，不能改线性**：`f_P` 在 0–120 上是 S 形，
无噪声最小二乘直线拟合会把斜率**压掉 140 倍**（`beta_P` → 0.0025，真值 0.35）
——精度极好但估错量。T/W 通道可以线性化，P 通道不行。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import numpy as np
from scipy.optimize import least_squares

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from fit_diagnostics import fit_with_retry, is_excludable  # noqa: E402
from likelihood import trials_from_arrays  # noqa: E402
from mapping import (PARAM_BOUNDS, SHAPE_MODELS,  # noqa: E402
                     WITHIN_FREE, WITHIN_FREE_LIN, MappingParams,
                     boundary_a, drift_magnitude, f_P, match_lin_to_exp)
from recover_single import (N_REP, T_LEVELS, T_REF, W_LEVELS, W_REF)  # noqa: E402
from simulate import (SUBJECT_MODE_CLIP, SUBJECT_SD, build_design,  # noqa: E402
                      design_arrays, draw_subject_params, simulate_subject)

# ------------------------------------------------------------------
# 配置
# ------------------------------------------------------------------
P_LEVELS = [0.0, 8.0, 32.0, 120.0]
P_COMMON_REF = 30.0            # 公共参考点：让 P 相关项在组间可比
N_SUBJ_PER_LEVEL = 10
N_RESTART = 2
MAXITER = 250
MAXFUN = 6000
BASE_SEED = 20261101

GROUP_FIT_NAMES = ["d_ref", "beta_P", "beta_S", "beta_SP", "tau_P"]
# D31（2026-10-14）：τ_P 无法从 4 个 P 水平估出来（n=10/组 时相对 SD ≈ 99%），
# 处方是**先验固定 τ_P**、只估斜率与自我效应。此时拟合参数少一个。
GROUP_FIT_NAMES_FIXED_TAU = ["d_ref", "beta_P", "beta_S", "beta_SP"]

# 拟合健康判定规则集中在 `fit_diagnostics.py`（D30）：
# `fit_with_retry` 只在 `degenerate` 时按 2 → 8 → 32 提高起点数重试；
# `bound`（贴界但 SE 健康）**保留不剔除** —— 真值可能就在界上。
# （2026-10-14 的教训：`SE = 0.0000` 的被试点曾以同等权重进入组间回归，
#   使 lin 的残差 RMS 从 0.1044 恶化到 0.4942。）

# ⚠️ 群体真值必须**与其他效应量自洽**（2026-10-13 的教训）
#    单被试真值里的 beta_P = 1.5 在 P_ref = 30 的锚定下意味着
#    d(P=0) = d_ref + 1.5·(0 − 0.632) = 0.70 − 0.948 < 0 → 漂移被 max(·,0) 压成 0，
#    该组变成"纯噪声"，似然面变平，拟合永不收敛（实测单组拟合 >10 分钟未返回）。
#    现按"P=0 时 d≈0.50、P=120 时 d≈0.81"反推：beta_P = (0.70−0.50)/0.632 ≈ 0.32。
GROUP_TRUTH_EXP = MappingParams(
    P_ref=P_COMMON_REF, T_ref=T_REF, W_ref=W_REF, shape_model="exp",
    d_ref=0.70, beta_P=0.35, tau_P=30.0,
    beta_T=0.55, tau_T=0.080,
    beta_S=0.16, beta_SP=0.06, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)

GROUP_INIT_EXP = MappingParams(
    P_ref=P_COMMON_REF, T_ref=T_REF, W_ref=W_REF, shape_model="exp",
    d_ref=0.50, beta_P=0.60, tau_P=60.0,
    beta_T=0.90, tau_T=0.150,
    beta_S=0.30, beta_SP=0.00, beta_ST=0.00,
    w_model="W1", a_ref=1.60, delta_a=0.10, tau_a=0.50,
    t0=0.25, z_ratio=0.50,
)

# lin 版本：用同一把尺子（`mapping.match_lin_to_exp`）换算，见 `recover_single.py`。
# 注意 `match_lin_to_exp` 只改 T/W 通路与参考点截距，**不动** P 通路
# （beta_P/tau_P/beta_SP）—— P 的换算不属于形状函数换算。
GROUP_TRUTH_LIN, GROUP_LIN_REPORT = match_lin_to_exp(
    GROUP_TRUTH_EXP, T_LEVELS, W_LEVELS)
GROUP_INIT_LIN, _ = match_lin_to_exp(GROUP_INIT_EXP, T_LEVELS, W_LEVELS)

GROUP_TRUTHS: dict[str, MappingParams] = {"exp": GROUP_TRUTH_EXP,
                                          "lin": GROUP_TRUTH_LIN}
GROUP_INITS: dict[str, MappingParams] = {"exp": GROUP_INIT_EXP,
                                         "lin": GROUP_INIT_LIN}
GROUP_NAMES: dict[str, list[str]] = {"exp": list(WITHIN_FREE),
                                     "lin": list(WITHIN_FREE_LIN)}

# 向后兼容：旧代码（含其他脚本）引用 `GROUP_TRUTH` / `GROUP_INIT` 时仍取 exp。
GROUP_TRUTH = GROUP_TRUTH_EXP
GROUP_INIT = GROUP_INIT_EXP


def fit_between(P_sub, d_ref_hat, beta_S_hat, P_ref, init, fit_names=None,
                tau_p_fixed=None, se_d=None, se_s=None):
    """联合（加权）非线性最小二乘：两条方程共用同一个 τ_P。

    ``tau_p_fixed`` 为 None（默认）
        自由估计 5 个参数（``GROUP_FIT_NAMES``）。
    ``tau_p_fixed`` 给定数值
        **τ_P 视为已知常数**（D31 处方），只估 4 个（``GROUP_FIT_NAMES_FIXED_TAU``）；
        返回的 dict 仍含 ``tau_P`` 键（值为该固定值），便于统一打印。
    ``se_d`` / ``se_s``
        各被试 `d_ref` / `beta_S` 的**被试内估计 SE**。给定则做**逆方差加权**
        （残差除以 SE），即 WLS；不给则退化为等权 OLS。

    返回值 ``(out, rms, wrms)``
        ``rms``  未加权残差 RMS（两种模式都可比）
        ``wrms`` 加权残差均方根（χ²/2n 的平方根）；OLS 模式下与 rms 相同。

    ⚠️ 为什么需要 WLS：被试内 SE 在不同被试间可差两个量级（实测 0.0067 vs
    0.0774，方差差 127 倍）。等权 OLS 会把一个几乎没信息的被试与一个高精度
    被试同等对待。加权才是有效（最小方差）估计量。
    """
    P_sub = np.asarray(P_sub, dtype=float)
    names = list(GROUP_FIT_NAMES if fit_names is None else fit_names)
    lo = np.array([PARAM_BOUNDS[n][0] for n in names])
    hi = np.array([PARAM_BOUNDS[n][1] for n in names])
    x0 = np.array(init, dtype=float)

    w_d = None if se_d is None else 1.0 / np.asarray(se_d, dtype=float)
    w_s = None if se_s is None else 1.0 / np.asarray(se_s, dtype=float)
    weighted = w_d is not None and w_s is not None

    def raw(x):
        prm = dict(zip(names, x))
        tau_P = float(tau_p_fixed) if tau_p_fixed is not None else prm["tau_P"]
        reg = f_P(P_sub, tau_P) - f_P(P_ref, tau_P)
        return np.concatenate([d_ref_hat - (prm["d_ref"] + prm["beta_P"] * reg),
                               beta_S_hat - (prm["beta_S"] + prm["beta_SP"] * reg)])

    def resid(x):
        r = raw(x)
        if not weighted:
            return r
        n = P_sub.size
        return np.concatenate([r[:n] * w_d, r[n:] * w_s])

    res = least_squares(resid, x0, bounds=(lo, hi), x_scale="jac",
                        max_nfev=40000)
    out = dict(zip(names, res.x))
    out["tau_P"] = float(tau_p_fixed) if tau_p_fixed is not None else out["tau_P"]
    rms = float(np.sqrt(np.mean(raw(res.x) ** 2)))
    wrms = float(np.sqrt(np.mean(res.fun ** 2)))
    return out, rms, wrms


def make_subject_truth(group_truth, P_s, P_common, rng,
                       mode: str = SUBJECT_MODE_CLIP):
    """把 P 的组间效应**移进被试层参数**，并把 ``P_ref`` 设为该被试自己的 P。

    ``mode`` 透传给 `simulate.draw_subject_params`：默认 ``"clip"``（与历史日志
    逐位一致），``"truncate"`` 则改用界内截断正态（没有边界概率堆，见
    `_scratch/check_bounds_trunc.py`）。

    为什么必须这样（2026-10-13 的实测教训）
    --------------------------------------
    两阶段方法的正确前提是：**被试内似然与生成数据使用同一套 P 项**。
    若让 `P_ref` 保持公共参考点，被试内似然就要用 β_P/τ_P 去算 P 偏移，
    但这两个参数**不在被试内自由参数里**，会用起点的错值（0.60/60 vs 真值 0.35/30）；
    估计出的 `d_ref_s` 会吸收这份不匹配 → 组间回归必然错
    （实测：β_P 估计 −0.476 vs 真值 +0.35，且 **oracle 也错**，说明不是估计噪声）。

    正确做法：令 `P_ref = P_s`，使 P 项恒为 0；把 P 效应写进 `d_ref` 与 `beta_S`，
    交给 `fit_between` 在组间回归里估计。此时 oracle（用真值被试层参数）才有意义。
    """
    reg = float(f_P(P_s, group_truth.tau_P) - f_P(P_common, group_truth.tau_P))
    base = group_truth.replace(
        P_ref=float(P_s),
        d_ref=group_truth.d_ref + group_truth.beta_P * reg,
        beta_S=group_truth.beta_S + group_truth.beta_SP * reg,
    )
    return draw_subject_params(base, rng, mode=mode), reg


def main():
    n_sub = int(sys.argv[1]) if len(sys.argv) > 1 else N_SUBJ_PER_LEVEL
    shape = sys.argv[2] if len(sys.argv) > 2 else "exp"
    if shape not in SHAPE_MODELS:
        raise SystemExit(f"未知参数化 {shape!r}；可选 {SHAPE_MODELS}")
    # 第三个参数：τ_P 的先验固定值（D31 处方）；缺省或 "free" = 自由估计。
    arg3 = sys.argv[3] if len(sys.argv) > 3 else "free"
    if arg3 == "free":
        tau_p_fixed = None
    else:
        try:
            tau_p_fixed = float(arg3)
        except ValueError:
            raise SystemExit(f"第三个参数应为 'free' 或 τ_P 的固定数值，收到 {arg3!r}")
        if tau_p_fixed <= 0:
            raise SystemExit(f"τ_P 的固定值必须为正，收到 {tau_p_fixed!r}")
    g_names = (GROUP_FIT_NAMES if tau_p_fixed is None
               else GROUP_FIT_NAMES_FIXED_TAU)

    # 群体真值（已按效应量自洽校准，见文件头的 ⚠️ 说明）
    group_truth = GROUP_TRUTHS[shape]
    group_init = GROUP_INITS[shape]
    names = GROUP_NAMES[shape]

    design = build_design(P_COMMON_REF, T_LEVELS, W_LEVELS, N_REP)
    n_trials = design["T"].size

    print("=" * 100)
    print(f"Stage 3b · 跨被试 P 参数恢复（两阶段）   （shape_model = {shape}）")
    print("=" * 100)
    print(f"  P 水平：{[int(x) for x in P_LEVELS]}（被试间）；公共参考点 P_ref = {P_COMMON_REF:g}")
    print(f"  每 P 组 {n_sub} 人 → 共 {len(P_LEVELS)*n_sub} 名被试")
    print(f"  被试内设计：T ∈ {[round(x*1000,1) for x in T_LEVELS]} ms × "
          f"W ∈ {[round(x*1000,1) for x in W_LEVELS]} ms × 4 类 × {N_REP} 次 = {n_trials} 试次/人")
    print(f"  被试间随机效应 SD：{SUBJECT_SD}")
    print(f"  被试内自由参数 {len(names)} 个：{names}")
    print(f"  群体真值：β_P = {group_truth.beta_P:.3f}、τ_P = {group_truth.tau_P:.1f}、"
          f"β_SP = {group_truth.beta_SP:.3f}")
    if tau_p_fixed is None:
        print(f"  组间回归：**自由估计** {len(g_names)} 个参数 {g_names}"
              f"（τ_P 自由；D31 已证它在 4 个 P 水平下不可估）")
    else:
        print(f"  组间回归：**τ_P 先验固定为 {tau_p_fixed:g}**（D31 处方），"
              f"只估 {len(g_names)} 个参数 {g_names}")
        print(f"      ⚠️ 固定值与真值 {group_truth.tau_P:.1f} 的偏离本身是**误设**："
              f"用它当敏感性分析，不要当成「知道真值」的 oracle。")
    print(f"  f_P 在各 P 水平的值（τ_P={group_truth.tau_P:.0f}）："
          f"{np.round(f_P(P_LEVELS, group_truth.tau_P), 4).tolist()}")

    # ---- 组间设计诊断：先看各 P 组的漂移是否落在合理区间 ----
    print("\n" + "-" * 100)
    print("组间设计诊断：各 P 组在参考 T 处的漂移幅度（漂移被压到 0 的组会变成纯噪声）")
    print("-" * 100)
    print(f"  {'P':>5s} {'f_P':>7s} {'d(P,T_ref)':>12s} {'d 范围(T 最小–最大)':>22s} "
          f"{'P(correct) 范围':>18s}")
    from wfpt import p_upper  # noqa: PLC0415
    # 用库函数算漂移/边界，**不手写形状公式** —— 这样 exp/lin 自动都正确。
    # （旧版手写 `exp(−T_ref/τ_T) − exp(−T/τ_T)`，lin 下会直接算错。）
    a_ref_truth = float(boundary_a([W_REF], group_truth)[0])
    for P in P_LEVELS:
        d_at_ref = float(drift_magnitude([P], [T_REF], [0.0], group_truth)[0])
        ds = []
        accs = []
        for T in T_LEVELS:
            d = float(drift_magnitude([P], [T], [0.0], group_truth)[0])
            ds.append(d)
            accs.append(float(p_upper(max(d, 1e-6), a_ref_truth, 0.5 * a_ref_truth)))
        flag = "  ⚠️ 退化" if min(ds) < 0.10 else ""
        print(f"  {P:5.0f} {float(f_P(P, group_truth.tau_P)):7.4f} {d_at_ref:12.4f} "
              f"{min(ds):10.4f} – {max(ds):8.4f} {min(accs):18.3f} – {max(accs):.3f}{flag}")
    print("-" * 100)

    P_sub, d_hat, d_se, s_hat, s_se = [], [], [], [], []
    d_true, s_true = [], []
    om_all, acc_all = [], []
    excluded: list[tuple[float, int, str]] = []   # 退化，剔除：(P, subj, 原因)
    excl_idx: list[int] = []                      # 在 P_sub 里的下标
    bound_only: list[tuple[float, int, str]] = []  # 贴界，**保留**：(P, subj, 原因)
    t_start = time.time()

    print(f"\n{'P':>5s} {'subj':>5s} {'logL':>9s} {'d_ref':>8s} {'±SE':>7s} "
          f"{'beta_S':>8s} {'±SE':>7s} {'遗漏':>6s} {'正确率':>7s} {'耗时':>6s}")
    for P in P_LEVELS:
        # ⚠️ 必须用**该组的 P** 构建设计表：simulate 与 fit 都读 design["P"]。
        #    若沿用公共参考点 P_COMMON_REF，所有被试都会在数据里被当成 P=30，
        #    P 的组间变异从未真正进入模拟，β_P/τ_P 就永远不可识别
        #    （开发期踩过这个坑：24 名被试跑 >10 分钟仍未返回）。
        design_P = dict(design)
        design_P["P"] = np.full_like(design["P"], float(P))
        for s in range(n_sub):
            seed = BASE_SEED + int(P) * 1000 + s
            rng = np.random.default_rng(seed)
            subj_truth, reg = make_subject_truth(group_truth, P, P_COMMON_REF, rng)
            sim = simulate_subject(design_P, subj_truth, rng)
            tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                    *design_arrays(design_P))
            # 逐被试收窄 t0 上界：t0 必须小于最小 RT，否则似然全为 −inf
            t0_cap = float(np.nanmin(sim["rt"])) - 0.005
            ov = {"t0": (PARAM_BOUNDS["t0"][0],
                         min(PARAM_BOUNDS["t0"][1], max(t0_cap, 0.06)))}
            init_s = group_init.replace(P_ref=float(P))
            t0s = time.time()
            fit, bh, se, verdict, reasons, n_used = fit_with_retry(
                tr, names, init_s, seed, ov,
                n_restart0=N_RESTART, maxiter=MAXITER, maxfun=MAXFUN)
            dt_fit = time.time() - t0s
            i_d, i_s = names.index("d_ref"), names.index("beta_S")

            P_sub.append(P); d_hat.append(bh[i_d]); d_se.append(se[i_d])
            s_hat.append(bh[i_s]); s_se.append(se[i_s])
            d_true.append(subj_truth.d_ref); s_true.append(subj_truth.beta_S)
            om_all.append(sim["omission"].mean())
            if is_excludable(verdict):
                excl_idx.append(len(P_sub) - 1)
                excluded.append((float(P), s, "; ".join(reasons)))
            elif verdict == "bound":
                bound_only.append((float(P), s, "; ".join(reasons)))

            is_match = np.asarray(design["is_match"]) == 1
            resp = sim["omission"] == 0
            ok = np.where(is_match, sim["side"] == 1, sim["side"] == 0)
            acc_all.append(float(np.mean(ok[resp])))
            mark = ("  ⚠️剔除(退化)" if is_excludable(verdict)
                    else ("  ·贴界(保留)" if verdict == "bound" else ""))
            print(f"{P:5.0f} {s:5d} {fit['loglik']:9.1f} {bh[i_d]:8.4f} {se[i_d]:7.4f} "
                  f"{bh[i_s]:8.4f} {se[i_s]:7.4f} {sim['omission'].mean():6.3f} "
                  f"{acc_all[-1]:7.3f} {dt_fit:5.1f}s{mark}")

    P_sub = np.array(P_sub); d_hat = np.array(d_hat); d_se = np.array(d_se)
    s_hat = np.array(s_hat); s_se = np.array(s_se)
    d_true = np.array(d_true); s_true = np.array(s_true)

    # ---------------- 两阶段回归 ----------------
    init_vec = ([group_init.d_ref, group_init.beta_P, group_init.beta_S,
                 group_init.beta_SP, group_init.tau_P] if tau_p_fixed is None else
                [group_init.d_ref, group_init.beta_P, group_init.beta_S,
                 group_init.beta_SP])
    keep = np.ones(P_sub.size, dtype=bool)
    keep[excl_idx] = False

    fb = dict(fit_names=g_names, tau_p_fixed=tau_p_fixed)
    est_fit, est_rms, _ = fit_between(P_sub, d_hat, s_hat, P_COMMON_REF, init_vec, **fb)
    orc_fit, orc_rms, _ = fit_between(P_sub, d_true, s_true, P_COMMON_REF, init_vec, **fb)
    if excl_idx:
        est_k, est_k_rms, _ = fit_between(P_sub[keep], d_hat[keep], s_hat[keep],
                                          P_COMMON_REF, init_vec, **fb)
        orc_k, orc_k_rms, _ = fit_between(P_sub[keep], d_true[keep], s_true[keep],
                                          P_COMMON_REF, init_vec, **fb)
    else:
        est_k, est_k_rms = est_fit, est_rms
        orc_k, orc_k_rms = orc_fit, orc_rms

    # 逆方差加权（WLS）对照：权重 = 1/(该被试的被试内 SE)。
    # 只对**保留下来**的被试有意义（退化被试的 SE 不可信，已剔除）。
    if np.any(keep):
        m = keep
        fw = dict(fb, se_d=d_se[m], se_s=s_se[m])
        est_w, est_w_rms, est_w_wrms = fit_between(
            P_sub[m], d_hat[m], s_hat[m], P_COMMON_REF, init_vec, **fw)
        orc_w, orc_w_rms, orc_w_wrms = fit_between(
            P_sub[m], d_true[m], s_true[m], P_COMMON_REF, init_vec, **fw)
        wls_info = (est_w, est_w_rms, est_w_wrms, orc_w, orc_w_rms, orc_w_wrms)
    else:
        wls_info = None

    print("\n" + "=" * 100)
    print("拟合健康报告（判据见 fit_diagnostics.py）")
    print("=" * 100)
    print(f"  共 {P_sub.size} 名被试")
    print(f"  * Hessian 退化、**剔除** {len(excl_idx)} 名"
          f"（起点数 2 → 8 → 32 重试后仍退化）")
    if excluded:
        for (P_e, s_e, why) in excluded:
            print(f"      P={P_e:.0f}/subj{s_e}: {why}")
    else:
        print("      （无）")
    print(f"  * 参数**贴界、但保留** {len(bound_only)} 名"
          f"（估计可信，只是落在箱体边缘；真值可能就在界上）")
    for (P_e, s_e, why) in bound_only:
        print(f"      P={P_e:.0f}/subj{s_e}: {why}")
    if not bound_only:
        print("      （无）")
    if excl_idx:
        print("  ⚠️ 组间回归**同时给出两套结果**：含退化被试（旧口径）与剔除后（推荐口径）。")
    else:
        print("  ✅ 无退化被试，两套口径相同。")

    print("\n" + "=" * 100)
    print("跨被试 P 参数恢复")
    print("=" * 100)
    print(f"  被试内 d_ref 的估计 SE 均值 = {np.nanmean(d_se):.4f}；"
          f"被试间 SD 真值 = {SUBJECT_SD['d_ref']:.4f}")
    print(f"  被试内 beta_S 的估计 SE 均值 = {np.nanmean(s_se):.4f}；"
          f"被试间 SD 真值 = {SUBJECT_SD['beta_S']:.4f}")
    print(f"\n  {'参数':>8s} {'真值':>10s} {'全部(实际)':>12s} "
          f"{'剔除后(实际)':>14s} {'Bias':>10s} {'oracle':>12s} {'Bias':>10s}")
    for nm in g_names:
        tv = getattr(group_truth, nm)
        print(f"  {nm:>8s} {tv:10.4f} {est_fit[nm]:12.4f} "
              f"{est_k[nm]:14.4f} {est_k[nm]-tv:10.4f} "
              f"{orc_k[nm]:12.4f} {orc_k[nm]-tv:10.4f}")
    print(f"\n  回归残差 RMS：全部(实际) {est_rms:.4f} ｜ 剔除后(实际) {est_k_rms:.4f} "
          f"｜ 剔除后 oracle {orc_k_rms:.4f}"
          + (f"（全部 oracle {orc_rms:.4f}）" if excl_idx else ""))

    if wls_info is not None:
        e_w, e_w_rms, e_w_wrms, o_w, o_w_rms, o_w_wrms = wls_info
        print(f"\n  逆方差加权（WLS，权重 = 1/被试内 SE；仅保留被试 "
              f"n={int(keep.sum())}）—— 与上面的等权 OLS 对照：")
        print(f"  {'参数':>8s} {'真值':>10s} {'OLS(实际)':>12s} {'WLS(实际)':>12s} "
              f"{'Δ':>10s} {'OLS(oracle)':>13s} {'WLS(oracle)':>13s}")
        for nm in g_names:
            tv = getattr(group_truth, nm)
            print(f"  {nm:>8s} {tv:10.4f} {est_k[nm]:12.4f} {e_w[nm]:12.4f} "
                  f"{e_w[nm]-est_k[nm]:10.4f} {orc_k[nm]:13.4f} {o_w[nm]:13.4f}")
        print(f"  未加权残差 RMS：OLS {est_k_rms:.4f} / WLS {e_w_rms:.4f}；"
              f"oracle OLS {orc_k_rms:.4f} / WLS {o_w_rms:.4f}")
        print(f"  加权残差均方根：WLS(实际) {e_w_wrms:.4f}｜WLS(oracle) {o_w_wrms:.4f}")
        print("  读法：WLS 若使 **oracle 列**更接近真值，说明等权确实在浪费精度；")
        print("        若 WLS 反而更差，说明 SE 本身太噪（数值 Hessian），不该拿它当权重。")

    print("\n" + "=" * 100)
    print("逐 P 水平的被试层均值（暴露 P 的识别性；仅剔除退化被试，贴界者保留）")
    print("=" * 100)
    if excl_idx:
        n_all = [int(np.sum(P_sub == P)) for P in P_LEVELS]
        n_keep = [int(np.sum((P_sub == P) & keep)) for P in P_LEVELS]
        print(f"  每组人数（全部 → 剔除后）："
              f"{ {int(p): (a, k) for p, a, k in zip(P_LEVELS, n_all, n_keep)} }")
    print(f"  {'P':>5s} {'n':>4s} {'f_P':>7s} {'d_ref 估计均值':>15s} {'d_ref 真值均值':>15s} "
          f"{'β_S 估计均值':>13s} {'β_S 真值均值':>13s}")
    for P in P_LEVELS:
        m = (P_sub == P) & keep
        print(f"  {P:5.0f} {m.sum():4d} {float(f_P(P, group_truth.tau_P)):7.4f} "
              f"{d_hat[m].mean():15.4f} {d_true[m].mean():15.4f} "
              f"{s_hat[m].mean():13.4f} {s_true[m].mean():13.4f}")

    print(f"\n  总耗时 {time.time() - t_start:.1f} s")
    print("\n  读法（依据 D31 / README §8.13，旧版『瓶颈在 P 水平设置』已推翻）：")
    print("   * 无噪声 oracle 在 4 个 P 水平下是**精确**的（残差 ~1e-15）；")
    print("     若 oracle 列仍有可观偏差，那是 **n 太小的抽样噪声**，不是水平数不够。")
    print("   * 有噪声 oracle 的误差按 1/√n 缩；n=10/组 时 τ_P 相对 SD ≈ 99% ⇒")
    print("     **τ_P 必须改为先验固定**（第三个命令行参数给数值）。")
    print("   * 若 oracle 准而「剔除后(实际)」不准 → 瓶颈在**被试内估计噪声**，")
    print("     需要加试次或加人数。")
    print("   * 若「全部(实际)」远差于「剔除后(实际)」→ 该轮由**退化拟合**主导，")
    print("     旧口径的数字不可用（见 README §8.11 B）。")
    print(f"\n  注：β_SP 的真值为 {group_truth.beta_SP:.1f}（自我效应不随 P 变化），")
    print("      故该项的『恢复』应表现为**估计接近 0**，而不是接近某个非零值。")


if __name__ == "__main__":
    main()
