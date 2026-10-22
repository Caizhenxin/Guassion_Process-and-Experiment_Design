"""把 scan_min_n 的默认输出根改到 2_Data/Generate_Data/_synth_datasets/_SYNTHETIC_SCAN。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\scan_min_n.py")
s = p.read_text(encoding="utf-8")
old = 'ROOT / "2_Data" / "Real_Data" / "_SYNTHETIC_SCAN"'
new = 'ROOT / "2_Data" / "Generate_Data" / "_synth_datasets" / "_SYNTHETIC_SCAN"'
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("ok:", new)
