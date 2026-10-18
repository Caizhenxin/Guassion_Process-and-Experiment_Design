#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_consent_pack.py —— 检查「被试招募与知情同意包」没被改坏（零依赖）

用法：
    python -X utf8 -u 1_Code\\Experiment\\exp_Check\\check_consent_pack.py
    python -X utf8 -u 1_Code\\Experiment\\exp_Check\\check_consent_pack.py --self-test

为什么需要这个脚本
------------------
招募公告与知情同意书是**唯一会离开代码库、直接进入被试手里的材料**。
它们出错的方式和代码不同：不是崩溃，而是
  (1) 数字与设计脱钩（写了 9 组、30 分钟、>60 Hz 也行）；
  (2) 占位符被"顺手删掉"而不是填掉（伦理批号凭空消失）；
  (3) 关键提醒被删（「刺激很短、看不清是正常的」「不要解释假设」）。
这三种都不会报错，只会让某一批数据在事后变得不可用。所以用判据盯住。

D82 口径：4 组（P = 0/8/32/120）、576 正式试次、3 段、60 秒联结学习、
最短刺激 33 毫秒、F/J 两键、约 25 分钟（纯任务约 17 分钟）、编号 group<1-4>_subject<n>。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "Stage6_被试招募与知情同意包.md"

# ---- 必须存在的章节（正则，容忍编号变化）----
REQUIRED_SECTIONS = [
    ("招募公告", r"##\s*\d*\.?\s*招募公告"),
    ("知情同意书", r"##\s*\d*\.?\s*知情同意书"),
    ("被试登记表", r"##\s*\d*\.?\s*被试登记表"),
    ("排期表", r"##\s*\d*\.?\s*排期表"),
    ("口述脚本", r"##\s*\d*\.?\s*主试口述脚本"),
    ("采集前检查清单", r"##\s*\d*\.?\s*采集前检查清单"),
]

# ---- 与 D4 设计必须一致的数字（写成"必须出现"的原文片段）----
DESIGN_FACTS = [
    ("正式试次数 576", "576"),
    ("分 3 段", "3 段"),
    ("联结学习 60 秒", "60 秒"),
    ("最短刺激 33 毫秒", "33 毫秒"),
    ("两键 F / J", "F"),
    ("总时长约 25 分钟", "25 分钟"),
    ("纯任务约 17 分钟", "17 分钟"),
    ("被试间 4 组", "4 组"),
    ("编号样例", "group1_subject1"),
]

# ---- 必须保留的"警告式"句子（删掉就失去保护作用）----
MUST_KEEP = [
    ("看不清是正常的（防被试要求重来）", "看不清是正常"),
    ("不要解释假设（防改变策略）", "不要解释"),
    ("60.004 Hz 屏（防换屏）", "60.004"),
    ("可随时退出（伦理必需）", "任何时刻"),
    ("匿名编号（伦理必需）", "不记录姓名"),
]

# ---- 必须仍以占位符形式存在（否则=被谁删了，而不是填了）----
PLACEHOLDERS = ["【", "】"]

# ---- 绝对不该出现的旧口径 ----
FORBIDDEN = [
    (r"9\s*组", "旧口径：9 组"),
    (r"无掩蔽组", "旧口径：无掩蔽组"),
    (r"组\s*7", "旧口径：组 7"),
    (r"200\s*人", "旧规模：200 人"),
    (r"EEG|脑电|电极", "本实验不测脑电"),
    (r"120\s*分钟", "时长写错"),
    (r">=\s*60\s*Hz|≥\s*60\s*Hz|至少\s*60\s*Hz", "刷新率前提被写松（必须是 60.004 Hz 那块屏）"),
]


def _read(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def check_text(text: str) -> tuple[list[tuple[str, str, str]], int, int]:
    """返回 (结果列表, 通过数, 总数)。每项 = (状态, 名称, 说明)。"""
    out: list[tuple[str, str, str]] = []

    for name, pat in REQUIRED_SECTIONS:
        ok = re.search(pat, text) is not None
        out.append(("PASS" if ok else "FAIL", f"章节：{name}", "" if ok else f"未找到 /{pat}/"))

    for name, needle in DESIGN_FACTS:
        ok = needle in text
        out.append(("PASS" if ok else "FAIL", f"数字：{name}", "" if ok else f"缺少「{needle}」"))

    for name, needle in MUST_KEEP:
        ok = needle in text
        out.append(("PASS" if ok else "FAIL", f"提醒：{name}", "" if ok else f"缺少「{needle}」"))

    has_ph = all(p in text for p in PLACEHOLDERS)
    out.append((
        "PASS" if has_ph else "FAIL",
        "占位符仍在（机构项必须人工填写）",
        "" if has_ph else "「【】」被删掉了：请确认是真的填了，而不是把占位符抹掉",
    ))

    for pat, why in FORBIDDEN:
        hit = re.search(pat, text)
        out.append(("FAIL" if hit else "PASS", f"禁用口径：{why}", f"命中「{hit.group(0)}」" if hit else ""))

    n_pass = sum(1 for s, _, _ in out if s == "PASS")
    return out, n_pass, len(out)


def self_test() -> int:
    """反例：删掉关键提醒 / 改成 9 组 / 抹掉占位符，都必须被判红。"""
    good = _read(PACK) if PACK.exists() else ""
    if not good:
        print("[SELF-TEST] 找不到包文件，无法自测")
        return 1

    cases = [
        ("干净副本应全过", good, 0),
        ("删掉「看不清是正常的」", good.replace("看不清是正常的", "显示有点快"), 1),
        ("改成 9 组", good + "\n本实验 9 组被试。", 1),
        ("抹掉占位符", good.replace("【", "").replace("】", ""), 1),
        ("放宽刷新率", good + "\n只要 ≥ 60 Hz 的屏都行。", 1),
    ]
    bad = 0
    for label, text, _ in cases:
        _, _, total = check_text(text)
        _, n_pass, _ = check_text(text)
        fails = total - n_pass
        expect_fail = (label != "干净副本应全过")
        ok = (fails > 0) == expect_fail
        print(f"[{'PASS' if ok else 'FAIL'}] self-test: {label}（未通过 {fails} 项）")
        if not ok:
            bad += 1
    print(f"\n{'-' * 52}\n[{'PASS' if bad == 0 else 'FAIL'}] 自测 {len(cases) - bad}/{len(cases)}")
    return 0 if bad == 0 else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    if not PACK.exists():
        print(f"[FAIL] 找不到 {PACK}")
        return 1

    text = _read(PACK)
    results, n_pass, total = check_text(text)

    print(f"检查：{PACK.name}（{len(text.splitlines())} 行）\n")
    for status, name, why in results:
        print(f"[{status}] {name}" + (f" —— {why}" if why else ""))

    print(f"\n{'-' * 52}")
    print(f"== 通过 {n_pass} / 未通过 {total - n_pass} ==")
    return 0 if n_pass == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
