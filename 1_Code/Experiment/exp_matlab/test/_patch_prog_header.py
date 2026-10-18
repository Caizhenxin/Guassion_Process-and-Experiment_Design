# -*- coding: utf-8 -*-
"""Exp_Design_Formal.m 头注两处对齐：
   1) L54 原写「点取消也在弹窗里重来」，与代码不符（取消是唯一会终止的情况）——改准确；
   2) 补 v4.3 段：弹窗循环抽成 exp_ask_subject_info.m（可 hooks 注入、无屏幕自测）。
"""
from pathlib import Path

P = Path(r"1_Code/Experiment/exp_matlab/Exp_Design_Formal.m")
t = P.read_text(encoding="utf-8")

old54 = '%        全部校验，点"取消"也在弹窗里重来（不会得到 NaN 继续跑）。'
new54 = ('%        全部校验；点"取消"/关窗是**唯一**会终止的情况（不把 NaN 带进实验）。')
assert old54 in t
t = t.replace(old54, new54, 1)

anchor = ('%   (#2) 同时清掉头注里"组7 无掩蔽"的旧说明，并在主试确认回显里打印\n'
          '%        "组别 → P"（如 groupID=2 ⇒ P=8），让主试回车前就能看出填错。\n')
assert anchor in t
add = anchor + (
    '%\n'
    '% ★★ v4.3 本次重构（2026-10-18，为了让这条路径能被无屏幕自测覆盖）★★\n'
    '%   弹窗 + 校验 + 主试确认的循环从本脚本正文搬到 exp_ask_subject_info.m（本脚本只调用它），\n'
    '%   好处：hooks 可以注入假的 inputdlg/warndlg/input，于是「先填 7 被拒 → 改填 1 通过」这条\n'
    '%   真实路径能在命令行跑一遍（test/check_ask_info.m，40 项全通过）。脚本正文因此少了约 50 行。\n'
    '%   自测入口：\n'
    '%     matlab -batch "cd(\'<仓库>/1_Code/Experiment/exp_matlab\'); addpath(\'test\'); check_ask_info"\n'
    '%     matlab -batch "cd(\'<仓库>/1_Code/Experiment/exp_matlab\'); addpath(\'test\'); check_input_validation"\n'
    '%     python -X utf8 1_Code/Experiment/exp_matlab/test/check_manual_d4.py   % 程序/校验/手册/Word 四者口径\n')
t = t.replace(anchor, add, 1)

P.write_text(t, encoding="utf-8", newline="\n")
print("header patched")
