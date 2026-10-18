# -*- coding: utf-8 -*-
"""一手证据表是 **2 列**（`| 文件 | 说明 |`）；D93/D94 与 D95 两行只写了第 1 列。

`check_table_integrity.py` 的 `mangled_rows` 抓到这里：表头 3 个竖线、这两行 2 个。
"""
from pathlib import Path

p = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "工作流_主计划.md"
L = p.read_text(encoding="utf-8").split("\n")

FIXES = {
    "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.8 → **v4.9**":
        "**D93/D94**：组 1 练习段 0 试次（v4.9 改 `max(4, P)`）与 `qc_group.py` 去重",
    "`1_Code/Experiment/intake.py`（**新建**，D95":
        "**D95**：单场入库判定（技术层 + 结构层 + 一致层合成一条命令）",
}

for prefix, cell2 in FIXES.items():
    i = next(k for k, x in enumerate(L) if x.startswith("| " + prefix))
    row = L[i].rstrip()
    assert row.endswith("|"), row[-40:]
    body = row[:-1].rstrip()                      # 去掉收尾竖线
    assert body.count("|") == 1, f"第 {i + 1} 行已有 {body.count('|')} 个竖线"
    L[i] = f"{body} | {cell2} |"
    print(f"第 {i + 1} 行补齐第 2 列：{cell2[:40]}…")

p.write_text("\n".join(L), encoding="utf-8", newline="\n")
