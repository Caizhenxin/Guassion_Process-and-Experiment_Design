"""查证 t0 上界是否被顶住：把 stage8 的众数换回自然参数，看 t0 落在界内的什么位置。"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import read_formal_data as RF  # noqa: E402

DATA = ROOT / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
RES = json.loads((ROOT / "2_Data" / "Real_Data" / "New_Design" / "_pipeline"
                  / "stage8" / "stage8_results.json").read_text(encoding="utf-8"))

T0_LO = 0.05
rejected = {r["file"] for r in RES["rejected"]}
rows = []
for gid in ("1", "2", "3", "4"):
    files = [f for f in sorted(DATA.glob(f"exp_group{gid}_subject*.txt"))
             if f.name not in rejected]
    modes = RES["groups"][gid]["M-T3"]["fit"]["modes"]
    assert len(files) == len(modes), (gid, len(files), len(modes))
    for f, x in zip(files, modes):
        rec, _ = RF.load_file(f, stage="formal")
        tr, _ = RF.fit_ready(RF.to_trials(rec))
        lo, hi = RF.t0_bounds(tr)["t0"]
        x6 = float(x[6])
        t0_hat = lo + (hi - lo) * expit(x6)
        rt = np.asarray(tr["rt"], dtype=float)
        rt = rt[np.isfinite(rt) & (rt > 0)]
        rows.append({
            "gid": int(gid), "sid": int(rec["subjectID"]),
            "t0_lo": round(lo, 4), "t0_hi": round(hi, 4),
            "t0_hat": round(t0_hat, 4),
            "fill": round((t0_hat - lo) / (hi - lo), 3),
            "rt_min": int(rt.min() * 1000), "rt_q01": int(np.quantile(rt, .01) * 1000),
            "rt_q05": int(np.quantile(rt, .05) * 1000),
            "rt_q50": int(np.median(rt) * 1000),
        })

rows.sort(key=lambda r: -(r["fill"]))
print(f"{'组-人':>6} {'t0_lo':>7} {'t0_hi':>7} {'t0_hat':>7} {'界内位置':>6} "
      f"{'minRT':>6} {'q01':>5} {'q05':>5} {'q50':>5}")
for r in rows:
    print(f"{r['gid']}-{r['sid']:<4} {r['t0_lo']:>7.3f} {r['t0_hi']:>7.3f} "
          f"{r['t0_hat']:>7.3f} {r['fill']:>6.2f} {r['rt_min']:>6d} "
          f"{r['rt_q01']:>5d} {r['rt_q05']:>5d} {r['rt_q50']:>5d}")

n_top = sum(1 for r in rows if r["fill"] > 0.95)
gaps = [r["rt_min"] for r in rows]
print(f"\n顶住上界（界内位置 > 0.95）的被试：{n_top}/{len(rows)}")
print(f"最小 RT 跨度 {min(gaps)}–{max(gaps)} ms；"
      f"q01 中位数 {int(np.median([r['rt_q01'] for r in rows]))} ms")
print(f"t0_hat 中位 {np.median([r['t0_hat'] for r in rows]):.3f} s；"
      f"minRT 中位 {int(np.median(gaps))} ms")
