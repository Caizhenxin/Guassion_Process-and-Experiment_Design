# -*- coding: utf-8 -*-
"""临时：把 v3 图文件名统一为与图号一致，并同步两个脚本中的引用。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "3_Figures" / "Thesis_v3_20260912"
PKG = ROOT / "1_Code" / "Python_for_Check" / "TenRules_Revision_20260912"
DOC = ROOT / "5_Reference" / "终版论文格式及要求"

RENAME = {
    "F7-3_ppc_interval.png": "F7-4_ppc_interval.png",
    "F7-4_ppc_coverage.png": "F7-5_ppc_coverage.png",
    "F7-5_ppc_qp.png": "F7-6_ppc_qp.png",
    "F7-6_model_comparison.png": "F7-3_model_comparison.png",
    "F8-3_stimcoding_crf.png": "F8-2_stimcoding_crf.png",
}

# 1) 图文件重命名
for old, new in RENAME.items():
    src, dst = FIG / old, FIG / new
    if src.exists():
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        print(f"[fig] {old} -> {new}")
    else:
        print(f"[fig] 跳过（不存在）{old}")

# 2) 图集脚本：目标文件名
p = PKG / "make_thesis_v3_figures.py"
s = p.read_text(encoding="utf-8")
for old, new in RENAME.items():
    s = s.replace(f'"{old}"', f'"{new}"')
p.write_text(s, encoding="utf-8")
print("[script] make_thesis_v3_figures.py 已同步")

# 3) 构建脚本：FIG 文件名
p = DOC / "_build_docx_v3.py"
s = p.read_text(encoding="utf-8")
for old, new in RENAME.items():
    n = s.count(f'"{old}"')
    s = s.replace(f'"{old}"', f'"{new}"')
    print(f"[builder] {old} -> {new} ({n})")
p.write_text(s, encoding="utf-8")
print("完成")
