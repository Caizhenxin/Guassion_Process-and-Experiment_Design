#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性探针：M-T1 下逐个 rho 值看内环读数（是否出现奇异信息矩阵）。

命名以 `_scratch_` 开头（派生/工作文件）。用完可删。
"""
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage9_inner as S9I  # noqa: E402

T4 = (0.03333, 0.08333, 0.14999, 0.24998)
W3 = (0.79998, 1.1999, 1.7999)
FOCUS = ["d_ref", "beta_T", "beta_S", "beta_ST"]

for rho in (1.0, 0.75, 0.6, 0.5):
    r = S9I.inner_eval(T4, W3, 12, model=S9I.M_T1, rho=rho, n_fim=1, seed=1000)
    g = S9I.geomean_relative_se(r, FOCUS)
    print(f"rho={rho}: omission={r['omission']:.4f} acc={r['acc']:.4f} "
          f"rt={r['rt_ms']:.1f}ms cond={r['cond']:.3g} n_bad={r['n_bad']} "
          f"se_rho={r['se_rho']:.4f} g4={g:.4f}")
    print("   rel_se: " + " ".join(f"{v:.4g}" for v in r["relative_se"]))
