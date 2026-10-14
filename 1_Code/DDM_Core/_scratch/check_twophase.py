"""M-T1 敏感性：两阶段漂移到底改不改变**可观测的行为量**？

## 为什么问这个

决策 D5 使漂移在 ``t = T`` 处从 ``d_stim`` 阶跃到 ``d_mask``（M-T1），
Stage 3/4 的全部结论却是在恒定漂移 M-T3 下算出的。定稿前必须知道：
把 M-T3 换成 M-T1 会让**预测的正确率 / 遗漏率 / 平均 RT** 改变多少？

如果改变 < 2%，M-T3 就是设计用途上足够的近似，§8.8 的"影响可能很小"
可以从外推升级为实测；如果改变很大，Stage 4 必须整体重跑。

## 做法

对 D4 设计的 4 个 T 水平 × 3 个 W 水平（× 自我/非自我），用解析机器算三个量：

* ``P(上边界 | 有反应)`` —— 预测正确率
* ``P(未反应)`` —— deadline 遗漏率
* ``E[RT | 有反应] = t0 + E[tau | tau < deadline]``

对 ``d_mask = rho * d_stim`` 的 rho ∈ {0, 0.5, 1.0, 1.5, 2.0} 各算一遍。

★ ``rho == 1.0`` 时两阶段模型**在数学上恒等于**单阶段模型，所以这一列既是
敏感性报告的一个点，也是**整套两阶段机器的自检**（W1 的行为量版本）——
若不等于单阶段结果，说明 `density_step` 或 `survival_step` 用错了。

阶段 1 漂移由 lin 参数化给出（与 design_grid 的真值一致）：
    d(T) = d_ref + beta_T*(T - T_ref) [+ I_self*(beta_S + beta_ST*(T - T_ref))]
    a(W) = a_ref + delta_a*(W - W_ref)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from wfpt import (  # noqa: E402
    _time_grid, density_step, flux, survival_series, survival_step,
)

# ---- 与 design_grid.py 的 lin 真值一致 -------------------------------------
LIN = dict(d_ref=0.7000, beta_T=1.2790, beta_S=0.1600, beta_ST=0.2330,
           a_ref=2.0000, delta_a=0.2260, t0=0.2200)
T_REF, W_REF = 0.10, 1.20
Z_RATIO = 0.50

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]      # D4
W_LEVELS = [0.79998, 1.19990, 1.79990]             # D4
RHO_LIST = [0.0, 0.5, 1.0, 1.5, 2.0]

N_GRID = 4000


def drift_and_boundary(T: float, W: float, is_self: bool):
    d = LIN["d_ref"] + LIN["beta_T"] * (T - T_REF)
    if is_self:
        d += LIN["beta_S"] + LIN["beta_ST"] * (T - T_REF)
    a = LIN["a_ref"] + LIN["delta_a"] * (W - W_REF)
    return max(d, 1e-6), a


def observables(rho: float, T: float, W: float, is_self: bool):
    """返回 (正确率|反应, 遗漏率, E[RT|反应], 响应比例)。"""
    d, a = drift_and_boundary(T, W, is_self)
    v1 = d
    v2 = rho * d
    z = Z_RATIO * a
    t0 = LIN["t0"]
    deadline = T + W - t0              # tau 空间的 deadline（RT = t0 + tau）
    if deadline <= 0:
        return np.nan, np.nan, np.nan, np.nan

    tg = _time_grid(deadline, N_GRID, 2.0)
    if abs(rho - 1.0) < 1e-12:
        # 单阶段（M-T3）：rho==1 时两阶段与单阶段恒等，用作自检
        f_up = flux(a - z, v1, a, tg)
        f_lo = flux(z, -v1, a, tg)
        om = float(survival_series(v1, a, z, np.array([deadline]))[0])
    else:
        f_up, f_lo = density_step(tg, v1, v2, a, z, T, n_x=161)
        om = float(survival_step(v1, v2, a, z, T, deadline))

    dt = np.diff(tg)
    responded = float(np.trapezoid(f_up + f_lo, tg))
    if responded <= 0:
        return np.nan, om, np.nan, responded
    up = float(np.trapezoid(f_up, tg))
    acc = up / responded
    mrt = t0 + float(np.trapezoid(tg * (f_up + f_lo), tg)) / responded
    # 行为量口径：正确率按**所有试次**算（含遗漏，与程序记录一致）
    acc_all = up
    return acc_all, om, mrt, responded


def main() -> int:
    print("=" * 104)
    print("M-T1 敏感性：d_mask = rho * d_stim，对可观测行为量的影响（D4 设计，lin 真值）")
    print("=" * 104)
    print(f"真值 d_ref={LIN['d_ref']} beta_T={LIN['beta_T']} a_ref={LIN['a_ref']} "
          f"delta_a={LIN['delta_a']} t0={LIN['t0']}  z_ratio={Z_RATIO}")
    print(f"D4: T={T_LEVELS}  W={W_LEVELS}  网格 {N_GRID}\n")

    # ---------- 自检：rho == 1 必须与单阶段逐位一致 ----------
    print("-" * 104)
    print("自检：rho = 1.0 时两阶段机器必须复现单阶段（M-T3）结果")
    print("-" * 104)
    print(f"{'T':>8}{'W':>9}{'self':>6}{'单阶段 acc':>13}{'两阶段 acc':>13}"
          f"{'单阶段 om':>12}{'两阶段 om':>12}  {'判定':<6}")
    selfcheck_ok = True
    for T in T_LEVELS:
        for W in W_LEVELS:
            for is_self in (False, True):
                d, a = drift_and_boundary(T, W, is_self)
                z = Z_RATIO * a
                dl = T + W - LIN["t0"]
                tg = _time_grid(dl, N_GRID, 2.0)
                f1 = flux(a - z, d, a, tg)
                om1 = float(survival_series(d, a, z, np.array([dl]))[0])
                f2, fl2 = density_step(tg, d, d, a, z, T, n_x=161)
                om2 = float(survival_step(d, d, a, z, T, dl))
                dacc = abs(float(np.trapezoid(f1, tg)) - float(np.trapezoid(f2, tg)))
                dom = abs(om1 - om2)
                good = dacc < 1e-6 and dom < 1e-6
                selfcheck_ok &= good
                print(f"{T:>8.4f}{W:>9.5f}{str(is_self):>6}"
                      f"{float(np.trapezoid(f1, tg)):>13.6f}{float(np.trapezoid(f2, tg)):>13.6f}"
                      f"{om1:>12.6f}{om2:>12.6f}  {'OK' if good else 'FAIL':<6}")
    print(f"\n自检总判定：{'✅ 通过（两阶段机器可信）' if selfcheck_ok else '❌ 失败——先修机器'}\n")

    # ---------- 敏感性表 ----------
    print("-" * 104)
    print("敏感性：各 rho 下的行为量（仅非自我试次，D4 的 12 个 T×W 单元）")
    print("-" * 104)
    hdr = f"{'T':>8}{'W':>9}"
    for rho in RHO_LIST:
        hdr += f"{'acc(rho=%.1f)' % rho:>14}"
    print(hdr)
    base = {}
    for T in T_LEVELS:
        for W in W_LEVELS:
            row = f"{T:>8.4f}{W:>9.5f}"
            for rho in RHO_LIST:
                acc, om, mrt, resp = observables(rho, T, W, False)
                row += f"{acc:>14.4f}"
                base[(T, W, rho)] = (acc, om, mrt, resp)
            print(row)

    print(f"\n{'T':>8}{'W':>9}" + "".join(f"{'om(rho=%.1f)' % r:>14}" for r in RHO_LIST))
    for T in T_LEVELS:
        for W in W_LEVELS:
            print(f"{T:>8.4f}{W:>9.5f}" +
                  "".join(f"{base[(T, W, r)][1]:>14.4f}" for r in RHO_LIST))

    print(f"\n{'T':>8}{'W':>9}" + "".join(f"{'RT(rho=%.1f)' % r:>14}" for r in RHO_LIST))
    for T in T_LEVELS:
        for W in W_LEVELS:
            print(f"{T:>8.4f}{W:>9.5f}" +
                  "".join(f"{base[(T, W, r)][2] * 1000:>14.1f}" for r in RHO_LIST))

    # ---------- 相对偏差 ----------
    print("\n" + "-" * 104)
    print("相对 M-T3（rho=1）的最大绝对偏差")
    print("-" * 104)
    print(f"{'rho':>6}{'max|d acc|':>14}{'max|d om|':>14}{'max|d RT| ms':>15}"
          f"{'acc 相对':>12}{'om 相对':>12}{'RT 相对':>12}")
    for rho in RHO_LIST:
        if abs(rho - 1.0) < 1e-12:
            continue
        da, do, dr = [], [], []
        for T in T_LEVELS:
            for W in W_LEVELS:
                a1, o1, m1, _ = base[(T, W, 1.0)]
                a2, o2, m2, _ = base[(T, W, rho)]
                da.append(abs(a2 - a1))
                do.append(abs(o2 - o1))
                dr.append(abs(m2 - m1) * 1000)
        rel_a = 100 * max(da) / max(abs(base[(T, W, 1.0)][0]),
                                   abs(base[(T_LEVELS[0], W_LEVELS[0], 1.0)][0]))
        print(f"{rho:>6.2f}{max(da):>14.4f}{max(do):>14.4f}{max(dr):>15.1f}"
              f"{100 * max(da) / 0.8:>11.1f}%{100 * max(do) / 0.3:>11.1f}%"
              f"{100 * max(dr) / 750:>11.1f}%")

    print("\n口径说明：acc = P(上边界且未遗漏) —— 与实验程序记录的正确率一致（含遗漏）。")
    print("          om  = P(tau > deadline)。RT = t0 + E[tau | tau < deadline]。")
    return 0 if selfcheck_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
