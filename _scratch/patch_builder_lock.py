# -*- coding: utf-8 -*-
"""临时：让构建脚本在目标 docx 被占用时自动改用备用文件名，并重建。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "5_Reference" / "终版论文格式及要求" / "_build_docx_v3.py"

s = BUILDER.read_text(encoding="utf-8")
old = """        if OUT.exists():
            OUT.unlink()"""
new = """        out_path = OUT
        if out_path.exists():
            try:
                out_path.unlink()
            except PermissionError:
                out_path = out_path.with_name(out_path.stem + "_新" + out_path.suffix)
                if out_path.exists():
                    try:
                        out_path.unlink()
                    except PermissionError:
                        import time as _t
                        out_path = out_path.with_name(
                            out_path.stem + _t.strftime("%H%M%S") + out_path.suffix)
                print("⚠️ 原文件被占用（Word 打开中），改输出到：", out_path.name)"""
assert s.count(old) == 1, f"未匹配：{s.count(old)}"
s = s.replace(old, new)
# 后续写出与打印使用 out_path
s = s.replace("""        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:""",
              """        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:""")
s = s.replace("""    print(f"OK -> {OUT.name}  ({OUT.stat().st_size/1024:.0f} KB, 内嵌图 {len(media)} 张)")""",
              """    print(f"OK -> {out_path.name}  ({out_path.stat().st_size/1024:.0f} KB, 内嵌图 {len(media)} 张)")""")
BUILDER.write_text(s, encoding="utf-8")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log8.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
