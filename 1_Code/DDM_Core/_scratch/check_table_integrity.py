"""五份工作流文档的表格完整性扫描（Stage 1 收尾时的回归检查）。

判据：Markdown 表格里不该出现"`|` 行 → 非空非 `|` 行 → `|` 行"这种三连
（中间那一行会把表格截断成两段）。空行是合法的分段，不算断。

用法：python _scratch/check_table_integrity.py <文件1> [文件2 ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def scan(path: Path) -> tuple[int, list[int], int]:
    lines = path.read_text(encoding="utf-8").split("\n")
    is_row = [bool(ln.lstrip().startswith("|")) for ln in lines]
    breaks: list[int] = []
    for i in range(1, len(lines) - 1):
        if is_row[i - 1] and is_row[i + 1] and not is_row[i] and lines[i].strip():
            breaks.append(i + 1)  # 1-based
    return len(lines), breaks, sum(is_row)


def main() -> int:
    bad = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"❌ 找不到文件：{p}")
            bad += 1
            continue
        n_lines, breaks, n_rows = scan(p)
        status = "✅" if not breaks else "❌"
        detail = "" if not breaks else f"  断点行号 = {breaks}"
        print(f"{status} {p.name}：{n_lines} 行、表格行 {n_rows}、internal_breaks = {len(breaks)}{detail}")
        bad += len(breaks)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
