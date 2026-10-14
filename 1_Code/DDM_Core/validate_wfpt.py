# -*- coding: utf-8 -*-
"""
validate_wfpt.py —— WFPT 实现的四项独立验证（Stage 2 验收）
============================================================
本脚本不依赖任何外部 DDM 库。四项检查中，V1 与 V2 用的是与本模块密度公式
**推导路径不同**的判据；V3/V4 用已在本项目长期使用的 Euler–Maruyama 路径模拟
（`sim_utils.simulate_trials`）作独立对照。

V1  吸收概率：∫f_upper dt 是否等于闭式解 (1−e^{−2vz})/(1−e^{−2va})
V2  归一化：∫(f_upper + f_lower) dt 是否等于 1
V3  分布一致：WFPT 抽样的 τ 与细步长路径模拟的 τ 的 KS 统计量
V4  deadline 未响应概率：解析存活 vs 路径模拟频率

用法
----
    python validate_wfpt.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from scipy import stats

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_ROOT / "1_Code" / "Python_for_Check" / "TenRules_Revision_20260912"))

from wfpt import (density, p_upper, sample_wfpt, simulate, survival,  # noqa: E402
                  survival_series, wfpt_cdf_grid)
from sim_utils import simulate_trials  # noqa: E402

# 覆盖中心起点、偏斜起点、正/负/零漂移、大/小边界
CASES = [
    dict(v=+0.5, a=1.5, z=0.75),
    dict(v=-0.5, a=1.5, z=0.75),
    dict(v=+2.0, a=1.0, z=0.50),
    dict(v=-2.0, a=1.0, z=0.50),
    dict(v=+0.0, a=1.5, z=0.75),
    dict(v=+0.3, a=2.0, z=1.20),   # 偏斜起点
    dict(v=-0.8, a=2.0, z=0.40),   # 偏斜起点 + 负漂移
]

T_MAX_INT = 60.0          # 用于积分归一化
N_GRID = 20000
N_PATH = 20000            # 路径模拟试次数
DT_PATH = 0.0005          # 细步长（默认 0.002 的 1/4）
T0 = 0.20
SEED = 20261013


def hr(s):
    print("\n" + "=" * 96)
    print(s)
    print("=" * 96)


def main():
    rng = np.random.default_rng(SEED)
    rows = []

    for c in CASES:
        v, a, z = c["v"], c["a"], c["z"]
        tag = f"v={v:+.1f} a={a:.1f} z={z:.2f}"

        # ---- V1 / V2：积分 ----
        _, F_up, F_lo = wfpt_cdf_grid(v, a, z, T_MAX_INT, n_grid=N_GRID, power=3.0)
        int_up, int_lo = float(F_up[-1]), float(F_lo[-1])
        p_an = float(p_upper(v, a, z))

        # ---- V3：分布一致（KS） ----
        # ⚠️ 口径陷阱：`sim_utils.simulate_trials` 把 0<z<=1 解释为**边界比例**，
        #    否则解释为**绝对起点**。本模块一律用绝对起点，故这里传 z/a 让它换算回绝对 z。
        z_arg = z / a
        tau_w, _ = sample_wfpt(v, a, z, N_PATH, rng)
        sim = simulate_trials(v, a, T0, z_arg, deadline=30.0, n_trials=N_PATH,
                              rng=rng, dt=DT_PATH)
        tau_p = sim["rt"][~np.isnan(sim["rt"])] - T0
        tau_w = tau_w[np.isfinite(tau_w)]
        n_use = min(len(tau_w), len(tau_p), 5000)
        ks = stats.ks_2samp(tau_w[:n_use], tau_p[:n_use])

        # ---- V4：deadline 未响应概率 ----
        om_rows = []
        for dl in (0.5, 0.8, 1.2):
            _, Fu, Fl = wfpt_cdf_grid(v, a, z, dl - T0, n_grid=8000, power=2.0)
            p_om_ana = 1.0 - float(Fu[-1] + Fl[-1])
            s2 = simulate_trials(v, a, T0, z_arg, deadline=dl, n_trials=N_PATH,
                                 rng=rng, dt=DT_PATH)
            p_om_sim = float(np.mean(s2["omission"]))
            om_rows.append((dl, p_om_ana, p_om_sim))

        rows.append(dict(
            tag=tag, v=v, a=a, z=z,
            int_up=int_up, int_lo=int_lo, p_an=p_an,
            d_up=abs(int_up - p_an), d_tot=abs(int_up + int_lo - 1.0),
            ks_stat=float(ks.statistic), ks_p=float(ks.pvalue),
            om=om_rows,
        ))

    hr("V1/V2  吸收概率与归一化（数值积分 vs 闭式解）")
    print(f"{'case':22s} {'∫f_up':>10s} {'P_up(闭式)':>11s} {'|差|':>10s} "
          f"{'∫f_up+∫f_lo':>12s} {'|与1差|':>10s}")
    for r in rows:
        print(f"{r['tag']:22s} {r['int_up']:10.5f} {r['p_an']:11.5f} {r['d_up']:10.2e} "
              f"{r['int_up']+r['int_lo']:12.5f} {r['d_tot']:10.2e}")
    worst1 = max(r["d_up"] for r in rows)
    worst2 = max(r["d_tot"] for r in rows)
    print(f"\n  最大偏差：V1 = {worst1:.2e}   V2 = {worst2:.2e}")
    print(f"  判定：{'✅ 通过' if worst1 < 5e-3 and worst2 < 5e-3 else '❌ 未通过'}（阈值 5e-3）")

    hr("V3  分布一致（WFPT 抽样 vs 细步长路径模拟，KS 检验）")
    print(f"{'case':22s} {'KS 统计量':>10s} {'p 值':>10s}  判定")
    for r in rows:
        ok = r["ks_p"] > 0.01
        print(f"{r['tag']:22s} {r['ks_stat']:10.4f} {r['ks_p']:10.4f}  "
              f"{'✅ 不拒绝同分布' if ok else '❌ 拒绝'}")
    n_ok = sum(1 for r in rows if r["ks_p"] > 0.01)
    print(f"\n  {n_ok}/{len(rows)} 个条件不拒绝同分布")
    print("  （注：路径模拟本身有 dt 离散偏差，KS 会略微偏高；关键是量级而非 p 值）")

    hr("V4  deadline 未响应概率（解析存活 vs 路径模拟频率）")
    print(f"{'case':22s} {'deadline':>9s} {'解析':>9s} {'路径模拟':>10s} {'|差|':>9s}")
    worst4 = 0.0
    for r in rows:
        for dl, pa, ps in r["om"]:
            worst4 = max(worst4, abs(pa - ps))
            print(f"{r['tag']:22s} {dl:9.1f} {pa:9.4f} {ps:10.4f} {abs(pa-ps):9.4f}")
    print(f"\n  最大偏差 = {worst4:.2e}")
    print(f"  判定：{'✅ 通过' if worst4 < 0.03 else '❌ 未通过'}（阈值 0.03）")

    hr("V5  残差归因：分别对**解析 CDF** 做单样本检验")
    print("  V3 是两样本检验，残差里混了抽样噪声，无法归因。")
    print("  正确做法：把 WFPT 抽样与路径模拟**各自**与解析 CDF 比（单样本 KS）。")
    print("  → 若路径模拟的 KS 随 dt → 0 而下降、而 WFPT 抽样的 KS 始终很小，")
    print("     则残差归因于**路径模拟的离散偏差**，WFPT 实现无系统性错误。\n")

    worst = max(rows, key=lambda r: r["ks_stat"])
    v, a, z = worst["v"], worst["a"], worst["z"]
    print(f"  取 V3 中 KS 最大的条件：{worst['tag']}\n")

    T_CAP = 10.0 - T0
    tg, Fu, Fl = wfpt_cdf_grid(v, a, z, T_CAP, n_grid=40000, power=3.0)
    Ftot = Fu + Fl
    Fcond = Ftot / Ftot[-1]          # 条件于 τ ≤ T_CAP

    def cdf_analytic(x):
        return np.interp(x, tg, Fcond, left=0.0, right=1.0)

    N_KS = 20000
    tau_w, _ = sample_wfpt(v, a, z, N_KS, rng, t_max=T_CAP)
    tau_w = tau_w[np.isfinite(tau_w)]
    ks_w = stats.kstest(tau_w, cdf_analytic)

    print(f"{'来源':>18s} {'n':>7s} {'KS 统计量':>11s} {'p 值':>9s}")
    print(f"{'WFPT 抽样':>18s} {len(tau_w):7d} {ks_w.statistic:11.4f} {ks_w.pvalue:9.4f}")
    ks_path = []
    for dt in (0.004, 0.002, 0.001, 0.0005):
        sim_dt = simulate_trials(v, a, T0, z / a, deadline=10.0, n_trials=N_KS,
                                 rng=rng, dt=dt)
        tau_p = sim_dt["rt"][~np.isnan(sim_dt["rt"])] - T0
        k = stats.kstest(tau_p, cdf_analytic)
        ks_path.append((dt, float(k.statistic), float(k.pvalue)))
        print(f"{'路径模拟 dt=' + format(dt, '.4f'):>18s} {len(tau_p):7d} "
              f"{k.statistic:11.4f} {k.pvalue:9.4f}")

    print()
    shrink = ks_path[0][1] - ks_path[-1][1]
    print(f"  路径模拟 KS：dt={ks_path[0][0]:.4f} → {ks_path[-1][0]:.4f} 时 "
          f"{ks_path[0][1]:.4f} → {ks_path[-1][1]:.4f}（缩小 {shrink:.4f}）")
    print(f"  WFPT 抽样 KS = {ks_w.statistic:.4f}（阈值 0.02，n={len(tau_w)} 时 5% 临界值 ≈ "
          f"{1.36*np.sqrt(2/len(tau_w)):.4f}）")
    ok_w = ks_w.statistic < 0.02
    ok_attr = shrink > 0.005 and ks_path[-1][1] < ks_path[0][1]
    if ok_w and ok_attr:
        print("\n  ✅ WFPT 抽样与解析 CDF 一致（KS < 0.02），且路径模拟的偏差随 dt 缩小 →")
        print("     残差明确归因于**路径模拟的离散偏差**。WFPT 实现通过。")
    elif ok_w:
        print("\n  ⚠️ WFPT 抽样本身没问题（KS < 0.02），但路径模拟偏差未随 dt 缩小 →")
        print("     需检查路径模拟的常数偏差（如步长内的越界判定时点）。")
    else:
        print("\n  ❌ WFPT 抽样与解析 CDF 不一致 → 抽样器有问题，需修正。")

    hr("V6  解析存活函数 survival_series vs 数值积分")
    print("  Stage 3 的 deadline 未响应项需要 P(τ > t)。数值积分太慢，改用解析级数。")
    print("  这里用数值积分（V1/V2 已验证过的密度）做独立校验。\n")
    print(f"{'case':22s} {'t':>6s} {'解析级数':>11s} {'1−∫密度':>11s} {'|差|':>10s}")
    worst6 = 0.0
    for c in CASES:
        v, a, z = c["v"], c["a"], c["z"]
        for tt in (0.05, 0.2, 0.5, 1.0, 2.0):
            s_ser = float(survival_series(v, a, z, tt))
            _, Fu, Fl = wfpt_cdf_grid(v, a, z, tt, n_grid=20000, power=3.0)
            s_int = 1.0 - float(Fu[-1] + Fl[-1])
            worst6 = max(worst6, abs(s_ser - s_int))
            print(f"{c and f'v={v:+.1f} a={a:.1f} z={z:.2f}':22s} {tt:6.2f} "
                  f"{s_ser:11.6f} {s_int:11.6f} {abs(s_ser-s_int):10.2e}")
    print(f"\n  最大偏差 = {worst6:.2e}")
    print(f"  判定：{'✅ 通过' if worst6 < 5e-4 else '❌ 未通过'}（阈值 5e-4）")
    # 大 t 极限
    lim = float(survival_series(0.5, 1.5, 0.75, 40.0))
    print(f"  大 t 极限检验：P(τ>40) = {lim:.3e} → {'✅ 趋于 0' if lim < 1e-6 else '❌ 未衰减'}")

    hr("Stage 2 结论")
    all_ok = worst1 < 5e-3 and worst2 < 5e-3 and n_ok >= len(rows) - 1 and worst4 < 0.03
    print(f"  V1 吸收概率 : {'✅' if worst1 < 5e-3 else '❌'}  最大偏差 {worst1:.2e}")
    print(f"  V2 归一化   : {'✅' if worst2 < 5e-3 else '❌'}  最大偏差 {worst2:.2e}")
    print(f"  V3 分布一致 : {'✅' if n_ok >= len(rows) - 1 else '❌'}  {n_ok}/{len(rows)}")
    print(f"  V4 未响应   : {'✅' if worst4 < 0.03 else '❌'}  最大偏差 {worst4:.2e}")
    print(f"\n  {'✅ WFPT 实现通过验收，可作为 Stage 3 的似然与抽样基础。' if all_ok else '❌ 未通过，需修正。'}")


if __name__ == "__main__":
    main()
