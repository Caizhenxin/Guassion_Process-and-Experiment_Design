"""检查：群体真值生成出来的**被试层真值**是否落在 `PARAM_BOUNDS` 允许的箱体内。

动机（2026-10-14）：组层重跑里出现「病态拟合」被剔除时，我第一反应是优化器退化。
但 `d_ref` 的下界是 0.20，而 P=0 组的群体真值本身只有 ~0.43 —— 若被试层随机效应
（`SUBJECT_SD`）把一部分被试推到 0.20 以下，**那些被试的真值就在箱体之外，任何
拟合都不可能恢复它**。这时「病态」标记抓到的不是算法问题，而是**真值设计**问题。

本脚本只做一件事：用与 `recover_group.py` 完全相同的种子与抽样顺序重放被试层真值，
逐参数统计有多少个真值落在 `PARAM_BOUNDS` 之外，并给出对应的 z 距离。
不跑似然、不模拟反应，因此是秒级。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_DDM = _HERE.parent
sys.path.insert(0, str(_DDM))

from mapping import PARAM_BOUNDS, WITHIN_FREE, WITHIN_FREE_LIN  # noqa: E402
from recover_group import (BASE_SEED, GROUP_INITS, GROUP_TRUTHS,  # noqa: E402
                           N_REP, P_COMMON_REF, P_LEVELS, T_LEVELS, W_LEVELS,
                           make_subject_truth)
from simulate import SUBJECT_SD  # noqa: E402


def scan(shape: str, n_sub: int) -> None:
    truth = GROUP_TRUTHS[shape]
    names = list(WITHIN_FREE) if shape == "exp" else list(WITHIN_FREE_LIN)
    # 「被试层」真值只在这些参数上带随机效应；其余是固定值。
    varying = [n for n in names if n in SUBJECT_SD]

    print("=" * 100)
    print(f"参数化 {shape!r}：被试层真值 vs PARAM_BOUNDS（每组 {n_sub} 人，"
          f"共 {len(P_LEVELS) * n_sub} 人）")
    print("=" * 100)
    print(f"  带被试间随机效应的参数：{varying}")

    truth_tab: dict[str, list[float]] = {n: [] for n in names}
    per_level: dict[float, dict[str, list[float]]] = {p: {n: [] for n in names}
                                                     for p in P_LEVELS}
    for P in P_LEVELS:
        for s in range(n_sub):
            seed = BASE_SEED + int(P) * 1000 + s
            rng = np.random.default_rng(seed)
            subj_truth, _reg = make_subject_truth(truth, P, P_COMMON_REF, rng)
            for n in names:
                v = float(getattr(subj_truth, n))
                truth_tab[n].append(v)
                per_level[P][n].append(v)

    n_tot = sum(len(v) for v in truth_tab.values()) // max(len(names), 1)
    print(f"\n  {'参数':>9s} {'群体真值':>10s} {'被试层均值':>11s} {'被试层SD':>9s} "
          f"{'最小':>9s} {'最大':>9s} {'下界':>8s} {'上界':>8s} {'越界数':>7s} {'越界%':>7s}")
    any_out = 0
    for n in names:
        lo, hi = PARAM_BOUNDS[n]
        v = np.array(truth_tab[n], float)
        n_out = int(np.sum((v < lo) | (v > hi)))
        any_out += n_out
        mark = "  ⚠️" if n_out else ""
        print(f"  {n:>9s} {float(getattr(truth, n)):10.4f} {v.mean():11.4f} "
              f"{v.std(ddof=1) if v.size > 1 else 0.0:9.4f} {v.min():9.4f} {v.max():9.4f} "
              f"{lo:8.2f} {hi:8.2f} {n_out:7d} {100.0 * n_out / max(v.size, 1):6.1f}%{mark}")
    print(f"\n  合计越界 {any_out} 个参数值。")

    # 对越界最严重的参数，按 P 水平拆开看 —— 这直接指出是哪一组的真值设计有问题。
    # 注意：真值**恰好等于**下界（如 0.2000）时 `v < lo` 为 False，越界数会报 0，
    # 但那个被试的拟合已经贴死在界上 —— 所以这里也把「贴着界」（相对余量 < 5%）算进来。
    worst = None
    for n in names:
        lo, hi = PARAM_BOUNDS[n]
        v = np.array(truth_tab[n], float)
        k = int(np.sum((v < lo) | (v > hi)))
        margin = min((v.min() - lo) / max(abs(lo), 1e-9), (hi - v.max()) / max(abs(hi), 1e-9))
        if worst is None or k > worst[1]:
            worst = (n, k, margin)
    if worst and (worst[1] > 0 or worst[2] < 0.05):
        n, _k, _m = worst
        lo, hi = PARAM_BOUNDS[n]
        print(f"  → {n!r} 真值最靠近界的相对余量只有 {100.0 * _m:.1f}%（<5% 即视为贴界）。")
        print(f"\n  越界最多的参数是 {n!r}（下界 {lo}，上界 {hi}）—— 按 P 水平拆分：")
        print(f"    {'P':>6s} {'n':>4s} {'均值':>10s} {'SD':>9s} {'最小':>10s} "
              f"{'最大':>10s} {'距下界/真值SD':>15s} {'预计越界%':>10s}")
        from math import erf, sqrt
        for P in P_LEVELS:
            v = np.array(per_level[P][n], float)
            sd = v.std(ddof=1) if v.size > 1 else 0.0
            z = (v.mean() - lo) / sd if sd > 0 else float("inf")
            below = 0.5 * (1.0 + erf((lo - v.mean()) / (sd * sqrt(2.0)))) if sd > 0 else 0.0
            print(f"    {P:6.0f} {v.size:4d} {v.mean():10.4f} {sd:9.4f} "
                  f"{v.min():10.4f} {v.max():10.4f} {z:15.2f} {100.0 * below:9.1f}%")
        print(f"\n    ⚠️ 「距下界/真值SD = z」小于 ~2 的组，其被试层真值会有可观比例落在箱体之外；")
        print(f"       这些被试**无论如何都拟合不出来**，被标成「病态」是正确行为，")
        print(f"       但根因是**真值/界宽设计**，不是优化器，也不是参数化。")

    # 逐被试列出「真值贴界」的个体 —— 这是「拟合贴界 ≠ 优化器失败」的直接证据。
    print(f"\n  逐个被试检查：真值距最近边界的相对余量 <1% 的个体")
    print(f"    {'P':>6s} {'subj':>5s} {'参数':>9s} {'真值':>10s} {'界':>8s} {'余量%':>8s}")
    hits = 0
    for P in P_LEVELS:
        for s in range(n_sub):
            for n in names:
                lo, hi = PARAM_BOUNDS[n]
                v = per_level[P][n][s]
                span = max(hi - lo, 1e-9)
                m = min(v - lo, hi - v) / span
                if m < 0.01:
                    side = "下界" if v - lo < hi - v else "上界"
                    print(f"    {P:6.0f} {s:5d} {n:>9s} {v:10.4f} "
                          f"{lo if side == '下界' else hi:8.2f} {100.0 * m:7.2f}%  ← {side}")
                    hits += 1
    if hits == 0:
        print("    （无）")
    print()


def main() -> None:
    n_sub = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"\n设计层次：T={T_LEVELS}  W={W_LEVELS}  N_REP={N_REP}")
    print(f"P 水平={P_LEVELS}  P_COMMON_REF={P_COMMON_REF}  BASE_SEED={BASE_SEED}")
    print()
    for shape in ("exp", "lin"):
        scan(shape, n_sub)


if __name__ == "__main__":
    main()
