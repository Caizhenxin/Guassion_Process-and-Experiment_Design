# 3_Figures：所有图的唯一落点

> 口径（D115，用户 2026-10-24）：**代码在 `1_Code`、数据在 `2_Data`、图在 `3_Figures`**。
> 这里的每一张图都能由脚本重跑出来，图不进代码目录、也不进数据目录。

## 1. 本项目新增的图（与 `2_Data/Generate_Data` 同名子目录）

| 目录 | 图 | 生成脚本 | 对应数据 |
|---|---|---|---|
| `M-T1/` | `fig1_rt_density` RT 分布 / `fig2_rt_quantiles` 分位曲线 / `fig3_accuracy_omission` 正确率-遗漏 / `fig4_crf` 条件正确率函数 / `fig5_delta` delta 图 / `fig6_mechanism` 漂移轨迹 | `python 1_Code/Experiment/gen_viz.py --model all` | `2_Data/Generate_Data/M-T1/{trials_long,subjects,cells}.csv` |
| `M-T2/` | 同上（斜坡模型） | 同上 | `2_Data/Generate_Data/M-T2/…` |
| `M-T3/` | 同上（单阶段） | 同上 | `2_Data/Generate_Data/M-T3/…` |
| `_compare/` | `fig7_model_compare` 三模型对照 / `fig8_spe_locus` SPE 位点签名 | `gen_viz.py`（fig7）、`python 1_Code/Experiment/spe_locus.py`（fig8） | `2_Data/Generate_Data/_compare/spe_locus.csv` |
| `_practice/` | `fig9_practice_lambda` λ 天花板 × 练习 × SPE | `python 1_Code/Experiment/practice_lambda.py` | `2_Data/Generate_Data/_practice/practice_lambda*.{csv,json}` |
| `figures_sim/` | `fig_sim_crlb` 参数精度下界 / `fig_sim_p_design` P 方案识别力 / `fig_sim_trials` 模拟试次级数据 | `python 1_Code/Experiment/make_sim_figures.py` | 数值表在 `5_Reference/03_论文写作/figures_sim/*.csv` |

## 2. 历史目录（旧项目口径）

`Animation/`、`ANOVA/`、`Generate_Data_gp_ddm_v24/`、`GP_Sigmoid*/`、`CRF_Analysis/`、`Cross_Validation/` … 等
40+ 个子目录来自旧的分析流程，未逐一对齐。收尾时的对齐计划与新目录规则写在
[`5_Reference/08_工作流/文件结构整理_待办.md`](../5_Reference/08_工作流/文件结构整理_待办.md) 第 8 条。

## 3. 约定

1. **图不进 `2_Data`**：数值表（CSV/JSON）随数据走，图一律写到这里。
2. **子目录名尽量与 `2_Data/Generate_Data/<同名>` 对应**，方便「图 → 数据 → 脚本」三级追溯。
3. 论文正式用的图，请复制到当章目录并在正文标注图号；本目录只保证「可重跑」。
