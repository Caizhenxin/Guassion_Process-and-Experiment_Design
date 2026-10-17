# -*- coding: utf-8 -*-
"""D59 第二批落纸：把「同族第四条（判词无法归因）」与随之的行数/项数写进四份文档。

背景（D59 当轮，落纸之后才发现）：
    第 5 节的四臂判词是**运行时**生成的冻结文本 —— `stage9_report.py` 只逐字转印
    payload 里的 `compare[*].verdict`，**不重算**。而裁决逻辑已经改过三代：
      D55 之前：`ΔA` 超带却借 `ΔB` 的带子 ⇒ 把 BO 差 32% 印成「不可分辨」（洗白）；
      D55–D58：能判「在 (A) 上显著更差」，但 `ΔA` 在带内时仍借 `ΔB` 的带子下结论；
      D59 起：两根带子**各判各的**。
    ⇒ 落盘件不记录「这批判词出自哪一版规则」，读者无法判断手上这份文本该不该信。

体例（与 `_apply_d56b.py` / `_apply_d57b.py` 一致）：
  * **行前缀定位**（命中数必须为 1）⇒ 只在**该行内**做子串替换，
    因此不会碰到别行里同类数字的历史记录（例如 D58 决策行里的 `47/47`）；
  * 每处替换断言该子串在这一行里出现 **1 次**；脚本尾部保证输出以换行结尾；
  * 默认**干跑**只打印将要改什么，`--apply` 才写盘。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPLY = "--apply" in sys.argv

MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
RA = ROOT / "1_Code" / "AutoRA_SPE" / "README.md"
RM = ROOT / "1_Code" / "DDM_Core" / "README.md"

_FILES: dict[Path, list[str]] = {}
_EDITS = 0


def load(p: Path) -> list[str]:
    if p not in _FILES:
        t = p.read_text(encoding="utf-8")
        _FILES[p] = t.split("\n")
    return _FILES[p]


def find_row(lines: list[str], prefix: str, what: str, after: str | None = None) -> int:
    lo = 0
    if after is not None:
        j = [i for i, ln in enumerate(lines) if ln.startswith(after)]
        assert len(j) == 1, f"❌ {what}：定位锚（after）命中 {len(j)} 行（要求 1）\n   锚：{after[:90]}"
        lo = j[0] + 1
    idx = [i for i in range(lo, len(lines)) if lines[i].startswith(prefix)]
    assert len(idx) == 1, f"❌ {what}：前缀命中 {len(idx)} 行（要求 1）\n   前缀：{prefix[:90]}"
    return idx[0]


def patch_row(lines: list[str], prefix: str, old: str, new: str, what: str,
              after: str | None = None) -> None:
    """只在**前缀唯一命中的那一行内**替换 `old`（该行内必须恰好出现 1 次）。"""
    global _EDITS
    i = find_row(lines, prefix, what, after=after)
    cnt = lines[i].count(old)
    assert cnt == 1, f"❌ {what}：`{old[:60]}` 在该行出现 {cnt} 次（要求 1）"
    lines[i] = lines[i].replace(old, new)
    _EDITS += 1
    print(f"  ✏️ {what}")


def insert_after(lines: list[str], prefix: str, block: list[str], what: str,
                 after: str | None = None) -> None:
    global _EDITS
    i = find_row(lines, prefix, what, after=after)
    lines[i + 1: i + 1] = block
    _EDITS += 1
    print(f"  ➕ {what}（{len(block)} 行）")


def patch_sub(lines: list[str], needle: str, old: str, new: str, what: str,
              after: str | None = None) -> None:
    """按**包含关系**定位行（有些行带缩进，行首前缀匹配会落空）。"""
    global _EDITS
    lo = 0
    if after is not None:
        j = [i for i, ln in enumerate(lines) if ln.startswith(after)]
        assert len(j) == 1, f"❌ {what}：定位锚（after）命中 {len(j)} 行（要求 1）"
        lo = j[0] + 1
    idx = [i for i in range(lo, len(lines)) if needle in lines[i]]
    assert len(idx) == 1, f"❌ {what}：含 `{needle[:50]}` 的行命中 {len(idx)} 行（要求 1）"
    i = idx[0]
    assert lines[i].count(old) == 1, f"❌ {what}：`{old[:60]}` 出现 {lines[i].count(old)} 次（要求 1）"
    lines[i] = lines[i].replace(old, new)
    _EDITS += 1
    print(f"  ✏️ {what}")


def append_in_row(lines: list[str], prefix: str, text: str, what: str,
                  after: str | None = None) -> None:
    """把 `text` 追加到该表格行**最后一个单元格内**（闭合竖线之前）；竖线数不变。

    行尾的 ` |` 在一行里出现多次 ⇒ 不能用 `replace`，必须按 `rpartition` 处理。
    """
    global _EDITS
    i = find_row(lines, prefix, what, after=after)
    row = lines[i]
    assert row.rstrip().endswith("|"), f"❌ {what}：该行不以闭合竖线结尾"
    assert text not in row, f"❌ {what}：该文本已在行内（幂等保护）"
    head = row.rstrip()[:-1].rstrip()
    lines[i] = f"{head} {text} |"
    _EDITS += 1
    print(f"  ✏️ {what}")


def save(p: Path) -> None:
    lines = _FILES[p]
    assert lines[-1] == "" or lines[-1].strip(), f"输出异常：{p.name} 末尾 {lines[-1]!r}"
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    if not APPLY:
        print(f"  ⏸️ 干跑：不写 {p.relative_to(ROOT).as_posix()}")
        return
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"  💾 已写 {p.relative_to(ROOT).as_posix()}（{len(text.splitlines())} 行）")


# ---------------------------------------------------------------- 主计划
def do_master_plan() -> None:
    lines = load(MP)
    print("\n[主计划]")

    # ① D59 决策行：两处历史箭头数字 + 新增「同族第四条」段并重排编号
    row = "| **D59** | 2026-10-16 |"
    patch_row(lines, row, "465 → **530 行、47/47**", "465 → **536 行、48/48**",
              "D59 决策行：check_stage9_loop.py 536 行、48/48")
    patch_row(lines, row, "346 → **362 行、50/50**", "346 → **372 行、52/52**",
              "D59 决策行：check_stage9_report.py 372 行、52/52")
    patch_row(
        lines, row, "⑧ **待办**",
        "⑧ ❗ **同族第四条（判词无法归因）**：第 5 节的判词是**运行时**生成的冻结产物"
        "（报告只逐字转印、不重算），而裁决逻辑改过三代（洗白 / 借另一根带子 / 各判各的）"
        "⇒ 落盘件必须自报规则版本：`1_Code/AutoRA_SPE/stage9_loop.py` 新增 `VERDICT_LOGIC` "
        "常量与 payload 的 `\"verdict_logic\"` 键，`1_Code/AutoRA_SPE/stage9_report.py` §5 印出版本"
        "（缺失则先警「判词可能由已被修正的规则生成」）；牙齿 **H7** 与 **R1p-m/R1p-n** "
        "⇒ 循环自测 465 → **536 行、48/48**（47.8 s）、报告自测 346 → **372 行、52/52**。"
        "⑨ **待办**",
        "D59 决策行：新增同族第四条（判词无法归因）与 H7/R1p-m/n")

    # ② D59 进度行：产出文件与牙齿数字 + 第 ⑥ 条
    prog = "| 2026-10-16 | **9**（判据带宽的标定种子 + 裁决短路 → D59） |"
    patch_row(lines, prog, "（465 → **530 行、47/47**）", "（465 → **536 行、48/48**）",
              "D59 进度行：循环自测 536 行、48/48")
    patch_row(
        lines, prog, "报告自测 346 → **362 行、50/50**）。",
        "报告自测 346 → **372 行、52/52**）。⑥ **同族第四条（判词无法归因）**：判词是运行时生成的"
        "冻结产物（报告只转印、不重算）而规则改过三代 ⇒ `stage9_loop.py` 新增 `VERDICT_LOGIC` "
        "与 payload 的 `\"verdict_logic\"`，报告 §5 印版本（缺失 ⇒ 先警）；牙齿 **H7** + "
        "**R1p-m/n**（循环自测 **48/48**、报告自测 **52/52**）。",
        "D59 进度行：新增第 ⑥ 条（同族第四条与牙齿）")
    patch_row(lines, prog, "831 → **886 行**", "831 → **896 行**",
              "D59 进度行：stage9_loop.py 896 行")
    patch_row(lines, prog, "370 → **397 行**", "370 → **408 行**",
              "D59 进度行：stage9_report.py 408 行")
    patch_row(lines, prog, "（**131 行**）", "（**133 行**）",
              "D59 进度行：stage9_report.md 133 行")

    # ③ 附录证据行
    app = "| `1_Code/AutoRA_SPE/stage9_loop.py`（831 → "
    patch_row(lines, app, "（831 → **886 行**）", "（831 → **896 行**）",
              "附录：stage9_loop.py 896 行")
    patch_row(lines, app, "（465 → **530 行**、**47/47**）", "（465 → **536 行**、**48/48**）",
              "附录：循环自测 536 行、48/48")
    patch_row(lines, app, "（370 → **397 行**）", "（370 → **408 行**）",
              "附录：stage9_report.py 408 行")
    patch_row(lines, app, "（346 → **362 行**、**50/50**）", "（346 → **372 行**、**52/52**）",
              "附录：报告自测 372 行、52/52")
    patch_row(
        lines, app, "⑤ 离线换带重判证明 `n_fim = 1` 的头条不成立",
        "⑤ 离线换带重判证明 `n_fim = 1` 的头条不成立；⑥ 落盘件自报裁决规则版本"
        "（`VERDICT_LOGIC` / `payload[\"verdict_logic\"]`，报告 §5 转印，缺失则先警）",
        "附录：新增第 ⑥ 条（裁决规则版本）")
    save(MP)


# ---------------------------------------------------------------- Stage 9
def do_stage9() -> None:
    lines = load(S9)
    print("\n[Stage 9 方案]")

    l317 = "| `1_Code/AutoRA_SPE/stage9_loop.py` | CRN 预计算表"
    patch_row(lines, l317, "（**886 行**、裸 LF", "（**896 行**、裸 LF",
              "§9 stage9_loop.py 896 行")

    l318 = "| `1_Code/AutoRA_SPE/check_stage9_loop.py` | 优化循环自测"
    patch_row(lines, l318, "（**530 行**、裸 LF", "（**536 行**、裸 LF",
              "§9 check_stage9_loop.py 536 行")
    patch_row(lines, l318, "**47/47 通过、exit 0、44.1 s**", "**48/48 通过、exit 0、47.8 s**",
              "§9 循环自测 48/48、47.8 s")
    patch_row(
        lines, l318, "**D58 新增 E 组·续三条与 H5/H5b 两条**）",
        "**D58 新增 E 组·续三条与 H5/H5b 两条**、**D59 新增 E10a–E10d 与 H6/H6b**）",
        "§9 循环自测：补记 D59 的牙齿")

    l320 = "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告"
    patch_row(lines, l320, "（**131 行**；", "（**133 行**；",
              "§9 stage9_report.md 133 行")
    patch_row(lines, l320, "5 四臂裁决（`inf` 一律印 `—`）",
              "5 四臂裁决（`inf` 一律印 `—`；D59 起印出落盘件自报的裁决规则版本，缺失 ⇒ ⚠️）",
              "§9 报告：§5 印裁决规则版本")

    l321 = "| `1_Code/AutoRA_SPE/stage9_report.py` | 落盘报告生成器"
    patch_row(lines, l321, "（**397 行**、裸 LF", "（**408 行**、裸 LF",
              "§9 stage9_report.py 408 行")
    patch_row(lines, l321, "并把 `n_bad` 的释义写成「不可识别方向条数」）",
              "并把 `n_bad` 的释义写成「不可识别方向条数」；D59 起 §5 印落盘件自报的裁决规则"
              "版本 `verdict_logic`，缺失 ⇒ 先警「判词可能由已被修正的规则生成」）",
              "§9 生成器：§5 的新纪律")

    l322 = "| `1_Code/AutoRA_SPE/check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, l322, "（**362 行**、裸 LF）。**50/50 通过、exit 0**",
              "（**372 行**、裸 LF）。**52/52 通过、exit 0**",
              "§9 报告自测 372 行、52/52")
    patch_row(lines, l322, "+ R1p-h/R1p-i 的 `n_repeats` 先警判据）",
              "+ R1p-h/R1p-i 的 `n_repeats` 先警判据 + **D59 的 R1p-j/k/l**（标定种子与限制句）"
              "与 **R1p-m/R1p-n**（裁决规则版本：缺失 ⇒ 先警必须出现；有 ⇒ 印出且不得先警））",
              "§9 报告自测：补记 D59 的牙齿")

    l416 = "| 2026-10-16 | **判据带宽的标定种子与裁决短路（决策 D59）**"
    patch_row(lines, l416, "831 → **886 行**", "831 → **896 行**",
              "§12 D59 行：stage9_loop.py 896 行")
    patch_row(lines, l416, "465 → **530 行（47/47，E10a–E10d + H6/H6b）**",
              "465 → **536 行（48/48，E10a–E10d + H6/H6b + H7）**",
              "§12 D59 行：循环自测 536 行、48/48")
    patch_row(lines, l416, "370 → **397 行**", "370 → **408 行**",
              "§12 D59 行：stage9_report.py 408 行")
    patch_row(lines, l416, "346 → **362 行（50/50，R1p-j/k/l）**",
              "346 → **372 行（52/52，R1p-j/k/l + R1p-m/n）**",
              "§12 D59 行：报告自测 372 行、52/52")
    patch_row(lines, l416, "`stage9_report.md` **131 行** |",
              "`stage9_report.md` **133 行**。另：**同族第四条** —— 判词是运行时生成的冻结产物"
              "而落盘件不记录规则版本 ⇒ 新增 `VERDICT_LOGIC` / `payload[\"verdict_logic\"]`，"
              "报告 §5 印版本（缺失则先警） |",
              "§12 D59 行：新增同族第四条")
    save(S9)


# ---------------------------------------------------------------- AutoRA README
def do_autora_readme() -> None:
    lines = load(RA)
    print("\n[AutoRA README]")

    row = "| `stage9_loop.py` | **优化循环**"
    patch_row(lines, row, "（**886 行**；", "（**896 行**；", "§7 stage9_loop.py 896 行")
    patch_row(
        lines, row, "并落盘 `seeds`/`family`",
        "并落盘 `seeds`/`family`，且落盘件自报裁决规则版本（`VERDICT_LOGIC` / "
        "`payload[\"verdict_logic\"]`）",
        "§7 循环：落盘件自报裁决规则版本")

    row2 = "| `check_stage9_loop.py` | 循环自测"
    patch_row(lines, row2, "（A–H 八组，**47/47**）", "（A–H 八组，**48/48**）",
              "§7 循环自测 48/48")
    patch_row(lines, row2, "**H5/H5b**（`n_init` 下限与退化提示的静态钉子）",
              "**H5/H5b**（`n_init` 下限与退化提示的静态钉子）；❗ **D59** 再加 "
              "**E10a–E10d**（`ΔA` 在带内但 `ΔB` 超带）、**H6/H6b**（标定种子独立重抽与 "
              "`seeds`/`family`）、**H7**（裁决规则版本）",
              "§7 循环自测：补记 D59 的牙齿")

    row3 = "| `stage9_report.py` | **Stage 9 落盘报告生成器**"
    patch_row(lines, row3, "（**397 行**）", "（**408 行**）", "§7 生成器 408 行")
    patch_row(lines, row3, "§7 的「几倍带子」自带限制句",
              "§7 的「几倍带子」自带限制句、§5 印落盘件自报的裁决规则版本（缺失 ⇒ 先警）",
              "§7 生成器：§5 的新纪律")

    row4 = "| `check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, row4, "（R1–R5 五组，**362 行、50/50、exit 0**）",
              "（R1–R5 五组，**372 行、52/52、exit 0**）", "§7 报告自测 372 行、52/52")
    patch_row(lines, row4, "`n_repeats < 4` 时报告必须先警 `sd` 自身的不确定度）⇒ **47/47**",
              "`n_repeats < 4` 时报告必须先警 `sd` 自身的不确定度）⇒ **47/47**；❗ **D59** "
              "再加 **R1p-j/k/l**（标定种子的缺失/存在/限制句）与 **R1p-m/R1p-n**（裁决规则版本）",
              "§7 报告自测：补记 D59 的牙齿")

    row5 = "| `stage9_report.md` | **落盘报告**"
    patch_row(lines, row5, "（**131 行**，", "（**133 行**，", "§7 交付件 133 行")
    save(RA)


# ---------------------------------------------------------------- DDM README
def do_ddm_readme() -> None:
    lines = load(RM)
    print("\n[DDM_Core README]")

    # §8.34 §2：代码改动清单 5 处 → 6 处，并补第 6 条
    # ⚠️ `### 2. 代码改动清单（5 处）` 在 README 里命中 2 行（另一处在 §8.33）
    #    ⇒ 必须用 `## 8.34 ` 标题作定位锚，只在其后搜索。
    head = "### 2. 代码改动清单（5 处）"
    patch_row(lines, head, "（5 处）", "（6 处）", "§8.34 §2：改动清单 6 处",
              after="## 8.34 ")
    insert_after(
        lines,
        "   （分母来自 `n_repeats` 次重抽；`n_fim = 1` 下同一份 `ΔA = 0.0412` 可印成 8.2 倍或 1.1 倍）。",
        ["6. `1_Code/AutoRA_SPE/stage9_loop.py`：新增模块常量 `VERDICT_LOGIC`（写明三代裁决逻辑的差别）"
         "与 payload 的",
         "   `\"verdict_logic\"` 键；`1_Code/AutoRA_SPE/stage9_report.py` §5 印出该版本，缺失时先警",
         "   「本落盘件没有记录裁决规则版本 ⇒ 判词可能由已被修正的规则生成」。**为什么不能省**：报告只"
         "逐字转印",
         "   `compare[*].verdict`（不重算），而规则改过三代 ⇒ 不记版本就没有任何办法判断手上这份判词该不该信。"],
        "§8.34 §2：新增第 6 条（裁决规则版本）", after="## 8.34 ")

    # §8.34 §6：校验证据的数字与新增一条
    patch_sub(lines, "⇒ **47/47、未通过 0 项、exit 0、48.8 s**",
              "**47/47、未通过 0 项、exit 0、48.8 s**", "**48/48、未通过 0 项、exit 0、47.8 s**",
              "§8.34 §6：循环自测 48/48", after="## 8.34 ")
    patch_sub(lines, "5. `python -u 1_Code/AutoRA_SPE/check_stage9_report.py`",
              "**50/50、未通过 0 项、exit 0**", "**52/52、未通过 0 项、exit 0**",
              "§8.34 §6：报告自测 52/52", after="## 8.34 ")
    patch_sub(lines, "（新增 R1p-j/k/l）；`stage9_report.md` 重新生成",
              "（新增 R1p-j/k/l）；`stage9_report.md` 重新生成 ⇒ **131 行**。",
              "（新增 R1p-j/k/l + R1p-m/n）；`stage9_report.md` 重新生成 ⇒ **133 行**"
              "（§5 多出「没有记录裁决规则版本」的先警，因为依据件是 D59 之前的 `n_fim = 1` 落盘件）。",
              "§8.34 §6：交付件 133 行", after="## 8.34 ")
    insert_after(
        lines,
        "6. `python 1_Code\\AutoRA_SPE\\check_stage9.py --quick` ⇒ 8 项、未通过 0 项、1.8 s、exit 0。",
        ["7. 第四处同族缺陷的牙齿：`1_Code/AutoRA_SPE/check_stage9_loop.py` 的 **H7**"
         "（`VERDICT_LOGIC` 常量与 `payload[\"verdict_logic\"]` 的静态钉子）与",
         "   `1_Code/AutoRA_SPE/check_stage9_report.py` 的 **R1p-m**（无 `verdict_logic` ⇒ 先警必须出现）、"
         "**R1p-n**（有 ⇒ 印出且不得先警）。"],
        "§8.34 §6：新增第 7 条（H7 与 R1p-m/n）", after="## 8.34 ")

    # §9 第 43 项
    row43 = "| 43 | ✅ **判据带宽的标定种子必须独立重抽"
    append_in_row(
        lines, row43,
        "+ **同族第四条**：判词是运行时生成的冻结产物而落盘件不记录规则版本 "
        "⇒ 新增 `VERDICT_LOGIC` / `payload[\"verdict_logic\"]`，报告 §5 印版本（缺失则先警），"
        "牙齿 = **H7** + **R1p-m/n**（循环自测 **48/48**、报告自测 **52/52**）",
        "§9 第 43 项：补记同族第四条")
    save(RM)


if __name__ == "__main__":
    print(f"{'应用' if APPLY else '干跑'}：{ROOT.name}/…")
    do_master_plan()
    do_stage9()
    do_autora_readme()
    do_ddm_readme()
    print(f"\n{'✅ 已应用' if APPLY else '🧪 干跑结束'}：{_EDITS} 处编辑"
          f"{'' if APPLY else '（加 --apply 写盘）'}")
