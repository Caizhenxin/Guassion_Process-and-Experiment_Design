# OPN 训练总结 — 思路与相关文件

> **整理日期**：2026-09-02
> **对象**：DesignSpace 项目中 Route 2（DDM/Angle + OPN）的 OPN 集成与拟合
> **来源**：`3_Study3_Empirical/OPN_integration_plan.md`、`4_S4_Model_Ph2/alterRoutes.md`、
> `3_Study3_Empirical/opn_smoke/*`（README 与 notebook）、`AGENTS.md`「hssm / Route 2 / OPN 统一守则」节、
> `3_Study3_Empirical/S3_Ph2_0_doc.md`、`PROJ_STATE.md`
> **参考论文**：*The Perils of Omitting Omissions when Modeling Evidence Accumulation*（Leng, Fengler,
> Shenhav & Frank, 2025）

---

## 1. OPN 是什么

- **OPN（Omission Probability Network，省略概率网络）**：一个**预训练神经网络**，输入
  序贯采样模型（SSM）参数 + 截止时间（deadline），输出**省略（无反应 / omission）的 log 概率**
  `log P(omission | θ, deadline)`。
- 属于 **LAN（Likelihood Approximation Network）** 生态：LAN 逼近"已观测试次"的逐试次似然
  `p(RT, choice | θ)`；**OPN 专责"缺失/省略试次"的似然**（超窗未反应）。
- 本项目使用的三个 OPN 网络（预训练 ONNX）：
  | 网络 | 边界 | 输入参数 |
  |---|---|---|
  | `ddm_opn.onnx` | 恒定边界 DDM | v, a, z, t, deadline |
  | `angle_opn.onnx` | 线性塌缩边界 Angle | v, a, z, t, θ, deadline |
  | `weibull_opn.onnx` | Weibull 非线性塌缩边界 | 同上类 |

> ⚠️ **本项目不重新训练 OPN 网络**。OPN 由论文作者训练好，作为预训练 `.onnx` 直接复用。
> 本项目"训练"的对象是 **DDM/Angle 的参数后验**——通过 hssm 将固定的 OPN 似然接入贝叶斯 MCMC 推断。

---

## 2. OPN 网络本身如何训练（论文层面，amortized neural likelihood）

OPN 的训练采用**amortized / 神经网络似然估计**思路（LAN 家族通用范式），对省略概率做有监督拟合并生成;项目未复现该训练，仅复用成品网络：

1. **大规模模拟生成训练数据**：在参数先验空间 + deadline 网格上**随机采样** DDM / Angle 参数，
   用 SSM 模拟器（`ssms`）模拟大量试次，记录是否在窗口内反应（`RT ≥ deadline` 即 omission）。
2. **构造监督标签**：统计"给定参数 + deadline 下未反应的比例" = omission 概率；也可通过
   **互补 CDF 截断似然**表达：`P(no response) ≈ (1 − exp(net_out))`，即用网络逼近的分布
   "1 − CDF(deadline)" 延伸出窗口外概率。
3. **训练网络**：让网络学习 `(θ, deadline) → log P(omission)` 的映射（基于 `lanfactory` 生态
   训练 + 导出 ONNX）。
4. **接入推断**：把网络似然转成 jax logp 函数（`NetworkLike.make_logp_jax_funcs`）→ 接入 pymc
   做贝叶斯 MCMC。

**论文核心结论（决定收益）**：若只删除 omission / 只拟合观测试次，会**系统性高估 v、低估 a**
（偏差随 omission 率增大）；把 omission 作为观测**联合建模**（LAN + OPN）后参数恢复显著改善；
该收益与 lapse（注意力脱落）建模**相互独立、可叠加**。在恒/塌缩边界（DDM / ANGLE / WEIBULL）上均获验证。

---

## 3. 本项目如何"训练/拟合"DDM+OPN / Angle+OPN

### 3.1 总体思路：双路径并行框架

