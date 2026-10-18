# -*- coding: utf-8 -*-
"""_apply_d78.py —— D78（数据累积 table→cell，修「第一个未响应试次必崩」）落纸

覆盖：Stage 7 §6.4 扩成 D77/D78 两件 + 文档行版本 + 四条自测 + §10 第 8 条 + §11 v1.3；
Stage 1 §6 第 0 步加第四条自测 + D78 补注；主计划 §5/§6/§7/§8；
README §8.51 两处过时表述 + §8.52 + §9 第 62 项。
幂等：insert_after/insert_before 断言锚点唯一，已存在则跳过。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
S7 = ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md"
S1 = ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md"
RD = ROOT / "1_Code/DDM_Core/README.md"

msgs: list[str] = []
BAT_CHK = 'matlab -batch "cd(\'<仓库>\\1_Code\\Experiment\\exp_matlab\'); addpath(\'test\'); check_input_validation"'


def insert_after(text: str, prefix: str, block: str, tag: str) -> str:
    first = block.split("\n")[0]
    if first in text:
        msgs.append(f"[跳过] {tag}")
        return text
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix!r} 命中 {len(hits)} 行")
    i = hits[0]
    lines[i + 1:i + 1] = block.split("\n")
    msgs.append(f"[插入] {tag}（锚点 L{i + 1}）")
    return "\n".join(lines)


def insert_before(text: str, prefix: str, block: str, tag: str) -> str:
    first = block.split("\n")[0]
    if first in text:
        msgs.append(f"[跳过] {tag}")
        return text
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix!r} 命中 {len(hits)} 行")
    i = hits[0]
    lines[i:i] = block.split("\n")
    msgs.append(f"[插入] {tag}（锚点 L{i + 1}）")
    return "\n".join(lines)


def replace_once(text: str, old: str, new: str, tag: str) -> str:
    if new in text:
        msgs.append(f"[跳过] {tag}")
        return text
    if text.count(old) != 1:
        raise SystemExit(f"❌ {tag}：命中 {text.count(old)} 次")
    msgs.append(f"[替换] {tag}")
    return text.replace(old, new)


# ---------------------------------------------------------------- Stage 7
t = S7.read_text(encoding="utf-8")
t = replace_once(t, "### 6.4 主试侧输入防线（D77，2026-10-18）",
                 "### 6.4 主试侧输入防线（D77）与数据写入防线（D78），2026-10-18", "S7 §6.4 标题")
t = replace_once(t, "（v2.1，349 行）+ `.docx`（14317 B）",
                 "（v2.2，362 行）+ `.docx`（15031 B）", "S7 文档行版本")
t = insert_after(
    t,
    "| 文档 |",
    "| **数据写入** | `exp_new_data.m`（新）+ `exp_data_table.m`（新）+ `Exp_Design_Formal.m` v4.4 | 累积容器是 cell（不是 `table()`）；保存时一次性 `cell2table`，char 列转 `string`（去补齐空格）；保存前核对 `size(data,1) == trialIndex-1` | `test/check_data_accum.m` **24/24**（含「先 f 后 NA」崩溃复现、不等长标签、静态守卫、写读回环） |",
    "S7 §6.4 数据写入行",
)
t = insert_after(
    t,
    BAT_CHK,
    'matlab -batch "cd(\'<仓库>\\1_Code\\Experiment\\exp_matlab\'); addpath(\'test\'); check_data_accum"',
    "S7 §6.4 命令块",
)
t = replace_once(t, "**现场纪律**：正式采集开始前，先在实验机跑这三条（约 20 s）：",
                 "**现场纪律**：正式采集开始前，先在实验机跑这四条（约 25 s）：", "S7 现场纪律")
t = replace_once(t, "三条全过才动机器；任一条 ❌ ⇒ 说明程序、校验或手册之一被改过且没同步，**不得**开始正式采集。",
                 "四条全过才动机器；任一条 ❌ ⇒ 说明程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集。",
                 "S7 四条全过")
t = insert_after(
    t,
    "> 教训（写进本 Stage 的原因）：`check_manual_d4.py` 是**唯一**一条会把「代码」和「文档」放在一起比的判据。",
    "> 教训之二（D78）：**「能跑完全程」不等于「能存下来」**。v4.3 的数据表用 `table()` 逐行增长，\n"
    "> 第一行 `f`（1 字符）把 `Response` 列宽锁死，第一个**未响应**试次写 `NA`（2 字符）就崩——\n"
    "> 这类缺陷只在「被试真的漏答一次」时才出现，跑一万个全响应试次都发现不了。数据写入路径必须由\n"
    "> `check_data_accum.m` 这种**构造出异常行**的自测钉住，不能靠「跑通一次」当证据。",
    "S7 D78 教训",
)
t = replace_once(t, "1. **确认跑的是 v4.1**（`Exp_Design_Formal.m` 头部 `v4.1`；或开跑后检查第一份数据的 T 列是否为 `0.083330` 一类 6 位小数）。",
                 "1. **确认跑的是 v4.4**（`Exp_Design_Formal.m` 头部 `v4.4`；或开跑后检查第一份数据的 T 列是否为 `0.083330` 一类 6 位小数，`Response` 列在漏答时为 `NA`）。",
                 "S7 §7 版本")
t = insert_after(
    t,
    "7. **主试侧输入只在校验层挡住",
    "8. **数据写入路径没有「跑通一次」就等于正确**（D78）：v4.3 的 `table()` 逐行累积把 `Response` 列宽锁死在 1 个字符，第一个未响应试次写 `NA` 即崩，且这类崩溃发生在**被试第一次漏答**的时候（现场表现为「跑到一半突然关屏」）。现由 `test/check_data_accum.m` 24/24 钉住（含崩溃复现与写读回环）；**改输出列或改响应取值时必须同步该自测**，否则它会静默放行。",
    "S7 §10 第 8 条",
)
t = insert_after(
    t,
    "| v1.2 | 2026-10-18 | 新增 §6.4（主试侧输入防线，D77）",
    "| v1.3 | 2026-10-18 | §6.4 扩成两件防线：D77（组别越界不再 error 退出）+ **D78（数据累积 `table()` → cell）**——v4.3 在第一个「未响应」试次必崩（`赋值右侧的值的宽度错误`），已由 `test/check_data_accum.m` 24/24 钉住；§7 现场清单改为确认 v4.4；新增 §10 第 8 条（数据写入路径的自测纪律）。 |",
    "S7 §11 v1.3",
)
S7.write_text(t, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- Stage 1
t = S1.read_text(encoding="utf-8")
t = replace_once(t, "### ★ 0. 程序自测（跑实验之前先做，约 20 s）",
                 "### ★ 0. 程序自测（跑实验之前先做，约 25 s）", "S1 §6 标题")
t = replace_once(t, "**跑实验之前先在实验机执行这三条**：",
                 "**跑实验之前先在实验机执行这四条**：", "S1 三条→四条")
t = insert_after(
    t,
    BAT_CHK,
    'matlab -batch "cd(\'<仓库>\\1_Code\\Experiment\\exp_matlab\'); addpath(\'test\'); check_data_accum"',
    "S1 命令块",
)
t = insert_after(
    t,
    "| `check_input_validation` |",
    "| `check_data_accum` | `通过 24 / 未通过 0` | 数据累积与保存：`f` 之后写 `NA` 不崩（D78 的复现）、不等长标签无补齐空格、`data = table()` 等旧写法静态拦下、写 CSV 再读回逐列核对 |",
    "S1 表格行",
)
t = replace_once(t, "三条全过才动机器。任一条 ❌ ⇒ 程序、校验或手册之一被改过且没同步，**不得**开始正式采集",
                 "四条全过才动机器。任一条 ❌ ⇒ 程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集",
                 "S1 四条全过")
t = insert_after(
    t,
    "另：程序现在**不会再因组别填错而退出**。",
    "另（D78）：v4.3 的数据表用 `table()` 逐行累积，第一个**未响应**试次写 `NA` 就崩（`赋值右侧的值的宽度错误`），\n"
    "2026-10-18 实机踩到；v4.4 改为 cell 累积 + 保存时 `cell2table`，由 `check_data_accum` 24/24 钉住。\n",
    "S1 D78 补注",
)
S1.write_text(t, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- 主计划
t = MP.read_text(encoding="utf-8")
t = insert_after(
    t,
    "| **D77** | 2026-10-18 |",
    "| **D78** | 2026-10-18 | ❗ **「跑通全程」不等于「能存下来」：v4.3 的数据表在第一个未响应试次必崩**。① 现象：主试实跑，前几个试次刷出 6 条「赋值时将各行添加到了表格中…」警告，随后 `错误使用 Exp_Design_Formal / 赋值右侧的值的宽度错误。赋值需要宽度为 1 的值。`（`data{trialIndex,14}=respStr` 处），`Screen('CloseAll')` 退出。② 机理：`data = table()` 后逐行 `data{r,c}=` 追加，table 变量类型由**第一次赋值**锁定——第一行 `f`（宽度 1）把 `Response` 列固化成 1 字符宽 char，第一个 timeout 试次写 `NA`（宽度 2）即维度冲突；同时 table 逐行增长是 O(n²) 复制并反复告警。③ 修法：新增 `exp_new_data.m`（0×25 cell 累积）、`exp_data_table.m`（一次性 `cell2table`，char 列转 `string(cellstr(...))` 去掉 cell2table 的补齐空格以免污染 CSV），`Exp_Design_Formal.m` 升 v4.4 并加行数自检 `size(data,1) == trialIndex-1`。④ 牙齿：新增 `test/check_data_accum.m` **24/24**（A 容器、B「先 f 后 NA」崩溃复现、C 不等长标签、D 静态守卫 `data = table()`/`data.Properties`、E 写 CSV 再读回）。⑤ 教训：这条路径**只有被试真的漏答一次**才会暴露；数据写入必须用「构造异常行」的自测钉住，不能拿「跑通一次」当证据。 |",
    "主计划 D78 决策行",
)
t = insert_after(
    t,
    "| 2026-10-18 | **1/7**（主试侧输入防线 → D77） |",
    "| 2026-10-18 | **1/7**（数据写入防线 → D78） |",
    "主计划 进度行",
)
t = insert_after(
    t,
    "| 2026-10-18 | **新增 D77：",
    "| 2026-10-18 | **新增 D78（数据累积 table→cell）**：`Exp_Design_Formal.m` v4.4（1357 行）；新增 `exp_new_data.m`/`exp_data_table.m`/`test/check_data_accum.m`（24/24）；手册 v2.2（362 行，四条自测 + §6.6 已知崩溃症状）；落纸 Stage 1/Stage 7/README。 |",
    "主计划 变更日志",
)
t = insert_after(
    t,
    "| `1_Code/Experiment/exp_matlab/{exp_ask_subject_info.m（**新建**）",
    "| `1_Code/Experiment/exp_matlab/{exp_new_data.m（**新建**）、exp_data_table.m（**新建**）、test/check_data_accum.m（**新建**）}` + `Exp_Design_Formal.m`（**v4.4**，1357 行） | **D78 的一手证据**：`test/_check_data_accum.txt`（通过 24 / 未通过 0）、`test/_checkcode_v44.txt`（新增两个函数 0 条告警） |",
    "主计划 §8 文件行",
)
MP.write_text(t, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- README
t = RD.read_text(encoding="utf-8")
t = replace_once(t, "重写为 **v2.1**（349 行，", "重写为 **v2.2**（362 行，", "README §8.51 手册版本")
t = replace_once(t, "正式采集前在实验机跑三条（约 20 s）",
                 "正式采集前在实验机跑四条（约 25 s）", "README §8.51 四条")
t = insert_before(
    t,
    "## 9. 尚未做",
    "### 8.52 数据写入防线：数据累积 `table()` → cell（2026-10-18，D78）\n"
    "\n"
    "1. **问题**：主试在实验机跑 v4.3，前几个试次刷出 6 条「赋值时将各行添加到了表格中，但并未对表格中所有现有的变量赋值」警告，随后在第一个**未响应**试次抛 `错误使用 Exp_Design_Formal / 赋值右侧的值的宽度错误。赋值需要宽度为 1 的值。`，`Screen('CloseAll')` 退出——整场数据作废。\n"
    "2. **机理**：v4.3 用 `data = table()` 建容器、逐行 `data{trialIndex,14} = respStr` 追加。table 的变量**类型与宽度由第一次赋值锁定**：第一行 `f`（1 字符）把 `Response` 固化成 1 字符宽 char，第一个 timeout 试次写 `NA`（2 字符）即维度冲突。附带代价：table 逐行增长每次都复制全表，576 试次是 O(n²)，且每次扩展都发一条警告。\n"
    "3. **修法**：`v4.4` 改为 **cell 累积**——新增 `1_Code/Experiment/exp_matlab/exp_new_data.m`（`0×25` cell，带列数校验）、`exp_data_table.m`（保存时一次性 `cell2table`，char 列转 `string(cellstr(...))` 去掉 cell2table 的补齐空格，否则 `'self'` 会写成 `'self    '` 污染 CSV）；主程序在保存前核对 `size(data,1) == trialIndex-1`，不等就 `warning('Exp_Design_Formal:rowCount')` 并写进日志。\n"
    "4. **牙齿**：`1_Code/Experiment/exp_matlab/test/check_data_accum.m` **通过 24 / 未通过 0**（无屏幕、秒级）：A 容器类型与列数、B 崩溃复现（`f` 之后写 `NA` 必须不报错且 `Response` 保留 `NA`）、C 不等长标签无补齐空格、D 静态守卫（主程序不得再出现 `data = table()` / `data.Properties`）、E 写 CSV 再 `readtable` 读回逐列核对。\n"
    "5. **为什么此前没抓到**：这条崩溃只在**被试真的漏答一次**时出现。D65/D70/D71 的干跑与 Stage 1 的历史演练从未构造过「`f` 之后跟 `NA`」的序列，`checkcode` 也看不出类型宽度问题。⇒ 数据写入路径必须用**构造异常行**的自测钉住，「跑通一次」不是证据。\n"
    "6. **现场纪律**：正式采集前在实验机跑**四条**自测（约 25 s）——`check_ask_info`、`check_input_validation`、`check_data_accum`、`check_manual_d4.py`。改输出列或改响应取值（例如新增一个按键）时**必须同步** `check_data_accum.m`，否则它会静默放行。\n",
    "README §8.52",
)
t = insert_after(
    t,
    "| 61 | ✅ **主试侧输入防线",
    "| 62 | ✅ **「跑通全程」不等于「能存下来」：数据累积 `table()` → cell（D78，§8.52）** | v4.3 在第一个未响应试次崩（`赋值右侧的值的宽度错误`）：`table()` 的类型/宽度由首次赋值锁定，`f`（宽 1）之后写 `NA`（宽 2）即冲突。v4.4 改为 `exp_new_data.m` cell 累积 + `exp_data_table.m` 一次性 `cell2table`（char 列转 `string` 去补空格），新增 `test/check_data_accum.m` **24/24**（含崩溃复现与写读回环）；手册 v2.2 与 Stage 1/Stage 7 的现场清单同步改为**四条**自测。 |",
    "README §9 第 62 项",
)
RD.write_text(t, encoding="utf-8", newline="\n")

for m in msgs:
    print(m)
print("完成（未校验）")
