# -*- coding: utf-8 -*-
"""临时：修复构建脚本中的引号错误并重建。"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "5_Reference" / "终版论文格式及要求" / "_build_docx_v3.py"

s = BUILDER.read_text(encoding="utf-8")
bad = '唯独 SPE_v 达到 100%。这为"绝对参数水平不可解释、相对效应可解释"的结论提供了直接证据。'
good = '唯独 SPE_v 达到 100%。这为「绝对参数水平不可解释、相对效应可解释」的结论提供了直接证据。'
print("bad 出现次数:", s.count(bad))
s = s.replace(bad, good)
try:
    ast.parse(s)
    print("语法 OK")
except SyntaxError as e:
    print("语法错误：行", e.lineno, e.msg)
    # 兜底：打印该行附近内容
    lines = s.splitlines()
    for i in range(max(0, e.lineno - 3), min(len(lines), e.lineno + 2)):
        print(f"  {i+1}: {lines[i][:160]}")
BUILDER.write_text(s, encoding="utf-8")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log6.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
