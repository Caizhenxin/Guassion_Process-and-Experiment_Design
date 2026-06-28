# DDM参数反推可行性分析 — 计划

## 概述

分析从真实被试的 CRF 曲线反推 DDM 参数 (v, a, t, z) 的可行性，生成一份完整的分析文档，保存到 `1_Code/Python_for_Check/Visualization/DDM_Parameter_Explore/`。

---

## 当前状态

### 用户确认的当前思路（正向）
```
v, a, t, z (DDM参数) → Euler-Maruyama仿真 → Trial Level数据 → CRF可视化 + 参数扫描曲线
```
已通过上轮实现在 `visualization_app.html` 的 "DDM参数模式" 标签页中完成。

### 用户提出的逆向思路
```
真实被试CRF曲线 → ??? → 反推 v, a, t, z
```

### 现有相关基础设施
| 方法 | 文件 | 输入 | 输出 | 是否可恢复z？ |
|------|------|------|------|:---:|
| EZ-Diffusion | `automation/core/ez_diffusion.py` | RT均值+方差+正确率 | v, a, t0 | 否 (假设z=a/2) |
| HDDM MCMC | `Python_HDDM/step2_hddm_fit.py` | 全部试次(RT, response) | v, a, t, z 后验分布 | 是 |
| Parameter Recovery | `Parameter_Recovery.ipynb` | 仿真数据+真实参数对比 | GP恢复精度评估 | 是 |
| CRF仿真 | `HDDM_Stim-Coding_Simulation/` | DDM参数 → CRF曲线 | 仅正向 | N/A |

**关键发现**: 项目中没有从 CRF 曲线反推 DDM 参数的代码。

---

## 分析文档内容规划

### 输出文件
`1_Code/Python_for_Check/Visualization/DDM_Parameter_Explore/DDM_CRF_逆向推断可行性分析.md`

### 文档结构

#### 1. 问题定义
- 正向流程回顾
- 逆向问题的数学表述：给定实测 CRF 点集 {(RT_i, P_match_i)}，求 argmin_{v,a,t,z} Loss(CRF_sim, CRF_obs)

#### 2. 理论可行性分析
- **参数可辨识性**: 从信息论角度分析 v/a/t/z 四个参数对 CRF 曲线的不同影响
  - v (漂移率) → 影响 CRF 整体高度（上界命中率水平）
  - a (决策边界) → 影响 CRF 陡峭程度 + RT 分布宽度
  - z (起点) → 影响 CRF 垂直偏移（先验偏向）
  - t0 (非决策时间) → 影响 CRF 水平平移
- 结论：理论上 4 个参数均可从 CRF 中辨识，但可能存在参数间的补偿效应（如 z 偏移与 v 变化可产生相似的 CRF 平移）

#### 3. 三种可行方法

##### 方法 A: EZ-Diffusion（闭合解，最快但仅恢复3参数）
- 参考: Wagenmakers et al. (2007)
- 优点: 无需求解优化，即时计算
- 缺点: 仅恢复 v/a/t0，假设 z=a/2；仅使用汇总统计量，信息损失

##### 方法 B: 全试次 HDDM MCMC（金标准，恢复4参数）
- 参考: Wiecki et al. (2013)
- 优点: 恢复完整后验分布，含不确定性量化
- 缺点: 计算量大（MCMC采样），需要完整试次数据而非汇总CRF

##### 方法 C: CRF 匹配优化（用户提出的创新方法）
- 思路: 使用优化算法（差分进化/Bayesian Optimization）搜索参数空间，最小化 CRF 距离
- 损失函数: CRF 点集之间的 MSE / Wasserstein 距离 / KL 散度
- 优点: 直接利用 CRF 结构信息，可恢复全部 4 参数
- 缺点: 计算成本中等，需要合理的参数先验范围

#### 4. 方法 C 的推荐实现路径
1. 定义仿真函数: `simulate_crf(v, a, t0, z, n_trials)` → CRF 点集
2. 定义损失函数: `crf_loss(crf_simulated, crf_observed)`
3. 优化器选择: `scipy.optimize.differential_evolution` 或 `scipy.optimize.minimize`
4. 参数边界: 基于文献和已有 HDDM 后验设定合理范围
5. 多起点 + Bootstrap 获得置信区间

#### 5. 潜在风险与局限
- **参数补偿效应**: 不同的 (v, z) 组合可能产生相似的 CRF → 需要先验约束
- **CRF 分箱敏感性**: CRF 的形状依赖于分位数数量 → 建议 N≥5
- **噪声影响**: 真实数据噪声 → Bootstrap 重采样获得稳健估计
- **计算效率**: 每次 CRF 仿真需要大量试次 → 可并行化

#### 6. 参考文献
- Wagenmakers et al. (2007) — EZ-diffusion
- Wiecki et al. (2013) — HDDM
- Ratcliff & McKoon (2008) — DDM 基础
- Ratcliff & Tuerlinckx (2002) — DDM 参数估计方法
- Turner & Sederberg (2014) — 无似然方法 (ABC/SBI)
- Palestro et al. (2018) — 认知模型的联合建模

#### 7. 结论与建议
- 方法 A (EZ) 可作为快速基线
- 方法 B (HDDM) 是金标准但需完整试次数据
- 方法 C (CRF匹配) 在理论上可行，推荐作为后续实验性功能实现

---

## 实施步骤

### Step 1: 创建分析文档
- 文件: `1_Code/Python_for_Check/Visualization/DDM_Parameter_Explore/DDM_CRF_逆向推断可行性分析.md`
- 按照上述结构撰写完整分析

### Step 2: (可选) 验证 EZ-Diffusion
- 若用户需要，可添加一个快速的 `ez_diffusion_demo.py` 演示脚本

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `DDM_Parameter_Explore/DDM_CRF_逆向推断可行性分析.md` | 新建 | 完整可行性分析文档 |

---

## 验证

- 文档包含所有上述章节
- 每个方法有参考文献引用
- 方法 C 有明确的实现路径建议
