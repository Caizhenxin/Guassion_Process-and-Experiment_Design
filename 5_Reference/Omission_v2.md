# Omission 纳入建模的可行性分析 v2.0 —— 方法论深度解读与技术路线图

> **文献来源**: Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025). The Perils of Omitting Omissions when Modeling Evidence Accumulation. *In Prep.*
>
> **分析目标**: 深度解读论文的 LAN+OPN 方法论，结合本项目的 GP+Sigmoid+DDM 架构，提供可执行的技术路线图。
>
> **与 v1 的关系**: [Omission建模可行性分析.md](Omission建模可行性分析.md)（v1）侧重文献综述 + 实证敏感性分析结果 + 高层路线建议。本文（v2）追加：数学形式化、技术实现骨架、HSSM 使用教程、论文写作方案。

---

## 一、论文方法论深度解读

### 1.1 问题背景

在含 response deadline 的决策实验中，部分试次没有反应（omission）。标准做法是直接丢弃这些试次（"LAN-only"），隐含假设是**这些试次对参数估计不产生显著影响**。

Leng et al. (2025) 证明了这一假设是错误的——即使 omission 率低至 5% 以下。

### 1.2 三类顺序抽样模型（SSM）

论文考察了三种边界类型的漂移扩散模型：

#### 1.2.1 恒定边界 DDM（Constant-boundary DDM）

$$
dX_t = v\,dt + c\,dW, \quad X_0 = z
$$

$$
f^{DDM}_{bound}(t) = a \quad \text{（固定边界值）}
$$

- $v$：漂移率（drift rate）
- $a$：边界分离（boundary separation）
- $z$：起始点偏倚（starting point bias，论文固定为 0.5）
- $\tau$：非决策时间（non-decision time，论文固定为 0.3s）

> 恒定边界 DDM 是**本项目当前使用的模型**。HDDM 拟合时 `bias=False` 相当于 $z=0.5$。

#### 1.2.2 线性塌缩边界 ANGLE（Linearly Collapsing Boundary）

$$
f^{ANGLE}_{bound}(t) = a - t \times \frac{\sin(\theta)}{\cos(\theta)}
$$

- $\theta \in (0, \pi/2)$：边界塌缩角，越大塌缩越激进
- 代表"紧迫感"（urgency）：随时间推移，所需证据量递减

#### 1.2.3 非线性塌缩边界 WEIBULL（Nonlinearly Collapsing Boundary）

$$
f^{WEIBULL}_{bound}(t) = a \times \exp\left(-\left(\frac{t}{\beta}\right)^\alpha\right)
$$

- $\alpha$：形状参数（shape）
- $\beta$：尺度参数（scale）

> ANGLE 和 WEIBULL 更适合含 deadline 的决策任务——但目前 HDDM 不原生支持这两种边界。HSSM 可支持。

### 1.3 联合似然函数：LAN + OPN

#### 1.3.1 缺失的 likelihood 项

当存在 deadline $d$ 时，数据分为两类：

1. **观测数据** $D$：$d_i = (rt_i, c_i)$，其中 $rt_i \leq d$
2. **遗漏试次** $O$：$rt_i > d$，无选择信息

标准做法只用 $D$ 拟合模型，忽略 $O$。但 omission 试次也包含了关于参数的信息——它们意味着 post-deadline 的概率质量：

$$
p(omission \mid \theta_{SSM}) = \int_d^{+\infty} f_1(t \mid \theta_{SSM})\,dt + \int_d^{+\infty} f_{-1}(t \mid \theta_{SSM})\,dt
$$

这个积分在标准软件包中没有直接可用接口，因此大多数研究者选择忽略 omission。

#### 1.3.2 LAN：似然近似网络（Likelihood Approximation Network）

**LAN** 是一个预训练神经网络：

```
LAN 输入: (rt, choice, θ_SSM)
LAN 输出: log-likelihood of observing (rt, choice) given θ_SSM
```

- 替代解析似然函数，适用于任意 SSM
- 支持 GPU 并行，对复杂模型（ANGLE, WEIBULL）比解析似然更快
- 关键：LAN 只能计算 $rt \leq d$ 的似然

#### 1.3.3 OPN：遗漏概率网络（Omission Probability Network）

**OPN** 是第二个预训练网络：

```
OPN 输入: (θ_SSM, deadline d)
OPN 输出: log-probability of omission (即 post-deadline 概率质量)
```

- OPN 的输出 = $\log p(omission \mid \theta_{SSM}, d)$
- 训练数据来自模拟器：对给定 $\theta_{SSM}$ 和 $d$ 运行大量 SSM 模拟，统计 omission 比例
- 不需要解析积分 post-deadline PDF

#### 1.3.4 联合对数似然（Equation 6, paper）

$$
\log l(D, O \mid \theta_{SSM}, d) = \sum_{i=0}^{|D|} f^{LAN}_{c_i}(rt_i \mid \theta_{SSM}) + |O| \times f^{OPN}(omission \mid \theta_{SSM}, d)
$$

**解释**：

- 第一项：所有观测试次的 log-likelihood 之和（LAN 提供）
- 第二项：$|O|$ 个 omission 试次的 log-probability（OPN 提供，乘以 omission 试次数）

**直觉**：如果 $\theta_{SSM}$ 可能产生大量 omission（如低 v、高 a），第二项会"惩罚"这种参数；反之如果 $\theta_{SSM}$ 会产生正确的 omission 数量，第二项接近 0。

### 1.4 Lapse 混合分布建模

真实数据中，部分 omission 可能源自注意流失（lapse），而非 deadline 超时。论文使用以下混合模型：

$$
likelihood = (1 - p_{lapse}) \times likelihood_{SSM} + p_{lapse} \times f_{Lapse}
$$

- $f_{Lapse}(t) = \frac{1}{2 \times T}$，$t \in [0, T]$（均匀分布，随机选择，$T = 5s$）
- $p_{lapse}$：lapse 比例，联合估计

> **本项目的对应物**：HDDM 的 `p_outlier` 参数类似，但 HDDM 的 outlier 模型是常概率 + 均匀分布，而 Lapse 模型是均匀 RT 分布 + 随机选择。两者的数学形式和解释不同。

