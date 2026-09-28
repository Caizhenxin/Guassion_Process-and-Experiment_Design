import pandas as pd, numpy as np, glob
for pat in ["2_Data/Generate_Data/**/gp_ddm_v2.4.5*.csv","2_Data/Generate_Data/**/gp_ddm_v2.5*.csv","2_Data/Generate_Data/**/gp_ddm_v2.4*.csv"]:
    for f in glob.glob(pat, recursive=True):
        try: d=pd.read_csv(f)
        except Exception as e: print(f,"ERR",e); continue
        cols=[c for c in ["v_s2","v_gp_raw","a_gp_raw","v_mix","a_mix","v","a","omission","RT","label"] if c in d.columns]
        print("="*70); print(f, "rows",len(d), "cols",len(d.columns))
        key = "label" if "label" in d.columns else None
        show=[c for c in cols if c not in ("RT",)]
        g = d.groupby([c for c in ["P","T","W"] if c in d.columns]).agg({c:["mean","std","nunique"] for c in ["v_gp_raw","a_gp_raw","v_s2","a_s2"] if c in d.columns})
        print(g.round(4).to_string())
        if "omission" in d.columns: print("omission mean:",round(d["omission"].mean(),4))
