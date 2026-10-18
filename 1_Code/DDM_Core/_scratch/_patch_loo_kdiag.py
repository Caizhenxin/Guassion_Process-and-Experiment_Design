# -*- coding: utf-8 -*-
"""给 `loo.psis_loo` 加一个「Pareto k 诊断是否可信」的显式字段。

背景（本会话实测）：`psis_one` 只有在 `S >= 10` 时才计算，而平滑要求
`M = min(S/5, 3√S) >= _MIN_EXCESS = 5` ⇒ **S < 25 时 M < 5，永远不会拟合 GPD，
`k_hat` 恒为 0.0**。于是 `n_k_gt_bad = 0` 看着「全部健康」，其实是没有诊断能力。
旧行为：12 抽样下 `k_max = 0.0`、`n_failed = 0`，报告与图表会把它当成「k 诊断通过」。

本补丁只**新增**一个布尔字段 `k_diag_ok`（默认不改变任何既有数值），
并在 `elpd_loo` 处保持原样，避免影响已归档的历史 JSON 对照。
"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\loo.py")
src = P.read_text(encoding="utf-8")

ANCHOR = '''        "n_failed": int(np.sum(~ok)),
    }'''
NEW = '''        "n_failed": int(np.sum(~ok)),
        # S < 25 时 M = min(S/5, 3√S) < 5，GPD 永不拟合 ⇒ k̂ 恒 0，
        # `n_k_gt_bad = 0` 不代表「诊断通过」，只代表「没有诊断能力」。
        "k_diag_ok": bool(S >= 25),
    }'''
assert src.count(ANCHOR) == 1
src = src.replace(ANCHOR, NEW)
P.write_text(src, encoding="utf-8", newline="\n")
print("[ok] loo.psis_loo 增加 k_diag_ok（S >= 25）")
