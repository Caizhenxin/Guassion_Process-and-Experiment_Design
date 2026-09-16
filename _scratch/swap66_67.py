# -*- coding: utf-8 -*-
"""临时：交换 §6.3.4 中图6-6/6-7 锚点顺序，使编号与出现顺序一致。"""
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BODY = DOC / "_v3_正文.md"
BUILDER = DOC / "_build_docx_v3.py"

s = BODY.read_text(encoding="utf-8")
pat = re.compile(r"三种配置下的参数对照见图 6-7。\n\n各拟合来源的收敛诊断分布见图 6-6。")
rep = "各拟合来源的收敛诊断分布见图 6-6。\n\n三种配置下的参数对照见图 6-7。"
s2, n = pat.subn(rep, s)
print("[body] 交换次数:", n)
BODY.write_text(s2, encoding="utf-8")

# 同步构建脚本锚点（保持与正文一致）
b = BUILDER.read_text(encoding="utf-8")
b = b.replace('("三种配置下的参数对照见图 6-7"', '("三种配置下的参数对照见图 6-7"')
BUILDER.write_text(b, encoding="utf-8")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
out = DOC / "毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx"
z = zipfile.ZipFile(out)
xml = z.read("word/document.xml").decode("utf-8")
caps = [m.strip()[:20] for m in re.findall(r"(图[0-9]-[0-9]+ [^<]{2,20})", xml)]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("[build] exit:", r.returncode)
print("图数:", len(caps), "|", " ".join(c.split(" ")[0] for c in caps))
print("表格:", xml.count("<w:tbl>"), "| 内嵌图:",
      len([n for n in z.namelist() if n.startswith("word/media/thesis_v3")]),
      "| %.2f MB" % (out.stat().st_size / 1048576), "| 红色待办:", xml.count("C00000"))
