import numpy as np
def k_P(P,kmin=0.1,kmax=0.05,g=0.2,P0=32): return kmin+(kmax-kmin)/(1+np.exp(-g*(P-P0)))
def v_P(P,P1=4,kmin=0.1,kmax=0.05,g=0.2,P0=32): return 1/(1+np.exp(-k_P(P,kmin,kmax,g,P0)*(P-P1)))
def v_P_alt(P,P1=4,kmin=0.01,kmax=0.15,g=0.1,P0=32): return 1/(1+np.exp(-(kmin+(kmax-kmin)/(1+np.exp(-g*(P-P0))))*(P-P1)))
print("=== v_P direction (code as-is: k_min=0.1 -> k_max=0.05) ===")
for P in [0,4,8,32,60,120]: print(f"  P={P:>4}  k={k_P(P):.4f}  v_P={v_P(P):.4f}")
print("=== v_P with k_min=0.01 -> k_max=0.15 (hypothesis direction) ===")
for P in [0,4,8,32,60,120]: print(f"  P={P:>4}  v_P={v_P_alt(P):.4f}")
print()
conds=[(0,30,300),(0,30,600),(120,30,600),(120,80,600),(8,100,1100),(120,500,1500),(120,30,800),(120,80,800)]
a1,a2=1.5,-0.4
print(f"{'cond':>18} {'M':>5} {'v_T':>6} {'v_P':>6} {'v_self':>8} {'v_str':>8} {'a0':>7} {'a(>600)':>8}")
for (P,T,W) in conds:
    M=T+W; v_T=1/(1+np.exp(-0.01*(T-100))); vp=v_P(P)
    vs=v_T*vp*3*(1+a1); vg=v_T*vp*3*(1+a2)
    a0=1/(1+np.exp(-0.01*(M-600)))*3
    a=a0*(1.2 if M>600 else 1.0)
    print(f"P{P:>4}_T{T:>4}_W{W:>5} {M:>5} {v_T:6.3f} {vp:6.3f} {vs:8.3f} {vg:8.3f} {a0:7.3f} {a:8.3f}")
print()
print("=== SPE from v alone (RT ~ a/(2v), SPE_ms = RT_self - RT_stranger) ===")
print(f"{'cond':>18} {'SPE_ms':>9}   observed(C)")
obs={(0,30,300):None,(0,30,600):None,(120,30,600):0.0,(120,80,600):21.6,(8,100,1100):-62.5,(120,500,1500):-67.8,(120,30,800):-14.4,(120,80,800):-11.1}
for (P,T,W) in conds:
    M=T+W; v_T=1/(1+np.exp(-0.01*(T-100))); vp=v_P(P)
    vs=v_T*vp*3*2.5; vg=v_T*vp*3*0.6
    a0=1/(1+np.exp(-0.01*(M-600)))*3; a=a0*(1.2 if M>600 else 1.0)
    rt_s=a/(2*abs(vs)); rt_g=a/(2*abs(vg))
    print(f"P{P:>4}_T{T:>4}_W{W:>5} {(rt_s-rt_g)*1000:9.1f}   obs={obs[(P,T,W)]}")
