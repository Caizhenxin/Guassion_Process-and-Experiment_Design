from pathlib import Path
p = Path(r"1_Code/DDM_Core/_scratch/_apply_d70.py")
t = p.read_text(encoding="utf-8")
old = "（3 人 × 96 试次、`n_x = 41`、"
new = "（3 人 × 96 试次、`n_x = 25`、"
print("count =", t.count(old))
if t.count(old) == 1:
    p.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
    print("✅ 已改")
