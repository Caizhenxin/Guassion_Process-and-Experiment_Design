# Python_HDDM_Nonmatching — 含 NonMatching 试次的 DDM 拟合工作流

本目录把 **NonMatching 试次纳入 DDM 模型**，解决原流程"仅 Matching 试次导致的基线偏差"。

> ⚠️ **2026-09-30 修订**：修掉了两个**阻断级**问题（旧结果全部作废，见第四节）。
> 权威依据：`5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`

---

## 一、2026-09-30 修了什么

| # | 问题 | 旧行为 | 新行为 |
|---|---|---|---|
| 1 | **模型设定与数据不相容** | `depends_on={"v": "identity"}`：匹配与不匹配**共用同一个 `v`**（同一个 `z`）。其硬性推论是 `P(正确\|匹配) + P(正确\|不匹配) ≡ 1`，而实测（87 人）为 **1.458**（self 1.516 / stranger 1.395）——偏离 0.46，远超估计噪声 | 提供 M0–M3 规格阶梯，默认 **M3**：`response` 改为**正确性编码**，`v` 按身份、`z` 按 cell |
| 2 | **遗漏被伪造** | `rt = deadline`；`response = 1 − Correct` ⇒ 遗漏**恒落在"错误"一侧**。实测 group3 有 **1978/5200 = 38.0%** 的试次被这样伪造，会把 `v` 系统性压向 0 | 遗漏的 `rt` / `response` / `correct` 一律留空，只由 `omission` 标记；另存 omissions 文件供 omission-aware 似然使用 |

**顺带修掉的两处工程问题**
- `step1` 新增**永久化的按键映射自检**：以设计规则推导 `condition`，再与记录值逐行比对。这道检查正是查出 `EXP_data_group2_11.csv`（100% 反转）的那一个。
- `generate_notebook.py` 旧版把 step1/2/3 的代码**整份复制**进 notebook，四处副本各自漂移（其中一段缩进已坏）。现改为 notebook 只调用脚本，**脚本是唯一事实来源**。

---

## 二、目录结构

```
1_Code/Python_HDDM_Nonmatching/
├── step1_prepare_data.py    # Step 1: 数据预处理（含 NonMatching + 按键映射自检）
├── step2_hddm_fit.py        # Step 2: Docker 内 HDDM 拟合（M0–M3 规格阶梯；--chains 多链 + R̂/ESS）
├── step3_extract_params.py  # Step 3: 参数提取 + 派生量 Δv / b / Δb + 绘图
├── omission_likelihood.py   # 阶段 1: 解析 P(遗漏)（Wiener 生存函数）+ 双口径自检
├── omission_potential.py    # 阶段 1: 把逐格遗漏项挂到 pymc2 的 HDDM 上（含接线自检）
├── step4_omission_aware_fit.py  # 阶段 1: 三臂对比 Drop / Censor / Omission-aware
├── generate_notebook.py     # 由上面的脚本生成 Docker_Run_Nonmatching.ipynb（只做导航）
├── Docker_Run_Nonmatching.ipynb
└── README.md
```

---

## 三、快速开始

### Step 1（本机或容器均可）

```powershell
python "1_Code\Python_HDDM_Nonmatching\step1_prepare_data.py"
```

**输入**：`2_Data/Real_Data/UnExtact/raw/*.csv`（**87** 个原始被试数据；G2-11 已剔除）
**输出**：`2_Data/Real_Data/HDDM_Ready_Nonmatching/`
- `hddm_data_group*.csv` — 有反应试次（Drop 口径），HDDM 直接可用
- `hddm_omission_group*.csv` — 遗漏试次，供 omission-aware 阶段

### Step 2（必须在 Docker 内）

```bash
docker pull hcp4715/hddm

docker run -it --rm --cpus=4 \
  -v "/d/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work" \
  -p 8888:8888 hcp4715/hddm jupyter notebook
```

容器内：

```python
# 主模型
%run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M3

# 冒烟测试（先跑单组，300 draws，确认模型能被接受）
%run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M3 --groups 3 --draws 300 --burn 100

# 复现旧设定（被否证，仅存档）
%run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M0
```

**输出**：`HDDM_Traces_Nonmatching/model{M}_{组号}_stats.csv`、`*_traces.npz/.pkl`、`model_spec.json`

> 参数：`--draws`（默认 3000）、`--burn`（默认 500）、`--groups`（只跑指定组）、`--model {M0,M1,M2,M3,all}`

### Step 3（建议本机）

```powershell
python "1_Code\Python_HDDM_Nonmatching\step3_extract_params.py"
```

**输出**：`HDDM_Traces_Nonmatching/all_groups_ddm_params.csv`、`3_Figures/HDDM_Results_Nonmatching/ddm_params_{M}.png`

---

## 四、模型规格阶梯（`--model`）

