# Omission 纳入建模的 LAN+OPN 实施作战计划

> **目标**: 参考 Leng et al. (2025) 的 LAN+OPN 方法论，完成本项目 omission 部分的核心实现。
>
> **读者**: 你自己——请按顺序逐节阅读并执行。每节末尾有 ✅ 验证点，确保前一步正确再继续。
>
> **前提**: 你已有 Docker HDDM 环境，已完成原有 8 组 HDDM 拟合和 Censor vs Drop 敏感性分析。

---

## 目录

|       Part       | 内容                                         |       预计时间       | 新写代码量 |
| :--------------: | :------------------------------------------- | :------------------: | :--------: |
| **Part 1** | 论文方法论快速复习                           |     30 min 阅读     |     0     |
| **Part 2** | 准备工作：环境与现有代码速览                 |         1 h         |     0     |
| **Part 3** | 阶段一：DDM 仿真器适配（为 OPN 训练做准备）  |        2-3 h        |  ~100 行  |
| **Part 4** | 阶段二：OPN 训练——遗漏概率网络的构建与训练 |        3-4 h        |  ~200 行  |
| **Part 5** | 阶段三：联合似然函数的 PyMC 实现             |        4-6 h        |  ~250 行  |
| **Part 6** | 阶段四：在真实数据上运行 LAN+OPN MCMC        | 2-3 h (计算时间另计) |  ~150 行  |
| **Part 7** | 阶段五：对比 HDDM Censor vs PyMC LAN+OPN     |        2-3 h        |  ~100 行  |
| **Part 8** | 常见问题排查                                 |          —          |     —     |

> **总时间估计**: ~20-25 小时（含计算等待）。建议分 4-5 天完成。

---

## Part 1: 论文方法论快速复习

### 1.1 论文到底做了什么

Leng et al. (2025) 处理的核心问题是：

> 在有 deadline 的决策实验中，部分试次没有反应（omission）。传统做法是直接丢弃这些试次（"LAN-only"）。论文证明了这会严重偏倚参数估计——即使 omission 率低至 5%。

论文的解决方案是 **LAN+OPN 联合似然**：

```
log_l(data | theta, deadline) = 
    Σ LAN(rt_i, choice_i | theta)         ← 所有观测试次 (rt ≤ deadline)
    + |O| × OPN(omission | theta, deadline) ← omission 试次的惩罚项
```

其中：

- **LAN** = Likelihood Approximation Network，输入 (rt, choice, theta)，输出该试次的 log-likelihood
- **OPN** = Omission Probability Network，输入 (theta, deadline)，输出 log-probability of omission

### 1.2 为什么你可以跳过 LAN，直接用解析似然

论文使用 LAN 是为了兼容 ANGLE/WEIBULL 等复杂边界。但你的项目只用**恒定边界 DDM**，而恒定边界 DDM 的似然函数有解析解（Wiener diffusion / 一阶通过时间分布）。

**这意味着**：你不需要训练 LAN。你只需训练 OPN，然后在 MCMC 中：

```python
# 伪代码：
def log_likelihood(theta, data):
    # 观测试次：使用 HDDM 已有的解析似然
    ll_observed = hddm_likelihood(data_observed, theta)
  
    # Omission 试次：使用你训练的 OPN
    ll_omission = n_omissions * opn.predict(theta, deadline)
  
    return ll_observed + ll_omission
```

这是本计划最大的简化——你把原本需要的 2 个神经网络（LAN + OPN）减少到只需训练 1 个（OPN）。

### 1.3 论文的训练数据来源

OPN 的训练数据来自模拟器：

1. 从参数 prior 采样：`v, a, z, t0, deadline`
2. 对每组参数运行大量 DDM 模拟（论文用 5000 次/组）
3. 统计 omission 比例 → 作为训练标签
4. 训练神经网络：`(v, a, t, z, deadline) → omission_probability`

**你需要实现的正是这个 pipelin**。

### 1.4 你需要写的新代码

| 模块                 | 说明                                               | 新写/复用      |
| :------------------- | :------------------------------------------------- | :------------- |
| DDM 仿真器（批量版） | 已有`simulate_ddm_with_deadline()`，需要批量版本 | 少量改写       |
| OPN 训练             | 生成训练数据 + 训练神经网络                        | **全新** |
| 联合似然函数         | PyMC 中实现`lan_opn_logp()`                      | **全新** |
| MCMC 拟合            | PyMC 层级贝叶斯模型                                | **全新** |
| 结果对比             | 已有`sensitivity_comparison.csv`，对比即可       | 少量改写       |

---

## Part 2: 准备工作

### 2.1 确认你的环境

在 Docker (hcp4715/hddm) 中打开终端，运行以下验证：

```python
# ===== 验证 1: Python 版本和关键包 =====
import sys; print(f"Python {sys.version}")

import numpy as np;  print(f"numpy  {np.__version__}")
import pymc as pm;   print(f"pymc   {pm.__version__}")
import pytensor;     print(f"pytensor {pytensor.__version__}")
import arviz as az;  print(f"arviz  {az.__version__}")
import torch;        print(f"torch  {torch.__version__}")

# 验证 sklearn（用于 OPN 训练）
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
print("✅ sklearn OK")

# 验证数据读取
import pandas as pd
from pathlib import Path
BASE_DIR = Path("/home/jovyan/work")
csv_files = sorted((BASE_DIR / "2_Data/Real_Data/HDDM_Ready").glob("*.csv"))
print(f"找到 {len(csv_files)} 个 HDDM 数据文件 ✅" if csv_files else "❌ 找不到数据文件！")

# ===== 验证 2: 已有 DDM 仿真器能用 =====
sys.path.insert(0, str(BASE_DIR / "1_Code/Python_for_Generate"))
from Backend.model_engine import simulate_ddm_with_deadline
rt, resp, omission, source = simulate_ddm_with_deadline(
    v=1.5, a=1.2, z=0.6, t0=0.3, deadline_s=0.63
)
print(f"测试仿真: RT={rt:.3f}s, resp={resp}, omission={omission} ✅")
```

