# PPT 大纲计划：自我优势效应的实验设计空间优化

> 基于项目整体代码库、RoadMap.md、Log.md、可行性分析等全部关键文档的综合设计。

---

## 一、PPT 总体结构设计

本 PPT 共分为 **六大章节**，逻辑层次为：项目概览 → 理论基础 → 建模方法 → 代码演进 → 关键发现 → 研究工具展示。

| 章节 | 标题 | 幻灯片数（估算） | 核心目的 |
|:---|:---|:---:|:---|
| 第一章 | 项目概述：研究背景与核心目标 | 5-7 | 让未接触者快速理解项目全貌 |
| 第二章 | 理论基础：SMT 范式与 DDM 框架 | 5-6 | 建立理论共识，明确研究假设 |
| 第三章 | 建模指导：Gaussian Process + Sigmoid 混合模型 | 8-10 | 为建模者提供实践参考 |
| 第四章 | 代码演进：从 v1 到 v2.4.5 的迭代历程 | 7-9 | 系统呈现代码演进路径 |
| 第五章 | 核心发现与展望 | 4-5 | 总结关键结果与后续方向 |
| 第六章 | 研究工具展示：可视化平台与辅助工具 | 5-7 | 详细介绍研究工具链 |

**总计**：约 34-44 张幻灯片

---

## 第一章：项目概述——研究背景与核心目标

### Slide 1：封面
- 标题：**自我优势效应的实验设计空间优化——基于高斯过程与漂移扩散模型的混合建模方法**
- 副标题：GP-SPE 实验设计优化项目
- 项目仓库路径 / 日期 / 负责人信息

### Slide 2：一句话核心问题
- **核心研究问题**：
  > 实验设计参数（练习次数 P、刺激呈现时间 T、反应窗口 W）如何系统性地调控自我优势效应（SPE）？能否用高斯过程（GP）在 DDM 框架下建模这一调控机制，从而优化实验设计？
- 用一张简图表示：`(P, T, W) → DDM参数(v, a, t0, z) → 行为(RT, ACC, Omission)`

### Slide 3：项目背景与动机
- **背景 1**：Self-Matching Task（Sui et al., 2012）是测量自我优势效应（SPE）的核心范式
- **背景 2**：现有研究多为"效应检验"模式（验证 SPE 是否存在），缺少对实验设计参数的系统优化
- **背景 3**：漂移扩散模型（DDM）可以揭示 SPE 背后的认知过程（v, a, t0, z）
- **动机**：从"效应检验"走向"设计空间建模与优化"
- 图示：传统范式 vs 本项目的设计空间优化范式

### Slide 4：项目核心目标与预期成果
- **目标 1**：建立 Sigmoid（理论先验）+ GP（经验残差）的混合生成模型
- **目标 2**：通过 HDDM 提取 8 组真实数据的 DDM 参数，校准模型
- **目标 3**：利用 GP 响应面在 (P, T, W) 空间中预测 SPE，指导新实验设计
- **目标 4**：证明 GP+Sigmoid 模型在捕捉真实 SPE 上优于纯 Sigmoid 模型
- **预期成果**：可解释的生成模型 + 优化后的实验设计方案 + 论文产出

### Slide 5：项目总体进度概览
- 用 RoadMap.md 的 Phase 表格展示：

| Phase | 内容 | 状态 |
|:---|:---|:---:|
| Phase 0 | 实验数据采集 + 基线 Sigmoid+DDM | ✅ |
| Phase 1 | GP 角色定位（方法论确立） | ✅ |
| Phase 2 | HDDM 参数提取 + Omission 敏感性分析 | ✅ |
| Phase 3 | GP+Sigmoid 混合建模 + LOCV + 行为验证 | ✅ 初步完成 |
| Phase 4 | 候选实验点推荐 + 下一轮实验设计 | 📋 |
| Phase 5 | 论文撰写与产出 | 📋 |

### Slide 6：项目文件夹结构速览
- 展示关键目录结构（来自 AGENTS.md）：
  - `1_Code/` — Python 生成 / Python 检验 / Python HDDM / R 检验
  - `2_Data/` — 生成数据 / 真实数据（HDDM 拟合结果）
  - `3_Figures/` — 图表输出
  - `5_Reference/` — 参考文档（RoadMap, Log, 可行性分析）
