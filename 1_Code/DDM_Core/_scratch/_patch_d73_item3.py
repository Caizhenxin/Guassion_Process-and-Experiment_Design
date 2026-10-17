# -*- coding: utf-8 -*-
"""D73 补丁：Stage 8 §11 第 3 条「被试太少」改口径为「口径不可估」。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

OLD = ("3. **被试层 PSIS-LOO 需要足够多的被试**：N=3 时 `max k` 达 4.33–5.00，不构成证据；"
       "~40 人/组的效果需在正式数据上验证。")
NEW = ("3. **被试层 PSIS-LOO 不是「被试太少」的问题，是口径不可估**（D73，见第 17 条）：`p_loo` 在被试层"
       "量的是 profile 边际在超参数抽取间的**离散度** ⇒ 加被试、加试次都不会让它变成参数个数"
       "（N=3 时 `max k` 4.33–5.00；N=4 × 569 试次时 `max k = 0.000`、`n_failed = 0` 两条判据全过，"
       "而 `p_loo/n_obs` 仍是数百）。模型比较请用试次层矩阵。")


def main() -> int:
    t = S8.read_text(encoding="utf-8")
    assert "\r" not in t
    if NEW in t:
        print("  [跳过] 已改")
        return 0
    assert t.count(OLD) == 1, f"旧文命中 {t.count(OLD)} 次"
    t = t.replace(OLD, NEW)
    if APPLY:
        S8.write_text(t, encoding="utf-8", newline="\n")
    print(f"  [{'写入' if APPLY else '干跑'}] Stage8 §11 第 3 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
