import json
from pathlib import Path

p = Path(r"2_Data\Real_Data\New_Design\_pipeline\stage8\stage8_results.json")
d = json.loads(p.read_text(encoding="utf-8"))
g1 = d["groups"]["1"]["M-T3"]["fit"]
print("fit keys:", list(g1))
for k, v in g1.items():
    if isinstance(v, list):
        print(f"\n{k} (len {len(v)}): head={[round(x,4) if isinstance(x,(int,float)) else x for x in v[:6]]}")
    elif isinstance(v, dict):
        print(f"\n{k}: dict keys={list(v)[:8]}")
        sub = v[list(v)[0]]
        print("   first:", str(sub)[:300])
    else:
        print(f"{k} = {v}")