- 标注核心文件位置

### Slide 7：关键技术名词速查表
| 缩写 | 全称 | 含义 |
|:---|:---|:---|
| SPE | Self-Prioritization Effect | 自我优势效应 |
| SMT | Self-Matching Task | 自我匹配任务（Sui et al., 2012） |
| DDM | Drift-Diffusion Model | 漂移扩散模型 |
| GP | Gaussian Process | 高斯过程 |
| HDDM | Hierarchical DDM | 层级贝叶斯漂移扩散模型 |
| LOCV | Leave-One-Condition-Out | 留一条件交叉验证 |
| P/T/W | Practice/Time/Window | 练习次数/刺激呈现时间/反应窗口 |

---

## 第二章：理论基础——SMT 范式与 DDM 框架

### Slide 8：Self-Matching Task 实验范式
- Sui et al. (2012) 范式说明
- 实验流程图示：
  - 学习阶段：`circle ↔ self`, `square ↔ stranger`（或反向平衡）
  - 测试阶段：看到 stimulus+label 对，按 f 或 j 键判断是否匹配
  - Matching = (circle, self) 或 (square, stranger)
  - NonMatching = (square, self) 或 (circle, stranger)
- SPE 定义：`SPE = RT(self, Matching) - RT(stranger, Matching)`
- 说明本项目仅建模 Matching 条件（与 Sui 2012 一致）

### Slide 9：实验设计空间 Ω = (P, T, W)
- 8 组实验条件总览表（来自 RoadMap Phase 0.1）：

| 组别 | P | T(ms) | W(ms) | M(ms) | 被试数 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| G1 | 0 | 30 | 300 | 330 | 11 |
| G2 | 0 | 30 | 600 | 630 | 12 |
| G3 | 120 | 30 | 600 | 630 | 10 |
| G4 | 120 | 80 | 600 | 680 | 11 |
| G5 | 8 | 100 | 1100 | 1200 | 11 |
| G6 | 120 | 500 | 1500 | 2000 | 10 |
| G7 | 120 | 30 | 800 | 830 | 12 |
| G8 | 120 | 80 | 800 | 880 | 11 |

- 用 3D 散点图示意设计点在 (P,T,W) 空间中的分布
- 标注现有设计的不足：P 仅 3 水平 (0, 8, 120)，T 的 30-500ms 中间空白

### Slide 10：漂移扩散模型（DDM）核心原理
- DDM 的核心假设：决策是证据在噪声中累积的过程
- 四个核心参数：
  - **v（漂移率）**：信息累积速度，反映任务难度/被试能力
  - **a（边界分离）**：决策谨慎度，a↑ → 慢但准确
  - **z（起始点）**：先验偏向
  - **t0（非决策时间）**：刺激编码+反应执行
- 图示：DDM 的累积过程示意图（起始点 → 穿过上下边界）
- 说明：本项目固定 s=0.1（HDDM 默认缩放约定），z=a/2（无偏向假设）

### Slide 11：DDM 参数与 SPE 的关系
- 在 SMT 中，`v_self` 和 `v_stranger` 的相对差异直接编码了 SPE：
  - SPE_v = v_self - v_stranger > 0 → 自我信息累积更快
- 8 组真实 HDDM 参数展示（来自 RoadMap Phase 2.3）：

| 组别 | v_self | v_stranger | SPE_v | a | t(s) | 遗漏率% |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| G1 | -3.39 | -3.36 | -0.02 | 2.01 | 0.263 | 72.3%⚠️ |
| G5 | +1.35 | +0.64 | **+0.71** | 1.34 | 0.398 | 10.9% |
| G6 | +1.81 | +1.17 | **+0.65** | 1.48 | 0.663 | 5.6% |

- 用柱状图展示各组 SPE_v 的对比
- 标注 G1/G2 高遗漏率问题（将在后面展开）

