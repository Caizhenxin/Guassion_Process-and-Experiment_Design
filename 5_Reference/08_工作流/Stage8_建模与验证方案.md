# Stage 8 ｜层级建模、后验预测检验与模型比较方案

- **日期**：2026-10-14
- **状态**：🟡 进行中（核心件已交付且带基准证据；正式数据到手后跑全量）
- **依据**：`5_Reference/08_工作流/工作流_主计划.md` §3 Stage 8（L332）；决策 **D41**（依赖/环境）；`5_Reference/AGENTS.md`；`1_Code/DDM_Core/README.md` §8.22
- **权威性**：⚠️ **部分过时风险** —— 本方案的全部数值证据都在**模拟数据**上取得；正式数据到手后必须按 §10 重跑并在 §11 记录差异。

---

## 1. 目的（照录主计划 §3 Stage 8）

> 层级 DDM 拟合 → PPC（分位数、正确/错误 RT、timeout、Self/Other × Match/Nonmatch）→ PSIS-LOO（含 Pareto k 诊断）→ 模型比较 → leave-one-participant-out。

其中 **leave-one-participant-out** 是为了一句明确的话：**不得用 trial-level LOO 冒充跨被试泛化**。本方案的 LOO 单位一律是**被试**。

---

## 2. 与相邻 Stage 的分工

| Stage | 问题 | 本方案的接口 |
|---|---|---|
| 4（设计处方） | 采什么设计 | 本方案在**定稿设计 D4** 上拟合（576 试次/人：3 block × 4 档 T × 4 类 × 12 次） |
| 7（采集质控） | 数据能不能用 | Stage 7 的 `qc_group.py` 逐 P 组放行后的数据才进本方案 |
| **8（本方案）** | **哪个模型对、后验像不像数据** | 产出 ELPD-LOO 比较表 + PPC 表 + 层级参数估计 |
| 9（设计优化） | 下一轮设计怎么改 | 用本方案的生成模型与不确定性量化当 GP 代理的输入 |

---

## 3. 依赖与环境决定（D41）

**实测环境**（`1_Code/DDM_Core/_scratch/_probe_env.py`）：

| 状态 | 包 |
|---|---|
| ✅ 可用 | python 3.13.9、numpy 2.3.5、scipy 1.16.3、pandas 2.3.3、matplotlib 3.10.6、sklearn 1.7.2 |
| ❌ `ModuleNotFoundError` | `pymc`、`numpyro`、`jax`、`arviz`、`cmdstanpy`、`emcee`、`torch`、`hddm`、`ssm` |

⇒ 主计划字面上的 PSIS-LOO 在本机**没有现成 PPL 可以执行**。D41 选择 **路线 (b) 零依赖**：

1. **后验抽样**用**拉普拉斯近似**（`likelihood.numerical_hessian` 的信息矩阵），不引入 PPL；
2. **PSIS-LOO 自实现**（`loo.py`，Vehtari/Gelman/Gabry 2017 算法 1）；
3. **PPC 与以被试为单位的 LOO 与抽样器无关** ⇒ 无论将来是否装 PPL，这两条都不需要重写。

**待用户拍板**（D41 未决部分）：是否安装 `pymc` + `arviz`。收益是真贝叶斯后验与成熟诊断（rank plot、R̂、ESS、`az.loo`）；代价是改变项目依赖面，而且**必须在论文方法里交代抽样器与先验**，而本项目全线目前是 MLE、没有任何先验。

---

## 4. 模型族与参数化

- **参数化**：以定稿的 `shape_model="lin"` 为准（README §8.7/§8.11 的结论：exp 参数集下 9 个设计的信息矩阵全部非正定，lin 下全部正定）。
- **被试内自由参数**（`mapping.WITHIN_FREE_LIN`，7 个）：`d_ref, beta_T, beta_S, beta_ST, a_ref, delta_a, t0`。
- **两个竞争模型**：
  - **M-T1**：时变输入（两阶段漂移），多一个自由参数 `rho`；
  - **M-T3**：恒定漂移，即 `rho = 1` 的严格嵌套特例；
  - **M-T2**：**按 D37 以论证关闭**，不进入拟合（理由与检验力无关：在 D4 上 `E[#(RT<T)] = 0.00`，M-T2 的判别特征结构性缺席）。
