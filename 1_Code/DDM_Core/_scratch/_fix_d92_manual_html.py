# -*- coding: utf-8 -*-
"""手册 v2.7 修正：`<details>/<summary>` HTML 会被原样写进 Word 版（打印出来是乱码标签），
改成普通小标题。"""
from pathlib import Path

F = Path("1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md")
src = F.read_text(encoding="utf-8")

OLD = "<details><summary>要一条一条手动跑，或想看清每条在测什么（都在 exp_matlab 目录下执行）</summary>"
NEW = "**要一条一条手动跑，或想看清每条在测什么**（都在 `exp_matlab` 目录下执行）："
assert src.count(OLD) == 1
src = src.replace(OLD, NEW)
assert src.count("</details>") == 1
src = src.replace("</details>\n", "")
F.write_text(src, encoding="utf-8", newline="\n")
print(f"手册：HTML 标签已去掉，{len(src.splitlines())} 行")
