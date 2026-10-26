"""λ 剖面（低漏答被试）：污染项在「漏答少」的人身上是否有用。"""
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
people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
rows = []
for p in people:
    tr = p["tr"]
    om = float(tr["omission"].mean())
    fast = float(np.mean((tr["omission"] == 0) & (tr["rt"] <= 0.40)))
    rows.append((om, fast, p["group"], p["subject"], p))
rows.sort()
print(f"{'组-被试':>8s}{'漏答率':>8s}{'快反应占比':>10s}")
for om, fast, g, s, _ in rows:
    print(f"{f'{g}-{s}':>8s}{om:>8.2f}{fast:>10.2f}")

pick = rows[:3] + rows[-3:]
for om, fast, g, s, p in pick:
    tr0 = p["tr"]
    responded = tr0["omission"] == 0
    rt_min = float(tr0["rt"][responded].min())
    init = replace(GROUP_INIT_LIN, t0=min(GROUP_INIT_LIN.t0, rt_min - 0.02))
    print(f"\n=== {g}-{s}：{tr0['rt'].size} 试次（漏答 {om:.2f}、快反应 {fast:.2f}）===")
    print(f"{'λ':>5s}{'ℓ_max':>11s}{'Δℓ':>8s}{'t0':>7s}{'v':>7s}")
    base = None
    for lam in (0.0, 0.05, 0.10, 0.15):
        tr = dict(tr0)
        tr["lambda_guess"] = lam
        r = L.fit_mle(tr, list(WITHIN_FREE_LIN), init,
                      n_restart=1, maxiter=250, maxfun=6000)
        ll = r["loglik"]
        base = ll if base is None else base
        print(f"{lam:>5.2f}{ll:>11.2f}{ll - base:>8.2f}"
              f"{r['params'].t0:>7.3f}{r['params'].d_ref:>7.3f}")
