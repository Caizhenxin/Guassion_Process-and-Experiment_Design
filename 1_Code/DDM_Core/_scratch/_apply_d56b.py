# -*- coding: utf-8 -*-
"""D56 第三批落纸：把「给 `check_stage9_loop.py` 补牙齿」的结果写进三份文档。

**已做**（D56 当轮）：`1_Code/AutoRA_SPE/check_stage9_loop.py` 261 → **374 行**，新增 **H 组**
三条**静态源码判据**（不重跑 13 分钟的内环）：
- `H1` `main()` 里 `ev.feasible_names()` 的首次出现**早于** `pareto_front(ev)` 与 `ev.best("A")`；
- `H2` payload 里有 `"front_scope"` 且四键齐全；
- `H3` payload 的 `"cache"` 段存在且经 `_jsonable()`。
实测 **31/31、exit 0、63.0 s**（28 → 31）。

⚠️ **诚实边界**：H1 是**源码顺序**判据，**不是**运行期的
`front_scope.n_evaluated == front_scope.n_candidates` —— 后者要跑一次全空间（10–15 min）才能
看见，目前由 `1_Code/AutoRA_SPE/_scratch_smoke_scope.json` 那次冒烟覆盖，**自测里没有**。

体例：子串定位 + 命中次数断言 + 竖线数/追加位置断言 + 幂等守卫。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d56b.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d56b.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RA = Path("1_Code/AutoRA_SPE/README.md")
RM = Path("1_Code/DDM_Core/README.md")
S9 = Path("5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md")
MP = Path("5_Reference/08_工作流/工作流_主计划.md")

H_SENTENCE = (
    " 另加**新牙齿**：`check_stage9_loop.py` 261 → **374 行**、28 → **31/31、exit 0、63.0 s**，"
    "新增 **H 组**三条**静态源码判据**（`H1` `main()` 里 `ev.feasible_names()` 必须早于 "
    "`pareto_front(ev)` 与 `ev.best(\"A\")`；`H2` payload 有 `\"front_scope\"` 且四键齐全；"
    "`H3` `\"cache\"` 段存在且经 `_jsonable()`）。⚠️ **边界**：H1 钉的是**源码顺序**，"
    "**不是**运行期的 `front_scope.n_evaluated == front_scope.n_candidates`（那要跑一次全空间，"
    "10–15 min，自测里没有，由冒烟覆盖）。"
)

REPLACEMENTS = [
    # ① AutoRA_SPE README §7 的文件清单（**当前状态**）
    (RA, "A–G 七组，**28/28**）",
     "A–H 八组，**31/31**）"),
    # ② Stage 9 §9 的文件表（**当前状态**）
    (S9, "✅ **已建**（**340 行**、裸 LF —— D55 前为 261 行）。**28/28 通过、exit 0、58.8 s**",
     "✅ **已建**（**374 行**、裸 LF —— D55 前为 261 行、D56 前为 340 行）。"
     "**31/31 通过、exit 0、63.0 s**（D56 新增 H 组三条静态源码判据）"),
    # ③ 主计划 D56 进度行的「仍开放」第 (2) 件 —— 已完成
    (MP,
     "**(2)** 给 `check_stage9_loop.py` 补一个新牙齿（断言前沿前已补全空间、"
     "`front_scope.n_evaluated == front_scope.n_candidates`）；",
     "~~**(2)** 给 `check_stage9_loop.py` 补一个新牙齿（断言前沿前已补全空间、"
     "`front_scope.n_evaluated == front_scope.n_candidates`）；~~ ✅ **2026-10-14 已完成"
     "（D56 当轮）**：新增 **H 组**三条**静态源码判据**（`H1` 顺序、`H2` `front_scope` 四键、"
     "`H3` `cache` 走 `_jsonable`）⇒ **374 行、31/31、exit 0、63.0 s**。"
     "⚠️ **诚实边界**：H1 是源码顺序，**不是**运行期的 "
     "`front_scope.n_evaluated == front_scope.n_candidates`（那要跑一次全空间，自测里没有，"
     "由 `_scratch_smoke_scope.json` 那次冒烟覆盖）；"),
]


def n_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    if "H 组" in RA.read_text(encoding="utf-8"):
        print("❌ AutoRA_SPE README 已含「H 组」（幂等守卫）")
        return 2

    files = {p: p.read_text(encoding="utf-8") for p in (RA, RM, S9, MP)}
    for p, t in files.items():
        if not t.endswith("\n"):
            print(f"❌ {p} 不以换行结尾")
            return 2
    lines = {p: t[:-1].split("\n") for p, t in files.items()}

    # 1) 三处子串替换
    for path, old, new in REPLACEMENTS:
        ls = lines[path]
        hits = [i for i, s in enumerate(ls) if old in s]
        if len(hits) != 1:
            print(f"❌ {path.name}：锚文本命中 {len(hits)} 行（期望 1），拒绝写回\n   {old[:60]!r}")
            return 2
        i = hits[0]
        out = ls[i].replace(old, new)
        if n_sep(out) != n_sep(ls[i]):
            print(f"❌ {path.name} L{i + 1} 竖线数变化 {n_sep(ls[i])} → {n_sep(out)}")
            return 2
        ls[i] = out
        print(f"✅ {path.name} L{i + 1}：更新（竖线数不变 = {n_sep(out)}）")

    # 2) README(DDM_Core) §9 第 39 项：把 H 组追加进该行（插在闭合竖线之前）
    ls = lines[RM]
    hits = [i for i, s in enumerate(ls) if s.startswith("| 39 | ✅ **前沿与推荐点的作用域缺陷已修")]
    if len(hits) != 1:
        print(f"❌ README §9 第 39 项命中 {len(hits)} 行")
        return 2
    i = hits[0]
    if "H 组" in ls[i]:
        print(f"❌ README L{i + 1} 已含「H 组」")
        return 2
    new = ls[i].rstrip()[:-1].rstrip() + H_SENTENCE + " |"
    if n_sep(new) != n_sep(ls[i]):
        print(f"❌ README L{i + 1} 竖线数变化 {n_sep(ls[i])} → {n_sep(new)}")
        return 2
    ls[i] = new
    print(f"✅ README §9 第 39 项追加 H 组（L{i + 1}，竖线数不变 = {n_sep(new)}）")

    for path, ls in lines.items():
        out = "\n".join(ls) + "\n"
        if apply:
            path.write_text(out, encoding="utf-8", newline="\n")
            print(f"✍️ 已写回：{path}（{len(ls)} 行）")
        else:
            print(f"（干跑）将写回 {path}（{len(ls)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
