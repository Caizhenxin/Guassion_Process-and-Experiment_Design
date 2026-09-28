import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
np.random.seed(42)
kernel = 1.0*RBF(length_scale=1.0) + WhiteKernel(noise_level=1e-5)
gp_v = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
gp_a = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
X_train = np.random.uniform(-1,1,size=(50,3))
Y_v = np.sin(X_train[:,0])*0.5 + 0.1*np.random.randn(50)
Y_a = 1.5 + 0.3*np.cos(X_train[:,1]) + 0.05*np.random.randn(50)
gp_v.fit(X_train,Y_v); gp_a.fit(X_train,Y_a)
print("trained kernel v:", gp_v.kernel_)
print("trained kernel a:", gp_a.kernel_)
def norm(P,T,W): return ((P-75)/75.0,(T-305)/295.0,(W-850)/650.0)
print(f"{'cond':>18} {'X':>26} {'gp_v':>8} {'std_v':>8} {'gp_a':>8} {'std_a':>8}")
for (P,T,W) in [(0,30,300),(0,30,600),(120,30,600),(120,80,600),(8,100,1100),(120,500,1500),(120,30,800),(120,80,800)]:
    Pn,Tn,Wn = norm(P,T,W)
    X=np.array([[Pn,Tn,Wn]])
    mv,sv = gp_v.predict(X,return_std=True); ma,sa = gp_a.predict(X,return_std=True)
    print(f"P{P:>4}_T{T:>4}_W{W:>5}  ({Pn:6.2f},{Tn:6.2f},{Wn:6.2f})  {mv[0]:8.3f} {sv[0]:8.3f} {ma[0]:8.3f} {sa[0]:8.3f}")
