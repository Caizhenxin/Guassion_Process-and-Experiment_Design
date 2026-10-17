import json, pathlib
p = pathlib.Path(r"1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("bytes", p.stat().st_size)
for k in ("n_evals", "seconds", "settings", "front_scope", "d54"):
    print(k, "=", d[k])
print("anchor =", d["anchor"])
print("best =", {k: v for k, v in d["best"].items() if k in ("name","A","B","J","omission","n_fim")})
print("pareto n =", len(d["pareto"]))
print("compare =", [{k: r[k] for k in ("arm","A_best","B_at_A_best","n_feasible","best_J")} for r in d["compare"]])
print("noise keys =", sorted(d["noise"].keys()))
h = d["histories"]["random"]
print("hist keys =", sorted(h.keys()))
