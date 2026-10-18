#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_apply_d83_docs.py —— D83 落纸：主计划决策/进度/文件行 + Stage1 §6 回填 + 手册 v2.5 + PTB 说明版本。

全部幂等，写入统一 newline="\\n"（D81 教训：edit 工具曾把文件写回 CRLF）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
WF = ROOT / "5_Reference" / "08_工作流"
PLAN = WF / "工作流_主计划.md"
S1 = WF / "Stage1_技术验证记录.md"
MAT = ROOT / "1_Code" / "Experiment" / "exp_matlab"
MAN = MAT / "主试培训手册_Exp_Design_Formal.md"
PTB = MAT / "PTB免费版配置说明.md"

D83_ROW = (
    "| **D83** | 2026-10-18 | ❗ **60 Hz 实机数据把「onset 之前的按键」这条缝抓出来了：5/576 试次被旧键敲掉刺激、误判成漏答；程序升 v4.6**。"
    "① 触发：用户在实验室同类机（实测 **59.111 Hz**）跑完 576 试次（`EXP_data_group1_1.csv` / `exp_group1_subject1.txt`），"
    "回放 Stage 1 判据：**6-B 279 例**刺激期按键 ✅、**6-D 5/5** ✅、环境门 ✅（±1 Hz 内），但 **6-C 有 5 行**"
    "`stimulus_dur_actual` 只有 0–1 帧（6–14 ms），且 `premature_press = 1`、`Response = NA`、`timeout = 1`。"
    "② 根因：注视期抢按是在 `kqCountPresses()`（`:964`）处读的，而它到真正 onset 之间隔着 `Screen('Flip')` 的 vsync 等待（最长约一帧）；"
    "**这段缝隙里按下的第二个键不会进抢按计数，却会被刺激期的 `kqFirstPressUntil` 立刻取走** ⇒ 刺激在 0–1 帧内被敲掉，本试次变成漏答。"
    "漏答率是本设计的核心因变量，0.87% 的系统性污染不能当噪声。③ 修法（v4.6，**1425 行**）：`kqFirstPressUntil(deadline, tFloor)` 只接受 "
    "`tFloor < t ≤ deadline` 的按键，四个调用点（练习/正式 × 刺激期/反应窗）都传 `stimulusFlipTime`；早于 onset 的键不消费、留给下一试次开头的 `KbQueueFlush()`。"
    "④ 牙齿：`test/check_full_session.py` 新增 A8b/A11/A12（v4.6 头注、四个调用点都带 tFloor、`kqScan` 边界表达式）⇒ **26/26**；"
    "重跑无屏幕冒烟两组仍 **27/27**（2.9 / 3.1 s）。⑤ 边界：那 5 行是 **v4.5 产物，不能靠改判据变绿**；Stage 1 的 6-C 要等 v4.6 复跑一次才算过关。 |"
)

PROGRESS_ROW = (
    "| 2026-10-18 | **6**（实机回放抓缝 → D83） | **把「抢按已被计数」与「抢按不参与反应」分开**："
    "59.111 Hz 实机 576 试次里 5 行 `stimulus_dur_actual` 仅 0–1 帧 ⇒ 程序 v4.6 给 `kqFirstPressUntil` 加 `tFloor`"
    "（四个调用点传 `stimulusFlipTime`）；静态判据 26/26、冒烟 27/27；6-C 待 v4.6 复跑 |"
)

FILE_ROW = (
    "| `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.5 → **v4.6**，1425 行）+ `test/check_full_session.py`（+A8b/A11/A12，26/26）"
    " + `1_Code/DDM_Core/_scratch/_apply_d83_preonset.py`（**新建**，补丁） | 四个反应窗口传 `tFloor = stimulusFlipTime`；"
    "`kqFirstPressUntil(deadline, tFloor)` / `kqScan(..., tFloor)` 只取窗口内的键；早于 onset 的键留给下一试次开头的 flush |"
)

