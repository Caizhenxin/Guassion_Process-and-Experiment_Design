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
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import xml.sax.saxutils as sax

BASE = Path(__file__).resolve().parent
TEMPLATE = BASE / "温_毕业论文_设计空间_v13最终版.docx"
OUT = BASE / ("毕业论文_蔡振辛_初稿v2_图版_20260902.docx"
              if os.environ.get("THESIS_FIGS") == "1"
              else "毕业论文_蔡振辛_初稿v1_20260902.docx")
DRAFT12 = BASE.parent / "毕业论文初稿_第1-2章_绪论与文献综述_20260902.md"
DRAFT35 = BASE.parent / "毕业论文初稿_第3-5章_已完成研究_20260902.md"

W = "xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'"


def esc(t):
    return sax.escape(t)


BASE_RPR = ('<w:rFonts w:hint="default" w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
            ' w:eastAsia="宋体" w:cs="Times New Roman"/><w:kern w:val="0"/><w:sz w:val="24"/>')


def runs_from_inline(text, color=None, size_half=None, font_east=None):
    """支持 **加粗** 与 `代码/路径`；rPr 基座复刻模板正文（宋体/小四）。"""
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
    extra_sz = ('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size_half, size_half)) if size_half else ""
    extra_ea = ('<w:eastAsia w:val="%s"/>' % font_east) if font_east else ""
    for fmt, seg in out:
        rpr = "<w:rPr>" + BASE_RPR + extra_sz + extra_ea + fmt + (
            "<w:color w:val='C00000'/>" if color else "") + "</w:rPr>"
        xml += "<w:r>%s<w:t xml:space='preserve'>%s</w:t></w:r>" % (rpr, esc(seg))
    return xml


def para(text, style=None, color=None, align=None, size_half=None, font_east=None, indent=True, line_400=True):
    ppr = "<w:pPr>"
    if style:
        ppr += "<w:pStyle w:val='%s'/>" % style
    if line_400:
        ppr += '<w:widowControl/><w:spacing w:line="400" w:lineRule="exact"/>'
    if indent and not align:
        ppr += '<w:ind w:firstLine="480" w:firstLineChars="200"/>'
    if align:
        ppr += "<w:jc w:val='%s'/>" % align
    ppr += "</w:pPr>"
    if size_half or font_east:
        return ("<w:p>%s<w:r><w:rPr>%s</w:rPr><w:t xml:space='preserve'>%s</w:t></w:r></w:p>"
                % (ppr, BASE_RPR +
                   ('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size_half, size_half) if size_half else "") +
                   ('<w:eastAsia w:val="%s"/>' % font_east if font_east else ""), esc(text)))
    return "<w:p>%s%s</w:p>" % (ppr, runs_from_inline(text, color=color))


def heading(text, level):
    style = {1: "2", 2: "3", 3: "4", 4: "4"}[level]
    sp = {"1": '<w:spacing w:before="312" w:after="312"/>',
          "2": '<w:spacing w:before="156" w:after="156"/>',
          "3": '<w:spacing w:before="120" w:after="120"/>',
          "4": '<w:spacing w:before="120" w:after="120"/>'}[str(level)]
    runrpr = ('<w:rPr><w:rFonts w:hint="default" w:ascii="Times New Roman"'
              ' w:hAnsi="Times New Roman" w:cs="Times New Roman"/></w:rPr>')
    return ("<w:p><w:pPr><w:pStyle w:val='%s'/>%s<w:outlineLvl w:val='%d'/></w:pPr>"
            "<w:r>%s<w:t xml:space='preserve'>%s</w:t></w:r></w:p>"
            % (style, sp, level - 1, runrpr, esc(re.sub(r"\*\*|`", "", text))))


def pagebreak():
    return "<w:p><w:r><w:br w:type='page'/></w:r></w:p>"


def toc_field():
    return ('<w:p><w:pPr><w:pStyle w:val="2"/></w:pPr>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:t>（目录：请全选文档后按 F9 更新域）</w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(26)
    w = int.from_bytes(head[16:20], "big")
    h = int.from_bytes(head[20:24], "big")
    return w, h


def image_para(path, rid, docid, target_w=4700000):
    w, h = png_size(path)
    cx = int(target_w)
    cy = int(cx * h / max(w, 1))
    pic = (
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:line="360" w:lineRule="auto"/></w:pPr>'
        '<w:r><w:drawing>'
        '<wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="%d" name="fig%d"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<pic:nvPicPr><pic:cNvPr id="%d" name="fig%d"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    ) % (cx, cy, docid, docid, docid, docid, rid, cx, cy)
    return pic


def md_to_xml(lines, sub_map=None, no_bullet=False, no_indent=False):
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
        out.append(para(s, color=color, indent=not no_indent))
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
    xml.append(para("硕 士 学 位 论 文", align="center", size_half=44, font_east="黑体", line_400=False))
    xml.append(para(" ", align="center", line_400=False))
    xml.append(para(meta["TITLE_CN"].split("：")[0] + "：", align="center", size_half=30, font_east="黑体", line_400=False))
    xml.append(para(meta["TITLE_CN"].split("：")[1] if "：" in meta["TITLE_CN"] else "", align="center", size_half=30, font_east="黑体", line_400=False))
    xml.append(para(" ", align="center", line_400=False))
    for label, val in [("研究生", meta["AUTHOR"]), ("指导教师", meta["ADVISOR"]),
                       ("培养单位", meta["UNIT"]), ("一级学科", meta["DISCIPLINE1"]),
                       ("二级学科", meta["DISCIPLINE2"]), ("完成时间", meta["FINISH_TIME"]),
                       ("答辩时间", meta["DEFENSE_TIME"])]:
        xml.append(para("%s：　%s" % (label, val), align="center", size_half=28, line_400=False))
    xml.append(para(" ", align="center", line_400=False))
    xml.append(para("学　　号：　%s" % meta["STUDENT_ID"], align="center", size_half=24, line_400=False))
    xml.append(pagebreak())

    # ============ 独创性/授权声明 ============
    xml.append(heading("学位论文独创性声明", 1))
    xml.append(para("本人郑重声明：所提交的学位论文是本人在导师指导下进行的研究工作和取得的研究成果。本论文中除引文外，所有实验、数据和有关材料均是真实的。本论文中除引文和致谢的内容外，不包含其他人或其它机构已经发表或撰写过的研究成果。其他同志对本研究所做的贡献均已在论文中作了声明并表示了谢意。", indent=False, line_400=False))
    xml.append(para("学位论文作者签名：　　　　　　　　　日　　期：　　年　　月　　日", indent=False, line_400=False))
    xml.append(pagebreak())
    xml.append(heading("学位论文使用授权声明", 1))
    xml.append(para("研究生在校攻读学位期间论文工作的知识产权单位属南京师范大学。学校有权保存本学位论文的电子和纸质文档，可以借阅或上网公布本学位论文的部分或全部内容，可以采用影印、复印等手段保存、汇编本学位论文。学校可以向国家有关机关或机构送交论文的电子和纸质文档，允许论文被查阅和借阅。", indent=False, line_400=False))
    xml.append(para("学位论文作者签名：　　　　　　　　　指导教师签名：", indent=False, line_400=False))
    xml.append(para("日　　期：　　年　　月　　日　　　　日　　期：　　年　　月　　日", indent=False, line_400=False))
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
    xml.append(md_to_xml(refs, no_bullet=True, no_indent=True))
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

        import os as _os
        media = []  # (target_name, bytes)
        if _os.environ.get("THESIS_FIGS") == "1":
            figdir = BASE.parents[1] / "3_Figures" / "Thesis_20260902" / "figures"

            def pick(prefix):
                hits = sorted(p.name for p in figdir.glob(prefix + "*.png"))
                return (figdir / hits[0]) if hits else None

            FIGS = [
                ("实验设计空间与理论假设", "F4-1_design_space.png", "F4-1_design_space.png",
                 "图4-1 实验设计空间 Ω 与 8 组取点分布",
                 "横轴分别为 P/W 与 T/W，颜色=质量档。G1/G2（高遗漏，红）位于资源受限角落，"
                 "主口径 G3–G8 覆盖 P∈{0,8,120}、T∈{30,80,100,500}、W∈{600,800,1100,1500}；"
                 "G7 与 G8 构成 W=800 处的 T 对比（30 vs 80 ms）。"),
                ("行为层面：SPE_RT 与 SPE_ACC", "F5-1_spe_subjects.png", "F5-1_spe_subjects.png",
                 "图5-1 被试级 SPE：行为层（RT/ACC）与 DDM 参数层（4 链）",
                 "行为 SPE_RT 中位数在多数单元为负（自我更快），长时限条件（G5/G6）偏移更明显，"
                 "短时限 P0_T30_W300 反而为正；SPE_ACC 差异小。右图 4 链 SPE_v 显示 G4–G8 为正、"
                 "G3 为负（与 G3 行为 SPE_RT 为正的方向一致）；组间差异未达统计显著（表5-3）。"),
                ("DDM 参数层面：SPE_v 的主口径检验", "F5-2_gpower_4chain.png", "F5-2_gpower_4chain.png",
                 "图5-2 参数层 SPE_v 观察效应量 vs 80% 功效门槛（4 链口径）",
                 "G3–G8 观察 f≈.40，低于最小可检测 f≈.47；G5–G8 更低（f≈.21 vs .52）。"
                 "说明以当前被试量，参数层组间差异缺乏检验功效——应结合行为层显著结果与描述性趋势解读。"),
                ("DDM 参数层面：SPE_v 的主口径检验", "F5-3_bf_prior_sensitivity_4chain.png", "F5-3_bf_prior_sensitivity_4chain.png",
                 "图5-3 贝叶斯因子对先验尺度的敏感性（G3–G8, 4 链）",
                 "在常见的先验尺度 r 下，ANOVA（组别哑变量）与回归的 BF10 均未超过 3 的实质性阈值，"
                 "部分先验下接近或低于 1，说明数据对“参数层存在组间差异”的支持为轶事级甚至不支持——"
                 "与研究一叙述（差异不显著+功效不足）一致。"),
                ("遗漏率与偏倚模式", "F6-1", "F6-1_omission_sensitivity.png",
                 "图6-1 Omission 敏感性：遗漏率与 Censor vs Drop 影响（图题待按所选图核对）",
                 "短窗口组（G1–G4）遗漏率高且 Censor/Drop 参数估计差异超出 95% CI；"
                 "低遗漏组（G5–G8）两种方案基本一致——对应表6-1 中 G1 的 Δ≈6.81 等结果。"),
                ("OPN 第一版", "F6-2", "F6-2_opn_accuracy.png",
                 "图6-2 OPN（省略概率网络）第一版预测表现",
                 "网络在训练/测试集上 R²≈.99/.99、MAE≈.017，说明小网络可近似 (θ, deadline)→omission 概率，"
                 "为显式 omission 建模提供概念验证（表6-2）。"),
                ("参数层拟合与交叉验证", "F7-1_insample_fit.png", "F7-1_insample_fit.png",
                 "图7-1 混合模型 in-sample 参数拟合（canonical4）",
                 "训练条件上预测与 4 链 HDDM 后验均值几乎重合（表7-3），主要反映 GP 对残差的吸收，"
                 "属插值性质，不宜作为外推能力的证据。"),
                ("参数层拟合与交叉验证", "F7-2_locv_fit.png", "F7-2_locv_fit.png",
                 "图7-2 留一条件交叉验证（LOCV, 6 折）",
                 "外推预测误差显著增大（v RMSE≈1.2），r 介于 −0.02~0.53，表明仅 6 个设计点不足以支撑"
                 "GP 泛化——这是需要更大设计空间采样的结构性证据（表7-4）。"),
                ("行为层重建（核心证据）", "F7-3_behavior_scatter.png", "F7-3_behavior_scatter.png",
                 "图7-3 行为层重建：模拟 vs 真实（identity 与 condition 层）",
                 "正确 RT 均值 r≈.97（RMSE≈45 ms）、ACC r≈.99、omission r≈.97、SPE_RT（条件层）r≈.75；"
                 "相关由跨条件趋势驱动，解读须同时参考 RMSE 与逐格偏差（表7-5，in-sample）。"),
                ("候选设计点（探索性）", "F7-4_candidate_points.png", "F7-4_candidate_points.png",
                 "图7-4 基于 GP 不确定性的候选实验点",
                 "高不确定性集中于 T≈480–500 ms、W≈300–350 ms 区域（总不确定≈2.39，主要来自 v）；"
                 "top-20 间几乎无区分，仅作为“信息量最少区域”的探索性提示，不作最优设计推荐。"),
                ("8.3 结果", "F8-1_sliding_window.png", "F8-1_sliding_window.png",
                 "图8-1 内部数据滑动窗口分析：匹配键 SPE 正确率差随 RT 窗口变化",
                 "内部 88 人数据：自我—陌生人正确率差在约 234–780 ms 窗口内显著为正，峰值约 0.19"
                 "（≈440 ms）——系内部数据证据，非跨研究结论。"),
                ("8.3 结果", "F8-3", "F8-3_stimcoding_crf.png",
                 "图8-3 起始点偏向（Stim-Coding）仿真的 CRF 曲线（双引擎）",
                 "起始点偏向越大，自我侧早期正确率优势越明显；两套引擎（Euler–Maruyama/HDDM）形态一致，"
                 "支持“偏向机制→行为模式”的生成链解释（定性对照）。"),
            ]
            # 解析实际文件名（F6-1/F6-2/F8-3 为前缀）
            resolved = []
            for anchor, spec, _fname, caption, explain in FIGS:
                if spec.startswith("F6-1") or spec.startswith("F6-2") or spec.startswith("F8-3"):
                    p = pick(spec)
                    if not p:
                        print("缺图:", spec)
                        continue
                    spec = p.name
                resolved.append((anchor, figdir / spec, caption, explain))
            # 按锚点分组并插入
            groups = {}
            for anchor, p, caption, explain in resolved:
                groups.setdefault(anchor, []).append((p, caption, explain))
            rid_idx = 1
            docid = 9000
            for anchor, items in groups.items():
                block = ""
                for p, caption, explain in items:
                    rid = "rIdThesisFig%d" % rid_idx
                    rid_idx += 1
                    docid += 1
                    media.append(("word/media/thesis_fig_%d.png" % (docid - 9000), p.read_bytes()))
                    block += image_para(str(p), rid, docid)
                    block += para(caption, align="center", size_half=21, line_400=False)
                    block += para("结果说明：" + explain, indent=False)
                anchor_ok = False
                pos = new_doc.find(anchor)
                if pos >= 0:
                    endp = new_doc.find("</w:p>", pos)
                    if endp >= 0:
                        cut = endp + len("</w:p>")
                        new_doc = new_doc[:cut] + block + new_doc[cut:]
                        anchor_ok = True
                print(("已插入图组" if anchor_ok else "⚠️ 锚点未找到:") + anchor)
            # 更新关系文件
            rels_name = "word/_rels/document.xml.rels"
            rels = zin.read(rels_name).decode("utf-8")
            add = ""
            for i in range(1, rid_idx):
                rid = "rIdThesisFig%d" % i
                add += '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/thesis_fig_%d.png"/>' % (rid, i)
            rels = rels.replace("</Relationships>", add + "</Relationships>")

        # 简单校验 XML
        import xml.etree.ElementTree as ET
        ET.fromstring(new_doc.encode("utf-8"))
        if OUT.exists():
            OUT.unlink()
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    data = new_doc.encode("utf-8")
                elif item.filename == rels_name and _os.environ.get("THESIS_FIGS") == "1":
                    data = rels.encode("utf-8")
                else:
                    data = zin.read(item.filename)
                zout.writestr(item, data)
            if _os.environ.get("THESIS_FIGS") == "1":
                for name, blob in media:
                    zout.writestr(name, blob)
        print("OK ->", OUT, "bytes:", OUT.stat().st_size)


if __name__ == "__main__":
    build()
