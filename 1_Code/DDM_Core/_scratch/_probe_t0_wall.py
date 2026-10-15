import sys, numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "../Experiment")
import likelihood as L, read_formal_data as R
rec, _ = R.load_file("_scratch/_fake_v41/exp_group1_subject1.txt")
tr, rep = R.fit_ready(R.to_trials(rec))
minrt = float(np.nanmin(tr["rt"]))
print("min RT kept = %.4f s | dropped %d" % (minrt, rep["n_dropped"]))
print("%-8s %-10s %s" % ("t0", "loglik", "per_trial"))
for t0 in (0.10, 0.20, 0.22, 0.23, 0.2360, 0.2371, 0.25, 0.30, 0.60):
    p = L.MappingParams(shape_model="lin", t0=t0)
    ll = L.per_trial_loglik(p, tr)
    tot = L.log_likelihood(p, tr)
    print("%-8.4f %-10s %s" % (t0, ("%.2f" % tot) if np.isfinite(tot) else "None/-inf",
          "finite" if ll is not None else "None"))
