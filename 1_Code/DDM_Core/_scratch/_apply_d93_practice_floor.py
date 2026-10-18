# -*- coding: utf-8 -*-
"""D93：练习段补 4 试次兜底（P=0 组原先是 0 个练习试次）。

设计口径（`5_Reference/08_工作流/Stage6_Pilot方案.md:40`、`qc_group.py:232`）：
    「P = 0 走 n_practice = 4 的兜底，P > 0 走完整练习」
程序实际：`loopCount = P / 4` ⇒ P=0 时 loopCount=0 ⇒ 练习段整段跳过。
修法：`nPractice = max(4, P)`，再 `loopCount = nPractice / 4`。
"""
from pathlib import Path

F = Path("1_Code/Experiment/exp_matlab/Exp_Design_Formal.m")
src = F.read_text(encoding="utf-8")

OLD = "loopCount = P / 4; % 计算循环次数（P/4次）"
NEW = ("nPractice = max(4, P);   % ★ D93：P=0 组也要看满 4 个练习试次（设计兜底，非 0）\n"
       "loopCount = nPractice / 4; % 计算循环次数（nPractice/4 次，每轮 4 类刺激各一次）")
assert src.count(OLD) == 1, src.count(OLD)
src = src.replace(OLD, NEW)

HEAD_ANCHOR = "%\n% ★★ v4.7 本次修正（2026-10-18，主试实机报告\"块首指导语一闪而过\"；D90）★★"
head = (
    "%\n"
    "% ★★ v4.9 本次修正（2026-10-18，D93：练习段 4 试次兜底）★★\n"
    "%   (#1) 练习循环原写 `loopCount = P / 4`。P=0 的组（组1）⇒ loopCount=0 ⇒ 练习段\n"
    "%        **整段跳过**，被试从没看过一次「注视点→形状+标签→掩蔽→按键」的完整流程就进正式段。\n"
    "%        设计口径是「P=0 走 n_practice = 4 的兜底」（Stage6_Pilot方案.md:40、qc_group.py:232），\n"
    "%        抓出这一条的是组级 QC 的 G3（真实实机数据：组1 练习段 0 试次 ≠ 应收 4）。\n"
    "%   (#2) 修法：`nPractice = max(4, P)`（练习试次 = 4/8/32/120），`loopCount = nPractice / 4`。\n"
    "%        变量 P 本身不改（列 8 仍写 P=0），P 仍是「额外练习试次数」。\n"
    "%   (#3) 受影响：组1 的 txt `stage=practice` 行数 0 → 4、总行数 576 → 580；\n"
    "%        其余三组不变（8/32/120 都 ≥ 4）。\n"
)
assert src.count(HEAD_ANCHOR) == 1
src = src.replace(HEAD_ANCHOR, head + HEAD_ANCHOR)

F.write_text(src, encoding="utf-8", newline="\n")
print(f"Exp_Design_Formal.m：{len(src.splitlines())} 行（练习段兜底 4 试次 + v4.9 头注）")