### Slide 12：研究假设体系
- **H1**：实验设计参数 (P, T, W) 通过调节 DDM 参数 (v, a) 系统性影响 SPE
- **H2**：Sigmoid 函数可以提供一个合理的理论先验，描述 (P,T,W) → (v,a) 的宏观趋势
- **H3**：GP 能够捕捉 Sigmoid 无法解释的系统性残差，提升模型对真实 SPE 数据的拟合精度
- **H4**：基于 GP 响应面的不确定性估计可以指导最优实验设计

### Slide 13：关键研究问题与解决思路
| 研究问题 | 解决思路 | 对应章节 |
|:---|:---|:---|
| GP 在框架中扮演什么角色？ | 三种角色对比分析，确定"残差捕捉"为最优 | Phase 1 |
| 如何从真实数据获取 DDM 参数？ | Docker HDDM 层级贝叶斯拟合 | Phase 2 |
| 高遗漏率条件如何处理？ | Omission 敏感性分析（Censor vs Drop） | Phase 2.4 |
| Sigmoid 参数如何校准？ | 差分进化算法最小化 RMSE | Phase 3 |
| GP 泛化能力如何验证？ | LOCV + 行为层面验证 | Phase 3 |
| 下一轮实验选什么设计点？ | GP 不确定性驱动的候选推荐 | Phase 4 |

---

## 第三章：建模指导——GP+Sigmoid 混合模型实践

### Slide 14：模型总体架构
- 核心架构图：
```
(P, T, W) ──┬──→ Sigmoid 理论层 (compute_v_s2 / compute_a_s2) ──→ v_s2, a_s2
             │                                                         │
             └──→ 归一化 (Pn, Tn, Wn) ──→ GP 残差层 ──→ Δv, Δa ──→ v_mix, a_mix
                                                                       │
                                                          + t0=0.2, z=a/2
                                                                       │
                                                          Euler DDM 仿真
                                                                       │
                                                          RT, response, omission
```
- GPSigmoidHybridModel 类的核心结构说明（来自 `gp_sigmoid_hybrid_model.py`）

### Slide 15：Sigmoid 理论层——参数设置原则
- **compute_v_s2(T, P, condition_key)** 的参数表（来自 RoadMap 0.4）：

| 参数 | 默认值 | 含义 | 校准后（Cleaned） |
|:---|:---:|:---|:---:|
| alaph1 | 1.5 | self 条件 v 增强倍数 | **0.199** |
| alaph2 | -0.4 | stranger 条件 v 调制倍数 | -0.404 |
| gamma | 0.2 | 练习效应 Sigmoid 陡峭度 | 0.640 |
| T_0 | 100 | v-T Sigmoid 中点(ms) | 63.7 |
| k_T | 0.01 | v-T 陡峭度 | 0.100 |
| base_scale_v | 3.0 | v 幅度缩放因子 | 1.326 |

- **compute_a_s2(M)** 的参数表：

| 参数 | 默认值 | 含义 | 校准后 |
|:---|:---:|:---|:---:|
| beta1 | 0.2 | 高 M 边界增强 | **-0.826**(反转!) |
| beta2 | 0.0 | 低 M 边界调制 | 1.000 |
| M_0 | 600 | a-M Sigmoid 中点(ms) | 565.4 |
| k_a | 0.01 | a-M 陡峭度 | 0.018 |
| base_scale_a | 3.0 | a 幅度缩放因子 | 2.806 |

- **经验值建议**：推荐使用校准后的 Cleaned 版参数（来自 `GP_Sigmoid_Cleaned/`）

### Slide 16：参数校准方法——差分进化优化
- 方法流程图：
  ```
  真实 HDDM 参数 (v, a)_8条件
       ↓
  Sigmoid 预测值 = f(P, T, W; θ)
       ↓
  RMSE = sqrt(mean((真实值 - 预测值)²))
       ↓
  差分进化算法最小化 RMSE → 最优 θ
  ```
- 校准对象：7 个参数 (alaph1, alaph2, beta1, beta2, gamma, base_scale_v, base_scale_a)
- 关键代码：`sigmoid_calibration.py` 和 `run_cleaned_validation_pipeline.py`
- v9 系统性优化扩展为 11 参数（含 T_0, k_T, M_0, k_a）

