#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性探针：可行集内部 `(A)`／`(B)` 的铺开程度 vs 判据带宽。

用法：
    python -u 1_Code/AutoRA_SPE/_scratch_feasible_spread.py <payload.json> [<payload2.json> ...]

为什么要它：D60 把判据带宽改成**差**的噪声带 `2·√2·sd`。带宽一旦讲清楚，
「本预算下 (A,B) 上最好」这句话到底有多少信息量，就取决于**可行集内部**的
铺开程度：如果 `(A)` 的极差不比带宽大多少，那么「最优设计」的身份就**统计上
不唯一** —— 报告里点名的那个设计只是可行带内的一个点，不是被数据选出来的。

输出：每个 payload 一行摘要 + 一段明细（可行集 n、`(A)`/`(B)`/遗漏率的三分位
与极差、极差与带宽之比、与最优**不可分辨**的可行设计个数）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DIFF_BAND_FACTOR = 2.0 * (2.0 ** 0.5)


def _q(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    i = p * (len(ys) - 1)
    lo = int(i)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (i - lo)


def report(path: str) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    noise = d.get("noise") or {}
    sd_a = float(noise.get("sd_A", 0.0) or 0.0)
    sd_b = float(noise.get("sd_B", 0.0) or 0.0)
    band_a = DIFF_BAND_FACTOR * sd_a
    band_b = DIFF_BAND_FACTOR * sd_b
    cache = d.get("cache", {})
    feas = [v for v in cache.values() if v.get("feasible")]
    a = [float(v["A"]) for v in feas]
    b = [float(v["B"]) for v in feas]
    om = [float(v["omission"]) for v in feas]

    print(f"\n=== {path} ===")
    print(f"锚点 = {d['anchor']['name']}（可行 = {bool(d['anchor'].get('feasible'))}，"
          f"A = {float(d['anchor']['A']):.6f}）")
    print(f"推荐点 = {d['best']['name']}（A = {float(d['best']['A']):.6f}，"
          f"B = {float(d['best']['B']):.6f}）")
    print(f"标定：`sd_A` = {sd_a:.6g}（n_repeats = {noise.get('n_repeats')}）、"
          f"`sd_B` = {sd_b:.6g} ⇒ 判据带 `2·√2·sd_A` = {band_a:.6g}、"
          f"`2·√2·sd_B` = {band_b:.6g}")
    if not feas:
        print("可行集为空 ⇒ 无从谈铺开程度。")
        return {"path": path, "n_feasible": 0}

    amin, amax = min(a), max(a)
    bmin, bmax = min(b), max(b)
    print(f"\n可行集 n = {len(feas)}")
    print(f"  `(A)`  最小 {amin:.6f} / 中位 {_q(a, 0.5):.6f} / 最大 {amax:.6f}"
          f" ⇒ 极差 {amax - amin:.6f} = 判据带的 {(amax - amin) / band_a:.2f} 倍"
          if band_a > 0 else f"  `(A)` 极差 {amax - amin:.6f}（带宽未知）")
    print(f"  `(B)`  最小 {bmin:.6f} / 中位 {_q(b, 0.5):.6f} / 最大 {bmax:.6f}"
          f" ⇒ 极差 {bmax - bmin:.6f} = 判据带的 {(bmax - bmin) / band_b:.2f} 倍"
          if band_b > 0 else f"  `(B)` 极差 {bmax - bmin:.6f}（带宽未知）")
    print(f"  遗漏率 最小 {min(om):.4f} / 中位 {_q(om, 0.5):.4f} / 最大 {max(om):.4f}"
          f"（冻结带 = {d.get('settings', {}).get('omission_band') or [0.05, 0.20]}）")

    # 与最优「不可分辨」的可行设计：`ΔA < 判据带`（两根带子各判各的，见 D60）。
    near = [v for v in feas if float(v["A"]) - amin < band_a]
    near_b = [v for v in feas if abs(float(v["B"]) - float(d["best"]["B"])) < band_b]
    print(f"\n  ⇒ `(A)` 与最优**不可分辨**（`ΔA < {band_a:.6g}`）的可行设计："
          f"**{len(near)} / {len(feas)}**")
    print(f"  ⇒ `(B)` 与推荐点**不可分辨**（`|ΔB| < {band_b:.6g}`）的可行设计："
          f"**{len(near_b)} / {len(feas)}**")
    print("  前 5 个（按 `(A)` 升序）：")
    for v in sorted(feas, key=lambda v: float(v["A"]))[:5]:
        da = float(v["A"]) - amin
        print(f"    A={float(v['A']):.6f} (ΔA={da:.6f} = {da / band_a:.2f} 带) "
              f"B={float(v['B']):.6f} 遗漏={float(v['omission']):.4f}  {v['name']}")

    # 「最优身份的不可分辨」若只是个计数，读者仍会问：这些设计**长什么样**？
    # 若它们共享同一种结构（例如都是「最大 W 档 + 3–4 档 T + r12/r16」），那么
    # 站得住的说法是「**设计族**稳健、**确切点**不稳健」—— 这比单说「不唯一」有用。
    if len(_near_list := sorted(near, key=lambda v: float(v["A"]))) <= 15:
        print(f"\n  与最优不可分辨的可行设计全列（{len(_near_list)} 个）：")
        for v in _near_list:
            da = float(v["A"]) - amin
            print(f"    ΔA={da:.6f}（{da / band_a:.2f} 带）A={float(v['A']):.6f} "
                  f"B={float(v['B']):.6f} 遗漏={float(v['omission']):.4f}  {v['name']}")

    return {
        "path": path,
        "n_feasible": len(feas),
        "a_min": amin, "a_max": amax, "a_median": _q(a, 0.5),
        "b_min": bmin, "b_max": bmax,
        "band_a": band_a, "band_b": band_b,
        "a_spread_over_band": (amax - amin) / band_a if band_a else None,
        "nA_indistinguishable": len(near), "nB_indistinguishable": len(near_b),
        "anchor_feasible": bool(d["anchor"].get("feasible")),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print("用法：python -u _scratch_feasible_spread.py <payload.json> [...]")
        return 2
    out = [report(p) for p in argv]
    if len(out) > 1:
        print("\n=== 汇总 ===")
        for r in out:
            if not r.get("n_feasible"):
                print(f"  {r['path']}：可行集为空")
                continue
            print(f"  {Path(r['path']).name}：可行 {r['n_feasible']}、"
                  f"`(A)` 极差/带 = {r['a_spread_over_band']:.2f}、"
                  f"与最优不可分辨 {r['nA_indistinguishable']} 个、"
                  f"锚点可行 = {r['anchor_feasible']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