| 规格 | `response` 编码 | `depends_on` | 可否拟合本数据 | 说明 |
|---|---|:---|:---:|:---|
| **M0** | 按键 | `v: identity` | ❌ | 旧设定。`P(正确\|匹配)+P(正确\|不匹配) ≡ 1` 被实测 1.458 否证，仅用于复现 |
| **M1** | 按键 | `v: cell` | ✅ | 四格各自一个 `v`，能拟合但 `a` 失去"速度—准确权衡"的解释 |
| **M2** | **正确性** | `v: identity`, `z: condition` | ✅ | 起点偏向按条件；不含身份差异 |
| **M3** | **正确性** | `v: identity`, `z: cell` | ✅ | **默认主模型**，可同时给出 Δv 与 Δb |

> ⚠️ **命名消歧**：代码里的 `M0–M3` 是**可直接运行的实现规格**；
> 规格文档 §3.4 的 `M0–M5` 是**概念上的消融阶梯**（含尚未实现的 `Δa` / `sv`）。两者编号相近但不等价：

| 代码 `--model` | 对应规格文档 §3.4 | 差异 |
|---|---|---|
| `M0` | M0 | 一致（代码里 `z` 仍自由估计，未强行固定 0.5） |
| `M1` | M1 | 一致 |
| `M2` | 介于 M2 与 M3 之间 | 起点偏向按 `condition`，暂不含身份维度 |
| `M3` | **M4** | 完整 Δz（`z` 按 `cell` = 身份 × 条件） |
| — | M5 | 辨识 `Δa` / `sv`，**尚未实现** |

### 为什么 M2/M3 才正确

`response` 改为**正确性编码**（`1 = 作对`）后，上界 = "正确"边界，于是：

- **`v` 是"朝正确方向积累证据的速率"** → 漂移方向随刺激自动翻转。两个正确率因此**不再互补**，可以同时很高——这正是 1.458 能被解释的原因。
- **`z` 仍是按键偏向**（这是刺激编码的精髓）。在"正确界"坐标下，一份恒定的匹配键偏向 `b` 表现为：

  | 刺激 | 正确界 = | z |
  |---|---|---|
  | 匹配 | 匹配键 | `0.5 + b` |
  | 不匹配 | 不匹配键 | `0.5 − b` |

  因此 `b = (z_匹配 − z_不匹配) / 2`；再让 `z` 依 `cell`（身份 × 条件）变化，就得到 **Δb**。

### 派生量（Step 3 逐 draws 计算，带不确定度）

```
Δv  = v(self) − v(stranger)                        证据优势成分
b_i = (z(匹配,i) − z(不匹配,i)) / 2                 身份 i 的匹配键偏向
Δb  = b_self − b_stranger                          偏向成分（SPE 的第二条通道）
```

> 独立 SDT 旁证（87 人，仅按匹配键）：`Δd′ = +0.41`、`Δc = −0.24` —— 两条通道都有信号，
> 与 Δv、Δb 的预期方向一致。

---

## 五、HDDM 就绪数据格式（Step 1 输出）

| 列名 | 类型 | 说明 |
|:---|:---|:---|
| `subj_idx` | int | 被试索引（0 起始，组内重编号） |
| `rt` | float | 反应时（秒，自刺激起点计） |
| `response` | int | **1 = 判断为 Matching（上界）, 0 = 判断为 NonMatching（下界）** — 按键编码 |
| `correct` | int | **1 = 作答正确, 0 = 作答错误** — 正确性编码（M2/M3 用它替换 `response`） |
| `identity` | int | 1 = self, 0 = stranger |
| `condition` | int | 1 = Matching 试次, 0 = NonMatching 试次 |
| `cell` | int | `identity * 2 + condition` → 0..3 |
| `deadline` | float | 反应窗口关闭时刻（秒）= `T + W` |
| `omission` | int | 主文件中恒为 0（遗漏行已移出）；omissions 文件中恒为 1 |

**omissions 文件的列**：`subj_idx, identity, condition, cell, deadline, T_ms, W_ms, P`

---

## 六、遗漏处理

**当前口径：Drop（只用有反应试次）。** 这是最保守、不会注入偏差的起点，但**不是终点**——
Leng et al. (2025) 证明忽略遗漏本身就会使参数有偏。

完整方案见规格文档 §4（四阶段路线）+ **§5（分步操作手册，含最终步骤 0–5）**：

| 阶段 | 内容 | 状态 |
|---|---|---|
| 0 | `deadline = T + W` + 反应窗口门控 | ✅ 已完成（遗漏率 MAE 0.072） |
| 1 | 遗漏进似然 + 三臂对比（Drop / Censor / Omission-aware） | 🔶 **代码已完成**（v0.17），正式对比待跑 |
| 2 | 补 `T+200` 处的点质量项（观测 RT = max(τ, T+200)） | 待做 |
| 3 | 塌缩边界 ANGLE / WEIBULL → 此时才需要 LAN + OPN | 可选 |

### 阶段 1 的三个文件怎么用

