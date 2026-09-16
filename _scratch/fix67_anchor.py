# -*- coding: utf-8 -*-
"""临时：对齐图6-7 锚点并重建。"""
import ast
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BUILDER = DOC / "_build_docx_v3.py"

s = BUILDER.read_text(encoding="utf-8")
pairs = [('("新旧参数对照见图 6-7"', '("三种配置下的参数对照见图 6-7"'),
         ('("新旧参数对照见图 6-7。"', '("三种配置下的参数对照见图 6-7"')]
for a, b in pairs:
    if a in s:
        s = s.replace(a, b)
        print("[builder] 命中并替换：", a)
ast.parse(s)
BUILDER.write_text(s, encoding="utf-8")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
out = DOC / "毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx"
z = zipfile.ZipFile(out)
xml = z.read("word/document.xml").decode("utf-8")
caps = [m.strip()[:20] for m in re.findall(r"(图[0-9]-[0-9]+ [^<]{2,20})", xml)]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("[build] exit:", r.returncode)
print("图数:", len(caps), "|", " ".join(c.split(" ")[0] for c in caps))
print("表格对象:", xml.count("<w:tbl>"), "| 内嵌图:",
      len([n for n in z.namelist() if n.startswith("word/media/thesis_v3")]),
      "| %.2f MB" % (out.stat().st_size / 1048576), "| 红色待办:", xml.count("C00000"))
