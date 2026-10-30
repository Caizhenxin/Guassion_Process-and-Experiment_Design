# 摘要

自我优势效应（self-advantage effect, SPE）指个体对与自我关联的刺激反应更快、更准。文献报告的 SPE 从 0 ms 到 250 ms 不等，同一范式内相差 4 倍以上。本文的出发点是：这一分歧的主要来源不是被试群体差异，而是**测量口径不统一**——SPE 的可观测值与参数归因，由设计、似然、模型与基准四层口径共同决定，任何一层没有锁住，数字就不可比。

本文以自我—他人匹配任务（self-matching task, SMT）为范式，围绕四层口径展开五项研究。研究一用 87 名被试的 8 组设计证明 deadline（反应窗 W）是快慢试次的截断阀：W 由 300 ms 增至 1500 ms 时，被试级 ΔRT 由 −3.3 ms 单调升至 +62.6 ms，超时率由 85.8% 降至 12.9%，即短 W 下的「无 SPE」实为慢试次被遗漏吃掉后的人为压缩。研究二比较 Censor 与 Drop 两种遗漏处理，证明遗漏率超过 15% 后漂移率估计出现系统性偏倚，并以参数恢复与覆盖率给出定量界限。研究三检验 Sigmoid 参数化与高斯过程（GP）残差层，留一条件交叉验证显示纯 Sigmoid（1.135）优于 Sigmoid+GP（1.232），且 GP 层的模型恢复对角率为 0/40，说明六个设计点不足以支撑该复杂度。研究四采用含截止时间的两阶段掩蔽扩散模型与层级贝叶斯估计，在 17 名被试上给出可识别性诊断：掩蔽期漂移衰减参数 ρ 的超参 Hessian 在四组中四组非正定，不可估；约束 ρ=1 后四组全部正定，逐试次 ELPD 稳定，但后验预测检验显示 RT 分布过散（预测—观测分位差 p10 −99 ms、p90 +185 ms），正确率被系统性高估约 4–5 个百分点，故绝对拟合仅可用于参数排序。研究五把本项目放回跨研究基准：96 个数据集按统一口径重算后，陌生人对比的 ΔRT 中位为 75.9 ms（95.8% 为正）、ΔACC 中位 0.072，本项目的 +33 ms 与 +0.067 分别位于第 18.3 与第 46.5 百分位；且文献库中 Close（42.8 ms）反而小于 Stranger（75.9 ms），不支持身份梯度随亲密度单调上升。

本文的核心理论发现是 SPE 的**匹配专属性**：17 名被试中，自我优势只出现在自我被掩蔽且判断为匹配的试次（ΔRT +59 ms、ΔACC +14.4 个百分点），在非匹配试次上消失（ΔRT +16 ms、ΔACC −0.9 个百分点），交互项分别为 t=4.40 与 t=5.90。信号检测分解显示辨别力 d′ 提高 0.50、判据 c 降低 0.29 同时存在，提示 SPE 是「证据累积加速」与「匹配判据放松」的双成分现象，而非单一反应偏向。模型层面，四组拟合的判据通道参数 dz_S 全部为正（+0.007 至 +0.056），而漂移通道参数 beta_S 组间符号相反，与双成分解释一致。

本文的贡献有三：一是给出可复现的设计处方（W ≥ 800 ms 才可观测量级相当的 SPE）与遗漏处理的似然方案；二是提出并演示「可识别性先行」的建模纪律——ρ、GP 层与形状族在当前设计下均不可裁定，复杂度必须由可识别性约束而非拟合优度决定；三是把 SPE 从单点数字改写为「带口径的分布」，使跨研究比较成为可能。全部分析脚本、拟合产物与图表均可复现。

**关键词**：自我优势效应；漂移扩散模型；层级贝叶斯；截止时间与遗漏；可识别性；匹配专属性；跨研究基准

# Abstract

The self-advantage effect (SPE) refers to faster and more accurate responses to self-associated stimuli. Reported SPE magnitudes range from 0 ms to 250 ms, a fourfold spread even within the same paradigm. This thesis argues that the main source of this divergence is not sampling but **measurement convention**: the observable size and the parametric attribution of SPE are jointly determined by four layers — design, likelihood, model, and benchmark — and any unlocked layer renders the number incomparable.

