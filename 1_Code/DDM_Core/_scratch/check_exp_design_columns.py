"""针对 `Exp_Design_Formal.m` 的静态一致性检查（v4，Stage 1 修正后）。

检查四件事：
  1. 脚本里调用到的本地函数是否都有定义（防止改名后漏定义）；
  2. 练习阶段 / 正式阶段各自给 `data{trialIndex, N}` 赋值的列号是否覆盖 1..25；
  3. 末尾 `columnNames` 的个数与名字；
  4. 每个 `fprintf(fileID, ...)` 格式串的占位符个数（应等于 25）。

用法：python _scratch/check_exp_design_columns.py <Exp_Design_Formal.m 路径>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

N_COLS = 25
EXPECTED_NAMES = [
    "groupID", "subjectID", "gender", "age", "handedness", "stage",
    "trialID", "P", "T", "W", "Shape", "Label", "CorrectKey", "Response", "RT",
    "Correct",
    "block", "premature_press", "timeout", "responded_by_deadline",
    "stimulus_onset_actual", "stimulus_offset_actual", "mask_onset_actual",
    "stimulus_dur_actual", "stimulus_frames",
]
LOCAL_FUNCS = {
    "getPairingRules", "getMatchKey", "deg2pix",
    "resolveEscKeyCode", "escAbort", "checkEscape",
    "kqCountPresses", "kqFirstPressUntil", "kqScan",
}
BUILTIN = {
    "for", "while", "if", "elseif", "else", "switch", "case", "otherwise",
    "try", "catch", "function", "return", "break", "continue", "end",
    "struct", "cell", "zeros", "ones", "table", "string", "char", "double",
    "logical", "numel", "length", "size", "isempty", "isnan", "ischar",
    "ismember", "strcmp", "find", "sum", "mean", "round", "mod", "tan", "pi",
    "sprintf", "fprintf", "fopen", "fclose", "ftell", "error", "warning",
    "disp", "input", "inputdlg", "str2double", "randi", "randperm", "sort",
    "min", "max", "num2str", "mat2str", "any", "all", "cellfun", "arrayfun",
}
PTB = {
    "Screen", "KbName", "KbCheck", "KbQueueCreate", "KbQueueStart",
    "KbQueueFlush", "KbQueueCheck", "KbQueueRelease", "GetSecs", "WaitSecs",
    "DrawFormattedText", "InitializeMatlabOpenGL", "HideCursor", "ShowCursor",
    "CenterRectOnPoint", "imread", "sca", "writetable", "MakeTexture",
}


def check(path: Path) -> int:
    src = path.read_text(encoding="utf-8")
    bad = 0

    defs = set(re.findall(
        r"^function\s+(?:\[[^\]]*\]|\w+)\s*=\s*(\w+)\s*[\(]|^function\s+(\w+)\s*\(",
        src, re.M,
    ))
    defs = {a or b for a, b in defs}
    print(f"本地函数定义（{len(defs)}）：{sorted(defs)}")
    missing_def = LOCAL_FUNCS - defs
    if missing_def:
        print(f"  ❌ 脚本调用但未定义：{sorted(missing_def)}")
        bad += 1
    else:
        print("  ✅ Stage 1 新增/改写的本地函数全部有定义")

    called = set(re.findall(r"(?<![\w.])([A-Za-z]\w*)\s*\(", src))
    unknown = sorted(called - defs - BUILTIN - PTB)
    if unknown:
        print(f"  ⚠️ 未能识别的调用（可能只是白名单不全）：{unknown}")

    def cols(block: str) -> list[int]:
        return sorted({int(m) for m in re.findall(r"data\{trialIndex,\s*(\d+)\}", block)})

    i_prac = src.index("% 练习\n")
    i_form = src.index("%% 匹配阶段-正式实验")
    i_save = src.index("%% 保存数据")
    for label, block in (("练习", src[i_prac:i_form]), ("正式", src[i_form:i_save])):
        got = cols(block)
        missing = [n for n in range(1, N_COLS + 1) if n not in got]
        extra = [n for n in got if n > N_COLS]
        flag = "✅" if not missing and not extra else "❌"
        print(f"  {flag} {label}阶段列号：{got}")
        if missing:
            print(f"      缺列：{missing}")
            bad += 1
        if extra:
            print(f"      越界列：{extra}")
            bad += 1

    m = re.search(r"columnNames = \{(.*?)\};", src, re.S)
    if not m:
        print("  ❌ 找不到 columnNames")
        return bad + 1
    names = re.findall(r"'([^']*)'", m.group(1))
    print(f"  columnNames 个数 = {len(names)}")
    if names == EXPECTED_NAMES:
        print("  ✅ 与 25 列表头逐字一致")
    else:
        print("  ❌ 与预期不一致")
        for i, (a, b) in enumerate(zip(names + [""] * 30, EXPECTED_NAMES + [""] * 30), 1):
            if a != b:
                print(f"      第 {i} 项：实际 {a!r} / 预期 {b!r}")
        bad += 1

    for mm in re.finditer(r"fprintf\(fileID, '([^']*)'", src):
        n = len(re.findall(r"%[-0-9.]*[dsf]", mm.group(1)))
        flag = "✅" if n == N_COLS else "❌"
        print(f"  {flag} fprintf(fileID) 占位符个数 = {n}")
        if n != N_COLS:
            bad += 1

    print("✅ 全部通过" if bad == 0 else f"❌ {bad} 处需要修")
    return bad


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "Exp_Design_Formal.m")
    sys.exit(1 if check(target) else 0)
