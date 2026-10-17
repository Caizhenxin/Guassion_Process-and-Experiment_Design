"""一次性探针：**遗漏率带上界**的敏感性 —— 为「D55 第 18 条」的三种处置提供决策读数。

背景（主计划 L529 仍开放第 (1) 件）：冻结带是 `[0.05, 0.20]`，而 Stage 5 已定稿、正是要据以
正式采集的锚点 D4 实测遗漏率 **0.3611** ⇒ 它自己落在带外，且被 5 个可行设计在 `(A,B)` 上支配。
三种处置：(a) 不动规格、把不相容作为 9A 头条结论报出；(b) 显式重冻结带；(c) 保留带但 D4 只作
归一化锚点。

本探针不改任何冻结量，只从**已落盘的 cache** 复算：
  1. 现在可行的那批设计的遗漏率分布（带上界到底卡在哪一段）；
  2. 把带上界从 0.20 逐步放宽到 0.40（下界不动），可行集规模、最优 `(A)` 与「D4 是否可行」
     「D4 是否仍被支配」各怎么变；
  3. 若改用 (c)（相对 D4 的比值），四臂与推荐点各是多少。

用法：
    python -u _scratch_probe_band_sensitivity.py <payload.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

UPPERS = (0.20, 0.25, 0.30, 0.35, 0.3611, 0.37, 0.40)


def has_ill(r: dict) -> bool:
    gates = r.get("gates") or []
    return (any(("cond" in g) or ("n_bad" in g) for g in gates)
            or float(r.get("cond", 0.0)) > 1e10
            or int(r.get("n_bad", 0)) > 0)


def dominates(a: dict, b: dict, tol: float = 1e-12) -> bool:
    return (float(a["A"]) <= float(b["A"]) + tol) and (float(a["B"]) >= float(b["B"]) - tol)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    cache = payload["cache"]
    anchor = cache[payload["anchor"]["name"]]
    lo, hi = payload["d54"]["omission_band"]
    om_d4 = float(anchor["omission"])
    print(f"落盘件：`{Path(argv[1]).name}`（`n_fim = {payload['settings']['n_fim']}`，"
          f"cache {len(cache)} 个）")
    print(f"冻结带 `[{lo}, {hi}]`；锚点 `{anchor['name']}` 遗漏率 **{om_d4:.4f}**、"
          f"`A = {anchor['A']:.4f}`、`B = {anchor['B']:.4f}`、"
          f"`feasible = {anchor['feasible']}`")
    print()

    print("## 1. 现行口径下的遗漏率分布")
    print()
    feas = [r for r in cache.values() if r["feasible"]]
    band_only = [r for r in cache.values()
                 if not r["feasible"] and not has_ill(r)
                 and any("D54" in g for g in (r.get("gates") or []))]
    for tag, group in (("可行", feas), ("只被带否决", band_only)):
        if not group:
            print(f"- {tag}：0 个")
            continue
        oms = sorted(float(r["omission"]) for r in group)
        print(f"- {tag}：{len(group)} 个；遗漏率 min {oms[0]:.4f} / "
              f"中位 {oms[len(oms) // 2]:.4f} / max {oms[-1]:.4f}")
    alloms = [float(r["omission"]) for r in cache.values()]
    print(f"- 全部 {len(alloms)} 个候选：遗漏率 min {min(alloms):.4f} / "
          f"max {max(alloms):.4f}")
    print()

    print("## 2. 把**带上界**放宽（下界 `0.05` 不动），其余闸门不变")
    print()
    print("| 带上界 | 过带的设计 | 其中数值可用 | D4 在带内 | 可行集内 `(A)` 最小 | 该点 `B` | 支配 D4 的可行设计 |")
    print("|---|---|---|---|---|---|---|")
    for up in UPPERS:
        passed = [r for r in cache.values() if float(r["omission"]) <= up]
        usable = [r for r in passed if not has_ill(r)]
        d4_in = om_d4 <= up
        if usable:
            best = min(usable, key=lambda r: float(r["A"]))
            n_dom = sum(1 for r in usable if dominates(r, anchor))
            print(f"| {up:.4f} | {len(passed)} | {len(usable)} | {'是' if d4_in else '否'} | "
                  f"`{best['A']:.4f}` | `{best['B']:.4f}` | {n_dom} |")
        else:
            print(f"| {up:.4f} | {len(passed)} | 0 | {'是' if d4_in else '否'} | — | — | — |")
    print()
    print("⚠️ 「过带」只算了遗漏率一个条件；上表「其中数值可用」= 过带 **且** 没有 `cond`/`n_bad` 闸门。")
    print("⚠️ **下界 `0.05` 从未生效**："
          f"候选里遗漏率最小值 = {min(alloms):.4f}（见 §1）⇒ 现实里卡住设计的是**上界**。")
    print()

    print("## 3. 若改用 (c)：相对锚点 D4 的比值（锚点 = 1.000）")
    print()
    ns = payload.get("noise", {})
    print(f"（判据的带宽：`2·sd_A = {2 * float(ns.get('sd_A', float('nan'))):.4f}`、"
          f"`2·sd_B = {2 * float(ns.get('sd_B', float('nan'))):.4f}`）")
    print()
    print("| 对象 | `A` | `A / A_D4` | `B` | `B / B_D4` |")
    print("|---|---|---|---|---|")
    print(f"| 锚点 D4 | {anchor['A']:.4f} | 1.0000 | {anchor['B']:.4f} | 1.0000 |")
    for r in payload.get("compare", []):
        a, b = float(r["A_best"]), float(r["B_at_A_best"])
        if a != a or a == float("inf"):
            print(f"| 臂 {r['arm']} | — | — | — | — |")
            continue
        print(f"| 臂 {r['arm']} | {a:.4f} | {a / float(anchor['A']):.4f} | "
              f"{b:.4f} | {b / float(anchor['B']):.4f} |")
    best = payload.get("best", {})
    if best:
        a, b = float(best["A"]), float(best["B"])
        print(f"| **推荐点** | {a:.4f} | {a / float(anchor['A']):.4f} | "
              f"{b:.4f} | {b / float(anchor['B']):.4f} |")
    print()
    if best:
        a = float(best["A"])
        print(f"⇒ 推荐点比 D4 的 `(A)` 小 **{(1 - a / float(anchor['A'])) * 100:.1f}%**"
              f"（比值 {a / float(anchor['A']):.4f}）；改用比值口径**不会**让 D4 变得可行，"
              f"但会让「D4 排第几」成为一个可报的量。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
