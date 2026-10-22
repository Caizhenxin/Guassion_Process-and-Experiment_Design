"""第二组候选：让自我×T 交互（beta_ST）可见。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import gen_model_data as G  # noqa: E402

CANDIDATES = {
    "F": dict(d_ref=0.80, a_ref=1.52, beta_T=0.95, beta_S=0.30, beta_ST=0.12, t0=0.19),
    "G": dict(d_ref=0.75, a_ref=1.50, beta_T=1.00, beta_S=0.32, beta_ST=0.15, t0=0.19),
    "H": dict(d_ref=0.85, a_ref=1.60, beta_T=1.05, beta_S=0.35, beta_ST=0.18, t0=0.20),
}


def report(name, kw):
    truth = G.GEN_TRUTH.replace(**kw)
    res = G.generate("M-T1", ROOT / "1_Code" / "DDM_Core" / "_scratch" / "_probe" / name,
                     n_subjects_per_group=4, truth=truth, verbose=False)
    tr = res["trials"]
    resp = [t for t in tr if not t["omission"]]
    acc = np.mean([t["correct"] for t in resp])
    om = np.mean([t["omission"] for t in tr])
    rt = np.median([t["rt_ms"] for t in resp])
    print(f"\n== {name}")
    print(f"   正确率 {acc:.3f}  遗漏 {om:.3f}  RT 中位 {rt:.0f} ms")
    for key, lab in (("T_ms", "T"), ("P", "P")):
        rows = {}
        for t in resp:
            rows.setdefault(t[key], {"s": [], "o": []})
            rows[t[key]]["s" if t["is_self"] == 1 else "o"].append(t["correct"])
        print(f"   按 {lab}：", {k: (round(float(np.mean(v["s"])), 3),
                                    round(float(np.mean(v["o"])), 3))
                                 for k, v in sorted(rows.items())})
    for key in ("T_ms", "W_ms"):
        rows = {}
        for t in resp:
            rows.setdefault(t[key], []).append(t["rt_ms"])
        print(f"   RT 中位按 {key}：", {k: round(float(np.median(v)), 0) for k, v in sorted(rows.items())})


for name, kw in CANDIDATES.items():
    report(name, kw)
