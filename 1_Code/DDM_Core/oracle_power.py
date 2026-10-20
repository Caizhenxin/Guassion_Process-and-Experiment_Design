# -*- coding: utf-8 -*-
"""
oracle_power.py —— P 水平设计的**纯识别力**评估（无 DDM 拟合）
==============================================================
设计问题与估计问题必须分开：

* **设计问题**：给定被试层参数的**真值**，这个 P 水平设置在统计上能否识别
  `β_P`（练习效应幅度）与 `τ_P`（饱和尺度）？→ 本脚本回答。**零拟合成本。**
* **估计问题**：从观测数据能估回多少被试层参数？→ `recover_group.py` 回答。

做法：反复从随机效应分布抽取被试层 `d_ref`（与 `beta_S`），对每 P 组取均值，
再做与 `recover_group.fit_between` **完全相同**的组间回归。
扫 `n_subj_per_level` 与 P 水平设置，报告 bias / RMSE / 覆盖率。

用法
----
    python oracle_power.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
_SCRATCH = _HERE.parents[0]
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "1_Code" / "DDM_Core"))

from mapping import f_P  # noqa: E402
from recover_group import (GROUP_FIT_NAMES, P_COMMON_REF, P_LEVELS,  # noqa: E402
                           fit_between)
from simulate import SUBJECT_SD  # noqa: E402

TRUTH = {"d_ref": 0.70, "beta_P": 0.35, "beta_S": 0.16, "beta_SP": 0.06,
         "tau_P": 30.0}
SD_D = SUBJECT_SD["d_ref"]
SD_S = SUBJECT_SD["beta_S"]

N_REP = 400
BASE_SEED = 20261115


def draw_level_means(P_levels, n_per_level, rng):
    """按真值模型抽各 P 组的被试层均值（含随机效应）。"""
    reg = f_P(np.array(P_levels, float), TRUTH["tau_P"]) - f_P(P_COMMON_REF, TRUTH["tau_P"])
    mu_d = TRUTH["d_ref"] + TRUTH["beta_P"] * reg
    mu_s = TRUTH["beta_S"] + TRUTH["beta_SP"] * reg
    d_hat = mu_d + rng.normal(0, SD_D / np.sqrt(n_per_level), size=len(P_levels))
    s_hat = mu_s + rng.normal(0, SD_S / np.sqrt(n_per_level), size=len(P_levels))
    return d_hat, s_hat


def evaluate(P_levels, n_per_level, n_rep=N_REP):
    rng = np.random.default_rng(BASE_SEED + n_per_level + int(sum(P_levels)))
    P_arr = np.array(P_levels, float)
    est = {k: [] for k in GROUP_FIT_NAMES}
    init = [TRUTH["d_ref"], TRUTH["beta_P"], TRUTH["beta_S"], TRUTH["beta_SP"],
            TRUTH["tau_P"]]
    for _ in range(n_rep):
        d_hat, s_hat = draw_level_means(P_levels, n_per_level, rng)
        # fit_between 的返回值在 D31 之后是三元组 (out, rms, wrms)；此前写死两个
        # 变量会在运行时报 "too many values to unpack"（2026-10-20 修）。
        fit, _rms, _wrms = fit_between(P_arr, d_hat, s_hat, P_COMMON_REF, init)
        for k in GROUP_FIT_NAMES:
            est[k].append(fit[k])
    out = {}
    for k in GROUP_FIT_NAMES:
        a = np.array(est[k])
        out[k] = dict(truth=TRUTH[k], mean=float(a.mean()), sd=float(a.std(ddof=1)),
                      bias=float(a.mean() - TRUTH[k]),
                      rmse=float(np.sqrt(np.mean((a - TRUTH[k]) ** 2))))
    return out


def main():
    print("=" * 104)
    print("P 水平设计的纯识别力（oracle：用被试层参数**真值**做组间回归，无 DDM 拟合）")
    print("=" * 104)
    print(f"  真值：{TRUTH}；被试间 SD：d_ref={SD_D}、beta_S={SD_S}")
    print(f"  每次 {N_REP} 次重复；回归模型与 recover_group.fit_between 完全相同\n")

    scenarios = [
        ("当前推荐", P_LEVELS, [6, 12, 20, 30, 50]),
        ("P 加密（6 水平）", [0, 4, 8, 16, 32, 64, 120], [6, 12, 20]),
        ("P 加宽（含 240）", [0, 8, 32, 120, 240], [12, 20, 30]),
        ("文献常见 3 水平", [0, 32, 120], [12, 20, 30]),
    ]
    rows = []
    for name, levels, ns in scenarios:
        print("-" * 104)
        print(f"【{name}】P 水平 = {[int(x) for x in levels]}（{len(levels)} 个水平）")
        print(f"  {'n/组':>5s} {'β_P 偏差':>10s} {'β_P RMSE':>10s} {'β_P SD':>9s} "
              f"{'τ_P 均值':>10s} {'τ_P 偏差':>10s} {'τ_P RMSE':>10s} {'τ_P SD':>9s}")
        for n in ns:
            r = evaluate(levels, n)
            print(f"  {n:5d} {r['beta_P']['bias']:10.4f} {r['beta_P']['rmse']:10.4f} "
                  f"{r['beta_P']['sd']:9.4f} {r['tau_P']['mean']:10.2f} "
                  f"{r['tau_P']['bias']:10.2f} {r['tau_P']['rmse']:10.2f} "
                  f"{r['tau_P']['sd']:9.2f}")
            rows.append((name, len(levels), n, r))
        print()

    print("=" * 104)
    print("判定")
    print("=" * 104)
    print(f"  {'场景':>16s} {'水平数':>6s} {'n/组':>5s} "
          f"{'β_P 相对RMSE':>13s} {'τ_P 相对RMSE':>13s}  判定")
    for name, nlev, n, r in rows:
        rel_p = r["beta_P"]["rmse"] / abs(TRUTH["beta_P"])
        rel_t = r["tau_P"]["rmse"] / abs(TRUTH["tau_P"])
        ok_p = rel_p < 0.30
        ok_t = rel_t < 0.50
        verdict = ("✅ 两者可识别" if (ok_p and ok_t)
                   else ("🟡 仅 β_P 可识别" if ok_p else "❌ 均不可识别"))
        print(f"  {name:>16s} {nlev:6d} {n:5d} {rel_p:13.2f} {rel_t:13.2f}  {verdict}")

    print("\n  说明：")
    print("   * 『τ_P 相对 RMSE』大 = 饱和尺度估不准。τ_P 靠的是跨 P 水平的**曲线形状**，")
    print("     水平越少、每组人越少，组均值的抽样噪声就越压过形状信号。")
    print("   * 这里的 oracle 是**上界**：真实分析还要叠加被试内估计噪声，只会更差。")


if __name__ == "__main__":
    main()
