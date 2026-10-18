# -*- coding: utf-8 -*-
"""重写 README §8.57–§8.58 这一段（前两次插入把两节的正文交错在一起了）。

做法：定位 `### 8.57` 标题与 `## 9.` 标题，把这一整段替换成本脚本里的干净版本。
所有事实都来自 D83 / D83b / D84 / D85 的原始记录，未新增也未删减结论。
"""
from __future__ import annotations

import sys
from pathlib import Path

README = Path(__file__).resolve().parents[3] / "1_Code" / "DDM_Core" / "README.md"

NEW = """### 8.57 数据写入防线之后：`onset` 之前的按键被当成反应（2026-10-18，D83 / D83b / D84）

**现象**：60 Hz 实机（实测 59.111 Hz）跑出的 576 个正式试次里，有 **5 行**的 `stimulus_dur_actual` 只有 0–1 帧
（6–14 ms）、`premature_press = 1`、`Response = NA`、`timeout = 1`。检查器 6-C 判 4/5：这 5 行的时长偏离是
**−1.37 / −1.61 / −4.35 / −13.95 / −14.15 帧**（其余 292 行落在 −0.02 ~ +1.16 帧）。卡顿只会让时长**变长**
（165 Hz 那场是 +2…+25 帧），这里是短到 0–1 帧 ⇒ 排除卡顿。

**根因**：注视期抢按在 `kqCountPresses()`（`Exp_Design_Formal.m:964`）读完立即 `KbQueueFlush()`（`:972`），
但该点距真正 onset（`:976` 的 `Screen('Flip')`）隔着一次 **vsync 等待（≤ 1 帧 ≈ 16.7 ms）**。
这条缝隙里按下的第二个键：不进抢按计数、队列又刚清过 ⇒ 刺激期 `kqFirstPressUntil` 一进循环就取到它，
刺激被立刻敲掉，试次记成漏答。**漏答率是本设计的核心因变量**（W 三档的论证全靠它），0.87% 的系统性高估不能当噪声。

**做法（v4.6）**：`kqFirstPressUntil(deadline, tFloor)` 只接受 `tFloor < 时间戳 ≤ deadline`；
四个调用点（练习/正式 × 刺激期/反应窗）都传 `stimulusFlipTime`；早于 onset 的键不消费，留给下一试次开头的
`KbQueueFlush()`。静态判据补 A8b/A11/A12 ⇒ `test/check_full_session.py` **26/26**，无屏幕冒烟两组仍 **27/27**。

**牙齿补强（D84）**：`> tFloor` 这一行很容易在「修漏答」时被改回 `>=` 或被删参数，而整场冒烟**照样全绿**
（桩的按键时刻与这条分界线无关）。新建 `test/check_kq_floor.m`（203 行）把这层语义钉成十例：它从程序**原文抽取**
`kqFirstPressUntil` / `kqScan` / `resolveEscKeyCode` 再测（不复刻逻辑），C2 是反向用例（不传 floor 时必须返回同一个键
⇒ 证明测试有牙）。首轮 **5/10**：根因是 `PsychStartup` 已把 PTB 的 `KbName` 放到 path 最前，桩用 `-end` 加在后面
⇒ `KbName('f')` 返回 **70** 而非 **6**，`f/j` 永远匹配不上（Esc = 27 两种口径一致才绿）；改成
`addpath(stubsDir, '-begin')` 再 `addpath(tmpDir, '-begin')` ⇒ **10/10**。结果落盘 `test/_kq_floor_result.txt`，
`check_full_session.py` 加 B27–B29 ⇒ **29/29**。它是开发者回归，**不进现场六条**。

**顺带修的检查器漂移（D83b）**：`check_stage1_acceptance.py` 的 `load_rows()` 写死 `split("\\t")`，
而主试交回的 `EXP_data_group1_1.csv` 是逗号分隔 ⇒ 整行被当成 1 列，打印「表头不是 v4.1 的 25 列（1 列）」。
已改为按首行嗅探分隔符（有制表符 ⇒ txt；否则含逗号 ⇒ `csv.reader`），两通道都能吃。

**边界**：这 5 行**保留为「v4.5 已知缺陷」，不放宽 6-C 判据去迁就既有数据**。要回填 Stage 1 §6，
仍须用 v4.6 在实验室机（60.004 Hz）上复跑一场。

### 8.58 阈值是从哪来的：87 份历史真人数据把 S6-5 的两条线顶翻了（2026-10-18，D85）

1. **现象**：第一场真实数据（576 试次、60 Hz、v4.5）走完 Stage 6/7 全链路——`read_formal_data.py` ✅、
   `qc_group.py` G1–G9 全 PASS 且剔除 0、`analyze_pilot.py` 的 S1-1 / S1-1b / S6-3 / S6-2c ✅；
   但 **S6-1**（timeout 23.4%、最差单元 43.8%）与 **S6-5**（RT 中位 0.069 s、过快 56.2%）FAIL。
   于是问题变成：**是数据坏了，还是判据错了？**
2. **做法**：新建 `1_Code/Experiment/analyze_rt_baseline.py`（零依赖），把 S6-5 关心的四个量在
   `2_Data/Real_Data/UnExtact/emp_data` 的 **87 份真人逐被试文件**上重算一遍，并统计每个阈值会判掉多少份真人。
3. **三个数字**：正确率 `0.55` 下限判掉 **31/87 = 35.6%**（历史 q05 = 0.451）；RT 中位 `0.30 s` 下限判掉
   **15/87 = 17.2%**（历史 min = 0.234 s）；「过快 > 10%」**0/87**（历史数据里一次都没触发）。
4. **改法**：S6-5 改两级——**FAIL** 线放在「历史真人从未出现」的位置（`RT 中位 < 0.20 s`、`正确率 < 0.45` 或 `> 0.995`、
   `过快 > 10%`），模糊带 `0.20–0.30 s` / `0.45–0.55` / `0.98–0.995` 只 WARN。
   改完这一场**仍然 FAIL**（0.069 s < 0.20 s、56.17% > 10%）⇒ 这次调整不是为了让数据过关。
5. **这一场到底是什么**：按 T 分档正确率 `0.477 / 0.487 / 0.495 / 0.477`——四条都贴着机会水平 0.5，
   且**不随 T 变长而回升**（"任务太难"会回升）；RT 中位 0.069 s 在 87 份真人里排 **P0**。
   ⇒ 是**主试按键的试跑**，不是被试数据；按「试跑」处理、不计入 Pilot 的 N=8。
6. **顺带抓出的第三个制表符 bug**：`1_Code/Experiment/analyze_pilot.py:86` 也是 `split("\\t")` 写死，
   传逗号 CSV 时整行读成 1 列 ⇒ 表头退化成 `col1` ⇒ 报「跳过 1 个旧版 16 列文件 / 没有任何 25 列数据文件」。
   D83b（`check_stage1_acceptance.py`）、D83c（`read_formal_data.py`）改的是前两处，这是**第三处**；
   同一处修法（首行嗅探 + `csv.reader`）已套用。**教训：凡是读产物的工具，都必须先确认它认哪种分隔符。**
7. **边界**：参照集是 D4 之前的设计（T/W 不同、无掩蔽），只能校准「像不像人在做任务」；`RT 中位` 在旧设计里
   被「掩蔽期不读队列」抬到 `T + 200 ms`，新设计下限更低 ⇒ `0.30 s` 不能当生理下界。
"""


def main() -> int:
    lines = README.read_text(encoding="utf-8").split("\n")
    i57 = [k for k, ln in enumerate(lines) if ln.startswith("### 8.57 ")]
    i9 = [k for k, ln in enumerate(lines) if ln.startswith("## 9.")]
    if len(i57) != 1 or len(i9) != 1:
        sys.exit(f"[FAIL] 标题命中异常 57={len(i57)} 9={len(i9)}")
    a, b = i57[0], i9[0]
    out = lines[:a] + NEW.rstrip("\n").split("\n") + [""] + lines[b:]
    text = "\n".join(out)
    README.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] 重写 §8.57–§8.58（替换第 {a + 1}–{b} 行）⇒ README = {len(text.splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
