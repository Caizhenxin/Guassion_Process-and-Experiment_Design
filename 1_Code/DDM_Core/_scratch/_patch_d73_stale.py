# -*- coding: utf-8 -*-
"""D73 补丁 2：清掉三处「被试层 LOO 需要足够多被试 / N 依赖」的旧口径。

命中点：
- 工作流_主计划.md L339（「一句必须带上的限制」）
- Stage8_建模与验证方案.md L213（§11 第 16 条 D70）
- 1_Code/DDM_Core/README.md L3548（§8.45 D70 段）
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

PAIRS = [
    (
        REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md",
        "- **一句必须带上的限制**：**被试层 PSIS-LOO 需要足够多的被试** —— N=3 实测 `max k` = 4.33 / 5.00、"
        "3/3 被试越界 ⇒ 该规模下**模型比较不构成证据**；~40 人/组的效果只能在**正式数据**上复验。",
        "- **一句必须带上的限制**（**D73 改写**）：**被试层 PSIS-LOO 的口径本身不可估** —— 它量的是 "
        "profile 边际在超参数抽取间的离散度，不是参数个数 ⇒ **加被试、加试次都不会好**（D70：3 人 × 96 "
        "试次 `p_loo/n_obs = 496`；4 人 analytic 干跑 `max k = 0.000`、`n_failed = 0` 两条判据全过，"
        "而 `p_loo/n_obs = 704`）。模型比较请用**试次层**矩阵；"
        "被试层留一用 bruteforce（小 N）/ K-fold（大 N）。**模型比较不构成证据**的范围因此改为"
        "「被试层 ΔELPD 一律不引用」，而不是「等 ~40 人再看」。",
    ),
    (
        REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md",
        " ⇒ 被试层 LOO **依旧无效**（§11 第 3 条的 N 依赖没有消失）；",
        " ⇒ 被试层 LOO **依旧无效**（**不是** N 依赖：见第 17 条 D73 的机理）；",
    ),
    (
        REPO / "1_Code" / "DDM_Core" / "README.md",
        "这不是数据来源的问题，是 §11 第 3 条的 N 依赖 ⇒ 「正向对照能做」与「LOO 能用」是两件事。",
        "这不是数据来源的问题，也不是「被试太少」（D73 已推翻该读法：被试层 `p_loo` 量的是 profile "
        "边际在超参数抽取间的离散度）⇒ 「正向对照能做」与「被试层 LOO 能用」是两件事；试次层 PSIS "
        "在同一批抽取下 `p_loo/n_obs = 0.138`、`k_max = 0`（§8.48）。",
    ),
]


def main() -> int:
    bad = 0
    for path, old, new in PAIRS:
        t = path.read_text(encoding="utf-8")
        assert "\r" not in t
        if new in t:
            print(f"  [跳过] {path.name}")
            continue
        n = t.count(old)
        if n != 1:
            print(f"  [失败] {path.name}：旧文命中 {n} 次")
            bad += 1
            continue
        if APPLY:
            path.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] {path.name}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
