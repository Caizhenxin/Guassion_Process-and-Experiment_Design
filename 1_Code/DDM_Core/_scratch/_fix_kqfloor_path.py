# -*- coding: utf-8 -*-
"""把 check_kq_floor.m 的 addpath 顺序改成「桩在前、受控目录再压最前」。

根因（D83d）：PsychStartup 已把 PTB 的 KbName 塞到 path 最前，桩用 '-end' 加在后面，
于是 KbName('f') 返回 70（PTB 口径）而不是桩的 6，f/j 永远匹配不上 ——
表现为 C2/C3/C5/C7/C10 全红、只有 Esc（27，两种口径一致）绿。
"""
import io
import sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8", newline="").read()

old = "addpath(tmpDir, '-begin');\naddpath(stubsDir, '-end');"
new = (
    "% 顺序要紧：PsychStartup 已把 PTB 的 KbName 放到 path 最前，\n"
    "% 若桩用 '-end' 加在后面，KbName('f') 会拿到 70（PTB 口径）而不是桩的 6，\n"
    "% f/j 就永远匹配不上（D83d 实测：只有 Esc=27 两种口径一致才绿）。\n"
    "addpath(stubsDir, '-begin');\n"
    "addpath(tmpDir, '-begin');"
)
assert src.count(old) == 1, "命中 %d 次" % src.count(old)
io.open(p, "w", encoding="utf-8", newline="\n").write(src.replace(old, new))
print("patched")
