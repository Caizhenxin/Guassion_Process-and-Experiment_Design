# -*- coding: utf-8 -*-
"""D90：给 check_full_session.py 加 A13（松键门槛），项数 29 → 30。"""
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "1_Code" / "Experiment" / "exp_matlab" / "test" / "check_full_session.py"
s = p.read_text(encoding="utf-8")
assert "（共 30 项）" not in s
s = s.replace("（共 29 项）", "（共 30 项）", 1)
anchor = "# ---------------- B 驱动侧 ----------------"
assert s.count(anchor) == 1
block = (
    'check("A13 v4.7 松键门槛：8 处空格等待之前都先等一次松键（D90）",\n'
    '      "function waitForSpaceRelease()" in code\n'
    '      and code.count("waitForSpaceRelease();") == 8\n'
    '      and "★★ v4.7 本次修正" in prog)\n\n'
)
s = s.replace(anchor, block + anchor, 1)
p.write_text(s, encoding="utf-8", newline="\n")
print("patched", len(s.split("\n")), "lines")
