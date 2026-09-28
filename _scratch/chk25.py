import pandas as pd, glob, numpy as np
for f in sorted(glob.glob("2_Data/Generate_Data/**/*v2.5*.csv", recursive=True)) + sorted(glob.glob("2_Data/Generate_Data/*.csv")):
    try: d=pd.read_csv(f)
    except Exception as e: print(f,"ERR"); continue
    gpcols=[c for c in d.columns if "gp" in c]
    print("-"*60); print(f,"rows",len(d))
    if gpcols: print("  gp cols:", {c:(round(d[c].mean(),4) if np.issubdtype(d[c].dtype,np.number) else d[c].iloc[0], int(d[c].nunique()) if np.issubdtype(d[c].dtype,np.number) else '-') for c in gpcols})