- ⚠️ **`beta_ST` 的处置**：README §9 第 23 项已建议维持 D24，把它**移出确证性集合**（确证集 6 个：`{d_ref, beta_T, beta_S, a_ref, delta_a, t0}`）。`stage8.py` 的后验相关矩阵给出了直接证据：`corr(beta_T, beta_ST) = −0.699`（同一份后验里即可看见补偿）。**因此 `beta_ST` 的估计值可以报，但不得进入确证性结论。**

---

## 5. 拟合路线：拉普拉斯-EM 层级拟合（`1_Code/DDM_Core/hier.py`）

### 5.1 群体模型

```
x_s ~ N(mu, diag(sigma^2))          # x = 被试参数的无约束坐标
y_s ~ p(y | theta_s),  theta_s = 反变换(x_s)
(mu, log sigma) 带弱信息先验
```

常量：`POP_MU_PRIOR_SD = 2.0`、`POP_LOGSIGMA_PRIOR_MU = log(0.5)`、`POP_LOGSIGMA_PRIOR_SD = 1.0`、`SIGMA_FLOOR = 1e-3`、`MAX_MODE_ITER = 80`、`HYPER_STEP = 0.05`。

### 5.2 拉普拉斯边际

```
log_marg = g(x*) + (K/2)·log 2π − 0.5·logdet(−∂²g/∂x²),   g = log p(y|x) + log N(x; mu, sigma²)
```

非正定的特征值个数（`n_flipped`）**如实传出**：`n_flipped ≠ 0` 说明该点不是可信的众数，该被试的边际不能用。

### 5.3 EM 的两步

- **E 步**：逐被试求 MAP 众数 `x*`，并给出上面的拉普拉斯边际；
- **M 步**（闭式，零额外似然评估）：
  ```
  mu_k      = Σ_s x*_{s,k} / n                （带先验平滑）
  sigma_k²  = mean_s[(x*_{s,k} − mu_k)² + Cov_s[k,k]]
  ```
  ❗ 那个 `+ Cov_s[k,k]` 是**标准修正**，漏掉会让 σ 系统性低估（自测实测：只用众数离散度 **0.4029** < 含修正的 **0.4499**）。

### 5.4 为什么用 EM 而不是直接优化 `(mu, log sigma)`

`1_Code/DDM_Core/_scratch/_probe_stage8_timing.py` 实测：

| 每人试次数 | 单次 `log_likelihood_step` | `hessian_x`（K=4） | 冷启动 L-BFGS ≤60 步 |
|---|---|---|---|
| 576 | **84.02 ms** | **3.43 s** | **9.32 s** |
| 192 | 42 ms | 1.72 s | 3.01 s |
| 96 | 21.6 ms | 0.96 s | 1.78 s |

⇒ 5 人一次外层评估 ≈ **64 s**，8 维 Nelder-Mead 要上百次评估 = 数小时；EM 8–15 轮即可收敛，M 步是闭式的。

### 5.5 已知实现陷阱

`likelihood._bounds_for` 写的是 `override.get(n, PARAM_BOUNDS[n])`，Python **先求值默认参数** ⇒ 即使 `override` 里有 `rho` 也会 `KeyError: 'rho'`（`rho` 只定义在 `twophase.MASK_RHO_BOUNDS`，不在 `likelihood.PARAM_BOUNDS`）。`hier.py` 因此自带 `_bounds_with_rho(names, override)`，合并 `{**PARAM_BOUNDS, RHO_NAME: MASK_RHO_BOUNDS}`。

---

## 6. 后验预测检验（PPC，`1_Code/DDM_Core/stage8.py`）