> ✅ **验证通过标准**: 所有 import 不报错，DDM 仿真返回非 NaN 值。

### 2.2 创建新的工作目录

```python
import os
from pathlib import Path

BASE_DIR = Path("/home/jovyan/work")
OPN_DIR = BASE_DIR / "1_Code/Python_for_Check/Omission_LAN_OPN"
DATA_DIR = BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN"
FIG_DIR  = BASE_DIR / "3_Figures/Omission_LAN_OPN"

for d in [OPN_DIR, DATA_DIR, FIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print(f"代码目录: {OPN_DIR}")
print(f"数据目录: {DATA_DIR}")
print(f"图表目录: {FIG_DIR}")
```

### 2.3 了解项目已有结构

花 5 分钟浏览以下文件，不需要逐行读，知道它们在哪即可：

| 文件                                                                     | 用途                                       |
| :----------------------------------------------------------------------- | :----------------------------------------- |
| `1_Code/Python_for_Check/Omission/Omission_Sensitivity_Analysis.ipynb` | 已完成的敏感性分析（参考数据处理）         |
| `1_Code/Python_for_Generate/Backend/model_engine.py`                   | DDM 仿真器`simulate_ddm_with_deadline()` |
| `2_Data/Generate_Data/Omission_Sensitivity/censor_traces/`             | Censor 方案的 HDDM 拟合结果                |
| `2_Data/Generate_Data/Omission_Sensitivity/sensitivity_comparison.csv` | Censor vs Drop 参数对比表                  |

> ✅ **验证**: 你能打开这些文件并找到相关函数/数据。

---

## Part 3: 阶段一 —— DDM 仿真器适配

### 3.1 目标

把已有的 `simulate_ddm_with_deadline()` 包装成一个**批量版本**，能够：

- 输入：`(N, v, a, z, t0, deadline)` → 对同组参数运行 N 次仿真
- 输出：omission 的次数

### 3.2 为什么需要批量版

OPN 训练需要大量数据（论文用 10 万组参数 × 5000 次仿真/组 = 5 亿次仿真）。单次单次跑太慢。

**关键优化**：对同一组参数 (v, a, z, t0, deadline)，N 次仿真可以向量化——所有试次使用相同的 Euler stepper 参数，只是噪声序列不同。

### 3.3 代码实现

创建 `1_Code/Python_for_Check/Omission_LAN_OPN/opn_simulator.py`：

```python
"""
OPN 训练用的批量 DDM 仿真器
基于 model_engine.py 中的 simulate_ddm_with_deadline() 改写
"""
import numpy as np
from numba import njit  # 如果有 numba，速度提升 10-50x

# ============================================================
# 方案 A: 纯 NumPy 向量化版本（推荐）
# ============================================================

def simulate_ddm_batch_vectorized(
    v: float, a: float, z: float, t0: float,
    deadline_s: float, n_trials: int = 5000,
    dt: float = 0.001,
) -> int:
    """
    对同一组 (v, a, z, t0, deadline) 运行 n_trials 次 DDM 仿真，
    返回 omission 次数。
  
    使用向量化实现：所有试次并行 Euler stepper。
    """
    decision_budget = deadline_s - t0
    if decision_budget <= dt:
        return n_trials
  
    max_steps = int(decision_budget / dt)
  
    # 初始化：所有试次的证据位置
    x = np.full(n_trials, z, dtype=np.float64)
    # 跟踪哪些试次已完成
    active = np.ones(n_trials, dtype=bool)
    response = np.zeros(n_trials, dtype=np.int8)
    omission = np.ones(n_trials, dtype=bool)  # 默认全是 omission
  
    for step in range(max_steps):
        if not active.any():
            break
      
        # Euler-Maruyama step（只更新仍活跃的试次）
        n_active = active.sum()
        noise = np.random.randn(n_active)
        dx = v * dt + np.sqrt(dt) * noise
        x[active] += dx
      
        # 上边界检查
        hit_upper = (x >= a) & active
        if hit_upper.any():
            response[hit_upper] = 1
            omission[hit_upper] = False
            active[hit_upper] = False
      
        # 下边界检查
        hit_lower = (x <= 0.0) & active
        if hit_lower.any():
            response[hit_lower] = 0
            omission[hit_lower] = False
            active[hit_lower] = False
  
    return omission.sum()


# ============================================================
# 方案 B: Numba JIT 加速版本（如已安装 numba）
# ============================================================

try:
    from numba import njit
  
    @njit
    def simulate_ddm_batch_numba(
        v: float, a: float, z: float, t0: float,
        deadline_s: float, n_trials: int = 5000,
        dt: float = 0.001,
    ) -> int:
        """Numba JIT 编译的单线程批量 DDM 仿真"""
        decision_budget = deadline_s - t0
        if decision_budget <= dt:
            return n_trials
      
        max_steps = int(decision_budget / dt)
      
        x = np.full(n_trials, z)
        active = np.ones(n_trials, dtype=np.bool_)
        omission_count = 0
      
        for step in range(max_steps):
            n_active = active.sum()
            if n_active == 0:
                break
          
            noise = np.random.randn(n_active)
            dx = v * dt + np.sqrt(dt) * noise
          
            for i in range(n_trials):
                if not active[i]:
                    continue
                x[i] += dx[i - (active[:i].sum() if i > 0 else 0) 
                         if n_active < n_trials else i]
              
                if x[i] >= a:
                    active[i] = False
                elif x[i] <= 0.0:
                    active[i] = False
                    omission_count += 1
      
        # 剩余的活跃试次 = omission
        omission_count += active.sum()
        return omission_count
  
    # 如果 numba 可用，默认使用 numba 版本
    SIMULATOR = simulate_ddm_batch_numba
    print("✅ 使用 Numba JIT 加速版本")
  
except ImportError:
    SIMULATOR = simulate_ddm_batch_vectorized
    print("⚠️ Numba 未安装，使用纯 NumPy 版本（较慢但可运行）")
```

