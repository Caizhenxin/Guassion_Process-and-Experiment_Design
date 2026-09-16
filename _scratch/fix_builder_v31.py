# -*- coding: utf-8 -*-
"""临时：给构建脚本加编码兜底 + 输出改为新文件名，然后重建。"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "5_Reference" / "终版论文格式及要求" / "_build_docx_v3.py"

s = BUILDER.read_text(encoding="utf-8")

guard = (
    "import sys\n"
    "\n"
    "try:  # 控制台编码兜底（避免 ⚠️ 等字符在 GBK 控制台报错）\n"
    "    sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"replace\")\n"
    "except Exception:\n"
    "    pass\n"
    "\n"
)
if "sys.stdout.reconfigure" not in s:
    s = guard + s
    print("[fix] 已插入编码兜底")

# 输出文件名改为 v3.1（绕开被 Word 占用的旧文件）
s = s.replace('OUT = BASE / "毕业论文_蔡振辛_初稿v3_图版_20260912.docx"',
              'OUT = BASE / "毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx"')
print("[fix] 输出目标:", [ln for ln in s.splitlines() if ln.startswith("OUT = ")][0])

ast.parse(s)
BUILDER.write_text(s, encoding="utf-8")
print("[fix] 语法 OK，已写入")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log11.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "(no stdout)")
if r.returncode:
    print((r.stderr or "")[-500:])
