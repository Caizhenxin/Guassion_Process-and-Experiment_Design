#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性探针：从落盘 payload 里挑出「推荐点 / 锚点 / 病态候选」的设计名。

用法：
    python -u 1_Code/AutoRA_SPE/_scratch_pick_designs.py <payload.json>

为什么要它：`(A)` 的**种子间**标准差只在锚点处量过（D59），而判据带宽却要
用在**任意两个设计**的差上（D60 的 √2 缺口）。要检验「同方差假设」，就得
先拿到几个有代表性的设计名，再去量它们各自的 `sd_A`。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if not argv:
        print("用法：python -u _scratch_pick_designs.py <payload.json>")
        return 2
    d = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    print(f"payload = {argv[0]}")
    print(f"anchor  = {d['anchor']['name']}")
    print(f"best    = {d['best']['name']}")
    cache = d.get("cache", {})
    feas = sorted((v for v in cache.values() if v.get("feasible")),
                  key=lambda v: float(v["A"]))
    print(f"\n可行集 (A) 最小 3 个（n = {len(feas)}）：")
    for v in feas[:3]:
        print(f"  A={v['A']:.6f} B={v['B']:.6f} 遗漏={float(v['omission']):.4f} "
              f"cond={float(v['cond']):.2e} n_bad={v['n_bad']}  {v['name']}")
    bad = sorted((v for v in cache.values()
                  if int(v.get("n_bad", 0)) > 0),
                 key=lambda v: -float(v["cond"]))
    print(f"\n病态候选（n_bad > 0，按 cond 降序）前 3 个（共 "
          f"{sum(1 for v in cache.values() if int(v.get('n_bad', 0)) > 0)} 个）：")
    for v in bad[:3]:
        print(f"  cond={float(v['cond']):.2e} n_bad={v['n_bad']} A={v['A']:.6f} "
              f"遗漏={float(v['omission']):.4f} 可行={v['feasible']}  {v['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
