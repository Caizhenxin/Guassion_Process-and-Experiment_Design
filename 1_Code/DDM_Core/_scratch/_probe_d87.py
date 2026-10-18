import csv, statistics as st, collections
p = r"1_Code\Experiment\exp_matlab\EXP_data_group1_99.csv"
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
f = lambda r, k: float(r[k])
form = [r for r in rows if r["stage"] == "formal"]
print("rows", len(rows), "cols", len(rows[0]), "formal", len(form), "practice", len(rows) - len(form))
NA = ("na", "NA", "")
npa = [r for r in form if r["Response"] in NA]
fl = [f(r, "stimulus_dur_actual") / f(r, "stimulus_frames") for r in npa if f(r, "stimulus_frames") > 0]
flip = st.median(fl)
print("flip %.6f ms hz %.3f" % (flip * 1000, 1 / flip))
for T in sorted({f(r, "T") for r in form}):
    sub = [r for r in form if abs(f(r, "T") - T) < 1e-9]
    d = st.median([f(r, "stimulus_dur_actual") for r in sub])
    fr = sorted({round(f(r, "stimulus_dur_actual") / flip) for r in sub if r["Response"] in NA})
    print(" T %.3f ms -> dur %.3f ms (%+0.4f) frames %s" % (T * 1000, d * 1000, (d - T) * 1000, fr))
for W in sorted({f(r, "W") for r in form}):
    sub = [r for r in form if abs(f(r, "W") - W) < 1e-9 and r["Response"] in NA]
    print(" W %.6f s -> frames %s" % (W, sorted({round(f(r, "stimulus_dur_actual") / flip) for r in sub})))
devs = [((f(r, "stimulus_dur_actual") - f(r, "T")) / flip, r) for r in npa]
print("non-press", len(npa), "dev min %+0.4f max %+0.4f" % (min(d for d, _ in devs), max(d for d, _ in devs)), "bad", sum(1 for d, _ in devs if not (-0.5 <= d < 1.5)))
print("dev==0", sum(1 for d, _ in devs if abs(d) < 1e-3), "frames==round", sum(1 for r in npa if round(f(r, "stimulus_dur_actual") / flip) == int(f(r, "stimulus_frames"))), "/", len(npa))
print("offset==mask", sum(1 for r in form if abs(f(r, "stimulus_offset_actual") - f(r, "mask_onset_actual")) < 1e-5), "/", len(form))
print("mask==onset+dur", sum(1 for r in form if abs(f(r, "mask_onset_actual") - f(r, "stimulus_onset_actual") - f(r, "stimulus_dur_actual")) < 1e-5), "/", len(form))
press = [r for r in form if r["Response"] in ("f", "j")]
print("premature", sum(1 for r in form if r.get("premature_press") == "1"), "responded", len(press), "RTmed %.4f" % st.median([f(r, "RT") for r in press]))
print("press frames<=1", sum(1 for r in press if f(r, "stimulus_frames") <= 1))
print("maskpress", sum(1 for r in press if f(r, "T") <= f(r, "RT") <= f(r, "T") + 0.2 + 1e-9))
print("timeout", sum(1 for r in form if r.get("timeout") == "1"), "deadline", sum(1 for r in form if r.get("responded_by_deadline") == "1"))
tmin = min(f(r, "T") for r in form)
c33 = [r for r in press if abs(f(r, "T") - tmin) < 1e-9]
print("Tmin cell responded", len(c33), "RT<T", sum(1 for r in c33 if f(r, "RT") < f(r, "T")))
print("NA", len(npa), "corrNaN", sum(1 for r in npa if r["Correct"] in ("NaN", "nan")), "to1", sum(1 for r in npa if r.get("timeout") == "1"), "dl0", sum(1 for r in npa if r.get("responded_by_deadline") == "0"))
print("block", sorted(collections.Counter(r["block"] for r in form).items()))