### 3.4 测试仿真器

```python
# ===== 测试 =====
import time
from opn_simulator import SIMULATOR

# 测试 1: 高 omission 率参数
n_om = SIMULATOR(v=-1.0, a=2.0, z=1.0, t0=0.3, deadline_s=0.6, n_trials=1000)
rate = n_om / 1000
print(f"高 omission 参数: {n_om}/1000 = {rate:.1%} (预期 >50%)")

# 测试 2: 低 omission 率参数
n_om = SIMULATOR(v=3.0, a=0.8, z=0.4, t0=0.2, deadline_s=1.5, n_trials=1000)
rate = n_om / 1000
print(f"低 omission 参数: {n_om}/1000 = {rate:.1%} (预期 <5%)")

# 测试 3: 速度基准
t0 = time.time()
for _ in range(10):
    SIMULATOR(v=1.5, a=1.2, z=0.6, t0=0.3, deadline_s=0.8, n_trials=5000)
elapsed = time.time() - t0
print(f"10 × 5000 trials: {elapsed:.1f}s → {50000/elapsed:.0f} trials/s")
```

> ✅ **验证标准**:
>
> - 高 omission 参数 >50%
> - 低 omission 参数 <10%
> - 速度 ≥1000 trials/s（Numpy）或 ≥10000 trials/s（Numba）

### 3.5 总结：路径选择

| 根据你的 Docker 环境  | 选择方案                                        |
| :-------------------- | :---------------------------------------------- |
| 已安装了 numba        | 方案 B（JIT 编译，速度快 10-50x）               |
| 未安装 numba 但愿意装 | `pip install numba` → 方案 B                 |
| 不想额外安装          | 方案 A（纯 NumPy，也可用但生成全部数据需约 8h） |

---

## Part 4: 阶段二 —— OPN 训练

### 4.1 OPN 是什么

OPN = Omission Probability Network = 一个神经网络，输入 `(v, a, t, z, deadline)`，输出 `log(p_omission)`。

论文用简单的 MLP 结构，你可以参考以下三层网络：

```
Input (5) → Dense(128, ReLU) → Dense(64, ReLU) → Dense(32, ReLU) → Output (1)
```

### 4.2 生成训练数据

创建 `1_Code/Python_for_Check/Omission_LAN_OPN/opn_train.py`：

```python
"""
OPN 训练脚本
步骤:
  1. 从参数 prior 采样 (v, a, t, z, deadline)
  2. 对每组参数运行批量 DDM 仿真
  3. 统计 omission 比例作为训练标签
  4. 训练 MLP 回归器
"""
import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import time
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from opn_simulator import SIMULATOR

BASE_DIR = Path("/home/jovyan/work")
DATA_DIR = BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Step 1: 定义参数 prior 和训练数据量
# ============================================================

# 基于本项目的参数范围和文献 (Tran et al., 2021) 的经验分布
# 单位：秒
PRIOR_RANGES = {
    'v':   (-5.0, 5.0),    # 漂移率
    'a':   (0.2, 3.0),     # 边界分离
    't':   (0.1, 0.7),     # 非决策时间
    'z':   (0.0, 1.0),     # 起始点（相对值 zr，实际 z = zr * a）
    'deadline': (0.3, 2.5),# deadline（秒）——覆盖本项目 330ms-2000ms 范围
}

# 训练数据量（可根据时间调整）
N_TRAIN_SAMPLES = 50000   # 5 万组参数
N_SIM_PER_SAMPLE = 5000   # 每组参数仿真 5000 次

# 子集大小（如果 5 万组太慢，先用 5000 组做实验）
N_TRAIN_SAMPLES_FAST = 5000

print(f"目标训练数据: {N_TRAIN_SAMPLES} 组参数 × {N_SIM_PER_SAMPLE} 次仿真")
print(f"预估时间: {N_TRAIN_SAMPLES * N_SIM_PER_SAMPLE / 5000 / 3600:.1f} 小时")

# ============================================================
# Step 2: 生成训练数据
# ============================================================

def generate_opn_training_data(n_samples, n_sim, prior_ranges, seed=42):
    """生成 OPN 训练数据"""
    np.random.seed(seed)
  
    X = np.zeros((n_samples, 5))  # (v, a, t, z, deadline)
    y = np.zeros(n_samples)       # omission_rate
  
    t_start = time.time()
  
    for i in range(n_samples):
        # 从 prior 均匀采样
        v  = np.random.uniform(*prior_ranges['v'])
        a  = np.random.uniform(*prior_ranges['a'])
        t0 = np.random.uniform(*prior_ranges['t'])
        zr = np.random.uniform(*prior_ranges['z'])  # 相对起始点 zr ∈ (0, 1)
        z  = zr * a  # 绝对起始点
        d  = np.random.uniform(*prior_ranges['deadline'])
      
        # 跳过不合逻辑的组合
        if d <= t0:
            continue
      
        # 批量仿真
        n_om = SIMULATOR(v=v, a=a, z=z, t0=t0, deadline_s=d, n_trials=n_sim)
      
        X[i] = [v, a, t0, zr, d]
        y[i] = n_om / n_sim
      
        # 进度
        if (i + 1) % (n_samples // 20) == 0:
            elapsed = time.time() - t_start
            eta = elapsed / (i + 1) * (n_samples - i - 1)
            print(f"  进度: {i+1}/{n_samples} ({100*(i+1)/n_samples:.0f}%) | "
                  f"耗时: {elapsed/60:.1f}min | 预计剩余: {eta/60:.1f}min")
  
    elapsed = time.time() - t_start
    print(f"✅ 生成完成！总耗时: {elapsed/60:.1f} min")
  
    return X, y

# 先用快速模式测试
print("\n----- 快速测试模式 (5000 组) -----")
X_fast, y_fast = generate_opn_training_data(
    n_samples=N_TRAIN_SAMPLES_FAST,
    n_sim=N_SIM_PER_SAMPLE,
    prior_ranges=PRIOR_RANGES,
)

# 保存
np.savez_compressed(
    DATA_DIR / "opn_training_data_fast.npz",
    X=X_fast, y=y_fast,
)
print(f"快速数据已保存: {DATA_DIR / 'opn_training_data_fast.npz'}")
```

