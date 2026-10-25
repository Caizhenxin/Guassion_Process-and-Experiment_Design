import json
from pathlib import Path

p = Path(r"2_Data\Real_Data\New_Design\_pipeline\stage8\stage8_group_1.json")
d = json.loads(p.read_text(encoding="utf-8"))
m = d["results"]["M-T3"]
print("M-T3 keys:", list(m))
for k in list(m):
    v = m[k]
    if isinstance(v, list):
        print(f"{k}: list len={len(v)}, type0={type(v[0]).__name__}")
        if v and isinstance(v[0], dict):
            print("   keys0:", list(v[0]))
            print("   sample:", {kk: (round(vv,4) if isinstance(vv,(int,float)) else vv) for kk, vv in v[0].items() if not isinstance(vv,(list, dict))})
    elif isinstance(v, dict):
        print(f"{k}: dict keys={list(v)[:12]}")
