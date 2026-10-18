# -*- coding: utf-8 -*-
"""真正把 README §8.58 移到 §8.57 正文之后（上一版把 §8.57 正文一起卷走了，等于没动）。"""
from __future__ import annotations

import sys
from pathlib import Path

README = Path(__file__).resolve().parents[3] / "1_Code" / "DDM_Core" / "README.md"
H57 = "### 8.57 `onset` 之前的按键"
H58 = "### 8.58 阈值是从哪来的"
BODY57 = "四个调用点（练习/正式 × 刺激期/反应窗）都传 `stimulusFlipTime`"


def find(lines: list[str], pred, tag: str) -> int:
    idx = [k for k, ln in enumerate(lines) if pred(ln)]
    if len(idx) != 1:
        sys.exit(f"[FAIL] {tag}: 命中 {len(idx)} 次")
    return idx[0]


def main() -> int:
    lines = README.read_text(encoding="utf-8").split("\n")
    i57 = find(lines, lambda s: s.startswith(H57), "§8.57 标题")
    i58 = find(lines, lambda s: s.startswith(H58), "§8.58 标题")
    i9 = find(lines, lambda s: s.startswith("## 9."), "## 9 标题")
    bstart = find(lines, lambda s: s.startswith(BODY57), "§8.57 正文首行")
    if not (i57 < i58 < bstart < i9):
        sys.exit(f"[FAIL] 顺序不符合预期: 57={i57 + 1} 58={i58 + 1} body={bstart + 1} 9={i9 + 1}")

    block58 = lines[i58:bstart]
    while block58 and block58[-1].strip() == "":
        block58.pop()
    body57 = lines[bstart:i9]
    while body57 and body57[-1].strip() == "":
        body57.pop()

    out = (lines[:i57]
           + [lines[i57], ""]
           + body57
           + [""] + block58 + [""]
           + lines[i9:])
    text = "\n".join(out)
    README.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] README = {len(text.splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
