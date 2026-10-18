# -*- coding: utf-8 -*-
"""D93（组 1 练习段 4 试次兜底 / v4.9）+ D94（qc_group 去重）落纸。

改动面：
  1. 5_Reference/08_工作流/工作流_主计划.md  —— 决策行 D93/D94、进度行、变更日志行、产出文件行
  2. 1_Code/DDM_Core/README.md               —— §8.64 / §8.65 + §9 第 77/78 项
  3. 1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md —— v2.8（练习段口径）
  4. 5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md —— 手册行 v2.8
  5. 1_Code/Experiment/exp_matlab/PTB免费版配置说明.md —— 程序 v4.9 / 手册 v2.8
每处都断言「旧文存在且只出现一次」，避免静默错改。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
MANUAL = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "主试培训手册_Exp_Design_Formal.md"
STAGE7 = ROOT / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md"
PTBDOC = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "PTB免费版配置说明.md"

problems: list[str] = []


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def sub_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        problems.append(f"{label}: 期望命中 1 次，实际 {n} 次")
        return text
    return text.replace(old, new)


def insert_after_line(text: str, anchor: str, addition: str, label: str) -> str:
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        problems.append(f"{label}: 锚点命中 {len(hits)} 行（应为 1）")
        return text
    lines.insert(hits[0] + 1, addition)
    return "\n".join(lines)


# ---------------------------------------------------------------- 1. 主计划

D93_ROW = (
    "| **D93** | 2026-10-18 | ❗ **首场真实数据把「组 1 练习段 0 试次」抓出来：程序升 v4.9**。"
    "① 触发：用户交回 v4.8 的 `EXP_data_group1_1.csv` + `exp_group1_subject1.txt`（组 1、P=0、576 行正式），"
    "`qc_group.py` 报 **G3 WARN：练习段 0 试次 ≠ 应收 4**；"
    "② 设计口径：`Stage6_Pilot方案.md:40` 写明「P=0 走 `n_practice = 4` 的兜底」，"
    "`qc_group.py:232` 用 `p_expect if p_expect else 4` ⇒ **组 1 也应有 4 个练习试次**；"
    "③ 程序实际：`Exp_Design_Formal.m` 原 `:584 loopCount = P / 4;`、`:587 for k = 1:loopCount` ⇒ "
    "P=0 时整段练习被跳过，被试没看过一次完整流程就进正式；"
    "④ 修法（v4.9）：`:594 nPractice = max(4, P);`、`:595 loopCount = nPractice / 4;`；"
    "`P` 变量与 CSV 第 8 列**都不改**（仍 0/8/32/120），练习行数为 **4/8/32/120**；"
    "⑤ 断言：`test/run_full_session.m:36 nPracExpected = max(4, P_groups(groupID));`、"
    "`:37 nExpected = nPracExpected + 3 * 192;`，B17 由「组 1 只有 formal」改为 `nPracRows == nPracExpected`；"
    "`check_full_session.py` 补 **A15**（`nPractice = max(4, P);` 存在、`loopCount = P / 4;` 消失、v4.9 头注）+ "
    "**B31** ⇒ **34/34**；"
    "⑥ 冒烟：组 1 修前 26/27（B17 旧判据红）⇒ 修后组 1、组 2 各 **27/27**（2.5 s / 2.5 s）；"
    "⑦ 口径更正：此前口头说的「练习 4/12/36/124」是错的，设计是 **max(4, P) = 4/8/32/120**。 |"
)

D94_ROW = (
    "| **D94** | 2026-10-18 | ✅ **工具自己也会误伤：`qc_group.py` 的 G2/G4 把「被试把整场跑了两遍」判成「试次数不符」**。"
    "① 触发：同一场的 txt **1152 行 = 576 × 2**，每个 `trialID` 恰出现 2 次，CSV 只等于最后一次"
    "（`fopen(..., 'a+')` 追加写留下的）；`qc_group.py` 首轮因此报 G2「正式段 576 试次：1 名不符」+ "
    "G4「每 (T,W) 格 48 试次：有被试不符」；"
    "② 与 D81b / D85 同根因（**第五次触发**）：读 txt 时没去重；"
    "③ 修法：`qc_group.py::subject_metrics` 在 `rows = ap.row_dicts(...)` 后按 `(stage, trialID)` 建 `seen`、"
    "保留最后一次、`rec[\"n_dropped\"]`、汇总表加「去重行」列（与 `check_stage1_acceptance.py::dedupe` 同口径）；"
    "④ 复跑：G2 PASS、G4 PASS、G5 PASS（18.8%）、G7 PASS（0.43%）；**G3 仍 WARN**（该场确实是 v4.8 产物、"
    "0 行练习 ⇒ 真红，正是 D93）；**G6 FAIL** 正确率 0.440 < 0.55（被试本人）；"
    "⑤ 边界：去重只解决「同 trialID 多行」；「一次运行内确实少行」仍会红。 |"
)

D93_PROGRESS = (
    "| 2026-10-18 | **6（首场真实数据回归）** | 用户交回 v4.8 组 1 被试 1 的一场：四条链路全通、"
    "S6-1/S6-5 红（被试本人，正确率 0.440 = 87 份历史最低 2%）；同时抓出「组 1 练习段 0 试次」（D93，v4.9）"
    "与「qc 把跑两遍判成试次不符」（D94）。本场**不计入 Pilot N**。 |"
)

D93_CHANGELOG = (
    "| 2026-10-18 | **新增 D93（组 1 练习段 0 试次）**：`Exp_Design_Formal.m` v4.8 → **v4.9**"
    "（`nPractice = max(4, P);`、`loopCount = nPractice / 4;`，1494 行）+ `test/run_full_session.m`"
    "（`nPracExpected`、B17 新判据、B1/B11 文案）+ `test/check_full_session.py`（+A15/B31，**34/34**）；"
    "冒烟组 1、组 2 各 **27/27**。 |"
)

D94_CHANGELOG = (
    "| 2026-10-18 | **新增 D94（QC 去重）**：`qc_group.py` 466 行，按 `(stage, trialID)` 去重并报「去重行」；"
    "复跑 G2/G4/G5/G7 转 PASS，G3 仍 WARN（真红，见 D93）、G6 FAIL（被试本身）；"
    "首场真实数据实测 RT 中位 0.670 s / 正确率 0.440 / 漏答 18.8% 已在 `analyze_rt_baseline.py` 的 87 份历史里定分位。 |"
)

D93_FILES = (
    "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.8 → **v4.9**，1494 行）+ "
    "`test/run_full_session.m`（188 行，`nPracExpected`/B17）+ `test/check_full_session.py`（**34/34**，+A15/B31）"
    "+ `1_Code/Experiment/exp_Check/qc_group.py`（**466 行**，D94 去重）+ "
    "`1_Code/DDM_Core/_scratch/_apply_d93_practice_floor.py` / `_apply_d93_driver.py` / `_apply_d93_b17.py` / "
    "`_apply_d94_qc_dedupe.py`（**新建**）"
)

plan = read(PLAN)
plan = insert_after_line(plan, "| **D92** |", D93_ROW, "主计划 D93 行")
plan = insert_after_line(plan, "| **D93** |", D94_ROW, "主计划 D94 行")
plan = insert_after_line(plan, "路径可移植）** |", D93_PROGRESS, "主计划 进度行")
plan = insert_after_line(plan, "**新增 D92（路径可移植）**", D93_CHANGELOG, "主计划 变更日志 D93")
plan = insert_after_line(plan, "**新增 D93（组 1 练习段 0 试次）**", D94_CHANGELOG, "主计划 变更日志 D94")
lines = plan.split("\n")
last_row = max(i for i, ln in enumerate(lines) if "（v4.7 → **v4.8**" in ln)
lines.insert(last_row + 1, D93_FILES)
plan = "\n".join(lines)

# ---------------------------------------------------------------- 2. README

SEC_864 = """### 8.64 组 1 的「练习段 0 试次」：设计说 4、程序做了 0（2026-10-18，D93）

