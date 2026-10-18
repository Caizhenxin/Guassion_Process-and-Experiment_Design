# -*- coding: utf-8 -*-
"""D93：B17 由「组1 无练习」改为「练习行数 = max(4,P) 且 stage 两段齐」。"""
from pathlib import Path

F = Path("1_Code/Experiment/exp_matlab/test/run_full_session.m")
src = F.read_text(encoding="utf-8")

old = (
    "    if P_groups(groupID) > 0\n"
    "        C{end+1} = {'B17 stage 同时出现 practice 与 formal', ...\n"
    "                    any(string(T.stage) == \"practice\") && any(string(T.stage) == \"formal\")};\n"
    "    else\n"
    "        C{end+1} = {'B17 组1 只有 formal（无练习）', all(string(T.stage) == \"formal\")};\n"
    "    end\n"
)
new = (
    "    % ★ D93：所有组都有练习段（P=0 走 4 试次兜底）⇒ practice 行数必须恰为 max(4,P)\n"
    "    nPracRows = sum(string(T.stage) == \"practice\");\n"
    "    C{end+1} = {sprintf('B17 练习行数 = max(4,P) = %d（实测 %d）且 stage 两段齐', nPracExpected, nPracRows), ...\n"
    "                nPracRows == nPracExpected && any(string(T.stage) == \"formal\")};\n"
)
assert src.count(old) == 1
src = src.replace(old, new)
F.write_text(src, encoding="utf-8", newline="\n")
print(f"run_full_session.m：{len(src.splitlines())} 行（B17 改口径）")
