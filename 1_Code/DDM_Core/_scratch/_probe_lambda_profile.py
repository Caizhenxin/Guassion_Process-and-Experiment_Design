"""λ 剖面：单个被试、M-T3（ρ=1）、8 个映射参数自由，λ 取 0/0.05/0.10/0.15/0.20 重拟合。

判据：λ>0 让最大似然明显上升（Δℓ 远超 1 个参数的代价）⇒ 污染项确实需要。
"""
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))

import stage8_run as S            # noqa: E402
from mapping import MappingParams  # noqa: E402
import likelihood as L             # noqa: E402
from recover_group import GROUP_INIT_LIN, WITHIN_FREE_LIN  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
WANT = {(1, 2), (3, 3), (4, 5)}

people, rejected = S.collect([DATA], None, MappingParams(shape_model="lin"))
print(f"可用 {len(people)} 人、被拒 {len(rejected)}")
pick = [p for p in people if (p["group"], p["subject"]) in WANT]

for p in pick:
    tr0 = p["tr"]
    om = tr0["omission"] == 0
    rt_min = float(tr0["rt"][om].min())
    init = replace(GROUP_INIT_LIN, t0=min(GROUP_INIT_LIN.t0, rt_min - 0.02))
    print(f"\n=== 组 {p['group']} 被试 {p['subject']}：{tr0['rt'].size} 试次"
          f"（漏答 {int(tr0['omission'].sum())}，最小 RT {rt_min:.3f} s，"
          f"W_ref {float(np.max(tr0['W'])):.2f}）===")
    print(f"{'λ':>5s}{'ℓ_max':>11s}{'Δℓ':>8s}{'t0':>7s}{'a':>7s}{'v':>7s}"
          f"{'秒':>6s}")
    base = None
    for lam in (0.0, 0.05, 0.10, 0.15, 0.20):
        tr = dict(tr0)
        tr["lambda_guess"] = lam
        t0s = time.time()
        r = L.fit_mle(tr, list(WITHIN_FREE_LIN), init,
                      n_restart=1, maxiter=250, maxfun=6000)
        ll = r["loglik"]
        base = ll if base is None else base
        par = r["params"]
        print(f"{lam:>5.2f}{ll:>11.2f}{ll - base:>8.2f}{par.t0:>7.3f}"
              f"{par.a_ref:>7.3f}{par.d_ref:>7.3f}{time.time() - t0s:>6.1f}")