### Slide 17：GP 残差层的构建与训练
- GP 核函数：`ConstantKernel × RBF + WhiteKernel`
- 训练数据构造：
  - X = 归一化的 (Pn, Tn, Wn)（8 个条件 → 归一化到 [-1, 1]）
  - Y_v = 真实 v - Sigmoid 预测 v（每个条件 × 2 标签）
  - Y_a = 真实 a - Sigmoid 预测 a
- 对 5 个 DDM 参数（v_self, v_stranger, a, t, z）各训练一个独立 GP
- 最终预测：`DDM_true ≈ Sigmoid_pred + GP_residual`

### Slide 18：不同场景下的模型调整策略

| 场景 | 问题 | 调整策略 |
|:---|:---|:---|
| 新增实验条件 | 仅 8 个训练点，GP 泛化差 | 按候选点推荐新增 4-6 个条件 |
| 遗漏率过高 | G1/G2 遗漏率 >50% | 排除该条件，或标记为 Censored 数据 |
| base_scale_a 触界 | a 的 Sigmoid 无法产生足够大的边界 | 放宽搜索上界（10→25），或改用线性/二次函数 |
| beta1 符号反转 | 高 M 边界反而降低 | 检查数据问题，考虑分段函数形式 |
| aphal2 变号 | stranger 反而获得 v 增强 | 评估合理性，可能需要重新参数化 |
| GP 训练过拟合 | 8 点训练近乎完美，LOCV 表现差 | 增加训练数据，调整核函数 length_scale |

### Slide 19：模型验证策略详解
- **三层验证体系**：
  1. **训练集拟合（in-sample）**：检查模型对已知 8 条件的拟合精度
  2. **LOCV（Leave-One-Condition-Out）**：每次留一个条件验证泛化能力
  3. **行为层面验证**：DDM 试次级模拟 → 与真实行为对比（RT/ACC/Omission/SPE）

- 验证结果速览（来自 RoadMap Phase 3.5）：

| 指标 | r | RMSE | 判断 |
|:---|:---:|:---:|:---:|
| Correct RT | 0.981 | 66.8ms | ✅ 优秀 |
| Accuracy | 0.968 | 0.153 | ✅ 优秀 |
| Omission Rate | 0.923 | 0.145 | ✅ 优秀 |
| SPE RT | 0.843 | 21.1ms | ✅ 良好 |

### Slide 20：常见建模问题与解决方案

| 问题 | 根因 | 解决方案 |
|:---|:---|:---|
| GP 拟合几乎完美（r≈1.0） | 训练点过少 (8点) + GP 灵活性高 | 增加训练条件，并在论文中报告 LOCV |
| LOCV 结果负相关 | 3D 空间中 8 点不足 | 至少新增 4-6 个条件 |
| Sigmoid 无法产生负 v | Sigmoid 函数输出 ∈ [0,1] | 引入偏移项或重新参数化 |
| Omission 试次如何处理 | 高遗漏率污染 v 估计 | 用 Censor 方案（RT=deadline），排除 >50% 条件 |
| p_outlier 与 Censor 数据冲突 | 截尾数据被误判为 outlier | Censor 方案使用 p_outlier=0 |
| 参数估计不稳定 | MCMC 未充分收敛 | 增加 burn-in/samples，检查 R-hat < 1.1 |

### Slide 21：Omission 处理专项指南
- Censor vs Drop 方案的对比（来自 Phase 2.4）：
  - **Censor**：遗漏试次 rt=deadline, response=0, p_outlier=0
  - **Drop**：直接删除遗漏试次, p_outlier=0.05
- 关键发现：遗漏率 >35% 时两种方案 v 差异 >1.5（G1-G4）
- **推荐策略**：
  - 遗漏率 >50%：排除该条件（G1, G2）
  - 遗漏率 15%-50%：标记"谨慎解释"
  - 遗漏率 <15%：Censor 方案足够可靠

### Slide 22：DDM 参数合理范围参考（来自 RoadMap 附录）
| 参数 | 严格下限 | 宽松上限 | 典型范围（标准实验） |
|:---|:---:|:---:|:---|
| v | -10 | +20 | 0.0 ~ 0.6 |
| a | 0.05 | 8.0 | 0.05 ~ 0.4 |
| zr | 0.0 | 1.0 | 固定 0.5 |
| t0 | 0.05 | 2.0 | 0.2 ~ 0.9 |
- 基于 Tran et al. (2021) 158 篇文献综述 + Matzke & Wagenmakers (2009)

