#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_apply_d83_preonset.py —— D83：把「onset 之前的按键」挡在反应窗口之外（Exp_Design_Formal.m v4.6）。

问题（2026-10-18 60 Hz 实机数据实测）：576 个正式试次里有 **5 个**（0.87%）
`stimulus_dur_actual` 只有 0–1 帧（6–14 ms）、`premature_press=1`、`Response=NA`、`timeout=1`。
成因：注视期按键是在 `kqCountPresses()` 处读的，而它离真正的刺激 onset 隔着
Screen('Flip') 的 vsync 等待（最长约一帧 ≈ 16.7 ms）。在「数完 → 真正上屏」这段缝隙里
按下的键不会被抢按计数看到，却会被刺激期的 `kqFirstPressUntil` 立刻取走 ⇒
刺激被这个"旧键"在 0–1 帧内敲掉，本试次被误判成漏答（漏答率是核心因变量，因此必须修）。

修法（不改时序、不改列）：
  1. `kqFirstPressUntil(deadline, tFloor)`：只接受 `tFloor < 时间戳 <= deadline` 的按键；
  2. 四个调用点（练习/正式 × 刺激期/反应窗口）都把 `stimulusFlipTime` 作为 tFloor 传进去；
  3. 这些"早于 onset"的键留在队列里不消费，由下一试次开头的 `KbQueueFlush()` 清掉
     （正式段 :888、练习段开头各已有的 flush）。

幂等；写入统一 newline="\\n"。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
SRC = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "Exp_Design_Formal.m"

V46_BLOCK = """% ★★ v4.6 本次修正（2026-10-18，60 Hz 实机数据实测发现；判据见 exp_Check/check_stage1_acceptance.py）★★
%   (#1) 「onset 之前的按键」会敲掉刺激：注视期抢按是在 kqCountPresses() 处读的，而它到真正的
%        刺激 onset 之间隔着 Screen('Flip') 的 vsync 等待（最长约一帧）。在这条缝隙里按下的键
%        不会被抢按计数看到，却会被刺激期的 kqFirstPressUntil 立刻取走 ⇒ 刺激在 0–1 帧内被敲掉
%        （stimulus_dur_actual 6–14 ms），本试次被误判为漏答 —— 实测 5/576 = 0.87%。
%        漏答率是本设计的核心因变量，因此必须修，不能当噪声。
%        修法：kqFirstPressUntil(deadline, tFloor) 只接受 tFloor < t <= deadline 的按键；
%              四个调用点（练习/正式 × 刺激期/反应窗口）传 stimulusFlipTime 作 tFloor。
%        这些早于 onset 的键不消费、留在队列里，由下一试次开头的 KbQueueFlush() 清掉。
%   ⚠ 教训：**"抢按已经被计数"不等于"抢按不会影响反应"**——计数与消费是两件事；
%      凡是以时间戳划分的窗口，边界都必须用同一个 tFloor 显式裁一次。
%
"""

# 四个调用点：刺激期 / 反应窗口（练习用 T, W；正式用 Ttrial, Wtrial）
CALL_SITES = [
    ("[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + T);",
     "[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + T, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键"),
    ("[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + W);",
     "[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + W, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键"),
    ("[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + Ttrial);",
     "[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + Ttrial, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键"),
    ("[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + Wtrial);",
     "[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + Wtrial, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键"),
]

OLD_SIG = "function [key, when, nEsc] = kqFirstPressUntil(deadline)"
NEW_SIG = "function [key, when, nEsc] = kqFirstPressUntil(deadline, tFloor)"

OLD_DOC = """    %   nEsc : 本区间内 Esc 的按下次数（>0 时由调用方调用 escAbort）
"""
NEW_DOC = """    %   nEsc : 本区间内 Esc 的按下次数（>0 时由调用方调用 escAbort）
    %   tFloor: 【可选】下界（绝对 getsecs 秒）。只接受 tFloor < 时间戳 <= deadline 的按键。
    %           ★ v4.6：反应窗口的物理起点是刺激 onset，而 onset 之前按下的键（注视末梢的抢按，
    %           隔着一次 vsync 等待才有机会被读到）不属于本试次反应。传 stimulusFlipTime 即可
    %           把这类键挡在窗口之外，否则它们会把刺激在 0–1 帧内敲掉、把试次变成漏答。
"""

OLD_SCAN_CALL = "[key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode);"
NEW_SCAN_CALL = "[key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode, tFloor);"

OLD_SCAN_SIG = "function [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode)"
NEW_SCAN_SIG = "function [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode, tFloor)"

OLD_COND = """        elseif isempty(key) && (idx(m) == fCode || idx(m) == jCode) ...
                && firstPress(idx(m)) <= deadline"""
NEW_COND = """        elseif isempty(key) && (idx(m) == fCode || idx(m) == jCode) ...
                && firstPress(idx(m)) > tFloor && firstPress(idx(m)) <= deadline"""


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    orig_lines = len(text.split("\n"))
    changed = 0

    # 1. 头注 v4.6 块（幂等）
    if "v4.6 本次修正" in text:
        print("[SKIP] v4.6 头注：已存在")
    else:
        anchor = "% ★★ v4.5 本次修正"
        assert text.count(anchor) == 1, f"v4.5 头注锚点命中 {text.count(anchor)} 次"
        text = text.replace(anchor, V46_BLOCK + anchor)
        print("[OK] v4.6 头注：已插入")
        changed += 1

    # 2. 四个调用点
    for old, new in CALL_SITES:
        n = text.count(old)
        assert n == 1, f"调用点 {old!r} 命中 {n} 次（应为 1）"
        if new.strip() in text:
            print(f"[SKIP] 调用点：已改 ({old[35:60]}…)")
            continue
        text = text.replace(old, new)
        print(f"[OK] 调用点：{old[35:60]}… → 加 tFloor")
        changed += 1

    # 3. 函数签名 + 文本
    for old, new, label in [
        (OLD_SIG, NEW_SIG, "kqFirstPressUntil 签名"),
        (OLD_SCAN_CALL, NEW_SCAN_CALL, "kqScan 调用（2 处）"),
        (OLD_SCAN_SIG, NEW_SCAN_SIG, "kqScan 签名"),
        (OLD_COND, NEW_COND, "kqScan 边界条件"),
        (OLD_DOC, NEW_DOC, "kqFirstPressUntil 文档"),
    ]:
        if new.strip() in text:
            print(f"[SKIP] {label}：已改")
            continue
        n = text.count(old)
        assert n in (1, 2), f"{label} 命中 {n} 次"
        text = text.replace(old, new)
        print(f"[OK] {label}：{n} 处")
        changed += n

    # 4. nargin 兜底
    if "if nargin < 2" in text:
        print("[SKIP] nargin 兜底：已存在")
    else:
        anchor = "    key = ''; when = NaN; nEsc = 0;\n    fCode = KbName('f');"
        assert text.count(anchor) == 1
        text = text.replace(anchor, "    if nargin < 2 || isempty(tFloor), tFloor = -Inf; end\n" + anchor)
        print("[OK] nargin 兜底：已插入")
        changed += 1

    if changed:
        SRC.write_text(text, encoding="utf-8", newline="\n")
        print(f"\n写入 {SRC.name}：{orig_lines} → {len(text.split(chr(10)))} 行")
    else:
        print("\n无改动。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