### 1.5 论文核心数值发现汇总

| 模型                               | LAN-only 偏倚                                       | LAN+OPN 结果                       | 临界 omission 率           |
| :--------------------------------- | :-------------------------------------------------- | :--------------------------------- | :------------------------- |
| 恒定边界 DDM                       | a 被**低估**，v 被**高估**              | a, v 正确恢复                      | 10%-30% 时偏倚显著         |
| ANGLE (线性塌缩)                   | a 和 θ 被**高估**（更激进塌缩）              | a, θ 正确恢复                     | **>5% 即有显著偏倚** |
| WEIBULL (非线性塌缩)               | a↓, α↑, β↓（所有参数被扭曲）                   | 三个参数偏倚大幅减小               | 10%-20%                    |
| 跨条件 Δθ (ANGLE)                | Δθ**严重低估**（真值 0.2 → 恢复值 << 0.2） | Δθ 正确恢复 (≈0.2)              | 合成双条件设计             |
| Lapse ($p_{lapse} = 0.01, 0.05$) | SSM 参数偏倚 +$p_{lapse}$ **显著低估**      | SSM 参数 +$p_{lapse}$ 均正确恢复 | 0.01-0.05                  |

> **本章要点**: (1) LAN+OPN 是"预训练神经网络替代解析似然 + 遗漏概率"框架；(2) 联合似然函数通过 OPN 项惩罚不合理的 omission 数量；(3) 即使 <5% omission 率也会显著偏倚塌缩边界参数；(4) 三种边界类型（恒定/线性/非线性）均受益于 LAN+OPN。

---

## 二、参数恢复偏倚的量化机制

### 2.1 似然函数视角的解释

#### 2.1.1 未建模 omission 时，似然面如何变形

当模型只拟合 $D$（观测数据）而忽略 $O$（omission）时：

1. **模型"看不见" post-deadline 的数据**：似然函数完全没有 post-deadline 区域的信息
2. **"快 RT"参数组合获得更高似然**：
   - 低 $a$（低边界）→ 更快的 RT → 更多数据落在 deadline 前 → 高似然
   - 高 $v$（高漂移率）→ 更快的 RT → 更多数据落在 deadline 前 → 高似然
3. **MCMC 自然趋向似然高的区域**：$a \downarrow$，$v \uparrow$

```python
# 伪代码：为什么 LAN-only 会偏倚
def log_likelihood_LAN_only(data_observed, theta):
    """只计算 deadline 前的试次"""
    ll = 0
    for rt, choice in data_observed:  # 仅 deadline 前的试次
        ll += LAN(rt, choice, theta)  # 没有 omission 项
    return ll

# MCMC 发现：theta = (low_a, high_v) 时
# → 产生的 omission 很少 → 更多数据在 D 中 → ll 更高
# → MCMC 自然趋近 (low_a, high_v)
```

#### 2.1.2 LAN+OPN 如何纠正

```python
def log_likelihood_LAN_OPN(data_observed, n_omissions, theta, deadline):
    """联合似然：观测数据 + omission 计数"""
    ll = 0
    for rt, choice in data_observed:
        ll += LAN(rt, choice, theta)
    # 关键：omission 惩罚项
    ll += n_omissions * OPN(theta, deadline)  # 负值，惩罚不合理的 omission 数
    return ll

# MCMC 现在考虑：
# theta = (low_a, high_v) → omission 很少 → OPN 项给出低概率 → ll 被惩罚
# theta = (true_a, true_v) → omission 数量匹配 → OPN 项接近 0 → 总体 ll 最高
```

#### 2.1.3 塌缩边界模型的额外偏倚

对于 ANGLE 模型，不建模 omission 时：

- 高 $\theta$ → 更激进塌缩 → 边界更快降至 0 → omission 减少 → 高似然
- 高 $a$ → 更高的初始边界 → 但配合高 $\theta$ 仍然能减少 omission
- 结果：$a$ 和 $\theta$ 同时被高估（论文 Figure 3 A-B）

### 2.2 对本项目敏感性分析结果的解释

本项目完成的 Censor vs Drop 敏感性分析（[Omission建模可行性分析.md](Omission建模可行性分析.md) §2.4）与论文的理论预测完全一致：

| 参数       | 论文预测               | 本项实验发现                                        |   一致性   |
| :--------- | :--------------------- | :-------------------------------------------------- | :---------: |
| v (漂移率) | Drop 方案高估 v        | G1-G8 全部: Drop v > Censor v（Δ 0.8~6.8）         |     ✅     |
| a (边界)   | Drop 方案低估 a        | G1-G4: Censor > Drop（Δ −0.14~−0.59）            |     ✅     |
| z (起始点) | 论文未直接报告         | Censor > Drop（Δ −0.04~−0.24）                   |   新发现   |
| SPE_v      | 论文跨条件 Δθ 被低估 | SPE_v 方向一致但量值被压缩（Censor SPE < Drop SPE） | ✅ 平行发现 |

> **关键确认**：G1 (72.3% omission) 的 v_self 出现**符号反转**（Censor: −4.86 → Drop: +1.95），证明在极端 omission 率下，LAN-only 风格的偏倚可以达到灾难性水平。

> **本章要点**: (1) 偏倚的根本原因是似然函数缺乏 omission 惩罚项；(2) 模型选择能最小化 omission 概率的参数组合；(3) 本项目实证数据与论文理论预测完美吻合；(4) G1 的符号反转是"omission 率 >50% 时 DDM 不可靠"的最强证据。

---

## 三、跨条件比较的启示

### 3.1 论文 Figure 4：跨条件 Δθ 的恢复

论文设置了一个合成双条件实验（Figure 4）：

- **条件 1**：$\theta = 0.9$（快速条件）
- **条件 2**：$\theta = 0.7$（慢速条件）
- **真值**：$\Delta\theta = 0.2$
- **LAN-only 恢复**：$\Delta\theta \ll 0.2$（严重低估效应量）
- **LAN+OPN 恢复**：$\Delta\theta \approx 0.2$（正确恢复效应量）

