# -*- coding: utf-8 -*-
"""D93：驱动判据跟上「练习试次 = max(4, P)」。

- `nExpected = P_groups(groupID) + 3*192` → `max(4, P_groups(groupID)) + 3*192`
- B11 原先分两支（组1 无练习 ⇒ 只认 [1 2 3]），现在所有组都有练习 ⇒ 统一认 [0 1 2 3]
"""
from pathlib import Path

F = Path("1_Code/Experiment/exp_matlab/test/run_full_session.m")
src = F.read_text(encoding="utf-8")

pairs = [
    (
        "% 预期行数：P 个练习试次 + 3 block × 192\n"
        "P_groups = [0; 8; 32; 120];\n"
        "nExpected = P_groups(groupID) + 3 * 192;",
        "% 预期行数：max(4, P) 个练习试次 + 3 block × 192\n"
        "%   ★ D93：P=0 组也有 4 个练习试次（设计兜底），旧口径 `P` 会让组1 少算 4 行\n"
        "P_groups = [0; 8; 32; 120];\n"
        "nPracExpected = max(4, P_groups(groupID));\n"
        "nExpected = nPracExpected + 3 * 192;",
    ),
]

for old, new in pairs:
    assert src.count(old) == 1, ("miss", old[:40])
    src = src.replace(old, new)

# B11：两分支合一
import re
m = re.search(
    r"\n\s*if P_groups\(groupID\) > 0\n"
    r"(?:.*\n)*?.*?B11 block 覆盖.*?\n"
    r"\s*else\n"
    r"(?:.*\n)*?.*?B11 block 覆盖.*?\n"
    r"\s*end\n",
    src,
)
assert m, "B11 分支未找到"
new_b11 = (
    "\n"
    "C{end+1} = {'B11 block 覆盖 0（练习）/1/2/3（D93：所有组都有练习段）', "
    "isequal(sort(unique(T.block(:))'), [0 1 2 3])};\n"
)
src = src[: m.start()] + new_b11 + src[m.end():]

# B1 文案：P + 576 → max(4,P) + 576
src = src.replace(
    "sprintf('B1 行数 = P + 576 = %d（实测 %d）', nExpected, height(T))",
    "sprintf('B1 行数 = max(4,P) + 576 = %d（实测 %d）', nExpected, height(T))",
)

F.write_text(src, encoding="utf-8", newline="\n")
print(f"run_full_session.m：{len(src.splitlines())} 行")
