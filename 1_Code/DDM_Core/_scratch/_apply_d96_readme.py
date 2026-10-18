# -*- coding: utf-8 -*-
"""D96 落纸（README 部分）：新 §8.67 + §9 第 80 项。

第一版 `_apply_d96_docs.py` 已把主计划与 Stage6 方案写完，但 README 的 §9 锚点猜错
（我按 `- **79（D95…**` 的列表写法找，实际是表格行 `| 79 | ✅ **…`），断言直接中止，
所以 README 一个字没动。这里只补 README，锚点用真实格式。
"""
from __future__ import annotations

from pathlib import Path

README = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\README.md")

README_667 = [
    "### 8.67 `stage6_report.py`：Pilot 达标报告器（D96，2026-10-18）",
    "",
    "- **它回答什么**：这 N 个人合起来算不算过关、按 `Stage6_Pilot方案.md` §8 该走哪条决策分支、能不能进 Stage 7。",
    "  `analyze_pilot.py` 逐条打印（人来数）、`intake.py` 判单场、`qc_group.py` 判 Stage 7 组层质量——三者都不是这个问题。",
    "- **怎么实现的**：单场裁决复用 `intake.audit_one`；逐条 S1/S6 裁决复用 `qc_group.run_subject_check`"
    "（内部子进程调 `analyze_pilot.py`）；脚本只加聚合与 §8 决策映射，**不复制任何判据**。",
    "- **聚合口径**：§2 判据计数只统计 KEEP 场次。混入 EXCLUDE 会把「被试提前退出」写成「判据普遍失败」，"
    "而两者的处置完全相反。不计入场次的非 PASS 裁决在 §1 每行与 §3 附注里显形"
    "（「正式段 288 行 + `S6-4` FAIL」= 缺一档 T 的程序缺陷）。",
    "- **输出**：§1 逐场次（判定/正式练习行数/去重/正确率/timeout/复核标记）、§2 判据 × PASS/WARN/FAIL/INFO/未取到、",
    "  §3 触发分支（含 `S6-2c` ⇒ Stage 8 静态 vs 时变）、§4 结论 + 「复核 ≠ 剔除」提示。退出码 0/1/2。",
    "- **自测**：`exp_Check/check_stage6_report.py` **22/22**（七例）。其中一个用例本身抓出了我的 fixture 缺陷：",
    "  混放用例把合成件放组 1，与真实场次的 `(1,1)` 同名，被 intake 的「同 (组,编号) 取最浅层」折叠成 2 场 ——",
    "  **fixture 的命名空间必须与样本隔离**，否则测的不是你想测的那件事。",
    "",
]

README_80 = (
    "| 80 | ✅ **Pilot 达标报告器：判据汇总 + §8 决策分支 + 可/不可进 Stage 7（D96，§8.67）** | "
    "`1_Code/Experiment/stage6_report.py`（221 行）只做聚合与决策映射：单场裁决复用 `intake`、"
    "逐条 S1/S6 裁决复用 `qc_group.run_subject_check`；判据计数只统计 KEEP 场次，"
    "不计入场次的非 PASS 裁决单独显形；自测 **22/22**。"
    "**尚未做**：Python 侧自测未进 `run_selftest.bat`；无按 P 档的横向比较视图（§3 要求四个 P 档各 ≥1 人） |"
)


def main() -> None:
    lines = README.read_text(encoding="utf-8").split("\n")
    text = "\n".join(lines)
    assert "### 8.67" not in text, "§8.67 已存在"

    hits = [i for i, l in enumerate(lines) if l.startswith("## 9. 尚未做")]
    assert len(hits) == 1, f"`## 9.` 命中 {len(hits)} 次"
    lines[hits[0]:hits[0]] = README_667

    hits = [i for i, l in enumerate(lines) if l.startswith("| 79 | ✅ **一场数据能不能计入 N")]
    assert len(hits) == 1, f"第 79 项命中 {len(hits)} 次"
    lines.insert(hits[0] + 1, README_80)

    README.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[ok] README：{len(lines)} 行")


if __name__ == "__main__":
    main()
