import pandas as pd, numpy as np
df=pd.read_csv(r"2_Data\Real_Data\EXP_data_combined.csv")
df["RT_sec"]=pd.to_numeric(df["RT_sec"],errors="coerce")
print("stages:",df["stage"].unique())
print("n subj:",df["SubjectUID"].nunique())
for g,d in df.groupby("groupID"):
    W=d["W"].iloc[0]; T=d["T"].iloc[0]
    r=d["RT_sec"].dropna()
    print(f"G{g} T={T} W={W} n={len(r)} RTmin={r.min():.3f} RTmax={r.max():.3f} mean={r.mean():.3f} "
          f"p90={r.quantile(.9):.3f} frac_ge_{W-0.01:.2f}={ (r>=W-0.01).mean():.3f} LOSS={ (d['RT_sec'].isna()).mean():.3f}")
