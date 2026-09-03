# -*- coding: utf-8 -*-
"""
Word 论文初稿生成器 v0 (2026-09-02)
====================================
以同校已过审论文《温_毕业论文_设计空间_v13最终版.docx》为格式模板（保留其 styles/theme/
sectPr），仅替换 word/document.xml 正文；正文内容由以下 md 源文件组装（中文保留，格式近似，
⚠️ 待补/待核 段落标红便于作者识别）：
  1) 封面+声明（内置模板文字）+ 摘要/Abstract（_b_front_摘要.md 的 META 与 摘要/Abstract 节）
  2) 目录域（打开后 Ctrl+A → F9 更新）
  3) 章节组装：
     第1章 引言        <- _b_ch1_引言.md
     第2章 文献综述    <- 初稿第1-2章文件：'# 第2章' 至 '## 2.3' 前
     第3章 综述(二)    <- 同上：'## 2.3' 至 '## 参考文献' 前（2.3→3.1,2.4→3.2,2.5→3.3,2.6→3.4）
     第4章 研究框架    <- _b_ch4_研究框架.md
     第5~7章 研究一/二/三 <- 初稿第3-5章文件（3→5,4→6,5→7 编号平移）
     第8章 研究四      <- _b_ch8_研究四_多源验证.md
     第9章 总讨论      <- _b_ch9_总讨论.md
     第10章 结论       <- _b_ch10_结论.md
     参考文献/附录/致谢 <- _b_refs_backmatter.md（去掉外层 # 标题行管理，参考文献行 '-'→正文行）
依赖：python 标准库（zipfile/xml）；无需 python-docx。
"""
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import xml.sax.saxutils as sax

BASE = Path(__file__).resolve().parent
TEMPLATE = BASE / "温_毕业论文_设计空间_v13最终版.docx"
OUT = BASE / "毕业论文_蔡振辛_初稿v0_20260902.docx"
DRAFT12 = BASE.parent / "毕业论文初稿_第1-2章_绪论与文献综述_20260902.md"
DRAFT35 = BASE.parent / "毕业论文初稿_第3-5章_已完成研究_20260902.md"

W = "xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'"


def esc(t):
    return sax.escape(t)


def runs_from_inline(text, color=None):
    """支持 **加粗** 与 `代码/路径`；返回 runs XML。"""
    out = []
    tokens = re.split(r"(\*\*.+?\*\*|`[^`]+`)", text)
    for tk in tokens:
        if not tk:
            continue
        if tk.startswith("**") and tk.endswith("**"):
            out.append(("<w:b/>", tk[2:-2]))
        elif tk.startswith("`") and tk.endswith("`"):
            out.append(("<w:b/><w:rFonts w:ascii='Consolas' w:hAnsi='Consolas'/>", tk[1:-1]))
        else:
            out.append(("", tk))
    xml = ""
    for fmt, seg in out:
        rpr = "<w:rPr>%s%s%s</w:rPr>" % (fmt, "<w:color w:val='C00000'/>" if color else "", "")
        xml += "<w:r>%s<w:t xml:space='preserve'>%s</w:t></w:r>" % (rpr, esc(seg))
    return xml


def para(text, style=None, color=None, align=None, size_half=None, font_east=None):
    ppr = "<w:pPr>"
    if style:
        ppr += "<w:pStyle w:val='%s'/>" % style
    if align:
        ppr += "<w:jc w:val='%s'/>" % align
    if size_half or font_east:
        rpr = "<w:rPr>"
        if size_half:
            rpr += "<w:sz w:val='%d'/><w:szCs w:val='%d'/>" % (size_half, size_half)
        if font_east:
            rpr += "<w:rFonts w:ascii='Times New Roman' w:hAnsi='Times New Roman' w:eastAsia='%s'/>" % font_east
        rpr += "</w:rPr>"
        ppr += "</w:pPr>"
        body = "<w:r>%s<w:t xml:space='preserve'>%s</w:t></w:r>" % (rpr, esc(text))
        return "<w:p>%s%s</w:p>" % (ppr, body)
    ppr += "</w:pPr>"
    return "<w:p>%s%s</w:p>" % (ppr, runs_from_inline(text, color=color))


