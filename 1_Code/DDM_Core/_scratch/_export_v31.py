# -*- coding: utf-8 -*-
"""把 v3.1 docx 导出为 markdown（含图表占位），用于 v4 重排。

输出：5_Reference/03_论文写作/_v31_export.md
约定：图片 → [[FIG:图X-Y]]；表格 → markdown 表；标题按 Heading 级别转 #。
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

BASE = Path(__file__).resolve().parents[3] / "5_Reference" / "03_论文写作"
SRC = BASE.parent / "05_交付件" / "毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx"
OUT = BASE / "_v31_export.md"

doc = Document(str(SRC))
body = doc.element.body


def para_text(p) -> str:
    return "".join(n.text or "" for n in p.iter(qn("w:t")))


def style_of(p) -> str:
    pPr = p.find(qn("w:pPr"))
    if pPr is None:
        return ""
    ps = pPr.find(qn("w:pStyle"))
    return ps.get(qn("w:val")) if ps is not None else ""


lines: list[str] = []
pending_fig = None
fig_no = 0
tbl_no = 0

for child in body.iterchildren():
    tag = child.tag.split("}")[-1]
    if tag == "p":
        if child.findall(".//" + qn("a:blip")):
            pending_fig = len(lines)  # 占位行，等下一段 caption 补图号
            lines.append("")
            continue
        txt = para_text(child).strip()
        if not txt:
            continue
        st = style_of(child)
        if st.startswith("Heading") or st.startswith("1") or st in ("2", "3", "4", "5"):
            lvl = 1
            if st.startswith("Heading"):
                m = re.search(r"(\d+)", st)
                lvl = int(m.group(1)) if m else 1
            elif st in ("2", "3", "4", "5"):
                lvl = {"2": 1, "3": 2, "4": 3, "5": 3}[st]
            lines.append("#" * max(1, min(lvl, 3)) + " " + txt)
            continue
        # 图题：紧跟在图片后的 “图X-Y …”
        m = re.match(r"^图\s*(\d+)\s*[-–—]\s*(\d+)", txt)
        if m and pending_fig is not None:
            fig_no += 1
            lines[pending_fig] = f"[[FIG:图{m.group(1)}-{m.group(2)}]]"
            lines.append(f"**{txt}**")
            pending_fig = None
            continue
        if txt.startswith("结果说明"):
            lines.append("> " + txt)
            continue
        lines.append(txt)
    elif tag == "tbl":
        tbl_no += 1
        rows = []
        for tr in child.findall(qn("w:tr")):
            cells = []
            for tc in tr.findall(qn("w:tc")):
                t = " ".join(
                    "".join(n.text or "" for n in p.iter(qn("w:t")))
                    for p in tc.findall(qn("w:p"))
                ).strip()
                cells.append(t.replace("|", "/"))
            rows.append(cells)
        if not rows:
            continue
        w = max(len(r) for r in rows)
        rows = [r + [""] * (w - len(r)) for r in rows]
        lines.append("")
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("|" + "|".join(["---"] * w) + "|")
        for r in rows[1:]:
            lines.append("| " + " | ".join(r) + " |")
        lines.append("")

OUT.write_text("\n\n".join(lines), encoding="utf-8")
txt = OUT.read_text(encoding="utf-8")
print(f"段落/表：{len(lines)} 行，{len(txt)} 字")
print(f"图占位 {txt.count('[[FIG:')} 个、表格 {tbl_no} 张")
miss = [m for m in re.findall(r"\[\[FIG:(图[^\]]+)\]\]", txt)]
print("图号：", " ".join(miss))
