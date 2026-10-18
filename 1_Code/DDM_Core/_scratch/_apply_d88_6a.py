# -*- coding: utf-8 -*-
"""D88：回填 Stage 1 §6-A（用户 2026-10-18 控制台确认预加载回显）。"""
import io
import sys
from pathlib import Path

STAGE1 = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "Stage1_技术验证记录.md"


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)


s = read(STAGE1)

old1 = "| 预加载回显出现且只出现一次 | ✅ | |"
new1 = ("| 预加载回显出现且只出现一次 | ✅ | ✅ **2026-10-18，v4.6，控制台亲见**：`掩蔽纹理预加载完成：self 5 张、stranger 5 张（Stage 1 修正 #1）`。"
        "该行是 `Exp_Design_Formal.m:365` 的 `fprintf`，位于**开场的一次性预加载段**（`:344-368`，两个 `for` 之后、"
        "联结阶段指导语之前），不在任何试次循环里 ⇒ 每次启动只打印一次 |")

old2 = "| 首个试次之前没有 `imread` 报错 | ✅ | |"
new2 = ("| 首个试次之前没有 `imread` 报错 | ✅ | ✅ 该场 576 个正式试次跑完并正常落盘（`EXP_data_group1_99.csv`），"
        "过程中未出现 `imread` / `Screen('MakeTexture')` 报错——这类错误会直接中止程序 |")

old3 = "**`6-A` 与 `6-E` 仍空**。"
new3 = "**`6-A` 已回填（D88，2026-10-18 控制台确认）**，只剩 **`6-E`**。"

for old, new in ((old1, new1), (old2, new2), (old3, new3)):
    if new in s:
        print("SKIP", old[:20])
        continue
    if s.count(old) != 1:
        sys.exit("HIT %d != 1 :: %s" % (s.count(old), old[:40]))
    s = s.replace(old, new)
    print("OK", old[:24])

write(STAGE1, s)
print("done")
