# -*- coding: utf-8 -*-
"""给「PowerShell 内联 python -c 带中文引号必炸」追加第三次触发记录（D97 落纸时反引号被吃）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\2026-10-17_PowerShell内联python-c带中文引号必炸.md")
old = p.read_text(encoding="utf-8")
add = """
## 再次触发记录（2026-10-18，D97 落纸）

**场景**：只改两行头部说明（状态行、阶段状态行）——看起来比写补丁脚本「轻」，
于是又用了 `python -X utf8 -u -c @"..."@` 内联脚本。

**新形态（第三次，仍未换方案，代价是内容被静默改写）**：
- 替换字符串里含 `` `正式采集_候选设计.md` ``，反引号被 here-string 吃掉 ⇒ 落盘后该行
  变成 `正式采集_候选设计.md 的候选清单由本文取代`（行内代码的定界符消失）。
- **assert 没抓住**：我断言的是 `a[5].startswith('> 权威性')`，只校验了**前缀**，
  内容被改写照样通过；事后靠肉眼看到输出里少了反引号才发现，改用 `write` 写 `.py`
  以 `chr(96)` 重建才修回。
- 同一批里还发现第二处：D97 决策行里写「354 → 366 行」是**估算值**，实测 381 行 ⇒
  行数类断言必须取实测值，不能凭加行数推算。

**规避策略（升级，写进流程）**：
1. 只要写的是**文档正文**（含反引号、中文、引号），一律 `write` 成 `.py` 再用 `python` 跑；
   内联 `-c` / here-string 只允许用于**只读**查询。
2. 校验断言要覆盖**被改写的内容**（`in` / `count`），不能只查 `startswith` / 行数。
3. 落盘后立刻把改动行 `repr()` 出来看一次定界符还在不在；文档里的行数 / 尺寸一律以实测为准。
"""
assert "D97 落纸" not in old
p.write_text(old.rstrip("\n") + "\n" + add, encoding="utf-8", newline="\n")
print("lines", len(p.read_text(encoding="utf-8").split("\n")))
