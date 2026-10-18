# -*- coding: utf-8 -*-
"""check_manual_d4.py —— 钉住「程序 / 校验函数 / 主试手册 / Word 版」四者口径一致（D4）

为什么需要它
------------
2026-10-18 主试按旧手册填「组别 7」直接报错（`D4 只有 4 个 P 组…groupID=7 越界`），
根因是：程序在 v4 已改为 D4（4 组、576 试次、3 block、25 列），而
`主试培训手册_Exp_Design_Formal.md` 还是旧的「9 条件 / 520 试次 / 10 block / 16 列 / 组7 无掩蔽」。
两边都"看着没问题"，只有对照才能发现漂移 —— 所以把对照做成脚本。

判据分四组
----------
A 程序侧  ：`Exp_Design_Formal.m` 里 D4 的常量与结构（组数/T/W/重复数/列名/调用校验函数）
B 校验函数：`exp_check_subject_info.m` 存在、默认 4 组、有自测
C 手册侧  ：`主试培训手册_Exp_Design_Formal.md` 与 A 一致，且**不含**旧版残留数字
D Word 版 ：`.docx` 存在且不早于 `.md`（防止改完 md 忘了重生成）

用法 / 退出码
-------------
    python -X utf8 1_Code/Experiment/exp_matlab/test/check_manual_d4.py
退出码 0 = 全部通过；1 = 有未通过项（逐条打印原因）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
EXP = HERE.parent                      # 1_Code/Experiment/exp_matlab
ROOT = HERE.parents[3]                 # 仓库根

PROG = EXP / "Exp_Design_Formal.m"
FUNC = EXP / "exp_check_subject_info.m"
TESTM = HERE / "check_input_validation.m"
MANUAL = EXP / "主试培训手册_Exp_Design_Formal.md"
DOCX = EXP / "主试培训手册_Exp_Design_Formal.docx"

COLUMNS25 = [
    "groupID", "subjectID", "gender", "age", "handedness", "stage", "trialID",
    "P", "T", "W", "Shape", "Label", "CorrectKey", "Response", "RT", "Correct",
    "block", "premature_press", "timeout", "responded_by_deadline",
    "stimulus_onset_actual", "stimulus_offset_actual", "mask_onset_actual",
    "stimulus_dur_actual", "stimulus_frames",
]

results: list[tuple[str, bool, str]] = []


def check(section: str, name: str, cond: bool, detail: str = "") -> None:
    results.append((section, bool(cond), f"{name}" + (f" ｜ {detail}" if detail and not cond else "")))


def main() -> int:
    for p in (PROG, FUNC, TESTM, MANUAL):
        if not p.exists():
            print(f"❌ 缺文件：{p}")
            return 2

    prog = PROG.read_text(encoding="utf-8")
    func = FUNC.read_text(encoding="utf-8")
    manual = MANUAL.read_text(encoding="utf-8")

    # ---------------- A. 程序侧 ----------------
    check("A 程序", "P_groups 恰为 D4 的 4 组 [0;8;32;120]",
          bool(re.search(r"P_groups\s*=\s*\[0;\s*8;\s*32;\s*120\]", prog)))
    check("A 程序", "T 名义水平 = 33.33/83.33/149.99/249.98",
          bool(re.search(r"T_nominal\s*=\s*\[33\.33,\s*83\.33,\s*149\.99,\s*249\.98\]", prog)))
    check("A 程序", "W 名义水平 = 799.98/1199.9/1799.9",
          bool(re.search(r"W_nominal\s*=\s*\[799\.98,\s*1199\.9,\s*1799\.9\]", prog)))
    check("A 程序", "每格重复 12 次（nRep）", bool(re.search(r"nRep\s*=\s*12", prog)))
    check("A 程序", "3 个 block（numel(W_levels)）", "block = numel(W_levels)" in prog)
    check("A 程序", "每块 192 试次（4×4×12）", "4 × 4 × 12 = 192" in prog)
    check("A 程序", "调用 exp_ask_subject_info 收集信息（v4.3 抽出成函数，便于无屏幕自测）",
          "exp_ask_subject_info(P_groups)" in prog)
    check("A 程序", "组别越界不再在弹窗处直接 error",
          "if ~isfinite(groupID)" not in prog, "脚本里仍留着手写校验块")
    check("A 程序", "25 列表头按序齐全",
          all(c in prog for c in COLUMNS25), "缺列名")
    check("A 程序", "头注不再自称「组7=无掩蔽」为现行条件",
          '(2) 组7 由旧版' not in prog and "组7\"由旧版" not in prog)

    # ---------------- A2. 弹窗循环函数（v4.3） ----------------
    ask = (EXP / "exp_ask_subject_info.m").read_text(encoding="utf-8")
    check("A2 弹窗函数", "文件存在且只有一个返回（info 结构体）",
          ask.lstrip().startswith("function info = exp_ask_subject_info"))
    check("A2 弹窗函数", "内部调用 exp_check_subject_info 逐项校验",
          "exp_check_subject_info(userInput, P_groups)" in ask)
    check("A2 弹窗函数", "非法时 warndlg 提示后重填（不 error 退出）",
          "warndlg" in ask and "callout(hooks, 'warndlg'" in ask)
    check("A2 弹窗函数", "只有取消才 error（含「已取消」）",
          "已取消" in ask and "isempty(userInput)" in ask)
    check("A2 弹窗函数", "填完回显并允许输入 r 重填",
          "输入 r 回车则重新填写信息" in ask and "strcmpi(strtrim(choice), 'r')" in ask)
    check("A2 弹窗函数", "支持 hooks 注入（无屏幕自测用）",
          "hooks" in ask and "callvoid(hooks, 'fprintf'" in ask)
    check("A2 弹窗函数", "自测文件存在且覆盖「填 7 被拒」路径",
          "check_ask_info.m" in [p.name for p in HERE.iterdir()])

    # ---------------- B. 校验函数 ----------------
    check("B 校验函数", "默认 P_groups = [0;8;32;120]",
          bool(re.search(r"P_groups\s*=\s*\[0;\s*8;\s*32;\s*120\]", func)))
    check("B 校验函数", "组别越界提示含「4 个 P 组」",
          "个 P 组（被试间）" in func)
    check("B 校验函数", "五项信息全部校验（编号/性别/年龄/惯用手）",
          all(k in func for k in ("被试编号必须", "性别只能填", "年龄必须", "惯用手只能填")))
    check("B 校验函数", "自测文件存在且覆盖组别=7", "组别=7" in TESTM.read_text(encoding="utf-8"))

    # ---------------- C. 手册侧 ----------------
    check("C 手册", "标题标明 D4", "D4" in manual.split("\n")[0])
    check("C 手册", "写明组别只有 1–4",
          ("组别**只有 1–4" in manual) or ("组别只有 1–4" in manual))
    check("C 手册", "4 组速查（P0/P8/P32/P120）",
          all(s in manual for s in ("组1 P0", "组2 P8", "组3 P32", "组4 P120")))
    check("C 手册", "正式试次 576", "576" in manual)
    check("C 手册", "3 个 block × 192", ("3 个 block" in manual) and ("192" in manual))
    check("C 手册", "表头 25 列", "25 列" in manual)
    check("C 手册", "25 个列名逐个出现",
          all(c in manual for c in COLUMNS25), "缺列名")
    check("C 手册", "四档 T 的秒值可出现",
          all(s in manual for s in ("0.033333", "0.083333", "0.14999", "0.24998")))
    check("C 手册", "三档 W 的秒值可出现",
          all(s in manual for s in ("0.79998", "1.1999", "1.7999")))
    check("C 手册", "写清「填 7 会怎样（提示并重填）」",
          ("填 7" in manual or "填了旧组号 7" in manual) and ("重填" in manual))

    # 旧版残留：这些数字若以「现行」口吻出现在手册里就是漂移。
    # 允许它们只出现在**明确标注旧版**的句子里（第 0 节要解释"填 7 为什么被拒"，
    # 必须点名旧版的 9 条件设计）；判据是"每一次出现都在含『旧版』的那一行"。
    def stale_absent(token: str, hist_ok: bool = True) -> bool:
        for line in manual.split("\n"):
            if token in line and not (hist_ok and any(
                    w in line for w in ("旧版", "旧的", "已作废", "上一版"))):
                return False
        return True

    stale = {
        "9 条件": "9 条件",
        "520 试次": "520",
        "10 个 block": "10 个 block",
        "16 列": "16 列",
        "组 7 与组 5": "组 7 与组 5",
        "无掩蔽组：7": "无掩蔽组：**7**",
    }
    for label, pat in stale.items():
        check("C 手册", f"不含旧版残留「{label}」（历史说明除外）", stale_absent(pat))

    # ---------------- D. Word 版 ----------------
    check("D Word", "docx 存在", DOCX.exists())
    if DOCX.exists():
        check("D Word", "docx 不早于 md（改完要重新生成）",
              DOCX.stat().st_mtime >= MANUAL.stat().st_mtime,
              "docx 比 md 旧，请跑 automation/md_to_docx.py")
        check("D Word", "docx 体积合理（>5 KB）", DOCX.stat().st_size > 5000,
              f"{DOCX.stat().st_size} B")

    # ---------------- 汇总 ----------------
    cur = None
    for section, ok, name in results:
        if section != cur:
            print(f"\n[{section}]")
            cur = section
        print(("  ✅ " if ok else "  ❌ ") + name)

    nfail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n== 共 {len(results)} 项：通过 {len(results) - nfail} / 未通过 {nfail} ==")
    if nfail:
        print("❌ 有未通过项：程序/校验函数/手册/Word 版口径不一致")
        return 1
    print("✅ 四份产物口径一致（D4：4 组、576 试次、3 block、25 列）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
