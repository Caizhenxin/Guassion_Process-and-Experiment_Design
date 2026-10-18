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
- ❗ ❗ **被试层 `p_loo` 不是「有效参数数」（D73）**：`loo_matrix` 的每一列是「给定一组超参数的profile 边际似然」，超参数抽样走到尾部时该列被个别荒诞抽样支配 ⇒ `p_loo` 量的是**离散度**。实测：D70（3 人 × 96 试次、S=30）`p_loo = 1489.098`（`n_obs = 3`）、`k_max = 5.000`；`_s8run_an`（2 人）出现负 p_loo（−706.371 / −2900.542）；探针 `_probe_loo_level.py` 里同一构造（3 人 × 47/46/47 试次、S=20）被试层 `p_loo = 45.002`、试次层同批抽取 `p_loo = 19.273`（`n_obs = 140`、`p_loo/n_obs = 0.138`、`k_max = 0.000`）。
- ⇒ **口径（D73）**：模型比较的 `ΔELPD` 用**试次层**矩阵（`n_obs` = 总试次）；**被试层**留一交给`loo_bruteforce`（小 N，金标准）或 K-fold（大 N）。
- ✅ **已落成可切换口径（D73 ⑧）**：`python stage8_run.py ... --loo-level trial`（默认 `participant`，全部历史日志与结论保持不变）；`hier.loo_matrix_trials` 返回 `(S, 总试次)`，逐试次似然非有限时该试次记 −inf 并计 `n_trial_ll_fail`；`compare_models` 会拒绝形状或层不一致的矩阵；`--loo-level` **进缓存配置键**（同 `--out` 换口径 `--resume` 会报配置不一致，不会静默混用）。被试层 PSIS 的数字只能作为「矩阵不可估」的证据引用，不得当作拟合优度。

---

## 8. 模型比较与决策规则（事前登记）

| 情形 | 动作 |
|---|---|
| ❗ **`p_loo` 不在 `[0, n_obs]`** | **判定为「本组 LOO 无效」**，不得引用 `ELPD`/`ΔELPD`；先查 `n_draws` 与样本量（**决策 D52**，见下） |
| `max k` 非有限，或 `n_failed ≥ n_obs` | 同上：**`nan` 不是最差挡位**，必须与「`k > 1.0`」分开报 |
| `max k ≤ 0.7` | 报 `ΔELPD` + 配对 SE；`\|Δ\| > 2·SE` 才称"更好" |
| `0.7 < max k ≤ 1.0` | 报 `n_k_gt_bad/N`；结论降级为"提示性" |
| `max k > 1.0` | **判定为不构成证据**；改用 `loo_bruteforce`（真留一）或增加被试后重跑 |
| 真留一与 PSIS 方向不一致 | 以**真留一**为准（它是金标准，代价是 N 倍重拟合） |

> ❗ **决策 D52｜`max k` 单独没有分辨力，必须同时看 `p_loo`。**
> 依据是 4 人 analytic 端到端干跑（`--n-x 31 --n-draws 32`）的实测：M-T1 给出
> `max k = 0.000`、`n_failed = 0`（上表**两条**既有判据全部通过），而 `p_loo = 2816.26`
> 对 `n_obs = 4`（本项目的 LOO 单位是**被试**，见 `1_Code/DDM_Core/hier.py:494` 的
> `loo_matrix` 返回 `(S, N)` 与 `1_Code/DDM_Core/loo.py:238` 的 `n_obs = N`）
> ⇒ **有效参数数是观测数的 704 倍**，结构性崩坏。
> 而同一个 `max k = 0.000` 在**健康**矩阵上也会出现（实测
> `rng.normal(-3.0, 0.3, size=(30, 3))` 的另一次抽样：`p_loo = 0.222`、`max k = 0.0`）
> ⇒ `max k` 为 0 既可能是"权重近似均匀"也可能是"权重彻底退化"，**无法分辨**。
> `p_loo` 的健康区间是 `[0, n_obs]`：`p_loo < 0` 意味着留一比拟合内还准（不可能），
> `p_loo > n_obs` 意味着惩罚超过全部信息量（N=2 的旧干跑实测 −706.37 / −2900.54，
> 但那一档本来就被 `n_failed = n_obs` 拦住了 ⇒ **这个洞是 N=4 才暴露的**）。
> 因此：① 判据改为 `0 ≤ p_loo ≤ n_obs` 才继续走下面的 `k` 挡位；
> ② 报告行**必须**打印 `p_loo/n_obs` 这个比值（它是唯一能分辨的那个数）；
> ③ 该判据已落进 `1_Code/DDM_Core/stage8_run.py` 的 `render_group`，并由
> `_scratch/check_stage8_run.py` 的 **A7c/A7d 两颗牙齿**（越界必须报「LOO 无效」）与
> **A7e 反向对照**（健康 `p_loo` 不得被误伤）守住，自测 **18/18 → 23/23**（D66 加 E1–E5 五颗输入契约牙齿）。

