# -*- coding: utf-8 -*-
"""收尾：证据表是 2 列；进度表里旧报告名改成按真值拆分的名字。"""
from pathlib import Path

MP = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design/5_Reference/08_工作流/工作流_主计划.md")
s = MP.read_text(encoding="utf-8")
L = s.split("\n")
for i, x in enumerate(L):
    if x.startswith("| `1_Code/Experiment/design_search.py`（**新建**，D107"):
        L[i] = ("| `1_Code/Experiment/design_search.py`（**新建**，D107，323 行）+ "
                "`5_Reference/03_论文写作/figures_sim/design_search_design.md`/`.csv` + "
                "`design_search_oracle.md`/`.csv`（两张表：组层真值 design / oracle） "
                "| ③ 设计空间第一轮：7 种被试内设计 × 6 种 P 方案，判据 `beta_T` 10% / `beta_P` 0.30 / `tau_P` 0.50；"
                "**oracle 口径 39–40 人/组**（`4T×4W r9` 最优）；**design 口径现行方案「被试层漂移不可识别」**、"
                "改 5 水平后 37 人/组；已暴露「P≤32 漂移被 `max(0,·)` 截到 0 ⇒ 只剩 2 个有效水平」 |")
        print("row", i + 1)
s = "\n".join(L).replace("报告 `figures_sim/design_search.md`",
                         "报告 `figures_sim/design_search_design.md` 与 `design_search_oracle.md`")
MP.write_text(s, encoding="utf-8", newline="\n")
print("ok")
