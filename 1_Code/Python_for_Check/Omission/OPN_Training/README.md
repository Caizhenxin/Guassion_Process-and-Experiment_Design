# OPN Training — 遗漏概率网络训练模块

> **Omission Probability Network (OPN)** 训练工具包，基于 Leng et al. (2025) 的 LAN+OPN 方法论，
> 用于训练一个神经网络来预测给定 DDM 参数和 deadline 下的 omission 概率。

## 目录

- [背景](#背景)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [模块结构](#模块结构)
- [参数说明](#参数说明)
- [输出文件](#输出文件)
- [API 文档](#api-文档)
- [常见问题](#常见问题)
- [参考文献](#参考文献)

## 背景

在有 deadline 的决策实验中，部分试次无法在截止时间前做出反应（omission）。
Leng et al. (2025) 提出了 LAN+OPN 框架：用 OPN（Omission Probability Network）
来预测给定 SSM 参数和 deadline 下的 omission 概率，然后将 omission 信息纳入联合似然函数。

本项目使用**恒定边界 DDM**（解析 Wiener 似然），因此只需训练 OPN，不需要训练 LAN。

**OPN 输入**: `(drift_rate v, boundary a, nondecision_time t0, relative_starting_point zr, deadline d)`
**OPN 输出**: `omission_probability ∈ [0, 1]`

### 理论框架

参考文档:
- `5_Reference/Omission_v2.md` — 论文方法论深度解读与技术路线图
- `5_Reference/Omission_LAN_OPN_实施作战计划.md` — 分阶段实施计划

## 环境要求

| 依赖 | 最低版本 | 用途 |
|:---|:---|:---|
| Python | 3.8+ | 运行环境 |
| numpy | 1.20+ | 数值计算、批量仿真 |
| scikit-learn | 1.0+ | MLP 回归器、数据预处理 |
| pandas | 1.3+ | 数据处理 |
| matplotlib | 3.4+ | 可视化 |
| joblib | 1.1+ | 模型序列化 |
| numba | 0.55+ | *(可选)* JIT 加速仿真器 (10-50x) |

### 安装依赖

```bash
# 基础依赖
pip install numpy scikit-learn pandas matplotlib joblib

# 可选加速（强烈推荐）
pip install numba
```

## 快速开始

### 1. 测试仿真器

```bash
cd 1_Code/Python_for_Check/Omission/OPN_Training
python opn_simulator.py
```

预期输出:
```
OPN Simulator 测试
  高 omission 参数: 852/1000 = 85.2%  (预期 > 50%)
  低 omission 参数: 15/1000 = 1.5%  (预期 < 10%)
  速度基准: 24500 trials/s  (omission rate = 0.234)
✅ Simulator 测试完成
```

### 2. 快速训练（5000 组参数，约 30 分钟）

```bash
python opn_train.py --mode fast
```

### 3. 完整训练（50000 组参数，约 5-8 小时）

```bash
python opn_train.py --mode full
```

### 4. 评估与可视化

```bash
python opn_evaluate.py
```

### 5. 仅测试仿真器速度

```bash
python opn_train.py --mode benchmark
```

## 模块结构

```
OPN_Training/
├── __init__.py               # 包导出
├── opn_simulator.py          # DDM 批量仿真器 (核心)
│   ├── simulate_ddm_batch_vectorized()  # NumPy 向量化
│   ├── simulate_ddm_batch_numba()       # Numba JIT 加速
│   ├── SIMULATOR                        # 自动选择最优版本
│   └── benchmark_simulator()            # 速度测试
├── opn_data.py               # 数据生成与预处理
│   ├── generate_opn_training_data()     # 从 prior 生成数据
│   ├── save_training_data() / load_training_data()
│   └── prepare_train_test_split()       # 划分 + 标准化
├── opn_model.py              # 模型构建、训练、评估
│   ├── build_opn()                      # 构建 MLP
│   ├── train_opn()                      # 训练
│   ├── evaluate_opn()                   # 评估 (R², MAE, RMSE)
│   └── save_model() / load_model()      # 持久化
├── opn_train.py              # 主训练流程 (CLI)
│   └── run_pipeline()                   # 5 步流水线
├── opn_evaluate.py           # 评估与可视化
│   ├── plot_full_diagnostics()          # 6 面板诊断图
│   ├── feature_sensitivity_analysis()   # 边际效应分析
│   └── compare_with_real_data()         # 与真实 omission 率对比
└── README.md                 # 本文档
```

## 参数说明

### 仿真器参数 (`opn_simulator.py`)

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `v` | float | — | 漂移率，范围建议 [-5, 5] |
| `a` | float | — | 边界分离，必须 > 0 |
| `z` | float | — | 绝对起始点，0 < z < a |
| `t0` | float | — | 非决策时间（秒） |
| `deadline_s` | float | — | 截止时间（秒） |
| `n_trials` | int | 5000 | 单组参数的仿真试次数 |
| `dt` | float | 0.001 | Euler 步长（秒） |

### 训练参数 (`opn_train.py`)

| 参数 | CLI 标志 | 默认值 | 说明 |
|:---|:---|:---|:---|
| 运行模式 | `--mode` | `fast` | `fast` / `full` / `train_only` / `benchmark` |
| 随机种子 | `--seed` | 42 | 可复现性 |
| 训练样本数 | `--n_samples` | 5000/50000 | 取决于 mode |
| 仿真次数/组 | `--n_sim` | 5000 | 每组参数的仿真试次数 |
| 隐藏层结构 | `--hidden_layers` | `128,64,32` | 逗号分隔的三层结构 |
| 最大迭代 | `--max_iter` | 500 | MLP 最大迭代次数 |
| L2 正则化 | `--alpha` | 0.001 | 防止过拟合 |
| 模型前缀 | `--model_prefix` | `opn` | 输出文件名前缀 |

### 完整运行示例

```bash
# 自定义训练配置
python opn_train.py \
    --mode full \
    --seed 123 \
    --n_samples 20000 \
    --n_sim 3000 \
    --hidden_layers "256,128,64" \
    --max_iter 800 \
    --alpha 0.002 \
    --model_prefix opn_v2
```

## 输出文件

### 数据文件 (`2_Data/Generate_Data/OPN_Training/`)

| 文件 | 格式 | 说明 |
|:---|:---|:---|
| `opn_training_data_fast.npz` | .npz | 快速模式训练数据 (X, y) |
| `opn_training_data_full.npz` | .npz | 完整模式训练数据 |
| `opn_model.joblib` | joblib | 训练后的 OPN 模型 |
| `opn_scaler.joblib` | joblib | 特征标准化器 |
| `opn_metrics.json` | JSON | 评估指标 (R², MAE, RMSE) |
| `opn_config.json` | JSON | 训练配置 |
| `opn_train_*.log` | 文本 | 训练日志 |
| `opn_model.pkl` | pickle | 模型备份 (兼容性) |

### 图表文件 (`3_Figures/OPN_Training/`)

| 文件 | 说明 |
|:---|:---|
| `opn_diagnostics.png` | 6 面板诊断图：真实vs预测、残差分布、4特征边际效应 |
| `opn_loss_curve.png` | 训练损失曲线（如可用） |

## API 文档

### 在代码中使用

```python
from opn_simulator import SIMULATOR
from opn_data import generate_opn_training_data, prepare_train_test_split
from opn_model import build_opn, train_opn, save_model
from opn_evaluate import predict_omission_rate, plot_full_diagnostics

# 生成数据
X, y = generate_opn_training_data(n_samples=5000, n_sim=5000, seed=42)

# 划分和标准化
X_train, X_test, y_train, y_test, scaler = prepare_train_test_split(X, y)

# 训练
opn = build_opn(hidden_layer_sizes=(128, 64, 32))
opn = train_opn(opn, X_train, y_train)

# 预测
params = np.array([[1.5, 1.2, 0.3, 0.5, 0.8]])  # (v, a, t0, zr, deadline)
om_rate = predict_omission_rate(opn, scaler, params)
print(f"Predicted omission rate: {om_rate[0]:.3f}")

# 可视化
plot_full_diagnostics(opn, scaler, X_test, y_test)
```

## 常见问题

### Q: 仿真器太慢怎么办？
**A**: 安装 numba (`pip install numba`)，速度提升 10-50 倍。已在代码中自动检测。

### Q: OPN 的 R² 低 (< 0.85) 怎么办？
**A**:
1. 增加 `--n_samples` (完整模式 50000)
2. 增加 `--n_sim` (减少仿真噪声)
3. 调整 `--hidden_layers` 更深的网络 (256,128,64)
4. 降低 `--alpha` 正则化强度

### Q: MCMC 使用 OPN log-probability 时怎么做？
**A**: OPN 输出的是 omission_rate (概率值), 需要转为 log:
```python
p_om = opn.predict(X_scaled)
logp_om = np.log(np.clip(p_om, 1e-10, 1 - 1e-10))
```
在 PyMC 中通过 `pm.Potential` 或 `pm.CustomDist` 将此 logp 加入联合似然。
详见 `5_Reference/Omission_LAN_OPN_实施作战计划.md` Part 5。

### Q: 支持 GPU 加速吗？
**A**: 当前 DDM 仿真器是 CPU 版本。如需 GPU 加速，可将 NumPy 向量化逻辑移植到 PyTorch/JAX。
对于 OPN 训练本身，sklearn MLP 是 CPU-only。GPU 训练可参考 PyTorch 版本的 MLP。

## 参考文献

- **Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025).**
  The Perils of Omitting Omissions when Modeling Evidence Accumulation. *In Prep.*
- **Fengler, A., et al. (2021).**
  Likelihood approximation networks (LANs) for fast inference of simulation models in cognitive neuroscience. *eLife, 10*, e65074.
- **Tran, N. H., van Maanen, L., Heathcote, A., & Matzke, D. (2021).**
  Systematic parameter reviews in cognitive modeling. *Frontiers in Psychology, 11*, 608287.
- **Ratcliff, R., & McKoon, G. (2008).**
  The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation, 20*(4), 873-922.

---

*创建日期: 2026-07-21 | 基于本项目 Sensitivity Analysis 实证结果*