```
                    S3_Ph2_0（模型选择阶段）
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
┌───────▼────────┐                  ┌─────────▼─────────┐
│ Route 1        │                  │ Route 2           │
│ 标准 DDM        │                  │ DDM/Angle + OPN   │
│（不考虑 omission）│                  │（考虑 omission）    │
│ S3 ✅ 已完成     │                  │ S3 ⏳ D0/D5 拟合选型│
└───────┬────────┘                  └─────────┬─────────┘
        ▼                                     ▼
┌───────────────┐                   ┌──────────────────┐
│ S4_Ph2_Route1 │                   │ S4_Ph2_Route2    │
│ 机制模型=DDM   │                   │ 机制模型=DDM/Angle│
│ v-flip 生成模拟│                   │ +OPN             │
└───────┬───────┘                   └───────┬──────────┘
        └───────────┬───────────────────────┘
                    ▼
        与实证数据 sim-vs-emp 系统比较
        判定：omission 是否需要显式建模
```

- Route 2 = **把 omission 显式纳入机制模型**：观测试次用 LAN 似然，missing（omission）试次用 OPN 似然。
- 启动 Route 2 的动机（科学缺口）：标准 DDM 在 D1 模拟 omission ≈3% vs 实证 71.6%——
  忽略 omission 的模型无法复现极端窗口设计的省略梯度。

### 3.2 集成方式（hssm，关键代码语义）

用 **hssm**（HSSM 0.4.0）构建贝叶斯模型，通过 `missing_data` / `deadline` / `loglik_missing_data`
开关把 OPN 接进来（核心工厂函数见 `hssm_formula_diagnosis.ipynb` 1.2）：

```python
# opn_path=None → 非 OPN：剔除 omission 行，纯 LAN 似然
# opn_path=...    → +OPN：missing_data=True, deadline=True, loglik_missing_data=<ddm_opn.onnx>
def make_workflow_model(data, model_name, opn_path=None):
    if opn_path is None:
        d = data[data["response"] != 0].copy(); kw = {}
    else:
        d = data.copy()
        kw = {"missing_data": True, "deadline": True, "loglik_missing_data": opn_path}
    return HSSM(
        data=d, model=model_name, loglik_kind="approx_differentiable",
        global_formula="y ~ 1",
        include=[
            {"name": "v", "formula": "v ~ Label*Matchness + (1|participant_id)"},
            {"name": "z", "formula": "z ~ Label + (1|participant_id)"},
            {"name": "a", "formula": "a ~ 1 + (1|participant_id)"},
            {"name": "t", "formula": "t ~ 1 + (1|participant_id)"},
        ],
        noncentered=True, p_outlier=0.05, **kw,
    )
```

- **数据编码约定**：观测试次 `rt=正向 RT 秒 + response=±1`（choice 编码，match=+1）；
  omission 行 `rt=-999.0 + response=0`；deadline 单独一列（D0 = 1.2s）。
- **MCMC 采样**：numpyro（NUTS），`draws=2000 / tune=1000 / chains=4 / target_accept=0.9`，
  `nuts={"chain_method": "parallel"}` + 采样前设 `XLA_FLAGS=--xla_force_host_platform_device_count=4`。
- **四模型矩阵**：`ddm_noopn / angle_noopn / ddm_opn / angle_opn`（机制 × 是否 OPN）。

### 3.3 两阶段验证路径（opn_smoke）

**阶段 1 — synthetic 参数恢复（复现论文 Fig.2）**：用 `ssms` 生成 3 组已知真值、不同 omission
率（28.5% / 8.5% / 57.5%）的 synthetic 数据；每组用两个模型拟合——
M1 = 仅观测试次（LAN-only），M2 = 全数据（LAN+OPN）。结论：

| 组（真值 v/a） | omission | M1 LAN-only | M2 LAN+OPN |
|---|---|---|---|
| G1 (1.0/1.0) | 28.5% | v=1.50 (+0.50) / a=0.77 (−0.23) | v=0.98 / a=0.99 ✅ |
| G2 (2.0/1.0) | 8.5% | v=2.46 (+0.46) / a=0.95 (−0.05) | v=2.03 / a=0.98 ✅ |
| G3 (1.0/1.5) | 57.5% | v=2.10 (+1.10) / a=1.06 (−0.44) | v=1.15 / a=1.57 ✅ |