**现象**：首场真实数据（组 1、P=0、576 行正式）进 `qc_group.py`，G3 报
「练习段 0 试次 ≠ 应收 4」。其余 8 条判据里 G2/G4 另因「跑了两遍」假红（见 §8.65）。

**谁对谁错**：设计文档与 QC 工具都写「P=0 走 4 个兜底练习」
（`Stage6_Pilot方案.md:40`、`qc_group.py:232` 的 `p_expect if p_expect else 4`），
所以**程序错了**：`Exp_Design_Formal.m` 原 `:584 loopCount = P / 4;`、`:587 for k = 1:loopCount`
⇒ P=0 时 `loopCount = 0`，练习整段被跳过，被试从没看过一次完整流程（含反馈）就进正式。

**修法（v4.9）**：`:594 nPractice = max(4, P);`、`:595 loopCount = nPractice / 4;`。
`P` 变量本身与 CSV 第 8 列都不改（组 1 仍写 0）——它是**组参数**，不是练习行数；
练习行数恒为 `max(4, P)` = 4/8/32/120。

**牙齿**：
- `test/run_full_session.m:36 nPracExpected = max(4, P_groups(groupID));`、
  `:37 nExpected = nPracExpected + 3 * 192;`；B17 从「组 1 只有 formal」改为 `nPracRows == nPracExpected`；
