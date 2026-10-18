# -*- coding: utf-8 -*-
"""修 D85 落纸的一处错位：README §8.58 被插到了 §8.57 标题之后（正文之前），
应移到 §8.57 正文结束、`## 9` 之前。"""
from __future__ import annotations

import sys
from pathlib import Path

README = Path(__file__).resolve().parents[3] / "1_Code" / "DDM_Core" / "README.md"
HEAD = "### 8.58 阈值是从哪来的：87 份历史真人数据把 S6-5 的两条线顶翻了（2026-10-18，D85）"


def main() -> int:
    lines = README.read_text(encoding="utf-8").split("\n")
    i = [k for k, ln in enumerate(lines) if ln.startswith(HEAD)]
    if len(i) != 1:
        sys.exit(f"[FAIL] §8.58 标题命中 {len(i)} 次")
    start = i[0]
    # 块结束：下一个空行之后紧跟非空块的行；这里块尾 = `## 9` 之前最后一个非空行
    j = next(k for k, ln in enumerate(lines) if ln.startswith("## 9."))
    if not (start < j):
        sys.exit("[FAIL] 顺序异常")
    block = lines[start:j]
    # 去掉尾部空行
    while block and block[-1].strip() == "":
        block.pop()
    rest = lines[:start] + lines[j:]
    # 插到 `## 9.` 之前（rest 里找）
    k = next(k for k, ln in enumerate(rest) if ln.startswith("## 9."))
    while k > 0 and rest[k - 1].strip() == "":
        k -= 1
    out = rest[:k] + [""] + block + [""] + rest[k:]
    text = "\n".join(out)
    README.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] §8.58 从第 {start + 1} 行移到 `## 9.` 之前；README = {len(text.splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
