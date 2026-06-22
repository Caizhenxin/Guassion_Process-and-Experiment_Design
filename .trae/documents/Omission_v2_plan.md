# Omission_v2.md 撰写计划

## 一、Summary

撰写一份对 Leng et al. (2025) 论文的**深度方法论解读 + 面向本项目的具体技术实施方案**，保存为 `5_Reference/Omission_v2.md`。

与 v1（`Omission建模可行性分析.md`）的关系：
- v1：文献综述 + 实证敏感性分析结果 + 高层路线建议（已完成）
- v2：论文方法论深度解读 + **数学形式化** + 具体可执行的技术路线图 + HSSM 使用教程

## 二、文件结构（约 8 章）

| # | 章节 | 内容 | 与 v1 的关系 |
|:---|:---|:---|:---|
| 封面 | 文档信息 | 文献引用、分析目标、与 v1 关系说明 | 新增 |
| 一 | 论文方法论深度解读 | LAN、OPN 的数学定义、联合似然公式、三种边界类型的参数恢复策略、Lapse 混合分布建模 | v1 §1 的深度扩展 |
| 二 | 参数恢复偏倚的量化机制 | 从数学角度解释为什么丢弃 omission 导致 a↓、v↑、θ↑、为什么 LAN+OPN 能纠正 | v1 §1 的理论补充 |
| 三 | 跨条件比较的启示 | 论文的合成实验（Δθ 恢复）对本项目的直接启示——SPE 效应方向可能稳健但量值被压缩 | 新增角度 |
| 四 | 本项目适配性深度评估 | 逐维度对照论文方案 vs 本项目：数据规模、DDM类型、软件栈、8组条件特征 | v1 §3 的更新升级 |
| 五 | 三种技术路线的具体实现方案 | 路线 A（维持 HDDM Censor）、路线 B（迁移 HSSM+LAN+OPN）、路线 C（HDDM增强建模）的**可执行代码骨架** | v1 §3.2 的实现化版本 |
| 六 | HSSM 入门教程 | HSSM 安装、基本 API、LAN+OPN 配置示例（deadlinedata=True）、与 HDDM 数据格式互转、本项目的适配说明 | 全新 |
| 七 | 分阶段实施建议 | 基于已完成敏感性分析结果的阶段性决策矩阵：短期（已完成哪些）、中期（待执行）、长期 | v1 §4-6 的浓缩版 |
| 八 | 论文写作建议 | Methods 中 omission 处理的写作模板、Discussion 中局限性论述要点 | 新增 |

## 三、各章节详细内容规划

### 第一章：论文方法论深度解读

**数据来源**：PDF `4_Reports/Reference/DDM/The Perils of Omitting Omissions...pdf`

**内容要点**：
1. **SSM 三类边界定义**（带数学公式）：
   - 恒定边界 DDM：$f^{DDM}_{bound}(t) = a$
   - 线性塌缩 ANGLE：$f^{ANGLE}_{bound}(t) = a - t \times \sin(\theta)/\cos(\theta)$
   - 非线性塌缩 WEIBULL：$f^{WEIBULL}_{bound}(t) = a \times \exp(-(t/\beta)^\alpha)$

2. **联合似然公式**（Equation 6 from paper）：
   $$log_l(D, O|\theta_{SSM}, d) = \sum_{i=0}^{|D|} f^{LAN}_{c_i}(rt_i|\theta_{SSM}) + |O| \times f^{OPN}(omission|\theta_{SSM}, d)$$

3. **LAN 工作原理**：预训练神经网络输入 (rt, choice, θ) → 输出 log-likelihood

4. **OPN 工作原理**：输入 (θ, deadline d) → 输出 post-deadline 概率密度积分值

5. **Lapse 混合分布**：
   $$likelihood = (1-p_{lapse}) \times likelihood_{SSM} + p_{lapse} \times f_{Lapse}$$
   均匀分布：$f_{Lapse}(t) = 1/(2T)$ for $t \in [0, T]$

6. **核心数值发现汇总表**（从论文 Figures 2-6 提炼）：
   - 恒定边界 DDM：LAN-only 低估 a、高估 v；LAN+OPN 正确恢复
   - ANGLE 模型：LAN-only 高估 a 和 θ；>5% omission 即有显著偏倚
   - 跨条件 Δθ：LAN-only 严重低估效应量（真值 0.2 → 恢复值远<0.2）
   - WEIBULL：LAN-only 偏倚所有 3 个边界参数
   - Lapse：LAN+OPN 正确恢复 p_lapse，LAN-only 显著低估

### 第二章：参数恢复偏倚的量化机制

**内容要点**：
1. 从似然函数角度解释偏倚机制：
   - 未建模 omission → 模型"看不见" post-deadline 的数据
   - 似然面在 "快RT参数" 区域更高 → MCMC 趋向高 v、低 a
   - 塌缩边界模型 → 更激进的塌缩（高 θ）减少 omission 概率
2. 用代码伪逻辑说明 joint likelihood 如何"惩罚" omission 高发的参数组合
3. 引用本项目敏感性分析的实证结果作为验证

### 第三章：跨条件比较的启示

**内容要点**：
1. 论文 Figure 4 的可视化描述和结论翻译
2. 对本项目的直接启示：
   - SPE_v 在两种处理方案下方向一致但量值不同 → 论文的 Δθ 发现与此平行
   - 即使偏倚方向在跨条件下一致，效应量仍可能被压缩
3. 建议：论文讨论中引用 Leng et al. Figure 4 作为方法论依据

### 第四章：本项目适配性深度评估

