import pandas as pd, numpy as np
r=pd.read_csv(r"2_Data\Real_Data\UnExtact\raw\EXP_data_group4_1.csv")
print(list(r.columns)[:20]); print(r.head(3).to_string())
odd = (r.subjectID%2==1)
mm_odd=((r.Shape=="circle")&(r.Label=="self"))|((r.Shape=="square")&(r.Label=="stranger"))
mm=np.where(odd,mm_odd,~mm_odd)
f=(r.stage=="formal")
for lab,mask in [("Matching",mm&f),("NonMatching",(~mm)&f)]:
    s=r[mask]
    print(lab,"n",len(s),"Correct mean",round(pd.to_numeric(s.Correct,errors="coerce").mean(),4))
    print("  key x resp table:"); print(pd.crosstab(s.CorrectKey,s.Response).to_string())
    print("  by shape/label acc:"); print(s.assign(c=pd.to_numeric(s.Correct,errors="coerce")).groupby(["Shape","Label"])["c"].mean().round(3).to_dict())
