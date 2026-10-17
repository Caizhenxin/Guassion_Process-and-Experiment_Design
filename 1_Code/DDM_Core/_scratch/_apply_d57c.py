# -*- coding: utf-8 -*-
"""D57 收尾：把两件**落纸之后才做到**的事补进文档。

1. **逐位复现**：同一组参数（`--budget 12 --n-fim 1 --noise-repeats 2 --seed 0`）独立重跑一次，
   与既有落盘件 `1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json` 比较 ⇒
   除逐臂**墙钟 `seconds`** 与 D57 改名的键 `B_at_best_A → B_at_A_best` 外，
   `settings` / `front_scope` / `d54` / `spec_sha256` / `n_evals` / `best` / `anchor` /
   `pareto` / `noise` 以及 `cache` 的 **174** 个设计**逐位相同**（差异 0 个）。
   ⇒ 报告里的数字不是"这次跑得巧"。
2. **全套汇总自测的耗时**：§9 的 `check_stage9.py` 行原写 `140.7 s`（D55 时代读数）。
   本脚本从刚落盘的 `1_Code/AutoRA_SPE/_scratch_agg_console_u8.txt` **现算**新读数再写入，
   不手抄 —— 手抄上一次运行的耗时正是本仓库反复记录的失配来源。

体例：前缀定位 + 命中次数断言 + 竖线数不变 + 幂等守卫 + 输出以换行结尾；干跑不加 `--apply`。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
RM = ROOT / "1_Code" / "DDM_Core" / "README.md"
AGG = ROOT / "1_Code" / "AutoRA_SPE" / "_scratch_agg_console_u8.txt"

LOG: list[str] = []


def log(m: str) -> None:
    LOG.append(m)


def n_sep(s: str) -> int:
    n, i = 0, 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "|":
            n += 1
        i += 1
    return n


def agg_seconds() -> float:
    """从刚跑完的汇总自测日志里**现算**总耗时（不手抄）。

    ⚠️ 该日志是 PowerShell 的 `>` 重定向产物，**编码可能是 UTF-16LE**（PS 5.1 默认），
    直接 `read_text(encoding="utf-8")` 会得到满屏替换字符、正则一条都匹配不上 ⇒
    这里按 utf-8 / utf-16 两种编码试解，取能认出「总耗时」的那一个。
    """
    assert AGG.exists(), f"❌ 缺 {AGG}（先跑 `python -u 1_Code/AutoRA_SPE/check_stage9.py`）"
    raw = AGG.read_bytes()
    text = ""
    for enc in ("utf-8", "utf-16"):
        try:
            cand = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if "总耗时" in cand:
            text = cand
            break
    assert text, "❌ 汇总日志读了两种编码都认不出「总耗时」（文件内容异常？）"
    ms = re.findall(r"总耗时\s*([\d.]+)\s*s", text)
    assert ms, "❌ 汇总日志里找不到「总耗时 … s」"
    assert "未通过 0 项" in text, "❌ 汇总日志不是全绿读数 ⇒ 不用它写文档"
    return float(ms[-1])


def find_line(text: str, prefix: str, what: str) -> int:
    ls = text.splitlines()
    hit = [i for i, ln in enumerate(ls) if ln.startswith(prefix)]
    assert len(hit) == 1, f"❌ {what}：前缀命中 {len(hit)} 行，期望 1"
    return hit[0]


def append_in_row(text: str, prefix: str, extra: str, what: str, guard: str) -> str:
    if guard in text:
        log(f"  ⏭️  幂等跳过：{what}")
        return text
    ls = text.splitlines()
    i = find_line(text, prefix, what)
    ln = ls[i].rstrip()
    assert ln.endswith("|"), f"❌ {what}：该行不以闭合竖线结尾"
    before = n_sep(ln)
    j = ln.rfind("|")
    ls[i] = ln[:j].rstrip() + extra.rstrip() + " |"
    assert n_sep(ls[i]) == before, f"❌ {what}：竖线数变了"
    log(f"  ✏️  {what}：行内追加 {len(extra)} 字符（竖线数 {before} 不变）")
    return "\n".join(ls) + "\n"


def ins_after(text: str, prefix: str, new_lines: list[str], what: str, guard: str) -> str:
    if guard in text:
        log(f"  ⏭️  幂等跳过：{what}")
        return text
    ls = text.splitlines()
    i = find_line(text, prefix, what)
    ls[i + 1 : i + 1] = new_lines
    log(f"  ✏️  {what}：在 L{i + 1} 之后插入 {len(new_lines)} 行")
    return "\n".join(ls) + "\n"


def repl(text: str, old: str, new: str, what: str, expect: int) -> str:
    k = text.count(old)
    if k == 0 and new in text:
        log(f"  ⏭️  幂等跳过：{what}")
        return text
    assert k == expect, f"❌ {what}：期望 {expect} 处，实际 {k} 处（old={old!r}）"
    log(f"  ✏️  {what}：{old} → {new}（{k} 处）")
    return text.replace(old, new)


RM_5_7 = [
    "7. **逐位复现**（`python -u 1_Code/AutoRA_SPE/_scratch_cmp_payloads.py <旧.json> <新.json>`）："
    "同一组参数（`--budget 12 --n-fim 1 --noise-repeats 2 --seed 0`）独立重跑一次 ⇒ "
    "`1_Code/AutoRA_SPE/_scratch_smoke_scope_b12b.json`（**346512 字节**，与旧件**同字节数**）："
    "`settings` / `front_scope` / `d54` / `spec_sha256` / `n_evals` / `best` / `anchor` / "
    "`pareto` / `noise` 以及 `cache` 的 **174** 个设计**逐位相同**（差异 **0** 个）；"
    "唯一不同的是逐臂**墙钟 `seconds`**（`random` 34.7 → 35.5 s、`grid` 35.4 → 32.3 s、"
    "`manual` 32.6 → 32.0 s、`bo` 2.8 → 2.6 s）与 D57 改名的键 "
    "`B_at_best_A` → `B_at_A_best`。⇒ **同一 seed 下设计值与判据完全可复现**，"
    "报告里的数字不是「这次跑得巧」；同时 ⇒ 比较两次运行时必须先排除 `seconds`，"
    "否则会把计时噪声当成「结果不稳定」（本探针第一版正是这么误报 5 处差异的）。",
]

MP_PROG_TAIL = (
    "；**逐位复现**：同参数独立重跑（`1_Code/AutoRA_SPE/_scratch_smoke_scope_b12b.json`，346512 字节）"
    "除逐臂墙钟 `seconds` 外**逐位相同**（`1_Code/AutoRA_SPE/_scratch_cmp_payloads.py`：0 处差异）"
)

S9_12_TAIL = (
    "；**逐位复现**：同参数独立重跑（`_scratch_smoke_scope_b12b.json`）除逐臂墙钟 `seconds` 外"
    "`settings`/`front_scope`/`d54`/`best`/`anchor`/`pareto`/`noise` 与 `cache` 的 174 个设计"
    "**逐位相同**"
)


def repl_in_row(text: str, prefix: str, old: str, new: str, what: str, expect: int) -> str:
    """只在**某一行内部**做替换（`§9` 的当前状态行 vs `§12` 的历史记录行都含同一个旧读数，
    全篇替换会篡改历史记录）。"""
    ls = text.splitlines()
    i = find_line(text, prefix, what)
    k = ls[i].count(old)
    if k == 0 and new in ls[i]:
        log(f"  ⏭️  幂等跳过：{what}")
        return text
    assert k == expect, f"❌ {what}：该行内期望 {expect} 处，实际 {k} 处（old={old!r}）"
    ls[i] = ls[i].replace(old, new)
    log(f"  ✏️  {what}：L{i + 1} 行内 {old} → {new}（{k} 处）")
    return "\n".join(ls) + "\n"


def main() -> int:
    apply = "--apply" in sys.argv
    sec = agg_seconds()
    new_s = f"{sec:.1f} s"
    log(f"【现算读数】汇总自测总耗时 = {new_s}（来源 {AGG.name}）")
    S9_ROW = "| `1_Code/AutoRA_SPE/check_stage9.py` |"
    S9_12 = "| 2026-10-14 | **无人可行点的臂不得混排 + 报告必须由落盘件生成（决策 D57）**"
    edits = {
        MP: lambda t: append_in_row(t, "| 2026-10-14 | **9**（无人可行点混排 + 落盘报告 → D57） |",
                                    MP_PROG_TAIL, "主计划 D57 进度行补逐位复现", "**逐位复现**"),
        # ⚠️ `140.7 s` 在 Stage9 里有两处：§9 的**当前状态行**要改成新读数，
        #    §12 的 D55 行是**历史记录**（那时确实是 140.7 s）⇒ 只改行内，不全篇替换。
        # ⚠️ 幂等守卫必须**足够长**：`**逐位复现**` 这几个字在 Stage9 里早已出现过（§2/§3 提到
        #    「逐位复现」的其它语境）⇒ 用它当守卫会让本条编辑被静默跳过。守卫取本句开头。
        S9: lambda t: repl_in_row(
            append_in_row(t, S9_12, S9_12_TAIL, "Stage9 §12 D57 行补逐位复现",
                          "**逐位复现**：同参数独立重跑（`_scratch_smoke_scope_b12b.json`）"),
            S9_ROW, "140.7 s", new_s, "Stage9 §9 当前状态行的汇总耗时", 1),
        RM: lambda t: ins_after(t, "6. **D57 写完之后的自查又揪出三处**", RM_5_7,
                                "DDM README §8.32 §5 新增第 7 条", "7. **逐位复现**"),
    }
    for path, fn in edits.items():
        log(f"【{path.relative_to(ROOT).as_posix()}】")
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        new = fn(text)
        assert new.endswith("\n")
        if apply:
            path.write_text(new, encoding="utf-8", newline="\n")
            log(f"  💾 已写盘（{len(new.splitlines())} 行）")
        else:
            log(f"  🔬 干跑（{len(text.splitlines())} → {len(new.splitlines())} 行）")
        log("")
    print("\n".join(LOG))
    print("干跑结束（未写盘）。加 --apply 落盘。" if not apply else "已落盘。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