**内容要点**：
1. 逐维度对照表（比 v1 更细化）：

| 维度 | 论文设置 | 本项目现状 | 适配度评估 |
|:---|:---|:---|:---:|
| 数据来源 | 合成数据（已知 ground truth） | 真实数据（被试 88 人，8 组） | ⚠️ |
| 样本量 | 每组约 100-500 合成试次 | G1-G8: 2600-3120 试次/组 | ✅ |
| DDM 类型 | DDM/ANGLE/WEIBULL | 仅恒定边界 DDM | ⚠️ |
| 参数估计 | LAN-based MCMC | HDDM MCMC (解析似然) | ⚠️ |
| 层次结构 | 支持层级贝叶斯 (HSSM) | 已使用层级贝叶斯 (HDDM) | ✅ |
| Omission 率 | 5-30% | 6.7-72.3%（跨度极大） | ⚠️ |
| Deadline | 固定 1.25s | 各组不同 (330-2000ms) | ✅ |

2. 核心适配障碍：
   - 8 组数据 + 仅恒定边界 DDM → ANGLE/WEIBULL 的结论不完全适用
   - 真实数据无 ground truth → 只能做相对比较（如敏感性分析），不能做绝对恢复评估
   - HSSM 的 LAN+OPN 功能仍在开发中（"in prep"）

### 第五章：三种技术路线的具体实现方案

比 v1 更具体——提供可执行的技术骨架：

**路线 A：维持 HDDM 截尾方案**
- 当前已有代码（`step2_hddm_fit.py`）
- 基于敏感性分析结论的参数取舍决策矩阵
- 论文写作中如何辩护此方案

**路线 B：迁移到 HSSM + LAN+OPN**
- 具体步骤（6 步）：
  1. 安装 HSSM 和依赖
  2. 准备数据（格式从 HDDM-ready 转换）
  3. 训练 OPN（伪代码框架）
  4. 配置 HSSM 模型（代码示例）
  5. 运行 MCMC 拟合
  6. 比较 HDDM Censor vs HSSM LAN+OPN 参数估计
- 所需资源和风险
- 本项目的 blockers（OPN 预训练数据量、HSSM 稳定性）

**路线 C：HDDM 增强建模**
- 三个具体方案的技术细节：
  - C1: Lapse-only 模型（利用 HDDM 现有 p_outlier）
  - C2: Sigmoid omission_rate 预测函数（`1_Code/Python_for_Generate/` 中新增）
  - C3: GP 联合预测 omission_rate（GPSigmoidHybridModel 扩展）
- 每个方案的代码骨架

### 第六章：HSSM 入门教程

**面向本项目的实用教程**：
1. HSSM 与 HDDM 的关系（同为 Python 层级贝叶斯 DDM）
2. 安装指南（pip/conda）
3. 基本 API 对比：HDDM vs HSSM
4. LAN+OPN 配置示例：
   ```python
   # HSSM with LAN+OPN (conceptual example)
   model = hssm.HSSM(
       data=df,
       model="angle",
       include=["v", "a", "theta", "t"],
       deadlinedata=True,   # 启用 OPN
       deadline=1.25,       # 实际应使用各组 deadline
   )
   ```
5. 数据格式从 HDDM-ready 到 HSSM-ready 的转换脚本
6. 当前限制与 workaround（HSSM 仍在开发中）

### 第七章：分阶段实施建议

基于已完成工作的决策矩阵：

| 阶段 | 状态 | 内容 |
|:---|:---:|:---|
| 短期 | ✅ 完成 | Censor vs Drop 敏感性分析（`Omission_Sensitivity_Analysis.ipynb`） |
| 短期 | ✅ 完成 | G7/G8 区分、G1-G2 排除决策 |
| 中期 | 📋 待执行 | GP 模型更新使用 G3-G8（任务 5.2 of RoadMap） |
| 中期 | 📋 待执行 | Sigmoid omission_rate 预测函数（路线 C2） |
| 长期 | 🔮 展望 | HSSM LAN+OPN 迁移评估 |
| 长期 | 🔮 展望 | 新增 4-6 个实验条件后重新评估 |

### 第八章：论文写作建议

1. Methods 中 omission 处理的写作段落模板
2. Discussion 中局限性论述：
   - 当前 Censor 方法的局限性
   - 引用 Leng et al. (2025) 的方法论依据
   - 未来 HSSM+OPN 的展望
3. 建议图表：
   - Sensitivity figure（已有 `3_Figures/Omission_Sensitivity/`）
   - Conceptual figure（LAN+OPN 框架示意图，引用论文 Figure 1）

## 四、Assumptions & Decisions

1. **假设 HSSM 仍在开发中**：教程部分以"概念示例"标注，避免用户误以为可以立即运行
2. **不创建新代码**：本文档是可行性分析，不是代码交付物。代码骨架以 Markdown 伪代码形式呈现
3. **以项目已有分析为基础**：引用 `Omission_Sensitivity_Analysis.ipynb` 的输出数据、`Omission建模可行性分析.md` 的结论，不做重复分析
4. **保留中文为主要语言**：技术术语首次出现时附英文原文

## 五、Verification

完成后检查：
- [ ] 文件 `5_Reference/Omission_v2.md` 存在且编码为 UTF-8
- [ ] 数学公式（LaTeX）在 Markdown 中至少可读
- [ ] 所有对已有文件的路径引用正确
- [ ] HSSM 教程部分的代码示例语法正确（概念层面）
- [ ] 与 `Omission建模可行性分析.md` v1 的交叉引用正确
- [ ] 每章末尾有明确的"本章要点"小结