→ 证明"纳入 omission 似然能恢复参数"，为阶段 2 提供科学动机。

**阶段 2 — D0 真实数据四模型拟合（`hssm_formula_diagnosis.ipynb`）**：在 D0（NoMask 预实验，
8 被试 × 520 试次，omission 8.9%）上运行四模型，比较：
- **收敛诊断**（r_hat / ess，notebook 1.4）；
- **PPC 量化比较**（1.5，四模型横向可比）：omission 偏差、ACC 偏差、RT 中位偏差、
  signed RT 1D Wasserstein（越小越好）；
- **LOO 模型比较**（1.6，仅同数据内：`ddm vs angle`、`ddm_opn vs angle_opn`）；
- **组级参数提取**（1.7，与 HDDM `m_dc_id` 对照）。

### 3.4 已知问题：angle_opn 采样卡死（2026-08-23 诊断）

- **现象**：正式规格下 angle_opn 首次 4 链全卡 ~10%，重试后 3 链卡，进程永远等——
  非死锁，而是**单步迭代极慢**、高 divergence。
- **根因（模型结构问题，非采样配置）**：Angle 的 θ 在 **LAN 与 OPN 梯度方向冲突**——
  LAN（观测似然）把 θ 推向 1.3+，OPN（omission 似然）把 θ 压在 0 附近（grad 达 −20.5）；
  后验在 θ 上呈狭窄"脊" → NUTS step size 从 2.34e+00 塌缩到 7.37e-05 → 每次迭代 1023 步
  leafpfrog + 高 divergence。
- **为何仅 angle_opn**：ddm_opn 无 θ（梯度不冲突）；angle_noopn 无 OPN（不冲突）。
- **建议方向（待用户决策）**：① 换用 `ddm_opn`（已验证可收敛）；② θ 加窄先验/固定；
  ③ 调步长参数（低成功率——这是模型问题）。

### 3.5 关键踩坑（沉淀）

1. **`hssm.set_floatX("float32")` 必须**：LAN/OPN 网络按 float32 训练，float64 → NaN energy →
   NUTS 全 divergence。
2. **hssm 0.4.0 API**：`save_idata_only` → `save_model(model_name, allow_absolute_base_path,
   base_path, save_traces_only)`；`model_stochastic_nodes` 移除 → 参数列表用 `m.params.keys()`；
   无 `hierarchical=True` → 随机效应须显式写 `(1|participant_id)`；层次模型须 `noncentered=True`。
3. **numpyro 并行采样**：顶层 `chain_method` 被 pymc 静默丢弃 → 必须放进 `nuts` dict；
   CPU 需 `XLA_FLAGS --xla_force_host_platform_device_count=4` 造虚拟设备，否则 4 链串行 ~6.8h。
4. **PPC 输出为联合变量** `'rt,response'`/`'rt,response,deadline'`，shape `(chain,draw,trial,ncol)`；
   noopn PPC trial 数 = 剔 omission 后行数、opn = 全数据行数，指标计算须按 trial 数自适应对齐。
5. **sandbox 运行**：需 `HF_HOME` / `PYTENSOR_FLAGS base_compiledir` / `MPLCONFIGDIR` 重定向到可写目录。
6. **数据编码**：`rt=-999.0 + response=0` 作 omission；`deadline` 列；hssm 自动把 missing 数据置顶。

---

## 4. 训练/拟合流程（一句话主线）

> **用 hssm 把预训练 OPN 网络当作 omission 的缺失似然接入贝叶斯模型** → 在同一模型里
> **联合拟合观测（LAN）与省略（OPN）试次** → numpyro/NUTS 采样参数后验（v/a/z/t[+θ]/被试随机效应）
> → 收敛诊断 + PPC + LOO → 与 Route 1（标准 DDM）做 sim-vs-emp 系统比较 → 判定 omission 是否需显式建模。

---

## 5. 相关文件清单

