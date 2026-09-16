# -*- coding: utf-8 -*-
"""临时：把编码兜底插到 from __future__ 之后，重建 v3.1。"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "5_Reference" / "终版论文格式及要求" / "_build_docx_v3.py"
s = BUILDER.read_text(encoding="utf-8")

# 移除上一版错误插入的 guard
bad = ("import sys\n\ntry:  # 控制台编码兜底（避免 ⚠️ 等字符在 GBK 控制台报错）\n"
       "    sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"replace\")\n"
       "except Exception:\n    pass\n\n")
s = s.replace(bad, "")

anchor = "from __future__ import annotations\n"
assert s.count(anchor) == 1, f"锚点异常 {s.count(anchor)}"
guard = anchor + (
    "\nimport sys\n"
    "try:  # 控制台编码兜底（避免 ⚠️ 等字符在 GBK 控制台报错）\n"
    "    sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"replace\")\n"
    "except Exception:\n"
    "    pass\n"
)
s = s.replace(anchor, guard)
ast.parse(s)
BUILDER.write_text(s, encoding="utf-8")
print("[fix] 已修正插入位置，语法 OK")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log12.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
tail = (r.stdout or "").strip().splitlines()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("[build] exit:", r.returncode)
print("最后一行:", tail[-1] if tail else "(no stdout)")
