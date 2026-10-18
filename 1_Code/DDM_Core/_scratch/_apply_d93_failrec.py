# -*- coding: utf-8 -*-
"""失败记录：给「append 追加写重复行」这条同根因追加第 N 次触发记录；更新 INDEX。"""
import io
from pathlib import Path

BASE = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement")
REC = BASE / "2026-10-18_Stage1验收检查器判据只在60Hz成立.md"
IDX = BASE / "INDEX.md"

ADD = """
## 再次触发记录（2026-10-18，第五次同根因：D94 的 `qc_group.py`）

- **触发场景**：首场真实数据的 txt 是 **1152 行 = 576 × 2**，每个 `trialID` 恰出现 2 次，
  CSV 只等于最后一次（`fopen(..., 'a+')` 追加写留下的第二遍）。
  `qc_group.py` 首轮报 **G2「正式段 576 试次：1 名不符」** 与 **G4「每 (T,W) 格 48 试次：有被试不符」**
  两条红——都是假红。
- **新发现的原因**：这次的误判出现在**质控工具**里，而不在验收检查器里。
  同一条教训（读 txt 必须先按 `(stage, trialID)` 去重）此前只在 `check_stage1_acceptance.py::dedupe`
  里落实过；`qc_group.py` 是后来新写的工具，复制了「读行」却没复制「去重」。
- **是否换方案**：是。`qc_group.py::subject_metrics` 建 `seen[(stage, trialID)] = r`、保留最后一次、
  `rec["n_dropped"]` 进汇总、表里加「去重行」列。复跑：G2/G4/G5/G7 转 PASS；
  **G3 仍红**（该场确实是 v4.8 产物、练习段 0 行 ⇒ 真红，见 D93）、G6 FAIL（被试本人）。
- **仍然有效的教训（升级为结构教训）**：**同一个「读产物」的动作被复制成了多个工具，
  修复就必须逐个工具做，而不是修一处就算完。** 判据侧要有「去重多少次」的显式计数，
  否则「去重」会掩盖「真的少了行」——所以去重只能消除假红，不能放宽判据。
"""

t = io.open(REC, encoding="utf-8").read()
assert "qc_group.py" not in t, "该记录已追加过 qc_group 触发记录"
io.open(REC, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + ADD)
print("record updated, lines =", len(t.splitlines()) + len(ADD.splitlines()))

ROW = (
    "| 2026-10-18 | 程序在 P=0 组把练习段整段跳过：设计写「4 个兜底」，代码算成 0 "
    "| `#练习段` `#max(4,P)` `#空循环` `#判据把bug写成预期` `#量纲混淆` `#Stage6` `#MATLAB` `#Psychtoolbox` "
    "| [2026-10-18_程序跳过组1的练习段导致被试未走通流程.md](./2026-10-18_程序跳过组1的练习段导致被试未走通流程.md) |"
)

idx = io.open(IDX, encoding="utf-8").read()
idx = idx.replace("\n\n| 2026-10-18 | 程序把自己带的资源交给", "\n| 2026-10-18 | 程序把自己带的资源交给")
anchor = "| 2026-10-18 | 程序把自己带的资源交给"
assert idx.count(anchor) == 1
idx = idx.replace(anchor, ROW + "\n" + anchor)
io.open(IDX, "w", encoding="utf-8", newline="\n").write(idx)
rows = [ln for ln in idx.splitlines() if ln.startswith("| 20")]
print("INDEX rows =", len(rows))
