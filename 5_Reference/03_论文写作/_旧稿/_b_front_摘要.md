# META
TITLE_CN=自我优势效应的实验设计空间优化：基于Ω的 DDM 参数预测与验证
TITLE_EN=Optimization of the Experimental Design Space of the Self-Prioritization Effect: DDM Parameter Prediction and Validation Based on Ω
AUTHOR=蔡振辛
STUDENT_ID=242302035
ADVISOR=胡传鹏 教授
UNIT=心理学院
DISCIPLINE1=心理学
DISCIPLINE2=基础心理学
FINISH_TIME=2027年（待定）
DEFENSE_TIME=2027年（待定）
DEGREE_YEAR=2026

# 摘要

实验设计参数的选取深刻影响心理现象能否被稳定、可靠地观察到，但传统研究往往仅在少数离散条件上比较效应大小，缺乏对"实验参数—潜在心理过程—行为表现"这一映射链条的系统建模。本研究以自我匹配任务（Self-Matching Task, SMT）中的自我优势效应（Self-Prioritization Effect, SPE）为载体，将练习试次数量（P）、刺激呈现时间（T）与反应窗口（W）形式化为三维实验设计空间 Ω，并以漂移扩散模型（DDM）参数（漂移率 v、边界分离 a、非决策时间 t、起始点 z）作为连接实验设计与行为数据的中介变量，构建"Sigmoid 理论先验 + 高斯过程（GP）残差"的混合生成模型，实现从实验设计参数到心理过程再到行为表现（反应时 RT、正确率 ACC、遗漏率）的定量预测，并通过真实数据、敏感性分析、外部数据库与机制仿真进行多源验证。

研究一在课题组前期采集的 88 名被试、8 组实验设计数据上，系统检验了设计空间对 SPE 行为表现与 DDM 参数的系统性调控：行为层 SPE_RT 在 8 个设计单元间存在显著差异（F(7,80)=2.79, p=.012），但 SPE_ACC 差异不显著（p=.183）；DDM 参数层在主口径（6 个高质量条件）下 SPE_v 差异显著（F(5,59)=2.95, p=.019），贝叶斯因子处于轶事至实质证据之间；而 P/T/W 的线性回归几乎无解释力（R²=.05），提示其作用具有强非线性，需要非线性映射建模。

研究二针对短反应窗口下高发的无反应（omission）试次，系统比较了 Censor 与 Drop 两种处理方案对 DDM 参数估计的影响（8 组×2 方案，16 次层级贝叶斯拟合）。结果显示，遗漏试次的处理方式会强烈改变漂移率 v 的绝对估计：在遗漏率超过约 35% 的条件下（G1–G4），两方案参数差异超出 95% CI 重叠范围（如 G1 的 v_self 相差 Δ=6.81），仅 SPE 的相对方向保持稳定；在遗漏率低于约 15% 的条件下（G5–G8），Censor 方案足够可靠。据此，本研究确立了"排除高遗漏组、以高质量条件为主口径"的数据策略，并首次构建了适用于本范式的省略概率网络（OPN）概念验证。

研究三在主口径 6 个设计条件上校准并验证了 Sigmoid+GP 混合生成模型。差分进化校准显示：校准后边界调制参数方向与"时间压力—决策边界"假设一致（β₁=+0.33），自我条件漂移率增益约为 +86%（低于初始默认 150%），且不再出现旧版（含低质量组）校准中观测到的边界参数饱和伪影；模型在行为层可高度重建真实被试的模式（正确 RT 均值 r=.97、ACC r=.90、SPE_RT r=.85），但参数层的留一条件交叉验证（LOCV）表明，仅 6 个设计点不足以支撑高斯过程的外推，这一局限同时构成了开展更大规模设计空间探索的必要性论据。基于 GP 预测不确定性，本研究还给出了下一轮实验的高信息量候选区域（T≈480–500 ms、W≈300–350 ms 附近）。

研究四将行为与模型层面的 SPE 特征与更大范围证据对照：一方面，基于课题组构建的 SPE 数据库（44 篇文献/70 数据集/3,603 人，本文使用其中可获得子集）考察 SPE 的跨研究分布及其与呈现时间、试次数等设计变量的关系；另一方面，通过 CRF（条件反应函数）分析与 Stim-Coding 仿真建立"起始点偏差—行为模式"的生成链条，并对由实测 CRF 反推 DDM 参数的可辨识性进行了可行性分析。