**M-T1 vs M-T3** 是本 Stage 的主比较；**M-T2 不参与**（D37 论证关闭）。

---

## 9. 工具链与自测证据

| 文件 | 作用 | 证据 |
|---|---|---|
| `1_Code/DDM_Core/loo.py` | 零依赖 PSIS-LOO | `_scratch/check_loo.py` **14/14 通过**：对解析高斯 LOO 的偏差 **0.015**（逐点最大 0.006）、`p_loo = 1.248`（真值 1）、WAIC 与 PSIS 一致；已知尾部 `k = 1/α` 下均值 0.3271 / 0.8301，α=1.2 时 **169/200 = 84% 报警**；D63 加 D1–D3 三条 ArviZ 复核断言后 **17/17** |
| `1_Code/DDM_Core/stage8.py` | 拉普拉斯抽样 + PPC（全局 + **分单元**） | `_scratch/check_stage8.py` **24/24 通过**（含分单元 PPC 的 D1–D7）：二维高斯协方差还原最大元素误差 **0.0059**、鞍点 `n_flipped = 1`、拉普拉斯 SD / OPG SE = **1.10 / 1.13 / 1.01 / 0.92**、PPC 双向校准 11/12 与 8/12；**D4 是「必须有分单元」的直接证据**：全局 `omission_rate` 只看到 **0.25**，而 Self-Match 单元内是 **1.0**、其余 **0.0** |
| `1_Code/DDM_Core/hier.py` | 拉普拉斯-EM + 被试层 LOO | `_scratch/check_hier.py` **0 项未通过**（D68 加 C 组 4 项机制断言：`cov` 该方向 = `1/floor`、`n_flipped` 如实记账、边际有限、负曲率方向众数发散；A/B 两组原总耗时 388.2 s）：闭式边际 max \|Δ\| = **3.97e-09**、σ̂ = **0.4499**（真值 0.5）、PSIS vs 真留一 **r = 0.9942**、群体均值后验 SD 10 人 0.1319 → 60 人 0.0710 |
| `_scratch/diag_gpd_bias.py` | 校准 `k̂` 的抽样分布 | 2000 次重复实测：单观测 **SD 0.103 / 0.143**、偏差 −0.009 / −0.013 |
| `_scratch/_make_ddm_pilot.py`（**D70 正向对照生成器**） | 按 M-T1 真值（`rho = 0.8`）用 `two_phase.simulate_euler_subject` 生成 RT/选择，再按 `Exp_Design_Formal.m` 的帧/掩蔽规则写成 v4.1 的 25 列 tab txt；`--preset qc` 用 `QC_TRUTH`（`d = 1.15 / a = 1.15 / t0 = 0.18`）、`--preset fim` 用 `TRUTH`（`d = 1.20 / a = 1.10 / t0 = 0.15`，与 Stage 9 探针同口径） | `_scratch/check_make_ddm_pilot.py` **12/12 通过**（G1–G12）；全量设计（2 人 × 576 试次）过 `1_Code/Experiment/qc_group.py` **G1–G9 全 PASS、剔除 0、待复核 0**；3 人 × 96 试次、`n_x = 25`、`analytic`：**PPC 认得出自己生成的数据** —— 6 个（被试 × 模型）块的全局统计量 **69/72 = 95.8% 在带内**、分单元 **120/120 = 100%**；而 D65 的非 DDM 数据只有 **37/72 = 51.4%** 与 **95/120 = 79.2%** ⇒ 分辨力是实打实的。但**被试层 LOO 在 N=3 上仍无效**（M-T1 `p_loo/n_obs` = 496、M-T3 = 3.68）⇒ 不得引用 ELPD/ΔELPD，正向对照能支持的**只有 PPC**。 |
| `1_Code/DDM_Core/stage8_run.py`（正向对照运行，D70） | 用 `ddm_pilot_posctrl`（DDM 生成、3 人 × 96 试次）跑全链路，判「PPC 会不会认对」 | 3 人 × 96 试次、`n_x = 25`：M-T1 ELPD −1642.940 ± 588.064（`p_loo` 1489.10 ⇒ 无效）、M-T3 ELPD −153.004 ± 43.343（`p_loo` 11.03、`p_loo/n_obs` 3.68 ⇒ 无效）；**PPC：M-T1 全局 34/36、分单元 60/60；M-T3 全局 35/36、分单元 60/60**（合计 **69/72** 与 **120/120**），阴性对照只有 **37/72** 与 **95/120**；总耗时 **6229.7 s**（M-T1 3966.0 s + M-T3 2236.9 s）；另 M-T1 的 Hessian 又一次 `n_flipped` = 1/16（特征值 [−0.539, 338]）⇒ 与 D68 的「最平方向随时翻负」一致 |
| `1_Code/DDM_Core/stage8_run.py`（干跑 I） | 全链路端到端：读数据 → 两模型层级拟合 → 被试层 LOO → 模型比较 → 分单元 PPC → 报告 | 3 人（142/143/141 试次）、`n_em` 5、`n_draws` 30、`n_x` 25、PPC 2、`analytic`：**5597.9 s**；M-T1 ELPD −521.183 ± 7.258、`p_loo` 185.369、`k_max` 5.000；M-T3 −350.223 ± 16.448、36.221、4.825；两行都被判「⛔ 本组 LOO 无效」（`p_loo/n_obs` 61.8 / 12.1） |
| `1_Code/DDM_Core/stage8_run.py`（干跑 II） | 同上（更小配置，用来量成本与查闸门） | 3 人、`n_em` 3、`n_draws` 12、`n_x` 21、PPC 1：**3013.2 s**；两个模型 `k_max` 全 **0.000**、`n_k_gt_bad` 全 0，而 `p_loo/n_obs` = **72.7 / 48.2** ⇒ 被判无效 ——**只读 `k_max` 会误判「可报」**（D52 在真实运行器里的现场证据） |
| `1_Code/Experiment/run_pipeline.py`（D98） | 把整条分析链串成一条命令（入库 → 达标 → 层级拟合 → 出图 → 结果节骨架），并用合成数据（8 人 × 576 试次）端到端验证；每步只调用既有工具，不复制判据 | `_stage8_out/stage8_group_1.json` 实测 **M-T1 ELPD -536.7（`p_loo` 10.07、`k_diag_ok` None）；M-T3 ELPD -537.4（`p_loo` 9.85、`k_diag_ok` None）**；`intake.py` 8/8 KEEP、`stage6_report.py` 判「可进入 Stage 7」 |
| `1_Code/DDM_Core/stage8_run.py`（输入契约，D66） | 入口分辨输入：目录只取 `*.txt`、非 txt 用 `_non_txt_reason()` 拒绝并逐条列出 `HEADER25` 缺列、空观测用 `rep["error"]` 说明、`RF.validate` 包进 try、无可用被试时打印明细并 **exit 2** | 喂 `EXP_data_combined.csv` ⇒ exit 2 并点名 **9 列**缺列（改前未捕获 `KeyError: matchKey`、exit 1）；喂无 txt 目录 ⇒ exit 2；`--synthetic 2 --plan-only` ⇒ exit 0 |
| `1_Code/DDM_Core/stage8_run.py`（组级缓存/续跑，D72） | 每组拟合完立刻写 `stage8_group_<组>.json`（含 `config`）；`--resume` 复用已完成组并在报告里留「♻️ 复用缓存」行；缓存损坏或配置不一致 ⇒ `ValueError`（不静默重算） | `_scratch/check_stage8_run.py` **31/31**（E13 落盘与报告内容、E14 `run_group` 调用 **0** 次且缓存字节不变、E15 换 `n_em` 报配置不一致、E14b 坏缓存报错、E16 缓存走 `*.tmp` + `os.replace` 原子写）；E 组原 26 项仍全绿 |
| `1_Code/DDM_Core/hier.py`（LOO 口径根因，D73） | 同一批超参数抽取下**同时**算被试层与试次层 PSIS-LOO，量两层的 `p_loo` / `k_max` / 离散度 | 被试层 `p_loo = 45.002`（`n_obs = 3`）、`k_max = 0.000`；试次层 `p_loo = 19.273`（`n_obs = 140`、比值 **0.138**）、`k_max = 0.000` ⇒ 试次层可用；另一次抽样里被试层矩阵全距 **2.3e9** |
| `1_Code/DDM_Core/stage8_run.py --loo-level trial`（D73 ⑧） | 试次层口径**端到端**跑通并落纸：`--synthetic 2 --synth-n-rep 1 --n-em 1 --n-draws 15 --n-x 11 --hyper-method analytic` ⇒ 报告印「LOO 口径 = `trial`」「`n_obs` = 总试次」，`check_loo.py` 26/26（F1–F5）、`check_stage8_run.py` 32/32（E17） | 该次运行 `p_loo/n_obs` = 8.57 / 12.7、`k_max` = 0、越界 0/93 ⇒ 换层本身不保证可用（见下一条 D74） |
| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（D74） | 同一份代码、只改配置，直接读 `hyper.eigval` 与 θ 的逐维 SD | 正定侧（3 人、`n_em=2`、`n_x=21`、S=20）：min eig **0.026544**、负特征值 **0/16**、θ SD ≤ 3.88、\|θ\| ≤ 9.32 ⇒ 试次层 `p_loo/n_obs` = **0.138**；非正定侧（2 人、`n_em=1`、`n_x=11`、S=15）：2 个负特征值（−0.825 / −0.947）、θ SD 达 **134**、\|θ\| 达 **303** ⇒ `p_loo/n_obs` = 8.57 / 12.7 ⇒ **判据顺序 = 先 `n_flipped`，再看层与比值** |
| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（D75 扫描） | 同一份代码、只改 N（`n_em=2`、`n_x=21`、S=2、seed 7、≈46 试次/人），读 `hyper.eigval` 与 `max_abs_theta` | N=2 正定（0.0388、0/16、7.0）、N=3 正定（0.0265、0/16、7.3）、N=4 **非正定**（−0.0875、1/16、62.8）、N=5 正定（0.1019、0/16、4.5）、N=6 **非正定**（−0.0051、1/16、33.6）；N=4 加试次到 187–191 仍 1/16 非正定（−0.357、max\|θ\| 97.9、256.4 s）⇒ **正定性逐次拟合而定，非样本量函数** |
| `1_Code/DDM_Core/stage8_health.py`（D76：组级健康判据） | 扫 `stage8_group_*.json`，把「这组 LOO 能不能引用」收敛成一条命令：三条硬闸（`n_flipped` > 0 / 口径非 trial / `p_loo` 越界·`k_max` 非有限·失败率 > 20% / `n_draws` < 10）+ 两条软告警（`max_abs_theta` ≥ 20 或缺失 ⇒ 按未落盘告警；`0.7 < k_max` ≤ 1.0）+ 混口径 ⇒ 不可比较 | `_scratch/check_stage8_health.py` **27/27 通过**（A 12 项单块判据、B 混口径与渲染、C `--strict`/`--json` 端到端、D 坏输入必须响亮）；实测两组病态缓存都判「⛔ 不可引用」：`stage8_trial_s15`（`n_flipped` 2/16、`p_loo` 797 / `n_obs` 93）、`stage8_d75_gate`（`p_loo` −242.9、`k_max` nan、`max\|θ\|` 269.1） |
| `1_Code/DDM_Core/_scratch/check_stage8_run.py`（E 组，D66） | 输入契约的回归守卫：E1 理由含 `v4.1`/`HEADER25` 且点名 9 个缺列；E2 CSV ⇒ `SystemExit(2)`；E3 无 txt 目录 ⇒ `SystemExit(2)`；E4 静态三条守卫；E5 正路未被误伤；**E6**（D70）报告表头的「来源」不得硬编码「正式数据」 | 自测 **26/26、未通过 0 项、exit 0**（D68 加 **A11/A12**：非正定必须写「σ 不得解读」+ `floor` + 收敛 σ 区间；正定只报「正定」；D70 加 **E6**） |
| `1_Code/DDM_Core/stage8_run.py::render_group`（D68） | 每个模型多一行「超参数 Hessian」：正定 ⇒ 报特征值区间 并写「正定」；非正定 ⇒ ⛔「本次的 σ（被试间 SD）不得解读」+ `floor = max(1e-8·max abs(λ), 1e-12)` + `1/floor` + **本次收敛 σ 的末轮区间** | 干跑件实测 M-T1 `n_flipped` = 1/16、eig ∈ [−0.203, 229]、`1/floor` ≈ 4.37e+05、收敛 σ ∈ [0.0127, 2.27e+03]（σ 已无意义）；M-T3 `n_flipped` = 0/14、eig ∈ [0.0199, 231]、σ ∈ [6.65e-06, 2.95] |