Using a self-matching task (SMT), five studies address these layers. Study 1 (N = 87, eight designs) shows that the response window W is a truncation valve: as W increases from 300 ms to 1500 ms, subject-level ΔRT rises monotonically from −3.3 ms to +62.6 ms while omission falls from 85.8% to 12.9%; the "null SPE" at short W is an artefact of slow trials being censored. Study 2 compares Censor and Drop treatments and shows that beyond 15% omission the drift rate is systematically biased, with recovery and coverage bounds quantified. Study 3 tests a Sigmoid parameterisation with a Gaussian-process residual layer; leave-one-condition-out cross-validation favours plain Sigmoid (1.135) over Sigmoid+GP (1.232), and the GP layer recovers its own generating model in 0/40 cases, indicating that six design points cannot support that complexity. Study 4 fits a two-stage masked diffusion model with an exact deadline likelihood and hierarchical Bayes estimation to 17 participants. Identifiability diagnostics show that the masking-phase drift-decay parameter ρ has a non-positive-definite hyper-parameter Hessian in all four groups and is therefore inestimable; with ρ = 1 all four groups are positive definite and trial-level ELPD is stable, but posterior predictive checks reveal over-dispersion of the RT distribution (predicted-minus-observed quantile gaps of −99 ms at p10 and +185 ms at p90) and a 4–5 percentage-point over-estimate of accuracy, so absolute fit licenses only parameter ranking. Study 5 relocates the project within a cross-study benchmark: recomputing 96 datasets under one convention yields a median stranger-contrast ΔRT of 75.9 ms (95.8% positive) and a median ΔACC of 0.072; the present +33 ms and +0.067 fall at the 18.3rd and 46.5th percentiles. Notably, Close identities (42.8 ms) show smaller effects than Strangers (75.9 ms), contrary to a monotonic intimacy gradient.

The central theoretical finding is the **match-specificity of SPE**: across 17 participants the self-advantage appears only when the self is masked and the judgement is a match (ΔRT +59 ms, ΔACC +14.4 points) and vanishes for non-matches (ΔRT +16 ms, ΔACC −0.9 points; interactions t = 4.40 and 5.90). Signal-detection decomposition shows simultaneous increases in sensitivity (Δd′ = +0.50) and a more liberal criterion (Δc = −0.29), indicating that SPE is a two-component phenomenon — accelerated evidence accumulation plus relaxed match criterion — rather than a pure response bias. Consistently, the fitted criterion-channel parameter dz_S is positive in all four groups (+0.007 to +0.056) while the drift-channel parameter beta_S changes sign across groups.

The thesis contributes (i) a reproducible design prescription (W ≥ 800 ms) and an exact likelihood treatment of omissions; (ii) an "identifiability-first" modelling discipline, showing that ρ, the GP layer, and even the shape family (exponential / linear / sigmoid / power; behavioural family differences < 2 SE) cannot be adjudicated by the present design, so complexity must be constrained by identifiability rather than goodness of fit; and (iii) a reframing of SPE from a single number into a distribution with explicit conventions, making cross-study comparison possible.

**Keywords**: self-advantage effect; drift-diffusion model; hierarchical Bayes; deadline and omission; identifiability; match-specificity; cross-study benchmark

# 第1章 引言

## 1.1 研究背景与动机

自我优势效应是自我加工研究中最稳定的行为现象之一：与自我关联的刺激（自己的名字、面孔、所属物品）在知觉、注意与记忆中均获得优先加工。为把这一现象放到决策层面考察，研究者发展了自我—他人匹配任务（SMT）：先让被试学习若干几何图形与「我 / 陌生人」的联结，随后在每次试验中呈现一个图形，要求判断它与屏幕上的标签是否匹配。自我条件的反应时更短、正确率更高，二者的差值即 SPE。

问题在于 SPE 的量级极不统一。本文对 96 个公开数据集按统一口径重算后，陌生人对比的 ΔRT 中位为 75.9 ms，但 5–95% 区间覆盖 0.4–192.1 ms，最小值为 −109.5 ms，最大值为 241.0 ms。同一现象在「谁更快的方向一致」上高度可靠（95.8% 为正），在「快多少」上却相差两个数量级。

这种分歧通常被归因于样本、文化与任务差异。本文认为还有一个更基本、也更可控的原因：**SPE 是在一个带截止时间的证据累积过程中被测量出来的，而测量口径没有被标准化**。具体而言有四层：

