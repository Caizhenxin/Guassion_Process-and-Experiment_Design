# -*- coding: utf-8 -*-
"""D73 补丁 2b：修掉已落纸的 §11 第 3 条里未经核实的「N=4 × 569 试次」说法。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

OLD = "（N=3 时 `max k` 4.33–5.00；N=4 × 569 试次时 `max k = 0.000`、`n_failed = 0` 两条判据全过，而 `p_loo/n_obs` 仍是数百）"
NEW = "（N=3 时 `max k` 4.33–5.00；N=4 的 analytic 干跑 `max k = 0.000`、`n_failed = 0` 两条判据全过，而 `p_loo/n_obs = 704`）"


def main() -> int:
    t = S8.read_text(encoding="utf-8")
    assert "\r" not in t
    if NEW in t:
        print("  [跳过] 已修")
        return 0
    n = t.count(OLD)
    if n != 1:
        print(f"  [失败] 旧文命中 {n} 次")
        return 1
    if APPLY:
        S8.write_text(t.replace(OLD, NEW), encoding="utf-8", newline="\n")
    print(f"  [{'写入' if APPLY else '干跑'}] §11 第 3 条数字纠正")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
