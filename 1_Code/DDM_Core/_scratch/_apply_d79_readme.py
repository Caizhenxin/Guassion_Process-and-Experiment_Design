# -*- coding: utf-8 -*-
"""_apply_d79_readme.py —— D79 落进 README（§8.53 + §9 第 63 项）+ 修 §8.52 的「四条」口径"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "1_Code" / "DDM_Core" / "README.md"

errors: list[str] = []
n = 0


def replace_once(old: str, new: str, name: str) -> None:
    raw = README.read_text(encoding="utf-8")
    if new in raw and old not in raw:
        print(f"[跳过] {name}")
        return
    if raw.count(old) != 1:
        errors.append(f"{name}: 命中 {raw.count(old)} 次")
        return
    README.write_text(raw.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[替换] {name}")


def insert_before(anchor: str, block: str, name: str) -> None:
    raw = README.read_text(encoding="utf-8")
    if block.split("\n")[0] in raw:
        print(f"[跳过] {name}")
        return
    if raw.count(anchor) != 1:
        errors.append(f"{name}: 锚点命中 {raw.count(anchor)} 次")
        return
    README.write_text(raw.replace(anchor, block + anchor, 1), encoding="utf-8", newline="\n")
    print(f"[插入] {name}")


# 1) §8.52 第 6 条：四条 → 六条（D79 之后现场纪律变了）
replace_once(
    "6. **现场纪律**：正式采集前在实验机跑**四条**自测（约 25 s）——`check_ask_info`、`check_input_validation`、`check_data_accum`、`check_manual_d4.py`。"
    "改输出列或改响应取值（例如新增一个按键）时**必须同步** `check_data_accum.m`，否则它会静默放行。",
    "6. **现场纪律**：正式采集前在实验机跑自测（D79 之后为**六条**，约 35 s）——`check_ask_info`、`check_input_validation`、`check_data_accum`、`runbatch_full_session(1, 99)`、`check_full_session.py`、`check_manual_d4.py`。"
    "改输出列或改响应取值（例如新增一个按键）时**必须同步** `check_data_accum.m`，否则它会静默放行。",
    "§8.52 第 6 条 四条→六条",
)

# 2) §8.53 新小节（插在 `## 9. 尚未做` 之前）
S853 = """### 8.53 整场无屏幕冒烟：把「跑完 + 存下」推进到「数值对得上」（2026-10-18，D79）

