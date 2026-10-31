# -*- coding: utf-8 -*-
"""一致性自检：把「同一事实两处写、但说法不一致」的过期点找出来。

用法：
    python -X utf8 _交接/_tools/一致性.py --check      检查真实工作区
    python -X utf8 _交接/_tools/一致性.py --selftest   用植入的坏样本自证（必须报红）

为什么要有它：2026-10-30 审计发现 `index\\总索引.md` 说插件「留档·机主搁置」，
而 `index\\进度.md` 说「V2–V7 与 P5 完成」——两处写同一事实、互相打架，
靠人工读一遍是发现不了的。本工具把这四类过期点变成可跑的判据。

判据（每条都必须能说出「差异集合」，不许只报一个 0）：
    C1 交接 §〇 说有「下一步」，总台待办板上必须真有对应行
    C2 死条目：索引里链接到的文件、交接里点名的路径，必须真实存在
    C3 版本号：交接与板上出现的 vX.Y 必须在 Log.md 里出现过
    C4 体量：当前交接 ≤ 4096 字节

退出码：0 = 全过；1 = 有差异；2 = 工具自身出错（不许把 2 当 0 看）。
"""

import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOVER = ROOT / "_交接" / "当前交接.md"
BOARD = Path(r"D:\GitHub_programe\GitHub\DSH_Workbench\boards\待办板.md")
LOG = ROOT / "Log.md"
INDEX5 = ROOT / "5_Reference" / "README.md"
TAG = "【gp-experiment】"
LIMIT = 4096


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def section(text, key="§〇"):
    """取 §〇 那一段（到下一个 § 或文件结束）。"""
    if not text:
        return ""
    i = text.find(key)
    if i < 0:
        return ""
    rest = text[i + len(key):]
    j = rest.find("\n§")
    return rest if j < 0 else rest[:j]


def section0(text):
    """§〇 标题可能写成 '## 〇' / '§〇' / '§0'，都试一遍。"""
    for key in ("§〇", "§0", "## 〇", "〇 当前交接"):
        body = section(text, key)
        if body.strip():
            return body
    return text or ""


def c1_handover_vs_board(handover, board):
    """交接说「下一步」⇒ 板上必须有 gp-experiment 的未完成行。"""
    out = []
    body = section0(handover)
    wants_next = "下一步" in body
    open_rows = [
        line for line in (board or "").splitlines()
        if line.lstrip().startswith("- [ ]") and TAG in line
    ]
    if wants_next and not open_rows:
        out.append("C1 交接 §〇 写了「下一步」，但待办板上没有一条 %s 的未完成行" % TAG)
    if open_rows and not body.strip():
        out.append("C1 待办板有 %d 条未完成行，但交接 §〇 是空的" % len(open_rows))
    return out


LINK = re.compile(r"\]\(([^)#][^)]*)\)")
PATHISH = re.compile(r"`([^`\n]+\.(?:md|py|json|yml|yaml|csv|png|svg|ipynb|docx|xlsx))`")


SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "node_modules",
             ".venv", ".venv-manim", "_scratch", "_stage8_out", "_stage8_demo"}
REF_EXT = {".md", ".py", ".json", ".yml", ".yaml", ".csv", ".png", ".svg",
           ".ipynb", ".docx", ".xlsx", ".mjs", ".ps1"}


def name_index(root):
    """整棵工作区的文件名索引（只收常见引用后缀），供「只写文件名」的引用兜底。"""
    index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in REF_EXT:
                index.setdefault(name, []).append(os.path.join(dirpath, name))
    return index


def c2_dead_entries(root, handover, index_text, index=None):
    """索引里点到的文件必须存在。两种写法都认：markdown 链接 + 反引号路径。

    相对路径先按「文档自己所在目录」解析，再退回工作区根；再不行就按文件名
    在全工作区兜底（索引爱写「目录在上一行、这里只给文件名」）。
    """
    if index is None:
        index = name_index(root)
    out = []
    checked = 0
    fallback = 0
    for label, text, base in (
        ("5_Reference/README.md", index_text, root / "5_Reference"),
        ("当前交接.md", handover, root / "_交接"),
    ):
        refs = [t.strip() for t in LINK.findall(text or "")]
        refs += [t.strip() for t in PATHISH.findall(text or "")]
        for target in refs:
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if "{" in target or "}" in target or "*" in target:
                continue  # 模板占位符 / glob 通配，不是真路径
            checked += 1
            candidates = [Path(target)] if os.path.isabs(target) else [base / target, root / target]
            if any(p.exists() for p in candidates):
                continue
            if Path(target).name in index:
                fallback += 1
                continue
            out.append("C2 [%s] 指向不存在的文件：%s" % (label, target))
    if fallback:
        print("（C2 有 %d 条按文件名兜底命中，说明参考写法省了目录前缀）" % fallback)
    if checked == 0:
        out.append("C2 一条路径都没检查到（判据空转 = 假绿灯，请核对解析规则）")
    return out


VERSION = re.compile(r"v\d+\.\d+")


def c3_version_known(handover, board, log_text):
    """交接与板上出现的版本号，必须在 Log.md 出现过。"""
    out = []
    if log_text is None:
        out.append("C3 Log.md 不存在 ⇒ 版本口径无处可查（判据空转）")
        return out
    seen = set(VERSION.findall(log_text))
    rows = [line for line in (board or "").splitlines() if TAG in line]
    for label, text in (("当前交接.md", section0(handover)), ("待办板", "\n".join(rows))):
        for ver in sorted(set(VERSION.findall(text))):
            if ver not in seen:
                out.append("C3 [%s] 出现 %s，但 Log.md 里没有这条记录" % (label, ver))
    return out


