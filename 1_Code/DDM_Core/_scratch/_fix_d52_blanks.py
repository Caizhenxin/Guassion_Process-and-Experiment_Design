"""检查并修复 `_apply_d52.py` 误删的空行（它把锚点行之后的空行一并摘掉了）。

`insert_after` 的"摘除空行再插入"逻辑是为**连续追加多行**设计的；本轮每个锚点只插
一行，结果把表格与 `---` 之间的空行吃掉了 4 处。本脚本：
1. 报告四处新行前后的实际形状；
2. 若新行之后不是空行，补一个空行；
3. 断言文件以换行结尾。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MASTER = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "工作流_主计划.md"

PREFIXES = [
    "| **D52** |",
    "| 2026-10-14 | **8/9**（N=4 干跑判读 → D52） |",
    "| 2026-10-14 | **新增 D52：LOO 可用性必须同时看",
    "| `1_Code/DDM_Core/stage8_run.py`（修改：`render_group`",
]


def main() -> int:
    raw = MASTER.read_bytes()
    print(f"文件末尾 24 字节：{raw[-24:]!r}")
    text = raw.decode("utf-8")
    lines = text.split("\n")

    fixed = 0
    for pre in PREFIXES:
        hits = [i for i, t in enumerate(lines) if t.startswith(pre)]
        if len(hits) != 1:
            raise SystemExit(f"❌ 前缀 {pre[:34]!r} 命中 {len(hits)} 次")
        i = hits[0]
        nxt = lines[i + 1] if i + 1 < len(lines) else "<EOF>"
        print(f"  L{i + 1} 之后是 {nxt[:46]!r}")
        if i + 1 < len(lines) and lines[i + 1].strip() != "":
            lines.insert(i + 1, "")
            fixed += 1

    out = "\n".join(lines)
    if not out.endswith("\n"):
        out += "\n"
        print("  ⇒ 补回文件末尾换行")
    MASTER.write_text(out, encoding="utf-8", newline="")
    print(f"✅ 补回 {fixed} 处空行；{MASTER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
