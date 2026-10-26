from pathlib import Path

PLAN = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
            r"\5_Reference\08_工作流\工作流_主计划.md")
lines = PLAN.read_text(encoding="utf-8").split("\n")
i = 561
print("修前行:", lines[i][:80])
bad = "`|stimulus_dur_actual − T| > 一帧" 
good = "`stimulus_dur_actual` 与 `T` 的差超过一帧"
assert bad in lines[i], "锚点不在 L562"
lines[i] = lines[i].replace(bad, good)
PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("修后该行竖线数 =", lines[i].count("|"))

import subprocess, sys
# check_files 的用法先看一眼
p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\DDM_Core\_scratch\check_files.py")
head = p.read_text(encoding="utf-8").split("\n")
for k, ln in enumerate(head[:30], 1):
    if "argv" in ln or "usage" in ln.lower() or "用法" in ln:
        print(f"{k}: {ln.strip()}")