1. **问题**：2026-10-17 一天两次实机崩溃（D77 组别越界、D78 第一个未响应试次崩）都落在**从未被执行过的路径**上。当时最强的自测只到函数级（`check_ask_info` 40/40、`check_data_accum` 33/33），进不了主循环；而主循环恰恰是最长、最容易带着状态 bug 跑下去的地方。
2. **做法**：为 PTB 造 **24 个桩**（`1_Code/Experiment/exp_matlab/test/stubs/`：`Screen`/`GetSecs`/`WaitSecs`/`KbQueue*`/`KbCheck`/`KbName`/`DrawFormattedText`/`inputdlg`/`warndlg`/`uiwait` 等，虚拟时钟 + 按试次序号编排的按键剧本），驱动 `test/run_full_session.m` + `test/runbatch_full_session.m` **直接调用主脚本**跑完整场（组 1：576 试次；组 2：584 = P8 练习 + 576），**3.0 s/场**，产物搬到 `test/_full_session_out/`（不与真实数据混目录）。回归 **27 项判据**：A 全程无异常；B1–B19 行数/列名/`Response` 取值/`Correct` 三分支/`premature_press`/`timeout`/`block`/`T`·`W` 档位/`trialID` 连续/`NA` 行 RT 为 NaN/stage 两段/`txt` 行数与表头；**B20 截断分支确实走到（28 行）、B21 截断行 `stimulus_dur_actual ≈ RT`（最大差 4.0 ms）、B22 无负 RT、B23 RT 有无与 `responded_by_deadline` 一致**。
3. **真 bug ①：逐试次 txt 通道从不 `fclose`**。`fopen(..., 'a+')` 之后只 `fprintf`，保存阶段才 `movefile`/退出：缓冲区可能未落盘（MATLAB 直到退出才 flush），Windows 下该文件被本进程独占 ⇒ 主试当场移动/上传即报「无法从源读取」。修法：保存阶段 `fclose(fileID)`（无句柄时跳过）。
4. **真 bug ②：注视期抢按被当成反应（负 RT）**。抢按已记进 `premature_press`，但那一按仍留在 KbQueue 里；紧随的刺激期 `kqFirstPressUntil` 立刻取到它 ⇒ `responseTime = 按键时刻 − 刺激 onset` **为负**，该行既算「已响应」，又让 `stimulus_dur_actual` 与「按键后下一帧」对不上（冒烟里 **62/584 行**，`read_formal_data.py` 直接判 ❌）。修法：记完抢按立即 `KbQueueFlush()`（练习段、正式段各一处）+ 数值兜底（`responseTime <= 0` ⇒ 仍按抢按处理、响应清空）。程序升 **v4.5**（1395 行）。
5. **三道牙**：`test/check_full_session.py` **23/23**（A 静态 10 项：三处修正仍在且顺序正确、没有回退到 `data = table()`；B 驱动 7 项：B20–B23 判据仍在、24 个桩、产物搬出程序目录、日志走 UTF-8；C 产物 3 项：两组日志 `pass=27 fail=0`、`read_formal_data.py` 2/2 通过；**D 反例 2 项**：把修正拿掉后 A 组必须失败——判据不是空的）；`read_formal_data.py` 端到端读两组产物**全部一致性判据通过**；`check_manual_d4.py` 40/40。
6. **边界**：冒烟**不替代**实机。桩的 PTB 时间戳全是假的（`GetSecs` 每次调用 +1 ms），帧率、真实延时、PTB 兼容性与 6-A/6-E 仍必须在实验机人测；它钉住的是**逻辑与数据约定**（谁写哪一列、写出的值自洽不自洽），这正是 D77/D78/D79 三次崩溃的共同来源。

"""
insert_before("## 9. 尚未做\n", S853, "§8.53 整场无屏幕冒烟")

# 3) §9 第 63 项（插在第 62 项之后）
ITEM63 = (
    "| 63 | ✅ **整场无屏幕冒烟：跑完 + 存下 + 数值对得上（D79，§8.53）** | "
    "24 个 PTB 桩 + `test/run_full_session.m` / `runbatch_full_session.m` 直接跑主脚本整场（组 1 576 / 组 2 584 试次，3.0 s/场，27/27 判据），"
    "并抓出两个真 bug：逐试次 txt 通道从不 `fclose`（文件被独占、「无法从源读取」）、注视期抢按被当成反应（**负 RT**，62/584 行 `stimulus_dur_actual` 对不上）。"
    "程序升 **v4.5**；`test/check_full_session.py` **23/23**（含反例自检）；`read_formal_data.py` 读两组产物 2/2 通过。"
    "冒烟**不替代**实机：PTB 时间戳是假的，6-A/6-E 仍须人测 |\n"
)


def append_item63() -> None:
    raw = README.read_text(encoding="utf-8")
    if "| 63 | ✅ **整场无屏幕冒烟" in raw:
        print("[跳过] §9 第 63 项")
        return
    lines = raw.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith("| 62 | ✅ **「跑通全程」不等于「能存下来」")]
    if len(hits) != 1:
        errors.append(f"§9 第 63 项: 锚点命中 {len(hits)} 次")
        return
    lines.insert(hits[0] + 1, ITEM63.rstrip("\n"))
    README.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("[插入] §9 第 63 项")


append_item63()

if errors:
    print("\n=== 失败 ===")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)
print("\nREADME 更新完成")