### 4.3 训练 OPN 模型

继续在同一个文件中：

```python
# ============================================================
# Step 3: 训练 OPN
# ============================================================

def train_opn(X, y, test_size=0.2, random_state=42):
    """训练 OPN（MLP 回归器）"""
    # 划分训练/测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
  
    # 特征标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
  
    # 训练 MLP
    opn = MLPRegressor(
        hidden_layer_sizes=(128, 64, 32),
        activation='relu',
        solver='adam',
        alpha=0.001,           # L2 正则化
        batch_size=256,
        learning_rate='adaptive',
        learning_rate_init=0.001,
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=random_state,
        verbose=True,
    )
  
    opn.fit(X_train_scaled, y_train)
  
    # 评估
    train_score = opn.score(X_train_scaled, y_train)
    test_score = opn.score(X_test_scaled, y_test)
  
    print(f"\n训练 R²: {train_score:.4f}")
    print(f"测试 R²: {test_score:.4f}")
    print(f"最终损失: {opn.loss_:.6f}")
    print(f"迭代次数: {opn.n_iter_}")
  
    # 简单诊断
    y_pred = opn.predict(X_test_scaled)
    mae = np.mean(np.abs(y_pred - y_test))
    print(f"MAE: {mae:.4f} ({mae*100:.1f} percentage points)")
  
    return opn, scaler, (train_score, test_score, mae)


print("\n----- 训练 OPN (快速模式) -----")
opn, scaler, metrics = train_opn(X_fast, y_fast)

# 保存模型
import joblib
joblib.dump(opn, DATA_DIR / "opn_model_fast.joblib")
joblib.dump(scaler, DATA_DIR / "opn_scaler_fast.joblib")
print(f"模型已保存: {DATA_DIR / 'opn_model_fast.joblib'}")

# ============================================================
# Step 4: 如果快速模式可行，生成完整数据并训练完整模型
# ============================================================

if input("\n快速模式通过？输入 'yes' 继续完整训练: ").strip().lower() == 'yes':
    print("\n----- 完整训练模式 (50000 组) -----")
    X_full, y_full = generate_opn_training_data(
        n_samples=N_TRAIN_SAMPLES,
        n_sim=N_SIM_PER_SAMPLE,
        prior_ranges=PRIOR_RANGES,
    )
    np.savez_compressed(DATA_DIR / "opn_training_data_full.npz", X=X_full, y=y_full)
  
    opn_full, scaler_full, metrics_full = train_opn(X_full, y_full)
    joblib.dump(opn_full, DATA_DIR / "opn_model_full.joblib")
    joblib.dump(scaler_full, DATA_DIR / "opn_scaler_full.joblib")
```

### 4.4 OPN 验证

```python
# ===== OPN 诊断图 =====
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

param_names = ['v (drift rate)', 'a (boundary)', 't0 (nondecision)', 
               'zr (bias)', 'deadline']

for i in range(5):
    ax = axes[i]
    ax.scatter(X_test[:, i], y_test, alpha=0.3, s=5, label='True')
    ax.scatter(X_test[:, i], y_pred, alpha=0.3, s=5, label='Predicted')
    ax.set_xlabel(param_names[i])
    ax.set_ylabel('Omission Rate')
    ax.legend(fontsize=7)
    ax.set_title(f'{param_names[i]} vs Omission Rate')

# 残差图
ax = axes[5]
residuals = y_pred - y_test
ax.hist(residuals, bins=50, alpha=0.7, edgecolor='black')
ax.axvline(0, color='red', linestyle='--')
ax.set_xlabel('Residual (Pred - True)')
ax.set_ylabel('Count')
ax.set_title(f'Residual Distribution (MAE={metrics[2]:.4f})')

plt.tight_layout()
plt.savefig(BASE_DIR / "3_Figures/Omission_LAN_OPN/opn_diagnostics.png", dpi=150)
plt.show()
```

> ✅ **验证标准**:
>
> - 测试 R² > 0.90（否则增加训练数据量或调整网络结构）
> - MAE < 0.03（即 3 个百分点）
> - 残差分布对称、无系统性偏差
> - 诊断图中预测值跟随真实值的趋势

