# -*- coding: utf-8 -*-
"""10/12/15 人/组 下能拿到什么精度（保留 P 方案 0/8/32/120、4T×3W r12）。

* `beta_T`（被试内）：单被试 se_betaT / sqrt(n)；
* `beta_P`（组间）：只用自洽水平 {32,120} 的**两参数**回归（d_ref, beta_P），
  避免三参数在两点上秩亏（秩亏时 pinv 会把不可估方向报成 0 方差）。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import numpy as np

from mapping import f_P
from simulate import SUBJECT_SD

import design_search as DS

T4 = [0.0333, 0.0833, 0.14999, 0.24998]
W3 = [0.79998, 1.19990, 1.79990]

se_ref = DS.subject_se(120.0, T4, W3, 12, n_fim=2)
se_mid = DS.subject_se(32.0, T4, W3, 12, n_fim=2)
print("单被试被试层 SE（4T×3W r12、n_fim=2）")
for k in ("d_ref", "beta_T", "tau_T", "a_ref"):
    print(f"  P=120 {k}={se_ref[k]:.4f}    P=32 {k}={se_mid[k]:.4f}")

# ---- 组间两参数（d_ref, beta_P），水平 {32,120}
tau, ref = DS.GROUP_TRUTH["tau_P"], DS.GROUP_P_REF
P_arr = np.array([32.0, 120.0])
base = f_P(P_arr, tau) - f_P(ref, tau)
J = np.column_stack([np.ones_like(base), base])
se_d = np.array([se_mid["d_ref"], se_ref["d_ref"]])
print(f"\n组层真值：beta_P={DS.GROUP_TRUTH['beta_P']}、d_ref={DS.GROUP_TRUTH['d_ref']}"
      f"（口径 {DS.GROUP_TRUTH.get('name_label', 'design')}），J 的第二列 = {np.round(base, 4)}")

print("\n== 组间 beta_P（两参数、水平 32/120）==")
for n in (6, 8, 10, 12, 15, 20, 30):
    var_i = (SUBJECT_SD["d_ref"] ** 2 + se_d ** 2) / n
    cov = np.linalg.pinv(J.T @ (J / var_i[:, None]))
    sd = np.sqrt(np.maximum(np.diag(cov), 0.0))
    rel = sd[1] / abs(DS.GROUP_TRUTH["beta_P"])
    print(f"  n={n:3d}  sd_d={sd[0]:.4f}  sd_beta_P={sd[1]:.4f}（相对 {rel:.3f}）"
          f"  95%CI 半宽 ±{1.96 * sd[1]:.3f}")

print("\n== 被试内 beta_T（单被试 SE / sqrt(n)）==")
for n in (6, 8, 10, 12, 15, 20, 30, 43):
    rel = se_ref["beta_T"] / np.sqrt(n) / abs(DS.WITHIN_TRUTH.beta_T)
    print(f"  n={n:3d}  相对 SE = {rel:.3f}")
