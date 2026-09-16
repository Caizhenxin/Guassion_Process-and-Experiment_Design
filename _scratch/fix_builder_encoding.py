# -*- coding: utf-8 -*-
"""临时：给构建脚本加 stdout 编码兜底并重建。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "5_Reference" / "终版论文格式及要求" / "_build_docx_v3.py"
s = BUILDER.read_text(encoding="utf-8")
if "sys.stdout.reconfigure" not in s:
    s = s.replace("import sys\n", "import sys\n\ntry:  # 控制台编码兜底\n"
                                  "    sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"replace\")\n"
                                  "except Exception:\n    pass\n", 1)
    BUILDER.write_text(s, encoding="utf-8")
    print("[fix] 已加入编码兜底")
else:
    print("[fix] 已有编码兜底")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log9.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
print((r.stdout or "")[-400:])
