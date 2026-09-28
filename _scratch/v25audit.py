import pandas as pd, numpy as np
d=pd.read_csv("2_Data/Generate_Data/Generate_Data_v2.5/gp_ddm_v2.5_2000.csv")
print("cols:",list(d.columns))
g=d[d.is_valid==1] if "is_valid" in d.columns else d
print("\n<<< by label >>>")
for lab,s in d.groupby("Label"):
    print(f"{lab:>9}: v_mean={s['v'].mean():7.3f}  a_mean={s['a'].mean():6.3f}  z_mean={s['z'].mean():6.3f}  t0={s['t0'].mean():.3f}  RT_mean={s['RT'].mean():.3f}  valid={s['is_valid'].mean():.3f}")
print("\nv_self - v_stranger =", round(d[d.Label=='self']['v'].mean()-d[d.Label=='stranger']['v'].mean(),3))
print("a_self - a_stranger  =", round(d[d.Label=='self']['a'].mean()-d[d.Label=='stranger']['a'].mean(),3))
print("z_self - z_stranger  =", round(d[d.Label=='self']['z'].mean()-d[d.Label=='stranger']['z'].mean(),3))
print("\n<<< per-subject SPE (RT) >>>")
se=d[d.Label=='self'].groupby('subjectID')['RT'].mean(); st=d[d.Label=='stranger'].groupby('subjectID')['RT'].mean()
print("mean SPE_RT ms =", round((se-st).mean()*1000,1), " sd =", round((se-st).std()*1000,1))
print("\n<<< parameter ranges >>>")
print(d[['v','a','z','t0','RT']].describe().round(3).to_string())
print("\nfrac response==1 (upper):", round((d.response==1).mean(),3), " ==0:", round((d.response==0).mean(),3))
print("z > a count:", int((d.z>d.a).sum()), " z/a mean:", round((d.z/d.a).mean(),3))
