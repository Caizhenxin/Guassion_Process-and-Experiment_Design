# -*- coding: utf-8 -*-
"""修 Stage9 里我插入的两行：去掉多余的尾格，保持 3 列 / 2 列。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\Stage9_设计空间优化与论文整合方案.md")
lines = p.read_text(encoding="utf-8").split("\n")

TOOL = ("| `1_Code/Experiment/make_sim_figures.py` | 论文级模拟图：CRLB（10% 精度所需组人数）、"
        "P 方案 oracle 识别力、试次级生成数据 | ✅ **已建**（462 行、裸 LF）。证据：三图 + `figures_index.md` + "
        "4 份 CSV/JSON 全部生成（`python -X utf8 1_Code/Experiment/make_sim_figures.py` 退出 0）；"
        "数字见主计划 D105 |")
LOG = ("| 2026-10-18 | **论文级模拟图落成（决策 D105）**：`make_sim_figures.py` 出 CRLB（`d_ref` 3 / "
       "`beta_T` 41 / `beta_ST` 2248 人才到 10%）、P 方案 oracle（40 人/组稳、20 人/组下限）、试次生成图；"
       "顺带修 `oracle_power.py` 与 `fit_between` 三元组不符的 bug | "
       "`1_Code/Experiment/make_sim_figures.py`（462 行）+ `5_Reference/03_论文写作/figures_sim/`（三图 + "
       "`figures_index.md` + 4 份 CSV/JSON） |")

n = 0
for i, ln in enumerate(lines):
    if ln.startswith("| `1_Code/Experiment/make_sim_figures.py`"):
        lines[i] = TOOL
        n += 1
    elif ln.startswith("| 2026-10-18 | **论文级模拟图落成（决策 D105）**"):
        lines[i] = LOG
        n += 1
assert n == 2, n
p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("fixed rows:", n)