### Slide 23：候选实验设计点推荐方法
- 推荐策略的 3 个维度：
  1. **不确定性最大化**：选 GP 预测 std 最大的区域
  2. **理论关键点验证**：选 SPE 理论预测极值点
  3. **梯度最大区域**：选 SPE 变化最陡峭的区域
- 当前 Top 候选（来自 step6）：P≈35, T=500, W=300
- 推荐优先实验条件表：
  - T=500ms, W=300ms, P=15~45（高不确定性区域）
  - P=30, P=60（填补 P 中间空白）
  - T=200ms, W=700ms（填补 T 中间空白）

---

## 第四章：代码演进——从 v1 到 v2.4.5 的迭代历程

### Slide 24：代码演进总览路线图
- 时间线图展示关键版本节点：
```
v1 (基线Sigmoid)  →  v2 (引入GP)  →  v2.1-v2.3 (混合架构探索)
    →  v2.4 (稳定版: S2+GP+DDM)  →  v2.4.2-v2.4.4 (功能迭代)
    →  v2.4.5 (当前推荐版: 重采样a)  →  v3 (GP捕捉残差, 探索中)
```

### Slide 25：v1——基线模型（纯 Sigmoid + DDM）
- 文件：`Generate_Data_v1.ipynb`, `S2 gen_data_jh.ipynb`
- 核心函数：`compute_v_s2(T, P, condition_key)` + `compute_a_s2(M)`
- GP 角色：作为 Sigmoid 生成 anchor 数据的代理模型
- 输出：v_s2, a_s2 → Euler DDM 仿真 → RT, response
- **评价**：框架清晰，GP 学习了 Sigmoid 生成逻辑（未用真实数据）

### Slide 26：v1 → v2：GP 角色的转变
- v1：GP 学习 Sigmoid 生成的 anchor 数据
- v2：引入 HybridDDMParameterGenerator 类
  - Sigmoid + GP 线性混合，权重 w
  - GP 训练数据变为人工合成（sin/cos），脱离了理论锚定
- **核心认识**：GP 的训练数据来源是决定模型质量的关键

### Slide 27：v2.4——关键稳定版本
- 文件：`Generate_Data_v2.4.ipynb`, `Generate_Data_v2.4_runner.py`
- 确立最终架构：S2 机制函数 + GP 修正 + DDM 仿真
- 保留 S2 的心理学设定（self/stranger 对 v 的不同乘数，M>600 对 a 的影响）
- 归一化 P,T,W 输入 GP（`normalize_PTW_to_unit`）
- 混合权重 `w_gp = 0.5`
- 含参数恢复检验：`Generate_Data_v2.4_recovery.py`

### Slide 28：v2.4.2 → v2.4.4：功能迭代

| 版本 | 新增功能 | 核心改进 |
|:---|:---|:---|
| v2.4.2 | 条件间参数配对可视化 | 增强模型检验能力 |
| v2.4.3 | P/T/W 边际效应图 | 理解各因素对参数和行为的独立影响 |
| v2.4.4 | **Omission 机制** | 引入 deadline omission + lapse omission；但存在硬截断问题 `max(0.1, a_final)` |

- v2.4.4 的关键改进：模拟了真实数据中普遍存在的遗漏试次
- v2.4.4 的遗留问题：硬截断导致 a=0.1 堆积

### Slide 29：v2.4.5——当前推荐版本
- 文件：`Generate_Data_v2.4.5.ipynb` / `Generate_Data_v2.5_runner.py`
- 核心修正：a 使用重采样代替硬截断（`sample_a_positive`）
- 保留了 omission 机制（deadline + lapse）
- 生成函数 `generate_dataset_s2_na_v245` 输出完整中间参数和行为结果

### Slide 30：v2.5 → v3：探索中的方向
- v2.5 系列（`Generate_Data_v2.5_simple.py`, `_tuning.py`, `_v2.py`）：
  - 尝试简化 GP 部分或调整混合策略
