# -*- coding: utf-8 -*-
"""更新 check_manual_d4.py：v4.3 把弹窗循环搬进 exp_ask_subject_info.m，
   判据要从「脚本里调用 exp_check_subject_info」改成「脚本 → exp_ask_subject_info
   → exp_check_subject_info」这条链，并钉住新文件与它的自测。
"""
from pathlib import Path

P = Path(r"1_Code/Experiment/exp_matlab/test/check_manual_d4.py")
t = P.read_text(encoding="utf-8")

old = '''    check("A 程序", "调用 exp_check_subject_info 做弹窗校验",
          "exp_check_subject_info(userInput, P_groups)" in prog)'''
new = '''    check("A 程序", "调用 exp_ask_subject_info 收集信息（v4.3 抽出成函数，便于无屏幕自测）",
          "exp_ask_subject_info(P_groups)" in prog)'''
assert old in t, "A 组锚点未命中"
t = t.replace(old, new)

old_b = '''    # ---------------- B. 校验函数 ----------------'''
new_b = '''    # ---------------- A2. 弹窗循环函数（v4.3） ----------------
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

    # ---------------- B. 校验函数 ----------------'''
assert old_b in t
t = t.replace(old_b, new_b, 1)

P.write_text(t, encoding="utf-8", newline="\n")
print("checker patched")
