"""粗略的 MATLAB 块结构平衡检查器。

统计 for / while / if / switch / try / parfor / function 与「关键字 end」的配对，
并把 `x(end)`、`a(1:end, :)` 这类**索引里的 end** 排除（括号深度 > 0 时不算块结束）。

用法：python _scratch/check_matlab_blocks.py <file.m>
退出码 0 = 平衡（允许 function 未闭合，若脚本采用「function 不带 end」风格）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

OPENERS = {"for", "while", "if", "switch", "try", "parfor", "function", "spmd"}


def strip_strings_comments(line: str) -> str:
    """去掉注释与字符串字面量；保留转置运算符 ' 与数组分词。"""
    out: list[str] = []
    i = 0
    n = len(line)
    in_str = False
    while i < n:
        ch = line[i]
        if in_str:
            if ch == "'":
                if i + 1 < n and line[i + 1] == "'":
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if ch == "'":
            prev = "".join(out).rstrip()
            if prev and (prev[-1].isalnum() or prev[-1] in ")]}._"):
                out.append(ch)          # 转置运算符
                i += 1
                continue
            in_str = True               # 字符串开始
            i += 1
            continue
        if ch == "%":
            break
        if ch == "." and i + 1 < n and line[i + 1] == ".":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8", errors="replace")
    par = 0
    stack: list[tuple[str, int]] = []
    problems: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        code = strip_strings_comments(raw)
        for tok in re.findall(r"[A-Za-z_]\w*|[()\[\]{}]", code):
            if tok in "([{":
                par += 1
                continue
            if tok in ")]}":
                par = max(0, par - 1)
                continue
            if par > 0 or not tok[0].isalpha():
                continue                     # 索引上下文里的 end 不算块结束
            if tok in OPENERS:
                stack.append((tok, lineno))
            elif tok == "end":
                if not stack:
                    problems.append(f"line {lineno}: 多余的 end（没有未闭合的块）")
                else:
                    stack.pop()

    funcs = [s for s in stack if s[0] == "function"]
    others = [s for s in stack if s[0] != "function"]
    print(f"{path.name}: 行数 = {len(text.splitlines())}")
    print(f"  未闭合的 function（本文件为「function 不带 end」风格时属正常）= {len(funcs)}")
    for opener, lineno in others:
        print(f"  ❌ 未闭合 {opener}（开于 line {lineno}）")
    for p in problems:
        print(f"  ❌ {p}")
    ok = not others and not problems
    print("  ✅ 块结构平衡" if ok else "  ❌ 块结构不平衡")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