# ---------------- Stage1 §6 回填 ----------------
FILLS = [
    # 6-B
    ("| T=33.33 ms 单元里 `Response` 为 `f`/`j`（不是 `NA`） | 至少 1 例 | |",
     "| T=33.33 ms 单元里 `Response` 为 `f`/`j`（不是 `NA`） | 至少 1 例 | **19 例**（2026-10-18，59.111 Hz 屏，576 试次） |"),
    ("| 该行 `RT` < 0.0333 | ✅ | |",
     "| 该行 `RT` < 0.0333 | ✅ | ✅ 19/19 全部 < 0.0333 |"),
    ("| 注视期抢按被记为 `premature_press = 1`，且**不**影响该试次 RT | ✅ | |",
     "| 注视期抢按被记为 `premature_press = 1`，且**不**影响该试次 RT | ✅ | ✅ 431 行 `premature_press = 1`；有 RT 的行 **全部为正**（v4.5 兜底后无负值） |"),
    ("| 掩蔽期内按键仍被记录（`RT` 落在 T ~ T+200 ms 之间） | ✅ | |",
     "| 掩蔽期内按键仍被记录（`RT` 落在 T ~ T+200 ms 之间） | ✅ | ✅ **142 例**（含 T 档内 0.033–0.45 s 全区间） |"),
    ("| `responded_by_deadline` / `timeout` 两列互补、无第三态 | ✅ | |",
     "| `responded_by_deadline` / `timeout` 两列互补、无第三态 | ✅ | ✅ `timeout` 135 / `responded_by_deadline` 441（和 = 576，无第三态） |"),
    # 6-C
    ("| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 ≤ 1 帧 | |",
     "| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 ≤ 1 帧 | ✅ 59.111 Hz 下 T = 33.83 / 84.59 / 152.26 / 253.76 ms（2/5/9/15 帧），偏离 ≤ 4.3 ms；W 三档 132 / 198 / 297 帧 |"),
    ("| 全部无刺激期按键试次的 `stimulus_frames` | 分别 ≈ 2 / 5 / 9 / 15（±1 帧） | |",
     "| 全部无刺激期按键试次的 `stimulus_frames` | 分别 ≈ 2 / 5 / 9 / 15（±1 帧） | ✅ 297 行里 291 行落在 0 / 2 / 5 / 9 / 15，另有 5 行抢按截断（见下行）与 1 行 +1 帧余量 |"),
    ("| `max (stimulus_dur_actual − T) / FlipIntv` | ∈ [−0.5, +1.5) | |",
     "| `max (stimulus_dur_actual − T) / FlipIntv` | ∈ [−0.5, +1.5) | ❌ **5 行越界**：−1.37 / −1.61 / −4.35 / −13.95 / −14.15 帧；其余 292 行 ∈ [−0.02, +1.16]（max 1.16 帧 = vsync 余量） |"),
    ("| `stimulus_offset_actual − mask_onset_actual` 恒为 0 | ✅ | |",
     "| `stimulus_offset_actual − mask_onset_actual` 恒为 0 | ✅ | ✅ 576/576（容差 1e-5） |"),
    ("| `mask_onset_actual − stimulus_onset_actual − stimulus_dur_actual` 恒为 0 | ✅ | |",
     "| `mask_onset_actual − stimulus_onset_actual − stimulus_dur_actual` 恒为 0 | ✅ | ✅ 576/576（容差 1e-5 秒） |"),
    # 6-D
    ("| `.txt` 首行表头为 25 个列名、与 §3 一致 | ✅ | |",
     "| `.txt` 首行表头为 25 个列名、与 §3 一致 | ✅ | ✅ 与 `HEADER25` 逐字一致 |"),
    ("| 漏答行的 `Response` 是 `NA`（不是空、不是 `0`） | ✅ | |",
     "| 漏答行的 `Response` 是 `NA`（不是空、不是 `0`） | ✅ | ✅ 135 行全部为 `NA` |"),
    ("| 漏答行的 `Correct` 是 `NaN`、`timeout = 1`、`responded_by_deadline = 0` | ✅ | |",
     "| 漏答行的 `Correct` 是 `NaN`、`timeout = 1`、`responded_by_deadline = 0` | ✅ | ✅ 135/135 |"),
    ("| 练习行 `block = 0`，正式行 `block ∈ {1,2,3}` | ✅ | |",
     "| 练习行 `block = 0`，正式行 `block ∈ {1,2,3}` | ✅ | ✅ 本场组 1（P=0）无练习行；正式 `block` 1/2/3 各 192 |"),
    ("| 用十六进制查看器搜不到 `0x00` 字节 | ✅ | |",
     "| 用十六进制查看器搜不到 `0x00` 字节 | ✅ | ✅ 0 个 |"),
]

