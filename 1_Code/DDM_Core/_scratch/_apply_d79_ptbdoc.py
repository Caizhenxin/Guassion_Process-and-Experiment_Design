# -*- coding: utf-8 -*-
"""_apply_d79_ptbdoc.py —— PTB 配置说明：程序升 v4.5、手册 v2.3、补齐 test/ 文件行"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "PTB免费版配置说明.md"

s = P.read_text(encoding="utf-8")
n = 0
errs: list[str] = []


def rep(old: str, new: str, name: str) -> None:
    global s, n
    if old not in s:
        if new in s:
            print(f"[跳过] {name}")
            return
        errs.append(name)
        return
    s = s.replace(old, new, 1)
    n += 1
    print(f"[替换] {name}")


rep("正式实验程序 **v4.4**", "正式实验程序 **v4.5**", "程序版本")
rep(
    "主试培训手册（v2.2，D4 口径；含 §6.6「已知崩溃：第一个未响应试次」）",
    "主试培训手册（v2.3，D4 口径；§3.2 六条自测、§6.6「已知崩溃」）",
    "手册版本",
)
rows = (
    "| `test/check_ask_info.m` | 弹窗路径级自测（40 项，填 7 → 拒 → 改 1 → 通过） |\n"
    "| `test/stubs/` | **24 个 PTB 桩**（虚拟时钟 + 按键剧本），让主程序在无屏幕、无 PTB 的环境下整场跑完 |\n"
    "| `test/run_full_session.m` | 整场冒烟驱动（函数；`run_full_session(groupID, subjectID)`） |\n"
    "| `test/runbatch_full_session.m` | 整场冒烟命令行入口（写 UTF-8 日志，末行 `SUMMARY pass=27 fail=0`） |\n"
    "| `test/check_full_session.py` | 冒烟判据自检（23 项，含「把修正拿掉必须失败」的反例） |\n"
)
rep("| `test/check_input_validation.m` | 上述校验的无屏幕自测（51 项） |\n",
    "| `test/check_input_validation.m` | 上述校验的无屏幕自测（51 项） |\n" + rows,
    "test/ 新增文件行")

if errs:
    print("\n=== 失败 ===")
    for e in errs:
        print("  ✗", e)
    sys.exit(1)

P.write_text(s, encoding="utf-8", newline="\n")
print(f"\n替换 {n} 处，总行数 {len(s.splitlines())}")
