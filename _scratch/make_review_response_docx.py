# -*- coding: utf-8 -*-
"""
make_review_response_docx.py —— 生成《南京师范大学硕士学位论文评阅意见修改说明》预案稿
=====================================================================================
以学校空白表单（A南京师范大学硕士学位论文评阅意见修改说明.docx）为模板（保留其 styles/footer/sectPr），
替换 word/document.xml 正文，输出到同一文件夹的新文件名。

内容说明（重要）
    · "示例意见"为根据本文薄弱环节**预判**的评阅问题，需在收到真实评阅意见后替换为原文；
    · "修改说明"部分与"详细修改说明"部分直接采用本项目已完成的实证工作与修订结果，可直接沿用。
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import xml.sax.saxutils as sax

FOLDER = Path(r"C:\Users\蔡振辛\Desktop\研究生毕业论文\提交文件")
TEMPLATE = FOLDER / "A南京师范大学硕士学位论文评阅意见修改说明.docx"
OUT = FOLDER / "A南京师范大学硕士学位论文评阅意见修改说明_蔡振辛_预案稿_20260913.docx"

RPR = ('<w:rFonts w:hint="eastAsia" w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
       ' w:eastAsia="宋体" w:cs="Times New Roman"/><w:kern w:val="0"/><w:sz w:val="{sz}"/>'
       '<w:szCs w:val="{sz}"/>')
SZ = 24  # 小四


def esc(t):
    return sax.escape(str(t))


def runs(text, bold=False, color=None, sz=SZ, font=None):
    fmt = "<w:b/>" if bold else ""
    ea = f'<w:rFonts w:eastAsia="{font}"/>' if font else ""
    col = f"<w:color w:val='{color}'/>" if color else ""
    rpr = "<w:rPr>" + RPR.format(sz=sz) + ea + fmt + col + "</w:rPr>"
    return f"<w:r>{rpr}<w:t xml:space='preserve'>{esc(text)}</w:t></w:r>"


def para(text, bold=False, color=None, align=None, indent=True, sz=SZ, font=None, space=0):
    text = str(text).replace("**", "")  # 不渲染 markdown 加粗标记
    ppr = "<w:pPr>"
    if align:
        ppr += f"<w:jc w:val='{align}'/>"
    if space:
        ppr += f'<w:spacing w:before="{space}" w:after="{space}"/>'
    else:
        ppr += '<w:spacing w:line="360" w:lineRule="auto"/>'
    if indent:
        ppr += '<w:ind w:firstLine="480" w:firstLineChars="200"/>'
    ppr += "</w:pPr>"
    return f"<w:p>{ppr}{runs(text, bold=bold, color=color, sz=sz, font=font)}</w:p>"


def heading(text, level=1):
    sz = 30 if level == 1 else (28 if level == 2 else 24)
    font = "黑体" if level <= 2 else "黑体"
    ppr = ('<w:pPr><w:spacing w:before="180" w:after="120"/>'
           '<w:outlineLvl w:val="%d"/></w:pPr>' % (level - 1))
    return f"<w:p>{ppr}{runs(text, bold=True, sz=sz, font=font)}</w:p>"


def table(rows, widths, header_bold=True, red_cols=()):
    """rows: list of list[str]；widths: 相对宽度列表（整数）"""
    total = sum(widths)
    grid = "".join(f'<w:gridCol w:w="{int(9000 * w / total)}"/>' for w in widths)
    borders = ('<w:tblBorders>'
               + "".join(f'<w:{e} w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
                         for e in ["top", "left", "bottom", "right", "insideH", "insideV"])
               + "</w:tblBorders>")
    xml = [f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>{borders}</w:tblPr>'
           f"<w:tblGrid>{grid}</w:tblGrid>"]
    for ri, row in enumerate(rows):
        xml.append("<w:tr>")
        if ri == 0:
            xml.append('<w:trPr><w:tblHeader/></w:trPr>')
        for ci, cell_text in enumerate(row):
            w = int(9000 * widths[ci] / total)
            color = "C00000" if (ri > 0 and ci in red_cols) else None
            body = ""
            for j, line in enumerate(str(cell_text).split("\n")):
                if j:
                    body += "<w:p/>"
                body += para(line, bold=(ri == 0 and header_bold), color=color, indent=False, sz=21)
            xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>{body}</w:tc>')
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


def build_body():
    B = []
    B.append(para("南京师范大学硕士学位论文评阅意见修改说明", bold=True, align="center", sz=36, font="黑体", indent=False))
    B.append(para("", indent=False))

    # 封面信息表
    B.append(table([
        ["姓名", "蔡振辛", "学号", "242302035"],
        ["入学时间", "2024 年 9 月", "学科名称", "心理学（基础心理学）"],
        ["所在学院", "心理学院", "指导教师", "胡传鹏 教授"],
        ["学位论文题目", "自我优势效应的实验设计空间优化：基于漂移扩散模型与高斯过程的混合建模研究", "", ""],
    ], [1.6, 2.4, 1.6, 3.0]))

    B.append(para(""))
    B.append(para("说明：本文件为修改说明的准备工作稿。表中“示例意见”系根据本文薄弱环节预判的问题，"
                  "请在收到评阅意见后替换为评阅专家原文；“修改说明”与“详细修改说明”部分为本文已完成的修订工作，可直接沿用。",
                  color="C00000", indent=False, sz=21))
    B.append(para(""))

    # 一、意见与修改说明对照表
    B.append(heading("论文评阅专家意见汇总与修改说明", 1))
    rows = [["序号", "评阅专家意见（示例，待替换）", "修改说明", "修改位置"]]

    rows.append(["1",
                 "论文构建了“实验设计参数 (P,T,W) → DDM 参数 (v,a,t,z) → 行为”的映射框架，但**参数估计本身是否可靠缺少检验**：未报告 MCMC 收敛诊断（R-hat/ESS），也未做参数恢复（parameter recovery）。",
                 "已补齐三个层次。① 收敛诊断：对全部拟合计算 R̂ 与 ESS，发现历史主拟合（单链 3,000 draws、500 burn-in、p_outlier = 0.05）中 G3 的起始点参数 ESS 仅 8.6、G8 的 ESS 为 22；② 据此按“p_outlier = 0 + 4 条链 × 8,000 draws / 2,000 burn-in”重跑主口径 6 个条件，全部核心参数达标（R̂ ≤ 1.000、ESS ≥ 9,439），并报告三方配置对照（p_outlier 0.05/0、单链与多链），确认此前极端参数主要源于 p_outlier 与 Censor 编码冲突；③ 参数恢复：以修正配置参数为真值的仿真恢复显示，绝对漂移率不可恢复（Censor 偏低约 0.75、Drop 偏高且噪声大，95% CI 覆盖率 ≤ 25%），但自我优势的相对效应 SPE_v 几乎完美恢复（覆盖率 100%、r ≈ .95）；遗漏率–偏倚曲线进一步显示绝对偏倚随遗漏率单调增大（5% 时 −0.07 → 70% 时 −4.00），而 SPE_v 偏倚在所有水平下 |≤0.26|。",
                 "6.2.2、6.3.3、6.3.4\n图6-3~6-5、6-6、6-7\n表6-2、6-3、6-4、6-5"])

    rows.append(["2",
                 "模型的行为层面验证只报告了拟合优度与相关（r 很高等），**缺少严格的后验预测检验（PPC）**，难以判断模型是否真的复现了行为。",
                 "已实施严格 PPC：从各条件 HDDM 迹线中联合抽样被试水平参数 200 次，按真实被试数、每身份 130 试次与真实 deadline 重新仿真，并用与真实数据完全相同的方式计算统计量（acc_all、acc_responded、遗漏率、正确 RT 均值与分位数、SPE_RT、SPE_ACC），报告 95% 预测区间覆盖率与尾概率，并补充 QP 图。结果显示五个统计量的覆盖率仅为 .00–.39，**行为分布层面存在系统性失配**（如长时限条件遗漏率观测 .056、预测 .008）。本文已将模型定位为“设计空间趋势模型”，并据此把跨试次变异、注意脱失（lapse）与塌缩边界（ANGLE/WEIBULL）列为改进方向。",
                 "7.2.4、7.3.5\n图7-4~7-6\n表7-4"])

    rows.append(["3",
                 "留一条件交叉验证（LOCV）结果不理想（部分参数相关系数为负），**模型泛化能力存疑**，作者却仍主张可用于实验设计优化。",
                 "已在正文明确区分两类结论并下调主张。① 条件内精度：修正参数配置后 LOCV 部分改善（v_stranger r = +.80、a r = +.77），但 v_self 与 SPE_v 仍不成立（r = −.10、−.36），说明**限制来自设计点数量（6 个）而非估计方法**；② 据此将模型定位为“设计空间趋势模型”，候选设计点推荐明确标注为**探索性**输出（top-20 的不确定性在第 3–4 位小数才分序），并给出下一轮实验的设计建议（补充 P 的中间水平等）。",
                 "7.2.4、7.3.2、7.3.6、9.4\n图7-2、7-7\n表7-4"])

    rows.append(["4",
                 "论文只有单一模型族，**缺少竞争模型的正式比较与模型恢复（混淆矩阵）**，“混合模型更优”的主张缺乏依据。",
                 "已补充四模型比较与模型恢复。模型比较（同一预测任务、留一条件交叉验证）：纯 Sigmoid 聚合 RMSE = 1.135 ＜ Sigmoid+GP = 1.232 ＜ 均值基线 = 1.269 ≪ 线性 = 8.535；模型恢复（每模型 40 次合成重复）：线性与 Sigmoid+GP 的对角率均为 0，Sigmoid 为 .675。结论修订为：**非线性理论映射不可或缺**，但在 6 个设计点下 GP 残差层未提升跨设计点预测，其价值在于不确定性量化与候选点识别；“混合模型更优”的表述已删除。",
                 "7.2.4、7.3.3、7.3.4\n图7-3\n表7-5、7-6"])

    rows.append(["5",
                 "“Censor（右截尾）”的表述不准确，且对遗漏试次的处理只给了定性结论，**缺少偏倚边界的量化证据**。",
                 "① 术语已更正为“将遗漏试次编码为截止时刻的错误反应参与拟合”，并说明其并非严格的右截尾似然，严格截尾建模列为未来方向；② 补充遗漏率–偏倚曲线（8 个目标遗漏率 × 2 种方案 × 2 次重复）与参数恢复，得出可量化的表述：**遗漏率 < 约 10% 时绝对参数偏倚可忽略，10%–35% 需谨慎，> 约 35% 后绝对水平不可解释；而自我优势的相对方向在各种遗漏率下均保持稳定**（SPE_v 偏倚 |≤0.26|，覆盖率 100%）。",
                 "6.2.1、6.3.1、6.3.3\n图6-1、6-3、6-4\n表6-2、6-3"])

    rows.append(["6",
                 "外部验证部分称“44 篇文献 / 70 个数据集 / 3,603 名被试”，但**未说明实际用于分析的数据规模**，且该数据库为在研项目，样本口径不清。",
                 "已改为按数据库本体（主索引 + 清洗后试次级数据）报告实际规模：主索引 108 行 / 50 个研究 / 合计有效被试 4,841 人；本文**实际可分析子集为 25 个数据集（18 个研究）/ 2,488 名被试 / 337,050 个试次**；跨研究 SPE_RT 合并均值为 −93.8 ms（数据集 bootstrap 95% CI −113.6 ~ −74.5），全部 25 个数据集方向一致；并与数据库自身的身份层分析对照（Self vs Stranger：k = 46、2,483 人、d_z ≈ 1.01）。敏感性分析显示在身份口径、RT 窗口、被试门槛变化下结果均为 −86 ~ −95 ms。同时说明：数据库对实验设计参数（尤其 T、W）的元数据不完整，故调节效应分析仅为探索性。",
                 "8.1~8.3、9.4\n图8-4\n表8-1~8-3"])

    rows.append(["7",
                 "论文所用 88 人行为数据由课题组前期采集，**作者独立贡献不明确**。",
                 "已在第 4 章加入数据来源与作者贡献声明：数据由课题组前期研究采集（MATLAB + Psychtoolbox），作者独立完成全部数据整理与质量审计、计算建模（HDDM 拟合与收敛诊断、遗漏敏感性分析、参数恢复、Sigmoid+GP 建模、模型比较与模型恢复、后验预测检验）、统计分析与外部数据库整合验证，并开发了可复现的工具链；数据使用已获课题组与导师许可。同时说明与课题组既往学位论文（温佳慧, 2025）使用部分相同数据但研究问题与分析路径均有实质区别。",
                 "4.2、9.2、9.3\n附录B"])

    rows.append(["8",
                 "文中“首次将 LAN+OPN 应用于 SMT 范式”“填补空白”等表述过强；引用了尚未正式发表的文献。",
                 "已删除“首次”“填补空白”类表述，改为“据我们所知，本文是首次在 SMT 范式中系统比较遗漏处理方案并报告参数恢复的工作”等可核查的表述；LAN+OPN 部分明确定位为方法路线与概念验证（自研 OPN 测试集 R² = .986），并将官方 ddm_opn 与 HSSM 的端到端联合似然估计列为未来方向；参考文献已更新为正式发表版本（Leng et al., 2026, PLoS Computational Biology, 22(8), e1014667），in-prep 文献按规范标注并在附录说明使用许可。",
                 "1.4、6.4、7.4、参考文献"])

    rows.append(["9",
                 "图表编号不统一、存在占位内容，缺少数据与代码的可复现性说明。",
                 "已统一图表编号（图 = 章-序号，与正文出现顺序严格一致；共 21 图、14 表），清除占位标记；新增“数字锁定表”登记每个统计量的数值、来源脚本、产物文件与运行日期（并同时登记三种参数配置 A/B/C 的数值）；附录 B 列出全部脚本、随机种子、Docker 镜像与运行环境。",
                 "附录A、附录B\n全文图表"])

    rows.append(["10",
                 "CRF 与机制部分仅有定性对照，缺少模拟与实测的定量比较；参数逆向推断缺少数值结果。",
                 "已将仿真与实测 CRF 定量叠加：实测自我优势在 RT ≈ 480 ms 处最大（+0.14，经被试级 cluster bootstrap 检验），与课题组早先的滑动窗口分析（峰值约 434–459 ms）一致；仿真显示起点偏向可解释该优势的一部分，但不足以完全复现其时间进程。参数逆向推断因存在 v–z、a–v 的补偿效应，已明确定位为“可辨识性可行性分析”，不报告参数恢复精度。",
                 "8.2、8.3、8.4\n图8-1、8-3"])

    rows.append(["11",
                 "缺少多重比较校正与探索性/确证性分析的声明。",
                 "已在各研究的方法与结果中明确区分确证性检验（研究一的行为层与参数层主要检验）与探索性分析（稳健子集、候选设计点、数据库调节效应），并报告贝叶斯因子与功效分析（G*Power 可检测最小效应）以说明证据强度；对探索性分析不作强结论。",
                 "5.2.3、5.4、7.3.6、8.4"])

    rows.append(["12",
                 "参考文献格式不统一、部分条目信息不全。",
                 "已按 APA 第 7 版统一格式，补齐卷期页码与 DOI；补充中文文献；对数据库与工具类引用（HDDM、HSSM、DDM 参数范围综述等）统一为软件/论文的规范格式。",
                 "参考文献"])

    B.append(table(rows, [0.7, 3.4, 6.4, 2.2], red_cols=(1,)))
    B.append(para(""))

    # 二、详细修改说明
    B.append(heading("详细修改说明", 1))

    B.append(heading("（一）参数估计的收敛性与可靠性：从“报告结果”到“验证结果”", 2))
    B.append(para("针对意见 1。本文的全部结论均建立在 DDM 参数估计之上，因此先验证估计本身是否可靠。"))
    B.append(para("1. 收敛诊断。对 24 次历史拟合计算 Split-R̂ 与 ESS（单链可用口径），发现历史主拟合平均仅约 70% 的核心参数达标，其中 G3 的起始点参数 ESS = 8.6（R̂ = 1.324）、G8 的 ESS = 22；敏感性分析中的 Censor 拟合 100% 达标。"))
    B.append(para("2. 参数重跑。按 HDDM 原生多链抽样（4 条链 × 8,000 draws / 2,000 burn-in，parallel），并在 p_outlier 上采用与 Censor 编码一致的 0（项目自身的遗漏敏感性分析已给出该建议）。重跑后 6 个条件核心参数全部达标（R̂ 最大 1.000、ESS 最小 9,439）。"))
    B.append(para("3. 配置对照。比较三种配置（A：p_outlier = 0.05、单链；B：p_outlier = 0、单链；C：p_outlier = 0、4 链）表明：p_outlier 的配置差异比抽样长度更关键——由 A 改为 B 时 v_self 的 95% CI 宽度中位数由 2.45 降至 1.16，G3（−1.89）、G8（+2.82）的极端取值明显回缩。本文以配置 C 作为最终口径，并在附录 A 中同时登记 A、B、C 三套数值。"))
    B.append(para("4. 结果修订。改用配置 C 后，研究一的参数层组间差异由显著变为不显著（F(5,59) = 2.95, p = .019 → F(5,59) = 1.72, p = .145, BF₁₀ = 1.03），研究三的 Sigmoid 校准参数亦实质变化（α₁：0.862 → 0.153，β₁：+0.328 → −0.631，拟合 RMSE：1.090 → 0.704）。本文已如实修订摘要、相关章节与结论：**行为层面的设计空间效应稳健，参数层面的组间差异不稳健；β₁ 的符号反转在收敛良好的估计下再次出现，应视为对该理论假设的真实偏离**。", ))

    B.append(heading("（二）模型验证链：参数恢复 → 模型比较/恢复 → 后验预测检验", 2))
    B.append(para("针对意见 2–4。本文按计算建模的十条规则（Wilson & Collins, 2019）补齐验证链："))
    B.append(para("1. 参数恢复（研究二）：以修正配置参数为真值生成合成数据并重新拟合，报告偏倚、RMSE 与 95% CI 覆盖率。结果显示绝对漂移率不可恢复，而自我优势的相对效应（SPE_v）几乎完全可恢复，为全文以相对效应为核心的结论提供了依据。"))
    B.append(para("2. 模型比较与模型恢复（研究三）：四模型在同一预测任务上比较，并对每个模型做 40 次合成重复以构建混淆矩阵。结果为“非线性映射必需、GP 层增量价值无法证实、设计对模型判别的功效不足”，据此删除了“混合模型更优”的表述。"))
    B.append(para("3. 后验预测检验（研究三）：以被试水平后验仿真并计算分层统计量与 95% 预测区间覆盖率，配合 QP 图。结果显示行为分布层面存在系统失配，本文据此把模型定位为“设计空间趋势模型”，并把模型形式扩展列为首要后续工作。"))

    B.append(heading("（三）外部验证与数据口径", 2))
    B.append(para("针对意见 5–7。本文的外部验证改用课题组 SPE 数据库本体（主索引 Dataset_inf.csv + 清洗后试次级数据），报告实际可分析子集规模（25 个数据集 / 2,488 名被试 / 337,050 试次）与跨研究效应（−93.8 ms，25/25 方向一致），并与数据库自身的身份层分析（d_z ≈ 1.01）相互印证；同时说明数据库元数据对 T、W 的记录不完整，调节效应仅为探索性。数据来源与作者贡献已在第 4 章声明，并说明数据为课题组前期采集、使用已获许可。"))

    B.append(heading("（四）表述、图表与可复现性规范", 2))
    B.append(para("针对意见 8–12。已删除“首次”“填补空白”等过强表述；更新参考文献为正式发表版本；统一图表编号并清除占位；新增数字锁定表与脚本/环境说明（附录 A、B）；明确区分数值的确证性与探索性分析，并报告贝叶斯因子与功效分析以说明证据强度。"))

    B.append(heading("（五）尚在推进的工作", 2))
    B.append(para("1. 样本扩充：正在按条件补充被试（目标每条件 ≥ 20 人）。扩充后将重新拟合、更新数字锁定表，并运行“留出被试验证”（以估计集拟合、预测未参与估计的被试），把目前的 in-sample 与 LOCV 验证升级为真正意义上的样本外验证。"))
    B.append(para("2. 模型形式扩展：拟引入跨试次变异（sv、st0、sz）、注意脱失（lapse）与塌缩边界模型（ANGLE/WEIBULL），并使用官方 ddm_opn 与 HSSM 完成遗漏的显式似然建模（LAN+OPN 路线）。"))
    B.append(para("3. 上述工作完成后，将同步更新正文中的相关数值与图表，并在修订说明中补充说明。"))

    B.append(para(""))
    B.append(para("作者签名：　　　　　　　　　　　　指导教师签名：", indent=False))
    B.append(para("日期：　　年　　月　　日　　　　　日期：　　年　　月　　日", indent=False))
    return "".join(B)


def main():
    assert TEMPLATE.exists(), f"模板不存在：{TEMPLATE}"
    body = build_body()
    with zipfile.ZipFile(TEMPLATE) as zin:
        doc = zin.read("word/document.xml").decode("utf-8")
        body_i = doc.find("<w:body>")
        head = doc[: body_i + len("<w:body>")]
        tail_i = doc.rfind("</w:body>")
        sect_i = doc.rfind("<w:sectPr", body_i, tail_i)
        tail = doc[tail_i + len("</w:body>"):]
        sectpr = doc[sect_i: tail_i] if sect_i > 0 else ""
        new_doc = head + body + sectpr + "</w:body>" + tail
        import xml.etree.ElementTree as ET
        ET.fromstring(new_doc.encode("utf-8"))
        if OUT.exists():
            try:
                OUT.unlink()
            except PermissionError:
                pass
        out_path = OUT if not OUT.exists() else OUT.with_name(OUT.stem + "_新" + OUT.suffix)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = new_doc.encode("utf-8") if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)
    print("OK ->", out_path, f"({out_path.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