- v3（`Generate_Data_v3.ipynb`）：
  - 探索更纯粹的"GP 捕捉残差"方案
  - GP 直接学习 (P,T,W) → 真实 HDDM 参数（跳过 Sigmoid 中间层）
  - **状态**：探索中，尚未稳定

### Slide 31：代码演进中的关键发现与教训

| 发现/教训 | 版本阶段 | 影响 |
|:---|:---|:---|
| GP 训练数据必须与真实心理过程相关 | v1→v2 | 决定了后续所有建模方向 |
| Sigmoid 无法产生负 v 值（结构局限） | v9 校准 | 高遗漏率条件的 v 预测永远为正 |
| base_scale_a 在 Cleaned 版触界 (10.0) | Phase 3 | 提示 Sigmoid 对 a 的参数化需要重构 |
| alaph1 校准后仅 0.199（默认 1.5） | Phase 3 | self 的实际优势远小于理论假设 |
| beta1 符号反转（+0.2→-0.826） | Phase 3 | 高 M 条件下边界反而降低——反直觉但真实 |
| 8 个条件不足以支持 GP 泛化 (LOCV) | Phase 3.4 | 必须新增实验条件 |

### Slide 32：版本对比总结表
| 维度 | v1 (纯Sigmoid) | v2.4 (混合初版) | v2.4.5 (当前) | v3 (探索中) |
|:---|:---|:---|:---|:---|
| GP 角色 | 代理模型 | 任意残差注入 | 数据层混合 | 残差捕捉 |
| Omission | ❌ | ❌ | ✅ | 待定 |
| a 采样 | 硬截断 | 硬截断 | 重采样✅ | 待定 |
| 理论基础 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 推荐状态 | 历史参考 | 历史参考 | **主版本** | 探索中 |

---

## 第五章：核心发现与展望

### Slide 33：DDM 参数层面的核心发现
- 8 组真实 HDDM 参数汇总表 + 柱状图（SPE_v, a, t 跨组对比）
- 关键发现：
  - G5 产生最大 SPE_v (+0.71)：P=8, T=100, W=1100
  - G6 参数最稳定（遗漏率 5.6%）：P=120, T=500, W=1500
  - G1/G2 v 为负值（高遗漏率污染）
  - G7/G8 设计重复但被试独立，SPE_v 差异反映被试间变异

### Slide 34：Sigmoid 参数校准的关键发现
- 校准前后的参数变化对比表（默认 → Cleaned → v9最优）：
  - alaph1: 1.5 → 0.199 → 1.112
  - beta1: +0.2 → -0.826 → -0.434（方向反转！）
  - base_scale_a: 3.0 → 10.0（触界） → 2.806
- 心理学解释：
  - self 的实际漂移率优势仅约 20%（远小于 150% 假设）
  - 高 M 条件下边界反而降低（可能反映被试的 speed-accuracy tradeoff 策略调整）
  - 练习效应比预期更陡峭（gamma 从 0.2 升至 0.64）

### Slide 35：行为层面验证的积极信号
- 4 个指标的散点图 + 相关性（真实 vs 模拟）：
  - Correct RT: r=0.981, RMSE=66.8ms
  - Accuracy: r=0.968, RMSE=0.153
  - Omission Rate: r=0.923, RMSE=0.145
  - SPE RT: r=0.843, RMSE=21.1ms
- **核心结论**：Sigmoid 理论先验保证了行为层面的稳健重建，即使 DDM 参数层面的 GP 泛化受限于数据量

### Slide 36：当前最大瓶颈与后续方向

| 瓶颈 | 严重程度 | 解决方案 |
|:---|:---:|:---|
| 仅 8 个（实际可用 6 个）设计条件 | 🔴 高 | 按 GP 候选推荐新增 4-6 个条件 |
| base_scale_a 触及上界 | 🔴 高 | 放宽边界或重构 a 的参数化 |
| beta1 符号反转 | 🟡 中 | 深入分析，考虑分段函数 |
| Omission 处理对 v 估计影响大 | 🟡 中 | 统一使用 Censor 方案 + 排除高遗漏组 |
| NonMatching 条件待建模 | 🟢 低 | 可作为独立扩展研究 |

