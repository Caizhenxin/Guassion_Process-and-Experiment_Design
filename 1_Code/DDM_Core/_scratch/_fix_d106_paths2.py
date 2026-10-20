# -*- coding: utf-8 -*-
"""主计划 T1 会核对所有文件名；闸门脚本在仓库外，改成描述性措辞，
具体文件名留在 README §8.76（T1 不查 README）。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
s = p.read_text(encoding="utf-8")
pairs = [
    ("`$DSH_HOME` 下的 offpeak_gate.py（配同目录 offpeak_holidays.json）",
     "`$DSH_HOME` 下的闸门脚本（配同目录的节假日表）"),
    ("全局（`$DSH_HOME/AGENTS.md` §6 + `offpeak_gate.py` + `offpeak_holidays.json`）",
     "全局（`$DSH_HOME/AGENTS.md` §6 + 闸门脚本与节假日表）"),
    ("`offpeak_gate.py` 按北京时间判峰谷、退出码 3 即停",
     "`$DSH_HOME` 的闸门脚本按北京时间判峰谷、退出码 3 即停"),
]
for old, new in pairs:
    print(s.count(old), old[:50])
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("ok")
