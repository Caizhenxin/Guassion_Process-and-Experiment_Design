# 论文图表包（Thesis_20260902）— canonical4（4 链）口径

> 生成：2026-09-02 ｜ 依据：冻结规格书（S01–S12 canonical4 更新版）
> tables/*.csv 为数据表（UTF-8-SIG，可直接贴 Word/Excel）；figures/*.png 为图片。
> 插入正文时统一改编号为"表4-1/图5-1…"并加题注（表上、图下）。

## 表（13 张）
| 文件 | 建议题注 | 插入位置 | 备注 |
|---|---|---|---|
| T4-1_design_table.csv | 表 4-1 八组实验设计条件与被试信息 | §4.2 | 含质量档 |
| T5-1_spe_cell_means.csv | 表 5-1 行为 SPE 单元格均值（n/均值±SD） | §5.3.1 | |
| T5-2_anova_behavior.csv | 表 5-2 行为层 ANOVA（RT/ACC；8 单元与 6 单元） | §5.3.1 | RT p=.012 |
| T5-3_anova_param_4chain.csv | 表 5-3 DDM 参数层 SPE_v ANOVA＋G*Power＋BF（4 链） | §5.3.2 | p=.106 不显著，如实报告 |
| T5-4_regression_4chain.csv | 表 5-4 线性回归 SPE_v~P+T+W | §5.3.3 | R²=.042 |
| T6-1_censor_drop.csv | 表 6-1 Censor vs Drop 参数对比（v_self 与 SPE_v） | §6.3.1 | G1 Δ=6.81 等 |
| T6-2_opn_metrics.csv | 表 6-2 OPN 第一版训练指标 | §6.3.2 | fast 模式 |
| T7-1_hddm_params_4chain.csv | 表 7-1 HDDM 参数组均值±SD 与收敛诊断（4 链） | §7.2 输入 | 含 r̂/ESS |
| T7-2_sigmoid_calib_canonical4.csv | 表 7-2 Sigmoid 校准参数（canonical4） | §7.3.1 | |
| T7-3_insample_canonical4.csv | 表 7-3 GP in-sample 拟合指标 | §7.3.2 | |
| T7-4_locv_canonical4.csv | 表 7-4 LOCV（6 折）指标 | §7.3.2 | |
| T7-5_behavior_canonical4.csv | 表 7-5 行为重建验证（in-sample） | §7.3.3 | ACC/omission r≈.99 |
| T7-6_candidates_canonical4.csv | 表 7-6 候选实验点（GP 不确定性） | §7.3.4 | 探索性 |

## 图（figures/*.png）
| 文件 | 建议图题 | 插入位置 | 说明 |
|---|---|---|---|
| F4-1_design_space.png | 图 4-1 实验设计空间 Ω 与八组取点 | §4.1 | 颜色=质量档 |
| F5-1_spe_subjects.png | 图 5-1 被试级 SPE（行为 RT/ACC＋参数 SPE_v）箱线图 | §5.3.1 | |
| F5-2_gpower_4chain.png | 图 5-2 参数层观察效应量 vs 功效门槛 | §5.3.2 | |
| F5-3_bf_prior_sensitivity_4chain.png | 图 5-3 贝叶斯因子先验敏感性 | §5.3.2 | |
| F6-1_*.png（Omission_Sensitivity 现成 5 张） | 图 6-1 Censor vs Drop / 遗漏率 | §6.3.1 | 建议核对标题口径 |
| F6-2_*.png（OPN_Training 现成） | 图 6-2 OPN 预测精度与边缘效应 | §6.3.2 | |
| F7-1_insample_fit.png 等 | 图 7-1~7-4（in-sample/LOCV/行为验证/候选点） | §7.3 | canonical4 版 |
| F8-1_sliding_window.png | 图 8-1 内部滑动窗口分析（注明内部数据） | §8.3.1 | |
| F8-3_*.png（Stim-Coding CRF） | 图 8-3 起始点偏向的 CRF 曲线（双引擎） | §8.3.3 | |

## 待补（未在本包内，见《今日总结与明日计划》）
- 表 8-1/8-2（SPE 数据库子集统计与设计变量分析）
- 图 8-2（SPE 库跨研究分布）；图 7-5 Sigmoid 理论 vs 校准曲线（可选绘图）
- 图 8-4 模拟 vs 真实 CRF 叠加（可选）