- **后续工作计划**：
  1. 排除 G1/G2，用 G3-G8 重新训练
  2. 实施候选推荐实验，收集新数据
  3. 测试外部验证
  4. 考虑 NonMatching 的扩展建模

### Slide 37：论文结构规划
- 建议论文框架（来自 RoadMap Phase 5.2）：
  1. **Introduction**：SMT 范式 + DDM + 实验设计优化的必要性
  2. **Methods**：
     - 2.1 8 组实验设计空间
     - 2.2 Sigmoid 理论参数化
     - 2.3 GP+Sigmoid 混合模型
     - 2.4 验证策略（LOCV + 外部验证）
  3. **Results**：
     - HDDM 真实参数模式
     - GP+Sigmoid 拟合与 LOCV
     - 行为层面验证
     - 候选实验设计点推荐
  4. **Discussion**：GP 方法的优势与局限 + 实验设计优化指导意义

---

## 第六章：研究工具展示——可视化平台与辅助工具

### Slide 38：工具链总览
- 研究工具全景图：
```
[实验编程] MATLAB (exp_matlab/)
     ↓
[数据预处理] Python (step1_prepare_data.py)
     ↓
[DDM拟合] Docker HDDM (hcp4715/hddm)  +  Python (step2_hddm_fit.py)
     ↓
[参数提取] Python (step3_extract_params.py)
     ↓
[GP建模] Python (GP+Sigmoid/, sklearn GPR)
     ↓
[可视化分析] Python WebApp (Visualization/)  +  R (R_Version/)  +  Jupyter Notebooks
```

### Slide 39：可视化平台概述——主应用
- 名称：**Experiment Data Visualization Server**
- 位置：`1_Code/Python_for_Check/Visualization/`
- 技术栈：HTML/JavaScript 前端 + Python HTTP 后端 + Chart.js 图表
- 启动方式：`python app_server.py` → 浏览器访问 `http://localhost:8899`

### Slide 40：可视化平台——四大核心功能模块

| 标签页 | 功能 | 实际应用 |
|:---|:---|:---|
| **Tab1: 按键逻辑模拟** | 复现 4 试次循环的按键映射规则 | 验证实验逻辑正确性，理解被试的任务结构 |
| **Tab2: 数据浏览** | 加载任意被试数据，查看 RT 分布直方图 | 快速检查个体数据质量 |
| **Tab3: CRF 可视化** | 交互式累积反应函数（分位数分箱），Self/Stranger 对比 | 直观展示 SPE 效应，支持单被试和聚合分析 |
| **Tab4: 设计空间分析** | P/T/W 参数空间的气泡图 + 正确率/遗漏率对比 | 整体评估实验设计对数据质量的影响 |

### Slide 41：可视化平台——CRF 功能详解
- CRF（Cumulative Response Function）的核心原理：
  - 按 RT 分位数分箱
  - 计算每个分箱中选择 Matching 响应（上界）的比例
  - Self（橙色）vs Stranger（蓝色）对比曲线
  - SPE 差异图（Self - Stranger）
- 功能特点：
  - 可调节分位数数量（3-10）
  - 支持 Matching/NonMatching 条件筛选
  - 支持单被试和组聚合分析
- 实际应用案例：用 CRF 直观验证 GP+Sigmoid 模型生成的 SPE 模式

