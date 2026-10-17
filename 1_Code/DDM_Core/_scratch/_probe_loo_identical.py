# -*- coding: utf-8 -*-
"""读 4 人干跑的 `stage8_results.json`，把两个模型的 LOO 读数逐位比出来。

**为什么**（D52/D53 之后的一条新诊断）：干跑报告里 M-T1 与 M-T3 的 `p_loo` 都打印成
`2816.26`。如果两个**结构不同**的模型在同一份数据上给出**逐位相同**的 `p_loo`，
那说明 PSIS 的权重分布已经退化到估计量在返回一个由数据结构（而不是模型）决定的值。
本脚本把这件事量出来，供写进 Stage 8 的已知限制与决策记录。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path("1_Code/DDM_Core/_scratch/_s8run_an4/stage8_results.json")
data = json.loads(P.read_text(encoding="utf-8"))

FIELDS = ("elpd_loo", "se", "p_loo", "n_obs", "n_draws", "n_obs", "k_max", "k_median",
          "n_k_gt_bad", "n_k_gt_unusable", "n_failed", "n_nonfinite_loglik")

for gname, models in data.get("groups", {}).items():
    print(f"=== 组 {gname} ===")
    rows = {}
    for mname, r in models.items():
        lk = r.get("loo", {})
        rows[mname] = r
        print(f"\n[{mname}]  rho_free={r.get('rho_free')}  seconds={r.get('seconds')}")
        print(f"  hyper_method={r.get('hyper_method')}  k={r.get('k')}  n_subjects={r.get('n_subjects')}")
        for k in FIELDS:
            if k in lk:
                print(f"  {k:22s} = {lk[k]!r}")
        fit = r.get("fit", {})
        print(f"  fit.n_flipped={fit.get('n_flipped')} n_em_used={fit.get('n_em_used')}"
              f" n_fallback={fit.get('n_fallback')} n_nonfinite_g={fit.get('n_nonfinite_g')}")
        print(f"  r.n_degenerate_fallback={r.get('n_degenerate_fallback')}"
              f" n_degenerate_nonfinite={r.get('n_degenerate_nonfinite')}"
              f" loo_stats={r.get('loo_stats')}")
    if len(rows) >= 2:
        names = list(rows)
        a, b = names[0], names[1]
        la, lb = rows[a].get("loo", {}), rows[b].get("loo", {})
        print(f"\n--- {a} vs {b} 的逐字段比较 ---")
        for k in FIELDS:
            if k in la and k in lb:
                same = "逐位相同" if repr(la[k]) == repr(lb[k]) else "不同"
                print(f"  {k:22s}: {la[k]!r} vs {lb[k]!r}  ⇒ {same}")
        if "p_loo" in la and "p_loo" in lb:
            pa, pb = float(la["p_loo"]), float(lb["p_loo"])
            n_obs = int(la.get("n_obs", 0))
            print(f"\n  `p_loo` 绝对差 = {abs(pa - pb):.6e}；`p_loo`/`n_obs` = "
                  f"{pa / n_obs:.4g} / {pb / n_obs:.4g}，健康区间是 [0, {n_obs}]")
        if "elpd_loo" in la and "elpd_loo" in lb:
            print(f"  ΔELPD = {float(lb['elpd_loo']) - float(la['elpd_loo']):.4f}"
                  f"（不能与各自的 `se` 直接相减 —— 那是两个边际 SE，不是配对 SE）")
