# -*- coding: utf-8 -*-
"""design_search 输出按真值分开命名（csv 与 md 各一行，不在同一处）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\design_search.py")
s = p.read_text(encoding="utf-8")
pairs = [
    ('    csv = OUT / "design_search.csv"',
     '    tag = GROUP_TRUTH["name_label"]\n    csv = OUT / f"design_search_{tag}.csv"'),
    ('    md = OUT / "design_search.md"',
     '    md = OUT / f"design_search_{tag}.md"'),
    ("    5_Reference/03_论文写作/figures_sim/design_search.csv",
     "    5_Reference/03_论文写作/figures_sim/design_search_<truth>.csv"),
    ("    5_Reference/03_论文写作/figures_sim/design_search.md",
     "    5_Reference/03_论文写作/figures_sim/design_search_<truth>.md"),
]
for old, new in pairs:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("ok")
