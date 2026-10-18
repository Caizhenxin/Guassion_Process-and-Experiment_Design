# -*- coding: utf-8 -*-
"""补上主计划三条新行的第 4 列（决策表/进度表都是 4 列，前一轮只写了 3 列）。"""
import io
from pathlib import Path

P = Path("5_Reference/08_工作流/工作流_主计划.md")
t = io.open(P, encoding="utf-8").read()

pairs = [
    ("（2.5 s / 2.5 s）；⑦ 口径更正：此前口头说的「练习 4/12/36/124」是错的，设计是 **max(4, P) = 4/8/32/120**。 |",
     "（2.5 s / 2.5 s）；⑦ 口径更正：此前口头说的「练习 4/12/36/124」是错的，设计是 **max(4, P) = 4/8/32/120**。 "
     "| 用户侧：换 v4.9 重跑一场（组 1 亦可），确认练习行 = 4、正式行 = 576，再判 S6-1/S6-5 |"),
    ("⑤ 边界：去重只解决「同 trialID 多行」；「一次运行内确实少行」仍会红。 |",
     "⑤ 边界：去重只解决「同 trialID 多行」；「一次运行内确实少行」仍会红。 "
     "| 用户侧：不必重跑程序；把 `qc_group.py` 对新数据跑一遍即得干净判定 |"),
    ("与「qc 把跑两遍判成试次不符」（D94）。本场**不计入 Pilot N**。 |",
     "与「qc 把跑两遍判成试次不符」（D94）。本场**不计入 Pilot N**。 "
     "| 用户侧：换 v4.9 重跑同一名被试，或直接招新被试；这一场的 CSV 留着当「工具回归样本」 |"),
]

for old, new in pairs:
    assert t.count(old) == 1, f"命中 {t.count(old)}：{old[:30]}"
    t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("ok, lines =", len(t.splitlines()))
