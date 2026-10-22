from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\spe_families.py")
s = p.read_text(encoding="utf-8")
old = '    ax.set_xlim(0.03, 0.21)'
new = ('    ax.set_xlim(0.02, 0.22)\n'
       '    ax.margins(y=0.18)')
assert s.count(old) == 1
p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
print("patched margins")
