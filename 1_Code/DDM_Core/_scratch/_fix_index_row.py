# -*- coding: utf-8 -*-
"""修 INDEX.md 最后一行：PowerShell here-string 把反引号吃掉，留下 `\\#标签\\`。

教训见 `2026-10-17_PowerShell内联python-c带中文引号必炸.md`：含反引号的文本一律用
`write` 工具落 .py 文件再跑，不要塞进 `python -c`。
"""
from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\INDEX.md")
BT = chr(96)

tags = ["静默失败", "后写覆盖", "聚合键", "同名文件", "判定器", "自测产物污染", "输入歧义", "只打文件名"]
row = (
    "| 2026-10-18 | 聚合键后写覆盖：新建的入库判定器静默判了另一份同名自测文件 | "
    + " ".join(f"{BT}#{t}{BT}" for t in tags)
    + " | [2026-10-18_聚合键后写覆盖导致判定器静默挑错文件.md]"
      "(./2026-10-18_聚合键后写覆盖导致判定器静默挑错文件.md) |"
)

L = P.read_text(encoding="utf-8").split("\n")
i = next(k for k, x in enumerate(L) if "聚合键后写覆盖" in x)
L[i] = row
P.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("已重写第", i + 1, "行")
print(row[:120], "…")
