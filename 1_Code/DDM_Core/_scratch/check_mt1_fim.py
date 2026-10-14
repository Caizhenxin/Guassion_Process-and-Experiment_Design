# -*- coding: utf-8 -*-
"""
check_mt1_fim.py —— 在 M-T1（两阶段时变漂移）下重算候选设计的 Fisher 信息
==========================================================================
**为什么做这个**（README §9 第 7 / 17 项）
----------------------------------------
`design_fim.py` 用 OPG 期望信息量在**恒定漂移（M-T3）**下给 9 个候选设计排了名次，
D24 / D4 的 T/W 水平就是照那个名次定下来的。但决策 **D5**（刺激期内按键即结束试次）
把数据生成机制改成了 **M-T1**：漂移在 `t = T` 处从 `d_stim` 阶跃到 `d_mask = rho * d_stim`。
§8.10 已实测 M-T1 是**一阶效应**（ρ=0.5 时正确率变 13 个百分点）——那么问题是：

    **M-T3 下排出来的设计名次，在 M-T1 下还成立吗？**

若不成立，D4 的 T 水平选择就建立在一个错的模型上。§9 第 7 项原先把这件事挂到
「先由正式数据估出 ρ 再决定」，但**设计排序的稳健性不必等 ρ**：可以做**以 ρ 为扫描变量**
的敏感性分析，看名次在 ρ ∈ {1, 0.75, 0.5} 上是否稳定。本脚本就做这件事。

自检（先跑，不过就不看结果）
---------------------------
- **A**：`ρ = 1` 时 `per_trial_loglik_step` 应与 `likelihood.per_trial_loglik` 逐试次一致
  （归一化后最大绝对差 < 1e-5）。这是「M-T3 是 M-T1 在 ρ=1 的严格嵌套特例」的复核。
- **B**：`ρ = 1` 时 M-T1 的 7 个被试内参数 SE 应与 `design_fim.design_se`（M-T3）的
  同一批 SE 一致（相对差 < 2%）。**这一条把本脚本钉在已验证过的量上**——
  如果 A/B 不过，下面所有 M-T1 数字都不可信。

⚠️ 与 `design_fim.py` 相同的三个限定
-----------------------------------
1. 这是 **Cramér–Rao 下界**（大样本、正则条件下最优）；真实 MLE 只会更差。
2. 用**「聚合被试」**（n_subj 名被试的试次合并、不含随机效应）；固定 n_subj 下
   比较单人 SE 与比较被试量等价。
3. 信息量用 **OPG**（逐试次得分外积）而非 Hessian——小曲率参数（`delta_a` 的 a
   跨度只有 0.13）在二阶差分下会被 `~1e-13` 的浮点噪声淹没。

用法
----
    python _scratch/check_mt1_fim.py [n_fim] [输出路径] [设计名子串过滤] [exp|lin]

第 4 个参数选参数集：
`exp`（默认）= `design_fim.NAMES`，**9 个**被试内参数（与 `design_fim.py` 排出的
9 设计名次可比 ⇒ 这才是 §9 第 7/17 项要检验的对象）；
`lin` = `mapping.WITHIN_FREE_LIN`，**7 个**（= 定稿文档声明要用的分析模型
`shape_model="lin"`，把 `tau_T`/`tau_a` 当已知固定值）。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent          # .../_scratch
sys.path.insert(0, str(_HERE.parent))            # .../DDM_Core

from design_fim import (DESIGNS, NAMES, P_SINGLE, PRIMARY,  # noqa: E402
                        TRUTH, check_validity)
from likelihood import (_bounds_for, opg_information,  # noqa: E402
                        per_trial_loglik, trials_from_arrays)
from mapping import WITHIN_FREE_LIN  # noqa: E402
from simulate import build_design, design_arrays  # noqa: E402
from twophase import (MASK_RHO_BOUNDS, per_trial_loglik_step,  # noqa: E402
                      simulate_euler_subject)

RHO_NAME = "rho"
ALL_NAMES = list(NAMES) + [RHO_NAME]
N_FREE = len(ALL_NAMES)                          # 7 + 1 = 8

RHO_LIST = [1.00, 0.75, 0.50]

#: ⚠️ 生成用 **Euler**（`simulate_euler_subject`，D33 已标定）而不是 `simulate_step_subject`：
#: 后者用数值 Laplace 反演（`sample_step`，n_grid=3000），单名被试要 ~10 分钟，
#: 而 Euler 在 dt=5e-5 下只要 ~6 s（`_scratch/check_euler_dt_u8.txt`）。
DT_GEN = 5e-5

SELFCHECK_A_TOL = 1e-5       # 归一化逐试次对数似然最大绝对差
SELFCHECK_B_TOL = 0.02       # ρ=1 时 vs M-T3 的 SE 相对差


def _gen(design, rho: float, seed: int, truth=None):
    """生成一份 M-T1 数据并打包成 `trials_from_arrays` 的格式。"""
    rng = np.random.default_rng(seed)
    sim = simulate_euler_subject(design, truth if truth is not None else TRUTH,
                                 rho, rng, dt=DT_GEN)
    return sim, trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                   *design_arrays(design))


# ------------------------------------------------------------------
# OPG：把 rho 当成第 8 个参数一起做有限差分
# ------------------------------------------------------------------
def opg_step_information(tr: dict, p, rho: float, rel_step: float = 1e-3,
                         include_rho: bool = True):
    """M-T1 的 OPG 期望信息量。

    ``include_rho=True``（默认）参数向量 = (9 个被试内参数, rho)，共 10 个。
    ``include_rho=False`` 只对 9 个被试内参数求差分、``rho`` **固定在给定值**——
    这是与 M-T3 做自检时必须用的形式：把 rho 一起放进去会改变其余参数的**边际** SE
    （ρ 与 `d_ref` 强相关），那不是实现错误而是真实代价，见自检 B 的第二张表。

    差分在**自然参数尺度**上做（步长 = 边界宽度 × rel_step），于是返回的协方差
    可直接开方得到参数自身单位的 SE。返回 ``(I, G)``。
    """
    lo, hi = _bounds_for(NAMES, None)
    theta0 = p.vector(NAMES)
    h = rel_step * (hi - lo)
    n = len(NAMES)
    nt = int(tr["rt"].size)
    ncol = n + (1 if include_rho else 0)
    G = np.zeros((nt, ncol))

    for i in range(n):
        d = np.zeros(n)
        d[i] = h[i]
        pt_p = per_trial_loglik_step(p.with_vector(NAMES, theta0 + d), tr, rho)
        pt_m = per_trial_loglik_step(p.with_vector(NAMES, theta0 - d), tr, rho)
        if pt_p is None or pt_m is None:
            raise ValueError(
                f"opg_step_information: 参数 {NAMES[i]} 在步长 {h[i]:g} 处越界；"
                f"请调小 rel_step 或检查真值是否贴近边界")
        G[:, i] = (pt_p - pt_m) / (2.0 * h[i])

    if include_rho:
        hr = rel_step * (MASK_RHO_BOUNDS[1] - MASK_RHO_BOUNDS[0])
        pt_p = per_trial_loglik_step(p, tr, rho + hr)
        pt_m = per_trial_loglik_step(p, tr, rho - hr)
        if pt_p is None or pt_m is None:
            raise ValueError(
                f"opg_step_information: rho 在 {rho:g} ± {hr:g} 处越界"
                f"（边界 {MASK_RHO_BOUNDS}）")
        G[:, n] = (pt_p - pt_m) / (2.0 * hr)

    return G.T @ G, G


def _se_from_I(I: np.ndarray) -> np.ndarray:
    return np.sqrt(np.maximum(np.diag(np.linalg.pinv(I)), 0.0))


# ------------------------------------------------------------------
# 自检
# ------------------------------------------------------------------
def selfcheck_a(seed: int = 0) -> float:
    """ρ=1 时 M-T1 与 M-T3 的逐试次对数似然最大绝对差（归一化到每试次量级）。"""
    T, W, r = DESIGNS["D4        (4T×3W, r12)"]
    design = build_design(P_SINGLE, T, W, r)
    _, tr = _gen(design, 1.0, seed)
    a = per_trial_loglik_step(TRUTH, tr, 1.0)
    b = per_trial_loglik(TRUTH, tr)
    return float(np.max(np.abs(a - b)) / max(1.0, float(np.max(np.abs(b)))))


def selfcheck_b(n_fim: int, seed: int = 0):
    """ρ=1 时在**同一份数据**上比对 M-T1 与 M-T3 的 OPG 信息量。

    ⚠️ 关键在于「同一份数据」：OPG 是 ``GᵀG``，依赖**具体实现的那一份 rt**，
    而不只是它的期望。所以这个自检必须在同一 `tr` 上算两次，
    否则量到的是**两个生成器之间的蒙特卡洛差**（Euler vs 解析抽样器），不是实现差。

    返回 ``(se_fixed, se_m3, se_free, rel_fixed)``：
    ``se_fixed`` = M-T1 但 ρ **固定在 1.0**（与 M-T3 参数个数相同）⇒ 应与 ``se_m3`` 一致；
    ``se_free`` = M-T1 把 ρ 当自由参数 ⇒ 多出来的相关会**抬高**其余参数的边际 SE。
    """
    T, W, r = DESIGNS["D4        (4T×3W, r12)"]
    design = build_design(P_SINGLE, T, W, r)
    ses_fix, ses_free, ses_m3 = [], [], []
    for k in range(n_fim):
        _, tr1 = _gen(design, 1.0, seed + 1000 * k)
        I_fix, _ = opg_step_information(tr1, TRUTH, 1.0, include_rho=False)
        ses_fix.append(_se_from_I(I_fix))
        I_free, _ = opg_step_information(tr1, TRUTH, 1.0, include_rho=True)
        ses_free.append(_se_from_I(I_free)[:len(NAMES)])
        I3, _ = opg_information(tr1, NAMES, TRUTH)     # ← 同一份 tr1，不重新生成
        ses_m3.append(_se_from_I(I3))
    a = np.mean(ses_fix, axis=0)
    b = np.mean(ses_m3, axis=0)
    c = np.mean(ses_free, axis=0)
    return a, b, c, np.abs(a - b) / np.maximum(np.abs(b), 1e-300)


# ------------------------------------------------------------------
# 主计算
# ------------------------------------------------------------------
def design_se_step(T_levels, W_levels, n_rep, rho: float,
                   truth=TRUTH, n_fim: int = 4, seed: int = 0) -> dict:
    """在 M-T1（给定 rho）下算该设计的预测 SE 与行为诊断。"""
    design = build_design(P_SINGLE, T_levels, W_levels, n_rep)
    n_trials = int(design["T"].size)

    Is, ses_i = [], []
    om, acc, rt_mean = [], [], []
    for k in range(n_fim):
        sim, tr = _gen(design, rho, seed + 1000 * k, truth=truth)
        I, _ = opg_step_information(tr, truth, rho)
        Is.append(I)
        ses_i.append(_se_from_I(I))

        om.append(float(sim["omission"].mean()))
        resp = sim["omission"] == 0
        is_match = np.asarray(design["is_match"]) == 1
        ok = np.where(is_match, sim["side"] == 1, sim["side"] == 0)
        if np.any(resp):
            acc.append(float(np.mean(ok[resp])))
        rt_mean.append(float(np.nanmean(sim["rt"])))

    I_mean = np.mean(Is, axis=0)
    cov = np.linalg.pinv(I_mean)
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    se_sd = np.std(np.asarray(ses_i), axis=0)

    return {
        "n_trials": n_trials,
        "se": se,
        "se_sd": se_sd,
        "omission": float(np.mean(om)),
        "acc": float(np.mean(acc)) if acc else float("nan"),
        "rt_ms": float(np.mean(rt_mean) * 1000),
        "T": T_levels, "W": W_levels, "rep": n_rep, "rho": rho,
    }


def main():
    global NAMES, ALL_NAMES, N_FREE
    n_fim = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    filt = sys.argv[3] if len(sys.argv) > 3 else None
    if filt in ("", "*", "all"):      # ⚠️ PowerShell 会把空字符串参数丢掉，
        filt = None                   # 所以用 `all` 当「不过滤」的哨兵
    param_mode = sys.argv[4] if len(sys.argv) > 4 else "exp"
    if param_mode == "lin":
        # 定稿文档声明要用的分析模型是 `shape_model="lin"`（7 个被试内参数）。
        # 换成 lin 参数集后，`tau_T`/`tau_a` 视为**已知固定值**，
        # 信息矩阵就是 9×9 的子块 —— 这正是「固定两个时标」的处方（§8.7 第 6 条）。
        NAMES = list(WITHIN_FREE_LIN)
        ALL_NAMES = list(NAMES) + [RHO_NAME]
        N_FREE = len(ALL_NAMES)
    elif param_mode != "exp":
        raise SystemExit(f"第 4 个参数只能是 exp 或 lin，收到 {param_mode!r}")

    designs = {k: v for k, v in DESIGNS.items() if (filt is None or filt in k)}

    print("=" * 118)
    print("Stage 4/5 · 在 M-T1（两阶段时变漂移）下复核候选设计的 Fisher 信息")
    print("=" * 118)
    print(f"  参数集模式：**{param_mode}**（{len(NAMES)} 个被试内参数"
          f"{'，= 与 design_fim.py 的 9 设计名次可比' if param_mode == 'exp' else '，= 定稿文档的分析模型 shape_model=\"lin\"'}）")
    print(f"  真值：{ {k: round(v, 4) for k, v in TRUTH.as_dict().items() if k in NAMES} }")
    print(f"  ρ 扫描：{RHO_LIST}（ρ=1 即 M-T3，用作自检）")
    print(f"  参数向量（{N_FREE} 个）：{ALL_NAMES}")
    print(f"  信息矩阵：{n_fim} 份独立 M-T1 模拟取平均后求逆 → 预测 SE（Cramér–Rao 下界）")

    # ---------------- 自检 ----------------
    print("\n" + "=" * 118)
    print("自检（不过就不看下面的结果）")
    print("=" * 118)
    da = selfcheck_a()
    ok_a = da < SELFCHECK_A_TOL
    print(f"  A. ρ=1 时 M-T1 vs M-T3 逐试次对数似然（归一化最大绝对差）："
          f"{da:.3e}  判据 < {SELFCHECK_A_TOL:g}  {'✅' if ok_a else '❌'}")

    a_se, b_se, c_se, rel = selfcheck_b(n_fim=1)
    ok_b = bool(np.all(rel < SELFCHECK_B_TOL))
    print("  B. ρ=1 时**在同一份数据**上 M-T1 与 M-T3 的 SE（应逐位一致）：")
    print("     （`M-T1(ρ固定)` 与 M-T3 参数个数相同，应一致；"
          "`M-T1(ρ自由)` 多一个自由参数）")
    for i, nm in enumerate(NAMES):
        print(f"       {nm:10s} M-T1(ρ固定)={a_se[i]:9.5f}  M-T3={b_se[i]:9.5f}  "
              f"相对差={rel[i]:8.3%}   M-T1(ρ自由)={c_se[i]:9.5f}"
              f"  Δ={c_se[i]/b_se[i]-1:+7.1%}")
    print(f"     判据（ρ固定 vs M-T3）全部 < {SELFCHECK_B_TOL:.0%}  "
          f"{'✅' if ok_b else '❌'}")
    print("     ⚠️ 注意「ρ自由」那一列：把 ρ 当自由参数**会抬高其余参数的边际 SE**"
          "（ρ 与 `d_ref` 强相关）——这是真实代价，不是实现错误。")
    if not (ok_a and ok_b):
        print("\n  ❌ 自检未过 ⇒ 中止（下面的 M-T1 数字不可信）")
        return

    # ---------------- 主循环 ----------------
    print("\n" + "=" * 118)
    print("① 各设计在各 ρ 下的预测 SE（自然参数单位；最后一列 rho 的 SE 只在 ρ<1 有意义）")
    print("=" * 118)
    head = (f"{'设计':34s} {'rho':>5s} {'试次':>5s} " +
            " ".join(f"{n[:8]:>9s}" for n in ALL_NAMES) +
            f" {'遗漏':>6s} {'正确率':>7s} {'RTms':>7s}")
    results = {}
    for rho in RHO_LIST:
        print("\n" + "-" * len(head))
        print(head)
        print("-" * len(head))
        for name, (T, W, r) in designs.items():
            bad = check_validity(T, W)
            if bad:
                print(f"{name:34s} {rho:5.2f}  ⚠️ 违反 C1（W > T+200ms）：{bad}（跳过）")
                continue
            t0 = time.time()
            res = design_se_step(T, W, r, rho, n_fim=n_fim)
            results[(name, rho)] = res
            print(f"{name:34s} {rho:5.2f} {res['n_trials']:5d} " +
                  " ".join(f"{v:9.4f}" for v in res["se"]) +
                  f" {res['omission']:6.3f} {res['acc']:7.3f} {res['rt_ms']:7.0f}"
                  f"   ({time.time()-t0:.1f}s)", flush=True)

    # ---------------- ② 相对 SE 与名次 ----------------
    truth_vec = np.array([TRUTH.as_dict()[n] for n in NAMES])

    print("\n" + "=" * 118)
    print("② 相对 SE 的几何平均（PRIMARY 参数集）与名次 —— 名次是否随 ρ 变化？")
    print("=" * 118)
    print(f"  {'rho':>6s}  按 PRIMARY 几何平均排序（越小越好）")
    print("  " + "-" * 106)
    ranks = {}
    for rho in RHO_LIST:
        ranking = []
        for name in designs:
            res = results.get((name, rho))
            if res is None:
                continue
            se7 = res["se"][:len(NAMES)]
            rel7 = se7 / np.abs(truth_vec)
            # PRIMARY 是按 exp 参数集定义的；lin 模式下 tau_T 不在 NAMES 里，
            # 于是「关注集」自动退化为 {d_ref, beta_T, beta_S, beta_ST}。
            pri = [k for k in PRIMARY if k in NAMES]
            g_pri = float(np.exp(np.mean(np.log(
                [rel7[NAMES.index(k)] for k in pri]))))
            ranking.append((g_pri, name))
        ranking.sort()
        ranks[rho] = [nm.split()[0] for _, nm in ranking]
        print(f"  {rho:6.2f}  " +
              " > ".join(f"{nm.split()[0]}({g:.3f})" for g, nm in ranking))

    print("\n  👉 名次稳定性检查：")
    base = ranks[RHO_LIST[0]]
    for rho in RHO_LIST[1:]:
        cur = ranks[rho]
        moved = [(i, base[i], cur[i]) for i in range(min(len(base), len(cur)))
                 if base[i] != cur[i]]
        if not moved:
            print(f"     ρ={rho:.2f}：与 ρ=1.00 **名次完全一致** ✅")
        else:
            print(f"     ρ={rho:.2f}：有 {len(moved)} 处名次变化 ⚠️  "
                  + "; ".join(f"第{i+1}名 {a}→{b}" for i, a, b in moved))

    # ---------------- ③ 逐参数：M-T1 相对 M-T3 的 SE 变化 ----------------
    print("\n" + "=" * 118)
    print("③ 逐参数：M-T1 相对 M-T3 的 SE 比值（>1 = M-T1 下更难估）")
    print("=" * 118)
    print(head)
    for rho in RHO_LIST[1:]:
        print(f"\n  --- ρ = {rho:.2f} / ρ = 1.00 ---")
        for name in designs:
            r1 = results.get((name, 1.00))
            r2 = results.get((name, rho))
            if r1 is None or r2 is None:
                continue
            ratio = r2["se"] / np.maximum(r1["se"], 1e-300)
            se_show = list(r2["se"][:len(NAMES)]) + [r2["se"][-1]]
            print(f"{name:34s} {rho:5.2f} {r2['n_trials']:5d} " +
                  " ".join(f"{v:9.4f}" for v in se_show) +
                  f"   SE比={ ' '.join(f'{x:6.2f}' for x in ratio[:len(NAMES)] + [ratio[-1]]) }")

    # ---------------- ④ rho 本身的 SE ----------------
    print("\n" + "=" * 118)
    print("④ `rho` 自身的预测 SE（D33 的检验力问题在 CRLB 视角下的对应量）")
    print("=" * 118)
    print(f"  {'设计':34s} " + " ".join(f"ρ={r:>5.2f}" for r in RHO_LIST))
    for name in designs:
        txt = []
        for rho in RHO_LIST:
            res = results.get((name, rho))
            txt.append("   —   " if res is None else f"{res['se'][-1]:8.4f}")
        print(f"  {name:34s} " + " ".join(txt))
    _d4 = results.get(("D4        (4T×3W, r12)", 1.00))
    _d4rho = _d4["se"][-1] if _d4 is not None else float("nan")
    print(f"\n  ⚠️ 这里**不是**「ρ=1 时信息奇异」：实测 D4 在 ρ=1 处 `rho` 的 SE = "
          f"**{_d4rho:.4f}**（有限值）。")
    print("     与 §8.14/§8.17 的「ρ=1 标定时 0/10 拒绝」**不矛盾**：CRLB 是**局部**量，")
    print("     而检验力问的是「Δρ=0.25 能否被检出」——按本设计约 0.8 SE，本来就弱。")
    print("     ρ 越小 `rho` 的 SE 越小 ⇒ 与「单侧检验力」同向。")

    # ---------------- ⑤ 组层可信度：单人 SE → n=40/组 与 n=160 ----------------
    print("\n" + "=" * 118)
    print("⑤ 组层可信度：把单人 SE 换算到 n=40/组 与 n=160（4 个 P 组合并）")
    print("=" * 118)
    print("  组层 SE = 单人 SE / √n（固定效应、无 P×参数 交互时成立）；z = |真值| / 组层 SE。")
    print("  z ≥ 1.96 才能在双侧 α=0.05 下稳定检出。⚠️ 这是 CRLB，真实 MLE 只会更差（偏差+非线性）。")
    print("\n  " + f"{'设计':32s} {'rho':>5s} {'n':>5s} " +
          " ".join(f"{n[:9]:>10s}" for n in NAMES))
    for name in designs:
        for rho in RHO_LIST:
            res = results.get((name, rho))
            if res is None:
                continue
            for n in (40, 160):
                se_n = res["se"][:len(NAMES)] / np.sqrt(float(n))
                z = np.abs(truth_vec) / np.maximum(se_n, 1e-300)
                print(f"  {name:32s} {rho:5.2f} {n:5d} " +
                      " ".join(f"{v:10.2f}" for v in z))
    print("\n  说明：D31/D32 的处方是 **n=40/组**，每个 P 组单独估计；"
          "`n=160` 一列是「若把 4 个 P 组合并估计同一个固定效应」的上限。")

    print("\n" + "=" * 118)
    print("限定（与 design_fim.py 相同的三条 + 一条新的）")
    print("=" * 118)
    print("  1. Cramér–Rao 下界；真实 MLE 只会更差。")
    print("  2. 聚合被试（不含随机效应）；固定 n_subj 下比较单人 SE 与比较被试量等价。")
    print("  3. OPG 而非 Hessian（小曲率参数在二阶差分下会被浮点噪声淹没）。")
    print("  4. ⚠️ 生成与似然都在 M-T1 下、真值是**同一个** `TRUTH`（P=120 的代表值）；")
    print("     这是「模型正确指定」的理想情形，不含误设代价。")
    print("  5. ⚠️ ρ 的 SE 只在 ρ<1 有意义；ρ=1 处 M-T1 退化进 M-T3，ρ 的方向是平坦的。")


if __name__ == "__main__":
    import io

    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    if out_path:
        buf = io.StringIO()
        real = sys.stdout

        class _Tee(io.TextIOBase):
            def write(self, s):
                real.write(s)
                buf.write(s)
                return len(s)

        sys.stdout = _Tee()
        try:
            main()
        finally:
            sys.stdout = real
            Path(out_path).write_text(buf.getvalue(), encoding="utf-8")
            real.write(f"\n[日志已写入 {out_path}]\n")
    else:
        main()
