# -*- coding: utf-8 -*-
"""把 PTB 说明里的程序/手册版本同步到 v4.9 / v2.8（D93 落纸的尾巴）。"""
import io
from pathlib import Path

P = Path("1_Code/Experiment/exp_matlab/PTB免费版配置说明.md")
t = io.open(P, encoding="utf-8").read()

a = "正式实验程序 **v4.8**（掩蔽纹理按程序目录解析、启动自检 10 张 PNG；数据仍写当前目录）"
b = ("正式实验程序 **v4.9**（掩蔽纹理按程序目录解析、启动自检 10 张 PNG；数据仍写当前目录；"
     "练习段 `max(4, P)`，组 1 也有 4 个兜底练习）")
assert t.count(a) == 1, f"v4.8 行命中 {t.count(a)}"
t = t.replace(a, b)

c = "主试培训手册（**v2.7**，D4 口径"
d = "主试培训手册（**v2.8**，D4 口径；练习试次 `max(4, P)`"
assert t.count(c) == 1, f"手册行命中 {t.count(c)}"
t = t.replace(c, d)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("PTB doc ok, lines =", len(t.splitlines()))