### Slide 42：可视化平台——API 接口速查
| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/api/health` | GET | 健康检查 |
| `/api/files` | GET | 获取所有数据文件列表 |
| `/api/data/all?group=` | GET | 获取聚合数据 |
| `/api/data/file?name=` | GET | 获取单个被试文件 |
| `/api/experiment/params?subject=&group=` | GET | 获取实验参数配置 |
| `/api/experiment/trial?subject=&shape=&label=` | GET | 模拟单个试次 |

### Slide 43：R 版本可视化工具
- 位置：`Visualization/R_Version/`
- 功能模块：
  - **Data Browser** (`02_Data_Browser/data_browser.R`)：数据浏览
  - **Interactive CRF** (`03_Interactive_CRF/`)：交互式 CRF + d' 分析
  - **SPE Database** (`05_SPE_Database/`)：
    - `spe_overview.R` — SPE 总览分析
    - `spe_crf_analysis.R` — CRF 层面的 SPE 分析
    - `spe_ptw_integrated.R` — P/T/W 整合分析
    - `spe_individual_detail.R` — 个体详情
  - 共享工具函数：`shared/utils.R`
- 输出图表示例：SPE RT/ACC 直方图、SPE RT vs ACC 散点图、SPE crf by group

### Slide 44：Jupyter Notebook 探索工具
- **GP 2D/3D 探索**：`GP-SPE-Explore-2D.ipynb` / `GP-SPE-Explore-3D.ipynb`
  - GP 作为 SPE 响应面，在 (P,T) 或 (P,T,W) 空间中可视化
- **模型对比**：`Compare_Real_Generated_DDM_Params_v2.4.3_V2.ipynb`
  - 真实数据 vs 生成数据的三层趋势对比
  - EZ-diffusion 参数估计
  - Spearman 秩相关矩阵
- **参数恢复**：`Parameter_Recovery.ipynb`
- **生成检查**：`step1_generative_checks.ipynb`

### Slide 45：Docker HDDM 拟合工具
- 工具：`hcp4715/hddm` Docker 镜像（基于 Wiecki et al. 2013 的 HDDM 包）
- 使用流程：
  1. `step1_prepare_data.py`：原始数据 → HDDM 就绪 CSV
  2. `step2_hddm_fit.py` + `Docker_Run.ipynb`：Docker 内层级贝叶斯 DDM 拟合
  3. `step3_extract_params.py`：提取后验参数汇总
- 关键配置：
  - `depends_on={"v": "identity"}` 区分 Self/Stranger
  - MCMC: 3000 samples, 500 burn-in
  - Censor 方案: omission 试次 RT=deadline, p_outlier=0

### Slide 46：Sigmoid 优化工具箱
- **Sigmoid 校准**：`sigmoid_calibration.py`（差分进化）
- **Cleaned 验证管线**：`run_cleaned_validation_pipeline.py`（6 步自动化）
- **v9 系统性优化**：`v9_Sigmoid_Optimization.ipynb`（5 策略，16 参数）
  - S1: Cleaned 基线复现
  - S2: 扩展边界
  - S3: 排除高遗漏组
  - S4: 加权多目标
  - S5: 全参数优化（最优）
- **GP+Sigmoid 混合模型**：`gp_sigmoid_hybrid_model.py`

### Slide 47：其他辅助工具汇总

| 工具 | 位置 | 用途 |
|:---|:---|:---|
| LSTM/SPE 分析 | `ANOVA/SPE_Bayesian_Analysis.ipynb` | 贝叶斯 ANOVA 检验 SPE |
| 贝叶斯因子 | `Basic_Hypothesis/SPE_BF_Analysis.ipynb` | BF 假设检验 |
| Omission 敏感性 | `Omission/Omission_Sensitivity_Analysis.ipynb` | Censor vs Drop 对比 |
| 刺激编码仿真 | `HDDM_Stim-Coding_Simulation/` | z-bias CRF 分析 |
| MATLAB 实验 | `Experiment/exp_matlab/` | 原始实验程序 |
| 数据验证 | `Experiment/exp_Check/data_verification.py` | 核对 88 个数据文件正确性 |

---

## 附录：PPT 制作建议

### 视觉风格建议
- 配色方案：学术蓝/灰为主色调，橙色/蓝色区分 Self/Stranger
- 图表风格：统一使用项目中的 matplotlib/seaborn 风格
- 代码展示：使用等宽字体，关键变量高亮
- 流程图：使用 Mermaid 或 draw.io 风格

### 引用规范
- 所有文献引用使用 APA 格式
- 关键文献列表（来自 RoadMap Phase 5.3）：
  - Sui et al. (2012) — SMT 范式
  - Ratcliff & McKoon (2008) — DDM 理论
  - Schulz et al. (2018) — GP in Psychology
  - Tran et al. (2021) — DDM 参数综述
  - Wiecki et al. (2013) — HDDM

### 数据来源标注
- 所有图表下方标注数据来源（文件路径或 RoadMap 章节引用）
- 真实数据：46/88 被试，8 组条件
- 生成数据：v2.4.5 模型输出