综上，本研究构建了从实验设计参数（P,T,W）经 DDM 参数（v,a,t,z）到行为表现（RT/ACC/omission）的完整映射框架，系统揭示了设计空间对 SPE 的调制规律及其边界条件，验证了"理论引导 + 数据校准"混合建模在实验设计优化中的价值，并为 DDM 应用中遗漏反应的处理提供了基于真实数据的量化依据。

关键词：自我优势效应；自我匹配任务；实验设计空间；漂移扩散模型；高斯过程；遗漏反应

# Abstract

The choice of experimental design parameters profoundly shapes whether a psychological phenomenon can be observed stably and reliably. However, traditional studies typically compare effects across only a few discrete conditions and lack a systematic model of the mapping from experimental parameters, through latent cognitive processes, to observable behavior. Using the Self-Prioritization Effect (SPE) in the Self-Matching Task (SMT) as a testbed, the present study formalizes the number of practice trials (P), stimulus duration (T), and response window (W) into a three-dimensional experimental design space Ω and employs drift-diffusion model (DDM) parameters (drift rate v, boundary separation a, non-decision time t, and starting point z) as latent mediators. We develop a hybrid generative model combining a theoretical Sigmoid prior with Gaussian process (GP) residual learning, enabling quantitative prediction from design parameters, through cognitive parameters, to behavioral outcomes (RT, ACC, and omission rate), and validate it through empirical data, sensitivity analyses, an external database, and mechanistic simulations.

Study 1 systematically tested how the design space modulates SPE at both behavioral and DDM-parameter levels using data from 88 participants across eight experimental designs collected by the laboratory. SPE in RT differed significantly across design cells (F(7,80)=2.79, p=.012), whereas SPE in ACC did not (p=.183). Under the primary quality-restricted scope of six conditions, SPE in drift rate differed significantly (F(5,59)=2.95, p=.019) with anecdotal-to-substantial Bayes factors, while linear regressions of P/T/W explained almost no variance (R²=.05), motivating nonlinear mapping.

Study 2 systematically compared Censor versus Drop treatments of omission trials on DDM parameter estimation (16 hierarchical Bayesian fits across 8 designs × 2 treatments). Parameter estimates of drift rate were strongly affected by the treatment: when omission rates exceeded approximately 35% (G1–G4), differences exceeded 95% CI overlap (e.g., Δ=6.81 for v_self in G1), although the relative SPE direction remained stable; below approximately 15% omission (G5–G8), the Censor scheme was sufficiently reliable. This established the data-quality criteria for the study, and a proof-of-concept Omission Probability Network (OPN) was developed.

Study 3 calibrated and validated the Sigmoid+GP hybrid model on the six high-quality conditions. Calibrated boundary-modulation parameters were consistent with the time-pressure hypothesis (β₁=+0.33), the self-advantage gain in drift rate was about +86% (lower than the default 150%), and boundary-saturation artifacts previously observed when including low-quality groups disappeared. The model reconstructed real behavioral patterns at the behavioral level (r=.97 for correct RT, .90 for ACC, .85 for SPE_RT), whereas leave-one-condition-out validation showed that six design points are insufficient for GP extrapolation—constituting the rationale for broader design-space sampling. GP prediction uncertainty further identified high-information candidate regions (T≈480–500 ms, W≈300–350 ms) for future experiments.

Study 4 confronted these findings with broader evidence: SPE database analyses of cross-study distributions and their relations to stimulus duration and trial counts (using the accessible subset of 44 papers/70 datasets/3,603 participants), together with CRF-based analyses and Stim-Coding simulations linking starting-point bias to behavioral patterns, and a feasibility analysis of reverse inference from empirical CRF curves to DDM parameters.

Taken together, this thesis constructs a complete mapping framework from experimental design parameters (P, T, W) through DDM parameters (v, a, t, z) to behavioral performance, revealing how the design space modulates SPE and its boundary conditions, and providing quantitative, data-based guidance for omission handling in DDM applications.

Keywords: Self-Prioritization Effect; Self-Matching Task; experimental design space; drift-diffusion model; Gaussian process; omission
