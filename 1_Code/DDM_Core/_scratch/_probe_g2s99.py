# -*- coding: utf-8 -*-
"""临时探针：看 exp_group2_subject99.txt 的结构与 RT 分布（6-E 用）。"""
import collections
import statistics as st

P = r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\exp_group2_subject99.txt"
raw = open(P, encoding="utf-8", errors="replace").read().splitlines()
print("lines", len(raw))
h = raw[0].split("\t")
print("cols", len(h))
print("header", h)
rows = [ln.split("\t") for ln in raw[1:] if ln.strip()]
idx = {k: i for i, k in enumerate(h)}


def g(r, k):
    return r[idx[k]].strip()


print("n", len(rows), "widthset", sorted({len(r) for r in rows}))
print("stage", collections.Counter(g(r, "stage") for r in rows))
print("block", collections.Counter(g(r, "block") for r in rows))
print("trialID", sorted({int(g(r, "trialID")) for r in rows})[:20], "...", max(int(g(r, "trialID")) for r in rows))
print("Response", collections.Counter(g(r, "Response") for r in rows))
print("premature", collections.Counter(g(r, "premature_press") for r in rows))
print("timeout", collections.Counter(g(r, "timeout") for r in rows))
resp = [r for r in rows if g(r, "Response") in ("f", "j")]
print("responded", len(resp))
for r in resp:
    print("  trial=%s T=%.3f RT=%s W=%.3f dur=%s frames=%s corr=%s" % (
        g(r, "trialID"), float(g(r, "T")), g(r, "RT"), float(g(r, "W")),
        g(r, "stimulus_dur_actual"), g(r, "stimulus_frames"), g(r, "Correct")))
if resp:
    rts = [float(g(r, "RT")) for r in resp]
    Ts = [float(g(r, "T")) for r in resp]
    print("RT med %.4f min %.4f max %.4f" % (st.median(rts), min(rts), max(rts)))
    print("RT<T", sum(1 for a, b in zip(rts, Ts) if a < b), "RT>=T", sum(1 for a, b in zip(rts, Ts) if a >= b))
    print("RT-T(ms)", [round((a - b) * 1000, 1) for a, b in zip(rts, Ts)])
