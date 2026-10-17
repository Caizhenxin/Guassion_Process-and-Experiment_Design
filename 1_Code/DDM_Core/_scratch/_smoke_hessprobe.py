import sys, time
sys.path.insert(0, r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core")
sys.path.insert(0, r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\_scratch")
import _probe_hess_scaling as P
t=time.perf_counter()
r = P.fit_group(2, ddm=True, rho_free=True)
print("A ddm n=2 ok", round(time.perf_counter()-t,1), "s"); print(" ", P.line("A", r))
t=time.perf_counter()
r2 = P.fit_group(2, ddm=False, rho_free=True, seed=7)
print("B nonddm n=2 ok", round(time.perf_counter()-t,1), "s"); print(" ", P.line("B", r2))
