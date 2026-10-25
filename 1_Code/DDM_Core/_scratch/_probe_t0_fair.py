"""公平对照：把「现状参数」与「截尾后重拟合参数」放到**同一批（截尾后）试次**上比 ℓ。

上一版比的是 ℓ_A(全部) vs ℓ_B(截尾)，而截尾本身就会让人均 ℓ 变好看（丢掉最差的几个点），
所以那个比较对 B 有利、不成立。这里改成两者都在截尾后的同一批试次上算。

现状参数直接取 stage8 D121 的众数（`fit.modes` 是无约束 x，用 `_from_x` 还原自然参数），
因此只需重拟合 B（3 次）。
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import read_formal_data as RF  # noqa: E402
from likelihood import fit_mle, log_likelihood, _from_x, PARAM_BOUNDS  # noqa: E402
from mapping import WITHIN_FREE_LIN, MappingParams  # noqa: E402
from recover_group import GROUP_INIT_LIN  # noqa: E402
from power_recovery import _clamp_init  # noqa: E402

DATA = ROOT / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
RES = json.loads((ROOT / "2_Data" / "Real_Data" / "New_Design" / "_pipeline"
                  / "stage8" / "stage8_results.json").read_text(encoding="utf-8"))
REJ = {r["file"] for r in RES["rejected"]}
CENSOR = 0.20
SUBJECTS = [("2", 5), ("4", 5), ("1", 3), ("3", 2)]


def _lo_hi(tr):
    lo = np.array([PARAM_BOUNDS[n][0] for n in WITHIN_FREE_LIN])
    hi = np.array([PARAM_BOUNDS[n][1] for n in WITHIN_FREE_LIN])
    tb = RF.t0_bounds(tr)["t0"]
    j = WITHIN_FREE_LIN.index("t0")
    lo[j], hi[j] = tb
    return lo, hi


def _subset(tr, keep):
    out = {}
    n = np.asarray(tr["rt"]).size
    for k, v in tr.items():
        arr = np.asarray(v)
        out[k] = arr[keep] if arr.shape[:1] == (n,) else v
    return out


for gid, sid in SUBJECTS:
    files = [f for f in sorted(DATA.glob(f"exp_group{gid}_subject*.txt"))
             if f.name not in REJ]
    idx = [int(f.stem.split("subject")[1]) for f in files].index(sid)
    x = RES["groups"][gid]["M-T3"]["fit"]["modes"][idx]

    rec, _ = RF.load_file(DATA / f"exp_group{gid}_subject{sid}.txt", stage="formal")
    tr, _ = RF.fit_ready(RF.to_trials(rec))
    rt = np.asarray(tr["rt"], float)
    keep = ~(np.isfinite(rt) & (rt < CENSOR))
    trB = _subset(tr, keep)

    lo, hi = _lo_hi(tr)
    th = _from_x(np.asarray(x, float), lo, hi)
    pA = MappingParams(shape_model="lin").with_vector(WITHIN_FREE_LIN, th)
    llA_full = log_likelihood(pA, tr)
    llA_cens = log_likelihood(pA, trB)

    ov = RF.t0_bounds(trB)
    init = _clamp_init(GROUP_INIT_LIN, ov)
    fB = fit_mle(trB, WITHIN_FREE_LIN, init, n_restart=2, maxiter=400, maxfun=20000,
                 bounds_override=ov, gtol=1e-9, ftol=1e-13)
    llB = fB["loglik"]
    n_tot = np.asarray(tr["rt"]).size
    n_cen = np.asarray(trB["rt"]).size
    print(f"\n══ {gid}-{sid}：丢 {n_tot - n_cen} 试次（{n_tot} → {n_cen}）")
    print(f"  t0 上界：现状 {_lo_hi(tr)[1][WITHIN_FREE_LIN.index('t0')]:.3f} → "
          f"截尾 {ov['t0'][1]:.3f}")
    print(f"  现状参数的 t0 = {pA.t0:.3f}（顶界？{abs(pA.t0 - _lo_hi(tr)[1][WITHIN_FREE_LIN.index('t0')]) < 1e-3}）")
    print(f"  截尾后重拟合的 t0 = {fB['params'].t0:.3f}")
    print(f"  同一批试次上：ℓ(现状参数) = {llA_cens:.2f}   ℓ(重拟合) = {llB:.2f}   "
          f"Δ = {llB - llA_cens:+.2f}（人均 {(llB - llA_cens) / n_cen:+.4f}）")
    print(f"  参考：现状参数在**全部**试次上 ℓ = {llA_full:.2f}（人均 {llA_full / n_tot:+.4f}）")
