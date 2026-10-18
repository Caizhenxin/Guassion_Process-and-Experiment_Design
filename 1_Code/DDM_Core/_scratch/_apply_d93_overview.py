# -*- coding: utf-8 -*-
"""§2 阶段总览的两处过时数据（Stage 1 的程序版本、Stage 6 的最新一场）。"""
import io
from pathlib import Path

P = Path("5_Reference/08_工作流/工作流_主计划.md")
t = io.open(P, encoding="utf-8").read()

old1 = "（现 **v4.7**，1460 行）"
new1 = "（现 **v4.9**，1494 行）"
assert t.count(old1) == 1, t.count(old1)
t = t.replace(old1, new1)

old2 = "**不计入 N=8**"
new2 = ("**不计入 N=8**；2026-10-18 又收回「组 1 被试 1」的 v4.8 一场（`EXP_data_group1_1.csv`），"
        "四条链路全通但正确率 0.440（87 份历史最低 2%）、S6-1/S6-5 红 ⇒ 也不计入，"
        "却换出两个真缺陷：组 1 练习段 0 试次（D93，程序已升 v4.9）、QC 把「跑了两遍」判成试次不符（D94）")
assert t.count(old2) == 1, t.count(old2)
t = t.replace(old2, new2)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("ok, lines =", len(t.splitlines()))