- `test/check_full_session.py` **A15**（静态：`nPractice = max(4, P);` 存在、`loopCount = P / 4;` 消失、v4.9 头注）
  + **B31**（B17 新判据）⇒ **34/34**；
- 冒烟：组 1 修前 26/27（B17 旧判据红），修后组 1、组 2 各 **27/27**。

**边界**：兜底 4 个试次只保证「被试见过一次完整流程」，不代表学过；
组 1 的学习量仍来自 60 s 联结学习。另：设计口径是 `max(4, P)`，
**不是** 4/12/36/124 那种「P+4」。

---

### 8.65 工具自己也会误伤：拿「跑了两遍」当「试次数不符」（2026-10-18，D94）

**现象**：同一场数据的 txt 是 **1152 行 = 576 × 2**，每个 `trialID` 恰出现 2 次，
CSV 只等于**最后一次**（`fopen(..., 'a+')` 追加写）。`qc_group.py` 首轮据此报
「G2 正式段 576 试次：1 名不符」+「G4 每 (T,W) 格 48 试次：有被试不符」——
两处都是把「被试把整场跑了两遍」误读成「程序少存了行」。

**根因**：读 txt 的那一步没有按 `(stage, trialID)` 去重。这是同一个根因的**第五次**触发
（D81b / D85 / Stage 1 验收 / 本次的 G2、G4）。

**修法**：`qc_group.py::subject_metrics` 在 `rows = ap.row_dicts(...)` 之后建
`seen[(stage, trialID)] = r`，`rows = list(seen.values())`（保留最后一次，与
`check_stage1_acceptance.py::dedupe` 同口径），并把 `n_dropped` 写进 `rec`、汇总表加「去重行」列。

**复跑（同一场）**：G2 PASS（576 全部合规）、G4 PASS、G5 PASS（18.8%）、G7 PASS（0.43%）、
**G3 仍 WARN**（该场确实是 v4.8 产物、0 行练习 ⇒ 真红，正是 §8.64）、
**G6 FAIL**（正确率 0.440 < 0.55，属被试本身）。

**边界**：去重只解决「同 `trialID` 多行」；一次运行内**确实少行**仍会红——
所以它是「消除假红」，不是「放宽判据」。

