# -*- coding: utf-8 -*-
"""临时：把收敛诊断图纳入 v3 图集与 docx 构建脚本，并重新编译。"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGV3 = ROOT / "3_Figures" / "Thesis_v3_20260912"
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BUILDER = DOC / "_build_docx_v3.py"

src = ROOT / "3_Figures" / "TenRules_Revision_20260912" / "F6-6_convergence.png"
dst = FIGV3 / "F6-6_convergence.png"
shutil.copy2(src, dst)
print("[fig] 已复制：", dst.name)

entry = '''    ("各拟合来源的收敛诊断分布见图 6-6。", "F6-6_convergence.png",
     "图6-6 HDDM 后验收敛诊断（Split-R̂ 与 ESS）",
     "基于 24 次拟合的既有单链迹线：左为 Split-R̂ 分布，右为有效样本量（对数）。"
     "Censor 敏感性拟合的核心参数全部达标（R̂ ≤ 1.024、ESS ≥ 173）；主拟合中 G5–G7 全部达标，"
     "但 G3 严重不收敛（z 的 ESS = 8.6）、G8 的起始点参数也不达标（ESS = 22）。"
     "注意：单链 Split-R̂ 为近似口径，严格的多链诊断需增加抽样并保存多条链。"),
'''
s = BUILDER.read_text(encoding="utf-8")
if "F6-6_convergence.png" not in s:
    marker = "]\n\n\ndef build()"
    assert s.count(marker) == 1, f"锚点数量异常: {s.count(marker)}"
    s = s.replace(marker, entry + marker)
    BUILDER.write_text(s, encoding="utf-8")
    print("[builder] 已登记图6-6")
else:
    print("[builder] 图6-6 已存在")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout[-600:] if r.stdout else "")
print(r.stderr[-400:] if r.stderr else "")
