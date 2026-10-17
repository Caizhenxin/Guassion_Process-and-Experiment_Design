# -*- coding: utf-8 -*-
"""把 D57 **写完之后**的自查结果补进四份文档（决策 D57 的第二批落纸）。

为什么会有这一批
----------------
`_apply_d57.py` 落纸时，报告生成器与它的自测报的是 **`stage9_report.py` 323 行 /
`check_stage9_report.py` 286 行、40/40**。落纸之后我又做了三件事，每一件都改掉了上面的数字，
而且**每一件都是「自测测的不是交付的那份东西」这一族**：

1. 磁盘上的 `1_Code/AutoRA_SPE/stage9_report.md` 带着一条**不该出现**的「旧版措辞」告警 ——
   报告的告警触发器原先读 `compare` 行里**不存在的旧键**（`B_at_best_A`）⇒ 四臂全为有限值时
   也判定为「含 `inf`」并印出一整段假告警。重跑生成器后消失。
2. `check_stage9_report.py` 原先只比对 `R.build(_REAL)`（**内存里重新生成**的报告），
   而交付件是磁盘上那一份 ⇒ 「修正后的措辞不得出现」这条判据**永远绿**，假告警因此从未被发现。
   新增 **R1l**：交付件必须与当前生成器的输出**逐字相同**。
3. R1l 第一次运行就红了 —— 暴露出报告头原先写 `payload_path.as_posix()`，
   于是**生成结果取决于调用方式**（CLI 相对路径 vs 自测绝对路径）。修法 = `_canonical()`
   （仓库内路径一律渲染成相对仓库根的 `posix` 形式）+ 新增 **R2i**。

本脚本只做两类改动：
  A. 数字更正：`323 行 → 337 行`、`286 行 → 304 行`、`40/40 → 42/42`（逐文件断言出现次数）；
  B. 把上面三件事写进正文（表格行在**最后一个单元格内**追加，列表处**插新项**）。

体例沿用 `_apply_d47`–`_apply_d57`：前缀定位 + 命中次数断言 + 竖线数不变 + 幂等守卫 +
输出以换行结尾；干跑（不加 `--apply`）只打印将要做的改动。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # 1_Code/DDM_Core/_scratch → 1_Code/DDM_Core → 1_Code → 仓库根

MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
RA = ROOT / "1_Code" / "AutoRA_SPE" / "README.md"
RM = ROOT / "1_Code" / "DDM_Core" / "README.md"

LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)


def n_sep(s: str) -> int:
    """未被反斜杠转义的竖线数（表格列数判据）。"""
    n, i = 0, 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "|":
            n += 1
        i += 1
    return n


def repl(text: str, old: str, new: str, what: str, expect: int) -> str:
    """逐文件数字更正：命中数必须严格等于 expect；已经改过（命中 0、新值在）则视为幂等跳过。"""
    k = text.count(old)
    if k == 0 and new in text:
        log(f"  ⏭️  幂等跳过：{what}（已是新值）")
        return text
    assert k == expect, f"❌ {what}：期望命中 {expect} 次，实际 {k} 次（old={old!r}）"
    log(f"  ✏️  {what}：{old} → {new}（{k} 处）")
    return text.replace(old, new)


def find_line(text: str, prefix: str, what: str) -> int:
    ls = text.splitlines()
    hit = [i for i, ln in enumerate(ls) if ln.startswith(prefix)]
    assert len(hit) == 1, f"❌ {what}：前缀命中 {len(hit)} 行，期望 1（prefix={prefix[:70]!r}）"
    return hit[0]


def append_in_row(text: str, prefix: str, extra: str, what: str, guard: str) -> str:
    """把 extra 追加到**该表格行最后一个单元格内部**（闭合竖线之前），竖线数必须不变。"""
    if guard in text:
        log(f"  ⏭️  幂等跳过：{what}")
        return text
    ls = text.splitlines()
    i = find_line(text, prefix, what)
    ln = ls[i].rstrip()
    assert ln.endswith("|"), f"❌ {what}：该行不以闭合竖线结尾 ⇒ 拒绝改写"
    before = n_sep(ln)
    j = ln.rfind("|")
    ls[i] = ln[:j].rstrip() + extra.rstrip() + " |"
    assert n_sep(ls[i]) == before, f"❌ {what}：竖线数变了（{before} → {n_sep(ls[i])}）"
    assert ls[i].endswith("|"), f"❌ {what}：改写后不以闭合竖线结尾"
    log(f"  ✏️  {what}：在行内追加 {len(extra)} 字符（竖线数 {before} 不变）")
    return "\n".join(ls) + "\n"


def ins_after(text: str, prefix: str, new_lines: list[str], what: str, guard: str) -> str:
    """在锚点行**之后**插入若干行（列表项处用；插入内容不自带空行）。"""
    if guard in text:
        log(f"  ⏭️  幂等跳过：{what}")
        return text
    ls = text.splitlines()
    i = find_line(text, prefix, what)
    ls[i + 1 : i + 1] = new_lines
    log(f"  ✏️  {what}：在 L{i + 1} 之后插入 {len(new_lines)} 行")
    return "\n".join(ls) + "\n"


def check_breaks(text: str, what: str) -> None:
    """断表断言：本脚本只改表格行内部与列表之间，不应产生空行插入表格。"""
    ls = text.splitlines()
    bad = []
    for i in range(1, len(ls) - 1):
        if ls[i].strip() == "" and ls[i - 1].lstrip().startswith("|") and ls[i + 1].lstrip().startswith("|"):
            bad.append(i + 1)
    assert not bad, f"❌ {what}：表格被空行截断（行号 {bad}）"


# ===== B 段追加文本（数字替换之后才追加，故正文里写的是「更正后」的数字） =====

S9_12_TAIL = (
    "；**D57 写完之后的自查又补两条牙齿**：**R1l** 交付件 `1_Code/AutoRA_SPE/stage9_report.md` 必须与"
    "生成器现输出**逐字相同**（原先只比内存里重生成的那份 ⇒ 磁盘上一条假告警从未被发现）、"
    "**R2i** payload 路径渲染必须**与调用方式无关**（新增 `_canonical()`）⇒ "
    "`check_stage9_report.py` 286 → **304 行、42/42**、`stage9_report.py` 323 → **337 行**"
)

S9_ROW_TAIL = (
    "；**D57 后自查补两条牙齿**：**R1l** 交付件 `stage9_report.md` 必须与生成器现输出**逐字相同**"
    "（原先只比内存里重生成的那份 ⇒ 磁盘上那条假告警从未被发现）、**R2i** payload 路径渲染必须"
    "**与调用方式无关**（原先写 `payload_path.as_posix()` ⇒ 相对/绝对路径生成的文件不同，"
    "而差异只出现在头部，最难被发现）"
)

S9_11_22 = [
    "22. **报告是交付件 ⇒ 两件事必须成对**：① 自测要比对**磁盘上那一份**（只比内存里重新生成的，"
    "等于没测交付件 —— D57 的假告警就是这么漏过去的）；② 生成结果必须**与调用方式无关**"
    "（路径渲染成相对仓库根的规范形式）—— 否则同一个人用相对/绝对路径调用会得到两个不同的"
    "「同一份」报告，差异还只出现在头部。",
]

RA_ROW_TAIL = (
    "；**D57 后自查补两条牙齿**：**R1l** 交付件 `stage9_report.md` 与生成器现输出逐字相同、"
    "**R2i** payload 路径渲染与调用方式无关（`_canonical()`）⇒ **42/42**"
)

RM_5_6 = [
    "6. **D57 写完之后的自查又揪出三处**（全部属于「自测测的不是交付的那份东西」这一族）："
    "① 报告 §5 的「旧版措辞」告警原先读 `compare` 行里**不存在的旧键** `B_at_best_A` ⇒ "
    "四臂全为有限值时也印出一整段假告警（重跑生成器后消失）；"
    "② `check_stage9_report.py` 原先只比对 `R.build(_REAL)`（**内存里重新生成**的报告）⇒ "
    "磁盘上那条假告警从未被发现 ⇒ 新增 **R1l**（交付件必须与现输出逐字相同）；"
    "③ R1l 第一次运行即红，暴露出报告头原先印 `payload_path.as_posix()` ⇒ **生成结果取决于调用方式**"
    "（相对 vs 绝对）⇒ 新增 `_canonical()` 与 **R2i**。⇒ 286 → **304 行、42/42**。",
]

RM_41_TAIL = (
    " ⇒ **D57 后自查补 R1l（交付件必须与现输出逐字相同）与 R2i（路径渲染与调用方式无关、`_canonical()`）"
    "两条牙齿 ⇒ 304 行、42/42**"
)

MP_DEC_TAIL = (
    " ⑥ **D57 写完之后的自查又揪出三处**（全属「自测测的不是交付的那份东西」）：报告 §5 的"
    "「旧版措辞」告警原先读 `compare` 行的**旧键** ⇒ 四臂全为有限值时也印假告警；"
    "`check_stage9_report.py` 原先只比**内存里重新生成**的报告 ⇒ 磁盘上那条假告警从未被发现"
    "（新增 **R1l**）；R1l 首次运行即红，暴露报告头写 `payload_path.as_posix()` ⇒ "
    "**生成结果取决于调用方式**（新增 `_canonical()` + **R2i**）。"
    "⇒ `stage9_report.py` 323 → **337 行**、`check_stage9_report.py` 286 → **304 行、42/42**"
)

MP_PROG_TAIL = (
    "；**D57 后自查**又补两条牙齿（**R1l** 交付件逐字一致 / **R2i** 路径渲染与调用方式无关，"
    "新增 `_canonical()`）⇒ `1_Code/AutoRA_SPE/stage9_report.py` **337 行**、"
    "`1_Code/AutoRA_SPE/check_stage9_report.py` **304 行、42/42**、`exit 0`"
)


def patch_mp(text: str) -> str:
    log("【工作流_主计划.md】")
    text = repl(text, "323 行", "337 行", "主计划 stage9_report.py 行数", 4)
    text = repl(text, "286 行", "304 行", "主计划 check_stage9_report.py 行数", 4)
    text = repl(text, "40/40", "42/42", "主计划报告自测项数", 6)
    text = append_in_row(text, "| **D57** | 2026-10-14 |", MP_DEC_TAIL, "D57 决策行补⑥", "⑥ **D57 写完之后的自查又揪出三处**")
    text = append_in_row(text, "| 2026-10-14 | **9**（无人可行点混排 + 落盘报告 → D57） |",
                         MP_PROG_TAIL, "D57 进度行补自查结果", "**D57 后自查**又补两条牙齿")
    check_breaks(text, "主计划")
    return text


def patch_s9(text: str) -> str:
    log("【Stage9_设计空间优化与论文整合方案.md】")
    text = repl(text, "323 行", "337 行", "Stage9 stage9_report.py 行数", 2)
    text = repl(text, "286 行", "304 行", "Stage9 check_stage9_report.py 行数", 2)
    text = repl(text, "40/40", "42/42", "Stage9 报告自测项数", 3)
    text = append_in_row(text, "| 2026-10-14 | **无人可行点的臂不得混排 + 报告必须由落盘件生成（决策 D57）**",
                         S9_12_TAIL, "§12 D57 行补自查结果", "自查又补两条牙齿")
    text = append_in_row(text, "| `1_Code/AutoRA_SPE/check_stage9_report.py` |",
                         S9_ROW_TAIL, "§9 自测行补两条牙齿", "**D57 后自查补两条牙齿**")
    text = ins_after(text, "21. ❗ **裁决与报告的呈现纪律（D57）**", S9_11_22, "§11 新增第 22 条", "22. **报告是交付件")
    check_breaks(text, "Stage9")
    return text


def patch_ra(text: str) -> str:
    log("【1_Code/AutoRA_SPE/README.md】")
    text = repl(text, "323 行", "337 行", "AutoRA README stage9_report.py 行数", 1)
    text = repl(text, "286 行", "304 行", "AutoRA README check_stage9_report.py 行数", 1)
    text = repl(text, "40/40", "42/42", "AutoRA README 报告自测项数", 1)
    text = append_in_row(text, "| `check_stage9_report.py` |",
                         RA_ROW_TAIL, "§7 自测行补两条牙齿", "**D57 后自查补两条牙齿**")
    check_breaks(text, "AutoRA README")
    return text


def patch_rm(text: str) -> str:
    log("【1_Code/DDM_Core/README.md】")
    text = repl(text, "323 行", "337 行", "DDM README stage9_report.py 行数", 2)
    text = repl(text, "286 行", "304 行", "DDM README check_stage9_report.py 行数", 1)  # §5 那条只写 42/42，不写行数
    text = repl(text, "40/40", "42/42", "DDM README 报告自测项数", 2)
    text = ins_after(text, "5. 报告第 7 节：推荐点", RM_5_6, "§8.32 §5 新增第 6 条", "6. **D57 写完之后的自查又揪出三处**")
    # ⚠️ `| 41 | ` 在本文件里有 3 处（其它表也用同一套序号）⇒ 前缀必须带上标签才唯一。
    text = append_in_row(text, "| 41 | ✅ **「没有可行点的臂不得混排」与「报告必须由落盘件生成」已落地（D57，§8.32）**",
                         RM_41_TAIL, "§9 第 41 项补两条牙齿", "**D57 后自查补 R1l**")
    check_breaks(text, "DDM README")
    return text


def main() -> int:
    apply = "--apply" in sys.argv
    for path, fn in ((MP, patch_mp), (S9, patch_s9), (RA, patch_ra), (RM, patch_rm)):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n"), f"❌ {path.name}：原文不以换行结尾"
        new = fn(text)
        assert new.endswith("\n"), f"❌ {path.name}：输出不以换行结尾"
        assert len(new) != len(text) or new == text, f"❌ {path.name}：没有变化"
        if apply:
            path.write_text(new, encoding="utf-8", newline="\n")
            log(f"  💾 已写盘：{path.relative_to(ROOT).as_posix()}（{len(new.splitlines())} 行）")
        else:
            log(f"  🔬 干跑：{path.relative_to(ROOT).as_posix()}（{len(text.splitlines())} → {len(new.splitlines())} 行）")
        log("")
    print("\n".join(LOG))
    print("干跑结束（未写盘）。加 --apply 落盘。" if not apply else "已落盘。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
