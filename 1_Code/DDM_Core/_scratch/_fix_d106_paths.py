# -*- coding: utf-8 -*-
"""把主计划里两个仓库外文件名从反引号里摘出来（check_traceability 会把反引号里的
裸文件名当成仓库内路径去核对）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
s = p.read_text(encoding="utf-8")
pairs = [
    ("`C:\\Users\\蔡振辛\\AppData\\Roaming\\dsh-desktop\\harness\\offpeak_gate.py`（+ 同目录 `offpeak_holidays.json`）",
     "`$DSH_HOME` 下的 offpeak_gate.py（配同目录 offpeak_holidays.json）"),
    ("`$DSH_HOME/offpeak_gate.py`", "`$DSH_HOME` 下的 offpeak_gate.py"),
]
for old, new in pairs:
    c = s.count(old)
    print(c, old[:60])
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("ok")