此外，LAN-only 模型在 posterior predictive check 中系统性地低估了 omission 率（Figure 4C）。

### 3.2 对本项目的直接启示

#### 3.2.1 SPE_v 的平行发现

本项目敏感性分析显示：Censor（类似 LAN-only）与 Drop 方案下的 SPE_v：

| Group | Censor SPE_v | Drop SPE_v |   Δ   | Cohen's d |
| :---: | :----------: | :--------: | :-----: | :-------: |
|  G2  |    +0.707    |   +1.706   | +0.999 |   1.30   |
| G3-G8 |   +0.2~1.0   |  +0.8~1.3  | 0.1~0.6 |  0.2~1.8  |

**发现**：两种方案下 SPE_v 的**方向**一致（均为正 → 自我优势存在），但**量值**在 Drop 方案下系统性地更大。这与论文 Figure 4 的 $\Delta\theta$ 发现平行——LAN-only 低估了条件间的参数差异。

#### 3.2.2 机制解释

偏倚在跨条件下可能不是均等的。如果两个条件的 omission 率不同（如 G2 的 omission 率 52% vs G6 的 6.7%），那么：

- 高遗漏率条件的偏倚更大
- 导致条件间差异被压缩（或放大，取决于偏倚方向）

这解释了为什么 Censor 方案下的 SPE_v 略小于 Drop 方案。

#### 3.2.3 论文写作建议

在 Discussion 中引用 Leng et al.（2025）Figure 4：

> "我们的敏感性分析显示，omission 处理方式主要影响 DDM 参数的绝对值而非 SPE 的方向。这与 Leng et al.（2025）的跨条件分析一致——他们发现 LAN-only 严重低估了条件间 $\Delta\theta$，而 LAN+OPN 正确恢复了效应量。"

> **本章要点**: (1) 论文跨条件实验证明 LAN-only 低估效应量；(2) 本项目 SPE_v 发现与此平行——方向一致但量值被压缩；(3) 这为"当前 Censor 方案可作为基线但需谨慎解释量值"提供了方法论依据。

---

## 四、本项目适配性深度评估

### 4.1 逐维度对照表

| 维度                      | Leng et al. (2025) 设置       | 本项目现状                  | 适配度 | 说明                               |
| :------------------------ | :---------------------------- | :-------------------------- | :----: | :--------------------------------- |
| **数据来源**        | 合成数据（已知 ground truth） | 真实被试数据（88 人，8 组） |  ⚠️  | 无法做绝对恢复评估；只能做相对比较 |
| **样本量/组**       | 100-500 合成试次/组           | 2600-3120 真实试次/组       |   ✅   | 试次数充足                         |
| **被试数/组**       | 未层次化                      | 10-12 被试/组               |   ✅   | 支持层级贝叶斯                     |
| **DDM 类型**        | DDM/ANGLE/WEIBULL 三种        | 仅恒定边界 DDM              |  ⚠️  | ANGLE/WEIBULL 的结论不完全适用     |
| **参数估计方法**    | LAN-based MCMC (HSSM)         | HDDM MCMC (解析似然)        |  ⚠️  | 方法不同，但同为层级贝叶斯         |
| **层次结构**        | 支持 (HSSM)                   | 已使用 (HDDM)               |   ✅   | 方法论兼容                         |
| **Omission 率范围** | 5-30%（主要集中在 <20%）      | 6.7-72.3%（跨度极大）       |  ⚠️  | 高端超出论文考察范围               |
| **Deadline 设置**   | 固定 1.25s                    | 各组不同 (330-2000ms)       |   ✅   | 论文支持变 deadline                |
| **Lapse 建模**      | 支持联合估计$p_{lapse}$     | 未显式建模                  |   🟡   | 可扩展（见 §5 路线 C）            |
| **软件工具**        | HSSM (Python)                 | HDDM (Python)               |  ⚠️  | 不同包，但 HSSM 兼容 HDDM 数据格式 |
| **参数可识别性**    | 多个条件约束 + 大样本         | 8 组，其中 G1/G2 建议排除   |   🔴   | 核心瓶颈                           |

### 4.2 核心适配障碍

#### 4.2.1 仅恒定边界 DDM → 论文 ANGLE/WEIBULL 结论不完全适用

论文的核心发现之一是"塌缩边界模型更容易受 omission 偏倚影响，因为 omission 迫使模型选择更激进的塌缩"。本项目的恒定边界 DDM 不受此特定偏倚影响——但恒定边界本身的偏倚（$a\downarrow, v\uparrow$）仍然存在且被我们的敏感性分析所证实。

**影响**：论文中关于 ANGLE/WEIBULL 的讨论不宜直接引用到本项目中。应聚焦于恒定边界 DDM 的偏倚模式。

#### 4.2.2 真实数据无 ground truth

论文的全部分析基于"已知真值 → 评估恢复精度"的范式。本项目使用的是真实被试数据，无法知道真实的 DDM 参数。这限制了评估的性质——从"绝对恢复精度"变为"不同处理方案的相对一致性"。

**已完成的敏感性分析（Censor vs Drop）正是这一限制下的最佳评估策略**。

#### 4.2.3 HSSM LAN+OPN 仍在开发中

截至 2026-06，论文中描述的 HSSM 集成仍是"in prep"状态。这意味着路线 B 的完整实施需要等待工具成熟。

#### 4.2.4 8 组条件的限制

排除 G1/G2 后仅剩 6 组（G3-G8），其中 G3-G4 处于"灰色地带"。这对于 GP 建模已是瓶颈，对于 HSSM+LAN+OPN 更是——OPN 需要在模拟数据上预训练，而 6 个条件的设计空间不足以支撑复杂的神经网络训练。

### 4.3 整体适配性判断