❗ **一条元教训**（写进 README §8.22）：`_scratch/check_loo.py` 首轮 9/12 不过，**根因是我的判据错了、不是代码错了**。给自己写的估计量设容差时，容差必须来自**实测的抽样分布**。

---

## 10. 正式数据到手后的动作（回填要求）

1. ❗ **先判 LOO 可用性、再谈 ΔELPD（D74/D75）**：每组拟合完，报告里「超参数 Hessian」行若非正定（`n_flipped` > 0）或本次抽样 `\|θ\|` 最大值远大于其余组（实测分离：正定 ≤ 7.3 vs 非正定 33.6–303），则该组的 `p_loo`/`ELPD` **一律不解读**；同时记录特征值谱与 `max_abs_theta`，并在该组报告口径行标注 `--loo-level`。⚠️ 不得因为「每组 ~40 人」就预先承诺 LOO 可用（D75：正定性在 N=2…6 上非单调）。此外，**拟合完立刻跑** `python -X utf8 1_Code\DDM_Core\stage8_health.py <该组的 --out 目录> --strict`（D76）：有任一组「不可引用」即非零退出，`--json` 留一份机器可读汇总；人读报告与检查器结论不一致时以检查器为准。
2. 用 `stage8_run.py` 在**每组 ~40 人**上跑全量层级拟合（预计是批处理作业，不是交互式运行）。
3. 重跑 `check_hier.py` 的 B 组规模（N=40 而非 3），确认 `k_max` 与 `n_k_gt_bad/N` 落在可用区。
4. 把 §9 的模拟证据替换/补充为正式数据证据，并回填 `工作流_主计划.md`（进度表 + 变更日志 + 证据表）与 `1_Code/DDM_Core/README.md`。
5. PPC 的**分单元**统计量（Self/Other × Match/Nonmatch）在正式数据上补齐（自测里只用了整体 12 项）。
6. ❗ **输入形态只有一种**：`stage8_run.py` 只吃 `Exp_Design_Formal.m` 写出的 **v4.1 逐被试 txt**（制表符、`HEADER25` 25 列，见 D66）。历史汇总 CSV（`2_Data/Real_Data/EXP_data_combined.csv`）**缺 9 个必填列**、`2_Data/Real_Data/` 下也没有任何 `*.txt` ⇒ **不得**把它当 Stage 8 的输入，也**不写** CSV 适配层（补列等于造数据）。

