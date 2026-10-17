# -*- coding: utf-8 -*-
"""修 `_apply_d56.py` 造成的一处布局缺陷：就地更正的后缀被追加到**行末闭合竖线之后**。

`check_table_integrity.py` 的判据是「行末必须有闭合竖线」⇒ 后缀必须插在**行内最后一个
竖线之前**，即 `| a | b | 后缀 |`，而不是 `| a | b | 后缀`。

本脚本把「以 `见 D56）**` 结尾但**不以 `|` 结尾**」的行改写为正确形状：
取行内最后一个 `|`，把它之后的文本搬到它之前，再补回 `" |"`。
断言：改写前后**未被转义的竖线个数不变**、且改写后行以 ` |` 结尾。

用法：
    python 1_Code/DDM_Core/_scratch/_fix_d56_tail.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_fix_d56_tail.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILES = [
    Path("5_Reference/08_工作流/工作流_主计划.md"),
    Path("5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md"),
]


def n_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    total = 0
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            print(f"❌ {path} 不以换行结尾，拒绝写回")
            return 2
        lines = text[:-1].split("\n")
        fixed = 0
        for i, s in enumerate(lines):
            # ⚠️ 只看**表格行**（以 `|` 开头）：`Stage9_...md` §11 的编号条目里也有
            # 「见 D56）**」，它是列表项、本来就没有闭合竖线 —— 上一版因此误报并
            # 整个文件都没写回。
            if "见 D56）**" not in s or not s.lstrip().startswith("|"):
                continue
            if s.rstrip().endswith("|"):
                continue
            j = s.rfind("|")
            if j < 0:
                print(f"❌ {path.name} L{i + 1}：行内没有竖线，拒绝")
                return 2
            head = s[:j].rstrip()
            tail = s[j + 1:].strip()
            new = head + " " + tail + " |"
            if n_sep(new) != n_sep(s):
                print(f"❌ {path.name} L{i + 1}：竖线数变化 {n_sep(s)} → {n_sep(new)}，拒绝")
                return 2
            if not new.rstrip().endswith("|"):
                print(f"❌ {path.name} L{i + 1}：改写后仍无闭合竖线，拒绝")
                return 2
            lines[i] = new
            fixed += 1
            print(f"✅ {path.name} L{i + 1}：后缀移入闭合竖线之前（竖线数不变 = {n_sep(new)}）")
        if fixed:
            out = "\n".join(lines) + "\n"
            if apply:
                path.write_text(out, encoding="utf-8", newline="\n")
                print(f"✍️ 已写回：{path}（{len(lines)} 行）")
            else:
                print(f"（干跑）将写回 {path}（{len(lines)} 行）")
        total += fixed
    print(f"合计修正 {total} 行")
    return 0 if total else 2


if __name__ == "__main__":
    raise SystemExit(main())