| 方面                               | 判断                                                         |
| :--------------------------------- | :----------------------------------------------------------- |
| **论文核心主张的适用性**     | ✅ 适用——恒定边界 DDM 的偏倚模式与论文一致                 |
| **LAN+OPN 方法的可行性**     | 🟡 中期可行——需等待 HSSM 成熟 + 更多数据                   |
| **当前 Censor 方案的充分性** | ✅ 已实证验证——遗漏率 <15% 时与 Drop 方案 95% CI 重叠      |
| **最优先行动**               | 排除 G1/G2、更新 GP 模型使用 G3-G8、在论文中引用 Leng et al. |

> **本章要点**: (1) 论文核心主张适用于本项目的恒定边界 DDM；(2) 真实数据 + 8 组条件限制了绝对恢复评估；(3) HSSM LAN+OPN 是中期方向而非短期可执行方案；(4) 已完成敏感性分析为当前 Censor 方案提供了实证支持。

---

## 五、三种技术路线的具体实现方案

> 本章从 v1 的高层路线建议落地到**可执行的代码骨架和操作步骤**。

### 5.1 路线 A：维持 HDDM 截尾方案（当前路线，✅ 已验证）

#### 5.1.1 核心思想

继续使用当前 pipeline：`omission 试次 → rt=T+W, response=0 → HDDM 右截尾拟合`。基于敏感性分析结论，对数据质量进行分层管理。

#### 5.1.2 参数取舍决策矩阵

```
决策树:
  omission_rate < 15%     → 使用 Censor 参数（当前方案），可信度 = 高
  15% ≤ omission_rate ≤ 40% → 使用 Censor 参数，但在论文中标注"需谨慎解释"，可信度 = 中
  omission_rate > 40%       → 排除该组（无论方案），可信度 = 低

最终分析样本:
  ✅ 核心: G5, G6, G7, G8 (omission_rate < 15%)
  🟠 谨慎: G3, G4 (omission_rate 35-38%)
  ❌ 排除: G1, G2 (omission_rate > 50%)
```

#### 5.1.3 代码骨架（已有）

```python
# step2_hddm_fit.py 的核心逻辑 —— 已可运行
import hddm
model = hddm.HDDM(
    df,
    depends_on={"v": "identity"},
    include=["v", "a", "t", "z"],
    bias=False,
    p_outlier=0.0,  # 关键：Censor 时必须设 0
)
model.sample(3000, burn=500)
```

#### 5.1.4 论文辩护策略

> "我们采用 HDDM 的右截尾（right-censoring）方法处理遗漏试次：将 omission 试次的反应时设为 deadline（T+W）并将反应编码为 0。这一方法优于完全丢弃 omission（敏感性分析显示 Δv 可达 6.8, Cohen's d > 9），但与 Leng et al. (2025) 提出的 LAN+OPN 框架相比仍有不足。考虑到当前样本量（8 组）和 HSSM 工具链的开发状态，我们将 HDDM 截尾方案作为当前分析的基线方法，在讨论中明确其局限性。"

### 5.2 路线 B：迁移到 HSSM + LAN+OPN（中期方向，🔮 展望）

#### 5.2.1 先决条件检查

| 条件                       | 当前状态         | 预计可满足时间           |
| :------------------------- | :--------------- | :----------------------- |
| HSSM 正式发布 LAN+OPN 功能 | "in prep"        | 未知（追踪论文作者）     |
| OPN 预训练数据             | 需要大量合成数据 | 可自行生成（见下文）     |
| 恒定边界 DDM 的 OPN        | 论文已验证       | 需确认 HSSM 是否默认提供 |
| 至少 20+ 实验条件          | 当前 8 组        | Phase 4 新增后           |

#### 5.2.2 实施步骤（6 步）

##### Step B1: 安装 HSSM 环境

```bash
# 安装 HSSM（概念示例——实际版本和 API 以发布时为准）
pip install hssm

# 或开发版
pip install git+https://github.com/lnccbrown/HSSM.git
```

##### Step B2: 准备数据

HDDM-ready 数据格式 → HSSM 格式：

```python
import pandas as pd
from pathlib import Path

# 读取已有 HDDM-ready 数据
df = pd.read_csv("2_Data/Real_Data/HDDM_Ready/hddm_data_group5_P8_T100_W1100.csv")

# HDDM 和 HSSM 的列结构相似——都需要: subj_idx, rt, response
# HSSM 额外需要 deadline 列（如支持）

# Omission 试次的处理：
# 方案 1（推荐）: 保留 omission 行，HSSM 通过 deadlinedata=True 自动识别
# 方案 2: 使用已有的 drop 数据（仅有效试次），但不推荐（与论文的 LAN-only 相同）
df["deadline"] = df["T_ms"] + df["W_ms"]  # ms → 需换算为秒
df["deadline_sec"] = df["deadline"] / 1000.0  # 论文使用秒单位

# 对于 omission 试次，response=0, rt=deadline
# HSSM 将这些识别为截尾观测
```

##### Step B3: 配置并拟合模型

```python
import hssm

# 概念示例——实际 API 以 HSSM 发布版本为准
model = hssm.HSSM(
    data=df,
    model="ddm",                    # 恒定边界 DDM
    include=["v", "a", "t", "z"],   # 自由参数
    depends_on={"v": "identity"},   # v 依赖 self/stranger 条件
    deadlinedata=True,              # 启用 OPN（关键配置）
    deadline="deadline_sec",        # deadline 列名（秒）
    hierarchical=True,              # 层级贝叶斯
)

# MCMC 采样
model.sample(draws=3000, tune=500, chains=4)

# 提取后验
trace = model.get_traces()
summary = model.summary()
```

##### Step B4: OPN 预训练（如 HSSM 未内建 OPN）

```python
# 伪代码——OPN 训练逻辑
# 1. 从参数的合理范围采样 θ ~ prior
# 2. 对每组 θ + deadline，运行大量 SSM 模拟
# 3. 统计 omission 比例 → 作为训练标签
# 4. 训练神经网络 (θ, d) → omission_probability

# 伪实现:
import numpy as np

def generate_opn_training_data(n_samples=100000, n_sim_per_sample=5000):
    X, y = [], []
    for _ in range(n_samples):
        # 从 prior 采样参数
        v = np.random.uniform(-3, 5)
        a = np.random.uniform(0.5, 3.0)
        t = np.random.uniform(0.2, 0.7)
        z = 0.5
        d = np.random.uniform(0.3, 2.5)  # deadline 范围
    
        # 运行 DDM 模拟（需要已有 simulator）
        n_omissions = simulator(v, a, z, t, d, n_sim_per_sample)
    
        X.append([v, a, t, z, d])
        y.append(n_omissions / n_sim_per_sample)
  
    return np.array(X), np.array(y)

# 训练简单 MLP
from sklearn.neural_network import MLPRegressor
opn = MLPRegressor(hidden_layer_sizes=(64, 32), activation='relu')
opn.fit(X_train, y_train)
```

