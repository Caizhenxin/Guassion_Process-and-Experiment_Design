# -*- coding: utf-8 -*-
"""把验收检查器的 `--doc` 默认路径改到真实文件名。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\exp_Check\check_stage1_acceptance.py")
s = p.read_text(encoding="utf-8")
s = s.replace('"5_Reference/08_工作流/Stage1_程序技术验收方案.md"',
              '"5_Reference/08_工作流/Stage1_技术验证记录.md"')
p.write_text(s, encoding="utf-8")
print("新默认路径在:", "Stage1_技术验证记录.md" in s)