- `laplace_draws(log_post_x, x0, n_draws=4000, ...)`：协方差 = `(−∂²log_post/∂x²)^{-1}`；非正定时把负/零特征值抬到 `eig_floor·max|λ|` 并报告 `n_flipped`；cholesky 失败时退回特征分解抽样。
- `sample_ppc(design, p, rng, sampler=simulate.simulate_subject)`：⚠️ **必须把设计列 `T`/`W`/`is_self`/`is_match`/`P` 与观测列合并**，否则 `RT<T` 与分单元统计量**静默变 `NaN`**。
- **`PPC_STATS`（12 项）**：`n_obs`、`omission_rate`、`acc`、`rt_p10`…`rt_p90`、`rt_p50_correct`、`rt_p50_error`、**`rt_lt_T_rate`**、`worst_cell_omission`。
- `ppc_table(obs_tr, design, draws, ...)` 输出每项的观测值、后验预测 95% 区间与是否在带内；`alpha = 0.05`。
- **判据**：**12 项里至少 10 项落在 95% 带内**才算"模型与数据相容"（自测实测：参数正确时 **11/12** 在带内；把 `d_ref` 砍半、`beta_T` 翻倍、`beta_S` 三倍后 **8/12** 在带外）。

---

## 7. 以被试为单位的 PSIS-LOO

- `loo.py` 实现 Vehtari/Gelman/Gabry 2017 算法 1：`gpd_fit`（**Grimshaw 一维剖面似然**）、`psis_one`、`psis_loo`、`waic`、`loo_compare`。
- 常量：`K_BAD = 0.7`、`K_UNUSABLE = 1.0`、`_MIN_EXCESS = 5`、`M = int(min(S/5, 3√S))`、截断 `w = min(w, S**0.75·mean(w))`。
- **`loo_compare` 的差值 SE 必须用配对差**，不能把两个 SE 相加。
- `hier.py` 的 `loo_matrix`：给定超参数后验抽样（`hyper_draws`），对每个被试在每个超参数抽样的条件后验下算边际对数似然，得到 `(S, N)` 矩阵交给 `psis_loo`。
- ❗ ❗ **N 太小时 k 会爆表**：自测（N=3）实测 `max k = 4.33 / 5.00`、3/3 个被试越界、`p_loo = 28.7 / 516.5` ⇒ **该规模下不构成模型比较证据**。正式设计的 ~40 人/组**必须在正式数据上重跑本诊断**才能引用。
- ⚠️ **单个 `k̂` 的噪声很大（实测 SD 0.096–0.129），不得逐点解读**。判断"是否该换 `k`-fold CV"看 **`n_k_gt_bad / N` 这个比例**与 **`k_max`**，而不是某个观测的 `k̂` 是否刚好越过 0.7。

---

## 8. 模型比较与决策规则（事前登记）

| 情形 | 动作 |
|---|---|
| `max k ≤ 0.7` | 报 `ΔELPD` + 配对 SE；`\|Δ\| > 2·SE` 才称"更好" |
| `0.7 < max k ≤ 1.0` | 报 `n_k_gt_bad/N`；结论降级为"提示性" |
| `max k > 1.0` | **判定为不构成证据**；改用 `loo_bruteforce`（真留一）或增加被试后重跑 |
| 真留一与 PSIS 方向不一致 | 以**真留一**为准（它是金标准，代价是 N 倍重拟合） |

**M-T1 vs M-T3** 是本 Stage 的主比较；**M-T2 不参与**（D37 论证关闭）。

---

## 9. 工具链与自测证据