### 4.5 如果 OPN 训练质量不够好

| 问题                                   | 解决方案                                                        |
| :------------------------------------- | :-------------------------------------------------------------- |
| R² < 0.85                             | 增加训练数据量（完整 5 万组）；增加网络层数                     |
| MAE > 0.05                             | 增大`N_SIM_PER_SAMPLE`（减少仿真噪声）；增加 `alpha` 正则化 |
| omission_rate 接近 0 或 1 的区域预测差 | 增加该区域的采样密度（调整 prior ranges）                       |
| 训练太慢                               | 使用 numba 加速；减少`N_TRAIN_SAMPLES` 先用小样本验证         |

---

## Part 5: 阶段三 —— 联合似然函数的 PyMC 实现

### 5.1 设计思路

这是实现的核心。你需要在 PyMC 中自定义似然函数，同时使用：

- 观测试次 → Wiener 解析似然（`pytensor` 实现）
- Omission 试次 → OPN 预测的 log-probability

```python
# 核心 log-likelihood 结构
def custom_logp(observed_data, omission_count, deadline, opn, scaler):
    # theta = (v, a, t, z) from PyMC
    # observed_data = (rt, response) for trials with rt <= deadline
  
    ll_observed = wiener_logp(rt, response, v, a, t, z)  # 解析似然（LAN 的替代）
    ll_omission = omission_count * opn_logp(v, a, t, z, deadline, opn, scaler)
  
    return ll_observed + ll_omission
```

### 5.2 实现 Wiener 解析似然

DDM 的一阶通过时间分布（Wiener first-passage time）的 log-PDF。你不需要自己推导——可以直接使用 PyMC 的 `pm.Wiener` 分布，或者用 `pytensor` 实现：

```python
"""
Wiener 解析似然函数（DDM 的 log-PDF）
"""
import pytensor.tensor as pt

def wiener_logp(rt, response, v, a, z, t0):
    """
    Wiener 一阶通过时间分布的 log-PDF。
  
    参数:
      rt: 反应时 (s) - 必须 > t0
      response: 1 (上界) or 0 (下界)
      v: 漂移率
      a: 边界分离 (> 0)
      z: 相对起始点 zr = z/a (∈ (0, 1))
      t0: 非决策时间 (s)
  
    返回:
      log probability density
    """
    # 确保参数合法性
    rt_adj = pt.maximum(rt - t0, 1e-10)  # 调整后的 RT
  
    # Wiener 分布的无限级数解（Navarro & Fuss, 2009）
    # 通常取前 k 项近似即可
  
    def wiener_small_time(rt_adj, v, a, z, k_max=20):
        """小 RT 近似（更多项）"""
        # 使用 pytensor 实现
        log_lik = pt.zeros_like(rt_adj)
        alpha = (a * z)
        for k in range(-k_max, k_max + 1):
            exponent = -(a * a * (z + 2 * k) ** 2) / (2 * rt_adj)
            log_lik += (a * (z + 2 * k)) / pt.sqrt(2 * pt.pi * rt_adj ** 3) * pt.exp(exponent)
        return pt.log(log_lik)
  
    # 实际使用 pm.Wiener 更简单：
    # return pm.Wiener.logp(rt_adj, v, a, z, 0.1)  # 第四个参数是 sv
  
    return wiener_small_time(rt_adj, v, a, z)
```

> **更好的选择**: PyMC 的 `pm.Wiener` 已经内置了 Wiener 似然。使用它比手写更可靠。

### 5.3 构建完整 PyMC 模型

创建 `1_Code/Python_for_Check/Omission_LAN_OPN/lan_opn_fit.py`：

