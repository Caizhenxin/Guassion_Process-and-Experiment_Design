import re, pathlib
p = pathlib.Path(r"1_Code\DDM_Core\_scratch\_apply_d117_docs.py")
s = p.read_text(encoding="utf-8")
for name in ("DECISION", "DECISION_REASON", "DECISION_ARTIFACT", "PROGRESS", "CHANGELOG", "EVIDENCE", "README_ROW", "FIG_ROW"):
    m = re.search(rf"^{name} = \((.*?)\n\)\n", s, re.S)
    if not m:
        print(name, "not found"); continue
    body = m.group(1)
    print(name, body.count("|"))
