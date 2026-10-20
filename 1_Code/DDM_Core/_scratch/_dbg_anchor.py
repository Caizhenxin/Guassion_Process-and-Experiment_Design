# -*- coding: utf-8 -*-
import pathlib
L = pathlib.Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md").read_text(encoding="utf-8").split("\n")
target = [x for x in L if "make_sim_figures.py" in x]
print(len(target))
for x in target:
    print(repr(x[:80]))
mine = "`1_Code/Experiment/make_sim_figures.py`（**新建**，D105"
print("mine:", repr(mine))
for x in target:
    print("match?", x.startswith(mine))
