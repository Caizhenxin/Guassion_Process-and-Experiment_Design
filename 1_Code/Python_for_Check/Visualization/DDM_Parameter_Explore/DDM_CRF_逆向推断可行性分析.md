# DDM 参数逆向推断可行性分析

## 从实测 CRF 曲线反推 DDM 参数 (v, a, t, z)

---

## 1. 问题定义

### 1.1 当前正向流程（已实现）

```
设定 DDM 参数 (v, a, t, z)
    ↓
Euler-Maruyama 仿真 → 生成 trial 级数据 (RT, response)
    ↓
前端 CRF 可视化 + RT 分布 + 参数扫描曲线
```

### 1.2 提出的逆向问题

```
真实被试的实测 CRF 曲线: {(RT_i, P_match_i)}_{i=1..N}
    ↓
    反推?
    ↓
底层 DDM 参数 (v̂, â, t̂, ẑ)
```

**数学表述**：求解优化问题

```
argmin_{v,a,t,z}  Loss( CRF_simulated(v,a,t,z), CRF_observed )
```

其中 `CRF_simulated` 是通过 DDM 仿真生成的合成 CRF 曲线。

---

## 2. 理论可行性分析

### 2.1 参数可辨识性

DDM 的 4 个核心参数对 CRF 曲线有**不同的、可分离的影响**：

| 参数 | 对 CRF 的影响 | 影响方向 |
|------|-------------|---------|
| **v** (漂移率) | 影响 CRF 整体高度 | v↑ → 上界命中率↑，CRF 曲线上移 |
| **a** (决策边界) | 影响 CRF 陡峭程度 + RT 跨分位展开度 | a↑ → RT 变慢变散，CRF 更平缓 |
| **z** (起点比例) | 影响 CRF 垂直偏移（先验偏向） | z↑ → CRF 整体上移（偏向选择上界） |
| **t0** (非决策时间) | 影响 CRF 水平平移 | t0↑ → 所有 RT 分位点右移 |

**关键结论**：4 个参数在理论上均可从 CRF 中辨识，因为每个参数对 CRF 的"指纹"不同。

### 2.2 参数间补偿效应（潜在风险）

存在部分参数组合产生相似 CRF 的情况：

- **v 与 z 的补偿**：提高 v（更强的漂移向上界）与提高 z（起点更偏向上界）都可以使 CRF 上移。但两者的 RT 分布特征不同——v 变化更多影响正确/错误 RT 的相对关系，而 z 变化对称地影响两个边界的 RT。
- **a 与 v 的部分补偿**：较高的 a 和较低的 v 都可能产生较慢的 RT，但 a 主要增加 RT 方差。

**缓解策略**：需要合适的参数先验范围 + 使用 CRF 的完整形状信息（而非仅汇总统计量）来区分。

### 2.3 与 EZ-Diffusion 的关系

EZ-Diffusion（Wagenmakers et al., 2007）仅使用 **3 个汇总统计量**（正确率、正确 RT 均值、正确 RT 方差），因此只能恢复 **3 个参数**（v, a, t0），且假设 z = a/2。

CRF 包含 **更丰富的信息**（N 个分位点的 RT × P_match 联合分布），理论上可支持恢复 **全部 4 个参数**。

---

## 3. 三种可行方法对比

### 方法 A: EZ-Diffusion（闭合解）

| 属性 | 描述 |
|------|------|
| **参考** | Wagenmakers, Van Der Maas & Grasman (2007) |
| **原理** | 从汇总统计量（Pc, M, V）解析求解 v, a, t0 |
| **现有实现** | `automation/core/ez_diffusion.py`（已验证） |
| **优点** | 无需优化，即时计算，数学保证唯一解 |
| **缺点** | 仅恢复 3 参数（v, a, t0），z 强制为 a/2；仅使用汇总信息，丢弃 RT 分布细节 |

**适用场景**：快速基线估计，参数数量要求不高时使用。