def heading(text, level):
    style = {1: "2", 2: "3", 3: "4", 4: "4"}[level]
    return "<w:p><w:pPr><w:pStyle w:val='%s'/><w:outlineLvl w:val='%d'/></w:pPr>%s</w:p>" % (
        style, level - 1, runs_from_inline(text))


def pagebreak():
    return "<w:p><w:r><w:br w:type='page'/></w:r></w:p>"


def toc_field():
    return ('<w:p><w:pPr><w:pStyle w:val="2"/></w:pPr>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:t>（目录：请全选文档后按 F9 更新域）</w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def md_to_xml(lines, sub_map=None, no_bullet=False):
    """极简 md→OOXML：'#/##/###/####' 标题、正文、'- '条目、'|'表格、'>'引用、'⚠️'标红。"""
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        s = line.strip()
        if not s or s == "---":
            i += 1
            continue
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            txt = s.lstrip("#").strip()
            if sub_map:
                for k, v in sub_map.items():
                    if txt.startswith(k + ".") or txt == k or txt.startswith("第%s章" % k) or txt.startswith("%s " % k):
                        txt = txt.replace(k, v, 1)
            out.append(heading(txt, min(lvl, 4)))
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            tbl = ["<w:tbl><w:tblPr><w:tblStyle w:val='16'/></w:tblPr>"]
            for ri, r in enumerate(rows):
                tbl.append("<w:tr>")
                for c in r:
                    run = "<w:rPr><w:b/></w:rPr>" if ri == 0 else ""
                    tbl.append("<w:tc><w:tcPr><w:tcW w:w='0' w:type='auto'/></w:tcPr><w:p>"
                               "<w:r>%s<w:t xml:space='preserve'>%s</w:t></w:r></w:p></w:tc>" % (run, esc(c)))
                tbl.append("</w:tr>")
            tbl.append("</w:tbl>")
            out.append("".join(tbl))
            continue
        color = None
        if s.startswith(">") or "⚠️" in s or "【待补" in s or "【待核" in s or "【写作提示" in s or "【作者" in s:
            color = "C00000"
            s = s.lstrip(">").strip()
        if s.startswith("- "):
            s = s[2:] if no_bullet else "• " + s[2:]
        out.append(para(s, color=color))
        i += 1
    return "".join(out)


def slice_lines(text, start_marker, end_marker=None):
    lines = text.splitlines(keepends=True)
    si = 0
    for j, ln in enumerate(lines):
        if ln.strip().startswith(start_marker):
            si = j
            break
    ei = len(lines)
    if end_marker:
        for j in range(si + 1, len(lines)):
            if lines[j].strip().startswith(end_marker):
                ei = j
                break
    # 去掉首章标题行本身（第X章标题由调用方提供）
    body = lines[si + 1:ei]
    return body


def sub_map_pairs(pairs):
    return {k: v for k, v in pairs}


def build():
    front = (BASE / "_b_front_摘要.md").read_text(encoding="utf-8")
    meta = {}
    for ln in front.splitlines():
        if ln.startswith("TITLE_CN=") or ln.startswith("TITLE_EN=") or ln.startswith("AUTHOR=") \
           or ln.startswith("STUDENT_ID=") or ln.startswith("ADVISOR=") or ln.startswith("UNIT=") \
           or ln.startswith("DISCIPLINE1=") or ln.startswith("DISCIPLINE2=") \
           or ln.startswith("FINISH_TIME=") or ln.startswith("DEFENSE_TIME="):
            k, v = ln.split("=", 1)
            meta[k] = v

    abstract_cn = []
    abstract_en = []
    cur = None
    for ln in front.splitlines():
        s = ln.strip()
        if s == "# 摘要":
            cur = "cn"
            continue
        if s == "# Abstract":
            cur = "en"
            continue
        if cur and (s.startswith("关键词：") or s.startswith("Keywords:")):
            if cur == "cn":
                abstract_cn.append(ln)
            else:
                abstract_en.append(ln)
            cur = None
        elif cur:
            (abstract_cn if cur == "cn" else abstract_en).append(ln)

    # ============ 封面 ============
    xml = []
    xml.append(para("硕 士 学 位 论 文", align="center", size_half=44, font_east="黑体"))
    xml.append(para(" ", align="center"))
    xml.append(para(meta["TITLE_CN"].split("：")[0] + "：", align="center", size_half=30, font_east="黑体"))
    xml.append(para(meta["TITLE_CN"].split("：")[1] if "：" in meta["TITLE_CN"] else "", align="center", size_half=30, font_east="黑体"))
    xml.append(para(" ", align="center"))
    for label, val in [("研究生", meta["AUTHOR"]), ("指导教师", meta["ADVISOR"]),
                       ("培养单位", meta["UNIT"]), ("一级学科", meta["DISCIPLINE1"]),
                       ("二级学科", meta["DISCIPLINE2"]), ("完成时间", meta["FINISH_TIME"]),
                       ("答辩时间", meta["DEFENSE_TIME"])]:
        xml.append(para("%s：　%s" % (label, val), align="center", size_half=28))
    xml.append(para(" ", align="center"))
    xml.append(para("学　　号：　%s" % meta["STUDENT_ID"], align="center", size_half=24))
    xml.append(pagebreak())

    # ============ 独创性/授权声明 ============
    xml.append(heading("学位论文独创性声明", 1))
    xml.append(para("本人郑重声明：所提交的学位论文是本人在导师指导下进行的研究工作和取得的研究成果。本论文中除引文外，所有实验、数据和有关材料均是真实的。本论文中除引文和致谢的内容外，不包含其他人或其它机构已经发表或撰写过的研究成果。其他同志对本研究所做的贡献均已在论文中作了声明并表示了谢意。"))
    xml.append(para("学位论文作者签名：　　　　　　　　　日　　期：　　年　　月　　日"))
    xml.append(pagebreak())
    xml.append(heading("学位论文使用授权声明", 1))
    xml.append(para("研究生在校攻读学位期间论文工作的知识产权单位属南京师范大学。学校有权保存本学位论文的电子和纸质文档，可以借阅或上网公布本学位论文的部分或全部内容，可以采用影印、复印等手段保存、汇编本学位论文。学校可以向国家有关机关或机构送交论文的电子和纸质文档，允许论文被查阅和借阅。"))
    xml.append(para("学位论文作者签名：　　　　　　　　　指导教师签名："))
    xml.append(para("日　　期：　　年　　月　　日　　　　日　　期：　　年　　月　　日"))
    xml.append(pagebreak())

    # ============ 摘要 / Abstract ============
    xml.append(heading("摘要", 1))
    xml.append("".join(para(s) for s in abstract_cn if s.strip()))
    xml.append(pagebreak())
    xml.append(heading("Abstract", 1))
    xml.append("".join(para(s) for s in abstract_en if s.strip()))
    xml.append(pagebreak())

    # ============ 目录 ============
    xml.append(toc_field())
    xml.append(pagebreak())

    # ============ 正文章节 ============
    draft12 = DRAFT12.read_text(encoding="utf-8")
    draft35 = DRAFT35.read_text(encoding="utf-8")

    ch1 = (BASE / "_b_ch1_引言.md").read_text(encoding="utf-8").splitlines(keepends=True)
    xml.append(heading("第1章 引言", 1))
    xml.append(md_to_xml(ch1[1:]))

    sec2 = slice_lines(draft12, "# 第2章 文献综述", "## 2.3 ")
    xml.append(heading("第2章 文献综述：自我优势效应与证据积累模型", 1))
    xml.append(md_to_xml(sec2))

    sec3 = slice_lines(draft12, "## 2.3 高斯过程", "## 参考文献")
    xml.append(heading("第3章 文献综述：遗漏反应建模、高斯过程与实验设计优化", 1))
    xml.append(md_to_xml(sec3, sub_map=sub_map_pairs([("2.3", "3.1"), ("2.4", "3.2"), ("2.5", "3.3"), ("2.6", "3.4")])))

    ch4 = (BASE / "_b_ch4_研究框架.md").read_text(encoding="utf-8").splitlines(keepends=True)
    xml.append(heading("第4章 研究框架与总体方法", 1))
    xml.append(md_to_xml(ch4[1:]))

    for src_ch, title, new in [(3, "研究一：实验设计空间对自我优势效应的系统性调控", 5),
                               (4, "研究二：Omission 处理方法对 DDM 参数估计的系统影响", 6),
                               (5, "研究三：Sigmoid 与高斯过程的混合生成模型：构建与验证", 7)]:
        seg = slice_lines(draft35, "# 第%d章" % src_ch,
                          "# 第%d章" % (src_ch + 1) if src_ch < 5 else None)
        xml.append(heading("第%d章 %s" % (new, title), 1))
        xml.append(md_to_xml(seg, sub_map=sub_map_pairs([(str(src_ch), str(new))])))

    for f, title in [("_b_ch8_研究四_多源验证.md", "第8章 研究四：SPE 数据库、CRF 与机制仿真的多源验证"),
                     ("_b_ch9_总讨论.md", "第9章 总讨论"),
                     ("_b_ch10_结论.md", "第10章 结论")]:
        body = (BASE / f).read_text(encoding="utf-8").splitlines(keepends=True)
        xml.append(heading(title, 1))
        xml.append(md_to_xml(body[1:]))

    back = (BASE / "_b_refs_backmatter.md").read_text(encoding="utf-8").splitlines(keepends=True)
    # 参考文献 段（'# 参考文献'后至'# 附录A'前）
    refs = slice_lines("".join(back), "# 参考文献", "# 附录A")
    xml.append(heading("参考文献", 1))
    xml.append(md_to_xml(refs, no_bullet=True))
    for sec_marker, title in [("# 附录A", "附录A　冻结设计表与关键数字锁定表"),
                              ("# 附录B", "附录B　脚本与可复现性说明"),
                              ("# 致谢", "致谢")]:
        seg = slice_lines("".join(back), sec_marker,
                          "# 附录B" if sec_marker == "# 附录A" else "# 致谢" if sec_marker == "# 附录B" else None)
        xml.append(heading(title, 1))
        xml.append(md_to_xml(seg))

    # ============ 打包：复用模板，仅替换 document.xml（不解压，内存重打包）============
    with zipfile.ZipFile(TEMPLATE) as zin:
        with zin.open("word/document.xml") as f:
            doc = f.read().decode("utf-8")
        body_i = doc.find("<w:body>")
        assert body_i >= 0, "template body not found"
        head = doc[: body_i + len("<w:body>")]
        tail_i = doc.rfind("</w:body>")
        sect_i = doc.rfind("<w:sectPr", body_i, tail_i)
        sect_j = doc.find("</w:sectPr>", sect_i)
        sectpr = doc[sect_i: sect_j + len("</w:sectPr>")]
        tail = doc[tail_i + len("</w:body>"):]
        new_doc = head + "".join(xml) + sectpr + "</w:body>" + tail
        # 简单校验 XML
        import xml.etree.ElementTree as ET
        ET.fromstring(new_doc.encode("utf-8"))
        if OUT.exists():
            OUT.unlink()
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = new_doc.encode("utf-8") if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)
        print("OK ->", OUT, "bytes:", OUT.stat().st_size)


if __name__ == "__main__":
    build()
