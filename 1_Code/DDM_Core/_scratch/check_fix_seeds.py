# -*- coding: utf-8 -*-
"""
check_fix_seeds.py —— 跨数据集（多 seed）确认 Stage 4 判决表
================================================================================
为什么必须做
------------
`Stage4_识别性结论与设计处方.md` §2.2 的全部判决都基于**单个数据集（seed=7）**。
而 `tau_T` 的 `x_hat` 在 D4 是 0.0050、在 low6 是 0.1728 —— **方向相反**，
这正是"不可识别"的典型征象，但也可能只是单数据集的偶然。
本脚本用 12 个独立数据集重跑关键剖面，统计每种判决出现的次数。

判决口径（与 check_fix.py 一致）
------------------------------
* **含真值**   —— 剖面 95% 区间包含真值 ⇒ 该参数可估且无偏；
* **有偏**     —— 区间闭合但不含真值 ⇒ 可估但估计有偏；
* **不可识别** —— 区间在某侧未闭合（撞参数边界）⇒ 不可估。

用法
----
    python check_fix_seeds.py            # 默认 12 个 seed
    python check_fix_seeds.py 20         # 指定个数
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
from likelihood import profile_se, trials_from_arrays  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

NAMES = list(WITHIN_FREE)
TRU = TRUTH.vector(NAMES)
T_L = [0.0333, 0.0833, 0.14999, 0.24998]
W_L = [0.79998, 1.19990, 1.79990]
REP = 12

#: (条件标签, 被固定的参数集合, 要剖面的参数)
CONDITIONS = [
    ("tau_T 自由",      set(),                ["beta_T", "beta_ST", "delta_a", "tau_T"]),
    ("仅固定 tau_a",    {"tau_a"},            ["delta_a", "beta_T", "beta_ST"]),
    ("两者都固定",      {"tau_T", "tau_a"},   ["beta_T", "beta_ST", "delta_a"]),
]


def strip(drop):
    return [n for n in NAMES if n not in drop]


def verdict(r):
    if r["lo"] is None or r["hi"] is None:
        return "不可识别"
    t = float(r["truth"])
    return "含真值" if r["lo"] <= t <= r["hi"] else "有偏"


def make(seed):
    design = build_design(P_SINGLE, T_L, W_L, REP)
    sim = simulate_subject(design, TRUTH, np.random.default_rng(seed))
    return trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                              *design_arrays(design)), float(sim["omission"].mean())


def main():
    n_seed = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    t_start = time.time()
    print("=" * 100)
    print(f"跨数据集确认：D4 设计，{n_seed} 个独立 seed")
    print("=" * 100)
    print(f"  自由参数集 {NAMES}")
    print(f"  真值 {dict(zip(NAMES, np.round(TRU, 4)))}\n")

    # counts[cond][param][verdict] = n
    counts: dict = {}
    xhats: dict = {}          # (cond, param) -> [x_hat per seed]  ← 用于展示漂移方向
    omis = []
    for s in range(n_seed):
        seed = 7 + 100 * s
        tr, om = make(seed)
        omis.append(om)
        for lab, fixed, params in CONDITIONS:
            free = strip(fixed)
            for nm in params:
                r = profile_se(tr, free, TRUTH, nm, n_grid=21)
                v = verdict(r)
                counts.setdefault(lab, {}).setdefault(nm, {}).setdefault(v, 0)
                counts[lab][nm][v] += 1
                xhats.setdefault((lab, nm), []).append(float(r["x_hat"]))
        print(f"  seed {seed} 完成（遗漏率 {om:.3f}）  "
              f"已用 {time.time()-t_start:.0f}s")

    print("\n" + "=" * 100)
    print(f"判决计数（共 {n_seed} 个数据集）")
    print("=" * 100)
    print(f"  {'条件':16s} {'参数':10s} {'含真值':>7s} {'有偏':>7s} {'不可识别':>9s}"
          f"   {'x_hat 范围':>26s}  真值")
    print("  " + "-" * 92)
    for lab, _f, params in CONDITIONS:
        for nm in params:
            c = counts.get(lab, {}).get(nm, {})
            k = NAMES.index(nm)
            xs = np.array(xhats[(lab, nm)])
            rng = f"[{xs.min():+.4f}, {xs.max():+.4f}]"
            print(f"  {lab:16s} {nm:10s} {c.get('含真值', 0):7d} {c.get('有偏', 0):7d} "
                  f"{c.get('不可识别', 0):9d}   {rng:>26s}  {TRU[k]:+.4f}")

    print("\n" + "=" * 100)
    print("读法")
    print("=" * 100)
    print("  * 一个参数若在多数数据集上『不可识别』或『有偏』⇒ 与单数据集结论一致，")
    print("    该参数不可估，应剥离出确证性结果。")
    print("  * x_hat 范围若跨越真值且宽度远大于真值本身 ⇒ 估计纯噪声（不可识别）。")
    print("  * 『含真值』次数多但 x_hat 范围很宽 ⇒ 只是区间太宽，不是精度好。")
    print(f"\n  总耗时 {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
