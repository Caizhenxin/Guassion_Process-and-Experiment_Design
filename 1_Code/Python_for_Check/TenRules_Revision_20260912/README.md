# TenRules_Revision_20260912 —— 十条规则修订分析包

> 建立日期：2026-09-12 ｜ 依据：`5_Reference/终版论文格式及要求/计算建模十条规则核对报告_初稿v2_20260912.md`
> 目的：补上初稿相对 Wilson & Collins (2019) 十条规则最关键的缺口——**参数恢复（规则5）**、
> **后验预测检验（规则7）**、**模型比较与模型恢复（规则2/6）**，并把研究二的 35%/15% 分档
> 从"事后归纳"升级为"仿真支持的结论"。

---

## 一、三个脚本与论文条目的对应

| 脚本 | 对应规则 | 论文中的位置 | 主要产物 |
|---|---|---|---|
| `param_recovery_frozen6.py` | 规则 5、规则 4、规则 9 | 研究二新增小节"参数恢复与遗漏率的偏倚边界" | `recovery_by_job.csv`、`recovery_summary.csv`、`omission_curve_bias.csv`、3 张图 |
| `ppc_frozen6.py` | 规则 7、规则 8 | 研究三"行为层验证"升级为严格 PPC | `ppc_by_identity.csv`、`ppc_condition.csv`、`ppc_coverage_summary.csv`、3 张图 |
| `model_comparison_frozen6.py` | 规则 2、规则 6、规则 9 | 研究三新增小节"模型比较与模型恢复" | `model_comparison_locv.csv`、`model_comparison_summary.csv`、`model_recovery_confusion*.csv`、1 张图 |
| `sim_utils.py` | — | 共享工具（仿真器、统计口径、迹线读取） | — |
| `fit_one_hddm.py` | — | 在 Docker 容器内执行单次 HDDM 拟合 | `<tag>_stats.csv`、`<tag>_traces.npz`、`<tag>_meta.json` |

**推荐执行顺序**：模型比较（快）→ PPC（中）→ 参数恢复（需 Docker，最慢）。

---

## 二、快速开始

```powershell
$py = "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\.venv\Scripts\python.exe"
cd "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Python_for_Check\TenRules_Revision_20260912"

# 0) 自检：验证仿真器与真实数据同量级（不需 Docker，几秒）
& $py param_recovery_frozen6.py --mode sanity

# 1) 模型比较 + 模型恢复（约 10–40 分钟，取决于 --reps）
& $py -u model_comparison_frozen6.py --reps 100
& $py -u model_comparison_frozen6.py --skip-recovery          # 只做比较（几分钟）

# 2) 后验预测检验（默认 200 次抽样，约 1–3 分钟）
& $py -u ppc_frozen6.py --n-draws 200

# 3) 参数恢复：先生成数据，再在 Docker 中拟合，最后汇总
& $py param_recovery_frozen6.py --mode prepare --n-reps 3
& $py param_recovery_frozen6.py --mode fit-docker --dry-run   # 先看命令
& $py param_recovery_frozen6.py --mode fit-docker             # 真正执行（约 1 小时）
& $py param_recovery_frozen6.py --mode collect

# 4) 额外：遗漏率–偏倚曲线（8 个遗漏率水平 × 2 方案 × 2 重复）
& $py param_recovery_frozen6.py --mode curve --curve-reps 2
& $py param_recovery_frozen6.py --mode fit-docker
& $py param_recovery_frozen6.py --mode collect
```

若脚本内调用 Docker 失败（路径映射问题），可直接运行自动生成的批处理：

```powershell
& "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Generate_Data\TenRules_Revision_20260912\param_recovery\run_fits.ps1"
```

Docker 镜像与路径映射（默认值可在命令行覆盖）：

```
镜像 : hcp4715/hddm
挂载 : D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work
```

---

## 三、口径与设计说明（写论文时必须一致）

### 3.1 与冻结版完全一致的部分
- 仿真器：Euler–Maruyama，`dt = 0.002`，`z` 按边界比例解释，超过 deadline 记为 omission
  （逐行对齐 `1_Code/Python_HDDM/GP+Sigmoid/run_cleaned_validation_pipeline.py::simulate_ddm_trials`，
  仅做向量化加速；`--mode sanity` 可复核）。
- HDDM 模型：`depends_on={"v": "identity"}`、`include=["v","a","t","z"]`、`bias=False`。
- 数据列：`subj_idx, rt, response, identity, omission`。
- **p_outlier**：Censor = 0.0，Drop = 0.05（脚本默认；每次拟合的实际取值写入 `*_meta.json`）。
  ⚠️ 仓库脚本 `run_censor_fit.py` 写的是 0.05，与 notebook 实际执行的 0.0 不一致——本包统一为
  0.0/0.05 并在附录中如实说明这一历史差异。

