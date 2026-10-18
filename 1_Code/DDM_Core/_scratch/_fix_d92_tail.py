# -*- coding: utf-8 -*-
"""D92 收尾两处：

1) 主计划：把追加的 D92 产出文件行接到上一行表格（原来中间留了一个空行 ⇒ split_rows=1）。
2) check_traceability.py：D 行正则不容忍列宽填充（`| D1           |`、`| **D9**  |`、`| ~~D21~~      |`），
   误报「D 编号缺 [1,2,3,4,9,21]」——第三次被表格对齐空格坑到，改为允许任意空白。

两处都幂等。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ---- 1) 主计划：接上表格 ----
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
lines = PLAN.read_text(encoding="utf-8").split("\n")
i = next(k for k, ln in enumerate(lines)
         if ln.startswith("| `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.7 →"))
assert lines[i - 1].strip() == "", f"上一行不是空行：{lines[i-1]!r}"
del lines[i - 1]
PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(f"主计划：断开处已接上，现 {len(lines)} 行")

# ---- 2) 检查器：正则容忍填充空格 ----
F = ROOT / "1_Code/DDM_Core/_scratch/check_traceability.py"
src = F.read_text(encoding="utf-8")
OLD = 'D_ROW_RE = re.compile(r"^\\| (?:\\*\\*|~~)?D(\\d+)(?:\\*\\*|~~)? \\|")'
NEW = ('D_ROW_RE = re.compile(r"^\\|\\s*(?:\\*\\*|~~)?D(\\d+)(?:\\*\\*|~~)?\\s*\\|")\n'
       '# ↑ D92：表格是按列宽填充过的（`| D1           |`、`| **D9**  |`、`| ~~D21~~      |`），\n'
       '#   要求「单个空格」会把 D1–D4 / D9 / D21 整行漏掉 ⇒ 误报编号不连续。允许任意空白。')
n = src.count(OLD)
assert n == 1, f"正则命中 {n} 次"
F.write_text(src.replace(OLD, NEW), encoding="utf-8", newline="\n")
print("check_traceability.py：D_ROW_RE 已放宽")
