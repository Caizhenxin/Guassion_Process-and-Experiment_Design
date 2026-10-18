#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_apply_d82_docs.py —— 把 D82（被试招募与知情同意包）落纸到主计划 / Stage6 / Stage7。

幂等：已插入的行不会重复插入。写入统一 newline="\\n" 裸 LF（D81 教训）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
WF = ROOT / "5_Reference" / "08_工作流"
PLAN = WF / "工作流_主计划.md"
S6 = WF / "Stage6_Pilot方案.md"
S7 = WF / "Stage7_数据采集执行与质控方案.md"

D82_ROW = (
    "| **D82** | 2026-10-18 | ✅ **把「怎么招、怎么讲、怎么签、怎么编号」固定在采集之前，并给它装上判据**。"
    "① 缺口：Stage 6/7 已有 Pilot 方案、质控 G1–G9、现场纪律，但**没有一份材料是能直接交到被试手里的**——"
    "招募公告、知情同意书、被试登记表、排期表、主试口述脚本全缺；而这类材料出错的方式不是崩溃，是"
    "「数字与设计脱钩」「占位符被顺手删掉」「关键提醒被删」，事后只会让某一批数据变得不可用。"
    "② 做法：新建 `5_Reference/08_工作流/Stage6_被试招募与知情同意包.md`（166 行）——招募公告（含「刺激很短、看不清是正常的」这条防污染提醒）、"
    "可打印知情同意书（自愿/可随时退出/匿名编号/报酬/伦理联系方式六段齐全）、被试登记表（编号 `group<1-4>_subject<n>`）、周排期表、"
    "开场口述脚本（含「**不要解释假设**」）、采集前检查清单（60.004 Hz 那块屏、帧量化 2/5/9/15）。所有机构相关项留 `【】` 占位，**不由 AI 代填**。"
    "③ 牙齿：新建 `1_Code/Experiment/exp_Check/check_consent_pack.py`（零依赖，**28 项判据**：6 个章节 + 9 个与 D4 一致的数字 + 5 条必须保留的提醒 + "
    "占位符仍在 + 7 条旧口径禁词如「9 组/无掩蔽组/≥ 60 Hz」），**28/28 通过**；`--self-test` 5/5（干净副本全过；删提醒、改 9 组、抹占位符、放宽刷新率各自被拦住）。"
    "④ 边界：判据只能保证材料**没被改坏**，不能保证伦理合规——批号、报酬、单位信息必须由研究者与伦理委员会填写。 |"
)

PROGRESS_ROW = (
    "| 2026-10-18 | **6**（被试材料 → D82） | **把「采集前的纸面环节」补齐并装上判据**："
    "新建知情同意包（招募/同意书/登记表/排期/口述脚本/检查清单，166 行）+ `check_consent_pack.py`（28 项判据 28/28、自测 5/5）；"
    "所有机构项留 `【】` 占位待人工填写 |"
)

FILE_ROW = (
    "| `5_Reference/08_工作流/Stage6_被试招募与知情同意包.md`（**新建**，166 行）+ "
    "`1_Code/Experiment/exp_Check/check_consent_pack.py`（**新建**，零依赖，28/28）+ "
    "`1_Code/DDM_Core/_scratch/_apply_d82_docs.py`（**新建**，本补丁） | 招募公告写「最短 33 ms、看不清是正常的」防被试要求重来；"
    "同意书六段（目的/流程/刺激/自愿退出/匿名/报酬/联系方式）；登记表编号规则 `group<1-4>_subject<n>`；"
    "口述脚本含「不要解释假设」；脚本判据盯住数字与设计不脱钩、占位符不被抹掉 |"
)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


def insert_after(text: str, anchor_prefix: str, new_line: str, label: str) -> str:
    if new_line.strip() in text:
        print(f"[SKIP] {label}：已存在")
        return text
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    assert len(hits) == 1, f"{label}：锚点 {anchor_prefix!r} 命中 {len(hits)} 次（应为 1）"
    lines.insert(hits[0] + 1, new_line)
    print(f"[OK] {label}：插在第 {hits[0] + 1} 行之后")
    return "\n".join(lines)


def main() -> int:
    # ---- 主计划：D82 决策行 ----
    t = read(PLAN)
    t = insert_after(t, "| **D81** | 2026-10-18 |", D82_ROW, "主计划 D82 决策行")

    # ---- 主计划：进度行 ----
    t = insert_after(
        t, "| 2026-10-18 | **6**（Stage 1 判据回放 → D81）", PROGRESS_ROW, "主计划进度行"
    )

    # ---- 主计划：§8 文件行（追加到文件表末尾）----
    if FILE_ROW.split(" | ")[0] in t:
        print("[SKIP] 主计划文件行：已存在")
    else:
        t = t.rstrip("\n") + "\n" + FILE_ROW + "\n"
        print("[OK] 主计划文件行：追加到文件表末尾")
    write(PLAN, t)

    # ---- Stage 6：现场清单补一条 ----
    t = read(S6)
    bullet = (
        "9. ☐ 招募公告、知情同意书、被试登记表、周排期表、开场口述脚本均已就位"
        "（见 `Stage6_被试招募与知情同意包.md`，D82）；**同意书签署必须在任何数据产生之前**。"
    )
    if bullet in t:
        print("[SKIP] Stage6 清单：已存在")
    else:
        lines = t.split("\n")
        hits = [i for i, ln in enumerate(lines) if ln.startswith("8. ☐ 按 §8 决策")]
        assert len(hits) == 1, f"Stage6 清单锚点命中 {len(hits)} 次"
        lines.insert(hits[0] + 1, bullet)
        t = "\n".join(lines)
        print(f"[OK] Stage6 清单：插在第 {hits[0] + 1} 行之后")
        write(S6, t)

    # ---- Stage 7：工具链表补一行 ----
    t = read(S7)
    row = (
        "| `1_Code/Experiment/exp_Check/check_consent_pack.py`（**新建**，D82） | "
        "招募/知情同意材料的**判据**（28 项：章节、与 D4 一致的数字、必须保留的提醒、占位符仍在、旧口径禁词）；"
        "自测 5/5 |"
    )
    if "check_consent_pack.py" in t:
        print("[SKIP] Stage7 工具链：已存在")
    else:
        lines = t.split("\n")
        hits = [i for i, ln in enumerate(lines) if ln.startswith("| `1_Code/DDM_Core/_scratch/make_fake_pilot.py`")]
        assert len(hits) == 1, f"Stage7 工具链锚点命中 {len(hits)} 次"
        lines.insert(hits[0] + 1, row)
        t = "\n".join(lines)
        print(f"[OK] Stage7 工具链：插在第 {hits[0] + 1} 行之后")
        write(S7, t)

    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
