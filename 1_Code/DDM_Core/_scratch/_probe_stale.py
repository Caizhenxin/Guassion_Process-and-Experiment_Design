import json, math
d = json.loads(open(r"1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json", encoding="utf-8").read())
for r in d["compare"]:
    print(r["arm"], repr(r.get("A_best")), repr(r.get("B_at_A_best")),
          math.isfinite(float(r.get("A_best", float("nan")))), math.isfinite(float(r.get("B_at_A_best", float("nan")))))
