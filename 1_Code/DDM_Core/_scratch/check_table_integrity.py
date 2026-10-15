"""工作流文档的表格完整性扫描（回归检查）。

两组判据：

1. **截断（internal_breaks）**：Markdown 表格里不该出现
   "`|` 行 → 非空非 `|` 行 → `|` 行"这种三连（中间那一行会把表格截断成两段）。
   空行是合法的分段，不算断。

2. **竖线数一致性（mangled_rows）**：同一张表里，表头行定义了列数；**每一行**
   的有效竖线数必须与表头相同，且必须**以 `|` 结尾**。
   这一组是 2026-10-14 补的：当时 D42 行把"max |Δ|"的绝对值符号写成了单元格里的
   字面竖线（`|` 而不是转义 `\\|`），导致该行 7 个竖线而兄弟行 6 个、且行末
   闭合竖线丢失——**判据 1 完全没有报**。守卫只查一种失效模式，就只防得住那一种。

   有效竖线 = 未被反斜杠转义的 `|`（`\\|` 在单元格里渲染成字面竖线，不算分隔符）。

3. **断表空行（split_rows）**：夹在两行表格行之间的空行会把表格截断 ⇒ 空行之后的
   那一行**没有表头**，被渲染成一段普通文本（竖线原样显示）。2026-10-14 实测主计划
   里有 7 处，其中 4 处让决策记录 D40–D43 全部失去表头。**判据 1 与判据 2 都测不到
   它**（孤立行自身内部是自洽的）。修法是 `_scratch/fix_table_blanks.py`。

用法：python _scratch/check_table_integrity.py <文件1> [文件2 ...]
（⚠️ 必须显式传文件参数：无参数时不打印任何结论并 exit 0。）
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def count_seps(line: str) -> int:
    """数一行的有效竖线数：转义的 `\\|` 不计入。"""
    n = 0
    i = 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            i += 2  # 转义对，跳过
            continue
        if line[i] == "|":
            n += 1
        i += 1
    return n


def find_split_rows(lines: list[str]) -> list[int]:
    """返回把表格截断的空行行号（0-based）。代码围栏内跳过。"""
    in_fence = False
    out: list[int] = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or i == 0 or i == len(lines) - 1:
            continue
        if ln.strip() != "":
            continue
        if lines[i - 1].lstrip().startswith("|") and lines[i + 1].lstrip().startswith("|"):
            out.append(i)
    return out


def scan(path: Path) -> tuple[int, list[int], int, list[tuple[int, int, int, str]], list[int]]:
    lines = path.read_text(encoding="utf-8").split("\n")
    is_row = [bool(ln.lstrip().startswith("|")) for ln in lines]

    breaks: list[int] = []
    for i in range(1, len(lines) - 1):
        if is_row[i - 1] and is_row[i + 1] and not is_row[i] and lines[i].strip():
            breaks.append(i + 1)  # 1-based

    mangled: list[tuple[int, int, int, str]] = []
    i = 0
    while i < len(lines):
        if not is_row[i]:
            i += 1
            continue
        j = i
        while j < len(lines) and is_row[j]:
            j += 1
        run = list(range(i, j))  # 这张表占用的行下标
        if len(run) >= 2:
            want = count_seps(lines[run[0]])
            for k in run[1:]:
                ln = lines[k]
                got = count_seps(ln)
                if got != want:
                    mangled.append((k + 1, want, got, "竖线数不一致"))
                elif not ln.rstrip().endswith("|"):
                    mangled.append((k + 1, want, got, "行末缺闭合竖线"))
        i = j

    return len(lines), breaks, sum(is_row), mangled, find_split_rows(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("⚠️ 未传入文件参数 —— 没有扫描任何东西（这不等于通过）")
        return 0
    bad = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"❌ 找不到文件：{p}")
            bad += 1
            continue
        n_lines, breaks, n_rows, mangled, splits = scan(p)
        status = "✅" if (not breaks and not mangled and not splits) else "❌"
        print(
            f"{status} {p.name}：{n_lines} 行、表格行 {n_rows}、"
            f"internal_breaks = {len(breaks)}、mangled_rows = {len(mangled)}、"
            f"split_rows = {len(splits)}"
        )
        if breaks:
            print(f"    断点行号 = {breaks}")
        for lineno, want, got, why in mangled:
            print(f"    L{lineno}：{why}（表头 {want} 个竖线，本行 {got} 个）")
        if splits:
            print(f"    断表空行行号 = {[i + 1 for i in splits]}（用 _scratch/fix_table_blanks.py 修）")
        bad += len(breaks) + len(mangled) + len(splits)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
