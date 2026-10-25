import json
from pathlib import Path

p = Path(r"2_Data\Real_Data\New_Design\_pipeline\stage8\stage8_results.json")
d = json.loads(p.read_text(encoding="utf-8"))
g = d["groups"]
print("groups type:", type(g).__name__)
if isinstance(g, dict):
    k0 = list(g)[0]
    print("group key:", k0, "| keys:", list(g[k0]))
    m = g[k0]["models"] if "models" in g[k0] else g[k0]
    print("models:", list(m))
    kk = list(m)[0]
    print("model keys:", list(m[kk]))
    for k2 in list(m[kk]):
        v = m[kk][k2]
        print(f"  {k2}: {type(v).__name__}" + (f" len={len(v)}" if hasattr(v, '__len__') else f" = {v}"))
