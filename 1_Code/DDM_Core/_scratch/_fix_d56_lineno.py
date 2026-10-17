# -*- coding: utf-8 -*-
"""把三份文档里 `stage9_loop.py` 的「770 行」改成实测的 **787 行**。

为什么：D56 落纸时我按压缩摘要里的中间读数写了 770，而 `check_files.py` 实测文件是
**787 行**（749 → 770 是「补 `_jsonable()` + payload `cache`」后的中间态，再补
「算前沿前先补全空间」+ payload `front_scope` 又加了 17 行）。
体例：逐文件断言命中次数 + 断言竖线数不变 + 幂等守卫。

用法：
    python 1_Code/DDM_Core/_scratch/_fix_d56_lineno.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_fix_d56_lineno.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OLD, NEW = "770 行", "787 行"
TARGETS = {
    Path("1_Code/DDM_Core/README.md"): 3,
    Path("5_Reference/08_工作流/工作流_主计划.md"): 3,
    # ⚠️ 计的是**行数**：Stage9 的两处「770 行」在**同一行**（§12 的 D56 行）
    Path("5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md"): 1,
}


def n_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    changes: dict[Path, list[str]] = {}
    for path, want in TARGETS.items():
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            print(f"❌ {path} 不以换行结尾")
            return 2
        lines = text[:-1].split("\n")
        hits = [i for i, s in enumerate(lines) if OLD in s]
        if len(hits) != want:
            print(f"❌ {path.name}：「{OLD}」命中 {len(hits)} 行（期望 {want}），拒绝写回")
            return 2
        for i in hits:
            new = lines[i].replace(OLD, NEW)
            if n_sep(new) != n_sep(lines[i]):
                print(f"❌ {path.name} L{i + 1} 竖线数变化")
                return 2
            lines[i] = new
        changes[path] = lines
        print(f"✅ {path.name}：{len(hits)} 行「{OLD}」→「{NEW}」")
    for path, lines in changes.items():
        out = "\n".join(lines) + "\n"
        if apply:
            path.write_text(out, encoding="utf-8", newline="\n")
            print(f"✍️ 已写回：{path}（{len(lines)} 行）")
        else:
            print(f"（干跑）将写回 {path}（{len(lines)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
