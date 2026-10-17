#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性探针：逐种子读数之间的**相关系数**（判据带宽是否该按独立性算？）。

用法：
    python -u 1_Code/AutoRA_SPE/_scratch_pair_corr.py <out>.vals.json [<out2>.vals.json ...]

背景（D60 → 本探针）：`1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 的判据带宽
按 `2·√2·sd` 算，理由是「比的是**两个不同设计**的差 ⇒ `Var(差) = 2·sd²`」——
这条推导**假定两个设计的读数彼此独立**（`ρ = 0`）。而 `1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`
在**同一份种子表**上逐个设计扫种子时，若两设计的读数正相关（`ρ > 0`），
则正确的差带是 `2·sd·√(2(1−ρ))`，比 `2·√2·sd` **窄**。

本探针只做一件事：从落盘的逐种子读数里算出 `ρ` 的**实测值**与由它推出的系数，
再把「独立性假设下的系数 2√2」摆在一起对照 —— 免得把推导当事实。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if not argv:
        print("用法：python -u _scratch_pair_corr.py <out>.vals.json [...]")
        return 2
    for path in argv:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = d.get("rows", [])
        n_seeds = len(d.get("seeds", []))
        print(f"\n=== {path}（n_seeds = {n_seeds}、n_fim = {d.get('n_fim')}）===")
        if len(rows) < 2:
            print("  行数 < 2 ⇒ 无从算相关系数。")
            continue
        anchor = rows[0]
        av = [float(x) for x in anchor["vals"]]
        m_a = sum(av) / len(av)
        sd_a = math.sqrt(sum((x - m_a) ** 2 for x in av) / (len(av) - 1))
        print(f"  基准行（`rows[0]`，通常是 CRN 口径第 1 名；锚点一般排在**最后一行**）："
              f"{anchor['name']}")
        print(f"    `sd` = {sd_a:.6f}")
        print(f"  {'设计':<62} {'sd':>9} {'ρ(与基准行)':>10} {'sd_pair':>9} "
              f"{'实测系数':>9} {'独立性假设':>10}")
        for r in rows[1:]:
            rv = [float(x) for x in r["vals"]]
            m_r = sum(rv) / len(rv)
            sd_r = math.sqrt(sum((x - m_r) ** 2 for x in rv) / (len(rv) - 1))
            dv = [b - a for a, b in zip(av, rv)]
            m_d = sum(dv) / len(dv)
            sd_d = math.sqrt(sum((x - m_d) ** 2 for x in dv) / (len(dv) - 1))
            cov = sum((a - m_a) * (b - m_r) for a, b in zip(av, rv)) / (len(av) - 1)
            rho = cov / (sd_a * sd_r) if sd_a * sd_r else float("nan")
            # 实测的判据系数：`|差| ≥ k·sd` 与 `|差| ≥ 2·sd_pair` 等价 ⇒ k = 2·sd_pair/sd。
            k_meas = 2.0 * sd_d / sd_a
            k_indep = 2.0 * math.sqrt(2.0)
            name = r["name"] if len(r["name"]) <= 60 else r["name"][:57] + "..."
            print(f"  {name:<62} {sd_r:>9.6f} {rho:>+10.3f} {sd_d:>9.6f} "
                  f"{k_meas:>9.3f} {k_indep:>10.3f}")
        print("  ⇒ **结论（D61 实测，含一次自我纠错）**：这里 `ρ` 明显为正、实测系数 "
              "1.09…1.99 < 2.83 —— 但**不能**据此说 D60 的 `2·√2` 偏宽。原因是**本探针的输入**"
              "（`_scratch_mean_A_rank_*.vals.json`）由 `_scratch_anchor_seed_scan._one()` 产生，"
              "它把种子**直接**交给 `inner_eval` ⇒ 同一份种子表下所有设计**共用同一条随机流**"
              "（共享 CRN）⇒ 正相关是当然的、`sd_pair` 自然偏小。而 `stage9_loop.Evaluator._raw` "
              "用的是 `seed=cell_seed(d[\"name\"], base_seed)` ⇒ 每个设计各自一条流 ⇒ 两条臂"
              "**相互独立** ⇒ 带宽必须是 `2·√2·sd`（D60 不改）。⇒ 本探针量到的是"
              "「**若改用共享流 CRN 配对**，判据系数可以收到 1.1…2.0」——那是一条候选改进，"
              "不是现有判据的缺陷；两个口径都能用，但不可混用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
