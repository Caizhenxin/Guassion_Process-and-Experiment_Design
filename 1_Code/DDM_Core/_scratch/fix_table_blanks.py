"""删掉夹在两行表格行之间的空行（空行会把 Markdown 表格截断成两张表）。

**为什么要有这个工具**：往表格尾部追加一行时，如果写成
"先在末尾插一个空行、再写新行"，Markdown 会在空行处结束表格 ⇒ 新行**没有表头**，
于是被渲染成一段普通文本（竖线原样显示），而不是表格的一行。
这类破损**不会**被 `check_table_integrity.py` 的第一代判据（行内换行）发现，
也**不会**被"竖线数一致性"判据发现（因为孤立行自己内部是自洽的）——
2026-10-14 实测：主计划里有 **7 处**，其中 4 处让决策记录 D40–D43 全部失去表头。

判定规则：空行 `i` 满足 `lines[i-1]` 与 `lines[i+1]` 都是表格行（`lstrip()` 后以 `|` 开头）
⇒ 删除该空行。代码围栏（``` ）内部一律跳过，避免碰到代码块里的 `|`。

用法：
    python _scratch/fix_table_blanks.py <文件...>            # 只报告
    python _scratch/fix_table_blanks.py --apply <文件...>    # 就地删除

写回时用 `newline=""` + 原样文本，保留原有行尾（CRLF/LF 不变）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_blanks(lines: list[str]) -> list[int]:
    """返回需要删除的空行下标（0-based）。"""
    in_fence = False
    out: list[int] = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if i == 0 or i == len(lines) - 1:
            continue
        if ln.strip() != "":
            continue
        prev_row = lines[i - 1].lstrip().startswith("|")
        next_row = lines[i + 1].lstrip().startswith("|")
        if prev_row and next_row:
            out.append(i)
    return out


def main() -> int:
    apply = "--apply" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if not args:
        print("⚠️ 未传入文件参数 —— 没有检查任何东西（这不等于通过）")
        return 0
    total = 0
    for arg in args:
        p = Path(arg)
        if not p.exists():
            print(f"❌ 找不到文件：{p}")
            continue
        text = p.read_text(encoding="utf-8")
        lines = text.split("\n")
        idx = find_blanks(lines)
        if not idx:
            print(f"✅ {p.name}：没有断表空行")
            continue
        total += len(idx)
        print(f"{'🔧' if apply else '❌'} {p.name}：{len(idx)} 处断表空行 -> 行号 {[i + 1 for i in idx]}")
        for i in idx:
            nxt = lines[i + 1].lstrip()[:34]
            print(f"      L{i + 1} 之后的表格行：{nxt}…")
        if apply:
            drop = set(idx)
            kept = [ln for j, ln in enumerate(lines) if j not in drop]
            p.write_text("\n".join(kept), encoding="utf-8", newline="")
            print(f"      已就地删除（{len(lines)} -> {len(kept)} 行）")
    if apply:
        print(f"\n合计删除 {total} 处")
        return 0
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
