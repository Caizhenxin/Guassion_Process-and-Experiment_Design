# 广义线性模型（GLM）功效检验方法综述

> 本文档介绍广义线性模型（GLM）功效检验的两种主要范式：传统频率学派与贝叶斯学派，涵盖原理、适用场景、代码示例及对比总结。

---

## 目录

- [广义线性模型（GLM）功效检验方法综述](#广义线性模型glm功效检验方法综述)
  - [目录](#目录)
  - [1. 背景：为什么 GLM 的功效分析更复杂？](#1-背景为什么-glm-的功效分析更复杂)
  - [2. 传统频率学派做法](#2-传统频率学派做法)
    - [2.1 渐近 Wald 检验法（解析近似）](#21-渐近-wald-检验法解析近似)
    - [2.2 模拟法（推荐）](#22-模拟法推荐)
      - [步骤](#步骤)
      - [Python 示例（Logistic 回归）](#python-示例logistic-回归)
    - [2.3 非中心分布近似法](#23-非中心分布近似法)
  - [3. 贝叶斯做法](#3-贝叶斯做法)
    - [3.1 贝叶斯因子设计分析（BFDA）](#31-贝叶斯因子设计分析bfda)
      - [步骤](#步骤-1)
      - [关键输出指标](#关键输出指标)
      - [R 代码示例](#r-代码示例)
    - [3.2 后验功效分析](#32-后验功效分析)
    - [3.3 ROPE + HDI 方法](#33-rope--hdi-方法)
      - [Python 示例（PyMC + ArviZ）](#python-示例pymc--arviz)
  - [4. 频率学派 vs 贝叶斯：对比总结](#4-频率学派-vs-贝叶斯对比总结)
    - [选择建议](#选择建议)
  - [5. 对 SPE 实验的启示](#5-对-spe-实验的启示)
    - [当前设计的局限](#当前设计的局限)
    - [未来改进方向](#未来改进方向)
    - [推荐参考文献](#推荐参考文献)
      - [一、经典方法论基础（频率学派 GLM/GLMM 功效分析）](#一经典方法论基础频率学派-glmglmm-功效分析)
      - [二、贝叶斯因子与 BFDA（经典与近年发展）](#二贝叶斯因子与-bfda经典与近年发展)
      - [三、GLMM 模拟法功效分析（心理学近年实用进展）](#三glmm-模拟法功效分析心理学近年实用进展)
      - [四、贝叶斯 GLMM 与心理学教程](#四贝叶斯-glmm-与心理学教程)
      - [五、DDM / 计算建模方向（与 SPE 实验高度相关）](#五ddm--计算建模方向与-spe-实验高度相关)

---

## 1. 背景：为什么 GLM 的功效分析更复杂？

GLM（Generalized Linear Model）包含非正态响应分布（Binomial、Poisson、Gamma 等）和连接函数（logit、log 等），使得功效分析比普通线性模型更复杂：

| 难点 | 说明 |
|:---|:---|
| **非正态似然** | 解析公式不存在或仅在大样本下近似成立 |
| **方差依赖于均值** | Logistic/Poisson 回归中 Var(Y) 是 μ 的函数 |
| **连接函数的非线性** | 效应量在原始尺度和链接尺度上不同 |
| **协变量的分布** | 多元预测变量使非中心参数计算更复杂 |

因此，**模拟法** 在实际应用中最为通用和推荐。

---

## 2. 传统频率学派做法

### 2.1 渐近 Wald 检验法（解析近似）

基于 **非中心卡方分布**，适用于简单单预测变量设计：

**核心逻辑**：

在 H₁ 下，Wald 统计量近似服从非中心卡方分布：

```
W = β̂ / SE(β̂)  ~  N(√λ, 1)           （单参数正态近似）
W²  ~  χ²(1, λ)                        （卡方形式）
```

其中非中心参数 **λ = β² / Var(β̂)**，Var(β̂) 依赖于 Fisher 信息矩阵，进而依赖于设计矩阵 X 和连接函数下的期望响应。

**计算步骤**：

1. 指定效应量 β（log-OR、log-RR 等）
2. 指定协变量分布（X 的均值、方差或二分类比例）
3. 基于 Fisher 信息计算 Var(β̂)，得到 λ
4. `Power = 1 − F_χ²(χ²_crit; df=1, λ)`

**常用软件**：

| 软件 | 适用场景 |
|:---|:---|
| **G\*Power** | Z-test 族 → Logistic/Poisson 回归 |
| **R `pwr`** | 基础功效分析 |
| **R `WebPower`** | `wp.logistic()`, `wp.poisson()` |

**局限**：仅适用于单预测变量的简单设计，多变量、交互项、重复测量等不适用。

---

### 2.2 模拟法（推荐）

这是 GLM 功效分析**最通用、最可靠**的方法，适用于任意复杂设计。

#### 步骤

```
1. 指定真实效应量 β_true（效应大小，从文献或最小有意义效应确定）
2. 指定设计矩阵 X（预测变量的分布/实验条件）
3. 指定 GLM 族和连接函数（Logistic / Poisson / Gamma 等）
4. 重复 N_sim 次：
   a. 根据 GLM 生成响应 Y：μ = g⁻¹(Xβ_true)，Y ~ Family(μ)
   b. 拟合 GLM，记录感兴趣参数 β 的 p 值
5. Power = 显著次数 / N_sim
```

#### Python 示例（Logistic 回归）

```python
import numpy as np
import statsmodels.api as sm

def sim_power_logistic(n, beta_true, X_dist, n_sim=1000, alpha=0.05):
    """
    模拟法计算 logistic 回归的统计功效。

    Parameters
    ----------
    n : int
        样本量
    beta_true : array-like
        真实回归系数 [β₀, β₁, ...]
    X_dist : dict
        预测变量分布, e.g. {'mean': 0, 'sd': 1}
    n_sim : int
        模拟次数
    alpha : float
        显著性水平

    Returns
    -------
    power : float
        统计功效
    sig_count : int
        显著的模拟次数
    """
    sig_count = 0
    for _ in range(n_sim):
        # 生成预测变量和响应
        X = np.random.normal(X_dist['mean'], X_dist['sd'], size=n)
        eta = beta_true[0] + beta_true[1] * X
        prob = 1 / (1 + np.exp(-eta))
        y = np.random.binomial(1, prob, size=n)

        # 拟合模型
        X_sm = sm.add_constant(X)
        model = sm.Logit(y, X_sm).fit(disp=0)
        p_val = model.pvalues.iloc[1]  # 感兴趣参数

        if p_val < alpha:
            sig_count += 1

    return sig_count / n_sim, sig_count


# 使用示例：OR=1.5 → β₁=log(1.5)，截距 β₀=-1.0，样本量 200
power, _ = sim_power_logistic(
    n=200,
    beta_true=[-1.0, np.log(1.5)],
    X_dist={'mean': 0, 'sd': 1},
    n_sim=1000
)
print(f"Power = {power:.3f}")
```

**优点**：

- 适用于任意复杂 GLM（交互项、多项式、多分类、随机效应扩展）
- 无需解析公式
- 可扩展为 power curve（遍历 N 得到 power-N 曲线）

**缺点**：

- 计算量取决于模拟次数（通常 1000–5000 次）

---

### 2.3 非中心分布近似法

当 GLM 是标准形式（Logistic / Poisson / 恒等连接），且样本量足够大时，可以用 **似然比统计量的非中心卡方近似**：

```
G² = 2[ℓ(β_full) − ℓ(β_null)]  ~  χ²(df, λ)

λ = 2 × n × KL(h₁ || h₀)        （Kullback-Leibler 散度）
```

R 包 `pwr`、`longpower`（纵向数据）和 `simr`（`lme4` 模型）使用了相关思路。此方法比 Wald 近似更精确，但仍需大样本假设。

---

## 3. 贝叶斯做法

贝叶斯功效分析的核心不同于频率学派：**不存在固定的 "α=0.05" 阈值**，而是从后验分布或贝叶斯因子的角度定义"成功"。

### 3.1 贝叶斯因子设计分析（BFDA）

> Schönbrodt & Wagenmakers (2018)，Psychonomic Bulletin & Review

不预设固定 N，而是 **序贯监控** BF 穿越阈值的轨迹，模拟"如果做实验，多久能得出结论"。

#### 步骤

```
1. 指定先验（对效应量的合理信念，可使用非信息先验或来自文献）
2. 指定 BF 证据阈值，如：
   - BF₁₀ > 10 → "强证据支持 H₁"
   - BF₀₁ > 10 → "强证据支持 H₀"
   - 1/10 ≤ BF ≤ 10 → "没有结论，需要更多数据"
3. 模拟循环（N_sim 次）：
   a. 从先验中抽取效应量 β_sim
   b. 根据 β_sim 和 GLM 生成数据
   c. 逐步增加 N，计算 BF，记录何时穿越阈值
4. 汇总输出
```

#### 关键输出指标

| 指标 | 含义 |
|:---|:---|
| **达到结论的比例** | 在 N_max 内穿越阈值的比例（贝叶斯版 power） |
| **中位样本量** | 达到结论所需的典型 N |
| **错误结论率** | H₁ 真实但 BF 支持 H₀ 的比例（以及反过来的比例） |
| **不确定比例** | N_max 内未得出结论的比例 |

#### R 代码示例

```r
library(BayesFactor)

bfda_logistic <- function(n_max, beta_true, prior_scale = 0.5, n_sim = 500) {
  decisions   <- numeric(n_sim)   # 1=支持H1, 0=支持H0, NA=未决定
  stopping_n  <- numeric(n_sim)   # 停止时的 N

  for (s in 1:n_sim) {
    decided <- FALSE
    for (n in seq(20, n_max, by = 10)) {
      # 生成数据
      X   <- rnorm(n)
      eta <- 0 + beta_true * X
      prob <- plogis(eta)
      y   <- rbinom(n, 1, prob)

      # 用 BIC 近似 BF（实际应用推荐 brms + bridge sampling）
      bf <- exp((BIC(glm(y ~ 1, binomial)) - BIC(glm(y ~ X, binomial))) / 2)

      if (bf > 10) {
        decisions[s]  <- 1
        stopping_n[s] <- n
        decided <- TRUE
        break
      } else if (bf < 0.1) {
        decisions[s]  <- 0
        stopping_n[s] <- n
        decided <- TRUE
        break
      }
    }
    if (!decided) {
      decisions[s]  <- NA
      stopping_n[s] <- n_max
    }
  }

  list(
    power_h1     = mean(decisions == 1, na.rm = TRUE),
    power_h0     = mean(decisions == 0, na.rm = TRUE),
    inconclusive = mean(is.na(decisions)),
    median_n     = median(stopping_n[!is.na(decisions)]),
    early_stop_pct = mean(!is.na(decisions))
  )
}
```

---

### 3.2 后验功效分析

利用 **现有数据的后验** 作为"真实效应"来源来做功效规划：

```
1. 从现有数据获得后验分布 p(θ | D_observed)
2. 从后验中采样 θ*_i（纳入参数不确定性）
3. 对每个 θ*_i，模拟生成新数据集 D*_i
4. 对每个 D*_i，拟合新模型并检验
5. 显著/支持结论比例 = 后验预测功效
```

**与频率学派模拟法的关键区别**：

- 频率学派用**单个点估计**作为真实效应
- 贝叶斯后验功效用**整个后验分布**，自然纳入参数不确定性，避免过度乐观

---

### 3.3 ROPE + HDI 方法

> Kruschke (2015), *Doing Bayesian Data Analysis*

不计算传统意义上的"功效"，而是用 **实际等效区域（Region of Practical Equivalence, ROPE）** 来判断：

```
1. 设定 ROPE，例如：
   - Logistic 回归：ROPE = [-0.1, 0.1]（log-OR 接近 0 即为无实际意义的效应）
   - 或转换到 OR 尺度：ROPE = [0.9, 1.1]

2. 计算后验 95% HDI（Highest Density Interval）

3. 决策规则：
   ┌────────────────────────────────────────────┐
   │ HDI 完全落在 ROPE 内   → 接受 H₀（等效）   │
   │ HDI 完全落在 ROPE 外   → 接受 H₁（有差异） │
   │ HDI 与 ROPE 重叠       → 不确定，需要更多数据 │
   └────────────────────────────────────────────┘
```

可以通过模拟研究：在给定 N 下，有多大比例的后验样本能给出**明确结论**——这就是贝叶斯版的功效概念。

#### Python 示例（PyMC + ArviZ）

```python
import pymc as pm
import arviz as az
import numpy as np

# 假设已有 MCMC 后验样本 trace
# 计算 HDI 并判断是否在 ROPE 内
rope = [-0.1, 0.1]  # ROPE on log-OR scale
hdi = az.hdi(trace, var_names=["beta"], hdi_prob=0.95)

if hdi["beta"][1] < rope[0]:  # HDI 上界 < ROPE 下界（负效应，不在 ROPE 内）
    decision = "Accept H1 (negative effect)"
elif hdi["beta"][0] > rope[1]:  # HDI 下界 > ROPE 上界（正效应，不在 ROPE 内）
    decision = "Accept H1 (positive effect)"
elif hdi["beta"][0] >= rope[0] and hdi["beta"][1] <= rope[1]:
    decision = "Accept H0 (practically equivalent)"
else:
    decision = "Inconclusive — need more data"
```

---

## 4. 频率学派 vs 贝叶斯：对比总结

| 维度 | 传统频率学派 | 贝叶斯 |
|:---|:---|:---|
| **核心统计量** | p 值 < α | BF 阈值 / ROPE + HDI |
| **解析方法** | 非中心卡方 / Wald（仅简单设计） | 无解析方法，完全依赖模拟 |
| **实用通用方法** | **模拟法**（任意设计可行） | **BFDA** / 后验预测模拟 |
| **样本量规划模式** | 固定 N → 达到目标 power | 固定 N 或序贯设计均可 |
| **效应量来源** | 点估计 / 文献 / 最小有意义效应 | 先验分布（可结合文献与专家知识） |
| **不确定性处理** | 仅考虑抽样误差 | 同时纳入参数不确定性（后验分布） |
| **能否序贯分析** | 不能中途看数据（p-hacking） | 天然支持序贯监控 |
| **"无效应"处理** | 仅"不拒绝 H₀" | 可提供支持 H₀ 的证据强度 |
| **主要软件** | G\*Power, R `pwr`, `WebPower`, `simr` | R `BayesFactor`, `brms`; Python PyMC |
| **学习曲线** | 较平缓 | 较陡（需 MCMC + 先验设定） |

### 选择建议

| 情境 | 推荐方法 |
|:---|:---|
| 简单 Logistic/Poisson 回归，单预测变量 | G\*Power 解析法 |
| 复杂 GLM（多变量 / 交互项） | 频率学派模拟法 |
| 希望序贯设计，节省样本量 | 贝叶斯 BFDA |
| 已有先验知识 / 历史数据 | 贝叶斯后验功效分析 |
| 需要量化"支持 H₀"的证据 | 贝叶斯（BF + ROPE） |
| 仅需传统 power 用于 grant / 伦理申请 | 频率学派模拟法 |

---

## 5. 对 SPE 实验的启示

本目录中的 [`SPE_BF_Analysis.ipynb`](./SPE_BF_Analysis.ipynb) 使用了 JZS 贝叶斯因子对 ANOVA 和线性回归进行分析。但对于 SPE 实验的完整 GLMM 功效规划，建议：

### 当前设计的局限

- 该 notebook 的 BF 计算**假设独立同分布**，未纳入被试随机效应
- 实际 DDM 参数存在层级结构（试次嵌套于被试）

### 未来改进方向

1. **频率学派路径**：R 的 `simr` 包，直接对 `lme4::lmer()` 模型做模拟功效分析
2. **贝叶斯路径**：R `brms` + BFDA 定制模拟，或对本目录的 JZS 函数进行扩展以纳入随机效应
3. **混合路径**：先用频率学派模拟法确定合理 N 范围，再用贝叶斯 BFDA 设计序贯停止规则

### 推荐参考文献

以下文献按主题分类，涵盖经典奠基论文、心理学近年方法论进展以及实用教程。

---

#### 一、经典方法论基础（频率学派 GLM/GLMM 功效分析）

- **Self, S. G., Mauritsen, R. H., & Ohara, J. (1992).** Power calculations for likelihood ratio tests in generalized linear models. *Biometrics*, 48(1), 31–39.  
  > GLM 功效分析的解析奠基之作，提出了基于似然比检验和非中心卡方近似的功效计算方法。

- **Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007).** G\*Power 3: A flexible statistical power analysis program for the social, behavioral, and biomedical sciences. *Behavior Research Methods*, 39(2), 175–191.  
  > 心理学最广泛使用的功效分析软件 G\*Power 的标志性文章，涵盖 t 检验、ANOVA、回归等多种设计。

- **Snijders, T. A. B., & Bosker, R. J. (2012).** *Multilevel Analysis: An Introduction to Basic and Advanced Multilevel Modeling* (2nd ed.). Sage.  
  > 多层模型（含 GLMM）的经典教材，为理解层级数据结构中的功效问题提供理论基础。

- **Bolker, B. M., Brooks, M. E., Clark, C. J., et al. (2009).** Generalized linear mixed models: A practical guide for ecology and evolution. *Trends in Ecology & Evolution*, 24(3), 127–135.  
  > 跨学科的 GLMM 实用指南，清晰解释了随机效应结构、连接函数与分布族的选择。

---

#### 二、贝叶斯因子与 BFDA（经典与近年发展）

- **Rouder, J. N., Speckman, P. L., Sun, D., Morey, R. D., & Iverson, G. (2009).** Bayesian t tests for accepting and rejecting the null hypothesis. *Psychonomic Bulletin & Review*, 16(2), 225–237.  
  > JZS 先验贝叶斯因子的提出论文，奠定了本目录 `SPE_BF_Analysis.ipynb` 中 t 检验 BF 的计算基础。

- **Rouder, J. N., Morey, R. D., Speckman, P. L., & Province, J. M. (2012).** Default Bayes factors for ANOVA designs. *Journal of Mathematical Psychology*, 56(5), 356–374.  
  > JZS 先验在 ANOVA 设计中的推广，是本目录 ANOVA BF 计算的核心参考文献。

- **Liang, F., Paulo, R., Molina, G., Clyde, M. A., & Berger, J. O. (2008).** Mixtures of g priors for Bayesian variable selection. *Journal of the American Statistical Association*, 103(481), 410–423.  
  > Zellner-Siow 先验与超 g 先验的理论基础，是 JZS 回归 BF 的重要前驱。

- **Schönbrodt, F. D., & Wagenmakers, E.-J. (2018).** Bayes factor design analysis: Planning for compelling evidence. *Psychonomic Bulletin & Review*, 25(1), 128–142.  
  > 提出 BFDA（贝叶斯因子设计分析）框架的里程碑论文，系统介绍了序贯 BF 设计和固定 N 设计下的功效模拟。

- **Stefan, A. M., Gronau, Q. F., Schönbrodt, F. D., & Wagenmakers, E.-J. (2019).** A tutorial on Bayes Factor Design Analysis using an informed prior. *Behavior Research Methods*, 51(3), 1042–1058.  
  > BFDA 的详细教程，重点介绍如何使用信息先验（informed prior）进行设计模拟。

- **Piray, P. (2025).** Addressing low statistical power in computational modelling studies in psychology and neuroscience. *Nature Human Behaviour*.  
  > **最新重磅论文**：揭示心理学计算建模研究中 79% 的研究功效低于 80% 标准，并开发了基于随机效应贝叶斯模型选择（Bayes factor）的功效分析框架。发现模型空间扩大会显著降低功效，固定效应模型选择的假阳性率高达 97%。

- **Moerbeek, M. (2025).** Optimal group sizes for testing group mean differences using the Bayes factor. *Journal of Applied Statistics*, 53(4), 710–728.  
  > 研究如何通过优化分组样本量来最大化贝叶斯因子，提供了 Shiny 应用工具。

---

#### 三、GLMM 模拟法功效分析（心理学近年实用进展）

- **Kumle, L., Võ, M. L.-H., & Draschkow, D. (2021).** Estimating power in (generalized) linear mixed models: An open introduction and tutorial in R. *Behavior Research Methods*, 53(6), 2528–2543.  
  > **心理学 GLMM 功效分析的标杆教程**，使用 `simr` 和 `mixedpower` R 包，覆盖了有/无先验数据、被试/刺激数规划三种场景，代码完全开源。

- **Brysbaert, M., & Stevens, M. (2018).** Power analysis and effect size in mixed effects models: A tutorial. *Journal of Cognition*, 1(1), 9.  
  > 针对心理学实验中的混合效应模型功效分析入门教程，简洁实用。

- **Green, P., & MacLeod, C. J. (2016).** SIMR: An R package for power analysis of generalized linear mixed models by simulation. *Methods in Ecology and Evolution*, 7(4), 493–498.  
  > `simr` R 包的介绍论文，该包是 `lme4` 模型模拟功效分析的标准工具。

- **Zimmer, F., & Debelak, R. (2023).** mlpwr: An R package for comprehensive power analysis and design optimization. *Psychological Methods*, 28(6), 1405–1422.  
  > `mlpwr` R 包：结合蒙特卡罗模拟与代理模型（surrogate modeling）进行多维设计参数空间的功效优化，适用于 GLMM 及多层级设计。

- **Kueppers, S., Rau, R., & Scharf, F. (2024).** Using Monte Carlo simulation to forecast the scientific utility of psychological app studies: A tutorial. *Multivariate Behavioral Research*, 59(4), 879–893.  
  > 展示如何使用蒙特卡罗模拟评估心理 APP 数据的科学效用，包括功效预估框架，对复杂数据结构的功效规划有借鉴意义。

- **He, S., & Lee, W. (2022).** Generalized linear mixed-effects models for studies using different sets of stimuli across conditions. *Frontiers in Psychology*, 13, 941234.  
  > 提出 NRI（非重复项目）设计下的 GLMM 扩展模型，通过模拟研究评估一类错误和功效，为实验心理学家提供了模型选择参考。

---

#### 四、贝叶斯 GLMM 与心理学教程

- **Kruschke, J. K. (2015).** *Doing Bayesian Data Analysis: A Tutorial with R, JAGS, and Stan* (2nd ed.). Academic Press.  
  > 贝叶斯数据分析的殿堂级教材，BEST、ROPE + HDI、贝叶斯功效分析等概念均出自本书。

- **Bürkner, P.-C. (2017).** brms: An R package for Bayesian multilevel models using Stan. *Journal of Statistical Software*, 80(1), 1–28.  
  > `brms` R 包的核心论文，该包是心理学贝叶斯 GLMM 的事实标准工具，支持多种分布族和复杂的随机效应结构。

- **潘晚坷, 温秀娟, 金海洋. (2023).** 贝叶斯混合效应模型：基于 brms 的应用教程. *心理技术与应用*, 11(10), 577–598.  
  > **中文学界实用教程**，系统介绍了用 brms 拟合贝叶斯混合效应模型，包括先验预测检验和 BF 假设检验。

- **朱训, 顾昕. (2023).** 贝叶斯因子及其应用. *心理技术与应用*, 11(9), 514–527.  
  > 中文贝叶斯因子入门教程，对心理学研究者友好。

- **王允宏, van den Bergh, D., Aust, F., et al. (2023).** 贝叶斯方差分析在 JASP 中的实现. *心理技术与应用*, 11(9), 528–541.  
  > 介绍如何在 JASP（无需编程的统计软件）中进行贝叶斯方差分析，适合不熟悉编程的心理学研究者。

- **Dora, J., McCabe, C. J., van Lissa, C. J., et al. (2024).** A tutorial on analyzing ecological momentary assessment data in psychological research with Bayesian (generalized) mixed-effects models. *Advances in Methods and Practices in Psychological Science*, 7(1).  
  > 使用贝叶斯（广义）混合效应模型分析 EMA 数据的详细教程，展示了贝叶斯 GLMM 在处理非正态结果和层级结构时的优势。

- **Alter, U., Too, M. A., & Cribbie, R. A. (2025).** Navigating the Bayes maze: The psychologist's guide to Bayesian statistics, a hands-on tutorial with R code. *International Journal of Psychology*, 60(1), e13271.  
  > **2025 年最新教程**：面向心理学家的贝叶斯统计完整指南，使用 `brms` + Stan，附带 R 代码和可复现示例。

- **Shen, Y., Psioda, M. A., & Ibrahim, J. G. (2023).** BayesPPD: An R package for Bayesian sample size determination using the power and normalized power prior for generalized linear models. *The R Journal*, 14(4), 335–351.  
  > 专用于 GLM 的贝叶斯样本量规划 R 包，支持纳入历史数据和多种分布族。

---

#### 五、DDM / 计算建模方向（与 SPE 实验高度相关）

- **Piray, P., Dezfouli, A., Heskes, T., Frank, M. J., & Daw, N. D. (2019).** Hierarchical Bayesian inference for concurrent model fitting and comparison. *PLOS Computational Biology*, 15(6), e1007043.  
  > 分层贝叶斯 DDM 模型拟合与比较的方法学论文，与你的 HDDM 分析直接相关。

- **Lee, M. D., & Wagenmakers, E.-J. (2014).** *Bayesian Cognitive Modeling: A Practical Course*. Cambridge University Press.  
  > 贝叶斯认知建模教材，涵盖 DDM、强化学习等计算模型的贝叶斯推断和模型比较。

- **Schad, D. J., Betancourt, M., & Vasishth, S. (2020).** Toward a principled Bayesian workflow in cognitive science. *Psychological Methods*, 26(1), 103–126.  
  > 认知科学中贝叶斯工作流的规范化指南，包括先验选择、MCMC 诊断和后验预测检验。

---

*最后更新：2026-06-26*