```python
"""
LAN+OPN 联合似然的 PyMC 层级贝叶斯模型
"""
import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt
import arviz as az
from pathlib import Path
import joblib
import pickle

BASE_DIR = Path("/home/jovyan/work")

# ============================================================
# Step 1: 加载 OPN 模型
# ============================================================

opn = joblib.load(BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN/opn_model_full.joblib")
scaler = joblib.load(BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN/opn_scaler_full.joblib")

def opn_logp(v, a, t0, zr, deadline, opn, scaler):
    """
    用 OPN 预测 log-p_omission。
  
    注意: OPN 训练时输出的是 omission_rate（概率值，0-1），
    需要转为 log-probability。
    """
    # 构造特征矩阵
    X = np.column_stack([v, a, t0, zr, deadline])
  
    # 注意：scaler.transform 是 numpy 操作，PyMC 中需要用 pytensor 包装
    # 这里简化——在自定义 logp 函数中使用 numpy
    X_scaled = scaler.transform(X)
    p_omission = opn.predict(X_scaled)
  
    # clamp 避免 log(0)
    p_omission = np.clip(p_omission, 1e-10, 1 - 1e-10)
  
    return np.log(p_omission)


# ============================================================
# Step 2: 加载并预处理真实数据
# ============================================================

def prepare_data_for_lan_opn(group_id, P, T_ms, W_ms):
    """
    准备 LAN+OPN 格式的数据。
  
    返回:
      obs_data: pd.DataFrame (仅 rt <= deadline 的试次, 含 subj_idx, rt, response)
      n_omissions: int (omission 试次数)
      deadline_s: float (deadline, 秒)
    """
    csv_path = BASE_DIR / f"2_Data/Real_Data/HDDM_Ready/hddm_data_group{group_id}_P{P}_T{T_ms}_W{W_ms}.csv"
    df = pd.read_csv(csv_path)
  
    deadline_s = (T_ms + W_ms) / 1000.0
  
    # 分离观测和 omission 试次
    is_omission = df['omission'] == 1
    n_omissions = is_omission.sum()
  
    obs_data = df[~is_omission].copy()
  
    print(f"  Group {group_id}: {len(df)} total, {n_omissions} omission ({n_omissions/len(df)*100:.1f}%), "
          f"{len(obs_data)} observed")
  
    return obs_data, n_omissions, deadline_s


# ============================================================
# Step 3: 构建 PyMC 模型并拟合
# ============================================================

def fit_lan_opn_model(obs_data, n_omissions, deadline_s, draws=2000, tune=500):
    """
    使用 LAN+OPN 联合似然拟合层级贝叶斯 DDM。
  
    由于 OPN 的 logp 是自定义函数（非标准 PyMC 分布），
    这里使用 pm.Potential 将其加入似然。
    """
    n_subjects = obs_data['subj_idx'].nunique()
    subject_idx = obs_data['subj_idx'].values
  
    # 数据转 NumPy
    rt = obs_data['rt'].values
    response = obs_data['response'].values  # HDDM 编码: 1=上界, 0=下界
  
    with pm.Model() as model:
        # ===== 组水平先验 =====
        mu_v = pm.Normal('mu_v', mu=0, sigma=3)
        mu_a = pm.Normal('mu_a', mu=1, sigma=1)
        mu_t = pm.Normal('mu_t', mu=0.3, sigma=0.1)
        mu_z = pm.Beta('mu_z', alpha=5, beta=5)  # zr
      
        sigma_v = pm.HalfNormal('sigma_v', sigma=1)
        sigma_a = pm.HalfNormal('sigma_a', sigma=0.5)
        sigma_t = pm.HalfNormal('sigma_t', sigma=0.1)
        sigma_z = pm.HalfNormal('sigma_z', sigma=0.2)
      
        # ===== 被试水平参数 =====
        v_subj = pm.Normal('v_subj', mu=mu_v, sigma=sigma_v, shape=n_subjects)
        a_subj = pm.LogNormal('a_subj', mu=pt.log(mu_a), sigma=sigma_a, shape=n_subjects)
        t_subj = pm.TruncatedNormal('t_subj', mu=mu_t, sigma=sigma_t, 
                                     lower=0.05, upper=1.0, shape=n_subjects)
        z_subj = pm.Beta('z_subj', alpha=mu_z*10, beta=(1-mu_z)*10, shape=n_subjects)
      
        # ===== 观测试次的似然（Wiener） =====
        for s in range(n_subjects):
            mask = subject_idx == s
            if mask.sum() == 0:
                continue
            pm.Wiener(
                f'wiener_{s}',
                v=v_subj[s],
                a=a_subj[s],
                z=z_subj[s],
                t=t_subj[s],
                sv=0.1,  # 跨试次漂移率变异（固定）
                observed=dict(rt=rt[mask], response=response[mask]),
            )
      
        # ===== Omission 似然（OPN） =====
        # 使用 pm.Potential 添加自定义似然项
      
        # 获取每个被试的 omission 数
        # 简化：假设 omission 均匀分布在所有被试中
        om_per_subject = n_omissions // n_subjects
      
        def opn_log_likelihood():
            # 提取参数
            v_vals = v_subj.eval()
            a_vals = a_subj.eval()
            t_vals = t_subj.eval()
            z_vals = z_subj.eval()
          
            total_ll = 0.0
            for s in range(n_subjects):
                # 构造 OPN 输入
                X_input = np.array([[v_vals[s], a_vals[s], t_vals[s], 
                                     z_vals[s], deadline_s]])
                X_scaled = scaler.transform(X_input)
                p_om = opn.predict(X_scaled)[0]
                p_om = np.clip(p_om, 1e-10, 1 - 1e-10)
              
                # log-likelihood of omission
                total_ll += om_per_subject * np.log(p_om)
          
            return total_ll
      
        # 将 OPN 似然加入模型
        pm.Potential('opn_likelihood', opn_log_likelihood())
      
        # ===== MCMC 采样 =====
        trace = pm.sample(
            draws=draws,
            tune=tune,
            chains=4,
            cores=4,
            return_inferencedata=True,
            random_seed=42,
        )
  
    return model, trace


# ============================================================
# Step 4: 对 G5 运行测试
# ============================================================

if __name__ == "__main__":
    # 先用 G5（遗漏率最低，最容易）做测试
    obs_data, n_omissions, deadline_s = prepare_data_for_lan_opn(5, 8, 100, 1100)
  
    print(f"\n开始 PyMC 拟合...")
    model, trace = fit_lan_opn_model(obs_data, n_omissions, deadline_s, draws=2000, tune=500)
  
    # 保存
    import arviz as az
    az.to_netcdf(trace, BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN/lan_opn_trace_G5.nc")
  
    # 诊断
    summary = az.summary(trace, var_names=['mu_v', 'mu_a', 'mu_t', 'mu_z'])
    print("\n参数后验摘要:")
    print(summary)
```

### 5.4 关于 `pm.Potential` 的注意事项

上面的实现在 `pm.Potential` 中使用了 `.eval()` 来提取参数值。这**不是**标准的 PyMC 用法——PyMC 通常要求 likelihood 中的所有操作用 pytensor 张量完成以支持自动微分。

因为 OPN 是一个 scikit-learn 模型（Numpy-based），不能直接在 pytensor 梯度计算中使用。有几种解决方案：

