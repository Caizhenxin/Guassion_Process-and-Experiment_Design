# -*- coding: utf-8 -*-
"""check_exp_conditions.py —— 正式采集前的**设计对齐核查**

**动机**
本项目的全部仿真结论（D22/D28/D29/D31–D36）都建立在 **D4** 上：

    P 被试间 ∈ {0, 8, 32, 120} ｜ T×W 被试内全交叉 ∈ {33.3, 83.3, 150, 250} × {800, 1200, 1800} ms
    × 自我/他人 × 匹配/不匹配 × 12 重复 = 576 试次/人

但实验程序 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` 的条件表（L172–182）是
**九个手挑组合、每人只跑一行**（L183 ``currentCondition = conditions(groupID, :)``）
⇒ 那是 **T 与 W 都做被试间**（P 也是被试间）的设计；D4 只有 P 是**被试间**，
T×W 是**被试内**。两者在 T/W 两个因子上结构不相容，且 T/W 水平取值也不同。

本脚本**不改任何设计**，只把两张表按 D4 的似然口径逐条量化，回答：

  1. 每条条件的**反应窗口**够不够用？时间轴自刺激 onset 起算
     （`Exp_Design_Formal.m` L452–455：``responseTime = GetSecs() − stimulusFlipTime``），
     掩蔽段固定 200 ms（L198）⇒ 掩蔽结束后真正可按键的时间只剩 ``W − T − 0.2``；
  2. 每条条件里有多少**刺激呈现期内按键**（``RT < T``）——M-T2/D5 那条腿唯一能吃到的试次。

★ 全部量都是**逐试次算完再平均**（``mean_t P_t``），不是「先把参数平均再代入」——
  因为匹配/不匹配会让 ``v`` 反号，参数均值接近 0，代入会给出完全错误的数。

真值用 D4 的 `lin` / `exp` 两族；⚠️ 真值是**仿真假设**，不是实采结果，
本脚本只用来判断设计是否**退化**（窗口被截断、目标类别为空）。

用法：``python _scratch/check_exp_conditions.py [输出路径]``
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

from mapping import MappingParams, match_lin_to_exp
from simulate import build_design, design_arrays
from wfpt import survival_series, survival_step

MASK_DURATION = 0.2           # `Exp_Design_Formal.m` L198
T_LEVELS_D4 = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS_D4 = [0.79998, 1.19990, 1.79990]
N_REP_D4 = 12
RHO_NEUTRAL = 0.5             # M-T1 掩蔽后的漂移比例，取中性代表

TRUTH_EXP = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70, t0=0.22,
    z_ratio=0.50, shape_model="exp")
TRUTH_LIN, _ = match_lin_to_exp(TRUTH_EXP, T_LEVELS_D4, W_LEVELS_D4)

#: `Exp_Design_Formal.m` L173–181 的九条条件（组号, P, T, W, M=1 有掩蔽）
EXP_CONDITIONS = [
    (1, 0.0, 0.03, 0.30, 1),
    (2, 0.0, 0.03, 0.60, 1),
    (3, 120.0, 0.03, 0.60, 1),
    (4, 120.0, 0.08, 0.60, 1),
    (5, 8.0, 0.10, 1.10, 1),
    (6, 120.0, 0.50, 1.50, 1),
    (7, 8.0, 0.10, 1.10, 0),
    (8, 120.0, 0.03, 0.80, 1),
    (9, 120.0, 0.08, 0.80, 1),
]


def _arms(TRUTH):
    """从 MappingParams 里取出逐试次的 (v, a, z, t0)——建一个一次性设计只为拿这 4 个数组。"""
    return design_arrays(build_design(120.0, [0.10], [1.20], 1)), TRUTH


def _cond_stats(P, T, W, masked, TRUTH, rho):
    """逐试次算完再平均。返回 dict。"""
    d = build_design(P, [T], [W], N_REP_D4)
    tp = tp_from_design(d, TRUTH)
    v = np.asarray(tp["v"], dtype=float)
    a = np.asarray(tp["a"], dtype=float)
    z = np.asarray(tp["z"], dtype=float)
    t0 = float(np.mean(np.asarray(tp["t0"], dtype=float)))
    T = float(d["T"][0])
    W = float(d["W"][0])

    # 相位项 P(τ < T) = 1 − S(T)：逐试次算完再平均
    p_tau = 1.0 - survival_series(v, a, z, T)

    # 可观测的刺激期内按键 P(RT < T) = P(τ < T − t0)
    x_obs = T - t0
    if x_obs > 0:
        p_rt = 1.0 - survival_series(v, a, z, x_obs)
    else:
        p_rt = np.zeros_like(v)

    # v2 程序新记录的 Premask 类：掩蔽结束前按键 ⇒ RT < T + 0.2
    x_pre = T + MASK_DURATION - t0
    if x_pre > 0:
        p_pre = 1.0 - survival_series(v, a, z, x_pre)
    else:
        p_pre = np.zeros_like(v)

    # 作答概率与平均 RT：逐 (v,a,z) 分组调用 survival_step
    use_rho = rho if masked else 1.0
    tm = W - t0
    p_resp = np.zeros_like(v)
    mean_rt = np.full_like(v, np.nan)
    if tm > 0:
        g = np.linspace(1e-4, tm, 3000)
        uniq = np.unique(np.round(np.column_stack([v, a, z]), 10), axis=0)
        for row in uniq:
            vv, aa, zz = (float(x) for x in row)
            m = (np.abs(v - vv) < 1e-9) & (np.abs(a - aa) < 1e-9) & \
                (np.abs(z - zz) < 1e-9)
            p_resp[m] = 1.0 - float(survival_step(vv, use_rho * vv, aa, zz, T, tm))
            S = survival_step(vv, use_rho * vv, aa, zz, T, g, n_x=81)
            mean_rt[m] = t0 + float(np.trapezoid(np.atleast_1d(S), g))
    return {
        "p_tau": float(np.mean(p_tau)),
        "p_rt": float(np.mean(p_rt)),
        "p_pre": float(np.mean(p_pre)),
        "p_resp": float(np.mean(p_resp)),
        "mrt": float(np.nanmean(mean_rt)) if np.any(np.isfinite(mean_rt)) else np.nan,
        "window": W - T - MASK_DURATION,
        "n": int(v.size),
    }


def tp_from_design(d, TRUTH):
    from mapping import trial_params
    return trial_params(d, TRUTH)


print("=" * 118)
print("正式采集前的设计对齐核查：实验程序 `Exp_Design_Formal.m` 的条件表  vs  仿真设计的 D4")
print("=" * 118)
print("实验（L172–183）：九条手挑组合，`currentCondition = conditions(groupID, :)` ⇒ **每人只跑一行**")
print("                  ⇒ P、T、W **三者都是被试间**")
print("D4（全部仿真结论的依据）：P **被试间** ｜ T×W **被试内全交叉** ⇒ 每人 576 试次覆盖 12 个 T×W 格子")
print()
print("时间轴（自刺激 onset 起算，L452–455）: [0,T] 刺激 → [T,T+0.2] 掩蔽 → [T+0.2,W] 可按键")
print("⇒ 掩蔽结束后真正可按键的时长 = W − T − 0.2 ；deadline 在 onset + W")
print()

# ---- A. 实验条件表逐条量化 ----
for arm, TRUTH in (("lin", TRUTH_LIN), ("exp", TRUTH_EXP)):
    print("=" * 118)
    print(f"【A. 实验条件表逐条量化 ｜ 真值族 = {arm}（t0 = {TRUTH.t0 * 1000:.0f} ms，ρ 取中性 {RHO_NEUTRAL}）】")
    print("=" * 118)
    print(f"{'组':>3}{'P':>6}{'T(ms)':>8}{'W(ms)':>8}{'掩蔽':>5}{'可按键窗':>9}"
          f"{'P(作答)':>9}{'粗略遗漏':>9}{'P(τ<T)':>9}{'P(RT<T)':>9}{'P(premask)':>11}"
          f"{'平均RT':>9}  退化?")
    for gid, P, T, W, M in EXP_CONDITIONS:
        st = _cond_stats(P, T, W, bool(M), TRUTH, RHO_NEUTRAL)
        omit = 1.0 - st["p_resp"] * 4 / 4  # 单条件即单人全部试次
        flags = []
        if st["window"] <= 0:
            flags.append("窗口≤0")
        elif st["window"] < 0.15:
            flags.append("窗口极窄")
        if st["p_resp"] < 0.5:
            flags.append(f"遗漏{100 * (1 - st['p_resp']):.0f}%")
        if st["p_tau"] < 1e-4:
            flags.append("相位窗口空")
        if M == 0:
            flags.append("无掩蔽")
        print(f"{gid:>3}{P:>6.0f}{1000 * T:>8.0f}{1000 * W:>8.0f}{'有' if M else '无':>5}"
              f"{1000 * st['window']:>9.0f}{st['p_resp']:>9.3f}{omit:>9.3f}"
              f"{st['p_tau']:>9.4f}{st['p_rt']:>9.5f}{st['p_pre']:>11.4f}"
              f"{1000 * st['mrt']:>9.1f}  {'、'.join(flags) if flags else '—'}")

# ---- B. D4 的 12 个 T×W 格子 ----
print()
print("=" * 118)
print("【B. 对照：D4 的 12 个 (T, W) 格子（被试内；P 取各档，此处用 P=120 为代表）】")
print("=" * 118)
for arm, TRUTH in (("lin", TRUTH_LIN), ("exp", TRUTH_EXP)):
    print(f"  【{arm}】")
    print(f"    {'T(ms)':>8}{'W(ms)':>8}{'P(τ<T)':>9}{'P(RT<T)':>9}{'P(作答)':>9}{'遗漏':>8}{'平均RT':>9}")
    for T in T_LEVELS_D4:
        for W in W_LEVELS_D4:
            st = _cond_stats(120.0, T, W, True, TRUTH, RHO_NEUTRAL)
            print(f"    {1000 * T:>8.1f}{1000 * W:>8.0f}{st['p_tau']:>9.4f}{st['p_rt']:>9.5f}"
                  f"{st['p_resp']:>9.3f}{1 - st['p_resp']:>8.3f}{1000 * st['mrt']:>9.1f}")

print()
print("=" * 118)
print("读数（脚本不做决定，只摆数字）")
print("=" * 118)
print("1. 结构：实验 = P/T/W 三者被试间（每人一行）；D4 = 只有 P 被试间，T×W 被试内。**不相容**。")
print("2. 取值：实验 W ∈ {300,600,800,1100,1500}、T ∈ {30,80,100,500} ms；")
print("        D4   W ∈ {800,1200,1800}、T ∈ {33.3,83.3,150,250} ms。")
print("3. 组 1（P=0,T=30,W=300）：掩蔽后只剩 70 ms 可按键 ⇒ P(作答)≈0.004，几乎全遗漏。")
print("   组 2/3/8/9 的 W ∈ {600,800} ⇒ 遗漏率 59–74%，远高于 D4 的 20–59%。")
print("4. P(τ<T) 在实验表的 T ≤ 100 ms 各条上全为 0；只有组 6（T=500 ms）非零（≈0.30）。")
print("   ⇒ 若以实验表为准，M-T2（斜坡）那条腿同样吃不到试次。")
print("5. 两个可能的行动：(a) 以实验表为准 ⇒ 重写其条件表使之容纳 T×W 被试内与 D4 的水平；")
print("                   (b) 以 D4 为准 ⇒ 把 D4 写进程序。二者都需你们与导师确认（本脚本不改）。")
print()
print("⚠️ 本脚本只量化，不修改任何设计或实验代码。")
