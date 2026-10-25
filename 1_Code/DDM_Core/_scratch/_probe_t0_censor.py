"""查证「快反应当污染项、把 t0 上界压死」：删掉极快试次后 t0 会不会抬起来。

对照三种做法（同一被试、同一模型 M-T3）：
  A 现状：全部已响应试次进拟合（t0 上界 = minRT − 0.02）
  B 截尾：丢掉 RT < CENSOR 的试次，t0 上界随之抬高
  C 放宽：不删试次，仅把 t0 上界放宽到 0.45（必然触发似然闸门，用作对照）

输出：三种做法的 ℓ、t0_hat、上界、以及被丢掉的试次数。
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import read_formal_data as RF  # noqa: E402
from mapping import WITHIN_FREE_LIN  # noqa: E402
from likelihood import fit_mle  # noqa: E402
from recover_group import GROUP_INIT_LIN  # noqa: E402
from power_recovery import _clamp_init  # noqa: E402
from scipy.special import expit  # noqa: E402

DATA = ROOT / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
CENSOR = 0.20
SUBJECTS = [("2", 5), ("4", 5), ("1", 3)]


def _fit(tr, ov):
    init = _clamp_init(GROUP_INIT_LIN, ov)
    return fit_mle(tr, WITHIN_FREE_LIN, init, n_restart=2, maxiter=400,
                   maxfun=20000, bounds_override=ov, gtol=1e-9, ftol=1e-13)


def _t0_of(p, ov):
    """`fit_mle` 的 `params` 是**自然参数**（MappingParams），直接用。"""
    return float(p.t0)


for gid, sid in SUBJECTS:
    f = DATA / f"exp_group{gid}_subject{sid}.txt"
    rec, _ = RF.load_file(f, stage="formal")
    tr, _ = RF.fit_ready(RF.to_trials(rec))
    rt = np.asarray(tr["rt"], float)
    n_all = rt.size
    n_fast = int(np.sum(np.isfinite(rt) & (rt < CENSOR)))
    print(f"\n══ {gid}-{sid}：保留试次 {n_all}、其中 RT<{CENSOR * 1000:.0f} ms 的有 "
          f"{n_fast} 个（{n_fast / n_all:.1%}）")

    ovA = RF.t0_bounds(tr)
    fA = _fit(tr, ovA)
    print(f"  A 现状      ℓ={fA['loglik']:.2f}  t0={_t0_of(fA['params'], ovA):.3f}  "
          f"上界={ovA['t0'][1]:.3f}")

    # B：截尾（丢掉极快试次）
    keep = ~(np.isfinite(rt) & (rt < CENSOR))
    trB = {}
    for k, v in tr.items():
        arr = np.asarray(v)
        if arr.shape[:1] == rt.shape:
            trB[k] = arr[keep]
        else:
            trB[k] = v
    ovB = RF.t0_bounds(trB)
    fB = _fit(trB, ovB)
    print(f"  B 截尾      ℓ={fB['loglik']:.2f}  t0={_t0_of(fB['params'], ovB):.3f}  "
          f"上界={ovB['t0'][1]:.3f}  （丢 {int((~keep).sum())} 试次，"
          f"ℓ 与 A 不可直接比）")

    # C：只放宽上界（预期触发似然闸门 ⇒ −inf）
    ovC = {"t0": (RF._T0_LOWER, 0.45)}
    fC = _fit(tr, ovC)
    ll = fC.get("loglik", float("nan"))
    print(f"  C 放宽界    ℓ={ll:.2f}  t0={_t0_of(fC['params'], ovC):.3f}  "
          f"上界=0.450")