```bash
# ① 解析 P(遗漏) 的自检（解析 vs sim_utils；判据是"误差随 dt 收缩"）
python omission_likelihood.py

# ② 接线自检（不采样，只验父节点接对了格子 / logp 两条路径一致）
python omission_potential.py --group 1

# ③ 三臂对比（先冒烟，再正式）
python step4_omission_aware_fit.py --arm all --groups 1 --draws 1500 --burn 500
python step4_omission_aware_fit.py --arm all --draws 4000 --burn 1000 --chains 2
```

**似然形式**：`logL = Σ_作答试次 log f_Wiener(rt | θ_格子) + Σ_格子 n_遗漏(格子)·log P(遗漏 | θ_格子, deadline)`。

其中 `P(遗漏) = S(deadline − t0)`，`S(D)` 是 Wiener 首达时的生存函数（闭式谱级数，见
`omission_likelihood.py` 顶部）。**逐格**由构造保证：势函数的父节点直接复用 HDDM 观测节点
`wfpt(cell.identity).subj` 的 `parents`——它们恰好就是该格的 `(v, a, z, t)`。

> ⚠️ 三臂里的 **Censor 臂是已知有偏的对照**（把遗漏伪造成"恰好在截止时刻按错键"）。
> 它的用处是量化偏差有多大，**不是**可选的替代方案。g1 有 71.6% 遗漏，Censor 臂实测
> 把漂移压到 `v ≈ −5`。

> **OPN 的现状**：模型早已训练完成（`2_Data/Generate_Data/OPN_Training/opn_model.joblib`，
> test R² = 0.986 / MAE = 0.017），但**从未接入任何似然**。它是阶段 3 的工具，
> 阶段 1 用解析 Wiener CDF 或"自家仿真器预计算查表"即可（后者可与 `sim_utils` 逐点对账）。

---

## 七、注意事项

1. **旧产物已作废**：`HDDM_Traces_Nonmatching/_invalid_20260930_M0旧设定/` 下 25 个文件是旧设定 + 伪造遗漏跑出来的，**不得引用**。目录已挪进子文件夹，Step 3 的非递归 glob 不会再读到。
2. **`p_outlier` 现为 0**（与论文主口径配置 C 一致）。旧版为 `0.05`。这是一个**独立于本次修复**的口径变更，若要跨版本比较请先统一。
3. **`bias=False` 在该版本 HDDM 下不影响 `z` 的估计**（实测产物中存在 `z`、`z_subj.*`），保留仅为与原脚本一致。
4. **冒烟测试先行**：改过模型设定后，建议先 `--groups 3 --draws 300` 确认能被接受再全量跑。
5. **数据范围**：87 名被试（`EXP_data_group2_11.csv` 已剔除，见 `2_Data/Real_Data/Excluded/README.md`）。
6. **本套代码与 `Python_HDDM` 完全独立**，互不干扰；两者现在都不含被剔除被试。
7. **🆕 容器里的 HDDM 是 pymc 2.3.8，不是 PyMC v5**。规格文档 §5 步骤 2 的伪代码
   （`pt.constant` / `with pm.Model():`）**照抄无效**。挂 `pm.Potential` 的正确做法是把它与节点
   一起交给 `pm.MCMC`，再 `model.pre_sample()`——必须在分配 `SliceStep` **之前**让势函数进入
   节点集合。另：`kabuki.sample(chains>1)` 会 `deepcopy` 后用 `nodes_db` 重建 MCMC，
   **把势函数丢掉**，所以多链必须自己循环。
8. **🆕 多链会静默丢链**：`kabuki` 的单链异常被 `except Exception: return None` 吞掉。
   `step2` 因此显式比对 `model.chains` 与请求链数；R̂ 为 NaN 的个数单独计数。改动多链代码后别删这两道检查。
9. **🆕 `sim_utils` 有 √dt 离散偏差**：EM 只在网格点判越界，漏掉"越界后折回"的路径，
   于是**系统性高估遗漏率 ≈ 0.47·√dt**（项目 dt=0.002 时约 +0.02）。这是拿解析生存函数
   在 dt=0.002 / 0.0005 两个口径对账时发现的（误差按 √dt 收缩，比值 0.502）。
   用它做 PPC 或参数恢复时要把这层偏差算进程。

---

## 八、8 组实验条件

| 组别 | P | T (ms) | W (ms) | M = T+W | 被试数 |
|---|---|---|---|---|---|
| 1 | 0 | 30 | 300 | 330 | 11 |
| 2 | 0 | 30 | 600 | 630 | 11 |
| 3 | 120 | 30 | 600 | 630 | 10 |
| 4 | 120 | 80 | 600 | 680 | 11 |
| 5 | 8 | 100 | 1100 | 1200 | 11 |
| 6 | 120 | 500 | 1500 | 2000 | 10 |
| 7 | 120 | 30 | 800 | 830 | 12 |
| 8 | 120 | 80 | 800 | 880 | 11 |

合计 **87** 名被试、45,240 个正式试次、14,063 个遗漏（31.1%）。

---

*2026-09-30 修订。本目录的模型设定与遗漏口径以本文件 + 上述规格文档为准。*
