import sys, numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "../Experiment")
import likelihood as L, read_formal_data as R
from mapping import trial_params
from wfpt import flux
rec, _ = R.load_file("_scratch/_fake_v41/exp_group1_subject1.txt")
tr, rep = R.fit_ready(R.to_trials(rec))
resp = tr["omission"] == 0
rts = tr["rt"][resp]
print("kept responded: n=%d  min=%.4f  next few=%s" % (
    rts.size, rts.min(), np.sort(rts)[:6].round(4)))
for t0 in (0.23, 0.236, 0.2371):
    p = L.MappingParams(shape_model="lin", t0=t0)
    tp = trial_params(tr, p)
    t = tr["rt"][resp] - t0
    a_r, z_r, v_r = tp["a"][resp], tp["z"][resp], tp["v"][resp]
    side = tr["side"][resp]
    d = np.where(side == 1, a_r - z_r, z_r)
    vv = np.where(side == 1, v_r, -v_r)
    f = flux(d, vv, a_r, t)
    bad = (t <= 0) | ~np.isfinite(f) | (f <= 0)
    idx = np.where(bad)[0]
    print("\nt0=%.4f  bad=%d" % (t0, idx.size))
    for i in idx[:4]:
        j = np.where(resp)[0][i]
        print("   trial#%d  rt=%.4f  t=%.6f  f=%.6g  T=%.4f W=%.4f side=%d" % (
            j, tr["rt"][j], t[i], f[i], tr["T"][j], tr["W"][j], side[i]))
    print("   min f over good = %.6g" % (f[~bad].min() if (~bad).any() else float("nan")))