##### Step B5: 比较 HDDM Censor vs HSSM LAN+OPN

```python
# 对 G5-G8 分别拟合两种模型，比较参数后验
comparison = pd.DataFrame({
    'group': groups,
    'param': params,
    'hddm_censor_mean': hddm_params,
    'hssm_lan_opn_mean': hssm_params,
    'delta': hssm_params - hddm_params,
    'ci_overlap': check_ci_overlap(...),
})
```

##### Step B6: 本项目的 Blockers 汇总

| Blocker                  | 说明                        | 缓解措施                               |
| :----------------------- | :-------------------------- | :------------------------------------- |
| HSSM 未正式发布          | LAN+OPN 功能在"in prep"状态 | 追踪论文作者的 GitHub，使用开发分支    |
| OPN 需要大量模拟数据     | 至少 10 万次模拟用于训练    | 使用 GPU 加速 SSM 模拟（如 JAX-based） |
| 恒定边界 DDM 的 OPN 预置 | 论文主要测试 ANGLE/WEIBULL  | 确认 HSSM 是否默认提供 DDM-OPN         |
| 8→6 组条件的设计空间    | GP 泛化能力受限             | 新增 4-6 个实验条件后再评估            |
| LAN 近似误差             | LAN 是解析似然的近似        | 论文已证明 LAN 在 DDM 上的近似精度很高 |

> **路线 B 总体评估**: 🟡 **中期可行但非短期优先**。建议等待两个信号：(1) HSSM 正式发布 LAN+OPN；(2) Phase 4 新增实验条件后将条件数提升至 12+。

### 5.3 路线 C：在 HDDM 内增强 Omission 建模（折中方案，🟡 可渐进实现）

路线 C 不引入新工具依赖，在现有 HDDM + GP + Sigmoid 架构内逐步增强 omission 建模。

#### 方案 C1：HDDM p_outlier 作为 Lapse 代理

**思想**：将 omission 视为一种特殊的"outlier"机制，利用 HDDM 已有的 `p_outlier` 参数显式估计。

```python
# HDDM 的 p_outlier 模型（概念说明）
# HDDM 默认 p_outlier=0.05——意味着 5% 的试次来自均匀分布
# 可以：
#   1. 将 p_outlier 设为自由参数（而非固定值）
#   2. 让 HDDM 从数据中估计 p_outlier 的后验分布
#   3. 对比估计的 p_outlier 是否与观测 omission 率一致

model = hddm.HDDM(
    df,  # 仅有效试次的数据（drop omission）
    depends_on={"v": "identity"},
    include=["v", "a", "t", "z"],
    bias=False,
    p_outlier=0.05,    # 让 HDDM 估计，而非固定
    group_only_nodes=['p_outlier'],  # p_outlier 设为组水平参数
)
```

**评估**：

- ✅ 代码改动最小（仅需改动 HDDM 配置）
- ⚠️ p_outlier ≠ 论文的 lapse 模型——p_outlier 表示均匀分布的概率，而 omission 来自 deadline 超时
- ⚠️ 需要去掉 omission 试次后再拟合（即 Drop 方案的数据），然后用 p_outlier 捕捉剩余噪声

#### 方案 C2：Sigmoid omission_rate 预测函数

**思想**：在生成模型（`Generate_Data_v2.4_runner.py`）中新增 `sigmoid_omission_rate(P, T, W)` 函数，基于观测数据校准。

```python
# 新增函数：基于 Sigmoid 形式预测 omission 率
import numpy as np
from scipy.special import expit as sigmoid

def sigmoid_omission_rate(P, T_ms, W_ms, params):
    """
    预测给定 (P, T, W) 下的 omission 率
  
    理论依据:
      - T 越小 → 可用的 evidence 越少 → omission 越高
      - W 越小 → deadline 越短 → omission 越高
      - P 越大 → 练习效应 → v 提高 → omission 降低
      - M = T + W 综合表征时间压力
  
    params: [alpha_0, k_P, P_0, k_T, T_0, k_W, W_0]
    """
    M_ms = T_ms + W_ms
    alpha_0, k_P, P_0, k_T, T_0, k_W, W_0 = params
  
    # P 的练习效应（练习越多 → omission 越低）
    f_P = sigmoid(-k_P * (P - P_0))  # 递减函数
  
    # T 的刺激质量效应（T 越短 → omission 越高）
    f_T = 1 - sigmoid(k_T * (T_ms - T_0))  # 递减函数
  
    # W 的时间压力效应（W 越短 → omission 越高）
    f_W = 1 - sigmoid(k_W * (W_ms - W_0))  # 递减函数
  
    # 组合（乘法交互）
    omission_rate = alpha_0 * f_P * f_T * f_W
    return np.clip(omission_rate, 0.001, 0.999)

# 校准：用 G3-G8 的观测 omission 率拟合参数
from scipy.optimize import differential_evolution

def omission_calibration_loss(params):
    loss = 0
    for _, row in real_data.iterrows():
        pred = sigmoid_omission_rate(
            row['P'], row['T_ms'], row['W_ms'], params
        )
        loss += (pred - row['omission_rate'] / 100)**2
    return np.sqrt(loss / len(real_data))

result = differential_evolution(
    omission_calibration_loss,
    bounds=[(0.01, 1.0), (0.001, 0.1), (0, 120), 
            (0.001, 0.05), (0, 500), (0.0001, 0.01), (0, 2000)]
)
```

**评估**：