D83_NOTE = """
> ⚠ **6-C 的 5 行越界（D83）**：这 5 行 `stimulus_dur_actual` 只有 0–1 帧、`premature_press = 1`、
> `Response = NA`、`timeout = 1`。根因不是显示卡顿，而是**注视末梢的键落进了反应窗口**——
> 注视期抢按在 `kqCountPresses()`（`Exp_Design_Formal.m:964`）处读取，该点距真正 onset 隔着一次
> `Screen('Flip')` 的 vsync 等待；这条缝隙里按下的第二个键不会进抢按计数，却被刺激期的
> `kqFirstPressUntil` 立刻取走，于是刺激在 0–1 帧内被敲掉、试次变成漏答。
> **v4.6 已修**（`kqFirstPressUntil(deadline, tFloor)`，四个调用点传 `stimulusFlipTime`），
> 但这 5 行是 **v4.5 产物**：按「不改判据去迁就数据」的原则，6-C 仍记为 ❌，
> 待 v4.6 在实验室机复跑一场后重判（预计 297 行全部 ∈ [−0.5, +1.5) 帧）。
"""

MANUAL_FIXES = [
    ("> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.5）",
     "> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.6）"),
    ("> 版本：v2.4（2026-10-18，", "> 版本：v2.5（2026-10-18，v2.5 补「onset 之前的按键」症状与 v4.6；v2.4 随"),
]

PTB_FIXES = [
    ("| `Exp_Design_Formal.m` | 正式实验程序 **v4.5**",
     "| `Exp_Design_Formal.m` | 正式实验程序 **v4.6**"),
    ("| 主试培训手册（v2.4，", "| 主试培训手册（v2.5，"),
]


def sub_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"[SKIP] {label}：已改")
        return text
    n = text.count(old)
    assert n == 1, f"{label}：锚点命中 {n} 次（应为 1）"
    print(f"[OK] {label}")
    return text.replace(old, new)


def insert_after(text: str, prefix: str, line: str, label: str) -> str:
    if line.strip() in text:
        print(f"[SKIP] {label}：已存在")
        return text
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, f"{label}：锚点命中 {len(hits)} 次"
    lines.insert(hits[0] + 1, line)
    print(f"[OK] {label}：第 {hits[0] + 1} 行之后")
    return "\n".join(lines)


def main() -> int:
    # 主计划
    t = (PLAN.read_text(encoding="utf-8"))
    t = insert_after(t, "| **D82** | 2026-10-18 |", D83_ROW, "主计划 D83 决策行")
    t = insert_after(t, "| 2026-10-18 | **6**（被试材料 → D82）", PROGRESS_ROW, "主计划进度行")
    if FILE_ROW.split(" | ")[0] in t:
        print("[SKIP] 主计划文件行：已存在")
    else:
        t = t.rstrip("\n") + "\n" + FILE_ROW + "\n"
        print("[OK] 主计划文件行：追加")
    PLAN.write_text(t, encoding="utf-8", newline="\n")

    # Stage1 回填
    t = S1.read_text(encoding="utf-8")
    for old, new in FILLS:
        t = sub_once(t, old, new, f"Stage1 回填：{new.split('|')[1].strip()[:28]}…")
    if "6-C 的 5 行越界（D83）" in t:
        print("[SKIP] Stage1 6-C 说明：已存在")
    else:
        anchor = "| `mask_onset_actual − stimulus_onset_actual − stimulus_dur_actual` 恒为 0 | ✅ | ✅ 576/576（容差 1e-5 秒） |"
        assert t.count(anchor) == 1
        t = t.replace(anchor, anchor + "\n" + D83_NOTE)
        print("[OK] Stage1 6-C 说明：已插入")
    S1.write_text(t, encoding="utf-8", newline="\n")

    # 手册 / PTB 版本
    t = MAN.read_text(encoding="utf-8")
    for old, new in MANUAL_FIXES:
        t = sub_once(t, old, new, f"手册版本：{new[:24]}…")
    MAN.write_text(t, encoding="utf-8", newline="\n")

    t = PTB.read_text(encoding="utf-8")
    for old, new in PTB_FIXES:
        t = sub_once(t, old, new, f"PTB 说明：{new[:30]}…")
    PTB.write_text(t, encoding="utf-8", newline="\n")

    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
