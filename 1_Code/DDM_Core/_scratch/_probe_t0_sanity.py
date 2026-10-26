"""自检：用 stage8_results.json 的 M-T3 单被试 MAP 参数做 PPC（RT 与正确率）。

目的：核实组层 `t0`≈0.45–0.56 s 是否真实。若真，则 RT = t0 + τ 要求
τ≈0.15 s，而 a≈2.0 / d≈1.2 的理论均值决策时间约 0.8 s，二者矛盾。
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
import hier                             # noqa: E402
import mapping                          # noqa: E402
import twophase as TP                   # noqa: E402
from recover_group import WITHIN_FREE_LIN   # noqa: E402

P = (REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "stage8_d123"
     / "stage8_results.json")
d = json.loads(P.read_text(encoding="utf-8"))
names = list(WITHIN_FREE_LIN)
lo, hi = hier._bounds_with_rho(names)

# 观测：正式段响应试次中位 RT（trial_clean 全表，含抢按，仅作量级参考）
tc = np.genfromtxt(REPO / "2_Data" / "Generate_Data" / "_real_check" / "trial_clean.csv",
                   delimiter=",", names=True, dtype=None, encoding="utf-8")
rt_obs = np.asarray(tc["rt"], float) if "rt" in tc.dtype.names else np.asarray(tc["RT"], float)
print("观测 RT 中位 %.3f s（n=%d）" % (np.nanmedian(rt_obs), rt_obs.size))

rng = np.random.default_rng(0)
for gid in ("1", "2"):
    m = d["groups"][gid]["M-T3"]
    modes = np.asarray(m["fit"]["modes"], float)
    vals = hier._from_x(modes, lo, hi)
    print(f"组 {gid} M-T3 被试 t0:", np.round(vals[:, 6], 4))
    design = {"P": np.full(400, 30.0), "T": np.full(400, 0.10),
              "W": np.full(400, 2.0), "is_self": np.zeros(400, int),
              "is_match": np.resize([1, 0], 400)}
    for i in range(modes.shape[0]):
        p = mapping.MappingParams()
        for j, n in enumerate(names):
            setattr(p, n, float(vals[i, j]))
        sim = TP.simulate_step_subject(design, p, 1.0, rng, t_max=6.0)
        rt = np.asarray(sim["rt"], float)
        ok = np.isfinite(rt) & (rt > 0)
        print("   被试%d 模拟 RT 中位 %.3f  漏答 %.3f  t0 %.3f  a %.3f  d %.3f"
              % (i + 1, np.median(rt[ok]) if ok.any() else float("nan"),
                 float(np.mean(sim["omission"])), p.t0, p.a_ref, p.d_ref))