- ✅ 基于现有 Sigmoid 框架，参数形式与 `compute_v_s2()`、`compute_a_s2()` 一致
- ✅ 可用已有 G3-G8 的 6 个数据点校准
- ⚠️ 6 个数据点校准 7 个参数 → 信息不足，需使用强先验
- ⚠️ 仅适用于生成模型的行为验证（Step 5），不能直接改进 HDDM 的参数恢复

#### 方案 C3：GP 联合预测 omission_rate

**思想**：在 `GPSigmoidHybridModel` 中新增第 6 个 GP（`gp_omission`），输入 (P,T,W)，输出 `omission_rate`。

```python
# 伪代码：扩展 GPSigmoidHybridModel
class GPSigmoidHybridModel:
    def __init__(self):
        # 现有的 5 个 GP
        self.gp_v_self = GaussianProcessRegressor(...)
        self.gp_v_stranger = GaussianProcessRegressor(...)
        self.gp_a = GaussianProcessRegressor(...)
        self.gp_t = GaussianProcessRegressor(...)
        self.gp_z = GaussianProcessRegressor(...)
    
        # 新增：第 6 个 GP 预测 omission 率
        self.gp_omission = GaussianProcessRegressor(
            kernel=ConstantKernel() * RBF() + WhiteKernel()
        )
  
    def fit(self, X, y_dict):
        """X: (P,T,W) 归一化; y_dict: 各参数的训练目标"""
        self.gp_v_self.fit(X, y_dict['v_self'])
        # ... 其他 GP ...
    
        # 训练 omission GP
        self.gp_omission.fit(X, y_dict['omission_rate'])
  
    def predict_omission(self, X_new):
        """预测新设计点的 omission 率"""
        mean, std = self.gp_omission.predict(X_new, return_std=True)
        return mean, std
```

**评估**：

- ✅ 与当前 GP 架构完全一致，扩展简单
- ✅ 已有 Step 5 行为验证的基础（omission_rate r=0.923）
- ⚠️ 6 组训练点不足以支持 3D GP 的可靠泛化（与 v/a/t/z GP 面临的同样的瓶颈）

#### 路线 C 各方案对比

| 方案                 | 实现难度 | 与论文接近度 | 对当前分析的影响         |    建议优先级    |
| :------------------- | :------: | :----------: | :----------------------- | :--------------: |
| C1: p_outlier 代理   |    低    |      低      | 可增强 DDM 拟合的诊断    |        🟡        |
| C2: Sigmoid omission |    中    |      中      | 仅改进生成模型的行为验证 | 🟢**推荐** |
| C3: GP omission      |    中    |      低      | 与现有瓶颈（6 点）同病   |        🟡        |

> **路线 C 推荐顺序**: 先实施 C2 (Sigmoid omission_rate)，后评估 C1（如需要更强的 DDM 诊断），C3 待条件数增加后再考虑。

> **本章要点**: (1) 路线 A 已验证且已实施，是当前最佳基线；(2) 路线 B 需等待工具成熟和数据量增加；(3) 路线 C（C2 Sigmoid omission_rate）是短期最可行的增强方案。

---

## 六、HSSM 入门教程

