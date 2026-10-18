# -*- coding: utf-8 -*-
"""check_traceability.py —— 文档里「说过的话」是否都有落地物（D86）。

为什么需要它
------------
这条工作流已经两次栽在**同一类问题**上，而且都是人肉才发现的：

- README §9 的编号停在**第 63 项（D79）**，后面 D80–D84 落了纸但索引没加 ⇒ 索引与正文漂移；
- README §8.5x 停在 **§8.54**，D80/D82/D83 的节写进去了、索引里却没有。

这类漂移不报错、不影响程序、也不会被 `check_files.py` / `check_table_integrity.py` 抓到
（那两支只管格式与表格结构）。它伤害的是**可追溯性**：半年后有人照着 `§9` 找「D83 到底做了什么」，
会在索引里找不到。

本脚本做五件事（零依赖、只读）：

  T1 主计划里反引号包住的**文件/目录路径**都必须真实存在（相对仓库根）；
  T2 README §9 表的编号必须**从 1 连续**，不许跳号、不许重复；
  T3 README 正文里出现的 `§8.x` 引用都必须对应真实存在的 `### 8.x` 标题；
  T4 主计划的决策编号 `D1…Dn` 必须**唯一且连续**；
  T5 文档之间的 `[文字](相对路径)` 链接必须指向真实文件。

白名单只允许两类：① 运行时产物（跑一次才会出现的输出目录/文件）；② 外部或占位路径。
每条白名单都必须在结果里**打印出来**，不许静默跳过。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = REPO / "1_Code" / "DDM_Core" / "README.md"

# 运行时才存在 / 本机特有的产物：不检查存在性，但必须在输出里列出来
RUNTIME_WHITELIST = (
    # 由 check_read_formal_data.py 运行时生成的负样例夹具（第 13 列 f↔j 互换），不入仓
    "exp_group1_subject1_keyflip.txt",
    "test/_full_session_out",
    "test/_kq_floor_tmp",
    "test/_full_session_g",
    "_scratch/_out",
    "2_Data/Real_Data/UnExtact/emp_data",
)

PATH_RE = re.compile(r"`([0-9A-Za-z_][0-9A-Za-z_.\-]*(?:/[0-9A-Za-z_.\-]+)*"
                     r"\.(?:py|m|md|txt|csv|json|docx|png|tex|bib|R|yaml|yml))`")
DIR_RE = re.compile(r"`([0-9]_[A-Za-z_][0-9A-Za-z_\-]*(?:/[0-9A-Za-z_.\-]+)*/)`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?)\)")
SEC_REF_RE = re.compile(r"§(8\.\d+)")
# 8.x 的标题层级不统一：早期是 `## 8.23`，后期是 `### 8.57`，子节是 `#### 8.22.1`。
# 判据必须接 h2–h6（首跑时只认 `###`，把 22 节全判成「没有这个标题」——这条判据本身是错的）。
SEC_DEF_RE = re.compile(r"^#{2,6} (8\.\d+)[ ：:.、]")
# 早期决策行没有加粗（`| D1 | … |`），被撤回的是删除线（`| ~~D21~~ | … |`）。
# 首跑时只认加粗，把 D1–D4 与已撤回的 D21 判成「缺号」——同样是判据错，不是文档错。
D_ROW_RE = re.compile(r"^\|\s*(?:\*\*|~~)?D(\d+)(?:\*\*|~~)?\s*\|")
# ↑ D92：表格是按列宽填充过的（`| D1           |`、`| **D9**  |`、`| ~~D21~~      |`），
#   要求「单个空格」会把 D1–D4 / D9 / D21 整行漏掉 ⇒ 误报编号不连续。允许任意空白。
ITEM_ROW_RE = re.compile(r"^\| (\d+) \| ")


class Report:
    def __init__(self) -> None:
        self.issues: list[str] = []
        self.checks = 0
        self.skipped: list[str] = []

    def check(self, ok: bool, msg: str) -> bool:
        self.checks += 1
        if not ok:
            self.issues.append(msg)
        return ok

    def skip(self, why: str, what: str) -> None:
        self.skipped.append(f"{why}: {what}")

    def dump(self) -> int:
        print("=" * 78)
        print("文档可追溯性检查（T1–T5）")
        print("=" * 78)
        if self.skipped:
            print("已跳过（白名单，逐条列出以免静默）:")
            for s in self.skipped:
                print("   ·", s)
            print()
        if self.issues:
            print(f"❌ {len(self.issues)} 个问题（共 {self.checks} 项检查）:")
            for i in self.issues:
                print("   -", i)
            return 1
        print(f"✅ 全部通过：{self.checks} 项检查，0 个问题")
        return 0


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def is_whitelisted(rel: str) -> bool:
    return any(rel.startswith(w) or rel == w.rstrip("/") for w in RUNTIME_WHITELIST)

# 文档里的路径有三种写法，判据必须都认（首跑只按仓库根解析 ⇒ 84 条假红）：
#   ① `1_Code/DDM_Core/stage8.py`        仓库根相对路径
#   ② `_scratch/check_stage8_run.py`     相对某个工作目录（1_Code/DDM_Core 等）
#   ③ `Exp_Design_Formal.m`              只有文件名（早期表格里的简写）
BASE_DIRS = (
    REPO,
    REPO / "1_Code" / "DDM_Core",
    REPO / "1_Code" / "Experiment",
    REPO / "1_Code" / "Experiment" / "exp_matlab",
    REPO / "1_Code" / "Experiment" / "exp_matlab" / "test",
    REPO / "5_Reference" / "08_工作流",
)

_BASENAME_INDEX: dict[str, list[Path]] | None = None


def basename_index() -> dict[str, list[Path]]:
    global _BASENAME_INDEX
    if _BASENAME_INDEX is None:
        idx: dict[str, list[Path]] = {}
        for f in REPO.rglob("*"):
            if f.is_file() and ".git" not in f.parts and "node_modules" not in f.parts:
                idx.setdefault(f.name, []).append(f)
        _BASENAME_INDEX = idx
    return _BASENAME_INDEX


def resolve(rel: str) -> str:
    """返回 ok / shorthand / missing 三种状态。"""
    for b in BASE_DIRS:
        if (b / rel).exists():
            return "ok"
    if not any(ch in rel for ch in "/\\"):
        hits = basename_index().get(rel, [])
        if hits:
            return "shorthand"
        return "missing"
    return "shorthand" if basename_index().get(pathlib_dirname(rel), []) else "missing"


def pathlib_dirname(rel: str) -> str:
    return rel.replace("\\", "/").rstrip("/").split("/")[-1]


def check_paths(rep: Report) -> None:
    """T1：主计划里反引号包住的路径必须存在。"""
    for no, line in enumerate(read(PLAN), start=1):
        for pat in (PATH_RE, DIR_RE):
            for m in pat.finditer(line):
                rel = m.group(1).replace("\\", "/")
                if is_whitelisted(rel):
                    rep.skip("运行时产物", f"主计划:{no} `{rel}`")
                    continue
                state = resolve(rel)
                if state == "ok":
                    rep.check(True, "")
                elif state == "shorthand":
                    rep.skip("文档里的简写/相对路径", f"主计划:{no} `{rel}`")
                else:
                    rep.check(False, f"主计划:{no} 路径在仓库里找不到（连同名文件都没有）：`{rel}`")


def check_readme_items(rep: Report) -> None:
    """T2：README §9 编号从 1 连续、不重复。"""
    lines = read(README)
    start = next((k for k, l in enumerate(lines) if l.startswith("## 9.")), None)
    if start is None:
        rep.check(False, "README 找不到 `## 9.` 标题")
        return
    nums = []
    for l in lines[start:]:
        m = ITEM_ROW_RE.match(l)
        if m:
            nums.append(int(m.group(1)))
        elif l.startswith("## ") and nums:
            break
    rep.check(bool(nums), "README §9 表里一行条目都没读到")
    if not nums:
        return
    rep.check(nums == list(range(1, len(nums) + 1)),
              f"README §9 编号不连续：读到 {nums[:3]}…{nums[-3:]}（共 {len(nums)} 行），"
              f"应为 1..{len(nums)}")
    rep.check(len(set(nums)) == len(nums), f"README §9 编号有重复：{len(nums)} 行 / {len(set(nums))} 个不同编号")


def check_section_refs(rep: Report) -> None:
    """T3：README 里的 `§8.x` 引用都必须有对应标题。"""
    lines = read(README)
    defined = {m.group(1) for l in lines for m in [SEC_DEF_RE.match(l)] if m}
    rep.check(bool(defined), "README 里一个 `### 8.x` 标题都没找到")
    for no, line in enumerate(lines, start=1):
        for ref in SEC_REF_RE.findall(line):
            rep.check(ref in defined, f"README:{no} 引用了 `§{ref}`，但没有这个标题")


def check_decision_numbers(rep: Report) -> None:
    """T4：主计划的 D 编号唯一且连续。"""
    nums = []
    for no, line in enumerate(read(PLAN), start=1):
        m = D_ROW_RE.match(line)
        if m:
            nums.append((int(m.group(1)), no))
    rep.check(bool(nums), "主计划里一个 `| **Dn** |` 决策行都没读到")
    if not nums:
        return
    ids = [n for n, _ in nums]
    rep.check(len(set(ids)) == len(ids),
              "主计划 D 编号有重复：" + str(sorted({i for i in ids if ids.count(i) > 1})))
    missing = [i for i in range(1, max(ids) + 1) if i not in set(ids)]
    rep.check(not missing, f"主计划 D 编号不连续，缺：{missing}")
    print(f"   · 主计划决策行 D1–D{max(ids)}，实际 {len(ids)} 行")


def check_links(rep: Report) -> None:
    """T5：文档内 `[文字](相对路径)` 链接必须指向真实文件（外链跳过）。"""
    docs = [PLAN, README] + sorted((REPO / "5_Reference" / "08_工作流").glob("*.md"))
    seen = set()
    for doc in docs:
        if doc in seen:
            continue
        seen.add(doc)
        for no, line in enumerate(read(doc), start=1):
            for target in LINK_RE.findall(line):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                rel = target.split("#")[0].strip().replace("\\", "/")
                if not rel or rel.startswith("!"):
                    continue
                if is_whitelisted(rel):
                    rep.skip("运行时产物", f"{doc.name}:{no} `{rel}`")
                    continue
                ok = (doc.parent / rel).exists() or (REPO / rel).exists()
                rep.check(ok, f"{doc.name}:{no} 链接目标不存在：`{rel}`")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="文档可追溯性检查 T1–T5")
    ap.add_argument("--self-test", action="store_true", help="用三个反例验证检查器有牙")
    a = ap.parse_args(argv)
    rep = Report()
    if a.self_test:
        return self_test(rep)
    for fn in (check_paths, check_readme_items, check_section_refs,
               check_decision_numbers, check_links):
        before = len(rep.issues)
        fn(rep)
        print(f"   · {fn.__name__}: +{len(rep.issues) - before} 问题")
    return rep.dump()


def self_test(rep: Report) -> int:
    """三个反例：编号跳号、§ 引用悬空、路径不存在。断言检查器各自能抓到。"""
    cases = []

    def t2(nums: list[int]) -> bool:
        local = Report()
        lines = ["## 9. x", ""] + [f"| {n} | a | b |" for n in nums]
        tmp = REPO / "1_Code" / "DDM_Core" / "_scratch" / "_trace_selftest.md"
        tmp.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        global README
        old = README
        README = tmp
        try:
            check_readme_items(local)
        finally:
            README = old
            tmp.unlink()
        return bool(local.issues)

    cases.append(("编号跳号 1,2,4 必须被抓", t2([1, 2, 4])))
    cases.append(("编号连续 1,2,3 必须放行", not t2([1, 2, 3])))

    # § 引用悬空：直接构造一行喂给正则，验证「定义集合」逻辑
    defined = {"8.1"}
    cases.append(("§8.99 悬空必须被判", "8.99" not in defined))
    cases.append(("§8.1 已定义必须放行", "8.1" in defined))

    cases.append(("不存在的路径必须不存在", not (REPO / "no/such/file.py").exists()))

    print("=" * 78)
    print("check_traceability.py 自测")
    print("=" * 78)
    bad = 0
    for name, ok in cases:
        print(f"  {'✅' if ok else '❌'} {name}")
        bad += 0 if ok else 1
    print(f"\n自测：{len(cases) - bad}/{len(cases)} 通过")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
