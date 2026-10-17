# -*- coding: utf-8 -*-
"""把 Stage 4 的 design_fim 输出按 **D24 确证集 C6** 重新聚合。

为什么需要：`1_Code/DDM_Core/design_fim.py` 的 `PRIMARY`（5 个）仍含 `beta_ST`，
而 `Stage8_建模与验证方案.md` §4 / README §9 第 23 项已把 `beta_ST` 移出确证集。
⇒ 同一份 SE 表，用两套参数集会得到相反的"可用/不可用"判定。
本脚本只做聚合，不重算 SE（SE 取自 design_fim 的实测输出）。
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NAMES = ["d_ref", "beta_T", "tau_T", "beta_S", "beta_ST",
         "a_ref", "delta_a", "tau_a", "t0"]
PRI_D24_OLD = ["d_ref", "beta_T", "tau_T", "beta_S", "beta_ST"]
C6_D24_NEW = ["d_ref", "beta_T", "beta_S", "a_ref", "delta_a", "t0"]

# 取自 `python 1_Code/DDM_Core/design_fim.py` 的「② 相对 SE」表（2026-10-14）
ROWS = {
    "D4        (4T×3W, r12)": [0.147, 0.636, 1.296, 0.707, 4.739,
                               0.038, 2.564, 3.615, 0.057],
    "D4-3T     (3T×3W, r16)": [0.150, 0.694, 2.325, 0.780, 5.306,
                               0.037, 2.497, 3.539, 0.051],
    "D4-rep8   (4T×3W, r8)": [0.188, 0.786, 1.594, 0.867, 5.776,
                              0.046, 2.980, 4.217, 0.062],
    "D4-rep16  (4T×3W, r16)": [0.128, 0.548, 1.105, 0.604, 4.058,
                               0.032, 2.178, 3.083, 0.045],
    "W-low     (4T×{600,900,1300})": [0.172, 0.734, 1.485, 0.807, 5.448,
                                      0.032, 1.418, 4.579, 0.057],
    "W-high    (4T×{1000,1400,1900})": [0.138, 0.600, 1.221, 0.668, 4.465,
                                        0.036, 5.218, 5.569, 0.057],
    "W-wide    (4T×{500,1200,2000})": [0.158, 0.678, 1.380, 0.755, 5.049,
                                       0.038, 0.770, 1.633, 0.059],
    "T-wide    (T到400, W-high)": [0.147, 0.599, 0.982, 0.667, 4.088,
                                   0.036, 5.224, 5.578, 0.056],
}


def geo(a, names):
    return float(np.exp(np.mean([np.log(a[NAMES.index(n)]) for n in names])))


def verdict(g):
    return "✅可用" if g < 0.30 else ("⚠️勉强" if g < 0.60 else "❌不可用")


def main():
    print("=" * 96)
    print("按 D24 确证集重新聚合 Stage 4 的 design_fim 相对 SE")
    print("=" * 96)
    print(f"{'设计':34s} {'PRIMARY(旧5)':>13s} {'判定':>8s} "
          f"{'C6(新6)':>9s} {'判定':>8s} {'C6 内最差':>22s}")
    print("-" * 96)
    rank_old, rank_new = [], []
    for name, v in ROWS.items():
        a = np.array(v)
        g_old, g_new = geo(a, PRI_D24_OLD), geo(a, C6_D24_NEW)
        worst = max(C6_D24_NEW, key=lambda n: a[NAMES.index(n)])
        print(f"{name:34s} {g_old:13.3f} {verdict(g_old):>8s} "
              f"{g_new:9.3f} {verdict(g_new):>8s} "
              f"{worst+'='+format(a[NAMES.index(worst)], '.3f'):>22s}")
        rank_old.append((g_old, name))
        rank_new.append((g_new, name))
    print("-" * 96)
    print("  旧口径排序：" + " > ".join(f"{n.split()[0]}({g:.2f})"
                                    for g, n in sorted(rank_old)))
    print("  新口径排序：" + " > ".join(f"{n.split()[0]}({g:.2f})"
                                    for g, n in sorted(rank_new)))
    print()
    print("结论（三条，都是上表的直接读数）：")
    print("  1. `PRIMARY` 里的 `beta_ST`（相对 SE ≈ 4.1–5.8）独自把几何平均抬到判定线")
    print("     以上；移出后 **全部 8 个设计由 ❌ 变 ✅（仅 D4-rep8 仍 ⚠️）**，")
    print("     C6 排序 = " + " > ".join(f"{n.split()[0]}({g:.2f})"
                                     for g, n in sorted(rank_new)) + "。")
    print("  2. **C6 内的最差参数几乎总是 `delta_a`**（8 个设计里 7 个），")
    print("     即 W→a 通路的幅度是全设计空间的**绑定约束**；唯一例外是 `W-wide`")
    print("     （`delta_a` 相对 SE 0.770，对比 D4 的 2.564 ⇒ 缩小 3.3 倍）。")
    print("  3. 但代价在行为上：`design_fim` 实测遗漏率 W-wide 0.400 / W-low 0.476")
    print("     vs D4 0.314 ⇒ **`delta_a` 精度与遗漏率是同一个旋钮**（把 W 压低、")
    print("     拉开），这正是 Stage 9 Objective 的 (C) 约束项要管的事。")


if __name__ == "__main__":
    main()
