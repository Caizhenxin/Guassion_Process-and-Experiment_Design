# -*- coding: utf-8 -*-
"""
validate_step.py —— 两阶段漂移（M-T1）的独立验证
=================================================
被验对象：``wfpt.py`` 的 ``green`` / ``density_step`` / ``survival_step`` / ``p_upper_step``。

**为什么必须验证**：M-T1 是决策 D5 之后的正式模型，它的三个量（密度、存活、
最终吸收概率）各自用了不同的推导路径（Girsanov 密度、解析存活级数、相消恒等式），
任何一处系数或符号写错都会**单独**给出看似合理的结果。所以这里用**互相独立的判据**
交叉检查，而不是只检查一条。

判据清单
--------
W1 **退化**：``v1 == v2`` 时必须逐点回到单阶段 ``flux`` / ``survival_series`` / ``p_upper``。
W2 **T→0 极限**：``T → 0`` 时退化为单阶段 ``v2``（不是 ``v1``——阶段 2 覆盖全部时间）。
W3 **Green 归一 = 存活**（**最关键**）：``∫_0^a G(x,T;z,v1) dx`` 必须等于
   ``survival_series(v1,a,z,T)``。这两条走的是完全不同的推导：
   前者是 Girsanov 密度（含 ``e^{v(x−z)}`` 因子），后者是把同一密度对 x 积分后
   用 ``∫_0^a sin(kπx/a)e^{vx}dx`` 的闭式化简。**若 Girsanov 因子写成 ``e^{v(x−z)/2}``
   （另一本教科书的常见形式），W3 会立刻失败。**
W4 **质量守恒**：``∫_0^{t_max}(f_up+f_lo)dt + survival_step(t_max) = 1``。
W5 **密度 ↔ 存活一致**：由密度数值积分得到的 ``1−F(t)`` 必须等于解析 ``survival_step(t)``。
W6 **最终吸收概率一致**：``∫_0^∞ f_up dt`` 必须等于 ``p_upper_step``。
W7 **路径模拟独立复核**：用细步长 Euler 直接模拟两阶段过程，
   比较 deadline 遗漏率与正确率——这是与解析式完全不同的方法。

运行：``python validate_step.py``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from wfpt import (  # noqa: E402
    _time_grid, density, density_step, flux, p_upper, p_upper_step,
    survival_series, survival_step,
)

# 覆盖：居中/偏斜起点、正/负/零漂移、大/小边界、大/小 T
CASES = [
    dict(name="居中/正漂移", v1=0.5, v2=0.0, a=2.0, z=1.0, T=0.25),
    dict(name="居中/负漂移", v1=-0.5, v2=0.0, a=2.0, z=1.0, T=0.25),
    dict(name="偏斜起点", v1=0.8, v2=0.2, a=1.5, z=0.4, T=0.10),
    dict(name="零漂移", v1=0.0, v2=0.0, a=2.0, z=1.0, T=0.20),
    dict(name="小 T", v1=0.6, v2=0.0, a=2.0, z=1.0, T=0.033),
    dict(name="大 T", v1=0.6, v2=0.0, a=2.0, z=1.0, T=0.50),
    dict(name="小边界", v1=1.0, v2=-0.3, a=0.9, z=0.45, T=0.15),
]

# W4/W5 的时间积分上限：必须大到尾部可忽略，否则与 p_upper_step 不可比
TAIL_MAX = 15.0


def w1_degenerate():
    print("\n" + "=" * 100)
    print("W1 退化：v1 == v2 时必须逐点回到单阶段公式")
    print("=" * 100)
    print(f"{'case':<12}{'v':>7}{'max|Δf_up|':>13}{'max|Δf_lo|':>13}"
          f"{'max|ΔS|':>12}{'Δp_upper':>12}  判定")
    ok = True
    for c in CASES:
        v, a, z, T = c["v1"], c["a"], c["z"], c["T"]
        t = np.linspace(0.01, 2.0, 60)
        f_u0, f_l0 = density(t, v, a, z)
        # n_x=801：Green 卷积的梯形误差是 O(dx²)，用细网格把「离散化误差」
        # 与「公式错误」分开。判据取**相对**密度量级——绝对阈值会把 W3 已经
        # 量化的离散化误差误判成公式错误（开发期实测：n_x=161 时残差 ~2e-8，
        # 正好等于 2e-5 × 峰值密度）。
        f_u1, f_l1 = density_step(t, v, v, a, z, T, n_x=801)
        scale_u = max(float(np.max(f_u0)), 1e-12)
        scale_l = max(float(np.max(f_l0)), 1e-12)
        d_fu = float(np.max(np.abs(f_u1 - f_u0))) / scale_u
        d_fl = float(np.max(np.abs(f_l1 - f_l0))) / scale_l
        ts = np.array([0.05, 0.3, 0.9, 1.5])
        d_s = float(np.max(np.abs(
            survival_step(v, v, a, z, T, ts) - survival_series(v, a, z, ts)
        )))
        d_p = abs(p_upper_step(v, v, a, z, T) - float(p_upper(v, a, z)))
        good = d_fu < 1e-5 and d_fl < 1e-5 and d_s < 1e-7 and d_p < 1e-9
        ok &= good
        print(f"{c['name']:<12}{v:>7.2f}{d_fu:>13.2e}{d_fl:>13.2e}"
              f"{d_s:>12.2e}{d_p:>12.2e}  {'✅' if good else '❌'}")
    print("  （d_fu/d_fl 为相对峰值密度的误差；n_x=801）")
    return ok


def w2_zero_T():
    print("\n" + "=" * 100)
    print("W2 T→0 极限：应退化为单阶段 v2")
    print("=" * 100)
    print(f"{'case':<12}{'max|Δf_up|':>13}{'max|ΔS|':>12}{'Δp_upper':>12}"
          f"{'n_x=161':>11}{'下降':>8}  判定")
    ok = True
    for c in CASES:
        v1, v2, a, z = c["v1"], c["v2"], c["a"], c["z"]
        T = 1e-12
        t = np.linspace(0.01, 2.0, 60)
        f_u0, _ = density(t, v2, a, z)
        f_u1, _ = density_step(t, v1, v2, a, z, T, n_x=801)
        d_fu = float(np.max(np.abs(f_u1 - f_u0)))
        ts = np.array([0.05, 0.3, 0.9, 1.5])
        d_s = float(np.max(np.abs(
            survival_step(v1, v2, a, z, T, ts, n_x=801) - survival_series(v2, a, z, ts)
        )))
        d_p = abs(p_upper_step(v1, v2, a, z, T, n_x=801) - float(p_upper(v2, a, z)))
        # T→0 时 Green 退化为 δ，只能以格点插值表示，误差是 O(dx²)——
        # 这是**离散化**而非公式问题。因此判据有两条：
        #   ① 绝对误差 < 1e-5（n_x=801）；
        #   ② **加密收敛**：n_x 161→801（dx 小 5×）时误差至少降 5×（理论 25×）。
        # 只卡①会把 O(dx²) 误判为公式错误；只卡②会放过系统性偏差。两条一起
        # 才能把「离散化」与「公式错」分开——这正是 W3/W4 分开检验的理由。
        fu_lo, _ = density_step(t, v1, v2, a, z, T, n_x=161)
        d_lo = float(np.max(np.abs(fu_lo - f_u0)))
        conv_ok = bool(d_lo < 1e-9 or d_fu < d_lo / 5.0)
        good = d_fu < 1e-5 and d_s < 1e-5 and d_p < 1e-5 and conv_ok
        ok &= good
        print(f"{c['name']:<12}{d_fu:>13.2e}{d_s:>12.2e}{d_p:>12.2e}"
              f"{d_lo:>11.2e}{d_lo / max(d_fu, 1e-300):>10.1f}×  {'✅' if good else '❌'}")
    print("  （T=1e-12 走 δ 分支；末列为 n_x 161→801 的误差下降倍数，理论 25×）")
    return ok


def w3_green_normalisation():
    print("\n" + "=" * 100)
    print("W3 ★关键★ Green 归一化 == 解析存活（两条独立推导的交叉点）")
    print("=" * 100)
    print(f"{'case':<12}{'T':>7}{'∫G dx':>14}{'survival_series':>17}{'相对差':>12}  判定")
    from wfpt import _x_grid, green  # noqa: E402

    ok = True
    for c in CASES:
        v1, a, z, T = c["v1"], c["a"], c["z"], c["T"]
        for n_x in (161, 801):
            xs = _x_grid(a, n_x)
            G = green(xs, T, v1, a, z)
            w = np.gradient(xs)
            mass = float(np.sum(G * w))
            s_ref = float(survival_series(v1, a, z, np.array([T]))[0])
            rel = abs(mass - s_ref) / max(abs(s_ref), 1e-12)
            good = rel < (5e-3 if n_x == 161 else 1e-3)
            if n_x == 801:
                ok &= good
            print(f"{c['name']:<12}{T:>7.3f}{mass:>14.6f}{s_ref:>17.6f}"
                  f"{rel:>12.2e}  {'✅' if good else '❌'} (n_x={n_x})")
    return ok


def w4_w5_mass_and_consistency():
    print("\n" + "=" * 100)
    print("W4/W5 质量守恒 + 密度↔存活一致（t_max=15 s，n_grid=4000）")
    print("=" * 100)
    print(f"{'case':<12}{'∫f_up':>12}{'p_upper':>12}{'质量总和':>12}"
          f"{'max|ΔS|':>12}{'截尾质量':>12}  判定")
    ok = True
    for c in CASES:
        v1, v2, a, z, T = c["v1"], c["v2"], c["a"], c["z"], c["T"]
        # t_max 必须足够大，否则 ∫f_up 与 p_upper_step 是**不可比**的两件事：
        # 前者被截到 t_max，后者含全部尾部。开发期实测 a=2 时 E=3 s 的尾部
        # 恰好是 (4/π)e^{−π²·3/8}/2 ≈ 0.0157，正是当时被误读成「公式错」的
        # 那个「恒定亏损」。这里把 t_max 提到 15 s，使尾部 ~e^{−π²·15/8} ≈ 9e-9，
        # 同时把尾部单独列出来，避免再次把截尾误差误判成公式错误。
        tg = _time_grid(TAIL_MAX, 4000, 2.5)
        f_up, f_lo = density_step(tg, v1, v2, a, z, T, n_x=161)
        dt = np.diff(tg)
        F_up = np.concatenate([[0.0], np.cumsum(0.5 * (f_up[1:] + f_up[:-1]) * dt)])
        F_lo = np.concatenate([[0.0], np.cumsum(0.5 * (f_lo[1:] + f_lo[:-1]) * dt)])
        mass_up = float(F_up[-1])
        tail = float(survival_step(v1, v2, a, z, T, TAIL_MAX))
        mass_total = float(F_up[-1] + F_lo[-1] + tail)
        p_up = p_upper_step(v1, v2, a, z, T)
        d_p = abs(mass_up - p_up)
        # W5：解析存活 vs 由密度积分得到的存活
        sel = np.array([0.2, 0.5, 1.0, 2.0])
        S_ana = np.atleast_1d(survival_step(v1, v2, a, z, T, sel))
        S_num = np.interp(sel, tg, 1.0 - F_up - F_lo)
        d_s = float(np.max(np.abs(S_ana - S_num)))
        good = abs(mass_total - 1.0) < 5e-3 and d_p < 5e-3 and d_s < 5e-3
        ok &= good
        print(f"{c['name']:<12}{mass_up:>12.6f}{p_up:>12.6f}{mass_total:>12.6f}"
              f"{d_s:>12.2e}{1.0 - mass_total:>12.2e}  {'✅' if good else '❌'}")
    return ok


def w7_path_simulation():
    print("\n" + "=" * 100)
    print("W7 路径模拟独立复核（细步长 Euler，dt=2e-4，n=6000）")
    print("=" * 100)
    print(f"{'case':<12}{'deadline':>9}{'遗漏·模拟':>11}{'遗漏·解析':>11}"
          f"{'正确率·模拟':>13}{'正确率·解析':>13}  判定")
    rng = np.random.default_rng(20261014)
    dt, n = 2e-4, 6000
    ok = True
    for c in CASES:
        v1, v2, a, z, T = c["v1"], c["v2"], c["a"], c["z"], c["T"]
        deadline = 1.2
        nstep = int(deadline / dt)
        x = np.full(n, z)
        alive = np.ones(n, bool)
        tau = np.full(n, np.inf)
        side = np.zeros(n, int)
        for i in range(nstep):
            idx = alive
            if not np.any(idx):
                break
            vv = v1 if (i * dt) < T else v2
            x[idx] = x[idx] + vv * dt + np.sqrt(dt) * rng.standard_normal(int(idx.sum()))
            hit = idx & ((x <= 0.0) | (x >= a))
            if np.any(hit):
                tau[hit] = (i + 1) * dt
                side[hit] = (x[hit] >= a).astype(int)
                alive &= ~hit
        om_sim = float(np.mean(~np.isfinite(tau)))
        resp = ~(~np.isfinite(tau))
        acc_sim = float(np.mean(side[resp] == 1)) if np.any(resp) else float("nan")
        om_ana = float(np.atleast_1d(survival_step(v1, v2, a, z, T, deadline))[0])
        p_up = p_upper_step(v1, v2, a, z, T)
        F_up = 1.0 - p_up  # 占位，下面用密度积分算 deadline 前的正确率
        tg = _time_grid(deadline, 1200, 2.0)
        f_up, _ = density_step(tg, v1, v2, a, z, T)
        dtg = np.diff(tg)
        P_up_hit = float(np.sum(0.5 * (f_up[1:] + f_up[:-1]) * dtg))
        acc_ana = P_up_hit / max(1.0 - om_ana, 1e-12)
        d_om = abs(om_sim - om_ana)
        d_acc = abs(acc_sim - acc_ana)
        good = d_om < 0.02 and d_acc < 0.03
        ok &= good
        print(f"{c['name']:<12}{deadline:>9.2f}{om_sim:>11.4f}{om_ana:>11.4f}"
              f"{acc_sim:>13.4f}{acc_ana:>13.4f}  {'✅' if good else '❌'}")
    return ok


def main():
    t0 = time.time()
    print("=" * 100)
    print("validate_step.py —— 两阶段漂移（M-T1）验证")
    print("=" * 100)
    res = {
        "W1 退化 (v1==v2)": w1_degenerate(),
        "W2 T→0 极限": w2_zero_T(),
        "W3 Green 归一 == 存活": w3_green_normalisation(),
        "W4/W5 质量守恒 + 密度↔存活": w4_w5_mass_and_consistency(),
        "W7 路径模拟复核": w7_path_simulation(),
    }
    print("\n" + "=" * 100)
    print("汇总")
    print("=" * 100)
    for k, v in res.items():
        print(f"  {k:<34} {'✅ 通过' if v else '❌ 失败'}")
    print(f"\n总耗时 {time.time() - t0:.1f} s")
    return 0 if all(res.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