1. **设计层**：反应窗 W 决定了哪些试次能被观测到。W 短则慢试次变成遗漏，而遗漏通常直接被剔除，等于把分布右尾剪掉；自我与他人的右尾厚度不同，剪掉的量也不同。
2. **似然层**：遗漏如何进入似然函数。剔除（Drop）、删失（Censor）与「带 deadline 的精确似然」对漂移率的推断不同，遗漏率越高差异越大。
3. **模型层**：观测到的 RT/正确率差距如何归因到参数。归因依赖参数可识别性，而可识别性又依赖设计的分辨率。
4. **基准层**：同一个「SPE」在不同身份层级（亲密他人 / 陌生人 / 名人）、不同试次组成（匹配与非匹配的比例）下不是同一个量。

四层中任何一层没有锁住，报出的数字就无法与他人的数字比较。本文的动机即在于把这四层逐层锁住，给出一个「带口径的 SPE」。

## 1.2 研究思路与目标

本文不试图给出一个新的、更大的 SPE 点估计，而是回答三个问题：

- **可观测性**：在什么设计条件下 SPE 才能被观测到，观测到的量级如何随设计变化？
- **可归因性**：在给定设计下，哪些决策参数可以被数据识别，SPE 应当归因到哪一个（或哪几个）参数？
- **可比性**：本项目的读数在跨研究分布中处于什么位置，差异来自哪里？

对应的总体思路是「先锁口径、再谈量级」：研究一确定设计边界，研究二确定遗漏的似然处理，研究三确定模型复杂度上限，研究四在锁好的口径下做层级拟合与可识别性诊断，研究五做跨研究基准定位。

## 1.3 研究问题

本文提出四个可检验的问题：

- **Q1（设计）**：SPE 的量级是否随反应窗 W 单调变化？若是，短 W 下的「无效应」是否可由遗漏截断解释？
- **Q2（似然）**：遗漏处理方式在多大遗漏率下开始扭曲漂移率估计？是否存在一个可接受的遗漏率上限？
- **Q3（模型）**：掩蔽期的漂移衰减 ρ、GP 残差层、以及漂移随 P/T 的函数形式（指数 / 线性 / Sigmoid / 幂函数），在当前设计下能否被数据区分？
- **Q4（机制）**：SPE 是单一的反应偏向，还是「证据累积加速」与「判据放松」的双成分？若为双成分，它应当在哪一类试次上更强？

## 1.4 研究意义与独立性说明

理论上，本文把 SPE 从「一个数字」改写为「一个受口径约束的分布」，并给出双成分解释，这为文献中量级分歧提供了一个可检验的说明。方法上，本文演示了一条「可识别性先行」的建模纪律：先用设计分辨率筛掉不可裁定的复杂度，再做参数解释。实践上，本文给出可直接套用的设计处方（W 的下限）与遗漏处理方案。

关于独立性：研究一至研究三使用 2026 年 9 月前采集的 87 名被试数据（8 组设计），研究四至研究五使用 2026 年 10 月按新设计（v4.1）采集的 17 名被试数据。两批数据在设计参数、模型版本与分析口径上均不同，本文在各自章节内分别说明，不做跨批次的直接参数比较；跨批次比较只使用行为层的 ΔRT 与 ΔACC。

## 1.5 论文结构

第 2、3 章为文献综述：第 2 章覆盖 SMT 与 SPE、漂移扩散模型及其层级估计与可辨识性；第 3 章覆盖截止时间与遗漏建模、高斯过程与设计优化、SPE 数据库与 CRF 研究。第 4 章给出研究框架、设计空间、数据沿革与五项研究导览。第 5–9 章为五项研究。第 10 章总讨论，第 11 章结论。

# 第2章 文献综述（一）：自我优势效应与证据积累模型

## 2.1 Self-Matching Task 与自我优势效应

### 2.1.1 SMT 范式与 SPE 的测量

SMT 的核心 manipulation 是「刺激—身份」的习得联结：被试先学习几何图形分别属于自己或某个陌生人，随后在每次试验中判断图形与屏幕标签是否匹配。由于两条件的刺激在物理上完全相同，任何行为差异都不能归因于低层视觉特征，只能归因于身份标签的加工，这是 SMT 相对「自我面孔 / 自我名字」范式的关键优势。

SPE 通常操作化为三个量：ΔRT = RT(他人) − RT(自我)（正值表示自我更快）、ΔACC = ACC(自我) − ACC(他人)、以及被试级的效应量。本文在第五章进一步把 ΔRT 拆成匹配与非匹配两类试次，理由见 §8.3。

### 2.1.2 SPE 的行为特征与影响因素

