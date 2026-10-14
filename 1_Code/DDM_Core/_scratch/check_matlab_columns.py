"""静态检查 `Exp_Design_Formal.m` 的输出列一致性（Stage 1 修正 #3 的证据之一）。

本机没有 MATLAB，无法运行程序，所以只能对着源码做一致性核对。检查五件事：

1. Stage 1 新增/改写的本地函数是否都真的有定义；
2. 练习阶段与正式阶段 `data{trialIndex, N}` 的列号集合是否都是 1..25 且不缺号；
3. `columnNames`（交给 `writetable` 的表头）与逐试次 `fprintf(fileID, ...)` 写出的
   表头是否逐字一致、个数是否都等于 25；
4. 两处逐试次 `fprintf(fileID, ...)` 的格式串占位符个数是否等于 25；
5. 【v4.1】第 9/10 列（T、W）的打印精度是否仍能区分设计里的每一档。
   T 在程序内部是【秒】：2/5/9/15 帧 = 0.03333/0.08333/0.14999/0.24998 s。
   旧的 `%.1f` 会把 83.33 ms 与 149.99 ms 都打成 `0.1` ⇒ 被试内因子 T 被静默摧毁。
   本项直接拿 `T_nominal`/`W_nominal` 按格式串实打一次，要求各档字符串两两不同。

用法（在 `1_Code/Experiment/exp_matlab/` 下）：
    python ../../DDM_Core/_scratch/check_matlab_columns.py Exp_Design_Formal.m
未找到问题返回 0，发现不一致返回 1。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

N_COLS = 25
STAGE1_FUNCS = [
    "checkEscape",
    "deg2pix",
    "escAbort",
    "getMatchKey",
    "getPairingRules",
    "kqCountPresses",
    "kqFirstPressUntil",
    "kqScan",
    "resolveEscKeyCode",
]

_ASSIGN = re.compile(r"data\{trialIndex,\s*(\d+)\}")
_STAGE = re.compile(r'data\{trialIndex,\s*6\}\s*=\s*"?(\w+)"?')
# `function f(...)` / `function y = f(...)` / `function [a, b] = f(...)` —— 一律取 `(` 前那个名字
_FUNC = re.compile(r"^\s*function\b[^(]*?(\w+)\s*\(", re.I)
_QUOTED = re.compile(r"'([^']*)'")
# 源码里 `data{trialIndex, 6}` 的取值 → 报告里用的中文名
_PHASE_LABEL = {"practice": "练习", "formal": "正式"}


def _strip_comment(line: str) -> str:
    """去掉 MATLAB 行尾注释，但【不】把字符串里的 % 当注释。

    旧写法是 `line.split("%")[0]`，会把格式串 `'%d\\t%d...'` 从第一个 % 处整段砍掉，
    于是第 4/5 项检查永远拿不到格式串、静默失效（只剩前 3 项在报 ✅）。
    MATLAB 单引号字符串用两个连续单引号表示一个引号，这里按此扫描。
    """
    in_str = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'":
            if in_str and i + 1 < len(line) and line[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
        elif ch == "%" and not in_str:
            return line[:i]
        i += 1
    return line


def _logical_lines(text: str) -> list[str]:
    """把 MATLAB 的 `...` 续行合并成逻辑行，便于对整条语句做正则。"""
    out: list[str] = []
    buf = ""
    for raw in text.split("\n"):
        stripped = _strip_comment(raw).rstrip()
        if stripped.endswith("..."):
            buf += stripped[:-3]
            continue
        out.append(buf + stripped)
        buf = ""
    if buf:
        out.append(buf)
    return out


def _placeholders(fmt: str) -> int:
    """数一个 printf 格式串里的转换说明符个数（`%%` 不算，转义序列不算）。"""
    return len(re.findall(r"%(?!%)[-+ #0-9.]*[diouxXeEfgGsc]", fmt))


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "Exp_Design_Formal.m")
    text = path.read_text(encoding="utf-8")
    logical = _logical_lines(text)
    problems: list[str] = []

    # ---- 1. 本地函数 ----
    funcs = sorted({m.group(1) for m in (_FUNC.match(l) for l in logical) if m})
    missing = [f for f in STAGE1_FUNCS if f not in funcs]
    print(f"本地函数定义（{len(funcs)}）：" + ", ".join(funcs))
    if missing:
        problems.append(f"缺少本地函数定义：{missing}")
        print(f"  ❌ 未找到定义：{missing}")
    else:
        print("  ✅ Stage 1 新增/改写的本地函数全部有定义")

    # ---- 2. 两阶段的列号集合 ----
    # 注意：`data{trialIndex, 6} = "<阶段名>"` 只是这个阶段 25 条赋值里的第 6 条，
    # 所以不能"按它之前/之后的行"来划阶段——否则第 1–5 条会被算到上一个阶段去。
    # 正确做法：以每处阶段标记为锚，向【上】回退 10 行作为该阶段的起点，
    # 一直到下一处标记的起点为止；并且跳过 fprintf 的参数区（那里也会出现
    # `data{trialIndex, N}`，但它不是赋值）。
    raw_lines = text.split("\n")
    anchors = [
        (i, m.group(1))
        for i, line in enumerate(raw_lines)
        if (m := _STAGE.search(line))
    ]
    if not anchors:
        problems.append("找不到 `data{trialIndex, 6}` 阶段标记，无法按阶段核对列号")
        print("  ❌ 找不到阶段标记")
    cols: dict[str, set[int]] = {}
    for k, (start, phase_name) in enumerate(anchors):
        begin = max(0, start - 10)
        end = max(0, anchors[k + 1][0] - 10) if k + 1 < len(anchors) else len(raw_lines)
        bucket = cols.setdefault(phase_name, set())
        for line in raw_lines[begin:end]:
            if "fprintf" in line or line.count("data{trialIndex,") != 1:
                continue
            m = _ASSIGN.search(line)
            if m:
                bucket.add(int(m.group(1)))
    for name, label in (("practice", "练习"), ("formal", "正式")):
        got = cols.get(name, set())
        want = set(range(1, N_COLS + 1))
        if got == want:
            print(f"  ✅ {label}阶段列号：[1..{N_COLS} 全]")
        else:
            gap = sorted(want - got)
            extra = sorted(got - want)
            problems.append(f"{label}阶段列号不完整：缺 {gap}、多 {extra}")
            print(f"  ❌ {label}阶段列号：缺 {gap}、多 {extra}")

    # ---- 3. columnNames 与写入表头 ----
    # `columnNames` 的赋值被 `...` 续行合并成【一条】逻辑行，所以只取那一条即可，
    # 否则会一路扫到文件末尾、把后面所有字符串字面量都当成列名。
    colnames: list[str] = []
    for line in logical:
        if re.search(r"columnNames\s*=\s*\{", line):
            colnames = [c for c in _QUOTED.findall(line) if re.fullmatch(r"\w+", c)]
            break

    header: list[str] = []
    for idx, line in enumerate(logical):
        if "fprintf(fileID" in line and "\\t" in line:
            spec = "".join(_QUOTED.findall(line))
            if "groupID" in spec:  # 表头那一处
                header = [c for c in spec.split("\\t") if c]
                break
    if header and header[-1].endswith("\\n"):
        header[-1] = header[-1][:-2]

    if len(colnames) == N_COLS and header == colnames:
        print(f"  ✅ columnNames 个数 = {N_COLS}，与 {N_COLS} 列表头逐字一致")
    else:
        if len(colnames) != N_COLS:
            problems.append(f"columnNames 个数 = {len(colnames)}，应为 {N_COLS}")
        if header != colnames:
            problems.append(f"写入表头与 columnNames 不一致：表头 {len(header)} 个")
            for i, (a, b) in enumerate(zip(header + [""] * N_COLS, colnames + [""] * N_COLS), 1):
                if a != b:
                    print(f"    ✗ 第 {i} 列：表头 {a!r} vs columnNames {b!r}")
        print(f"  ❌ columnNames {len(colnames)} 个，表头 {len(header)} 个")

    # ---- 4. 逐试次 fprintf 的占位符个数 ----
    n_printf = 0
    for line in logical:
        if "fprintf(fileID" in line and "%d" in line:
            n_printf += 1
            spec = "".join(_QUOTED.findall(line))
            n_ph = _placeholders(spec)
            if n_ph != N_COLS:
                problems.append(f"第 {line[:40]!r} 处 fprintf 占位符 {n_ph} 个，应为 {N_COLS}")
                print(f"  ❌ 占位符 {n_ph} 个 ≠ {N_COLS}")
    if n_printf and not any("占位符" in p for p in problems):
        print(f"  ✅ fprintf(fileID) 占位符个数 = {N_COLS}（{n_printf} 处）")

    # ---- 5. T/W 打印精度必须保留设计的每一档（v4.1 教训）----
    # 第 9/10 列在程序内部是【秒】，而 v3 继承下来的格式串用的是 %.1f：
    # 0.08333 s 与 0.14999 s 都打成 `0.1` ⇒ 四档 T 变两档，且数值本身失真。
    # 这里把 T_nominal / W_nominal（毫秒，源码里的设计值）换算成秒后按格式串实打一次，
    # 要求各档的字符串两两不同——这直接测"下游还认不认得出 T"。
    _VEC = re.compile(r"^\s*(\w+)\s*=\s*\[\s*([-\d.,\s]+)\]")
    nominal_ms: dict[str, list[float]] = {}
    for line in logical:
        m = _VEC.match(line)
        if m and m.group(1) in ("T_nominal", "W_nominal"):
            nominal_ms[m.group(1)] = [
                float(v) for v in m.group(2).replace(" ", "").split(",") if v
            ]

    data_specs: list[str] = []
    for line in logical:
        if "fprintf(fileID" in line and "%d" in line:
            data_specs = re.findall(
                r"%(?!%)[-+ #0-9.]*[diouxXeEfgGsc]", "".join(_QUOTED.findall(line))
            )
            break

    if len(data_specs) == N_COLS and len(nominal_ms) == 2:
        for col, key, label in ((9, "T_nominal", "T"), (10, "W_nominal", "W")):
            fmt = data_specs[col - 1]
            levels = [ms / 1000.0 for ms in nominal_ms[key]]  # 秒（T_levels 的量化前名义值）
            try:
                shown = [fmt % v for v in levels]
            except (TypeError, ValueError) as exc:
                problems.append(f"第 {col} 列（{label}）格式串 {fmt!r} 无法格式化浮点数：{exc}")
                print(f"  ❌ 第 {col} 列（{label}）格式串 {fmt!r} 不能用于浮点值")
                continue
            if len(set(shown)) == len(shown):
                print(
                    f"  ✅ 第 {col} 列（{label}）打印精度 {fmt} → {shown}"
                    f"（{len(shown)} 档可辨，对应 {'/'.join(f'{ms:g}' for ms in nominal_ms[key])} ms）"
                )
            else:
                problems.append(
                    f"第 {col} 列（{label}）格式串 {fmt!r} 把 {len(levels)} 档打成了 {len(set(shown))} 档：{shown}"
                )
                print(f"  ❌ 第 {col} 列（{label}）打印精度不足：{fmt} → {shown}")
    else:
        problems.append("无法核对 T/W 打印精度（数据行格式串或 T_nominal/W_nominal 没解析到）")
        print("  ❌ 无法核对 T/W 打印精度")

    if problems:
        print(f"\n❌ 共 {len(problems)} 处不一致：")
        for p in problems:
            print(f"   - {p}")
        return 1
    print("\n✅ 输出列一致性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