### A. 计划与决策（已入库）
| 文件 | 角色 |
|---|---|
| `3_Study3_Empirical/OPN_integration_plan.md` | ★ 双路径框架 + Route 2 完整执行计划（阶段 0–5、里程碑、决策） |
| `4_S4_Model_Ph2/alterRoutes.md` | §1 opn/LAN 方法调研、机理、可借鉴/不借鉴、落地路径 |
| `4_S4_Model_Ph2/S4_Ph2_Route1_plan.md` | Route 1（标准 DDM）对照计划 |
| `3_Study3_Empirical/S3_Ph2_0_doc.md` | §6 陷阱 15–17：OPN/float32/固定 z/angle 卡死 |
| `AGENTS.md` | 「hssm / Route 2 / OPN 统一守则」节（环境/API/并行/PPC/缓存） |
| `PROJ_STATE.md`、`README.md` | 项目状态与进展（Route 1/2 进度） |

### B. 代码与产物（`opn_smoke/`，gitignored，含/不含 heavy 产物）
| 文件 | 角色 |
|---|---|
| `opn_smoke/README.md` | opn_smoke 两阶段说明 + 复跑方法 |
| `opn_smoke/phase1_recovery/fit.py` | 阶段 1：拟合一个模型 `fit.py <G*><M*><draws><tune><chains>`（按文档，当前 FS 可能已清理） |
| `opn_smoke/phase2_d0d5/hssm_formula_diagnosis.ipynb` | ★ 主 notebook：D0 四模型定义/采样/诊断/PPC/LOO/参数提取 |
| `opn_smoke/phase2_d0d5/fit_D0_analytical.py` | analytical 似然（精确 Wiener）对照，区分 LAN 网络 vs 管线问题 |
| `opn_smoke/phase2_d0d5/bench_samplers.py` | 采样器速度基准（numpyro/nutpie/blackjax/pymc） |
| `opn_smoke/phase2_d0d5/D0_hssm_cond_input.csv` | D0 hssm 输入（8 被试 × 4160 行，含 omission） |
| `opn_smoke/phase2_d0d5/D0_fits/idata/{ddm,angle}_{noopn,opn}/traces.nc` | 后验轨迹（angle_opn 空/失败） |
| `opn_smoke/phase2_d0d5/D0_fits/param_group_compare.csv` | 四模型组级参数对比 |
| `opn_smoke/phase2_d0d5/D0_fits/ppc_compare.csv`、`figure/D0_ppc_compare.png` | PPC 量化指标 |
| `opn_smoke/networks/` | LAN 网络缓存（HF hub：ddm/angle/weibull LAN onnx） |
| `opn_smoke/phase1_recovery/results/`、`figure/` | 阶段 1 产物（G*_M*.nc、results_table.csv、recovery_2x2.png） |

### C. 外部/输入资产（gitignored，可能不在当前工作区）
| 文件 | 角色 |
|---|---|
| `opn-main/` | OPN 论文 + 网络（已 gitignore 的第三方项目） |
| `opn-main/Networks/{ddm,angle,weibull}_opn.onnx` | ★ OPN 预训练网络（本项目复用，不重训） |
| `opn-main/Leng_et_al_2025_Perils_of_Omitting_Omissions.md` | 论文 md 存档 |
| `opn-main/SimulationCode/runModelDDM.py` | 论文复现代码（LAN 接 pymc + omission 截断） |
| `3_Study3_Empirical/data/emp_data/EXP_NoMask_data_group1_*.csv` | D0 实证数据源（8 被试） |
| `ssms` / `hssm`(0.4.0) / `lanfactory` / numpyro / jax / pytensor | 运行依赖生态 |

> 注：opn_smoke 目录 **gitignored**；heavy 后验产物（`.nc`）在本机不复现 / 未入库，
> 可按 `opn_smoke/README.md` 的复跑方法用 `hssm` env 重新生成。

---

## 版本历史
| 版本 | 日期 | 更新 |
|---|---|---|
| v0.2 | 2026-09-02 | 新增 OPN 训练思路与相关文件总结 |