| 方案                                                                     | 优缺点                                 |
| :----------------------------------------------------------------------- | :------------------------------------- |
| **方案 A**: `pm.Potential` + 数值近似                            | 不是完全贝叶斯，但可跑通；适合初步验证 |
| **方案 B**: 将 OPN 重写为 pytensor 网络                            | 完全贝叶斯，但需要重新实现 MLP 推理    |
| **方案 C**: 两步法——先拟合 observed-only MCMC，再用手算 OPN 修正 | 简单但不够规范                         |
| **方案 D**: 使用 PyMC 的 `pm.CustomDist`                         | 官方推荐的自定义分布方式               |

**推荐**: 先用**方案 A** 验证概念（确认 OPN 预测的 omission probability 是否合理），然后用**方案 B** 做到完整的贝叶斯推断。

### 5.5 方案 B：将 OPN 权重导入 PyMC

如果你的 OPN 是小型 MLP（3 层），可以把权重/偏置导入 PyMC：

```python
import pytensor.tensor as pt

def opn_logp_pytensor(v, a, t, z, deadline, weights, biases):
    """用 pytensor 重建 OPN 的前向传播"""
    X = pt.stack([v, a, t, z, deadline], axis=1)
  
    # Layer 1
    h1 = pt.nnet.relu(pt.dot(X, weights[0]) + biases[0])
    # Layer 2
    h2 = pt.nnet.relu(pt.dot(h1, weights[1]) + biases[1])
    # Layer 3
    h3 = pt.nnet.relu(pt.dot(h2, weights[2]) + biases[2])
    # Output
    logit = pt.dot(h3, weights[3]) + biases[3]
    p_omission = pt.nnet.sigmoid(logit)
  
    return pt.log(pt.clip(p_omission, 1e-10, 1 - 1e-10))

# 从 sklearn MLP 提取权重
def extract_mlp_weights(opn_model):
    """提取 sklearn MLPRegressor 的权重"""
    weights = []
    biases = []
    for i, coef in enumerate(opn_model.coefs_):
        weights.append(coef)
        biases.append(opn_model.intercepts_[i])
    return weights, biases

w, b = extract_mlp_weights(opn)
```

> `extract_mlp_weights` 返回的权重可直接用于 pytensor 重建 OPN。这样 OPN 的 logp 就可以参与 MCMC 的梯度计算，实现完整贝叶斯推断。

---

## Part 6: 阶段四 —— 在真实数据上运行

### 6.1 运行所有可用组

扩展 `lan_opn_fit.py`，对每组运行拟合：

```python
GROUPS_TO_FIT = [
    (5, 8, 100, 1100),
    (6, 120, 500, 1500),
    (7, 120, 80, 800),
    (8, 120, 80, 800),
    # (3, 120, 30, 600),   # 灰色地带，可选
    # (4, 120, 80, 600),   # 灰色地带，可选
]

OUT_DIR = BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN"
OUT_DIR.mkdir(parents=True, exist_ok=True)

all_summaries = []

for group_id, P, T, W in GROUPS_TO_FIT:
    print(f"\n{'='*50}")
    print(f"拟合 Group {group_id}: P={P}, T={T}ms, W={W}ms")
    print(f"{'='*50}")
  
    obs_data, n_omissions, deadline_s = prepare_data_for_lan_opn(group_id, P, T, W)
    model, trace = fit_lan_opn_model(obs_data, n_omissions, deadline_s)
  
    # 提取组水平参数
    summary = az.summary(trace, var_names=['mu_v', 'mu_a', 'mu_t', 'mu_z'], 
                         hdi_prob=0.95)
    summary['group_id'] = group_id
    summary['omission_count'] = n_omissions
    all_summaries.append(summary)
  
    # 保存迹线
    az.to_netcdf(trace, OUT_DIR / f"lan_opn_trace_G{group_id}.nc")
  
    # 基本诊断
    rhat = az.rhat(trace).max().to_array().max().values
    print(f"  max R-hat: {rhat:.3f} {'✅' if rhat < 1.05 else '⚠️'}")

# 汇总保存
all_df = pd.concat(all_summaries)
all_df.to_csv(OUT_DIR / "lan_opn_all_groups_summary.csv")
print(f"\n✅ 所有组拟合完成！汇总: {OUT_DIR / 'lan_opn_all_groups_summary.csv'}")
```

### 6.2 MCMC 收敛检查清单

对每组检查：

| 指标        | 阈值        | 不通过则                                      |
| :---------- | :---------- | :-------------------------------------------- |
| R-hat       | < 1.05      | 增加 draws/tune，或检查 model identifiability |
| ESS (bulk)  | > 400       | 增加 draws                                    |
| ESS (tail)  | > 400       | 同上                                          |
| Trace plot  | 无趋势/漂移 | 增加 burn-in                                  |
| Divergences | 0           | 增加 target_accept (0.95)                     |

```python
# 收敛诊断
trace_g5 = az.from_netcdf(OUT_DIR / "lan_opn_trace_G5.nc")
print(az.rhat(trace_g5))  # R-hat
print(az.ess(trace_g5))   # ESS
az.plot_trace(trace_g5)   # 迹线图
plt.show()
```

---

## Part 7: 阶段五 —— 对比 HDDM Censor vs PyMC LAN+OPN

### 7.1 参数对比表

