import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\_scratch")
import check_hier as C
C.case_c()
print("N_FAIL =", C.N_FAIL)