### 3.2 参数恢复的真值与试次规模
- 真值 = 冻结表 `input_conditions_g3g8.csv` 的群体后验均值（v_self、v_stranger、a、t、z）。
- 每条件被试数默认取真实人数（10–12 人）；`--n-subjects-override 20` 可**预览"每条件 ≥20 人"
  的样本量扩充方案**对恢复精度与 CI 覆盖率的影响（见《样本量扩充分析计划》）。
- 每被试每身份 130 试次（88 人数据为每人 260 Matching = 130 self + 130 stranger）。
- `--jitter none|moderate`：`none` 为群体水平恢复（最干净）；`moderate` 加入被试水平抖动
  （v≈0.30、a≈0.20、t≈0.02、z≈0.02），检验"存在个体差异时恢复是否仍成立"。

### 3.3 PPC 为什么必须用被试个体后验
`--mode sanity` 显示：用**群体均值**仿真时，G8 的正确率会虚高到 ≈1.00（真实 ≈0.69），
因为群体均值抹平了个体差异与极端被试。故 `ppc_frozen6.py` 从迹线中按 draw 索引**联合抽取**
被试水平参数（保留参数间后验相关），再逐被试仿真。

### 3.4 模型恢复的适用范围（务必在论文中写明）
模型恢复在**参数层**（设计→DDM 参数映射）进行：合成"真值表"由各模型对 6 条件的预测
加噪声生成，再跑完整四模型 LOCV 比较。这不是行为层的模型恢复（那需要每个合成数据集都重跑
HDDM，成本高一个量级）。论文中的表述建议为：
"模型恢复在设计—参数映射层面进行，检验的是设计点数量是否足以区分四种映射形式。"

---

## 四、产物清单与论文引用位置

```
2_Data/Generate_Data/TenRules_Revision_20260912/
├── param_recovery/
│   ├── prepared/{censor,drop}/*.csv        合成 HDDM 输入
│   ├── fits/{censor,drop}/*_stats.csv      HDDM 拟合结果
│   ├── jobs.json                           作业清单（真值/deadline/遗漏率/n_subjects）
│   ├── run_fits.ps1 / run_fits.sh          自动生成的批处理
│   ├── recovery_by_job.csv                 逐作业真值/估计/CI/覆盖率
│   ├── recovery_summary.csv                按方案汇总（bias / RMSE / 覆盖率 / r）
│   └── omission_curve_bias.csv             遗漏率分箱 → 偏倚
├── ppc/
│   ├── ppc_by_identity.csv                 身份层观测 vs 95% 预测区间
│   ├── ppc_condition.csv                   条件层（SPE_RT / SPE_ACC）
│   ├── ppc_coverage_summary.csv            覆盖率汇总（正文可直接引用）
│   └── ppc_quantile_table.csv              QP 图数据
└── model_comparison/
    ├── model_comparison_locv.csv           各模型 × 各参数的 LOCV RMSE 与 r
    ├── model_comparison_summary.csv        聚合 RMSE 与排名
    ├── model_recovery_confusion.csv        混淆矩阵（计数）
    ├── model_recovery_confusion_prob.csv   混淆矩阵（行归一化）
    └── model_recovery_summary.json         恢复率与预算记录

3_Figures/TenRules_Revision_20260912/
    param_recovery_scatter.png              真值 vs 恢复值
    param_recovery_omission_bias.png        遗漏率 → 偏倚（含 15%/35% 参考线）
    param_recovery_coverage.png             95% CI 覆盖率
    ppc_interval_by_identity.png            观测 vs 预测区间
    ppc_coverage.png                        PPC 覆盖率
    ppc_quantile_probability.png            QP 图（观测 vs 预测）
    model_comparison.png                    模型比较条形图 + 混淆矩阵热图
```

---

## 四之二、实测结果速览（2026-09-12，本包首次运行）

### 模型比较（LOCV 聚合 RMSE，越小越好）
| 模型 | 聚合 RMSE | 排名 |
|---|:-:|:-:|
| M3 纯 Sigmoid | **1.135** | 1 |
| M4 Sigmoid+GP（主模型） | 1.232 | 2 |
| M1 均值基线 | 1.269 | 3 |
| M2 线性 | 8.535 | 4 |

→ 线性形式被可靠排除；**GP 残差层在 6 个设计点下未提升跨设计点预测**（论文需据此改写 GP 的贡献表述）。

### 模型恢复（40 次重复，对角恢复率）
M1 均值 .575｜M2 线性 **.000**｜M3 Sigmoid .675｜M4 Sigmoid+GP **.000**

→ 比较程序无法区分 Sigmoid 与 Sigmoid+GP，且线性从不胜出；混淆矩阵非对角提示**设计对模型判别的功效不足**。

### 后验预测检验（200 次被试水平后验抽样，95% 预测区间覆盖率）
acc_all **.167**｜acc_responded **.167**｜正确 RT 均值 **.278**｜RT 中位数 **.333**｜遗漏率 **.333**

