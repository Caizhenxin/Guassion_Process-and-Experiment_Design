# -*- coding: utf-8 -*-
"""把「check_full_session 通过 32」这类期望值同步到 34（D93 的 A15/B31 之后）。"""
import io
from pathlib import Path

M = Path("1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md")
S1 = Path("5_Reference/08_工作流/Stage1_技术验证记录.md")

m = io.open(M, encoding="utf-8").read()
assert m.count("== 通过 32 / 未通过 0 ==") == 1
m = m.replace("== 通过 32 / 未通过 0 ==", "== 通过 34 / 未通过 0 ==")
io.open(M, "w", encoding="utf-8", newline="\n").write(m)

s = io.open(S1, encoding="utf-8").read()
assert s.count("== 通过 32 / 未通过 0 ==") == 1
s = s.replace("== 通过 32 / 未通过 0 ==", "== 通过 34 / 未通过 0 ==")
old = "`check_full_session.py` 32/32（含 D92 的 A14/B30）"
assert s.count(old) == 1
s = s.replace(old, "`check_full_session.py` 34/34（含 D92 的 A14/B30、D93 的 A15/B31）")
io.open(S1, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
