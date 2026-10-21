# -*- coding: utf-8 -*-
"""按用户决定（保留 P 方案 0/8/32/120、tau_P 降级为探索性）重算：
只对 beta_T（10%）与 beta_P（0.30）两条判据求所需人数。

两种口径都报：
  * 保守：只用真正携带信息的两个水平 {32, 120}；
  * 乐观：把 P=0 也算进去（`drift_magnitude` 里它被截到 0，模型预测为负、
    与生成数据的符号不一致，所以这个口径不能当主结论）。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import numpy as np
import design_search as DS

DS.use_truth("design")
T4 = [0.0333, 0.0833, 0.14999, 0.24998]
W3 = [0.79998, 1.19990, 1.79990]
W4 = [0.79998, 1.09995, 1.39992, 1.79990]

# 每个候选被试内设计的 beta_T 需人数
cands = {
    "4T×3W r12（现行，576 试次）": (T4, W3, 12),
    "4T×4W r9（144 试次）": (T4, W4, 9),
    "4T×2W r18（144 试次）": (T4, [0.79998, 1.79990], 18),
}
print(f"{'设计':30s} {'βT 需 N':>8s}   {'βP 需 N（{32,120}）':>20s}   {'βP 需 N（{0,32,120}）':>22s}")
for name, (T, W, r) in cands.items():
    se_ref = DS.se_full(name, DS.P_SINGLE, T, W, r, 2)
    rel_bT = DS.rel_se(se_ref)["beta_T"]
    n_bT = int(np.ceil((rel_bT / 0.10) ** 2))
    out = []
    for lv in ([32, 120], [0, 32, 120]):
        ses = []
        for p in lv:
            s = DS.se_full(name, float(p), T, W, r, 1)["d_ref"]
            ses.append(s)
        keep = [p for p, s in zip(lv, ses) if np.isfinite(s) and s > 1e-9 and s < DS.SE_D_UNUSABLE]
        se_used = np.array([s for p, s in zip(lv, ses) if p in keep])
        if len(keep) < 2:
            out.append("不可估")
            continue
        r_ = DS.needed_n(se_used, np.array(keep, float), 0.30, "beta_P", n_max=600)
        out.append(str(r_["n"]))
    print(f"{name:30s} {n_bT:8d}   {out[0]:>20s}   {out[1]:>22s}")