---

## 11. 已知限制（**必须随结果一起报**）

1. **本项目全线是 MLE、没有任何先验** ⇒ 默认 `log_post` 就是对数似然，抽到的是"以 MLE 为中心、按观测信息量宽度"的**近似**后验，**不等于**真贝叶斯后验。论文里不得写成"贝叶斯后验"。
2. **拉普拉斯是局部近似**：似然面在 `(τ_T, β_T, β_ST)`、`(τ_a, δ_a)` 方向极平 ⇒ 必须**同时报特征值谱与 `n_flipped`**。
3. **被试层 PSIS-LOO 不是「被试太少」的问题，是口径不可估**（D73，见第 17 条）：`p_loo` 在被试层量的是 profile 边际在超参数抽取间的**离散度** ⇒ 加被试、加试次都不会让它变成参数个数（N=3 时 `max k` 4.33–5.00；N=4 的 analytic 干跑 `max k = 0.000`、`n_failed = 0` 两条判据全过，而 `p_loo/n_obs = 704`）。模型比较请用试次层矩阵。
4. **单个 `k̂` 不得逐点解读**（SD 0.096–0.129）。
5. **运行时**：576 试次/人、K=4 时单次似然 84 ms、Hessian 3.43 s、冷启动 L-BFGS 9.32 s；160 人的全量层级拟合**不能**在交互式会话里跑。
6. **仿真器的事实来源存在潜在冲突**：`5_Reference/AGENTS.md` 规定"仿真器只有一个事实来源：`1_Code/Python_for_Check/TenRules_Revision_20260912/sim_utils.py`"，而 DDM_Core 这条线有自己的 `simulate.py` / `wfpt.py` / `twophase.py`。该条早于 DDM_Core 线，**须在论文方法与 README 里明确交代本线用的是哪一套**。
7. **真实规模必须按组续跑**：每组 ~40 人 × 576 试次的层级拟合是**几十小时**的批处理作业（§11 第 5 条）；`stage8_run.py` 自 D72 起每组落盘、`--resume` 可续，但缓存**只按组号匹配**且配置已绑定 ⇒ 换数据/换 `n_em` 必须换 `--out` 目录。报告里「♻️ 复用缓存」行必须保留，否则读者无法分辨哪些组是这次算的。
8. **PPC 是证伪工具、不是估计方法**：自测的"错误参数"臂只做了粗扰动，不能反过来当作参数恢复的证据。
9. 本方案的一切结论目前**只覆盖 `lin` 参数化与 2 个真值家族**（`exp` / `lin`），且是**模拟数据**。
10. ❗ **`max k` 不是 LOO 可用性的充分判据**（决策 D52）：N=4 的干跑实测 `max k = 0.000`、`n_failed = 0` 两条判据全过，而 `p_loo/n_obs = 704`（结构性崩坏）。**凡报出 LOO 结果，必须同时报 `p_loo`、`n_obs` 与 `p_loo/n_obs`**；只报 `max k` 与 `n_k_gt_bad` 的表格**不得**用来支持模型比较。
11. **`n_x`（似然网格分辨率）必须写进任何性能/退化结论**：`--n-x 31` 与自测默认的 41 不是同一个配置（D51 的 `_numdiff` 退化只在 31 下复现）。
12. ❗ **成本预估器低估 3–4 倍**（D65）：主配置预估 29.4 min / 实测 5597.9 s（93.3 min，×3.2）；小配置预估 13.2 min / 实测 3013.2 s（50.2 min，×3.8）。它的标定口径是「48 试次/人、`n_x=41`、单次似然 34 ms」，而合成干跑每人 141–143 试次、正式数据是 576 试次/人 ⇒ **正式采集的时间计划必须按预估 ×4 留余量**，且这还不含重复运行的次数。
13. ❗ **合成干跑的数据不是 DDM 生成的**（D65）：`_scratch/make_fake_pilot.py` 按 `Exp_Design_Formal.m` 的规则表转录（RT = `T + lognormvariate(−0.5, 0.45)`、正确率固定 0.75、刺激内按键均匀分布）。因此干跑里 PPC 的系统性失配（遗漏率观测 0.06–0.09 vs 预测 0.19–0.26、`rt_p50` 观测 0.70 vs 预测 0.60）是**阴性对照成功**：它说明 PPC 能认出「这份数据不是这个模型生成的」，**不能**反过来当作对模型的批评。要在 DDM 数据上验模型恢复，必须用 `1_Code/DDM_Core/simulate.py` 那一套生成器。
14. ❗ **报数值健康时必须同时报 `n_degenerate_nonfinite`**（D65）：主配置它是 **54**（M-T1）/ **16**（M-T3），而 `n_nonfinite_loglik` = **0** —— 非有限的目标函数求值不进那个计数，并伴 scipy `_numdiff` 的 `RuntimeWarning: invalid value encountered in subtract`（D51 同族，但 `n_x = 25` 就出现）。另：`analytic` 超参数 Hessian 在 N=3 上**并非必正定**（M-T1 最小特征值 −0.2031、`n_flipped = 1`；M-T3 +0.0199、0）⇒ §11 第 2 条的「必须同报特征值谱与 `n_flipped`」不是仪式。**D68 把后果补上**：非正方向被 `floor` 抬起 ⇒ 方差 ≈ 1/floor（实测 `1/floor` ≈ 4.37e+05），层级 σ² 会被它撑大；干跑件里 M-T1 的收敛 σ 末轮最大 **2.27e+03** ⇒ **本次 σ 不得解读**，报告已按此打印（`stage8_run.py::render_group` 的「超参数 Hessian」行）。**N 依赖实测（D68 回填）**：A 组（DDM、seed 7）归一化最小特征值 **−4.202e-03（N=3，1/16）→ −1.362e-03（N=6，1/16）→ +1.394e-03（N=12，0/16）→ +1.184e-03（N=24，0/16）** ⇒ 符号翻、量级不变；B 组（非 DDM、N=3）种子 7/11/99 = 1/16、1/16、2/16；A 组 N=3 换 seed=99 = 0/16 ⇒ **逐数据集偶发**。结论：不得写「小样本现象、N≈40 安全」，只能写「最平方向随时可能翻负 ⇒ 正式数据上逐模型按 `n_flipped` 判」。
15. ❗ **输入契约是硬约束**（D66）：Stage 8 只吃 v4.1 逐被试 txt；历史汇总 CSV 缺 9 列（含 `block`/`premature_press`/`timeout`/三个 `*_actual`）⇒ 缺的就是**没记下来的信息**，不是解析缺陷。任何人拿历史数据跑 Stage 8 的结果都必须先过这条闸。
16. ❗ **正向对照只在 N=3 / 96 试次上做过（D70）**：`p_loo/n_obs` 仍是 496（M-T1）/ 3.68（M-T3） ⇒ 被试层 LOO **依旧无效**（**不是** N 依赖：见第 17 条 D73 的机理）；所以正向对照能支持的只有 PPC 与「模型比较的方向」，**不能**支持「~40 人时 LOO 可用」。另：`TRUTH` 选得比被试快时（RT 中位 0.275 s）连 DDM 数据也会被 `analyze_pilot.py` 的 S6-5 判 FAIL ⇒ 生成数据时必须显式选 `QC_TRUTH`，否则 QC 的 FAIL 会掩盖真相。
17. ❗ **被试层 PSIS-LOO 不可估，不是「被试太少」（D73）**：`p_loo` 在被试层量的是 profile 边际在超参数抽取间的**离散度**，因此随抽样数/尾部荒诞值涨落（D70 的 3 人 × 96 试次给出 496；`_s8run_an` 的 2 人给出**负值**）。⇒ 模型比较用**试次层**矩阵（同批抽取实测 `p_loo/n_obs = 0.138`、`k_max = 0`），被试层留一用 bruteforce（小 N）/ K-fold（大 N）。报告必须同时印 `n_hessian_fail`。
18. ❗ **「试次层」不是 LOO 可用的充分条件（D74）**：超参数 Hessian 非正定（`n_flipped` > 0）时，抽样里混着 |θ| 达数百的荒诞尾部值 ⇒ 两层都会越界（实测同一份代码：正定配置试次层 `p_loo/n_obs` = 0.138，非正定配置 8.57 / 12.7）。因此引用任何 `p_loo`/`ELPD` 前**必须先报 `n_flipped` 与特征值谱**。
19. ❗ **不得写「人够了 LOO 就可用」（D75）**：超参数 Hessian 的正定性在 N=2…6 上**非单调**（2/3/5 正定、4/6 非正定），调大每人试次也不消除（N=4：≈46 → 187–191 试次后仍 1/16 非正定、`max|θ|` 从 62.8 升到 97.9）。且失败拟合的 `λ_min` 可只到 −0.005（相对 `λ_max` 约 1e-5）⇒ **符号不说明程度**，必须与 `max_abs_theta` 并列报告。
20. ❗ **「能不能引用 LOO」有唯一代码出口**（D76）：`stage8_health.py` 的硬闸（`n_flipped` > 0、口径非 trial、`p_loo ∉ [0, n_obs]` 或 `k_max` 非有限或失败率 > 20%、`n_draws` < 10）与软告警（`max_abs_theta` ≥ 20 或缺失、`0.7 < k_max ≤ 1.0`）逐条对应 D73–D75；**同组内混用两种口径 ⇒ 模型比较不成立**。人读报告与跑检查器必须给出同一结论；若不一致，以检查器为准并修报告判词，不得反过来放宽判据。

