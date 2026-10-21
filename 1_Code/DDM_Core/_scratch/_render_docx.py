# -*- coding: utf-8 -*-
"""用 Word COM 把 docx 转成 PDF，再用 PyMuPDF 渲染前几页为 PNG，便于检查版式。"""
import sys
from pathlib import Path

import fitz

ROOT = Path(r"D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
DOCX = ROOT / "5_Reference/05_交付件/论文预览_可写部分_v1_20261021.docx"
PDF = ROOT / "1_Code/DDM_Core/_scratch/_preview_doc.pdf"
OUTDIR = ROOT / "1_Code/DDM_Core/_scratch"

if PDF.exists():
    PDF.unlink()

import win32com.client as win32  # noqa: E402

word = win32.Dispatch("Word.Application")
word.Visible = False
try:
    d = word.Documents.Open(str(DOCX), ReadOnly=True)
    d.SaveAs(str(PDF), FileFormat=17)  # wdFormatPDF
    print("pdf pages:", d.ComputeStatistics(2))  # wdStatisticPages
    d.Close(False)
finally:
    word.Quit()

doc = fitz.open(PDF)
print("pdf", PDF.stat().st_size, "bytes,", doc.page_count, "pages")
for i in range(min(doc.page_count, 8)):
    pix = doc[i].get_pixmap(dpi=110)
    f = OUTDIR / f"_doc_p{i+1}.png"
    pix.save(f)
    print(f.name, f.stat().st_size)