```python
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path("/home/jovyan/work")

# 加载 LAN+OPN 结果
lan_opn_df = pd.read_csv(BASE_DIR / "2_Data/Generate_Data/Omission_LAN_OPN/lan_opn_all_groups_summary.csv")

# 加载已有的 HDDM Censor 结果
censor_dir = BASE_DIR / "2_Data/Generate_Data/Omission_Sensitivity/censor_traces"
censor_params = []

# 解析文件名提取参数
import re
for stats_path in sorted(censor_dir.glob("*_stats.csv")):
    fname = stats_path.stem.replace("_stats", "")
    m = re.search(r"group(\d+)_P(\d+)_T(\d+)_W(\d+)", fname)
    if not m:
        continue
    gid = int(m.group(1))
  
    stats = pd.read_csv(stats_path, index_col=0)
  
    # 提取组水平参数（HDDM 的层级后验中的 group mean）
    # v(1)=v_self, v(0)=v_stranger
    for param_name, stat_key in [('v_self', 'v(1)'), ('v_stranger', 'v(0)'), 
                                   ('a', 'a'), ('t', 't'), ('z', 'z')]:
        if stat_key in stats.index:
            censor_params.append({
                'group_id': gid,
                'parameter': param_name,
                'censor_mean': stats.loc[stat_key, 'mean'],
                'censor_q025': stats.loc[stat_key, '2.5q'],
                'censor_q975': stats.loc[stat_key, '97.5q'],
            })

censor_df = pd.DataFrame(censor_params)

# 对比
print("\n" + "=" * 80)
print("HDDM Censor vs PyMC LAN+OPN — 参数对比")
print("=" * 80)

# 简化：仅对比 v_self
for _, row in lan_opn_df.iterrows():
    gid = row['group_id']
    c_row = censor_df[(censor_df['group_id'] == gid) & (censor_df['parameter'] == 'v_self')]
    if len(c_row) == 0:
        continue
    c_row = c_row.iloc[0]
  
    delta = row['mean'] - c_row['censor_mean']
    ci_overlap = not (row['hdi_2.5%'] > c_row['censor_q975'] or 
                      row['hdi_97.5%'] < c_row['censor_q025'])
  
    print(f"G{gid}: HDDM={c_row['censor_mean']:.3f}, "
          f"LAN+OPN={row['mean']:.3f}, Δ={delta:.3f}, "
          f"CI overlap: {'✅' if ci_overlap else '❌'}")
```

### 7.2 可视化

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

param_keys = ['v_self', 'v_stranger', 'a', 't', 'z']
param_labels = ['Drift Rate v_self', 'Drift Rate v_stranger', 
                'Boundary a', 'Nondecision t', 'Starting Point z']

for i, (key, label) in enumerate(zip(param_keys, param_labels)):
    ax = axes[i]
  
    # 提取数据
    # (此处需要根据实际数据结构调整)
    groups = [5, 6, 7, 8]
    hddm_vals = [...]
    lan_opn_vals = [...]
  
    x = np.arange(len(groups))
    width = 0.35
  
    ax.bar(x - width/2, hddm_vals, width, label='HDDM Censor', color='#4472C4')
    ax.bar(x + width/2, lan_opn_vals, width, label='PyMC LAN+OPN', color='#ED7D31')
  
    ax.set_xticks(x)
    ax.set_xticklabels([f'G{g}' for g in groups])
    ax.set_ylabel(label)
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)

fig.suptitle('HDDM Censor vs PyMC LAN+OPN: DDM Parameters', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE_DIR / "3_Figures/Omission_LAN_OPN/lan_opn_vs_hddm_censor.png", dpi=200)
plt.show()
```

> ✅ **验证标准**:
>
> - 对于 G5-G8（低遗漏率），HDDM Censor 和 LAN+OPN 的参数 95% CI 应重叠
> - 如果重叠且 Delta < 0.5 → **当前 Censor 方案已足够好，LAN+OPN 作为方法论验证**
> - 如果不重叠 → 说明 Censor 方案确有不足，LAN+OPN 有实质性改进

---

## Part 8: 常见问题排查

| 问题                      | 原因                           | 解决                                                                           |
| :------------------------ | :----------------------------- | :----------------------------------------------------------------------------- |
| OPN 训练数据生成太慢      | 纯 NumPy 单线程                | 安装`pip install numba` 使用 JIT 加速；或减少 `N_TRAIN_SAMPLES` 先用小样本 |
| OPN R² 低 (< 0.85)       | 训练数据不足/网络太小          | 增加`N_TRAIN_SAMPLES`；增加 `hidden_layer_sizes` 到 `(256, 128, 64)`     |
| MCMC 不收敛 (R-hat > 1.1) | omission 惩罚项破坏后验几何    | 增加`target_accept=0.95`；增加 tune 到 1000                                  |
| `pm.Potential` 报错     | `.eval()` 在采样循环中不可用 | 切换到方案 B（pytensor 重建 OPN）                                              |
| Wiener 似然返回 NaN       | rt_adj <= 0（t0 >= rt）        | 增加`pt.maximum(rt - t0, 1e-10)` 保护                                        |
| 内存不足                  | 大量被试 × 大量试次           | 分批拟合被试；或增加`n_subjects` 维度的 shrinkage                            |

---

## 总结：你的 5 天行动路线

```
Day 1: Part 1 + Part 2 (阅读 + 环境验证) + Part 3 (DDM 仿真器)
        → 输出: opn_simulator.py 可用，速度达标

Day 2: Part 4 (OPN 训练)
        → 输出: OPN 模型 + scaler，R² > 0.90

Day 3: Part 5 (联合似然实现)
        → 输出: lan_opn_fit.py，G5 测试通过

Day 4: Part 6 (全部 group 拟合)
        → 输出: 4 组 LAN+OPN 后验迹线，收敛诊断通过

Day 5: Part 7 (对比 HDDM Censor)
        → 输出: 参数对比表 + 可视化图表
```

---

*计划编写日期：2026-06-13 | 基于 Leng et al. (2025) 全文 + 本项目的 DDM 基础设施*
