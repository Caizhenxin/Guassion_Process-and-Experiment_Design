import sys, os, numpy as np
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "_scratch"))
import cellmean as cm
from mapping import trial_params
from simulate import build_design, design_arrays, simulate_subject
import check_cellmean as C

design = build_design(C.P_FIXED, C.T_LEVELS, C.W_LEVELS, C.N_REP)
rng = np.random.default_rng(12345)
sim = simulate_subject(design, C.TRUTH_LIN, rng)
from likelihood import trials_from_arrays
tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *design_arrays(design))

p = C.TRUTH_LIN
cp = C.cell_from_lin(p)
tp = trial_params(tr, p)
tc = cm.trial_params_cell(tr, cp)
for k in ("v","a","z","d"):
    dv = np.abs(tp[k]-tc[k]); j = int(np.argmax(dv))
    print(f"{k:3s} max|diff| = {dv.max():.3e} at {j}  lin={tp[k][j]:.6f} cell={tc[k][j]:.6f}")
print("t0", tp["t0"], tc["t0"])
ki, ji = cm._indices(tr)
print("ki counts:", np.unique(ki, return_counts=True))
print("ji counts:", np.unique(ji, return_counts=True))
print("d_ref,dt,st:", cp.d_ref, cp.dt_1, cp.dt_2, cp.dt_3, "|", cp.st_1, cp.st_2, cp.st_3)