文献中 SPE 的稳健性体现在方向而非量级：本文重算的 96 个数据集中 95.8% 为正。影响因素包括身份层级（自我 > 亲密他人 > 陌生人 > 名人，但本文的重算结果对这一单调性提出质疑，见 §9.3）、练习（多天训练后效应可能增大也可能减弱）、以及任务参数（刺激时长 T、反应窗 W、掩蔽比例 P）。其中 W 的作用长期被低估：当 W 较短时，慢试次被遗漏，而遗漏通常被剔除，等于对分布做右尾截断。

## 2.2 漂移扩散模型（DDM）

### 2.2.1 基本理论与参数含义

DDM 假设决策是一个带漂移的随机累积过程：证据以速率 v 向两个边界（正确 / 错误）累积，边界间距 a，起点 z，非决策时间 t0。首次越界时间即 RT，越界方向即反应。在带截止时间的任务中还需引入 W：若累积在 W 内未越界，则记为遗漏。

### 2.2.2 参数的层级贝叶斯估计（HDDM）

个体差异通常用层级模型处理：被试级参数服从群体分布，群体分布的超参由所有被试共同约束。本文的实现采用 EM + Laplace 近似（见 §4.3 与 §8.2），并以逐试次 ELPD 与 Pareto-k 诊断做模型比较。

### 2.2.3 参数的经验取值范围与可辨识性

参数可辨识性是本文反复遇到的问题。文献中常见做法是「拟合后看区间是否跨零」，但区间宽度本身依赖设计分辨率：同样的 576 试次，如果把 T 分成 6 档，每格只剩 8 个重复，联合组层的标准误反而变大。本文因此把「可识别性」提升为独立判据（研究三、研究四），而不是事后解释。

# 第3章 文献综述（二）：遗漏反应建模、高斯过程与实验设计优化

## 3.1 含截止时间的决策任务与遗漏反应

带 deadline 的任务中，遗漏有三种处理方式：（1）Drop：整条试次剔除；（2）Censor：视为「到点未决」的右删失观测；（3）精确似然：把「在 W 内未越界」的概率直接写进似然。三者的差别随遗漏率上升而放大：当遗漏率低于 5% 时几乎无差别，超过 15% 后 Drop 与 Censor 都会使漂移率产生系统性偏倚（研究二的定量结果见 §6.3）。

## 3.2 高斯过程与实验设计优化

高斯过程（GP）是一种非参数先验，常用作「参数随设计变量变化」的灵活函数形式。其代价是：GP 层引入的额外自由度需要设计点的支撑，否则只能拟合噪声。本文研究三用留一条件交叉验证直接检验这一点（§7.3.3），结论是六个设计点不足以支撑 GP 层的增量价值。

## 3.3 SPE 数据库与大规模证据整合

跨研究整合的困难在于口径不一致：不同研究报告的是不同身份层级、不同试次组成、不同修剪规则下的 ΔRT。本文研究五的主要工作量即在于把 96 个公开数据集重算到同一口径（统一的修剪规则、统一的最小单元试次数、统一的身份变量），再与本研究对比。

## 3.4 CRF 与机制层面的决策研究

条件反应函数（CRF）方法通过操纵截止时间、观察「匹配键反应比例随 RT 变化」的曲线来推断判据与漂移的相对贡献。本文在研究五中沿用该方法，作为模型层面结论的行为学旁证。

## 3.5 文献小结与研究空白

综述给出的空白是：（1）缺少对 W 截断效应的系统量化；（2）遗漏处理的偏差界限只有定性描述；（3）模型复杂度（GP 层、形状族、掩蔽参数）缺乏基于可识别性的门槛；（4）SPE 的跨研究分布没有被统一口径地估计过；（5）SPE 是否依赖试次类型（匹配 / 非匹配）几乎没有被检验。本文的五项研究分别对应这五点。

# 第4章 研究框架与总体方法

## 4.1 实验设计空间与理论假设

本文把实验操纵写成三维设计空间 Ω = (P, T, W)：P 为自我被掩蔽（掩蔽刺激覆盖自我图形）的试次比例，T 为刺激呈现时长，W 为反应窗（deadline）。三者的组合决定了任务难度、遗漏率与可观测的 RT 范围。

理论假设有两条。**假设一（练习 / 掩蔽 → 漂移）**：P 通过改变「自我标签的可及性」影响漂移率，方向为 P 越大、自我条件的漂移率越低（自我被掩蔽时更难提取自我联结）。**假设二（deadline → 遗漏）**：W 通过截断影响遗漏率，且对自我与他人两条件的影响不对称——若自我条件的 RT 分布整体左移，则短 W 下被截掉的试次更少，ΔRT 被压缩。

