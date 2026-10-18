# -*- coding: utf-8 -*-
"""修 check_ask_info.m 的两类 MATLAB 语法/语义错误：
   1) `w = st('warns'){1};`         —— 不能对函数返回值直接 `{}` 索引
   2) `any(contains(st('log'),…))`  —— contains 作用于 cell 返回 cell，any(cell) 会报错
"""
from pathlib import Path

P = Path(r"1_Code/Experiment/exp_matlab/test/check_ask_info.m")
t = P.read_text(encoding="utf-8")

t = t.replace("""if numel(st('warns')) >= 1
    w = st('warns'){1};""",
              """if numel(st('warns')) >= 1
    W = st('warns');
    w = W{1};""")

t = t.replace("""ok('S4-2 说明含「性别」', numel(st('warns')) == 1 && contains(st('warns'){1}, '性别'));""",
              """W = st('warns');
ok('S4-2 说明含「性别」', numel(W) == 1 && contains(W{1}, '性别'));""")

t = t.replace("""ok('S5-2 说明含「年龄」', numel(st('warns')) == 1 && contains(st('warns'){1}, '年龄'));""",
              """W = st('warns');
ok('S5-2 说明含「年龄」', numel(W) == 1 && contains(W{1}, '年龄'));""")

t = t.replace("""ok('S6-2 说明含「惯用手」', numel(st('warns')) == 1 && contains(st('warns'){1}, '惯用手'));""",
              """W = st('warns');
ok('S6-2 说明含「惯用手」', numel(W) == 1 && contains(W{1}, '惯用手'));""")

t = t.replace("""ok('S7-2 说明含「编号」', numel(st('warns')) == 1 && contains(st('warns'){1}, '编号'));""",
              """W = st('warns');
ok('S7-2 说明含「编号」', numel(W) == 1 && contains(W{1}, '编号'));""")

n_log = t.count("any(contains(st('log')")
t = t.replace("any(contains(st('log'), '本组 P = 0'))", "logged(st, '本组 P = 0')")
t = t.replace("any(contains(st('log'), '组4 P120'))", "logged(st, '组4 P120')")
t = t.replace("any(contains(st('log'), '本组 P = 32'))", "logged(st, '本组 P = 32')")
t = t.replace("any(contains(st('log'), '本组 P = 8'))", "logged(st, '本组 P = 8')")
t = t.replace("any(contains(st('log'), '本组 P = 120'))", "logged(st, '本组 P = 120')")

# 插入 logged 辅助函数（放在 ok/check_case 之后、第一个用例之前）
anchor = "fprintf('== check_ask_info：exp_ask_subject_info 无屏幕自测 ==\\n');"
helper = (
    "    function tf = logged(st, pat)\n"
    "        % 回显日志里是否出现过某段文字（fprintf 被 hooks 截获后存在 st('log')）\n"
    "        L = st('log');\n"
    "        tf = false;\n"
    "        for ii = 1:numel(L)\n"
    "            if contains(L{ii}, pat)\n"
    "                tf = true;\n"
    "                return;\n"
    "            end\n"
    "        end\n"
    "    end\n\n"
)
assert anchor in t
t = t.replace(anchor, helper + anchor, 1)

P.write_text(t, encoding="utf-8", newline="\n")
print(f"patched: cell-index fix ×5, any(contains) → logged ×{n_log}")
print("remaining 'any(contains' =", t.count("any(contains"))
