"""PPC 口径探针：预测数据是否也该套「剔 RT<0.20」——否则 p10 被系统性拉低。"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))

import stage8 as S8                                  # noqa: E402
import stage8_run as S                               # noqa: E402
import hier                                          # noqa: E402
from mapping import MappingParams                    # noqa: E402
from recover_group import WITHIN_FREE_LIN            # noqa: E402

OUT = REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "stage8_d123"
DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
RT_FLOOR = 0.20
QS = (10, 25, 50, 75, 90)

people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
groups = {}
for p in people:
    groups.setdefault(p["group"], []).append(p)

for gname, subj, model in ((4, 5, "M-T3"), (1, 1, "M-T1"), (2, 5, "M-T3")):
    plist = groups[gname]
    idx = [i for i, p in enumerate(plist) if p["subject"] == subj][0]
    res = json.loads((OUT / f"stage8_group_{gname}.json").read_text(encoding="utf-8"))["results"][model]
    ov = {**plist[idx]["t0_bounds"]}
    if res["rho_free"]:
        ov = {**ov, "rho": (0.0, 3.0)}
    names = WITHIN_FREE_LIN + (["rho"] if res["rho_free"] else [])
    lo, hi = hier._bounds_with_rho(names, ov)
    th = hier._from_x(np.asarray(res["fit"]["modes"][idx], float), lo, hi)
    p_map = plist[idx]["p_base"].with_vector(WITHIN_FREE_LIN, th[:len(WITHIN_FREE_LIN)])
    tr = plist[idx]["tr"]
    design = {k: np.asarray(tr[k]) for k in ("P", "T", "W", "is_self", "is_match")}
    rng = np.random.default_rng(20261026)
    preds = [S8.sample_ppc(design, p_map, rng) for _ in range(8)]

    def qs(rt):
        rt = np.asarray(rt, float)
        return np.percentile(rt, QS) * 1000.0

    obs = tr["rt"][(tr["omission"] == 0) & (tr["rt"] >= RT_FLOOR)]
    raw, flt = [], []
    for s in preds:
        m = s["omission"] == 0
        raw.append(s["rt"][m])
        flt.append(s["rt"][m & (s["rt"] >= RT_FLOOR)])
    raw = np.concatenate(raw)
    flt = np.concatenate(flt)
    print(f"\n=== 组 {gname} 被试 {subj} / {model} ===")
    print(f"{'':>6s}" + "".join(f"{f'p{q}':>9s}" for q in QS))
    print(f"{'观测':>6s}" + "".join(f"{v:>9.0f}" for v in qs(obs)))
    print(f"{'预测(原)':>6s}" + "".join(f"{v:>9.0f}" for v in qs(raw)))
    print(f"{'预测(剔)':>6s}" + "".join(f"{v:>9.0f}" for v in qs(flt)))
    o = qs(obs)
    print(f"{'差值(原)':>6s}" + "".join(f"{v - x:>+9.0f}" for v, x in zip(qs(raw), o)))
    print(f"{'差值(剔)':>6s}" + "".join(f"{v - x:>+9.0f}" for v, x in zip(qs(flt), o)))
    print(f"  剔掉比例：预测 {1 - flt.size / raw.size:.3f}；观测 <0.20 已被上游剔除")
