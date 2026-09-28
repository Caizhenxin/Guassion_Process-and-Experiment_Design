import pandas as pd, numpy as np
d=pd.read_csv(r"2_Data\Real_Data\HDDM_Ready\hddm_data_group3_P120_T30_W600.csv")
print("G3 rows",len(d),"cols",list(d.columns))
print(d.groupby("identity")["response"].mean().round(4))
print("overall response==1 mean:",round(d.response.mean(),4))
print(d.head(5).to_string())
print("subj n:",d.subj_idx.nunique())
e=pd.read_csv(r"2_Data\Real_Data\HDDM_Ready\hddm_data_group8_P120_T80_W800.csv")
print("G8 response==1 mean:",round(e.response.mean(),4), "identity means",e.groupby("identity")["response"].mean().round(3).to_dict())
