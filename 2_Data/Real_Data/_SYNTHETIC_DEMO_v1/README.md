# `_SYNTHETIC_DEMO_v1` —— **合成数据，不是人类被试数据**

生成时间：2026-10-18T15:40:34

## 这是什么

这一目录里的 8 个 `.txt` 由 `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`
（M-T1 两阶段 DDM）模拟生成，**只用于把 Stage 1 → Stage 8 的流水线跑通**。
它们**不得**进入任何正式分析、也不得写进论文的结果表格。

## 真值（用于对照「流程能不能把已知参数捞回来」）

见 `synth_truth.json`（由生成器直接导出，非手抄）：

- 相位污染系数 `rho = 0.8`（M-T1 为真，M-T3 应被拒绝）
- P 效应 `beta_P = 1.5`（组 1/2/3/4 = P 0/8/32/120）
- 其它参数见 `group_truth`

## 规模与构成

| 组 | P | 练习试次 | 正式试次 | 被试 |
|---|---|---|---|---|
| 1 | 0 | 4 | 576 | 2 |
| 2 | 8 | 8 | 576 | 2 |
| 3 | 32 | 32 | 576 | 2 |
| 4 | 120 | 120 | 576 | 2 |

合计 8 名被试、每名 12 个 `(T, W)` 格 × 48 试次。抢按按 3% 注入（真实被试约 1%–3%），
以便 `check_stage1_acceptance.py` 的 6-B「刺激期内按键」有样本。

## 换真数据时怎么做

把主试用 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` 收来的
`EXP_data_group*_*.csv` + `exp_group*_subject*.txt` 放进 `2_Data/Real_Data/` 下
一个新目录（例如 `2026-11_pilot/`），然后对那个目录重跑同一套命令即可；
**不要**把真数据和本目录混放（`intake.py` 会把同名快照判为 shadowed）。
