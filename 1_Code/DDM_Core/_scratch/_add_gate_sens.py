from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\spe_families.py")
s = p.read_text(encoding="utf-8")
old = 'for fam in ("ceiling", "selfsat", "power", "ratio", "gate", "noise"):'
new = ('for fam in ("ceiling", "selfsat", "power", "ratio", "gate", '
       '"gate_drift", "noise"):')
assert s.count(old) == 1, s.count(old)
p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
print("patched")