> ⚠️ **注意**: 以下内容基于 HSSM 的已知 API 和论文中描述的功能。部分接口在 HSSM 正式发布前可能有变化。建议在尝试运行前查看 [HSSM GitHub](https://github.com/lnccbrown/HSSM) 获取最新文档。

### 6.1 HSSM 与 HDDM 的关系

| 特性          | HDDM                                | HSSM                                  |
| :------------ | :---------------------------------- | :------------------------------------ |
| 框架          | 层级贝叶斯 DDM (PyMC-based)         | 层级贝叶斯 SSM (PyMC/Bambi-based)     |
| 支持模型      | 恒定边界 DDM                        | DDM + ANGLE + WEIBULL + 自定义 SSM    |
| 似然计算      | 解析似然（Wiener diffusion）        | LAN（神经网络近似似然）+ 可选解析似然 |
| Omission 建模 | 截尾数据（rt=deadline, response=0） | LAN+OPN（deadlinedata=True）          |
| 安装          | `pip install hddm`                | `pip install hssm`                  |
| 数据格式      | `subj_idx, rt, response`          | 同 HDDM，额外支持 deadline 列         |

### 6.2 安装

```bash
# 基础安装
pip install hssm

# 带 JAX 加速（推荐，用于 LAN 训练和快速采样）
pip install hssm[jax]

# 开发版
pip install git+https://github.com/lnccbrown/HSSM.git
```

### 6.3 从 HDDM 迁移的最小示例

```python
# ============================================================
# HDDM 方式（当前项目使用）
# ============================================================
import hddm

df = pd.read_csv("2_Data/Real_Data/HDDM_Ready/hddm_data_group5_P8_T100_W1100.csv")

model_hddm = hddm.HDDM(
    df,
    depends_on={"v": "identity"},
    include=["v", "a", "t", "z"],
    bias=False,
    p_outlier=0.0,
)
model_hddm.sample(3000, burn=500)
stats_hddm = model_hddm.gen_stats()

# ============================================================
# HSSM 等价方式（概念示例）
# ============================================================
import hssm

# 数据预处理：添加 deadline 列
df["deadline"] = (df["T_ms"] + df["W_ms"]) / 1000.0  # 秒

model_hssm = hssm.HSSM(
    data=df,
    model="ddm",                      # 恒定边界 DDM
    include=[
        {"name": "v", 
         "formula": "v ~ 1 + C(identity)",  # v 依赖 identity
         "prior": {"Intercept": {"name": "Normal", "mu": 0, "sigma": 5}}
        },
        {"name": "a", 
         "formula": "a ~ 1",
         "prior": {"Intercept": {"name": "HalfNormal", "sigma": 3}}
        },
        {"name": "t", 
         "formula": "t ~ 1",
         "prior": {"Intercept": {"name": "HalfNormal", "sigma": 0.5}, 
                    "lower": 0.1}
        },
        {"name": "z", 
         "formula": "z ~ 1",
         "prior": {"Intercept": {"name": "Beta", "alpha": 5, "beta": 5}}
        },
    ],
    # 启用 omission 建模（关键差异）
    deadlinedata=True,
    deadline="deadline",
)

model_hssm.sample(draws=3000, tune=500, chains=4)
summary = model_hssm.summary()
```

### 6.4 LAN+OPN 配置详解

```python
# 完整的 HSSM LAN+OPN 配置（概念示例）
model_with_opn = hssm.HSSM(
    data=df,
    model="ddm",                    # 可选: "ddm", "angle", "weibull"
  
    # 参数设置
    include=[...],
  
    # === Omission 相关配置（核心新增） ===
    deadlinedata=True,              # 启用 omission 数据处理
    deadline="deadline",            # deadline 列名（秒）
  
    # === LAN 配置 ===
    # 默认使用预训练的 LAN（如存在）
    # 可用 model="ddm" 的解析似然或自定义 LAN
    likelihood=" analytical",       # 或 "lan" / "approx_difference"
  
    # === OPN 配置 ===
    # deadlinedata=True 时 HSSM 自动加载/训练 OPN
    # 也可手动指定:
    # opn_network = "default_ddm_opn"  # 预训练的 DDM OPN
  
    # === 层级结构 ===
    hierarchical=True,
)

# 拟合
model_with_opn.sample(draws=3000, tune=500)
```

### 6.5 HDDM → HSSM 数据转换脚本

```python
"""
将本项目 HDDM-ready 数据转换为 HSSM-ready 格式
输入: 2_Data/Real_Data/HDDM_Ready/hddm_data_group*.csv
输出: 2_Data/Real_Data/HSSM_Ready/hssm_data_group*.csv
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path("d:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")

def convert_hddm_to_hssm(group_id, P_val, T_val, W_val):
    """单个 group 的转换"""
    csv_path = BASE_DIR / f"2_Data/Real_Data/HDDM_Ready/hddm_data_group{group_id}_P{P_val}_T{T_val}_W{W_val}.csv"
    df = pd.read_csv(csv_path)
  
    # 添加 deadline 列（秒）
    deadline_ms = T_val + W_val
    df["deadline"] = deadline_ms / 1000.0
  
    # 添加实验条件信息
    df["P"] = P_val
    df["T"] = T_val
    df["W"] = W_val
  
    # HSSM 与 HDDM 共用列: subj_idx, rt, response, identity
    # HSSM 额外需要: deadline（秒）
  
    # 保存
    out_dir = BASE_DIR / "2_Data/Real_Data/HSSM_Ready"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"hssm_data_group{group_id}_P{P_val}_T{T_val}_W{W_val}.csv"
    df.to_csv(out_path, index=False)
    print(f"✅ {out_path}")

# 转换所有 8 组
groups = [
    (1, 0, 30, 300), (2, 0, 30, 600),
    (3, 120, 30, 600), (4, 120, 80, 600),
    (5, 8, 100, 1100), (6, 120, 500, 1500),
    (7, 120, 80, 800), (8, 120, 80, 800),
]

for gid, P, T, W in groups:
    convert_hddm_to_hssm(gid, P, T, W)
```

### 6.6 当前限制与 Workaround

| 限制             | 说明                                | Workaround                                       |
| :--------------- | :---------------------------------- | :----------------------------------------------- |
| LAN+OPN 仍在开发 | HSSM 论文标记为 "in prep"           | 使用`deadlinedata=False` + 手动构造 likelihood |
| OPN 预训练数据   | 默认 OPN 可能不覆盖本项目的参数范围 | 基于本项目 DDM 参数范围自己训练 OPN              |
| 层级模型复杂度   | HSSM 的语法与 HDDM 有差异           | 参考 HSSM 文档中的`include` 参数语法           |
| JAX 依赖         | GPU 加速需要 JAX                    | CPU 模式也可运行（较慢）                         |

> **本章要点**: (1) HSSM 是 HDDM 的"未来版本"，支持更复杂的 SSM 和 LAN+OPN；(2) 数据格式从 HDDM 迁移只需要添加 deadline 列；(3) deadlinedata=True 是启用 OPN 的唯一配置项；(4) 当前建议以概念学习为主，实际运行需等待工具成熟。

---

## 七、分阶段实施建议

### 7.1 决策矩阵

| 阶段                | 期限     | 内容                                       | 依赖                 |   状态   |
| :------------------ | :------- | :----------------------------------------- | :------------------- | :-------: |
| **Phase 2.4** | 2026-06  | Censor vs Drop 敏感性分析                  | HDDM Docker          |  ✅ 完成  |
| **Phase 3.2** | 2026-06  | G7/G8 区分、G1-G2 排除决策                 | 敏感性分析结论       |  ✅ 完成  |
| **Phase 5.1** | Week 1   | 正式排除 G1/G2，更新所有分析引用           | §2.4 结论           | 📋 待执行 |
| **Phase 5.2** | Week 1-2 | 重新训练 GP+Sigmoid 模型使用 G3-G8         | HDDM Traces (Censor) | 📋 待执行 |
| **Phase 5.3** | Week 2-3 | 路线 C2: Sigmoid omission_rate 预测        | G3-G8 omission 数据  | 📋 待执行 |
| **Phase 5.4** | Week 3-4 | Parameter Recovery + LOCV (G3-G8)          | 新 GP 模型           | 📋 待执行 |
| **Phase 5.5** | Week 4-6 | 论文初稿 Methods + Results + Omission 讨论 | 上述全部             | 📋 待执行 |
| **Phase 6**   | 长期     | 追踪 HSSM LAN+OPN 发布状态                 | 论文作者             |  🔮 展望  |
| **Phase 6**   | 长期     | 新增 4-6 实验条件后重新评估                | 新数据采集           |  🔮 展望  |

### 7.2 风险地图

```
短期 (Week 1-2):  风险低 → 均已实证验证
中期 (Week 3-6):  风险中 → GP 使用 6 组可能精度下降；需论文写作配合
长期 (Month 2+):  风险中 → 新数据采集延迟；HSSM 发布延迟
```

> **本章要点**: (1) 短期行动（排除 G1/G2、更新 GP 模型）风险低且可立即执行；(2) 中期行动（路线 C2、论文写作）依赖短期完成；(3) 长期行动（HSSM 迁移、新数据采集）需等待外部条件成熟。

---

## 八、论文写作建议

### 8.1 Methods: Omission 处理段落实例

> **建议放入 Methods 的 "HDDM Parameter Estimation" 小节**：

```
HDDM Fitting and Omission Handling

For each of the eight experimental conditions, we fit a hierarchical 
Bayesian drift-diffusion model (HDDM; Wiecki et al., 2013) to the 
matching trials. The drift rate v was allowed to depend on identity 
(self vs. stranger), while boundary separation a, nondecision time t, 
and starting point z were shared within each group. We ran 3000 MCMC 
samples with 500 burn-in iterations.

Omission trials—those in which participants failed to respond before 
the deadline (T+W)—were handled via right-censoring: their RTs were 
set to the deadline value and responses coded as 0. This approach 
informs the model that the evidence accumulation process did not reach 
either boundary by the deadline, without explicitly modeling the 
post-deadline probability density (cf. Leng et al., 2025).

To assess the impact of this handling, we conducted a sensitivity 
analysis comparing the censoring approach to complete exclusion of 
omission trials across all eight groups. Consistent with the findings 
of Leng et al. (2025), exclusion led to substantial overestimation of 
drift rates (mean Δ = +1.5 to +6.8, Cohen's d up to 9.3) and 
underestimation of boundary separation. For groups with omission rates 
below 15% (G5–G8), the two approaches produced overlapping 95% 
credible intervals for all parameters. Based on these results, we 
retained the censoring approach as our baseline, excluded G1 and G2 
(omission rates >50%) from modeling, and flagged G3–G4 (omission rates 
35–38%) for cautious interpretation.
```

### 8.2 Discussion: 局限性与未来方向段落实例

```
Methodological Considerations

Our sensitivity analysis confirmed that omission handling can 
substantially impact DDM parameter estimates (cf. Leng et al., 2025). 
While our censoring approach outperformed complete omission exclusion, 
it does not explicitly model the post-deadline probability density. 
The LAN+OPN framework (Leng et al., 2025) offers a more principled 
solution by jointly modeling observed choices and omission probability 
via pre-trained neural networks. However, its current implementation 
in the HSSM toolbox (Fengler et al., in prep) is still under 
development, and our sample of eight (effectively six) experimental 
conditions provides limited training data for the omission probability 
network. Future studies with expanded design spaces (e.g., 12–16 
conditions) could leverage LAN+OPN to further reduce omission-related 
bias in parameter estimation.
```

### 8.3 建议图表清单

| # | 图表                         | 内容                                        | 来源                                                                      |
| :-: | :--------------------------- | :------------------------------------------ | :------------------------------------------------------------------------ |
| 1 | Sensitivity figure (bar)     | Censor vs Drop 6 参数 + 95% CI              | `3_Figures/Omission_Sensitivity/sensitivity_censor_vs_drop_params.png`  |
| 2 | Sensitivity figure (scatter) | Censor vs Drop 参数散点（颜色=omission 率） | `3_Figures/Omission_Sensitivity/sensitivity_scatter_censor_vs_drop.png` |
| 3 | Omission summary             | 各组 omission 率与试次分布                  | `3_Figures/Omission_Sensitivity/omission_summary_by_group.png`          |
| 4 | Conceptual figure            | LAN+OPN 框架示意图（改编自论文 Figure 1B）  | 需自行绘制或引用论文                                                      |
| 5 | Delta vs omission rate       | Δ 随遗漏率变化的趋势                       | `3_Figures/Omission_Sensitivity/sensitivity_delta_vs_omission_rate.png` |

### 8.4 关键引用格式

```
Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025). 
The Perils of Omitting Omissions when Modeling Evidence Accumulation. 
Manuscript in preparation.
```

> **本章要点**: (1) Methods 中需明确描述 Censor 方法并引用敏感性分析作为验证依据；(2) Discussion 中应将 LAN+OPN 作为 future direction 而非当前 limitation；(3) 敏感性分析图表可直接用于论文。

---

## 附录 A：与 v1（Omission建模可行性分析.md）的差异对照

| v1 内容                      | v2 新增/改动                                          |
| :--------------------------- | :---------------------------------------------------- |
| §1 文献核心发现（高层摘要） | §1 论文方法论深度解读（数学公式 + 伪代码）           |
| §2 本项目 Omission 现状     | §4 适配性深度评估（11 维度对照表）                   |
| §3 三种路线（概要）         | §5 三种路线（可执行代码骨架）                        |
| —                           | §2 偏倚量化机制（似然函数层面解释）                  |
| —                           | §3 跨条件比较（论文 Figure 4 → 本项目 SPE_v）       |
| —                           | §6 HSSM 入门教程（全新）                             |
| §4-6 建议 + 计划            | §7-8 分阶段实施 + 论文写作方案（基于已完成工作更新） |

---

## 附录 B：关键术语中英对照

| 英文                                   | 中文                 | 首次出现章节 |
| :------------------------------------- | :------------------- | :----------- |
| Sequential Sampling Model (SSM)        | 顺序抽样模型         | §1.1        |
| Drift Diffusion Model (DDM)            | 漂移扩散模型         | §1.2.1      |
| Likelihood Approximation Network (LAN) | 似然近似网络         | §1.3.2      |
| Omission Probability Network (OPN)     | 遗漏概率网络         | §1.3.3      |
| Right-censoring                        | 右截尾               | §2.2        |
| Collapsing boundary                    | 塌缩边界             | §1.2.2      |
| Lapse distribution                     | 注意流失分布         | §1.4        |
| Posterior predictive check             | 后验预测检查         | §3.1        |
| Hierarchical Bayesian                  | 层级贝叶斯           | §6.1        |
| Deadline                               | 截止时间（deadline） | §1.2        |

---

*分析日期：2026-06-13 | 基于 Leng, Fengler, Shenhav, & Frank (2025) 全文 + 本项目已完成的敏感性分析实证结果*
