# -*- coding: utf-8 -*-
"""看 D65 干跑件里「非正定 Hessian」对 σ 的实际后果（D68 素材）。

只读：`stage8_synth3_dryrun/stage8_results.json`。
打印每个模型的 hyper 特征值、n_flipped、以及 exp(log_sigma) 的量级，
并与真值（合成数据 rho=0.6 等）对照，判断 σ 是否被 1/floor 撑大。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\DDM_Core\_scratch\stage8_synth3_dryrun\stage8_results.json")
d = json.loads(p.read_text(encoding="utf-8"))
print(f"文件：{p.name}；顶层键 = {sorted(d)}")
groups = d.get("groups") or {}
for tag, models in groups.items():
    if not isinstance(models, dict):
        continue
    print(f"\n== 组 {tag}（{len(models)} 个模型）==")
    for name, m in models.items():
        if not isinstance(m, dict):
            continue
        hy = m.get("hyper") or {}
        ev = hy.get("eigval")
        ls = hy.get("log_sigma")
        mu = hy.get("mu")
        nf = hy.get("n_flipped")
        if ev is None:
            print(f"  {name}：无 hyper.eigval")
            continue
        ev = np.asarray(ev, dtype=float)
        sigma = np.asarray(np.exp(np.asarray(ls, dtype=float))).ravel() if ls is not None else None
        print(f"  {name}：n_flipped={nf}/{ev.size}、eig ∈ [{ev.min():.3g}, {ev.max():.3g}]")
        if sigma is not None:
            print(f"    σ = exp(log_sigma)：形状 {np.asarray(ls).shape}、"
                  f"min {sigma.min():.3g}、max {sigma.max():.3g}")
            tail = np.exp(np.asarray(ls, dtype=float))[-1].ravel() if np.asarray(ls).ndim > 1 else sigma
            print(f"    σ（**末行/收敛**，前 8 个）= " + ", ".join(f"{float(v):.3g}" for v in tail[:8]))
            print(f"    σ（末行）max = {float(np.max(tail)):.3g}")
        if mu is not None:
            mu = np.asarray(mu, dtype=float).ravel()
            print(f"    μ（前 8 个）= " + ", ".join(f"{float(v):.3g}" for v in mu[:8]))
