# -*- coding: utf-8 -*-
"""D93/D94：给 `check_full_session.py` 补两条牙齿。

A15 —— v4.9「练习段 4 试次兜底」：`nPractice = max(4, P)` 存在、`loopCount = nPractice / 4`、
       头注有 v4.9 段、旧的 `loopCount = P / 4` 已消失。
B31 —— 驱动判据跟上：`nPracExpected = max(4, P_groups(groupID))`、B17 认「练习行数 = max(4,P)」、
       不再有「组1 只有 formal」的旧分支。
另把 docstring 的「共 32 项」改为「共 34 项」。
"""
from pathlib import Path

F = Path("1_Code/Experiment/exp_matlab/test/check_full_session.py")
src = F.read_text(encoding="utf-8")

A15 = '''
check("A15 v4.9 练习段 4 试次兜底：P=0 组也要练习（D93）",
      "★★ v4.9 本次修正" in prog
      and "nPractice = max(4, P);" in code
      and "loopCount = nPractice / 4;" in code
      and "loopCount = P / 4;" not in code)

'''
anchor = "# ---------------- B 驱动侧 ----------------"
assert src.count(anchor) == 1
src = src.replace(anchor, A15.lstrip("\n") + anchor)

B31 = '''
check("B31 驱动判据跟上练习兜底：nExpected = max(4,P) + 576、B17 认 practice 行数（D93）",
      "nPracExpected = max(4, P_groups(groupID));" in runner
      and "nExpected = nPracExpected + 3 * 192;" in runner
      and 'nPracRows == nPracExpected' in runner
      and "组1 只有 formal（无练习）" not in runner)

'''
anchor2 = "# tFloor 契约测试（D83）"
assert src.count(anchor2) == 1
src = src.replace(anchor2, B31.lstrip("\n") + anchor2)

src = src.replace("共 32 项", "共 34 项")

F.write_text(src, encoding="utf-8", newline="\n")
print(f"check_full_session.py：{len(src.splitlines())} 行")