---
"""

section_9_add = """| 77 | ✅ **组 1 的练习段是 0 试次，而设计说 4（D93，§8.64）** | 程序 v4.9：`nPractice = max(4, P);`、`loopCount = nPractice / 4;`；`P` 与 CSV 第 8 列不变；练习行数 4/8/32/120；`check_full_session.py` A15/B31 ⇒ 34/34，冒烟两组各 27/27。 |
| 78 | ✅ **`qc_group.py` 把「跑了两遍」判成「试次数不符」（D94，§8.65）** | 按 `(stage, trialID)` 去重、保留最后一次、报「去重行」；复跑 G2/G4/G5/G7 转 PASS；G3 仍 WARN（真红，见 D93）、G6 FAIL（被试本身）。 |
"""

readme = read(README)
readme = sub_once(readme, "## 9. 尚未做", SEC_864 + "\n## 9. 尚未做", "README §8.64/§8.65")
readme = insert_after_line(
    readme, "| 76 | ✅ **路径可移植", section_9_add.rstrip("\n"), "README §9 第 77/78 项"
)

# ---------------------------------------------------------------- 3. 手册 v2.8

MANUAL_EDITS = [
    ("> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.8）",
     "> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.9）"),
    ("> 版本：v2.7（2026-10-18，v2.7 把六条自测改成路径无关",
     "> 版本：v2.8（2026-10-18，v2.8 把练习段口径改成 `max(4, P)`——组 1 也有 4 个兜底练习——并对应程序 v4.9；v2.7 把六条自测改成路径无关"),
    ("| 组别 | P（额外练习试次） | 掩蔽 |",
     "| 组别 | P（组参数）⇒ 实际练习试次 | 掩蔽 |"),
    ("| 1 | 0（无额外练习） | 有，200 ms |",
     "| 1 | 0 ⇒ **4**（兜底） | 有，200 ms |"),
    ("- **P（额外练习试次数）**：**被试间** 4 组 = 0 / 8 / 32 / 120 个练习试次。",
     "- **P（额外练习试次数）**：**被试间** 4 组 = 0 / 8 / 32 / 120；**实际练习试次 = `max(4, P)`**\n"
     "  ⇒ 组 1 也有 4 个兜底练习（不是「组 1 没有练习」，v2.8 更正）。"),
    ("- 练习试次 = 本组的 P（组 1 没有练习，直接从联结学习进入正式）。",
     "- 练习试次 = `max(4, 本组的 P)`：组 1 为 **4 个兜底练习**（先走通一遍完整流程再进正式），\n"
     "  组 2/3/4 为 8 / 32 / 120。`P` 仍是组参数，CSV 第 8 列组 1 写 0（练习行数与它不是同一个量）。"),
    ("| 1 | 有 | 0 | 4 | 3 | 576 | ≈ 25–30 分钟 |",
     "| 1 | 有 | 4（兜底） | 4 | 3 | 576 | ≈ 25–30 分钟 |"),
    ("### 5.3 练习阶段（只有 P>0 的组才有）",
     "### 5.3 练习阶段（4–120 试次；组 1 为 4 个兜底）"),
    ("- 组 2（P=8）有 8 个练习试次；组 3（P=32）有 32 个；组 4（P=120）有 120 个；**组 1（P=0）没有练习**。",
     "- 练习试次 = `max(4, P)`：组 1（P=0）**4 个兜底**、组 2 为 8、组 3 为 32、组 4 为 120。\n"
     "  组 1 的这 4 个试次同样给正确/错误/过慢反馈，目的是让被试在正式前走通一遍完整流程。"),
    ("- 一个被试的完整会话约产生：CSV 约 **576 + P** 行、txt 同量行。",
     "- 一个被试的完整会话约产生：CSV 约 **576 + max(4, P)** 行（组 1 = 580 行）、txt 同量行。"),
    ("- [ ] `stage = \"formal\"` 的行数 = **576**；练习行数 = P（组 1 应为 0 行练习）",
     "- [ ] `stage = \"formal\"` 的行数 = **576**；练习行数 = `max(4, P)`（组 1 应为 **4** 行练习，不是 0）"),
]

manual = read(MANUAL)
for old, new in MANUAL_EDITS:
    manual = sub_once(manual, old, new, f"手册: {old[:24]}")
manual = manual.replace(
    '- **怎么确认跑的是 v4.8**：`type Exp_Design_Formal.m | findstr "v4.8"`，应打印 ★★ v4.8 本次修正 段头注。',
    '- **怎么确认跑的是 v4.9**：`type Exp_Design_Formal.m | findstr "v4.9"`，应打印 ★★ v4.9 本次修正 段头注。',
)

# ---------------------------------------------------------------- 4. Stage7 / PTB

stage7 = read(STAGE7)
stage7 = sub_once(
    stage7,
    "`主试培训手册_Exp_Design_Formal.md`（v2.7，421 行）",
    "`主试培训手册_Exp_Design_Formal.md`（v2.8，426 行）",
    "Stage7 手册行",
)

ptb = read(PTBDOC)
for old, new in [
    ("`Exp_Design_Formal.m`（v4.8", "`Exp_Design_Formal.m`（v4.9"),
    ("（v2.7", "（v2.8"),
]:
    if old in ptb:
        ptb = ptb.replace(old, new, 1)

if problems:
    print("REFUSED — 以下锚点未按预期命中：")
    for p in problems:
        print("  -", p)
    sys.exit(1)

write(PLAN, plan)
write(README, readme)
write(MANUAL, manual)
write(STAGE7, stage7)
write(PTBDOC, ptb)

print("OK")
print("PLAN lines   =", len(plan.split("\n")))
print("README lines =", len(readme.split("\n")))
print("MANUAL lines =", len(manual.split("\n")))
