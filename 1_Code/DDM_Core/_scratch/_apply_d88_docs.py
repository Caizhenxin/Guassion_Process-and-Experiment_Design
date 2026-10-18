# -*- coding: utf-8 -*-
"""D88 落纸：主计划决策行 + 进度行 + README §9 第 72 项。"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)


D88 = ("| **D88** | 2026-10-18 | ✅ **Stage 1 §6-A 回填：预加载回显由用户控制台亲见，六张表只剩 6-E**。"
       "① 用户报告：启动 v4.6 时控制台出现 `掩蔽纹理预加载完成：self 5 张、stranger 5 张（Stage 1 修正 #1）`；"
       "② 该行是 `Exp_Design_Formal.m:365` 的 `fprintf`，位于开场**一次性预加载段**（`:344-368`，两个 `for` 之后、联结阶段指导语之前），"
       "不在试次循环里 ⇒ 每次启动只打印一次，「出现在指导语之前」这一点由代码位置保证；"
       "③ 第二行判据（首个试次前无 `imread` 报错）由该场 576 试次跑完并落盘反证（`imread`/`MakeTexture` 报错会中止程序）；"
       "④ 仍缺：**6-E**（刺激内与刺激后按键的延时可比性），它需要在**真被试** Pilot 上比对两类按键的 RT 分布，"
       "本场（RT 中位 0.127 s、RT<T 43.9%）只能说明仪器能记到两类键，不能作为可比性证据 | "
       "`5_Reference/08_工作流/Stage1_技术验证记录.md`（§6-A 两行 + §7 第 5 条状态）、主计划 D88、README §9 第 72 项 | "
       "① 6-E 待真被试 Pilot；② 之后 Stage 1 可宣布完成、进 Stage 6 |\n")

PROG = ("| 2026-10-18 | **1/7**（6-A 回填 → D88） | **把 6-A 从「见过一行字」变成「知道它为什么只出现一次」**：定位到 `Exp_Design_Formal.m:365` 的 `fprintf` 在开场一次性预加载段内（`-368` 结束、指导语之前），"
        "不在试次循环 ⇒ 次数与位置都由代码保证；第二行判据用「576 试次跑完且落盘」反证无 `imread` 报错 | Stage1 §6-A、主计划 D88 | 只剩 6-E（需真被试 Pilot） |\n")

ITEM = ("| 72 | ✅ **Stage 1 §6-A 回填：预加载回显亲见（D88）** | 用户控制台确认 `掩蔽纹理预加载完成：self 5 张、stranger 5 张`；"
        "该 `fprintf` 在 `Exp_Design_Formal.m:365` 的一次性预加载段内（指导语之前、不在试次循环）⇒ 每次启动只打印一次。§6 只剩 6-E。 |\n")


def insert_after(path, anchor_prefix, newline_text, marker):
    s = read(path)
    if marker in s:
        print("SKIP", path.name, marker[:24])
        return
    lines = s.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    if len(idx) != 1:
        sys.exit("anchor %r not unique: %d" % (anchor_prefix, len(idx)))
    lines.insert(idx[0] + 1, newline_text.rstrip("\n"))
    write(path, "\n".join(lines))
    print("OK", path.name, "->", marker[:24])


insert_after(PLAN, "| **D87** |", D88, "| **D88** |")
insert_after(PLAN, "| 2026-10-18 | **6**（检查器自身缺陷 → D87） |", PROG, "（6-A 回填 → D88）")
insert_after(README, "| 71 | ✅ ", ITEM, "| 72 | ✅ ")
print("done")
