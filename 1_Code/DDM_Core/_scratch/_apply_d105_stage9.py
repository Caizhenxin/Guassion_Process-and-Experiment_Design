# -*- coding: utf-8 -*-
"""D105 落纸（续 2）：Stage9 方案补两行——按锚点行的实际列数自适应构造新行。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\Stage9_设计空间优化与论文整合方案.md")
lines = p.read_text(encoding="utf-8").split("\n")

TOOL_CELLS = [
    "`1_Code/Experiment/make_sim_figures.py`",
    "论文级模拟图：CRLB（10% 精度所需组人数）、P 方案 oracle 识别力、试次级生成数据",
    "✅ **已建**（462 行、裸 LF）。证据：三图 + `figures_index.md` + 4 份 CSV/JSON 全部生成"
    "（`python -X utf8 1_Code/Experiment/make_sim_figures.py` 退出 0）；数字见主计划 D105",
]
LOG_CELLS = [
    "2026-10-18",
    "**论文级模拟图落成（决策 D105）**：`make_sim_figures.py` 出 CRLB（`d_ref` 3 / `beta_T` 41 / "
    "`beta_ST` 2248 人才到 10%）、P 方案 oracle（40 人/组稳、20 人/组下限）、试次生成图；"
    "顺带修 `oracle_power.py` 与 `fit_between` 三元组不符的 bug",
]

idx = [i for i, ln in enumerate(lines) if ln.startswith("| `1_Code/AutoRA_SPE/check_stage9_inner.py`")]
assert len(idx) == 1, len(idx)
nc = lines[idx[0]].count("|") - 1
print("工具链锚点行：", nc, "列")
row = "| " + " | ".join(TOOL_CELLS[:nc] if nc <= len(TOOL_CELLS) else
                        TOOL_CELLS + [""] * (nc - len(TOOL_CELLS))) + " |"
lines.insert(idx[0] + 1, row)

last = max(i for i, ln in enumerate(lines) if ln.startswith("| 2026-"))
nc2 = lines[last].count("|") - 1
print("日志锚点行：", nc2, "列")
row2 = "| " + " | ".join(LOG_CELLS[:nc2] if nc2 <= len(LOG_CELLS) else
                         LOG_CELLS + [""] * (nc2 - len(LOG_CELLS))) + " |"
lines.insert(last + 1, row2)

p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("Stage9 →", len(lines), "行")
