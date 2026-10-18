# -*- coding: utf-8 -*-
"""_patch_v44_data_accum.py —— Exp_Design_Formal.m v4.3 → v4.4（D78）

修两个缺陷：
1) `data = table()` + `data{r,c}=` 逐行增长：table 变量宽度被第一行锁死，
   第一个 timeout 写 'NA' 就崩（"赋值右侧的值的宽度错误"）；且反复打印扩行警告、O(n^2)。
2) `data.Properties.VariableNames = columnNames;` 在空表/增长后的表上都不可靠。

改成：cell 累积（exp_new_data）→ 保存时一次性 cell2table（exp_data_table，char 列转 string）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "1_Code/Experiment/exp_matlab/Exp_Design_Formal.m"

PAIRS = [
    ("""% 初始化一个空的表格
data = table();
""",
     """% 逐试次累积容器：**必须用 cell 而不是 table()**（★ v4.4 / D78）
% table 的变量类型由第一次赋值锁定：第一行写 'f'（宽度 1）就把 Response 列固化成
% 1 字符宽，第一个 timeout 试次写 'NA'（宽度 2）会报
% 「赋值右侧的值的宽度错误。赋值需要宽度为 1 的值」并整场退出（2026-10-18 实机踩到）。
% cell 不锁宽度；保存时用 exp_data_table 一次性转换。
data = exp_new_data(25);
"""),
    ("""data.Properties.VariableNames = columnNames;
% 设置保存文件的路径（根据被试编号命名文件）
filename = ['EXP_data_group' num2str(groupID) '_' num2str(subjectID) '.csv'];
% 保存为 CSV 文件
writetable(data, filename);
""",
     """% ★ v4.4：cell → table 一次性转换（char 列转 string，去掉补齐空格；见 exp_data_table.m）
if size(data, 1) ~= trialIndex - 1
    warning('Exp_Design_Formal:rowCount', ...
        '累积 %d 行，但 trialIndex-1 = %d —— 有试次没写进内存表，请检查。', ...
        size(data, 1), trialIndex - 1);
end
dataTable = exp_data_table(data, columnNames);
% 设置保存文件的路径（根据被试编号命名文件）
filename = ['EXP_data_group' num2str(groupID) '_' num2str(subjectID) '.csv'];
% 保存为 CSV 文件
writetable(dataTable, filename);
"""),
]

t = SRC.read_text(encoding="utf-8")
for old, new in PAIRS:
    if new in t:
        print("[跳过] 已打过补丁的片段存在")
        continue
    if t.count(old) != 1:
        raise SystemExit(f"❌ 锚点命中 {t.count(old)} 次：{old.splitlines()[0]}")
    t = t.replace(old, new)
    print("[替换] " + old.splitlines()[0].strip())

t = t.replace("function Exp_Design_Formal()", "function Exp_Design_Formal()", 1)
SRC.write_text(t, encoding="utf-8", newline="\n")
print(f"written: {SRC.relative_to(ROOT)} 行数 = {t.count(chr(10)) + 1}")
