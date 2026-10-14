"""`Exp_Design_Formal.m` 的「未定义标识符」静态检查。

存在的理由：v4 修过一个真实缺陷——`T_levels` 那三行把变量写成了 `FlipInv`，
而程序里定义的是 `FlipIntv`。MATLAB 只会在实机跑到那一行时报
"Undefined function or variable 'FlipInv'"，本机没有 MATLAB，所以必须静态查。

做法：剥掉注释与字符串 → 收集所有"被赋值过的名字"（LHS / for / function 形参与输出 /
persistent / global / catch）→ 把"被使用但从未被赋值且不是函数调用"的名字报出来。

用法：python _scratch/check_matlab_undefined.py <file.m>
退出码 0 = 没有可疑的未定义标识符。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 语言内建 + 工具函数（只需要覆盖本文件实际用到的）
BUILTIN = {
    "for", "while", "if", "elseif", "else", "switch", "case", "otherwise",
    "try", "catch", "function", "return", "break", "continue", "end", "true",
    "false", "struct", "cell", "zeros", "ones", "table", "string", "char",
    "double", "single", "int8", "int16", "int32", "logical", "numel", "length",
    "size", "isempty", "isnan", "ischar", "isnumeric", "isstruct", "iscell",
    "islogical", "ismember", "strcmp", "strcmpi", "find", "sum", "mean", "round",
    "floor", "ceil", "mod", "rem", "tan", "sin", "cos", "pi", "sqrt", "abs",
    "min", "max", "sort", "any", "all", "setdiff", "intersect", "union", "unique",
    "sprintf", "fprintf", "fopen", "fclose", "ftell", "error", "warning", "disp",
    "input", "inputdlg", "str2double", "randi", "randperm", "num2str", "mat2str",
    "num2cell", "cellfun", "arrayfun", "repmat", "reshape", "cat", "horzcat",
    "vertcat", "nan", "NaN", "inf", "persistent", "global", "clc", "clear",
    "eval", "evalin", "assignin", "strsplit", "strjoin", "strrep", "regexprep",
    "lower", "upper", "strtrim", "cumsum", "diff", "interp1", "polyfit",
    "polyval", "linspace", "diag", "inv", "trace", "exp", "log", "log2", "log10",
    "sign", "ferror", "fseek", "frewind", "isrow", "iscolumn", "isvector",
    "isfloat", "isinteger", "swapbytes", "typecast", "bitand", "bitor", "bitxor",
    "printf", "tic", "toc", "clock", "now", "etime", "datestr", "load", "save",
}
PTB = {
    "Screen", "KbName", "KbCheck", "KbQueueCreate", "KbQueueStart",
    "KbQueueFlush", "KbQueueCheck", "KbQueueRelease", "GetSecs", "WaitSecs",
    "DrawFormattedText", "InitializeMatlabOpenGL", "HideCursor", "ShowCursor",
    "CenterRectOnPoint", "imread", "imwrite", "sca", "writetable", "MakeTexture",
    "Flip", "OpenWindow", "CloseAll", "WindowSize", "GetFlipInterval",
}
KEYWORDS = {"end"}


def strip_comments_and_strings(src: str) -> list[str]:
    """逐行剥掉 `%` 之后的注释、单引号字符串与双引号字符串（保留转置运算符）。"""
    out_lines = []
    for line in src.split("\n"):
        res, i, n, quote = [], 0, len(line), None
        while i < n:
            ch = line[i]
            if quote is not None:
                if ch == quote:
                    if i + 1 < n and line[i + 1] == quote:
                        i += 2
                        continue
                    quote = None
                i += 1
                continue
            if ch == "'":
                # 只有"紧贴着变量/右括号"的单引号才是转置运算符；
                # `case 'circle'` 这种前面是空格的必须是字符串开始
                prev = res[-1] if res else ""
                if prev and not prev.isspace() and (prev.isalnum() or prev in ")]}._"):
                    res.append(ch)
                    i += 1
                    continue
                quote = "'"
                i += 1
                continue
            if ch == '"':
                quote = '"'
                i += 1
                continue
            if ch == "%":
                break
            res.append(ch)
            i += 1
        out_lines.append("".join(res))
    return out_lines


def main(path: Path) -> int:
    src = path.read_text(encoding="utf-8")
    lines = strip_comments_and_strings(src)
    code = "\n".join(lines)

    defined: set[str] = set()
    funcs: set[str] = set()

    for m in re.finditer(
        r"^\s*function\s+(?:\[([^\]]*)\]\s*=\s*|(\w+)\s*=\s*)?(\w+)\s*(?:\(([^)]*)\))?",
        code, re.M,
    ):
        outs, single_out, fname, args = m.groups()
        funcs.add(fname)
        defined.add(fname)
        for group in (outs, single_out, args):
            if group:
                for name in re.split(r"[,\s]+", group.strip()):
                    if name:
                        defined.add(name)

    # LHS 赋值：name = / name(i) = / name{i} = / [a,b] = / a.b = （字段不算新变量）
    for m in re.finditer(r"^\s*(\[[^\]]*\]|\w+(?:\{[^}]*\}|\([^)]*\))?(?:\{\d+\}|\(\d+\))?)\s*=(?!=)", code, re.M):
        lhs = m.group(1)
        base = re.match(r"\s*\[?\s*([A-Za-z]\w*)", lhs)
        names = re.findall(r"[A-Za-z]\w*", lhs)
        if lhs.strip().startswith("["):
            for n in names:
                defined.add(n)
        elif base and not re.search(r"\)\s*$|\}\s*$", lhs.split(".")[0]):
            defined.add(base.group(1))
    for m in re.finditer(r"\[([^\]]*)\]\s*=(?!=)", code):
        for n in re.findall(r"[A-Za-z]\w*", m.group(1)):
            defined.add(n)
    for m in re.finditer(r"\bfor\s+([A-Za-z]\w*)\s*=", code):
        defined.add(m.group(1))
    for m in re.finditer(r"\b(?:persistent|global)\s+([^\n;]*)", code):
        for n in re.findall(r"[A-Za-z]\w*", m.group(1)):
            defined.add(n)
    for m in re.finditer(r"\bcatch\s+([A-Za-z]\w*)", code):
        defined.add(m.group(1))

    known = defined | funcs | BUILTIN | PTB | KEYWORDS

    used: dict[str, int] = {}
    for lineno, line in enumerate(lines, 1):
        for m in re.finditer(r"(?<![\w.])([A-Za-z]\w*)", line):
            name = m.group(1)
            after = line[m.end():]
            if re.match(r"\s*\(", after):
                continue      # 函数调用/索引，另行处理
            if name in KEYWORDS:
                continue
            used.setdefault(name, lineno)

    # 函数调用名也要查（否则漏掉 resolveEscKeyCode 这类）
    for m in re.finditer(r"(?<![\w.])([A-Za-z]\w*)\s*\(", code):
        name = m.group(1)
        if name in KEYWORDS:
            continue
        used.setdefault(name, code[: m.start()].count("\n") + 1)

    unknown = {k: v for k, v in used.items() if k not in known}
    print(f"文件行数 = {len(lines)}；已定义名字 {len(defined)} 个、函数 {len(funcs)} 个")
    if unknown:
        print(f"❌ 共 {len(unknown)} 个『被使用但未见赋值/定义』的标识符：")
        for k in sorted(unknown, key=lambda x: unknown[x]):
            print(f"    L{unknown[k]:>5}  {k}")
        return len(unknown)
    print("✅ 没有发现未定义的标识符")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "Exp_Design_Formal.m")))
