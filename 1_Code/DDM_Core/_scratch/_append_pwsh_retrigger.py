# -*- coding: utf-8 -*-
"""给 PowerShell 内联 python 那份失败记录追加「再次触发记录」。"""
from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\2026-10-17_PowerShell内联python-c带中文引号必炸.md")
BT = chr(96)

text = f"""

## 再次触发记录（2026-10-18，第 N 次）

**场景**：改 `5_Reference/08_工作流/工作流_主计划.md` 的一行错误表格行时，用
`python -X utf8 -u -c @"..."@` 内联脚本，脚本里含 {BT}`1_Code/Experiment/...`{BT} 形式的行内代码。

**新发现的失败形态（与「引号必炸」并列的第二个雷：反引号）**：
- PowerShell 双引号 here-string 把**反引号当转义符**吃掉 ⇒ Python 收到的字符串里
  {BT}`Exp_Design_Formal.m`{BT} 变成 `Exp_Design_Formal.m`，于是 `assert r.startswith('{BT}1_Code/...')`
  直接 `AssertionError`，但报错信息看起来像「文件内容不对」。
- 更隐蔽的一次：往 `INDEX.md` 追加表格行时，`{BT}#标签{BT}` 里的反引号被吃掉、留下
  `\\#标签\\`，**脚本退出码 0、行数也对**，只有把该行 `repr()` 出来才看得出标签被破坏。

**规避策略（本次采用，写进流程）**：
1. 任何要落纸的文本，只要含反引号 / 中文 / 引号，一律先用 `write` 工具写成 `.py` 文件再 `python 跑`;
   不用 `python -c`，不用 here-string。
2. 追加表格行后必须 `repr()` 打印一次，别只看行数。
3. 已有脚本里出现 `SyntaxWarning: invalid escape sequence`（如 `\\#`）就是反引号被吃的信号，
   见到就当失败处理，不要忽略。
"""

with P.open("a", encoding="utf-8", newline="\n") as f:
    f.write(text)
print("已追加", len(text), "字符；总行数", len(P.read_text(encoding="utf-8").split("\n")))
