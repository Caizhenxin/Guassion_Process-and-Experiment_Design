# -*- coding: utf-8 -*-
"""清掉 check_ask_info.m 的 6 条 Code Analyzer 提示：
   L134 未使用的 st       → [hooks, ~]
   L181 父函数循环变量 k 与嵌套函数共用 → 改名 kk / kd / kc
   L204/213/220 %#ok 指令位置警告 → 改为文件级 %#ok<*INUSD>
"""
from pathlib import Path

P = Path(r"1_Code/Experiment/exp_matlab/test/check_ask_info.m")
t = P.read_text(encoding="utf-8")

t = t.replace("[hooks, st] = make_hooks({{}}, {''});", "[hooks, ~] = make_hooks({{}}, {''});")

t = t.replace("    for k = 1:numel(fail_msg)\n        fprintf('  - %s\\n', fail_msg{k});",
              "    for kk = 1:numel(fail_msg)\n        fprintf('  - %s\\n', fail_msg{kk});")

t = t.replace("function out = fake_inputdlg(varargin)   %#ok<INUSD>",
              "function out = fake_inputdlg(varargin)")
t = t.replace("function h = fake_warndlg(msg, varargin)   %#ok<INUSD>",
              "function h = fake_warndlg(msg, varargin)")
t = t.replace("function out = fake_input(varargin)   %#ok<INUSD>",
              "function out = fake_input(varargin)")

t = t.replace("            k = st('di') + 1;\n            st('di') = k;\n            if k > numel(dialogs)",
              "            kd = st('di') + 1;\n            st('di') = kd;\n            if kd > numel(dialogs)")
t = t.replace("inputdlg 被调用第 %d 次，但脚本只准备了 %d 个回包', k, numel(dialogs));",
              "inputdlg 被调用第 %d 次，但脚本只准备了 %d 个回包', kd, numel(dialogs));")
t = t.replace("            out = dialogs{k};", "            out = dialogs{kd};")
t = t.replace("            k = st('ci') + 1;\n            st('ci') = k;\n            if k > numel(confirms)",
              "            kc = st('ci') + 1;\n            st('ci') = kc;\n            if kc > numel(confirms)")
t = t.replace("                out = confirms{k};", "                out = confirms{kc};")

# 文件级抑制：未使用的输入参数（假的 inputdlg/warndlg/input 都不需要真实入参）
lines = t.split("\n")
assert lines[0].startswith("function check_ask_info")
lines.insert(1, "%#ok<*INUSD>   % 假的 inputdlg/warndlg/input 用不到真实入参，全文件抑制该类提示")
t = "\n".join(lines)

P.write_text(t, encoding="utf-8", newline="\n")
print("patched check_ask_info.m")
