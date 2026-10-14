"""check_fixtau_misspec.py —— τ_P 先验固定值的**误设代价**（D31 处方的前置检查）

问题
----
D31 的处方是「把 τ_P 从自由参数里去掉，先验固定」。§8.13 E 段证明这样能把
`beta_P` 的相对 SD 从 25.3%（n=10/组）降到 17.9%，n=40/组 时到 8.5%。
**但 E 段是把 τ_P 固定在真值 30 上算的**——那是最好情形。真实研究里 τ_P 只有
先验/文献值，一定不等于真值。固定一个**错**的 τ_P 会不会把 `beta_P` 系统性带偏？
偏多少？这是决定「处方能不能用」的关键问题，不能靠推断。

做法
----
1. **无噪声**：直接喂组模型在 4 个 P 水平上的期望值（每组等人数），
   令 `fit_between` 在 τ_P 固定为 prior 的条件下估计 `beta_P`。
   此时残差完全来自「形状记错」，得到的是**纯误设偏差**。
2. **有噪声**：用与 `recover_group.py` 完全相同的种子方案抽出 n=40/组 的被试真值
   （`make_subject_truth`），重复 `--repeats` 次，看误设偏差是否被抽样噪声淹没。

读法
----
- 无噪声行里 `beta_P` 随 prior 单调偏 → 该 prior 误设会**系统性**带偏结论。
- 只要 prior 在真值附近 ±2 倍以内、且无噪声 `beta_P` 偏差明显小于有噪声 SD，
  处方就可以用；否则必须把 τ_P 的**不确定性**写进论文的限制段。

用法
----
    python _scratch/check_fixtau_misspec.py [重复次数]
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mapping import f_P                                        # noqa: E402
from recover_group import (BASE_SEED, GROUP_FIT_NAMES_FIXED_TAU,  # noqa: E402
                           GROUP_INITS, GROUP_TRUTHS, P_COMMON_REF,
                           fit_between, make_subject_truth)

P_LEVELS = [0.0, 8.0, 32.0, 120.0]
PRIORS = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 80.0, 120.0]
N_PER_LEVEL = 40


def init4(shape):
    g = GROUP_INITS[shape]
    return [g.d_ref, g.beta_P, g.beta_S, g.beta_SP]


def noise_free(truth, P_levels):
    P = np.asarray(P_levels, float)
    reg = f_P(P, truth.tau_P) - f_P(P_COMMON_REF, truth.tau_P)
    return P, truth.d_ref + truth.beta_P * reg, truth.beta_S + truth.beta_SP * reg


def draw(P_levels, n_per, rep, truth):
    P_sub, d, s = [], [], []
    for P in P_levels:
        for k in range(n_per):
            seed = BASE_SEED + rep * 100000 + int(P) * 1000 + k
            rng = np.random.default_rng(seed)
            st, _ = make_subject_truth(truth, P, P_COMMON_REF, rng)
            P_sub.append(P)
            d.append(st.d_ref)
            s.append(st.beta_S)
    return np.array(P_sub), np.array(d), np.array(s)


def fit_fixed(P, d, s, prior, shape):
    out, rms, _ = fit_between(P, d, s, P_COMMON_REF, init4(shape),
                              fit_names=GROUP_FIT_NAMES_FIXED_TAU,
                              tau_p_fixed=prior)
    return out, rms


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    for shape in ("lin", "exp"):
        truth = GROUP_TRUTHS[shape]
        tP = float(truth.tau_P)
        print("=" * 104)
        print(f"τ_P 先验固定值的误设代价   ——   shape_model = {shape}"
              f"，真值 τ_P = {tP:g}，真值 β_P = {truth.beta_P:.4f}")
        print(f"  现行 P 水平 {[int(x) for x in P_LEVELS]}；"
              f"有噪声行 = 每组 {N_PER_LEVEL} 人 × {reps} 次重复")
        print("=" * 104)

        P_nf, d_nf, s_nf = noise_free(truth, P_LEVELS)

        # 有噪声：预先抽好 reps 批，避免每列重抽（同种子 ⇒ 各行可逐列比较）
        batches = [draw(P_LEVELS, N_PER_LEVEL, r, truth) for r in range(reps)]

        hdr = (f"  {'prior':>7s} {'prior/真值':>10s} "
               f"{'无噪声 β_P':>12s} {'偏差':>9s} {'偏差/真值':>10s} "
               f"{'有噪声 β_P 均值':>15s} {'SD':>8s} {'偏置':>9s} "
               f"{'d_ref 均值':>11s} {'β_SP 均值':>11s}")
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for prior in PRIORS:
            o_nf, _ = fit_fixed(P_nf, d_nf, s_nf, prior, shape)
            bp_nf = float(o_nf["beta_P"])
            bps, drefs, bsps = [], [], []
            for (P_b, d_b, s_b) in batches:
                o_b, _ = fit_fixed(P_b, d_b, s_b, prior, shape)
                bps.append(float(o_b["beta_P"]))
                drefs.append(float(o_b["d_ref"]))
                bsps.append(float(o_b["beta_SP"]))
            bps = np.array(bps)
            print(f"  {prior:7.1f} {prior / tP:10.2f} "
                  f"{bp_nf:12.4f} {bp_nf - truth.beta_P:9.4f} "
                  f"{(bp_nf - truth.beta_P) / truth.beta_P:9.1%} "
                  f"{bps.mean():15.4f} {bps.std(ddof=1):8.4f} "
                  f"{bps.mean() - truth.beta_P:9.4f} "
                  f"{np.mean(drefs):11.4f} {np.mean(bsps):11.4f}")

        print(f"\n  真值参照：β_P = {truth.beta_P:.4f}、d_ref = {truth.d_ref:.4f}、"
              f"β_S = {truth.beta_S:.4f}、β_SP = {truth.beta_SP:.4f}")
        # 逐 P 水平的真实回归自变量形状（供读「为什么偏」）
        reg = f_P(P_LEVELS, tP) - f_P(P_COMMON_REF, tP)
        print(f"  真 τ_P 下的 reg 向量 f_P(P)−f_P(P_ref)：{np.round(reg, 4).tolist()}")
        print()


if __name__ == "__main__":
    main()
