"""通用文件体检：语法（仅 .py）+ 行尾 + BOM + 行数。

用法::

    python 1_Code\\DDM_Core\\_scratch\\check_files.py <文件…>

为什么单独一个文件：`python -c` 里的引号在 PowerShell 下极易被吃掉
（本项目已经因为"命令行引号被解释"踩过好几次），写成文件最省事。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(path: Path) -> bool:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    ok = True
    has_bom = raw[:3] == b"\xef\xbb\xbf"
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n")
    bare_lf = lf - crlf
    ast_note = "-"
    if path.suffix == ".py":
        try:
            ast.parse(text)
            ast_note = "OK"
        except SyntaxError as exc:
            ast_note = f"SYNTAX ERROR: {exc}"
            ok = False
    if has_bom:
        ok = False
    if crlf:
        ok = False
    print(f"{'✅' if ok else '❌'} {path.as_posix():58s} "
          f"lines={text.count(chr(10)):5d} bare_LF={bare_lf:5d} CRLF={crlf:4d} "
          f"BOM={has_bom!s:5s} ast={ast_note}")
    return ok


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    results = [check(Path(p)) for p in argv[1:]]
    print(f"\n{sum(results)}/{len(results)} 通过"
          f"{'（全部裸 LF、无 BOM）' if all(results) else ' ❌ 有问题'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
