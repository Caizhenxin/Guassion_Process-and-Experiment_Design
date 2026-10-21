# -*- coding: utf-8 -*-
"""生成《论文预览（可写部分）》docx —— 论文里现在就能落笔的章节。

落点：5_Reference/05_交付件/论文预览_可写部分_v1_20261021.docx
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
OUT = ROOT / "5_Reference/05_交付件/论文预览_可写部分_v1_20261021.docx"
FIG = ROOT / "5_Reference/03_论文写作/figures_sim"

doc = Document()

# ------------------------------------------------------------------ 基础样式
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.8)
sec.top_margin, sec.bottom_margin = Cm(2.6), Cm(2.4)

st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
pf = st.paragraph_format
pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
pf.space_after = Pt(3)


def _font(run, name="宋体", size=12, bold=False, italic=False, color=None):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def h(text, level=1, space_before=12, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.keep_with_next = True
    sizes = {0: 18, 1: 15, 2: 13, 3: 12}
    r = p.add_run(text)
    _font(r, "黑体", sizes.get(level, 12), bold=True)
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def para(text, indent=True, size=12, italic=False, space_after=3, align=None):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    # 支持 **粗体** 片段
    parts = text.split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        _font(r, "宋体", size, bold=(i % 2 == 1), italic=italic)
    return p


def eq(text, size=12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = "Cambria Math"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    r.font.size = Pt(size)
    r.italic = True
    return p


def bullet(text, size=12):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    parts = text.split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        _font(r, "宋体", size, bold=(i % 2 == 1))
    return p


def note(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    _font(r, "楷体", 10.5, italic=False, color=(0x44, 0x4A, 0x55))
    return p


def table(rows, widths=None, size=10.5, header=True):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(str(cell))
            _font(r, "宋体", size, bold=(header and i == 0))
            if header and i == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(path, caption, width=15.5):
    if not path.exists():
        note(f"（缺图：{path.name}）")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(caption)
    _font(r, "宋体", 10, bold=False)


# ================================================================== 封面
for _ in range(3):
    doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("自我匹配任务中的证据积累")
_font(r, "黑体", 24, bold=True)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("——基于两阶段漂移扩散模型的机制研究")
_font(r, "黑体", 15, bold=True)

for _ in range(2):
    doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("论文预览（可写部分）")
_font(r, "宋体", 16, bold=True)

for _ in range(6):
    doc.add_paragraph()
for line in ["版本：v1 ｜ 2026-10-21",
             "对应代码标签：pipeline-v1.13",
             "说明：本文件只包含**不依赖真实数据**即可完成的章节；",
             "　　　所有需要真实数据的位置均标为【待数据】。"]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    parts = line.split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        _font(r, "宋体", 11, bold=(i % 2 == 1))

doc.add_page_break()

# ================================================================== 摘要
h("摘　要", 1, space_before=0)
para("自我相关刺激相对于他人刺激的反应优势（自我优势效应）已被反复观察，但其机制仍不清楚：这一优势究竟来自"
     "证据积累速率的提高、反应阈值的降低，还是非决策时间的缩短？本研究采用两阶段漂移扩散模型（two-phase "
     "drift-diffusion model, M-T1）对自我匹配任务的逐试次选择与反应时进行建模，将刺激呈现期与掩蔽之后的"
     "证据积累分开刻画，并用「掩蔽后证据保留率」ρ 量化掩蔽对证据积累的打断程度。实验采用 4（练习量 "
     "P = 0 / 8 / 32 / 120 次，被试间）× 4（刺激呈现时长 T = 33.3 / 83.3 / 150 / 250 ms）× 3（反应期限 "
     "W = 800 / 1200 / 1800 ms）× 2（自我/他人）× 2（匹配/不匹配）的混合设计，每名被试完成 576 个试次。")
para("基于解析 Cramér–Rao 下界与蒙特卡洛模拟的功效分析表明：在本设计下，漂移幅度 d_ref、边界 a_ref 与"
     "非决策时间 t0 具有很高的估计精度；呈现时长效应 β_T 是唯一需要较大样本的被试内参数（约 37–43 人/组"
     "可将相对标准误压到 10%）；而自我×呈现时长的交互 β_ST（约需 2248 人/组）与练习饱和常数 τ_P 在本设计下"
     "不可估计，故本研究不将其作为推断目标，并在方法中明确说明其不可估的原因。")
note("【待数据】以上为方法学层面的预期，不含任何真实被试的统计结果。摘要中的样本量、区间宽度与效应方向须在"
     "数据齐备后重写。")
p = doc.add_paragraph()
r = p.add_run("关键词：")
_font(r, "黑体", 12, bold=True)
r = p.add_run("自我优势效应；漂移扩散模型；证据积累；掩蔽；练习效应；参数可辨识性")
_font(r, "宋体", 12)

doc.add_page_break()

# ================================================================== 第一章
h("第一章　引言", 1, space_before=0)

h("1.1　研究背景", 2)
para("当刺激与自我相关联时，人们往往反应更快、更准确，这一现象被称为自我优势效应（self-prioritisation "
     "effect）。已有研究主要在反应时与正确率这两个汇总指标上讨论该效应，但这两个指标同时受多个认知成分"
     "影响：刺激编码的速度、证据积累的速率、反应阈值的设置，以及运动执行所需的时间。仅凭汇总指标无法区分"
     "这些成分，因此「自我优势」究竟发生在加工的哪一环节，长期以来缺乏一致的答案。")
para("本研究的基本立场是：**要回答机制问题，必须把汇总指标拆解为过程参数**。为此，我们采用序列采样模型"
     "（sequential sampling model）中的漂移扩散模型，将选择与反应时同时纳入似然，从而把「更快」分解为"
     "「漂移更大」「边界更低」「非决策时间更短」三种可分别检验的可能。")

h("1.2　证据积累框架", 2)
para("漂移扩散模型假设被试在每一个试次中从某个起点出发，以带噪声的方式积累证据，直到触及上边界或下边界"
     "才做出反应；反应时为首次通过时间加上非决策时间。该框架的核心优点是把「速度—准确性权衡」显式参数化："
     "边界越高，反应越慢但越准；漂移越大，反应越快且越准。")
para("在掩蔽范式下，刺激的物理呈现时长（T）与反应期限（W）是两个独立的设计变量，它们对证据积累的作用"
     "完全不同：T 决定「证据能以多大速率进入」，W 决定「积累能用多久」。标准漂移扩散模型只允许一个恒定"
     "漂移，无法区分这两者。为此本研究采用两阶段模型：刺激呈现期内漂移为 d_stim，掩蔽出现后降为 ρ·d_stim。")

h("1.3　练习与时间压力", 2)
para("练习量（P）与反应期限（W）是两个常被忽略但可能系统改变机制的变量。练习可能提高刺激—反应映射的"
     "自动化程度，从而增大漂移；期限则可能改变被试的策略性阈值。若不在模型中显式包含这两条通路，"
     "练习或期限的效应就会被错误地归因到自我优势上。因此本研究把它们作为设计变量纳入映射方程。")

h("1.4　研究问题与假设", 2)
para("本研究提出四个可检验的假设，均以**参数区间**而非「显著与否」表述：")
table([
    ["假设", "内容", "判定标准"],
    ["H1", "自我刺激的漂移更大（β_S > 0）", "β_S 的 95% 区间不含 0；同时报告 a 与 t0 的对比，以排除「只是更急」"],
    ["H2", "练习提高漂移（β_P > 0）", "组间回归的 β_P 区间不含 0，并报告效应量与区间宽度"],
    ["H3", "呈现越久漂移越大（β_T > 0）", "被试内 β_T 的区间不含 0"],
    ["H4", "掩蔽后证据未完全消失（0 < ρ）", "ρ 的区间不含 0，且 ρ ≠ 1（ΔBIC 与 ΔELPD 同向）"],
], widths=[1.6, 6.2, 7.4])
note("写作纪律：样本量不足时明确写出「本研究的区间宽度为 ±X，因此只能排除大于 Y 的效应」，"
     "不以「显著／不显著」作结论（依据项目决策 D104 的证据阶梯）。")

# ================================================================== 第二章
h("第二章　方法", 1)

h("2.1　被试", 2)
para("【待数据】计划招募 4 组被试，每组 10–40 人（最终人数以实际收到为准）。入组标准、排除标准、"
     "知情同意与伦理审批信息见《被试招募与知情同意包》。")
para("样本量的确定依据解析信息量与蒙特卡洛模拟（见 3.6 节）：呈现时长效应 β_T 是本设计的硬约束，"
     "约 37–43 人/组可将相对标准误压到 10%；若实际只能收到 10–15 人/组，β_T 的相对精度约为 17–21%，"
     "β_P 的 95% 区间半宽约为 0.40–0.49（真值 1.5 的 27–33%），本研究将据此把结论限定为「方向 + 区间」。")

h("2.2　刺激与材料", 2)
para("刺激为几何图形（圆形／方形）与身份标签（自我／他人）的组合。每个试次先呈现注视点，随后呈现"
     "身份标签与图形构成的复合刺激，呈现时长 T 由设计决定（33.3 / 83.3 / 150 / 250 ms，对应 2/5/9/15 帧，"
     "60 Hz），随后立即出现掩蔽。被试需判断图形的位置（上／下）并按对应键，反应期限 W 内未反应记为遗漏。")
para("刺激呈现的实际帧数与时长由采集程序逐试次记录（stimulus_frames、stimulus_dur_actual），用于"
     "质量控制：若实际时长与设计值的偏差超过 2 帧，该场次数据作废。")

h("2.3　设计与程序", 2)
table([
    ["因素", "水平", "被试内/间"],
    ["练习量 P", "0 / 8 / 32 / 120 次", "间（4 组）"],
    ["刺激呈现时长 T", "33.3 / 83.3 / 150 / 250 ms", "内"],
    ["反应期限 W", "800 / 1200 / 1800 ms", "内"],
    ["身份", "自我 / 他人", "内"],
    ["匹配性", "匹配 / 不匹配", "内"],
    ["重复", "12 次/单元", "—"],
], widths=[4.2, 7.4, 3.6])
para("每名被试完成 4 × 3 × 2 × 2 × 12 = 576 个试次，分若干区组进行。练习量的操纵通过在被试间分配"
     "不同数量的练习试次实现；练习阶段与正式阶段的试次在结构与反馈上保持一致，仅练习阶段提供正确性反馈。")

h("2.4　数据记录与预处理", 2)
para("每个试次记录：组别、被试编号、试次编号、设计变量（P、T、W、身份、匹配性）、正确键、实际按键、"
     "反应时、是否正确、是否提前按键、是否超时、是否在期限内反应，以及刺激与掩蔽的实际呈现时刻与帧数。")
para("预处理包括：剔除提前按键与设备异常试次；按 2.2 节的帧偏差标准剔除整场数据；对反应时做对数变换后"
     "检查分布形态；对单元缺失率超过 5% 的被试做敏感性分析。")

# ================================================================== 第三章
h("第三章　计算模型", 1)
para("本章给出模型的完整规格。模型由三层构成：任务层（设计变量）、被试层（机制参数）与组层（群体效应）。"
     "任务层的变量通过映射方程进入被试层的机制参数，机制参数再通过扩散过程产生观测。")

h("3.1　证据积累：两阶段漂移", 2)
para("反应由一次带边界的随机游走产生。漂移率在刺激呈现期内为 d_stim，掩蔽出现后（t > T）变为 ρ·d_stim：")
eq("d(t) = d_stim　(0 ≤ t ≤ T)　；　d(t) = ρ · d_stim　(t > T)")
para("其中 ρ ∈ [0, 3] 为掩蔽后证据保留率：ρ = 0 表示掩蔽后完全停止积累，ρ = 1 表示掩蔽不影响积累"
     "（此时模型退化为单阶段模型 M-T3），ρ > 1 表示掩蔽后加速。由于 M-T3 是 M-T1 的严格嵌套特例，"
     "「掩蔽是否打断积累」可以用一个参数的区间与信息准则来检验，而不必在两个模型之间做取舍。")
para("该模型有一个可观测的判别性预测：对于反应时小于 T 的试次，两阶段模型下整个积累过程都发生在"
     "刺激呈现期内，因此其反应时分布与 T 无关；而在单阶段模型中，漂移本身随 T 变化，这些快反应也会随 T 改变。"
     "这正是本研究设置 4 个呈现时长水平的根本理由。")
para("边界间距随期限变化：")
eq("a(W) = a_ref + Δa · [ Q_T(W; τ_a) − Q_T(W_ref; τ_a) ]　，　z = z_ratio · a")
para("起点居中（z_ratio = 0.5），非决策时间为 t0。反应时为首次通过时间加 t0；若首次通过时间超过"
     " W − t0，该试次记为遗漏，其似然由未触及边界的存活概率给出。")

h("3.2　从设计变量到机制参数", 2)
para("漂移幅度由三个部分相加，其中身份项仅在自我条件下加入：")
eq("d_stim = d_ref + β_P [ f_P(P; τ_P) − f_P(P_ref; τ_P) ] + β_T [ Q_T(T; τ_T) − Q_T(T_ref; τ_T) ]")
eq("+ 𝟙_self · ( β_S + β_SP Δf_P + β_ST ΔQ_T )")
para("两个饱和函数为：")
eq("f_P(P; τ_P) = 1 − exp(−P / τ_P)　，　Q_T(X; τ) = 1 − exp(−X / τ)")
para("参考点取 P_ref = 120（最高练习组）、T_ref = 100 ms、W_ref = 1200 ms。生成数据时使用指数形式，"
     "估计时使用线性形式（ΔQ_T = T − T_ref），两者通过设计层的行为最小二乘对齐（最大残差 0.045，"
     "漂移跨度 0.262 对 0.277、边界跨度 0.071 对 0.073）。")

h("3.3　参数与估计", 2)
table([
    ["参数", "含义", "层级", "能否估计"],
    ["d_ref", "参考条件的漂移", "被试", "是"],
    ["β_T", "呈现时长 → 漂移", "被试", "是（主效应）"],
    ["τ_T", "呈现时长饱和常数", "被试", "弱"],
    ["β_S", "自我加性偏移", "被试", "弱"],
    ["β_ST", "自我 × 呈现时长", "被试", "否"],
    ["a_ref", "参考期限的边界", "被试", "是"],
    ["Δa / τ_a", "期限 → 边界", "被试", "否"],
    ["t0", "非决策时间", "被试", "是"],
    ["ρ", "掩蔽后证据保留率", "被试", "是"],
    ["β_P / τ_P / β_SP", "练习效应 / 饱和 / 练习×身份", "组", "β_P 是；τ_P、β_SP 否"],
    ["mu / sigma", "群体均值 / 个体差异 SD", "组", "是（8 人/组为下限）"],
], widths=[3.0, 6.4, 2.0, 4.0])
para("估计采用经验贝叶斯 + 拉普拉斯近似：每名被试有独立的参数向量，群体分布为对角正态；众数搜索用"
     "L-BFGS-B。组层参数 β_P 通过「先估计被试层漂移、再做组间回归」的两步法得到。模型比较使用 PSIS-LOO"
     "（已与 ArviZ 交叉验证，elpd 相对差 3.54×10⁻⁵）与 BIC；拟合优度用后验预测检验（RT 分位数、正确率、遗漏率）。")

h("3.4　可辨识性与样本量", 2)
para("参数的估计精度由解析 Cramér–Rao 下界给出。下表列出「要把参数相对标准误压到 10% 与 25%，每组需要多少人」"
     "（每名被试 576 试次，4T×3W、每单元 12 次重复）：")
table([
    ["参数", "真值", "单被试 SE", "到 10% 需 N", "到 25% 需 N", "判定"],
    ["d_ref", "0.70", "0.103", "3", "1", "可估"],
    ["β_T", "0.55", "0.350", "41", "7", "可估（主效应）"],
    ["τ_T", "0.08", "0.104", "169", "27", "探索性"],
    ["β_S", "0.16", "0.113", "51", "9", "探索性"],
    ["β_ST", "0.10", "0.474", "2248", "360", "不可估"],
    ["a_ref", "2.00", "0.076", "1", "1", "可估"],
    ["Δa", "0.55", "1.410", "658", "106", "不可估"],
    ["τ_a", "0.70", "2.530", "1307", "209", "不可估"],
    ["t0", "0.22", "0.012", "1", "1", "可估"],
], widths=[2.2, 2.0, 2.8, 3.2, 3.2, 3.4], size=10)
para("两条必须在限制中说明的结论：其一，自我与呈现时长的交互 β_ST 在本设计下不可估——不是效应小，而是"
     "信息量相差两个数量级；其二，练习饱和常数 τ_P 不可估，且原因是模型口径而非人数：漂移幅度取非负约束后，"
     "P = 0 与 P = 8 两组的漂移被截断至接近 0，只有 {32, 120} 两个水平与线性组层模型自洽，两点无法确定曲线的"
     "饱和常数。因此本研究不把「练习曲线的形状」作为研究问题。")
figure(FIG / "fig_sim_crlb.png", "图 3-1　参数精度的 Cramér–Rao 下界：每组人数与相对标准误的关系")
para("当每组人数为 10 / 12 / 15 时，β_T 的相对精度约为 21% / 19% / 17%（折算 MLE 实际精度后约 30% / 28% / 25%），"
     "β_P 的相对精度约为 17% / 15% / 14%，其 95% 区间半宽约为 0.49 / 0.44 / 0.40。")
figure(FIG / "fig_sim_p_design.png", "图 3-2　P 水平设计的纯识别力（oracle：用被试层真值做组间回归，不含拟合噪声）")

h("3.5　生成模型与模拟数据", 2)
para("模型可直接生成被试级、试次级的模拟数据，用于功效分析、参数恢复检验与流水线验证。生成物包括每个试次的"
     "漂移、边界、起点、非决策时间，以及由此产生的反应时、选择侧别与是否遗漏；此外还记录刺激帧数与实际时长，"
     "以便与真实数据走同一条质控路径。")
figure(FIG / "fig_sim_trials.png", "图 3-3　模型生成的试次级数据：反应时分位数、反应时分布与正确率/遗漏率随设计变量的变化")

# ================================================================== 第四章
h("第四章　计划分析（结果章骨架）", 1)
para("本章给出拿到真实数据后的分析顺序与报告方式。所有表格的数值均为【待数据】。")
table([
    ["步骤", "内容", "判据／闸门"],
    ["1", "导检与质量控制（帧偏差、时长、提前按键、遗漏）", "帧偏差 > 2 帧的场次作废"],
    ["2", "整表与描述统计", "单元缺失 > 5% 需报告并做敏感性分析"],
    ["3", "层级拟合（拉普拉斯 + EM）", "k_max 与 p_loo/n_obs 在正常范围"],
    ["4", "组间回归（β_P）", "仅使用自洽的 P 水平 {32, 120}"],
    ["5", "模型比较（M-T1 vs M-T3）：ρ、ΔBIC、ΔELPD", "LOO 闸门未过时 ΔELPD 仅作流程验证"],
    ["6", "后验预测检验（RT 分位数、正确率、遗漏率）", "系统性偏差则回查映射方程"],
    ["7", "效应量报告（区间 + 标准化效应量）", "不以「显著／不显著」作结论"],
], widths=[1.6, 8.6, 6.4])

h("4.1　描述统计", 2)
para("【待数据】按组 × 呈现时长 × 期限报告正确率、遗漏率与反应时分位数（0.1 / 0.3 / 0.5 / 0.7 / 0.9），"
     "并给出个体差异的分布形态。")
h("4.2　模型比较", 2)
para("【待数据】报告 M-T1 与 M-T3 的 ρ 估计、ΔBIC 与 ΔELPD；同时报告 ρ 的区间，用于回答「掩蔽是否打断积累」。")
h("4.3　参数估计", 2)
para("【待数据】报告被试层参数的群体均值与个体差异 SD、组层 β_P 的估计与区间，以及 β_S、β_T 的方向与区间。")
h("4.4　稳健性", 2)
para("【待数据】报告剔除极端反应时、剔除单元缺失较多的被试、改变先验/初值后的估计变化，以及仅使用"
     "自洽 P 水平与使用全部水平的差异。")

# ================================================================== 第五章
h("第五章　讨论（框架）", 1)
h("5.1　预期解释", 2)
para("若 H1–H4 成立，本研究将把自我优势定位在证据积累环节，并给出其与练习、呈现时长的交互结构。"
     "与仅报告反应时差异的研究相比，参数层面的证据能说明「快」是由漂移、边界还是非决策时间贡献的，"
     "从而使「自我优先」从描述性结论变为机制性结论。")
h("5.2　限制", 2)
para("（1）**不可估的参数**：β_ST、Δa、τ_a 在本设计下不可估，练习饱和常数 τ_P 因漂移幅度的非负约束而"
     "不可估；相关结论只能表述为「本设计无法回答」，不得以「效应不存在」表述。")
para("（2）**两步法的代价**：组层参数由被试层估计再做回归得到，未与被试层联合估计，因此区间偏窄。"
     "这一点在报告 β_P 的区间时需明示。")
para("（3）**解析下界偏乐观**：Cramér–Rao 下界是「最好的可能」，实际 MLE 的精度更差，经验折算约为 1.5–2 倍。")
para("（4）**模拟数据的定位**：本研究所有模拟结果只用于方法学的功效论证，不作为实证证据。")

# ================================================================== 附录
doc.add_page_break()
h("附录 A　待填清单（真实数据到位后逐项替换）", 1)
table([
    ["占位符", "含义", "来源"],
    ["【样本量】", "各组实际人数", "数据锁库台账"],
    ["【ρ】", "掩蔽后保留率估计与区间", "stage8_run.py"],
    ["【ΔBIC / ΔELPD】", "M-T1 与 M-T3 的比较", "twophase / loo"],
    ["【β_P】", "练习效应与区间", "recover_group.fit_between"],
    ["【β_T】", "呈现时长效应（组均值）与区间", "层级拟合"],
    ["【sigma】", "个体差异 SD", "层级拟合"],
    ["【健康指标】", "k_max、p_loo/n_obs、收敛诊断", "stage8_health.py"],
], widths=[3.6, 7.6, 5.4])

h("附录 B　本文件的依据与复现", 1)
para("本文件的全部方法与数字来自以下产物：")
bullet("模型章模板：5_Reference/03_论文写作/论文_模型章_模板.md")
bullet("结果章模板与自动填表：论文_结果章_模板.md + 1_Code/Experiment/manuscript.py")
bullet("三张图：5_Reference/03_论文写作/figures_sim/（由 make_sim_figures.py 生成）")
bullet("模拟数据 notebook：1_Code/Python_for_Generate/S3_两阶段DDM_模拟数据生成.ipynb")
bullet("设计空间与样本量：Stage9_设计空间优化与论文整合方案.md §13、Stage4_识别性结论与设计处方.md")
note("复现命令：python -X utf8 1_Code/Experiment/make_sim_figures.py；"
     "python -X utf8 1_Code/DDM_Core/_scratch/_run_s3_notebook_cells.py")

# 页脚
footer = doc.sections[0].footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run("论文预览（可写部分）v1 ｜ 2026-10-21 ｜ 需真实数据处均标【待数据】")
_font(r, "宋体", 9, color=(0x66, 0x6C, 0x77))

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("saved", OUT, OUT.stat().st_size, "bytes")