def c4_size(handover_bytes):
    if handover_bytes is None:
        return ["C4 当前交接.md 不存在"]
    if handover_bytes > LIMIT:
        return ["C4 当前交接.md 超线：%d B > %d B" % (handover_bytes, LIMIT)]
    return []


def run(root, handover_path, board_path, log_path, index_path):
    handover = read(handover_path)
    board = read(board_path)
    log_text = read(log_path)
    index_text = read(index_path)
    size = handover_path.stat().st_size if handover_path.exists() else None
    findings = []
    findings += c1_handover_vs_board(handover, board)
    findings += c2_dead_entries(root, handover, index_text)
    findings += c3_version_known(handover, board, log_text)
    findings += c4_size(size)
    return findings


def report(findings, title):
    print("=" * 60)
    print(title)
    print("=" * 60)
    if not findings:
        print("全过：没有发现同一事实两处写不一致的过期点。")
        return 0
    for line in findings:
        print("  - " + line)
    print("-" * 60)
    print("差异 %d 条。" % len(findings))
    return 1


GOOD_HANDOVER = """# 当前交接

## §〇 当前交接
- 下一步：补 P0 四条
- 版本：v0.20
- 依据：`_交接/工作台纪律.md`
"""

BAD_HANDOVER = """# 当前交接

## §〇 当前交接
- 下一步：补 P0 四条
- 版本：v9.99
- 依据：`_交接/根本不存在.md`
"""

BOARD_OK = "- [ ] 2026-10-30 【gp-experiment】补 P0 四条\n"
BOARD_EMPTY = "- [x] 2026-10-30 【gp-experiment】已办完\n"
LOG_OK = "# Log\n\n## v0.20\n- 2026-10-30 工作台审计\n"
INDEX_OK = "# README\n\n- [纪律](工作台纪律.md)\n"


def selftest():
    """自证：好样本必须全过；坏样本必须被抓到（抓不到 = 工具假绿灯）。"""
    ok = 0
    # 沙箱不保证 %TEMP% 可写，样本目录放工作区内，跑完删掉
    sandbox = ROOT / "_交接" / "_tools" / "_selftest_tmp"
    if sandbox.exists():
        shutil.rmtree(sandbox, ignore_errors=True)
    sandbox.mkdir(parents=True, exist_ok=True)
    try:
        root = sandbox
        (root / "_交接").mkdir()
        (root / "5_Reference").mkdir()
        (root / "Log.md").write_text(LOG_OK, encoding="utf-8")
        (root / "5_Reference" / "README.md").write_text(INDEX_OK, encoding="utf-8")
        (root / "_交接" / "工作台纪律.md").write_text("# 纪律\n", encoding="utf-8")
        (root / "工作台纪律.md").write_text("# 纪律\n", encoding="utf-8")
        (root / "_交接" / "当前交接.md").write_text(GOOD_HANDOVER, encoding="utf-8")
        board = root / "board.md"
        board.write_text(BOARD_OK, encoding="utf-8")

        good = run(root, root / "_交接" / "当前交接.md", board, root / "Log.md",
                   root / "5_Reference" / "README.md")
        print("[自证 1] 好样本 → %s" % ("全过 ✓" if not good else "误报 ✗：%s" % good))
        ok += 1 if not good else 0

        # 反例 A：交接说有下一步，板是空的
        board.write_text(BOARD_EMPTY, encoding="utf-8")
        bad_a = run(root, root / "_交接" / "当前交接.md", board, root / "Log.md",
                    root / "5_Reference" / "README.md")
        caught_a = any(f.startswith("C1") for f in bad_a)
        print("[自证 2] 板空反例 → %s" % ("抓到 ✓" if caught_a else "漏了 ✗"))
        ok += 1 if caught_a else 0

        # 反例 B：版本号 Log 里没有 + 点名文件不存在
        board.write_text(BOARD_OK, encoding="utf-8")
        (root / "_交接" / "当前交接.md").write_text(BAD_HANDOVER, encoding="utf-8")
        bad_b = run(root, root / "_交接" / "当前交接.md", board, root / "Log.md",
                    root / "5_Reference" / "README.md")
        caught_b = any(f.startswith("C3") for f in bad_b) and any(f.startswith("C2") for f in bad_b)
        print("[自证 3] 版本空 + 死路径反例 → %s" % ("抓到 ✓" if caught_b else "漏了 ✗"))
        ok += 1 if caught_b else 0

        # 反例 C：索引链接指向不存在的文件
        (root / "_交接" / "当前交接.md").write_text(GOOD_HANDOVER, encoding="utf-8")
        (root / "5_Reference" / "README.md").write_text(
            "# README\n\n- [幽灵](幽灵文件.md)\n", encoding="utf-8")
        bad_c = run(root, root / "_交接" / "当前交接.md", board, root / "Log.md",
                    root / "5_Reference" / "README.md")
        caught_c = any("幽灵文件.md" in f for f in bad_c)
        print("[自证 4] 死条目反例 → %s" % ("抓到 ✓" if caught_c else "漏了 ✗"))
        ok += 1 if caught_c else 0
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    print("-" * 60)
    print("自证：%d/4 通过。%s" % (ok, "工具可信。" if ok == 4 else "工具不可信，先修它。"))
    return 0 if ok == 4 else 1


def main(argv):
    mode = argv[1] if len(argv) > 1 else "--check"
    if mode == "--selftest":
        return selftest()
    if mode != "--check":
        print("用法：一致性.py --check | --selftest")
        return 2
    findings = run(ROOT, HANDOVER, BOARD, LOG, INDEX5)
    return report(findings, "一致性自检 · %s" % ROOT.name)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))