---

### 方法 B: HDDM 层次贝叶斯 MCMC（金标准）

| 属性 | 描述 |
|------|------|
| **参考** | Wiecki, Sofer & Frank (2013) |
| **原理** | 对全部试次的 RT 和 choice 进行层次贝叶斯建模，MCMC 采样后验分布 |
| **现有实现** | `1_Code/Python_HDDM/step2_hddm_fit.py`（已验证） |
| **优点** | 恢复完整后验分布（均值 + 不确定性区间）；支持层次结构（群体 + 个体）；用户自定义参数依赖 |
| **缺点** | 计算量大（MCMC 采样数千次 × 多个被试）；**需要完整试次数据**，不能仅凭 CRF 汇总统计；不适用于实时交互 |

**适用场景**：正式统计推断，需要不确定性量化时使用。是当前项目 DDM 分析的**金标准**。

---

### 方法 C: CRF 匹配优化（用户提出的创新方法）

| 属性 | 描述 |
|------|------|
| **原理** | 使用数值优化器在参数空间中搜索，最小化模拟 CRF 与观测 CRF 之间的距离 |
| **损失函数** | CRF 点集之间的 MSE / MAE / Wasserstein 距离 |
| **优化器** | `scipy.optimize.differential_evolution`（全局） 或 `scipy.optimize.minimize`（局部） |
| **优点** | 直接利用 CRF 结构信息；可恢复全部 4 参数；适合交互式探索场景 |
| **缺点** | 每次迭代需大量仿真（全局优化约需数万次仿真）；存在局部最优风险；参数先验范围对结果影响大 |

#### 推荐实现路径

```
1. 定义仿真函数
   simulate_crf(v, a, t0, z, n_trials=1000, n_quantiles=5) → [{rtMean, upperProp}, ...]

2. 定义损失函数
   crf_loss(params, crf_observed):
       crf_sim = simulate_crf(*params)
       return mean_squared_error(crf_sim, crf_observed)

3. 优化器选择与参数边界
   from scipy.optimize import differential_evolution
   bounds = [(0.1, 4.0),   # v
             (0.3, 3.0),   # a
             (0.05, 0.5),  # t0
             (0.05, 0.95)] # z

4. 多起点 + Bootstrap 获得置信区间
   - 对观测 CRF 做 Bootstrap 重采样
   - 每个 Bootstrap 样本独立优化
   - 参数估计 = 所有 Bootstrap 估计的中位数, CI = 2.5%~97.5%

5. 加速策略
   - 预计算 CRF 模板库（网格化参数空间）
   - GPU 并行仿真
   - 使用代理模型（Bayesian Optimization）替代全局优化
```

---

## 4. 潜在风险与局限

### 4.1 参数补偿效应
- v 和 z 对 CRF 高度的影响存在部分重叠
- **缓解**：使用 CRF 的完整 5 点形状信息（而非仅汇总），结合 RT 分布的分位数信息

### 4.2 CRF 分箱敏感性
- CRF 形状依赖于分位数数量 N_quantile
- N 过小 → 信息丢失；N 过大 → 噪声放大
- **建议**：N = 5~10

### 4.3 仿真噪声
- 每次 DDM 仿真的随机性导致即使相同参数也可能产生不同 CRF
- **缓解**：增大仿真试次数（n_trials ≥ 1000），多次重复取平均

### 4.4 计算效率
- 每次 `simulate_crf` 需仿真 1000+ 试次 × Euler-Maruyama 迭代
- 全局优化可能需要数千到数万次函数评估
- **预估**：单线程 Python 下一次完整的差分进化优化约需 30~120 秒

### 4.5 模型假设
- 假设真实数据生成过程符合标准 DDM（无跨试次变异 sv/sz/st）
- 实际数据中的 contaminants（注意力波动、策略切换）可能扭曲 CRF
- **缓解**：可使用带 contaminant 的扩展 DDM 模型，但会增加参数数量

