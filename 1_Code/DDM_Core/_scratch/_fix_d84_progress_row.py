# -*- coding: utf-8 -*-
"""把 D84 的进度行补成 5 列（日期 | Stage | 本轮做了什么 | 产出文件 | 下一步）。

教训：进度表是 5 列，我按 3 列写 ⇒ check_table_integrity 报 mangled_rows=1。
和 D81 那次「手工拼表格行少 2 列」是同一个错，这已是第二次，所以这次直接按列补全。
"""
import io
import sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8", newline="").read()

old = ("| 2026-10-18 | **6**（v4.6 修法的契约测试 → D84） | **把「onset 之前的键不算反应」从注释变成断言**："
       "`check_kq_floor.m` 从程序原文抽取三个函数、十例全过（10/10），并用 C2 反向证明测试有牙；"
       "顺带抓出测试自身的坑 —— 桩目录必须压在 PTB 之前，否则 `KbName('f')` 拿到 70（首轮 5/10，只有 Esc 绿）；"
       "`check_full_session.py` 由 26 增到 **29/29**。 |")

new = ("| 2026-10-18 | **6**（v4.6 修法的契约测试 → D84） | **把「onset 之前的键不算反应」从注释变成断言**："
       "`check_kq_floor.m` 从程序原文抽取 `kqFirstPressUntil`/`kqScan`/`resolveEscKeyCode` 再测（不复刻逻辑），"
       "十例全过（10/10），C2 是反向用例（不传 floor 时必须返回同一键 ⇒ 证明测试有牙）；"
       "首轮 **5/10**，根因是 `PsychStartup` 把 PTB 的 `KbName` 放在 path 最前、桩用 `-end` 加在后面 ⇒ "
       "`KbName('f')` 返回 70 而非 6，`f/j` 永远匹配不上（Esc=27 两种口径一致才绿）；改成桩 `-begin` 后 10/10。 "
       "| `test/check_kq_floor.m`（218 行）、`test/_kq_floor_result.txt`、`test/check_full_session.py`（26 → 29 项） "
       "| 无（开发者回归，不进现场六条；主试手册仍是 v2.5 六条） |")

assert src.count(old) == 1, "命中 %d 次" % src.count(old)
io.open(p, "w", encoding="utf-8", newline="\n").write(src.replace(old, new))
print("patched")
