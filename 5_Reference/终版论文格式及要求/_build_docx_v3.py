# -*- coding: utf-8 -*-
"""
Word 论文 v3 生成器（2026-09-12）
=================================
以同校已过审论文《温_毕业论文_设计空间_v13最终版.docx》为格式模板（沿用其 styles/theme/sectPr），
仅替换 word/document.xml 正文；内容来源：
  1) 封面+声明+摘要/Abstract+目录  <- _v3_front_摘要.md（META + # 摘要 / # Abstract）
  2) 正文（第1–10章 + 参考文献 + 附录A-C + 致谢）<- _v3_正文.md
  3) 插图：按"锚点段落"把图插入该段之后，并附图题与结果说明
     （图文件目录：3_Figures/Thesis_v3_20260912/）

输出：毕业论文_蔡振辛_初稿v3_图版_20260912.docx
依赖：仅 python 标准库（zipfile/xml），无需 python-docx。
"""
from __future__ import annotations

import sys
try:  # 控制台编码兜底（避免 ⚠️ 等字符在 GBK 控制台报错）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import re
import xml.etree.ElementTree as ET
import xml.sax.saxutils as sax
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
TEMPLATE = BASE / "温_毕业论文_设计空间_v13最终版.docx"
FRONT = BASE / "_v3_front_摘要.md"
BODY = BASE / "_v3_正文.md"
FIGDIR = BASE.parents[1] / "3_Figures" / "Thesis_v3_20260912"
OUT = BASE / "毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx"

BASE_RPR = ('<w:rFonts w:hint="default" w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
            ' w:eastAsia="宋体" w:cs="Times New Roman"/><w:kern w:val="0"/><w:sz w:val="24"/>')


def esc(t):
    return sax.escape(t)


def runs_from_inline(text, color=None):
    out = []
    for tk in re.split(r"(\*\*.+?\*\*|`[^`]+`)", text):
        if not tk:
            continue
        if tk.startswith("**") and tk.endswith("**"):
            out.append(("<w:b/>", tk[2:-2]))
        elif tk.startswith("`") and tk.endswith("`"):
            out.append(("<w:rFonts w:ascii='Consolas' w:hAnsi='Consolas'/>", tk[1:-1]))
        else:
            out.append(("", tk))
    xml = ""
    for fmt, seg in out:
        rpr = "<w:rPr>" + BASE_RPR + fmt + ("<w:color w:val='C00000'/>" if color else "") + "</w:rPr>"
        xml += "<w:r>%s<w:t xml:space='preserve'>%s</w:t></w:r>" % (rpr, esc(seg))
    return xml


