# -*- coding: utf-8 -*-
"""
check_fix.py —— 破解 (tau_T, beta_T, beta_ST) 脊的处方验证
================================================================================
问题（Stage 4 已确立）
----------------------
1. **设计层面**：T 放在 33/83/150/250 ms 时，tau_T 的条件相对精度 253%；
   把 T 移进 10-100 ms 的指数曲率区，同样试次下改善 4-6 倍（check_ttau）。
2. **模型层面**：即使设计改善，(tau_T, beta_T, beta_ST) 三者仍构成**尺度退化脊**
   —— dqt 在 Q_T 饱和区只是被 beta_T/beta_ST 整体缩放，于是：
   * beta_T 剖面单调升到上界，95% 区间 [2.0, 5.0]，真值 0.55 被排除；
   * beta_ST 剖面 95% 区间 [-2.0, -1.0]，真值 0.10 被排除；
   * tau_T 剖面极大值落在 0.02（真值 0.08）。

处方假设
--------
**把 tau_T 先验固定**（等价地固定 tau_a），脊就被切断：其余参数不再能通过缩放
dqt 互相补偿。本脚本直接验证这个假设。

做法
----
`profile_se(tr, names, p, which)` 的 `names` 就是**自由参数集**。
把 tau_T 从 `names` 里去掉，它自然被钉在 `p` 里给的值（= 真值）。
于是「自由剖面 vs 固定剖面」只差一个参数集，没有任何新机制。

用法
----
    python check_fix.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from design_fim import P_SINGLE, TRUTH  # noqa: E402
from likelihood import log_likelihood, profile_se, trials_from_arrays, fit_mle  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

NAMES = list(WITHIN_FREE)
TRU = TRUTH.vector(NAMES)
W_D4 = [0.79998, 1.19990, 1.79990]

DESIGNS = {
    "D4   (T=33/83/150/250, 576)": ([0.0333, 0.0833, 0.14999, 0.24998], W_D4, 12),
    "low6 (T=10/20/33/60/100/200, 864)": ([0.0100, 0.0200, 0.0333, 0.0600,
                                          0.1000, 0.2000], W_D4, 12),
}

TARGETS = ("beta_T", "beta_ST", "delta_a", "tau_T")


def strip(drop):
    """自由参数集 = NAMES 去掉 drop。被去掉的参数钉在 p 里给的值（= 真值）。"""
    return [n for n in NAMES if n not in drop]


def make(design_T, W, rep, seed=7):
    design = build_design(P_SINGLE, design_T, W, rep)
    rng = np.random.default_rng(seed)
    sim = simulate_subject(design, TRUTH, rng)
    return trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                              *design_arrays(design))


def report(tag, r, nm):
    """打印一条剖面结果并返回它。

    注意 ``x_hat``：剖面的极大值位置（= 约束 MLE）。区间 ``[lo,hi]`` 的参考点是
    ``x_hat`` 而不是真值，所以「区间不含真值」= **估计有偏**，不是「不可识别」。
    看可识别性请读 ``SE`` 与 ``未闭合``。
    """
    t = float(r["truth"])
    xh, bias = float(r["x_hat"]), float(r["bias"])
    if r["lo"] is None or r["hi"] is None:
        iv, width = "— 未闭合 —", "—"
        verdict = f"不可识别（{r['unbounded']}）"
    else:
        iv = f"[{r['lo']:+.4f}, {r['hi']:+.4f}]"
        width = f"{r['hi'] - r['lo']:.4f}"
        if r["lo"] <= t <= r["hi"]:
            verdict = "区间含真值"
        else:
            verdict = "有偏（极值被推离真值）"
    se = "inf" if not np.isfinite(r["se"]) else f"{r['se']:.4f}"
    print(f"    {tag:12s} {nm:9s} x_hat={xh:+.4f}(偏{bias:+.4f}) "
          f"95%CI={iv:24s} 宽={width:>8s} SE={se:>7s}  {verdict}")
    return r


def verdict_of(r, nm):
    if r is None:
        return "—"          # 该列没有测这个参数（例如 tau_T 在被固定的列里）
    if r["lo"] is None or r["hi"] is None:
        return "不可识别"
    t = float(r["truth"])
    return "含真值" if r["lo"] <= t <= r["hi"] else "有偏"


def main():
    t0 = time.time()
    print("=" * 106)
    print("处方验证：先验固定 tau_T 能否切断 (tau_T, beta_T, beta_ST) 脊")
    print("=" * 106)
    print(f"  真值：{ {n: round(float(v), 4) for n, v in zip(NAMES, TRU)} }")
    print("  profile_se(tr, names, p, which)：names 就是自由参数集；")
    print("  把 tau_T 从 names 去掉 = 把它钉在真值。\n")

    summary = {}
    for dname, (T, W, rep) in DESIGNS.items():
        tr = make(T, W, rep)
        ll_t = log_likelihood(TRUTH, tr)
        n = int(np.asarray(tr["rt"]).size)
        print("=" * 106)
        print(f"设计：{dname}   试次={n}   ll(真值)={ll_t:.3f}")
        print("=" * 106)

        print("  A. tau_T 自由（Stage 4 已确立的病态情形）")
        for nm in TARGETS:
            r = profile_se(tr, NAMES, TRUTH, nm, n_grid=25)
            report("free", r, nm)
            summary[(dname, "free", nm)] = r

        print("\n  B. tau_T 固定于真值（处方）——只能剖面 *其余* 参数，")
        print("     tau_T 本身已不在自由集中，剖面它会被 profile_se 拒绝（ValueError）。")
        for nm in [t for t in TARGETS if t != "tau_T"]:
            r = profile_se(tr, strip({"tau_T"}), TRUTH, nm, n_grid=25)
            report("fixed tau_T", r, nm)
            summary[(dname, "fixed_tauT", nm)] = r

        print("\n  C. tau_a 固定于真值（备选处方，对照）")
        for nm in ("delta_a",):
            r = profile_se(tr, strip({"tau_a"}), TRUTH, nm, n_grid=25)
            report("fixed tau_a", r, nm)
            summary[(dname, "fixed_taua", nm)] = r

        print("\n  E. tau_T 与 tau_a 同时固定于真值（完整处方）")
        free_both = strip({"tau_T", "tau_a"})
        for nm in ("beta_T", "beta_ST", "delta_a"):
            r = profile_se(tr, free_both, TRUTH, nm, n_grid=25)
            report("fixed both", r, nm)
            summary[(dname, "fixed_both", nm)] = r

        print("\n  D. 联合 MLE（固定 tau_T，gtol=1e-10）：点估计 vs 真值")
        free = strip({"tau_T"})
        fit = fit_mle(tr, free, TRUTH, n_restart=12, seed=1, maxfun=40000,
                      gtol=1e-10, ftol=1e-14)
        print(f"    ll={fit['loglik']:.4f}  n_starts_ok={fit['n_starts_ok']}  "
              f"success={fit['success']}  nfev={fit['nfev']}")
        pv = fit["params"].vector(NAMES)
        for nm in free + ["tau_T"]:
            k = NAMES.index(nm)
            pinned = "  (固定)" if nm == "tau_T" else ""
            print(f"      {nm:9s} 估计={pv[k]:+9.4f}  真值={TRU[k]:+9.4f}  "
                  f"误差={pv[k]-TRU[k]:+9.4f}{pinned}")

    print("\n" + "=" * 106)
    print("判决：固定 tau_T 前后，各参数 95% 区间是否包含真值")
    print("=" * 106)
    hdr = (f"  {'设计':34s} {'参数':9s} {'tau_T自由':>11s} {'仅固定tau_T':>12s}"
           f" {'仅固定tau_a':>12s} {'两者都固定':>11s}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for dname in DESIGNS:
        for nm in TARGETS:
            a = summary.get((dname, "free", nm))
            b = summary.get((dname, "fixed_tauT", nm))
            cc = summary.get((dname, "fixed_taua", nm))
            d = summary.get((dname, "fixed_both", nm))
            print(f"  {dname:34s} {nm:9s} {verdict_of(a, nm):>11s} "
                  f"{verdict_of(b, nm):>12s} {verdict_of(cc, nm):>12s} "
                  f"{verdict_of(d, nm):>11s}")

    print("\n" + "=" * 106)
    print("结论与处方")
    print("=" * 106)
    print("  1. 若 B/D 组由『未闭合/排除』变成『含真值』⇒ 脊由 tau_T 造成，固定它即可解锁。")
    print("  2. 固定 tau_T 有理论代价：它把『M-T1 ramp 的时标』从被估参数降级为")
    print("     先验假设，必须在论文中声明并用敏感性分析覆盖。")
    print("  3. 设计层面仍应把 T 移进 10-100 ms（check_ttau 显示 4-6 倍改善），")
    print("     否则即使固定 tau_T，其余参数的方差仍偏大。")
    print(f"\n  总耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
