from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Generate_Data\README.md")
s = P.read_text(encoding="utf-8")
old = "每支关键参数的 `|dSPE/dθ|` 与 `SE@40 人/组`"
new = "每支关键参数的 `dSPE/dθ`（取绝对值）与 `SE@40 人/组`"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
P.write_text(s, encoding="utf-8", newline="\n")
print("fixed table cell")
