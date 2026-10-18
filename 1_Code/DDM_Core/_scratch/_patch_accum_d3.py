# -*- coding: utf-8 -*-
"""D2–D6 静态守卫要先剥掉注释行（v4.4 头注里就提到了 `data = table()` 这个旧写法）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\test\check_data_accum.m")
t = p.read_text(encoding="utf-8")

old = """src = fileread(srcPath);
check('D2 用 exp_new_data 建容器', contains(src, 'data = exp_new_data(25);'), '缺 exp_new_data(25)');
check('D3 不再有 data = table()', ~contains(src, 'data = table()'), '仍有 data = table()');
check('D4 不再访问 data.Properties', ~contains(src, 'data.Properties'), '仍有 data.Properties');
check('D5 保存前用 exp_data_table 转换', contains(src, 'exp_data_table(data, columnNames)'), ...
      '缺 exp_data_table(data, columnNames)');
check('D6 仍有行数自检 warning', contains(src, 'Exp_Design_Formal:rowCount'), '缺 rowCount 自检');"""

new = """srcLines = splitlines(string(fileread(srcPath)));
% 只查可执行代码：剥掉注释行（头注里会引用 `data = table()` 这个旧写法，不能算命中）
isComment = startsWith(strtrim(srcLines), '%');
code = strjoin(cellstr(srcLines(~isComment)), newline);
check('D2 用 exp_new_data 建容器', contains(code, 'data = exp_new_data(25);'), '缺 exp_new_data(25)');
check('D3 不再有 data = table()', ~contains(code, 'data = table()'), '仍有 data = table()');
check('D4 不再访问 data.Properties', ~contains(code, 'data.Properties'), '仍有 data.Properties');
check('D5 保存前用 exp_data_table 转换', contains(code, 'exp_data_table(data, columnNames)'), ...
      '缺 exp_data_table(data, columnNames)');
check('D6 仍有行数自检 warning', contains(code, 'Exp_Design_Formal:rowCount'), '缺 rowCount 自检');"""

if new in t:
    print("已打过")
elif old in t:
    p.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
    print("patched")
else:
    print("MISS")
