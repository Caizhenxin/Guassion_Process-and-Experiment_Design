from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\power_recovery.py")
s = p.read_text(encoding="utf-8")
pairs = [
    ('ax.text(CHI2_1_95 * 1.03, 0.62, "χ²(1,.95)=3.84", fontsize=8)',
     'ax.text(CHI2_1_95 * 1.03, 0.28, "χ²(1,.95)=3.84", fontsize=8)'),
    ('ax.set_ylabel("（点＝一名被试，两行对齐）")', 'ax.set_ylabel("")'),
]
for old, new in pairs:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("patched fig13 layout")
