# -*- coding: utf-8 -*-
"""用 D65 干跑的真实 results.json 渲染一次报告（不重新拟合），
确认新的「超参数 Hessian」两行在真实数字上打得出来（D68 素材）。
"""
import json
import sys
from pathlib import Path

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import stage8_run as SR                                             # noqa: E402

p = REPO / "1_Code" / "DDM_Core" / "_scratch" / "stage8_synth3_dryrun" / "stage8_results.json"
d = json.loads(p.read_text(encoding="utf-8"))
res = d["groups"]["1"]
lines = SR.render_group(res, [], tag="1", n_draws=4, seed=0)
txt = "\n".join(lines)
keep = [ln for ln in lines
        if ("ELPD" in ln or "超参数 Hessian" in ln or "floor" in ln or "ρ" in ln)]
print("\n".join(keep))
print(f"\n[自检] 含「不得解读」= {'不得解读' in txt}")
