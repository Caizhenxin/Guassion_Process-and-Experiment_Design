# -*- coding: utf-8 -*-
"""_apply_d79_docs.py —— 把 D79（整场无屏幕冒烟）落进三份文档

落点：
  主计划       §5 决策行 / §6 进度行 / §7 变更日志 / §8 文件行（均插在 D78 行之后）
  Stage 1      §6 第 0 步「四条」→「六条」+ 表格两行 + 修掉一句被 D78 注插断的话
  Stage 7      §6.4 标题 + 表格一行 + 现场纪律改五条 + 教训之三

幂等：所有插入都先查「本行是否已存在」，复核行首前缀唯一性，缺锚点即报错退出。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S1 = ROOT / "5_Reference" / "08_工作流" / "Stage1_技术验证记录.md"
S7 = ROOT / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md"

errors: list[str] = []
n_applied = 0


def insert_after(path: Path, prefix: str, new_lines: list[str], guard: str) -> None:
    """在唯一一条以 prefix 开头的行之后插入 new_lines；guard 出现即已插过。"""
    global n_applied
    text = path.read_text(encoding="utf-8")
    if guard in text:
        print(f"[跳过] {path.name} :: {guard[:28]}")
        return
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        errors.append(f"{path.name}: 锚点 {prefix[:40]!r} 命中 {len(hits)} 次")
        return
    i = hits[0]
    lines[i + 1 : i + 1] = new_lines
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    n_applied += 1
    print(f"[插入] {path.name} :: 第 {i+2} 行起 {len(new_lines)} 行")


def replace_once(path: Path, old: str, new: str, name: str) -> None:
    global n_applied
    text = path.read_text(encoding="utf-8")
    if new and new in text and old not in text:
        print(f"[跳过] {path.name} :: {name}")
        return
    if text.count(old) != 1:
        errors.append(f"{path.name}: {name} 命中 {text.count(old)} 次（应为 1）")
        return
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    n_applied += 1
    print(f"[替换] {path.name} :: {name}")


# ---------------------------------------------------------------- 主计划 §5
D79_DECISION = (
    "| **D79** | 2026-10-18 | ✅ **整场无屏幕冒烟：从「跑完 + 存下」推进到「数值对得上」，并抓出两个只有实跑才暴露的 bug**。"
    "① 动机：2026-10-17 一天两次实机崩溃（D77 组别越界、D78 第一个未响应试次崩）都落在**从未被执行过的路径**上，"
    "而当时最强的自测也只到函数级（`check_ask_info` 40/40、`check_data_accum` 33/33），进不了主循环。"
    "② 做法：为 PTB 造 **24 个桩**（`test/stubs/`：`Screen`/`GetSecs`/`WaitSecs`/`KbQueue*`/`KbCheck`/`KbName`/`DrawFormattedText`/`inputdlg`/`warndlg`/`uiwait` 等，虚拟时钟 + 按键剧本），"
    "驱动 `test/run_full_session.m` + `runbatch_full_session.m` 直接调主脚本跑完整场（组 1：576 试次；组 2：584 = P8 练习 + 576），**3.0 s/场**，"
    "产物搬到 `test/_full_session_out/`（不与真实数据混），回归 **27 项判据**（A 无异常；B1–B19 行数/列名/各分支取值；"
    "**B20 截断分支确实走到（28 行）、B21 截断行 `stimulus_dur_actual ≈ RT`（最大差 4.0 ms）、B22 无负 RT、B23 RT 有无与 `responded_by_deadline` 一致**）。"
    "③ 真 bug ①：逐试次 txt 通道 `fopen(...,'a+')` 之后**从不 fclose** ⇒ 缓冲区可能未落盘，Windows 下该文件被本进程独占（主试当场移动/上传报「无法从源读取」）；"
    "修法：保存阶段 `fclose(fileID)`。"
    "④ 真 bug ②：注视期抢按已记进 `premature_press`，但那一按仍留在 KbQueue 里，紧随的刺激期 `kqFirstPressUntil` 立刻取到它 ⇒ "
    "`responseTime = 按键时刻 − 刺激 onset` **为负**，该行既算「已响应」又让 `stimulus_dur_actual` 与「按键后下一帧」对不上（冒烟里 62/584 行）；"
    "修法：记完抢按立即 `KbQueueFlush()`（练习段、正式段各一处）+ 数值兜底（`responseTime <= 0` ⇒ 仍按抢按处理、响应清空）。"
    "⑤ 三道牙：`test/check_full_session.py` **23/23**（A 静态 10 项 + B 驱动 7 项 + C 产物 3 项 + D 反例 2 项，含「拿掉修正后必须失败」的自检）、"
    "`read_formal_data.py` 端到端读两组产物 **全部一致性判据通过**、`check_manual_d4.py` 40/40。"
    "⑥ 边界：冒烟**不替代**实机 —— 桩的 PTB 时间戳全是假的，帧率/延时/PTB 兼容性与 6-A/6-E 仍归 Stage 1 人测；"
    "程序升 **v4.5**（1395 行）。"
)
D79_DECISION += (
    " | 桩 `1_Code/Experiment/exp_matlab/test/stubs/`（**24 个**）；驱动 `test/run_full_session.m` / `test/runbatch_full_session.m`；"
    "`test/check_full_session.py`（**23/23**）；日志 `test/_full_session_g{1,2}_s99.txt`（`pass=27 fail=0`）、`test/_read_formal_session.txt`（2/2 通过）；"
    "`Exp_Design_Formal.m` v4.5 | 每次改主循环先跑整场冒烟再上机；D78 的「能存下来」升级为「数值对得上」；实机项仍归 Stage 1 |"
)

insert_after(
    MP,
    "| **D78** | 2026-10-18 |",
    [D79_DECISION],
    "| **D79** | 2026-10-18 |",
)

# ---------------------------------------------------------------- 主计划 §6
D79_PROGRESS = (
    "| 2026-10-18 | **1/7**（整场无屏幕冒烟 → D79） | "
    "**跑完整场 + 数值对得上**：24 个 PTB 桩 + 整场驱动（组 1 576 试次、组 2 584 试次，3.0 s/场，27/27 判据）；"
    "抓出两个真 bug —— 逐试次 txt 通道从不 `fclose`、注视期抢按被当成「负 RT 的反应」（62/584 行 `stimulus_dur_actual` 对不上）；"
    "修法 `fclose` + 抢按后 `KbQueueFlush()`（练习/正式各一处）+ `responseTime <= 0` 兜底；"
    "`check_full_session.py` **23/23**、`read_formal_data.py` **2/2 通过** | "
    "程序 **v4.5**（1395 行）；`test/stubs/`、`test/run_full_session.m`、`test/runbatch_full_session.m`、`test/check_full_session.py` | "
    "每次改主循环先跑冒烟再上机；PTB 时间戳是假的，实机项仍归 Stage 1（6-A/6-E） |"
)

insert_after(
    MP,
    "| 2026-10-18 | **1/7**（数据写入防线 → D78） |",
    [D79_PROGRESS],
    "（整场无屏幕冒烟 → D79）",
)

# ---------------------------------------------------------------- 主计划 §7
D79_CHANGELOG = (
    "| 2026-10-18 | **新增 D79（整场无屏幕冒烟）**：新增 `test/stubs/`（24 个 PTB 桩）、`test/run_full_session.m`、"
    "`test/runbatch_full_session.m`、`test/check_full_session.py`（**23/23**）；`Exp_Design_Formal.m` v4.4 → **v4.5**（1395 行）："
    "逐试次 txt 通道补 `fclose`、抢按后补 `KbQueueFlush()`（练习/正式各一处）、`responseTime <= 0` 兜底；"
    "整场回归组 1/组 2 均 `pass=27 fail=0`，`read_formal_data.py` 读两组产物 2/2 通过 |"
)

insert_after(
    MP,
    "| 2026-10-18 | **新增 D78（数据累积 table→cell）**：",
    [D79_CHANGELOG],
    "**新增 D79（整场无屏幕冒烟）**",
)

# ---------------------------------------------------------------- 主计划 §8
D79_FILES = (
    "| `1_Code/Experiment/exp_matlab/test/{stubs/（24 个 PTB 桩，**新建**）、run_full_session.m（**新建**）、"
    "runbatch_full_session.m（**新建**）、check_full_session.py（**新建**）}` + `Exp_Design_Formal.m`（v4.5，1395 行） | "
    "2026-10-18（D79） |"
)

insert_after(
    MP,
    "| `1_Code/Experiment/exp_matlab/{exp_new_data.m（**新建**）",
    [D79_FILES],
    "test/stubs/（24 个 PTB 桩",
)

# ---------------------------------------------------------------- Stage 1：修被插断的那句 + 六条自测
replace_once(
    S1,
    "另：程序现在**不会再因组别填错而退出**。填错（越界/留空/非整数）会弹一个说明窗口，列出\n"
    "另（D78）：v4.3 的数据表用 `table()` 逐行累积，第一个**未响应**试次写 `NA` 就崩（`赋值右侧的值的宽度错误`），\n"
    "2026-10-18 实机踩到；v4.4 改为 cell 累积 + 保存时 `cell2table`，由 `check_data_accum` 33/33 钉住。\n"
    "\n"
    "「组1 P0 ｜ 组2 P8 ｜ 组3 P32 ｜ 组4 P120」，关掉后自动回到「实验信息」窗重填；填完还会回显\n"
    "「groupID ⇒ 本组 P」让你核对，输错就输入 `r` 回车重来，不必 Ctrl+C 重开。\n",
    "另：程序现在**不会再因组别填错而退出**。填错（越界/留空/非整数）会弹一个说明窗口，列出\n"
    "「组1 P0 ｜ 组2 P8 ｜ 组3 P32 ｜ 组4 P120」，关掉后自动回到「实验信息」窗重填；填完还会回显\n"
    "「groupID ⇒ 本组 P」让你核对，输错就输入 `r` 回车重来，不必 Ctrl+C 重开。\n"
    "\n"
    "另（D78）：v4.3 的数据表用 `table()` 逐行累积，第一个**未响应**试次写 `NA` 就崩（`赋值右侧的值的宽度错误`），\n"
    "2026-10-18 实机踩到；v4.4 改为 cell 累积 + 保存时 `cell2table`，由 `check_data_accum` 33/33 钉住。\n"
    "另（D79）：v4.4 之前还把抢按当成反应（负 RT）、且逐试次 txt 通道从不 `fclose`；v4.5 修掉，\n"
    "由「整场无屏幕冒烟」`runbatch_full_session` 27/27 + `check_full_session.py` 23/23 钉住。\n",
    "修断句 + D79 注",
)

replace_once(
    S1,
    "### ★ 0. 程序自测（跑实验之前先做，约 25 s）",
    "### ★ 0. 程序自测（跑实验之前先做，约 35 s）",
    "§6 第 0 步标题",
)

replace_once(
    S1,
    "而程序早已 D4。这类\"文档与代码漂移\"不会自己报错，只能靠对照。**跑实验之前先在实验机执行这四条**：\n"
    "\n"
    "```bat\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum\"\n"
    "python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py\n"
    "```\n",
    "而程序早已 D4。这类\"文档与代码漂移\"不会自己报错，只能靠对照。**跑实验之前先在实验机执行这六条**：\n"
    "\n"
    "```bat\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); runbatch_full_session(1, 99)\"\n"
    "python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py\n"
    "python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_full_session.py\n"
    "```\n",
    "§6 命令块 四条→六条",
)

replace_once(
    S1,
    "| `check_manual_d4.py` | `共 40 项：通过 40 / 未通过 0` | 程序常量 / 手册 / Word 版 / 自测**四者口径一致**（4 组、576 试次、3 block、25 列） |\n",
    "| `check_manual_d4.py` | `共 40 项：通过 40 / 未通过 0` | 程序常量 / 手册 / Word 版 / 自测**四者口径一致**（4 组、576 试次、3 block、25 列） |\n"
    "| `runbatch_full_session(1, 99)` | `SUMMARY pass=27 fail=0` | **整场冒烟**（D79）：用 24 个 PTB 桩在无屏幕环境跑完整场 576 试次，再把产物喂回 `read_formal_data.py`；"
    "B20–B23 专钉「刺激期内按键 = min(T, RT)」「无负 RT」「RT 与 responded_by_deadline 一致」 |\n"
    "| `check_full_session.py` | `== 通过 23 / 未通过 0 ==` | 上面那次冒烟的**仓库侧**牙齿：程序里三处 v4.5 修正仍在、驱动判据仍在、两组日志 `pass=27 fail=0`、产物已回读通过；含 2 条反例自检 |\n",
    "§6 表格补两行",
)

replace_once(
    S1,
    "四条全过才动机器。任一条 ❌ ⇒ 程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集",
    "六条全过才动机器。任一条 ❌ ⇒ 程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集",
    "§6 四条全过→六条",
)

# ---------------------------------------------------------------- Stage 7 §6.4
replace_once(
    S7,
    "### 6.4 主试侧输入防线（D77）与数据写入防线（D78），2026-10-18",
    "### 6.4 输入防线（D77）、数据写入防线（D78）与整场冒烟（D79），2026-10-18",
    "§6.4 标题",
)

replace_once(
    S7,
    "| **数据写入** | `exp_new_data.m`（新）+ `exp_data_table.m`（新）+ `Exp_Design_Formal.m` v4.4 | 累积容器是 cell（不是 `table()`）；保存时一次性 `cell2table`，char 列转 `string`（去补齐空格）；保存前核对 `size(data,1) == trialIndex-1` | `test/check_data_accum.m` **33/33**（含「先 f 后 NA」崩溃复现、不等长标签、静态守卫、写读回环、按行号写入（F 组）） |\n",
    "| **数据写入** | `exp_new_data.m`（新）+ `exp_data_table.m`（新）+ `Exp_Design_Formal.m` v4.4 | 累积容器是 cell（不是 `table()`）；保存时一次性 `cell2table`，char 列转 `string`（去补齐空格）；保存前核对 `size(data,1) == trialIndex-1` | `test/check_data_accum.m` **33/33**（含「先 f 后 NA」崩溃复现、不等长标签、静态守卫、写读回环、按行号写入（F 组）） |\n"
    "| **整场冒烟** | `test/stubs/`（24 个 PTB 桩，新）+ `test/run_full_session.m`（新）+ `test/runbatch_full_session.m`（新）+ `Exp_Design_Formal.m` v4.5 | 无屏幕跑完整场（组 1 576 试次 / 组 2 584），再把产物喂回 `read_formal_data.py`；专钉「刺激期内按键 = `min(T, RT)`」「无负 RT」「抢按不算反应」「txt 通道已落盘」 | `test/check_full_session.py` **23/23** + 冒烟自身 **27/27**（两组） |\n",
    "§6.4 表格补整场冒烟行",
)

replace_once(
    S7,
    "**现场纪律**：正式采集开始前，先在实验机跑这四条（约 25 s）：\n"
    "\n"
    "```bat\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum\"\n"
    "python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py\n"
    "```\n"
    "\n"
    "四条全过才动机器；任一条 ❌ ⇒ 说明程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集。\n",
    "**现场纪律**：正式采集开始前，先在实验机跑这五条（约 35 s）：\n"
    "\n"
    "```bat\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum\"\n"
    "matlab -batch \"cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); runbatch_full_session(1, 99)\"\n"
    "python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_full_session.py\n"
    "python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py\n"
    "```\n"
    "\n"
    "五条全过才动机器；任一条 ❌ ⇒ 说明程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集。\n"
    "（`runbatch_full_session` 会往 `test/_full_session_out/` 写两份**假数据**，看完即可删，**不得**与真实数据混目录。）\n",
    "§6.4 现场纪律 四条→六条",
)

replace_once(
    S7,
    "> 只测代码（51/51、40/40）发现不了手册过期；只读手册也发现不了程序已改。这类漂移不会报错，只会让主试\n"
    "> 在实验机上撞一次。\n",
    "> 教训之三（D79）：**「跑完 + 存下」仍不等于「数值对得上」**。抢按被当成反应这件事，在 CSV 里只是一行\n"
    "> `RT` 为负的记录，肉眼看不出来；是「把产物再喂回 `read_formal_data.py`」之后才暴露的（62/584 行\n"
    "> `stimulus_dur_actual` 与「按键后下一帧」不符）。凡是「产物 → 下游读取器」的约定，都必须有一条端到端判据。\n"
    "> 只测代码（51/51、40/40）发现不了手册过期；只读手册也发现不了程序已改。这类漂移不会报错，只会让主试\n"
    "> 在实验机上撞一次。\n",
    "§6.4 教训之三",
)

if errors:
    print("\n=== 失败 ===")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)
print(f"\n共应用 {n_applied} 处")
