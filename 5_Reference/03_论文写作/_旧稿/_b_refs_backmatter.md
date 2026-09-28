# 参考文献

中文文献（按拼音排序）

- 胡传鹏, 王非, 宋梦迪, 隋洁, 彭凯平. (2016). 心理学研究中的可重复性问题：从危机到契机. 心理科学进展, 24(9), 1504-1518.
- 刘逸康, 胡传鹏. (2023). 证据积累模型的行为与认知神经证据. 科学通报, 69(8), 1068-1081.
- 温佳慧. (2025). 实验设计的维度与空间：以自我匹配任务为例 [硕士学位论文]. 南京师范大学心理学院.

英文文献（按字母排序）

- Brainard, D. H. (1997). The psychophysics toolbox. Spatial Vision, 10(4), 433–436.
- Cai, Z., Wang, Q., Liu, Z., Sui, J., & Hu, C.-P. (in prep). The self-prioritization effect database with standardized meta-data.
- Dutilh, G., Krypotos, A.-M., & Wagenmakers, E.-J. (2011). Task-related versus stimulus-specific practice: A diffusion model account. Experimental Psychology, 58(6), 434–442.
- Fengler, A., Govindarajan, L. N., Chen, T., & Frank, M. J. (2021). Likelihood approximation networks for fast inference of sampling models in cognitive neuroscience. [出处卷期页码待核]
- Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2026). The perils of omitting omissions when modeling evidence accumulation. PLoS Computational Biology, 22(8), e1014667.
- Luce, R. D. (1986). Response times: Their role in inferring elementary mental organization. Oxford University Press.
- Matzke, D., & Wagenmakers, E.-J. (2009). Psychological interpretation of the ex-Gaussian and shifted Wald parameters: A diffusion model analysis. Psychonomic Bulletin & Review, 16(5), 798–817.
- Myung, J. I., Cavagnaro, D. R., & Pitt, M. A. (2013). A tutorial on adaptive design optimization. Journal of Mathematical Psychology, 57(3), 53–67.
- Ratcliff, R. (1978). A theory of memory retrieval. Psychological Review, 85(2), 59–108.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice decision tasks. Neural Computation, 20(4), 873–922.
- Rouder, J. N., Speckman, P. L., Sun, D., Morey, R. D., & Iverson, G. (2009). Bayesian t tests for accepting and rejecting the null hypothesis. Psychonomic Bulletin & Review, 16(2), 225–237.
- Rouder, J. N., Morey, R. D., Speckman, P. L., & Province, J. M. (2012). Default Bayes factors for ANOVA designs. Journal of Mathematical Psychology, 56(5), 356–374.
- Schulz, E., Speekenbrink, M., & Krause, A. (2018). A tutorial on Gaussian process regression: Modelling, exploring, and exploiting functions. Journal of Mathematical Psychology, 85, 1–16.
- Sui, J., & Humphreys, G. W. (2015). The integrative self: How self-reference integrates perception and memory. Trends in Cognitive Sciences, 19(12), 719–728.
- Sui, J., He, X., & Humphreys, G. W. (2012). Perceptual effects of social salience: Evidence from self-prioritization effects on perceptual matching. Journal of Experimental Psychology: Human Perception and Performance, 38(5), 1105–1117.
- Tran, N. H., van Maanen, L., Heathcote, A., & Matzke, D. (2021). Systematic parameter reviews in cognitive modeling: Towards a robust and cumulative characterization of psychological processes in the diffusion decision model. Frontiers in Psychology, 11, 608287.
- Voss, A., Rothermund, K., & Voss, J. (2004). Interpreting the parameters of the diffusion model: An empirical validation. Memory & Cognition, 32(7), 1206–1220.
- Wiecki, T. V., Sofer, I., & Frank, M. J. (2013). HDDM: Hierarchical Bayesian estimation of the drift-diffusion model in Python. Frontiers in Neuroinformatics, 7, 14.

# 附录A 冻结设计表与关键数字锁定表

（依据《冻结规格书_v1_20260902.md》：8 组条件的权威设计参数、质量分档、以及论文所有统计量（S01–S12）的来源文件与运行日期登记表。本附录在定稿时以正式表格形式给出。）

# 附录B 脚本与可复现性说明

本文全部统计与建模结果均由以下冻结脚本产出（seed 固定、路径自动推导，见 1_Code/）：
- BF/ANOVA 冻结版：1_Code/Python_for_Check/Basic_Hypothesis/BF_freeze_20260902.py
- 行为 ANOVA 冻结版：1_Code/Python_for_Check/ANOVA/run_spe_anova_freeze_20260902.py
- GP+Sigmoid 6 条件冻结版：1_Code/Python_HDDM/GP+Sigmoid/run_frozen6_20260902.py（产物 2_Data/Generate_Data/GP_Sigmoid_Frozen6/）
- Omission 敏感性：1_Code/Python_for_Check/Omission/Omission_Sensitivity_Analysis.ipynb
数据与图分别存放于 2_Data/ 与 3_Figures/；论文数据与代码在正式发表前将上传至 OSF/GitHub。

# 致谢

（致谢内容待补：感谢导师胡传鹏教授的指导；感谢课题组温佳慧等同学在数据采集与前期工作中的贡献；感谢参与实验的所有被试；感谢学院与评审专家。）

致谢正文将在提交前补写完整。