| 文件 | 作用 | 证据 |
|---|---|---|
| `1_Code/DDM_Core/loo.py` | 零依赖 PSIS-LOO | `_scratch/check_loo.py` **14/14 通过**：对解析高斯 LOO 的偏差 **0.015**（逐点最大 0.006）、`p_loo = 1.248`（真值 1）、WAIC 与 PSIS 一致；已知尾部 `k = 1/α` 下均值 0.3271 / 0.8301，α=1.2 时 **169/200 = 84% 报警** |
| `1_Code/DDM_Core/stage8.py` | 拉普拉斯抽样 + PPC（全局 + **分单元**） | `_scratch/check_stage8.py` **24/24 通过**（含分单元 PPC 的 D1–D7）：二维高斯协方差还原最大元素误差 **0.0059**、鞍点 `n_flipped = 1`、拉普拉斯 SD / OPG SE = **1.10 / 1.13 / 1.01 / 0.92**、PPC 双向校准 11/12 与 8/12；**D4 是「必须有分单元」的直接证据**：全局 `omission_rate` 只看到 **0.25**，而 Self-Match 单元内是 **1.0**、其余 **0.0** |
| `1_Code/DDM_Core/hier.py` | 拉普拉斯-EM + 被试层 LOO | `_scratch/check_hier.py` **0 项未通过**（总耗时 388.2 s）：闭式边际 max \|Δ\| = **3.97e-09**、σ̂ = **0.4499**（真值 0.5）、PSIS vs 真留一 **r = 0.9942**、群体均值后验 SD 10 人 0.1319 → 60 人 0.0710 |
| `_scratch/diag_gpd_bias.py` | 校准 `k̂` 的抽样分布 | 2000 次重复实测：单观测 **SD 0.103 / 0.143**、偏差 −0.009 / −0.013 |

❗ **一条元教训**（写进 README §8.22）：`_scratch/check_loo.py` 首轮 9/12 不过，**根因是我的判据错了、不是代码错了**。给自己写的估计量设容差时，容差必须来自**实测的抽样分布**。

---

## 10. 正式数据到手后的动作（回填要求）

1. 用 `stage8_run.py` 在**每组 ~40 人**上跑全量层级拟合（预计是批处理作业，不是交互式运行）。
2. 重跑 `check_hier.py` 的 B 组规模（N=40 而非 3），确认 `k_max` 与 `n_k_gt_bad/N` 落在可用区。
3. 把 §9 的模拟证据替换/补充为正式数据证据，并回填 `工作流_主计划.md`（进度表 + 变更日志 + 证据表）与 `1_Code/DDM_Core/README.md`。
4. PPC 的**分单元**统计量（Self/Other × Match/Nonmatch）在正式数据上补齐（自测里只用了整体 12 项）。

---

## 11. 已知限制（**必须随结果一起报**）

1. **本项目全线是 MLE、没有任何先验** ⇒ 默认 `log_post` 就是对数似然，抽到的是"以 MLE 为中心、按观测信息量宽度"的**近似**后验，**不等于**真贝叶斯后验。论文里不得写成"贝叶斯后验"。
2. **拉普拉斯是局部近似**：似然面在 `(τ_T, β_T, β_ST)`、`(τ_a, δ_a)` 方向极平 ⇒ 必须**同时报特征值谱与 `n_flipped`**。
3. **被试层 PSIS-LOO 需要足够多的被试**：N=3 时 `max k` 达 4.33–5.00，不构成证据；~40 人/组的效果需在正式数据上验证。
4. **单个 `k̂` 不得逐点解读**（SD 0.096–0.129）。
5. **运行时**：576 试次/人、K=4 时单次似然 84 ms、Hessian 3.43 s、冷启动 L-BFGS 9.32 s；160 人的全量层级拟合**不能**在交互式会话里跑。
6. **仿真器的事实来源存在潜在冲突**：`5_Reference/AGENTS.md` 规定"仿真器只有一个事实来源：`1_Code/Python_for_Check/TenRules_Revision_20260912/sim_utils.py`"，而 DDM_Core 这条线有自己的 `simulate.py` / `wfpt.py` / `twophase.py`。该条早于 DDM_Core 线，**须在论文方法与 README 里明确交代本线用的是哪一套**。
7. **PPC 是证伪工具、不是估计方法**：自测的"错误参数"臂只做了粗扰动，不能反过来当作参数恢复的证据。
8. 本方案的一切结论目前**只覆盖 `lin` 参数化与 2 个真值家族**（`exp` / `lin`），且是**模拟数据**。

---

## 12. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-10-14 | 首版：环境决定 D41、拉普拉斯-EM 层级拟合、PPC 12 项判据、以被试为单位的 PSIS-LOO、模型比较决策规则、8 条已知限制；全部数值证据来自三个自测脚本（14/14、17/17、0 失败） |