def para(text, style=None, color=None, align=None, size_half=None, font_east=None,
         indent=True, line_400=True):
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
        rpr = BASE_RPR + ('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size_half, size_half) if size_half else "") \
              + ('<w:eastAsia w:val="%s"/>' % font_east if font_east else "") \
              + ("<w:color w:val='C00000'/>" if color else "")
        return "<w:p>%s<w:r><w:rPr>%s</w:rPr><w:t xml:space='preserve'>%s</w:t></w:r></w:p>" % (ppr, rpr, esc(text))
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
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def image_para(path, rid, docid, target_w=4700000):
    w, h = png_size(path)
    cx = int(target_w)
    cy = int(cx * h / max(w, 1))
    return (
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:line="360" w:lineRule="auto"/></w:pPr>'
        '<w:r><w:drawing>'
        '<wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
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


RED_KEYS = ("⚠️", "⏳", "【待补", "【待核", "【待填", "【写作提示", "【作者", "【说明")


def md_to_xml(lines):
    out, i = [], 0
    while i < len(lines):
        s = lines[i].rstrip("\n").strip()
        if not s or s == "---":
            i += 1
            continue
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            out.append(heading(s.lstrip("#").strip(), min(lvl, 4)))
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
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
        color = "C00000" if any(k in s for k in RED_KEYS) else None
        if s.startswith("> "):
            color = "C00000"
            s = s[2:]
        if s.startswith("- "):
            s = "• " + s[2:]
        out.append(para(s, color=color))
        i += 1
    return "".join(out)


# ------------------------------------------------------------------
# 插图清单：(锚点段落文本, 图文件名, 图题, 结果说明)
# 图插在"包含锚点文本的段落"之后
# ------------------------------------------------------------------
FIGS = [
    ("本研究所使用的 8 个实验条件及其质量分档如表 4-1 与图 4-1 所示。", "F4-1_design_space.png",
     "图4-1 实验设计空间 Ω = (P, T, W) 与 8 组取点",
     "颜色代表质量分档：灰=排除（遗漏率 > 50%）、橙=谨慎（遗漏率约 35–40%）、蓝=主口径核心（遗漏率 < 16%）。"
     "可见 G1/G2 位于“练习不足 + 窗口极短”的资源受限角落；G7/G8 在 W = 800 处构成 T = 30 vs 80 ms 的对比；"
     "P 仅有 0/8/120 三个水平，是后文模型外推受限的根本原因。"),
    ("被试级 SPE 的分布见图 5-1。", "F5-1_spe_subjects.png",
     "图5-1 被试级 SPE 分布（黑菱形=条件均值）",
     "左图为 SPE_RT（自我 − 陌生人，负值=自我更快），右图为 SPE_ACC。箱体高度反映个体差异（远大于组间差异）；"
     "G5（−47.9 ms）与 G6（−65.9 ms）效应最强，G1（+4.3 ms）与 G3（+13.8 ms）出现方向反转；"
     "箱体下方标注该条件的遗漏率。要点：SPE 不是恒定常数，而是设计参数的函数。"),
    ("各条件的 HDDM 群体层参数与其 95% 可信区间见图 5-2。", "F5-2_hddm_params_forest.png",
     "图5-2 HDDM 群体层参数与 95% 可信区间（森林图）",
     "三幅图分别为 v_self、v_stranger 与 a。横线不跨 0 表示该参数显著；两条件横线不重叠表示差异可靠。"
     "关键现象：G1–G3 的漂移率可信区间极宽（甚至跨 0），说明这些条件的参数不可辨识——这是第 6 章数据质量准则的直接依据。"),
    ("两种处理方案的参数差异随遗漏率的变化见图 6-1。", "F6-1_omission_delta.png",
     "图6-1 Censor 与 Drop 的参数差异随遗漏率变化",
     "横轴为遗漏率，纵轴为两种处理方案的参数之差；圆点=95% 可信区间不重叠（差异可靠），方点=重叠；"
     "黄色阴影为 15%–35%（本数据没有条件落在该区间）。可见遗漏率越大差异越大，G1 的 Δv_self = 6.81；"
     "而 ΔSPE_v 始终很小，说明相对效应比绝对水平稳健。"),
    ("OPN 第一版的预测表现见图 6-2。", "F6-2_opn.png",
     "图6-2 OPN（省略概率网络）第一版的预测表现",
     "以小型多层感知机近似“(DDM 参数, deadline) → omission 概率”的映射，训练/测试集 R² = .990/.986、"
     "测试 MAE = .017。该结果为概念验证（4,699 组快速模式样本）；正式路线为复用官方 ddm_opn.onnx 并接入 HSSM 完成联合似然估计。"),
    ("in-sample 拟合结果见图 7-1。", "F7-1_insample.png",
     "图7-1 混合模型 in-sample 拟合",
     "训练条件上预测值与 HDDM 后验均值几乎重合（v、z 的 r ≈ 1.00，a 的 r = 0.36）。"
     "该图反映的是 GP 对残差的吸收，属插值性质，不能作为外推能力的证据。"),
    ("留一条件交叉验证（LOCV）的结果见图 7-2。", "F7-2_locv.png",
     "图7-2 留一条件交叉验证（LOCV，6 折）",
     "每次留出一个设计条件、用其余 5 个条件重训后再预测被留出条件。预测误差显著增大（v_self 的 RMSE = 1.59），"
     "相关系数 r 介于 −0.29 至 +0.26（v_self 为 −0.03）。结论：仅 6 个设计点不足以支撑参数层外推——"
     "这是设计问题而非方法问题，也是扩充设计空间的直接论据。"),
    ("模型比较与模型恢复的结果见图 7-3。", "F7-3_model_comparison.png",
     "图7-3 模型比较与模型恢复",
     "左图为四个候选模型在同一预测任务上的 LOCV 聚合误差：纯 Sigmoid（1.135）< Sigmoid+GP（1.232）"
     "< 均值基线（1.269）≪ 线性（8.535）。右图为模型恢复的混淆矩阵：线性与 Sigmoid+GP 的对角率均为 0，"
     "说明当前设计无法判别精细的模型差异。两点结论：非线性映射不可或缺；GP 层的价值在于不确定性量化而非预测精度。"),
    ("后验预测检验的逐格结果见图 7-4。", "F7-4_ppc_interval.png",
     "图7-4 后验预测检验：观测值 vs 95% 预测区间",
     "从各条件的 HDDM 迹线中联合抽样被试水平参数 200 次，按真实被试数、每身份 130 试次与真实 deadline 重新仿真。"
     "红叉为观测值，蓝线与横线为预测中位数与 95% 预测区间。多数红叉落在区间之外，说明模型在行为分布层面存在系统失配。"),
    ("各统计量的覆盖率汇总见图 7-5。", "F7-5_ppc_coverage.png",
     "图7-5 PPC 覆盖率汇总",
     "五个统计量的 95% 预测区间覆盖率仅为 .17–.33（名义值 .95）：acc_all 与 acc_responded 均为 .167、"
     "正确 RT 均值 .278、RT 中位数 .333、遗漏率 .333。覆盖率 ≥ .90 才算通过，故当前模型未通过该检验。"),
    ("RT 分位数与正确率的联合模式（QP 图）见图 7-6。", "F7-6_ppc_qp.png",
     "图7-6 QP 图：正确 RT 分位数 × 正确率（观测 vs 预测）",
     "QP 图是 DDM 领域检验模型拟合的标准图形。线为预测中位数，× 为观测值。观测点与预测线的偏离方向"
     "（长时限条件高估正确率、低估遗漏率）提示模型缺少跨试次变异、注意脱失（lapse）与塌缩边界机制。"),
    ("基于 GP 预测不确定性的候选设计点见图 7-7。", "F7-7_candidates.png",
     "图7-7 基于 GP 预测不确定性的候选设计点（探索性）",
     "高不确定性集中于 T ≈ 480–500 ms、W ≈ 300–350 ms 区域，主要来自漂移率分量。但 top-20 候选的不确定性"
     "几乎相同（第 3–4 位小数才分序），且短窗口区域在真实数据中与高遗漏相关，故本图仅作为"
     "“覆盖最差的高不确定区域”的探索性提示，不作为最优设计推荐。"),
    ("内部数据的滑动窗口分析结果见图 8-1。", "F8-1_sliding_window.png",
     "图8-1 内部数据滑动窗口分析：匹配键 SPE 正确率差随 RT 窗口变化",
     "基于内部 88 人匹配试次：自我—陌生人正确率差在约 234–780 ms 窗口内显著为正，峰值约 0.19（约 440 ms）。"
     "需注意：该结论基于内部数据，不得表述为“大规模跨研究发现”。"),
    ("Stim-Coding 仿真得到的 CRF 曲线见图 8-2。", "F8-2_stimcoding_crf.png",
     "图8-2 起始点偏向（Stim-Coding）仿真的 CRF 曲线（双引擎）",
     "人为设定起始点偏向（z = 0.50/0.55/0.60/0.65），用 Euler–Maruyama 与 HDDM 生成器两套引擎仿真得到 CRF 曲线。"
     "偏向越大，自我侧早期（快反应）正确率优势越明显；两套引擎形态一致，支持“起始点偏向 → 早期行为优势”的生成链解释。"
     "（与真实 CRF 的定量叠加对比仍待补充。）"),
    ("各拟合来源的收敛诊断分布见图 6-6", "F6-6_convergence.png",
     "图6-6 HDDM 后验收敛诊断（Split-R̂ 与 ESS）",
     "基于 24 次拟合的既有单链迹线：左为 Split-R̂ 分布，右为有效样本量（对数）。"
     "Censor 敏感性拟合的核心参数全部达标（R̂ ≤ 1.024、ESS ≥ 173）；主拟合中 G5–G7 全部达标，"
     "但 G3 严重不收敛（z 的 ESS = 8.6）、G8 的起始点参数也不达标（ESS = 22）。"
     "注意：单链 Split-R̂ 为近似口径，严格的多链诊断需增加抽样并保存多条链。"),
    ("模拟与实测 CRF 的定量叠加对比见图 8-3。", "F8-3_crf_overlay.png",
     "图8-3 模拟与实测 CRF 的定量叠加对比",
     "(A) 实测 CRF（88 人，被试级 cluster bootstrap 95% CI）：自我条件的匹配键反应比例在各 RT 分位箱均高于"
     "陌生人条件，差异在 RT ≈ 480 ms 处最大（+0.14）。(B) 仿真 CRF：4 个起始点偏向（z = 0.50–0.65）× 两套引擎，"
     "并叠加实测的自我/陌生人曲线。(C) 差异曲线：仿真（大偏向 − 中性）与实测（自我 − 陌生人）在快反应端方向一致，"
     "但慢反应端仿真差异偏小，说明起点偏向只能解释实测自我优势的一部分。"),
    ("SPE 数据库可获得子集的跨研究分布及其与设计变量的关系见图 8-4。", "F8-4_spe_database.png",
     "图8-4 SPE 数据库可获得子集的跨研究分布与设计变量关系（探索性）",
     "(A) 44 个数据集的 SPE_RT 森林图（点=数据集均值，横线=被试级 95% CI，红点线=合并均值 −98.0 ms）；"
     "全部数据集均为自我更快。(B)(C) SPE 与刺激呈现时间、练习试次数的关系（点大小 ∝ 被试数）："
     "ρ 分别为 −0.19 与 +0.21，95% CI 均跨 0，属探索性且不显著。"),
    ("参数恢复的真值—恢复值对照见图 6-3。", "F6-3_param_recovery_scatter.png",
     "图6-3 参数恢复：真值 vs 恢复值",
     "左列为 Censor 方案、右列为 Drop 方案；三行分别为 v_self、v_stranger 与边界 a。虚线为完美恢复线。"
     "可见漂移率的绝对水平存在系统性偏倚（Censor 低估、Drop 高估），而边界 a 的散点更分散。"
     "作为对照，SPE_v（自我与陌生人漂移率之差）在两方案下均紧密贴合对角线，覆盖率 100%。"),
    ("遗漏率与参数偏倚的关系见图 6-4。", "F6-4_omission_bias_curve.png",
     "图6-4 遗漏率 → 参数偏倚曲线",
     "横轴为实际遗漏率，纵轴为估计偏倚，红色与橙色虚线标注论文原先引用的 35% 与 15% 分档。"
     "漂移率的绝对偏倚随遗漏率单调增大（Censor 向负方向、Drop 向正方向），50% 以上达到 1.6–3.2；"
     "而 SPE_v 的偏倚在所有水平下均小于 0.11，说明相对效应稳健。"),
    ("各参数 95% CI 覆盖率对比见图 6-5。", "F6-5_recovery_coverage.png",
     "图6-5 参数恢复的 95% CI 覆盖率",
     "虚线为名义 95%。Censor 与 Drop 方案下 v、a、t、z 的覆盖率均远低于名义值（0–28%），"
     "唯独 SPE_v 达到 100%。这为「绝对参数水平不可解释、相对效应可解释」的结论提供了直接证据。"),
    ("三种配置下的参数对照见图 6-7", "F6-7_refit_comparison.png",
     "图6-7 主口径重跑：新旧群体层参数对照",
     "灰点为历史配置（p_outlier = 0.05、单链 3,000 draws）的估计，蓝点为修正配置（p_outlier = 0、4 链 × 8,000 draws）"
     "并含 95% CI。可见历史配置的区间宽度约为修正配置的两倍，且 G3、G6、G8 的中心值发生实质移动——"
     "说明早期参数结论受到配置冲突与收敛不足的共同影响。"),
]


def build():
    front = FRONT.read_text(encoding="utf-8")
    meta, abstract_cn, abstract_en, cur = {}, [], [], None
    for ln in front.splitlines():
        s = ln.strip()
        if s.startswith(("TITLE_CN=", "TITLE_EN=", "AUTHOR=", "STUDENT_ID=", "ADVISOR=", "UNIT=",
                         "DISCIPLINE1=", "DISCIPLINE2=", "FINISH_TIME=", "DEFENSE_TIME=")):
            k, v = s.split("=", 1)
            meta[k] = v
            continue
        if s == "# 摘要":
            cur = "cn"; continue
        if s == "# Abstract":
            cur = "en"; continue
        if cur:
            (abstract_cn if cur == "cn" else abstract_en).append(ln)

    xml = []
    xml.append(para("硕 士 学 位 论 文", align="center", size_half=44, font_east="黑体", line_400=False))
    xml.append(para(" ", align="center", line_400=False))
    t_cn = meta["TITLE_CN"]
    if "：" in t_cn:
        a, b = t_cn.split("：", 1)
        xml.append(para(a + "：", align="center", size_half=30, font_east="黑体", line_400=False))
        xml.append(para(b, align="center", size_half=30, font_east="黑体", line_400=False))
    else:
        xml.append(para(t_cn, align="center", size_half=30, font_east="黑体", line_400=False))
    xml.append(para(" ", align="center", line_400=False))
    for label, val in [("研究生", meta["AUTHOR"]), ("指导教师", meta["ADVISOR"]), ("培养单位", meta["UNIT"]),
                       ("一级学科", meta["DISCIPLINE1"]), ("二级学科", meta["DISCIPLINE2"]),
                       ("完成时间", meta["FINISH_TIME"]), ("答辩时间", meta["DEFENSE_TIME"])]:
        xml.append(para("%s：　%s" % (label, val), align="center", size_half=28, line_400=False))
    xml.append(para(" ", align="center", line_400=False))
    xml.append(para("学　　号：　%s" % meta["STUDENT_ID"], align="center", size_half=24, line_400=False))
    xml.append(pagebreak())

    xml.append(heading("学位论文独创性声明", 1))
    xml.append(para("本人郑重声明：所提交的学位论文是本人在导师指导下进行的研究工作和取得的研究成果。本论文中除引文外，"
                    "所有实验、数据和有关材料均是真实的。本论文中除引文和致谢的内容外，不包含其他人或其它机构已经发表或撰写过的"
                    "研究成果。其他同志对本研究所做的贡献均已在论文中作了声明并表示了谢意。", indent=False, line_400=False))
    xml.append(para("学位论文作者签名：　　　　　　　　　日　　期：　　年　　月　　日", indent=False, line_400=False))
    xml.append(pagebreak())
    xml.append(heading("学位论文使用授权声明", 1))
    xml.append(para("研究生在校攻读学位期间论文工作的知识产权单位属南京师范大学。学校有权保存本学位论文的电子和纸质文档，"
                    "可以借阅或上网公布本学位论文的部分或全部内容，可以采用影印、印等复制手段保存、汇编本学位论文。"
                    "学校可以向国家有关机关或机构送交论文的电子和纸质文档，允许论文被查阅和借阅。", indent=False, line_400=False))
    xml.append(para("学位论文作者签名：　　　　　　　　　指导教师签名：", indent=False, line_400=False))
    xml.append(para("日　　期：　　年　　月　　日　　　　日　　期：　　年　　月　　日", indent=False, line_400=False))
    xml.append(pagebreak())

    xml.append(heading("摘要", 1))
    xml.append("".join(para(s) for s in abstract_cn if s.strip()))
    xml.append(pagebreak())
    xml.append(heading("Abstract", 1))
    xml.append("".join(para(s) for s in abstract_en if s.strip()))
    xml.append(pagebreak())

    xml.append(toc_field())
    xml.append(pagebreak())

    body = BODY.read_text(encoding="utf-8").splitlines(keepends=True)
    xml.append(md_to_xml(body))
    new_doc = "".join(xml)

    # ---- 插入插图（锚点定位）----
    media, rid_idx, docid, report = [], 1, 9000, []
    for anchor, fname, caption, explain in FIGS:
        path = FIGDIR / fname
        if not path.exists():
            report.append(f"缺图：{fname}")
            continue
        pos = new_doc.find(esc(anchor))
        if pos < 0:
            report.append(f"⚠️ 锚点未找到：{anchor[:24]}…")
            continue
        endp = new_doc.find("</w:p>", pos)
        cut = endp + len("</w:p>")
        rid = "rIdThesisFigV3_%d" % rid_idx
        rid_idx += 1
        docid += 1
        media.append(("word/media/thesis_v3_fig_%d.png" % (docid - 9000), path.read_bytes()))
        block = image_para(str(path), rid, docid)
        block += para(caption, align="center", size_half=21, line_400=False)
        block += para("结果说明：" + explain, indent=False)
        new_doc = new_doc[:cut] + block + new_doc[cut:]
        report.append(f"已插入 {caption.split(' ')[0]}")

    with zipfile.ZipFile(TEMPLATE) as zin:
        doc = zin.read("word/document.xml").decode("utf-8")
        body_i = doc.find("<w:body>")
        head = doc[: body_i + len("<w:body>")]
        tail_i = doc.rfind("</w:body>")
        sect_i = doc.rfind("<w:sectPr", body_i, tail_i)
        sect_j = doc.find("</w:sectPr>", sect_i)
        sectpr = doc[sect_i: sect_j + len("</w:sectPr>")]
        tail = doc[tail_i + len("</w:body>"):]
        new_doc = head + new_doc + sectpr + "</w:body>" + tail

        ET.fromstring(new_doc.encode("utf-8"))  # 校验 XML

        rels_name = "word/_rels/document.xml.rels"
        rels = zin.read(rels_name).decode("utf-8")
        add = "".join(
            '<Relationship Id="rIdThesisFigV3_%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"'
            ' Target="media/thesis_v3_fig_%d.png"/>' % (i, i) for i in range(1, rid_idx))
        rels = rels.replace("</Relationships>", add + "</Relationships>")

        out_path = OUT
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
                print("⚠️ 原文件被占用（Word 打开中），改输出到：", out_path.name)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    data = new_doc.encode("utf-8")
                elif item.filename == rels_name:
                    data = rels.encode("utf-8")
                else:
                    data = zin.read(item.filename)
                zout.writestr(item, data)
            for name, blob in media:
                zout.writestr(name, blob)

    print("插图报告：")
    for r in report:
        print("  ", r)
    print(f"OK -> {out_path.name}  ({out_path.stat().st_size/1024:.0f} KB, 内嵌图 {len(media)} 张)")


if __name__ == "__main__":
    build()
