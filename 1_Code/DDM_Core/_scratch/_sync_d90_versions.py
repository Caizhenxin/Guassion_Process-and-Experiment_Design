# -*- coding: utf-8 -*-
"""D90：Stage7 / PTB 说明里的程序与手册版本行同步到 v4.7 / v2.6。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
edits = [
    (ROOT / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md",
     [("`主试培训手册_Exp_Design_Formal.md`（v2.5，395 行）+ `.docx`（16647 B）",
       "`主试培训手册_Exp_Design_Formal.md`（v2.6，403 行）+ `.docx`（68121 B）")]),
    (ROOT / "1_Code" / "Experiment" / "exp_matlab" / "PTB免费版配置说明.md",
     [("正式实验程序 **v4.6**", "正式实验程序 **v4.7**"),
      ("主试培训手册（v2.5，D4 口径", "主试培训手册（v2.6，D4 口径")]),
]
for path, pairs in edits:
    s = path.read_text(encoding="utf-8")
    for old, new in pairs:
        assert s.count(old) == 1, "%s: 锚点命中 %d 次: %r" % (path.name, s.count(old), old)
        s = s.replace(old, new, 1)
    path.write_text(s, encoding="utf-8", newline="\n")
    print("ok", path.name, len(s.split("\n")), "行")
