# -*- coding: utf-8 -*-
"""
design_fim.py —— 用期望信息量（Fisher / OPG）比较候选设计（Stage 4）
====================================================================
**为什么不用「模拟→拟合→看恢复」**：一个设计 × 真值单元要几十次逐被试拟合
（实测 ≈ 3 s/人，4×30 人 ≈ 6 分钟），全网格要几小时。而设计比较真正需要的
只是**预测精度**，这可以用信息量在**不到一秒**内算出（最优实验设计的标准工具，
Myung & Pitt；Cavagnaro et al.）。

为什么是 OPG（逐试次得分外积）而不是 Hessian
--------------------------------------------
第一版用 `numerical_hessian` + `pinv`，输出 ``bT~bST = −1.4e113`` 这样的垃圾相关，
且 768 试次的 D4-rep16 给出的 ``δa`` SE 反而比 576 试次的 D4 大 4 倍。
根因在二阶中心差分：浮点噪声 ``~1e−13`` **直接**与信号 ``C·h²`` 竞争，
而本例 δa=0.55 只让 a 在 W 范围内变 6.7%（跨度 0.134），曲率太小，信号沉在噪声下。
OPG 里噪声以**平方**进入，且天然半正定。实测 cond ≈ 8×10⁴，无退化方向。

    对比（同一份 D4 数据）：Hessian 用 28.5 s，OPG 用 0.08 s。

因为便宜，这里把**信息矩阵在 ``N_FIM`` 份独立模拟上取平均后再求逆**
（``E[I]`` 才是 Fisher 信息量；先求逆再平均是对非线性函数取平均，有 Jensen 偏差）。

⚠️ 三个必须记住的限定
--------------------
1. 这是 **Cramér–Rao 下界**（大样本、正则条件下最优）。真实 MLE 只会更差。
2. 逐被试设计比较用**“聚合被试”**（= n_subj 名被试的试次合并、不含随机效应）。
   被试内参数是逐被试估计后再平均，组层 SE ≈ 单人 SE / √n_subj，
   故**固定 n_subj** 下比较单人 SE 与被试量比较等价。
3. 当前生成器是**恒定漂移（M-T3）**。因决策 D5（按键即结束试次），
   严格应换成 M-T1（漂移在 t = T 处阶跃）。本脚本在 M-T3 下成立，
   **M-T1 的影响见 README §8.4 待办**。

用法
----
    python design_fim.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from likelihood import fim_diagnostics, opg_information, trials_from_arrays  # noqa: E402
from mapping import WITHIN_FREE, MappingParams  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

P_SINGLE = 120.0            # 逐被试设计比较：固定 P，使 P 相关项恒为 0
T_REF, W_REF = 0.10, 1.20

#: 被试内真值（已按实测正确率 0.72–0.89 校准）
TRUTH = MappingParams(
    P_ref=P_SINGLE, T_ref=T_REF, W_ref=W_REF,
    d_ref=0.70, beta_T=0.55, tau_T=0.080,
    beta_S=0.16, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
    #: 起点通道（D118）。``0.10`` 是**设计用**的圆整值：实测 87 人反解出
    #: ``β_S≈0.19、Δz_S≈0.085``（模型章 §3.15.3）。CRLB 对 dz_S 的 SE 几乎
    #: 不依赖真值大小（信息量 ∝ 该参数带来的试次级差异），故 0.085/0.10
    #: 给出的人数是同一个量级。取 0 会让相对 SE 除以 0，故不能留默认值。
    dz_S=0.10,
)

#: 论文里真正要解释的参数（用于给设计排总名次）。
#: 2026-10-22（D118）把 ``dz_S`` 并入：判据通道现在是主假设 H4 的一半，
#: 不排进 PRIMARY 会让「设计是否够用」的结论漏掉它。
PRIMARY = ["d_ref", "beta_T", "tau_T", "beta_S", "beta_ST", "dz_S"]
#: W→a 通路（P1 曾发现只有 6.7% 变化，单独看）
A_PATH = ["a_ref", "delta_a", "tau_a"]

#: 候选设计（只列被试内部分；P 由被试间决定）
#: 名称 -> (T 水平, W 水平, 每单元重复次数)
DESIGNS = {
    "D4        (4T×3W, r12)": ([0.0333, 0.0833, 0.14999, 0.24998],
                               [0.79998, 1.19990, 1.79990], 12),
    "D4-3T     (3T×3W, r16)": ([0.0333, 0.0833, 0.14999],
                               [0.79998, 1.19990, 1.79990], 16),
    "D4-rep8   (4T×3W, r8)": ([0.0333, 0.0833, 0.14999, 0.24998],
                              [0.79998, 1.19990, 1.79990], 8),
    "D4-rep16  (4T×3W, r16)": ([0.0333, 0.0833, 0.14999, 0.24998],
                               [0.79998, 1.19990, 1.79990], 16),
    "W-low     (4T×{600,900,1300})": ([0.0333, 0.0833, 0.14999, 0.24998],
                                      [0.59996, 0.89994, 1.29990], 12),
    "W-high    (4T×{1000,1400,1900})": ([0.0333, 0.0833, 0.14999, 0.24998],
                                        [0.99990, 1.39990, 1.89990], 12),
    "W-wide    (4T×{500,1200,2000})": ([0.0333, 0.0833, 0.14999, 0.24998],
                                       [0.50000, 1.19990, 2.00000], 12),
    "T-wide    (T到400, W-high)": ([0.0333, 0.0833, 0.20000, 0.39997],
                                   [0.99990, 1.39990, 1.89990], 12),
    "A-screen  (2T×2W, r16)": ([0.0333, 0.14999], [0.79998, 1.79990], 16),
}

#: 参数名与顺序**直接跟随** ``mapping.WITHIN_FREE``（exp 形式，当前 10 个，
#: 含 ``dz_S``）——加参数时这里自动跟上，不需要改本文件。
NAMES = list(WITHIN_FREE)
N_FIM = 12                  # 平均信息矩阵的独立模拟份数


def check_validity(T_levels, W_levels):
    """约束 C1：W > T + 200 ms。"""
    return [(T, W) for T in T_levels for W in W_levels if W <= T + 0.2]


def design_se(T_levels, W_levels, n_rep, truth=TRUTH, n_fim=N_FIM, seed=0):
    """返回该设计的预测 SE、参数相关矩阵、信息矩阵病态与行为诊断。

    ``se`` 为按平均信息矩阵求逆得到的 Cramér–Rao 下界（自然参数单位）。
    ``se_sd`` 为逐模拟份数 SE 的标准差 —— 用来判断设计之间的差异是否大于蒙特卡洛噪声。
    """
    design = build_design(P_SINGLE, T_levels, W_levels, n_rep)
    n_trials = design["T"].size

    Is, ses_i = [], []
    om, acc, rt_mean = [], [], []
    for r in range(n_fim):
        rng = np.random.default_rng(seed + 1000 * r)
        sim = simulate_subject(design, truth, rng)
        tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                *design_arrays(design))
        I, _ = opg_information(tr, NAMES, truth)
        Is.append(I)
        ses_i.append(np.sqrt(np.maximum(np.diag(np.linalg.pinv(I)), 0.0)))

        # 行为诊断
        om.append(float(sim["omission"].mean()))
        resp = sim["omission"] == 0
        is_match = np.asarray(design["is_match"]) == 1
        ok = np.where(is_match, sim["side"] == 1, sim["side"] == 0)
        acc.append(float(np.mean(ok[resp])))
        rt_mean.append(float(np.nanmean(sim["rt"])))

    I_mean = np.mean(Is, axis=0)
    cov = np.linalg.pinv(I_mean)
    d = np.sqrt(np.maximum(np.diag(cov), 1e-300))
    corr = cov / np.outer(d, d)
    diag = fim_diagnostics(I_mean, NAMES)

    return {
        "n_trials": n_trials,
        "se": np.sqrt(np.maximum(np.diag(cov), 0.0)),
        "se_sd": np.std(np.asarray(ses_i), axis=0),
        "corr": corr,
        "cond": diag["cond"], "n_bad": diag["n_bad"],
        "omission": float(np.mean(om)),
        "acc": float(np.mean(acc)),
        "rt_ms": float(np.mean(rt_mean) * 1000),
        "T": T_levels, "W": W_levels, "rep": n_rep,
    }


def main():
    truth_vec = np.array([TRUTH.as_dict()[n] for n in NAMES])
    print("=" * 112)
    print("Stage 4 · 候选设计比较（期望信息量 / OPG Fisher 信息量）")
    print("=" * 112)
    print(f"  真值：{ {k: round(v, 4) for k, v in TRUTH.as_dict().items() if k in NAMES} }")
    print(f"  信息矩阵：{N_FIM} 份独立模拟取平均后求逆 → 预测 SE（Cramér–Rao 下界）")
    print(f"  参数：{NAMES}")
    print(f"  关注集 PRIMARY={PRIMARY}\n  A 通路  A_PATH={A_PATH}\n")

    results = {}
    for name, (T, W, r) in DESIGNS.items():
        bad = check_validity(T, W)
        if bad:
            print(f"  ⚠️ {name} 违反约束 W > T+200：{bad}（跳过）")
            continue
        t0 = time.time()
        res = design_se(T, W, r)
        res["valid"] = True
        results[name] = res
        print(f"  已算 {name:34s} 试次={res['n_trials']:4d}  "
              f"遗漏={res['omission']:.3f} 正确率={res['acc']:.3f}  "
              f"RT={res['rt_ms']:.0f}ms  cond={res['cond']:.1e}  "
              f"({time.time()-t0:.1f}s)", flush=True)

    head = f"{'设计':34s} {'试次':>5s} " + " ".join(f"{n[:8]:>9s}" for n in NAMES)
    sep = "-" * len(head)

    # ---------------- 1. 预测 SE ----------------
    print("\n" + "=" * 112)
    print("① 预测标准误 SE（越小越好；单位 = 参数自身单位）")
    print("=" * 112)
    print(head); print(sep)
    for name, res in results.items():
        print(f"{name:34s} {res['n_trials']:5d} " +
              " ".join(f"{v:9.4f}" for v in res["se"]))

    # ---------------- 2. 相对 SE ----------------
    print("\n" + "=" * 112)
    print("② 相对 SE = SE / |真值|（<0.3 好；0.3–1 勉强；>1 实际不可用）")
    print("=" * 112)
    print(head); print(sep)
    rel = {}
    for name, res in results.items():
        rel[name] = res["se"] / np.abs(truth_vec)
        print(f"{name:34s} {res['n_trials']:5d} " +
              " ".join(f"{v:9.3f}" for v in rel[name]))
    print("\n  真值量纲参考：" + "  ".join(f"{n}={v:.3f}" for n, v in zip(NAMES, truth_vec)))

    # ---------------- 3. 相对 D4 ----------------
    base = results.get("D4        (4T×3W, r12)")
    if base is not None:
        print("\n" + "=" * 112)
        print("③ 相对 D4 的 SE 比值（<1 = 比 D4 更准）")
        print("=" * 112)
        print(head); print(sep)
        for name, res in results.items():
            print(f"{name:34s} {res['n_trials']:5d} " +
                  " ".join(f"{v/b:9.3f}" for v, b in zip(res["se"], base["se"])))

    # ---------------- 4. 总名次 ----------------
    print("\n" + "=" * 112)
    print("④ 总名次：相对 SE 的几何平均（越小越好），以及蒙特卡洛可辨性")
    print("=" * 112)
    print(f"  {'设计':34s} {'试次':>5s} {'PRIMARY':>9s} {'A通路':>9s} {'全部':>9s} "
          f"{'MC信噪':>8s}  判定")
    print("  " + "-" * 104)
    ranking = []
    for name, res in results.items():
        g_all = float(np.exp(np.mean(np.log(rel[name]))))
        g_pri = float(np.exp(np.mean(np.log([rel[name][NAMES.index(k)]
                                             for k in PRIMARY]))))
        g_a = float(np.exp(np.mean(np.log([rel[name][NAMES.index(k)]
                                           for k in A_PATH]))))
        mc = float(np.nanmean(res["se"] / np.maximum(res["se_sd"], 1e-12)))
        verdict = ("✅可用" if g_pri < 0.30 else
                   "⚠️勉强" if g_pri < 0.60 else "❌不可用")
        ranking.append((g_pri, name))
        print(f"  {name:34s} {res['n_trials']:5d} {g_pri:9.3f} {g_a:9.3f} "
              f"{g_all:9.3f} {mc:8.1f}  {verdict}")
    print("\n  按 PRIMARY 排序：" +
          " > ".join(f"{n.split()[0]}({g:.2f})" for g, n in sorted(ranking)))
    print("  MC信噪 = SE / 逐份SE的标准差；越大表示设计名次差异越不是蒙特卡洛噪声。")

    # ---------------- 5. 相关 ----------------
    print("\n" + "=" * 112)
    print("⑤ 关键参数相关（|r| 接近 1 = 互相补偿，几乎不可分开估计）")
    print("=" * 112)
    pairs = [("beta_T", "beta_ST"), ("beta_T", "tau_T"), ("beta_S", "beta_ST"),
             ("a_ref", "delta_a"), ("a_ref", "tau_a"), ("delta_a", "tau_a")]
    print(f"  {'设计':34s} " + " ".join(
        f"{a.replace('beta_','b').replace('_ref','')}~"
        f"{b.replace('beta_','b').replace('_ref','')}" for a, b in pairs))
    for name, res in results.items():
        C = res["corr"]
        txt = []
        for a, b in pairs:
            v = C[NAMES.index(a), NAMES.index(b)]
            v = 0.0 if not np.isfinite(v) else float(np.clip(v, -1, 1))
            txt.append(f"{v:+5.2f}")
        warn = "  ⚠️矩阵病态，相关不可信" if res["cond"] > 1e10 else ""
        print(f"  {name:34s} " + " ".join(f"{t:>9s}" for t in txt) + warn)

    # ---------------- 6. 效应量敏感性 ----------------
    print("\n" + "=" * 112)
    print("⑥ 效应量敏感性：W→a 的幅度 Δa 取不同值时，a 类参数与 a_ref 的预测 SE")
    print("=" * 112)
    print("  P1 曾发现 a 在 W 范围内只变 6.7%。这里检查：是设计的问题，还是效应量本身太小。")
    T_L, W_L, R_L = DESIGNS["D4        (4T×3W, r12)"]
    cols = ["a_ref", "delta_a", "tau_a"]
    print(f"\n  {'Δa':>6s} {'a 跨度':>9s} {'a跨度/a_ref':>12s} " +
          " ".join(f"{c+' SE':>11s}" for c in cols) + f" {'δa 相对SE':>11s}")
    for da in (0.2, 0.55, 1.0, 1.8):
        tr_ = TRUTH.replace(delta_a=da)
        a_vals = [tr_.a_ref + da * (np.exp(-W_REF / tr_.tau_a)
                                    - np.exp(-W / tr_.tau_a)) for W in W_L]
        span = max(a_vals) - min(a_vals)
        res = design_se(T_L, W_L, R_L, truth=tr_, n_fim=6)
        s = res["se"]
        i_da = NAMES.index("delta_a")
        print(f"  {da:6.2f} {span:9.3f} {span/tr_.a_ref:12.1%} " +
              " ".join(f"{s[NAMES.index(c)]:11.4f}" for c in cols) +
              f" {s[i_da]/da:11.2f}")

    print("\n" + "=" * 112)
    print("读法与限定")
    print("=" * 112)
    print("  1. 这是 **Cramér–Rao 下界**：真实 MLE 的精度只会更差，不是更好。")
    print("  2. 组层 SE ≈ 单人 SE / √n_subj（固定 n_subj 下，比较单人 SE 即等价）。")
    print("  3. 信息量用 OPG（逐试次得分外积）而非 Hessian，理由见模块 docstring：")
    print("     二阶差分的噪声 ~1e−13 会淹没小曲率参数（δa 的 a 跨度只有 0.13），")
    print("     导致 pinv 输出 1e113 量级的垃圾。OPG 噪声平方进入，实测 cond ~1e5。")
    print("  4. ⚠️ 当前生成器是**恒定漂移（M-T3）**；因决策 D5，严格应换 M-T1")
    print("     （漂移在 t = T 处从 d_stim 阶跃到 d_mask）。M-T1 列为 Stage 4 待办。")


if __name__ == "__main__":
    main()
