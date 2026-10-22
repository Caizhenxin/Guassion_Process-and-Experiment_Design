"""挑一套「像这个范式」的生成真值：正确率 0.55–0.75、遗漏 0.10–0.30、RT 中位 0.5–0.8 s。

用法：python -X utf8 1_Code/DDM_Core/_scratch/_probe_gen_truth.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import gen_model_data as G  # noqa: E402

CANDIDATES = {
    "A_soft":   dict(d_ref=0.75, a_ref=1.45, beta_T=0.90, beta_S=0.25, t0=0.18),
    "B_mid":    dict(d_ref=0.65, a_ref=1.35, beta_T=0.80, beta_S=0.25, t0=0.18),
    "C_hard":   dict(d_ref=0.55, a_ref=1.30, beta_T=0.70, beta_S=0.25, t0=0.18),
    "D_slow":   dict(d_ref=0.48, a_ref=1.20, beta_T=0.60, beta_S=0.22, t0=0.22),
    "E_easy":   dict(d_ref=0.85, a_ref=1.55, beta_T=1.00, beta_S=0.28, t0=0.20),
}


def stats(trials: list[dict]) -> dict:
    resp = [t for t in trials if not t["omission"]]
    acc = float(np.mean([t["correct"] for t in resp]))
    om = float(np.mean([t["omission"] for t in trials]))
    rt = np.array([t["rt_ms"] for t in resp], dtype=float)
    out = {"acc": acc, "om": om, "rt_med": float(np.median(rt)),
           "rt_p10": float(np.percentile(rt, 10)), "rt_p90": float(np.percentile(rt, 90))}
    for name, key in (("acc_by_T", "T_ms"), ("acc_by_P", "P")):
        groups = {}
        for t in resp:
            groups.setdefault(t[key], []).append(t["correct"])
        out[name] = {k: round(float(np.mean(v)), 3) for k, v in sorted(groups.items())}
    self_acc = [t["correct"] for t in resp if t["is_self"] == 1]
    other_acc = [t["correct"] for t in resp if t["is_self"] == 0]
    out["self_minus_other_acc"] = round(float(np.mean(self_acc) - np.mean(other_acc)), 3)
    rt_self = [t["rt_ms"] for t in resp if t["is_self"] == 1]
    rt_other = [t["rt_ms"] for t in resp if t["is_self"] == 0]
    out["other_minus_self_rt"] = round(float(np.median(rt_other) - np.median(rt_self)), 1)
    return out


def main() -> int:
    for name, kw in CANDIDATES.items():
        truth = G.GEN_TRUTH.replace(**kw)
        res = G.generate("M-T1", ROOT / "1_Code" / "DDM_Core" / "_scratch" / "_probe" / name,
                         n_subjects_per_group=2, truth=truth, verbose=False)
        s = stats(res["trials"])
        print(f"\n== {name}  d_ref={kw['d_ref']} a_ref={kw['a_ref']} beta_T={kw['beta_T']}")
        print(f"   正确率 {s['acc']:.3f}  遗漏 {s['om']:.3f}  RT 中位 {s['rt_med']:.0f} ms "
              f"[p10 {s['rt_p10']:.0f}, p90 {s['rt_p90']:.0f}]")
        print(f"   自我−他人 正确率 {s['self_minus_other_acc']:+.3f}；"
              f"他人−自我 RT 中位 {s['other_minus_self_rt']:+.0f} ms")
        print(f"   按 T 正确率 {s['acc_by_T']}")
        print(f"   按 P 正确率 {s['acc_by_P']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