---

## 12. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-10-14 | 首版：环境决定 D41、拉普拉斯-EM 层级拟合、PPC 12 项判据、以被试为单位的 PSIS-LOO、模型比较决策规则、8 条已知限制；全部数值证据来自三个自测脚本（14/14、17/17、0 失败） |
| v1.1 | 2026-10-14 | **§8 加决策 D52**：`p_loo` 必须落在 `[0, n_obs]`，且报告行必须打印 `p_loo/n_obs`；依据 = 4 人干跑 `max k = 0.000` + `n_failed = 0` 全过而 `p_loo/n_obs = 704`（N=4 才暴露的洞，N=2 被 `n_failed = n_obs` 拦住）。§11 加第 9、10 条限制（`max k` 不充分；`n_x` 必须写进结论）。代码落点 `1_Code/DDM_Core/stage8_run.py::render_group`，自测 `_scratch/check_stage8_run.py` **18/18**（新增 A7c/A7d/A7e） |
| v1.2 | 2026-10-17 | **§9 加两行合成数据端到端干跑证据**（`stage8_run.py` 全链路跑通，5597.9 s / 3013.2 s，产物含报告与结果 JSON）；`check_loo.py` 行补记 D63 的 **17/17**（新增 D1–D3 三条 ArviZ 复核断言）。**§11 加第 11–13 条限制**（成本低估 3–4 倍、合成数据非 DDM ⇒ PPC 失配只作阴性对照、必须同报 `n_degenerate_nonfinite` 与 Hessian 特征值谱）。决策 D65 |
| v1.3 | 2026-10-17 | **§8 自测数 18/18 → 23/23、§9 加两行输入契约证据、§10 加第 5 条回填要求、§11 加第 14 条限制（D66：只吃 v4.1 逐被试 txt，历史 CSV 缺 9 列不可转换）** |
| v1.4 | 2026-10-17 | **§9 加 `render_group` 的「超参数 Hessian」行、`check_stage8_run.py` 自测 23/23 → 25/25（A11/A12）、`check_hier.py` 加 C 组 4 项机制断言（`cov` 该方向 = `1/floor`、负曲率方向众数发散）、实测非正定的 N 依赖（A 组归一化最小特征值 **−4.202e-03 → −1.362e-03 → +1.394e-03 → +1.184e-03**，符号翻而量级不变；换 seed 会翻 ⇒ 逐数据集偶发）；§11 第 13 条补「非正定 ⇒ σ 不得解读」的后果与实测值（M-T1 收敛 σ 末轮最大 2.27e+03）。决策 D68 |
| v1.5 | 2026-10-17 | **§9 加正向对照生成器与运行两行、`check_stage8_run.py` 自测 25/25 → 26/26（E6：报告表头的「来源」不得硬编码「正式数据」）、§11 加第 15 条限制**（N=3/96 试次下 LOO 仍无效；`TRUTH` 比被试快时 QC 会误判；PPC 有分辨力：正向 69/72 vs 阴性 37/72） |
| v1.6 | 2026-10-17 | **§7 加「被试层 `p_loo` 是离散度」两条口径（D73）、§9 加 LOO 口径根因探针行、§11 重排编号并加第 17 条（被试层不可估）、`check_loo.py` 17 → 21/21（E1–E4：病态抽样不中断整轮）、`hier.loo_matrix` 容错 + `n_hessian_fail`、`stage8_run.py` 报 `n_degenerate_hessian`** |
| v1.7 | 2026-10-17 | **试次层 LOO 落成代码**（`--loo-level {participant,trial}`、`hier.loo_matrix_trials`、`compare_models` 层/形状守卫；`check_loo.py` 21 → 26/26、`check_stage8_run.py` 31 → 32/32）；**新增 D74**：超参数 Hessian 正定是前置条件（`render_group` 判词加「非正定 ⇒ `p_loo` 不可解读」，`check_stage8_run.py` 32 → **34/34**）；§7 加「已落成可切换口径」、§9 加两行端到端与正定/非正定对照、§11 加第 18 条 |
| v1.9 | 2026-10-18 | **§9 加 `run_pipeline.py` 一行（D98）**：全流程一键跑通，合成数据 8 人端到端；`loo.psis_loo` 增 `k_diag_ok`（`n_draws < 25` 时 `k̂` 恒 0，此前是静默的健康读数；`check_loo.py` 26/26 仍全过）。 |
| v1.8 | 2026-10-17 | **新增 D75**：超参数 Hessian 正定性非样本量函数（N=2…6 扫描 + N=4 加试次两路实测）；`hier.hyper_draws` 增 `max_abs_theta`、§9 的 Hessian 行并列入报告、`check_stage8_run.py` 34 → **37/37**（A13/A13b/A14）；§10 回填要求新增「逐组先看 `n_flipped` 与 `max_abs_theta`，再决定 LOO 是否可引用」；§11 加第 19 条 |
| v1.9 | 2026-10-17 | **新增 D76**：`1_Code/DDM_Core/stage8_health.py`（组级健康判据一键报告：三条硬闸 + 两条软告警 + 混口径判定，`--json`/`--strict`）+ `_scratch/check_stage8_health.py` **27/27**；§10 第 1 条补「拟合完立刻跑 `--strict`」；§11 加第 20 条 |