---

## 5. 参考文献

1. **Wagenmakers, E. J., Van Der Maas, H. L., & Grasman, R. P. (2007).** An EZ-diffusion model for response time and accuracy. *Psychonomic Bulletin & Review, 14*(1), 3-22.
   > EZ-diffusion 闭合解：从正确率和 RT 统计量反推 v, a, t0。

2. **Wiecki, T. V., Sofer, I., & Frank, M. J. (2013).** HDDM: Hierarchical Bayesian estimation of the Drift-Diffusion Model in Python. *Frontiers in Neuroinformatics, 7*, 14.
   > HDDM 层次贝叶斯 DDM 拟合框架，当前项目的参数估计金标准。

3. **Ratcliff, R., & McKoon, G. (2008).** The diffusion decision model: theory and data for two-choice decision tasks. *Neural Computation, 20*(4), 873-922.
   > DDM 的完整理论基础，包含参数可辨识性讨论。

4. **Ratcliff, R., & Tuerlinckx, F. (2002).** Estimating parameters of the diffusion model: Approaches to dealing with contaminant reaction times and parameter variability. *Psychonomic Bulletin & Review, 9*(3), 438-481.
   > DDM 参数估计方法综述，讨论 contaminant 处理和参数恢复精度。

5. **Turner, B. M., & Sederberg, P. B. (2014).** A generalized, likelihood-free method for posterior estimation. *Psychonomic Bulletin & Review, 21*(2), 227-250.
   > 无似然推断方法（ABC），适用于 CRF 匹配这类无法写出解析似然的问题。

6. **Palestro, J. J., et al. (2018).** A tutorial on joint modeling. In *Computational Models of Brain and Behavior* (pp. 299-310).
   > 认知模型联合建模教程，讨论仿真基推断方法。

7. **Voss, A., & Voss, J. (2007).** Fast-dm: A free program for efficient diffusion model analysis. *Behavior Research Methods, 39*(4), 767-775.
   > Fast-dm 参数估计软件，使用 Kolmogorov-Smirnov 统计量匹配完整 RT 分布。

8. **Voss, A., Voss, J., & Lerche, V. (2015).** Assessing cognitive processes with diffusion model analyses: A tutorial based on fast-dm-30. *Frontiers in Psychology, 6*, 336.
   > Fast-dm-30 教程，讨论基于完整分布（而非仅汇总统计量）的参数估计优势。

---

## 6. 结论与建议

| 方法 | 可行性 | 精度 | 速度 | 推荐场景 |
|------|:---:|:---:|:---:|------|
| **A: EZ-Diffusion** | 已验证 | 中等（3参数） | 极快 | 快速基线估计 |
| **B: HDDM MCMC** | 已验证（金标准） | 高（4参数+不确定性） | 慢（分钟级） | 正式统计推断 |
| **C: CRF 匹配优化** | **理论可行** | 中高（4参数） | 中等（秒~分钟级） | 交互式探索、快速反推 |

### 最终建议

1. **方法 C（CRF 匹配优化）在理论上完全可行**，其本质是仿真基推断（Simulation-Based Inference），有充分的文献支持（Turner & Sederberg 2014; Palestro et al. 2018）。

2. **优先实现路径**：
   - 先用 EZ-Diffusion（方法 A）作为基线快速估计
   - 再以 EZ 结果作为优化初始点，运行 CRF 匹配优化（方法 C）精调参数
   - 最终用 HDDM MCMC（方法 B）做正式验证

3. **作为后续实验性功能，推荐实现方法 C**：
   - 在 `DDM_Parameter_Explore/` 下创建 `crf_inverse_fit.py`
   - 集成到 `visualization_app.html` 的 DDM 标签页
   - 用户输入实测 CRF 数据 → 一键反推 DDM 参数 → 叠图对比

---

*分析日期: 2026-06-28*
