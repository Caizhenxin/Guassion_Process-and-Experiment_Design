# -*- coding: utf-8 -*-
"""D96 落纸：`stage6_report.py`（Pilot 达标报告器）写进四份文档。

改动位置（每处都断言「命中恰 1 次」，命中数不对就整批不写）：

主计划 `5_Reference/08_工作流/工作流_主计划.md`
  1. 决策表：在 D95 行后插 D96
  2. 进度表：末行后插一行
  3. 变更日志：末行后插一行
  4. 一手证据：末行后插一行

`5_Reference/08_工作流/Stage6_Pilot方案.md`
  5. §6.2 之后新增 §6.3（报告器）
  6. §9 现场清单第 7 条改成「分析器 + 报告器两条命令」
  7. §12 变更日志加 v1.3

`1_Code/DDM_Core/README.md`
  8. 新 §8.67（插在 `## 9. 尚未做` 之前）
  9. §9 末项后加第 80 项
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
STAGE6 = ROOT / "5_Reference/08_工作流/Stage6_Pilot方案.md"
README = ROOT / "1_Code/DDM_Core/README.md"


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def write(p: Path, lines: list[str]) -> None:
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def find_one(lines: list[str], needle: str, startswith: bool = False) -> int:
    hits = [i for i, l in enumerate(lines) if (l.startswith(needle) if startswith else needle in l)]
    assert len(hits) == 1, f"锚点命中 {len(hits)} 次（应为 1）：{needle[:60]}"
    return hits[0]


D96_DECISION = (
    "| **D96** | 2026-10-18 | ✅ **Pilot 达标报告器 `stage6_report.py`：把「这 N 个人能不能进 Stage 7」收成一份报告**。"
    "① 触发：Stage 6 真正要回答的问题——「N 个人合起来算不算过关、按 `Stage6_Pilot方案.md` §8 该走哪条决策分支」"
    "——此前只能由人对着 `analyze_pilot.py` 的屏显逐个 tag 数；而 `intake.py` 判的是**单场**、"
    "`qc_group.py` 判的是 Stage 7 的**组层数据质量**（G1–G9），三者都不是这个问题；"
    "② 落地件：`1_Code/Experiment/stage6_report.py`（**221 行**，零依赖）+ "
    "`1_Code/Experiment/exp_Check/check_stage6_report.py`（**171 行，22/22**）；"
    "③ 判据不分叉：单场裁决复用 `intake.audit_one`、逐条 S1/S6 裁决复用 `qc_group.run_subject_check`"
    "（后者内部子进程调 `analyze_pilot.py`，单一事实来源），本脚本**只新增聚合与决策映射**；"
    "④ 聚合口径：判据汇总**只用 KEEP 场次**（把 EXCLUDE 场次混进汇总会把「被试提前退出」当成「判据普遍失败」）；"
    "不计入场次的非 PASS 裁决仍然显形（§1 每行 + §3 附注），因为「缺一档 T」这类**程序缺陷**正是靠它被看见；"
    "⑤ 输出：§1 逐场次、§2 判据 × PASS/WARN/FAIL 计数、§3 按 §8 触发的决策分支（含 S6-2c ⇒ Stage 8 静态/时变）、"
    "§4 结论（可/不可进 Stage 7 + 复核率提示「复核 ≠ 剔除」）；退出码 0/1/2；"
    "⑥ 自测七例 22 项：干净 2 人判「可进」、真实 v4.8 场次判 N=0、**混放时不计入者不进汇总**、"
    "`--defect-missing-t` 让 S6-4 以「提前退出 + 裁决 S6-4 FAIL」双线显形、空目录 2、`--expect-n 8` 报 N 不足、`--out` 写盘；"
    "⑦ 自己踩的坑：混放用例最初把合成件放组 1，与真实场次的 `(1,1)` 同名 ⇒ 触发 intake 的「同 (组,编号) 取最浅层」，"
    "测出来的「3 场」其实是 2 场；改成合成件放组 2 才测到了真正想测的东西（**fixture 命名空间必须与样本隔离**）。"
    " | `1_Code/Experiment/stage6_report.py`（**新建**，221 行）+ "
    "`1_Code/Experiment/exp_Check/check_stage6_report.py`（**新建**，171 行，**22/22**）+ "
    "`1_Code/DDM_Core/_scratch/_apply_d96_docs.py` | **(1)** Pilot 每场交回后跑 "
    "`python -X utf8 1_Code/Experiment/stage6_report.py 1_Code/Experiment/pilot_data --expect-n 8`，"
    "§4 判「可进入 Stage 7」才回填三处；**(2)** 四个用户侧 Stage 不变 |"
)

D96_PROGRESS = (
    "| 2026-10-18 | **6（Pilot 达标报告器 → D96）** | 把「N 个人合起来算不算过关、该走 §8 哪条分支」"
    "从「对着屏显数 tag」收成**一份 Markdown 报告**：判据汇总只用 KEEP 场次，不计入场次的裁决单独显形（避免把"
    "「提前退出」误读成「判据普遍失败」）；§8 的五条决策规则逐字搬进代码，S6-2c 单独判 Stage 8 静态/时变。"
    "自测 **22 项通过**，并用真实 v4.8 场次 + `--defect-missing-t` 缺陷件做了双线验证。"
    " | `1_Code/Experiment/stage6_report.py`（**新建**，221 行）+ "
    "`1_Code/Experiment/exp_Check/check_stage6_report.py`（**新建**，22/22） | Pilot 每场交回后跑一次 |"
)

D96_CHANGELOG = (
    "| 2026-10-18 | **新增 D96（Pilot 达标报告器）**：`1_Code/Experiment/stage6_report.py`（221 行，"
    "单场 `intake` + 逐条 `qc_group.run_subject_check` 聚合 + §8 决策映射 + Markdown 报告，退出码 0/1/2）+ "
    "`exp_Check/check_stage6_report.py`（**22/22**）；判据汇总只统计 KEEP 场次，"
    "不计入场次的非 PASS 裁决单独显形 |"
)

D96_EVIDENCE = (
    "| `1_Code/Experiment/stage6_report.py`（**新建**，D96，221 行）+ "
    "`1_Code/Experiment/exp_Check/check_stage6_report.py`（**新建**，22/22） | "
    "**D96**：Pilot 达标聚合（判据汇总 + §8 决策分支 + 可/不可进 Stage 7） |"
)

STAGE6_63 = [
    "",
    "### 6.3 达标报告器 `1_Code/Experiment/stage6_report.py`（**零依赖**）",
    "",
    "前两个工具各自只回答半边：`analyze_pilot.py` 逐条打印裁决（人来数），`intake.py` 判**单场**能不能计入 N。",
    "Stage 6 要回答的是「这 N 个人合起来算不算过关、按 §8 走哪条分支」。报告器把它做成一条命令：",
    "",
    "```bash",
    "python -X utf8 1_Code/Experiment/stage6_report.py 1_Code/Experiment/pilot_data --expect-n 8",
    "```",
    "",
    "- **不复用判据实现**：单场裁决调 `intake.audit_one`，逐条 S1/S6 裁决调 `qc_group.run_subject_check`"
    "（内部子进程 `analyze_pilot.py`，单一事实来源）。报告器只加**聚合**与 **§8 决策映射**。",
    "- **汇总口径**：§2 判据计数**只统计 KEEP 场次**。把 EXCLUDE 场次混进去，会把「被试提前退出」显示成"
    "「判据普遍失败」，而两者的处置完全相反。",
    "- **不计入场次仍显形**：§1 的「复核标记／不计入原因」列与 §3 附注会列出它们的非 PASS 裁决——"
    "「正式段只有 288 行 + `S6-4` FAIL」这种组合正是**程序缺陷**（缺一档 T）的信号，不能因为排除就看不见。",
    "- **退出码**：0 = §4 判「可进入 Stage 7」；1 = 有 FAIL 或计入 N 不足；2 = 目录里没有场次。",
    "- 自测：`python -X utf8 1_Code/Experiment/exp_Check/check_stage6_report.py`（**22/22**，七例："
    "干净 2 人 / 真实 v4.8 场次 / 混放 / `--defect-missing-t` / 空目录 / `--expect-n` 不足 / `--out` 写盘）。",
]

STATGE6_7 = (
    "7. ☐ 跑分析器与报告器：`python -X utf8 1_Code/Experiment/analyze_pilot.py 1_Code/Experiment/pilot_data`"
    "（日志存 `pilot_data/analyze_pilot_log.txt`），再跑 "
    "`python -X utf8 1_Code/Experiment/stage6_report.py 1_Code/Experiment/pilot_data --expect-n 8 "
    "--out 1_Code/Experiment/pilot_data/stage6_report.md`。"
)

STAGE6_CHANGELOG = (
    "| v1.3 | 2026-10-18 | 新增 §6.3 达标报告器 `stage6_report.py`（D96）：把「判据汇总 + §8 决策分支 + 可/不可进 Stage 7」"
    "收成一份 Markdown 报告；判据汇总只统计 KEEP 场次，不计入场次的非 PASS 裁决单独显形（附自测 22/22）。"
    "§9 现场清单第 7 条改为「分析器 + 报告器」两条命令。 |"
)

README_667 = [
    "### 8.67 `stage6_report.py`：Pilot 达标报告器（D96，2026-10-18）",
    "",
    "- **它回答什么**：这 N 个人合起来算不算过关、按 `Stage6_Pilot方案.md` §8 该走哪条决策分支、能不能进 Stage 7。",
    "  `analyze_pilot.py` 逐条打印（人来数）、`intake.py` 判单场、`qc_group.py` 判 Stage 7 组层质量——三者都不是这个问题。",
    "- **怎么实现的**：单场裁决复用 `intake.audit_one`；逐条 S1/S6 裁决复用 `qc_group.run_subject_check`"
    "（内部子进程调 `analyze_pilot.py`）；脚本只加聚合与 §8 决策映射，**不复制任何判据**。",
    "- **聚合口径**：§2 判据计数只统计 KEEP 场次。混入 EXCLUDE 会把「被试提前退出」写成「判据普遍失败」。",
    "  不计入场次的非 PASS 裁决在 §1 每行与 §3 附注里显形（「正式段 288 行 + `S6-4` FAIL」= 缺一档 T 的程序缺陷）。",
    "- **输出**：§1 逐场次（判定/正式练习行数/去重/正确率/timeout/复核标记）、§2 判据 × PASS/WARN/FAIL、"
    "§3 触发分支（含 `S6-2c` ⇒ Stage 8 静态 vs 时变）、§4 结论 + 「复核 ≠ 剔除」提示。退出码 0/1/2。",
    "- **自测**：`exp_Check/check_stage6_report.py` **22/22**（七例）。其中一个用例本身抓出了我的 fixture 缺陷："
    "混放用例把合成件放组 1，与真实场次的 `(1,1)` 同名，被 intake 的「同 (组,编号) 取最浅层」规则折叠成 2 场 —— "
    "**fixture 的命名空间必须与样本隔离**，否则测的不是你想测的那件事。",
    "",
]

README_80 = (
    "- **80（D96，2026-10-18）** Pilot 达标报告器 `1_Code/Experiment/stage6_report.py`（221 行）："
    "判据汇总只统计 KEEP 场次 + §8 决策映射 + 可/不可进 Stage 7 结论；自测 22/22。"
    "尚未做：报告是**人读的 Markdown**，还没接进 `run_selftest.bat`（Python 侧自测仍在手工跑）；"
    "也还没有「多组横向比较」视图（按 P 档比较 timeout/正确率），而 §3 要求四个 P 档各 ≥1 人。"
)


def main() -> None:
    lines = read(PLAN)
    i = find_one(lines, "| **D95** |", startswith=True)
    lines.insert(i + 1, D96_DECISION)

    i = find_one(lines, "| 2026-10-18 | **6/7（单场入库判定器 → D95）** |", startswith=True)
    lines.insert(i + 1, D96_PROGRESS)

    i = find_one(lines, "新增 D95（单场入库判定器）", startswith=True) if False else find_one(
        lines, "| 2026-10-18 | **新增 D95（单场入库判定器）**")
    lines.insert(i + 1, D96_CHANGELOG)

    i = find_one(lines, "`1_Code/Experiment/intake.py`（**新建**，D95，251 行）")
    lines.insert(i + 1, D96_EVIDENCE)

    write(PLAN, lines)
    print(f"[ok] 主计划：{len(lines)} 行")

    # ---- Stage6 方案 ----
    s6 = read(STAGE6)
    j = find_one(s6, "## 7. 工具自测（六例，全部通过）", startswith=True)
    assert s6[j - 1].strip() == "" or s6[j - 1].startswith("|"), f"§7 前一行异常：{s6[j-1][:40]}"
    s6[j:j] = STAGE6_63
    k = find_one(s6, "7. ☐ 跑分析器：", startswith=True)
    s6[k] = STATGE6_7
    m = find_one(s6, "| v1.2 | 2026-10-17 |", startswith=True)
    s6.insert(m + 1, STAGE6_CHANGELOG)
    write(STAGE6, s6)
    print(f"[ok] Stage6 方案：{len(s6)} 行")

    # ---- README ----
    rd = read(README)
    n = find_one(rd, "## 9. 尚未做", startswith=True)
    rd[n:n] = README_667
    o = find_one(rd, "- **79（D95，2026-10-18）**", startswith=True)
    rd.insert(o + 1, README_80)
    write(README, rd)
    print(f"[ok] README：{len(rd)} 行")


if __name__ == "__main__":
    main()
