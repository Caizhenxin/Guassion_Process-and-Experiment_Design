# -*- coding: utf-8 -*-
"""_patch_v44_header.py —— 在 Exp_Design_Formal.m 头注里加 v4.4 段（D78），并更新自测入口列表。

锚点：v4.3 段的最后一行（python check_manual_d4.py 那行）之后的空注释行。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "1_Code/Experiment/exp_matlab/Exp_Design_Formal.m"

ANCHOR = """%     python -X utf8 1_Code/Experiment/exp_matlab/test/check_manual_d4.py   % 程序/校验/手册/Word 四者口径
%
"""

NEW = """%     python -X utf8 1_Code/Experiment/exp_matlab/test/check_manual_d4.py   % 程序/校验/手册/Word 四者口径
%     matlab -batch "cd('<仓库>/1_Code/Experiment/exp_matlab'); addpath('test'); check_data_accum"
%
% ★★ v4.4 本次修正（2026-10-18，主试实跑第一个 timeout 试次就崩：请修 #1）★★
%   (#1) 数据累积容器 table → cell。旧代码 `data = table()` 之后逐行 `data{trialIndex,14}=respStr`，
%        table 的变量类型由**第一次赋值**锁定：第一行写 'f'（宽度 1）就把 Response 固定成
%        1 字符宽 char 矩阵，第一个 timeout 试次写 'NA'（宽度 2）立刻报
%        「赋值右侧的值的宽度错误。赋值需要宽度为 1 的值」并整场退出（Screen('CloseAll')）。
%        次生症状：每加一行都打印「赋值时将各行添加到了表格中，但并未对表格中所有现有的
%        变量赋值」（主试看到的那 6 条警告），且 table 逐行增长是 O(n^2) 复制。
%        修法：exp_new_data(25) 建 0×25 cell 累积；保存时 exp_data_table 一次性 cell2table。
%   (#2) 顺带修掉一个**只在更晚才会暴露**的静默错误：cell2table 会把不等长的字符列用空格
%        补齐成 char 矩阵（'self' / 'stranger' ⇒ 'self     '），writetable 会把这些补齐空格
%        原样写进 CSV ⇒ 下游按 'self' 精确匹配失败。exp_data_table 统一把 char 列转
%        string(cellstr(...))（cellstr 逐行去尾随空格）。
%   (#3) 保存前增加行数自检：size(data,1) 与 trialIndex-1 不等就 warning（有试次没进内存表）。
%   ⚠ 教训：**"能跑完全程"不等于"能存下来"**——数据写入路径必须单独自测
%      （test/check_data_accum.m：混合 f/j/NA 三行 + 不等长 stim 标签 + 静态守卫）。
%
"""

t = SRC.read_text(encoding="utf-8")
if NEW in t:
    print("[跳过] v4.4 头注已存在")
elif t.count(ANCHOR) != 1:
    raise SystemExit(f"❌ 锚点命中 {t.count(ANCHOR)} 次")
else:
    t = t.replace(ANCHOR, NEW)
    SRC.write_text(t, encoding="utf-8", newline="\n")
    print("[插入] v4.4 头注")
print(f"行数 = {t.count(chr(10)) + 1}")