→ 模型在**跨条件趋势**上一致（早期 r=.85–.97），但在**行为分布层面存在系统性失配**
（如 G6 遗漏率：观测 .056 vs 预测 .008）。这是严格 PPC 的应有结果，指向跨试次变异、lapse 与
塌缩边界（ANGLE/WEIBULL）等模型扩展——与 Leng et al. (2026) 一致。

### 参数恢复
68 个 HDDM 拟合作业已就绪（条件 36 + 遗漏率曲线 32），待 Docker 运行：

```powershell
& $py param_recovery_frozen6.py --mode fit-docker
& $py param_recovery_frozen6.py --mode collect
```

---

## 五、已知限制（写进论文局限或方法说明）

1. **参数恢复的合成数据不含跨试次变异**（无 `sv/st0/sz`）与 lapse 机制，也未模拟 HDDM 的
   `p_outlier` 污染过程；因此恢复结果代表"理想化生成模型下"的表现，属最佳情形（规则5 亦提醒
   这一点）。若要更严格，可在 `simulate_trials` 中加入跨试次变异或污染过程作为扩展。
2. **参数恢复用群体均值作真值**：真值本身来自真实数据拟合，含估计误差（非绝对真值），
   论文中须表述为"以冻结后验均值为参考真值的恢复检验"。
3. **模型恢复为参数层**（见 §3.4）。
4. **PPC 的观测统计定义**与项目早期脚本可能略有差异：`acc_all` 将 omission 计为错误，
   另给出 `acc_responded` 以便与旧口径对照；两个定义都会输出，避免口径混用。
5. **DE 预算**：模型比较使用 `--maxiter 80 / --popsize 8`（冻结版校准为 300/12），四个模型
   预算一致故公平；`model_recovery_summary.json` 记录了实际预算。

---

*维护提示：本包所有脚本均从 `2_Data/Real_Data/HDDM_Ready/`、`HDDM_Traces/` 与
`GP_Sigmoid_Frozen6/` 读取数据，**不修改任何既有产物**；当样本量扩充到每条件 ≥20 人后，
只需重跑真实数据的 HDDM 拟合并更新冻结表，本包三个脚本即可直接复用于新数据。*

---

## 六、2026-09-12 新增脚本（收敛诊断 / CRF 叠加 / SPE 库 / 留出验证 / 图集）

| 脚本 | 作用 | 产物 |
|---|---|---|
| `hddm_convergence.py` | 24 次拟合的收敛诊断（单链 Split-R̂ + 自相关 ESS） | `convergence/`；图6-6 |
| `crf_overlay.py` | 模拟 CRF 与实测 CRF 的定量叠加（实测试次直接取自 HDDM_Ready，避免标签方向混淆） | `crf/`；图8-3 |
| `spe_database_analysis.py` | SPE 数据库可获得子集分析（实际样本量、跨研究分布、设计变量调节效应） | `spe_database/T8-1~T8-3`；图8-4 |
| `holdout_subject_validation.py` | 留出被试验证（预测新被试）：prepare / fit-docker / collect | `holdout/`；图9-1 |
| `make_thesis_v3_figures.py` | 生成 v3 论文图集（新绘 4 张 + 汇总 12 张） | `3_Figures/Thesis_v3_20260912/` |

### 运行顺序建议

```powershell
$py = "...\.venv\Scripts\python.exe"

# 收敛诊断（秒级）
& $py -u hddm_convergence.py

# CRF 叠加（约 2 分钟，含被试级 bootstrap）
& $py -u crf_overlay.py

# SPE 数据库子集（约 3–5 分钟，含 1000 次数据集 bootstrap）
& $py -u spe_database_analysis.py

# 参数恢复（需 Docker；并行 4 容器时约 30–60 分钟）
& $py -u param_recovery_frozen6.py --mode fit-docker --parallel 4
& $py -u param_recovery_frozen6.py --mode collect

# 留出被试验证（建议每条件 ≥20 人后再运行）
& $py -u holdout_subject_validation.py --mode prepare
& $py -u holdout_subject_validation.py --mode fit-docker
& $py -u holdout_subject_validation.py --mode collect
```

### 本轮关键结果（供论文引用）

* **收敛**：Censor 敏感性拟合 100% 达标（R̂ ≤ 1.024、ESS ≥ 173）；主拟合 G5–G7 全达标，**G3 严重不收敛（z 的 ESS = 8.6）**、G8 的 z 不达标（ESS = 22）。
* **CRF 叠加**：实测自我优势在 **RT ≈ 480 ms** 最大（+0.14）；起始点偏向只能解释其一部分。
* **SPE 数据库**：实际分析 **44 个数据集 / 2,480 名被试 / 296,240 试次**；SPE_RT = **−98.0 ms [−116.0, −82.1]**；设计变量调节效应均不显著（T: ρ = −0.19；P: ρ = +0.21）。
* **留出验证**：脚本已跑通 prepare；当前样本下只能拆出 3–4 名验证被试（功效不足），待扩样本。