八组实验条件及其质量分档见图 4-1 与表 4-1。

[[FIG:图4-1]]

## 4.2 数据集与数据沿革

本文使用两批数据。**第一批（2026-09 前）**：87 名被试，8 组设计（D1 至 D6 及两个补充组），每组约 11 人，每人约 570 试次；该批数据用于研究一至研究三。**第二批（2026-10）**：17 名被试，新设计 v4.1，四组 P（0 / 8 / 32 / 120%），每人 576 试次，用于研究四与研究五。两批数据的模型版本不同，故本文不跨批次比较参数，只比较行为层的 ΔRT 与 ΔACC。

需要说明的是，第二批数据的采集目标为 55 人（按 AIPE 口径的每组 13–16 人），当前完成 17 人，属阶段性样本；本文所有涉及第二批的推断均标注了样本量，并对小样本下的区间宽度做了说明。

## 4.3 建模总体方法

第二批数据使用两阶段掩蔽扩散模型（v4.1）。其核心结构是：在刺激呈现期（时长 T）内漂移率为 v；掩蔽期（T 至 W）内漂移率衰减为 ρ·v（ρ ∈ [0, 1]，ρ = 1 表示无衰减，退化为单阶段）。边界与起点沿用标准 DDM，另加两个身份通道：

- **漂移通道**：d = d_ref + beta_T·(T − T_ref) + is_self·(beta_S + beta_ST·(T − T_ref))
- **判据通道**：z = a·clip(z_ratio + is_self·dz_S, ε, 1 − ε)

其中 is_self 为自我条件指示，dz_S 允许自我条件在起点上偏移，从而在不改变漂移的前提下改变正确率与 RT 的权衡。该设计使「漂移加速」与「判据放松」成为两个可分离的机制假设，这一点在研究四中被证明是必要的（§8.3）。

似然函数采用带 deadline 的精确形式：对已反应试次使用首次越界密度在 [t0, W] 上的积分，对遗漏试次使用「在 W 内未越界」的概率。相比 Drop 与 Censor，这一形式把遗漏当作信息而非缺失。

## 4.4 统计口径与主口径决策

本文预先登记四条口径：（1）RT 分析只用正确且已反应的试次，遗漏单独建模；（2）抢按（RT < t0 下限）试次剔除并在数据质量部分报告；（3）被试级效应用配对检验，组层效应用层级模型；（4）模型比较以留一条件交叉验证为主判据，ΔBIC 与逐试次 ELPD 为辅，逐被试 LRT 不作主判据（因其在 ρ 的检验中会随校正方式翻转结论）。

## 4.5 验证链与可复现性

每条结论都要求至少两级验证：行为层结论需有被试级配对检验与效应量；参数层结论需有参数恢复或可识别性诊断；跨研究结论需有统一口径的重算脚本。全部脚本、拟合产物与图表均在版本库中，附录 B 给出复现命令。

## 4.6 五项研究导览

本文的五项研究构成一条「逐层锁口径」的链条：

| 研究 | 锁住的层 | 核心问题 | 主要结论 | 章节 |
|---|---|---|---|---|
| 研究一 | 设计层 | W 如何决定可观测的 SPE | W 由 300 增至 1500 ms，ΔRT 由 −3.3 升至 +62.6 ms | 第 5 章 |
| 研究二 | 似然层 | 遗漏处理在多大遗漏率下失真 | 遗漏率 > 15% 后漂移率偏倚显著 | 第 6 章 |
| 研究三 | 模型层 | GP 层与函数形式的复杂度上限 | 纯 Sigmoid 优于 Sigmoid+GP；GP 恢复率 0/40 | 第 7 章 |
| 研究四 | 模型层 + 机制 | 新设计下哪些参数可估、SPE 来自哪个通道 | ρ 不可估；dz_S 全正、beta_S 反号；SPE 匹配专属 | 第 8 章 |
| 研究五 | 基准层 | 本项目在跨研究分布中的位置 | ΔRT 位于第 18.3 百分位；Close < Stranger | 第 9 章 |

需要强调的是，五项研究不是并列的五个实验，而是同一个论证的五步：研究一说明「为什么以前的数字不可比」，研究二与研究三说明「为什么模型不能随便加复杂度」，研究四在锁好的口径下给出机制归因，研究五把结果放回文献分布。任何一步缺失，后面的结论都会退化为一个孤立的点估计。
