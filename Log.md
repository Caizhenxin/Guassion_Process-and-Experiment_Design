# 版本更新日志

---

## v0.17 (2026-10-01)

**责任人**：蔡振辛

### 执行结果一：M3 收敛诊断完成（升级到 4 链）

`step2_hddm_fit.py` 新增 `--chains N`（多链）+ 自动 **R̂ / ESS** 诊断。8 组全部按配置 C 口径重跑：
**4 链 × 8000 draws / 2000 burn（留存 6000/链）**，`p_outlier=0`，Drop 口径。

| 组 | 核心参数 R̂ 最大 | ESS 最小 | 超标 | NaN |
|---|---|---|---|---|
| g1 | 1.028 | 129 | 0 | 0 |
| g2 | 1.001 | 5430 | 0 | 0 |
| g3 | 1.003 | 3850 | 0 | 0 |
| g4 | 1.001 | 7122 | 0 | 0 |
| g5 | 1.001 | 6513 | 0 | 0 |
| g6 | 1.001 | 6256 | 0 | 0 |
| g7 | 1.000 | 9665 | 0 | 0 |
| g8 | 1.000 | 9633 | 0 | 0 |

**判据（R̂ < 1.05 且无 NaN）：✅ 8/8 通过。** g1 的 ESS 最低（129）符合预期——它只有 1625 个有效试次，
是全库最小的条件组。

**派生量对账（4 链 vs v0.16 的 1 链）**

| 量 | v0.17（4 链） | v0.16（1 链） | 结论 |
|---|---|---|---|
| Δv | **+0.403 ± 0.209** | +0.407 ± 0.195 | 几乎相同 |
| Δb | **+0.042 ± 0.029** | +0.042 ± 0.029 | 相同 |
| b 自我 / b 陌生人 | +0.075 / +0.033 | +0.075 / +0.033 | 相同 |

→ **v0.16 的单链结论本就已收敛**，多链只是把"未做收敛诊断"这个未决项补上，数字无需修订。

**两处防"静默失败"的措施**（缝 `kabuki` 的坑）：`kabuki.sample(chains>1)` 会把单链异常
`except Exception: return None` **吞掉**，于是链数悄悄变少而脚本毫不知情。step2 因此显式比对
`model.chains` 与请求链数，不一致直接报错；R̂ 为 NaN 的个数单独计数，不与"超标"混为一谈。

**运行方式**：容器被限制为 **8 核**（`NanoCpus=8`），故按 4 批并行、每批 2 组 × 4 链（各写
`model_spec_part*.json` 分片，避免并发覆盖），跑完合并回 `model_spec.json`。实测 16 条链争抢 8 核时
速率稳定在 ~0.4 s/iter，无退化。全程约 2 小时。

### 执行结果二：阶段 1「遗漏进似然」的代码落地

**① 解析 `P(遗漏)`** —— 新增 `1_Code/Python_HDDM_Nonmatching/omission_likelihood.py`

恒定边界 Wiener 首达时的生存函数，闭式谱级数：
`S(D) = (2π/a²)·e^{−v²D/2}·e^{−v·z·a}·Σ_k k·sin(kπz)[1−(−1)^k e^{va}]/(v²+(kπ/a)²)·e^{−k²π²D/(2a²)}`，
`P(遗漏) = S(deadline − t0)`。D≤0 时返回 1。

**② 逐格遗漏势函数** —— 新增 `1_Code/Python_HDDM_Nonmatching/omission_potential.py`

在 HDDM 的 pymc2 模型上挂一个 `pm.Potential`：
`logL_遗漏 = Σ_格子 n_遗漏(格子)·log P(遗漏 | θ_格子, deadline)`。
父节点直接复用观测节点 `wfpt(cell.identity).subj` 的 `parents`——
它们**恰好**是该格的 `(v, a, z, t)`（`z` 已是 Φ 还原后的 `z_subj(cell).s`），
因此"逐格"与"口径一致"两条硬约束由构造保证，不必自己拼层级先验。

**③ 三臂对比运行脚本** —— 新增 `1_Code/Python_HDDM_Nonmatching/step4_omission_aware_fit.py`
（`drop` / `censor` / `omission`，共用 M3 规格与采样设置）。多链在脚本内**自己循环**——
kabuki 的 `chains>1` 会 `deepcopy` 后用 `nodes_db` 重建 MCMC，**把势函数丢掉**。

### 一条方法论发现：仿真器的 √dt 离散偏差（影响全项目）

拿解析式与唯一事实来源 `sim_utils.simulate_trials` 对账 12 个真实条件：

| 口径 | 解析 vs 仿真 MAE |
|---|---|
| 项目 dt = 0.002 | 0.0204 |
| 细步长 dt = 0.0005 | 0.0107 |

比值 **0.5 = √(1/4)**：误差精确按 **√dt** 收缩，故残差是**仿真器的离散偏差**（EM 只在网格点判越界，
漏掉"越界后折回"的路径），不是解析实现的错。**据此把自检判据定为"误差必须随 dt 收缩"**，
而不是固定阈值——固定阈值既可能放过实现错误，也可能冤枉正确的实现。

> ⚠️ 这条附带解释了 v0.16 的一项残留：PPC 里"仿真一致高估正确率 +0.03~+0.10"，
> 其中约 0.02~0.05 可能就来自 `sim_utils` 在 dt=0.002 下的遗漏率离散偏差。**待阶段 2 的 PPC 复核确认。**

自检中还抓到过一个真 bug：最初的谱级数**漏了起点规范变换因子 `e^{−v·z·a}`**，误差达 0.23；
是靠 dt 扫描才暴露出来的（单看"MAE 0.23"无法判断是公式错还是仿真错）。

### 三臂冒烟（g1，400 draws / 150 burn，单链——**数字不可解释，只证管道通**）

| 臂 | 试次 | 用时 | v(0) | v(1) | a |
|---|---|---|---|---|---|
| drop | 1625 | 175 s | −0.127 | −0.019 | 0.362 |
| censor | 5720 | 201 s | **−5.034** | −4.871 | 0.889 |
| omission | 1625 | 555 s | −0.104 | −0.062 | 1.148 |

**Censor 臂的 `v ≈ −5.0` 是 §4.2 所证偏差的现场演示**：g1 有 71.6% 的试次是遗漏，
把它们全部伪造成"恰好在截止时刻按错键"，等于往数据里注入数倍于真实信号的反向证据，
漂移被压到 −5。**该臂只能作对照，不可作为结论**。

**势函数确实在起作用**：omission 臂全程 logp 从 **−7970.69 → −1458.52**（改善 6512 个对数单位）。

### 关键前置确认（spike）
- **容器的 HDDM 是 pymc 2.3.8，不是 PyMC v5**。规格文档 §5 步骤 2 的伪代码
  （`pt.constant` / `with pm.Model():`）照抄无效，须按 pymc2 改写。
- 可行路径：把 `pm.Potential` 与节点**一起**交给 `pm.MCMC`，再 `model.pre_sample()`——
  必须在 `pre_sample` 分配 `SliceStep` **之前**让势函数进入节点集合，事后追加拿不到正确计算集。
- `SliceStep` 无梯度，兼容不可导的解析式（契约 C6 在 pymc2 下更容易满足）。

### 性能：谱级数矩阵化
势函数在一次迭代里会被调用上百次（每个随机节点的步进器都要算一遍），逐项 Python 循环会把采样
拖慢 3 倍以上。改成矩阵形式（`(K, n)` 一次算完所有 k 项）后：**2.12 ms → 0.53 ms / 次（快 4×）**，
且与循环版逐点最大差 **1.3e-13**。项数上界由指数因子解析给出：`K ≈ √(2·log(1/tol))·a/(π√D)`。

### 三级自检（全部通过）
1. **`omission_likelihood.py`**：矩阵版 vs 循环版 ≤ 1e-10（实测 1.3e-13）；解析 vs 仿真误差随 dt 收缩（比值 0.502）
2. **`omission_potential.py`**：逐格结构与父节点对账 44 格，结构错误 **0** 条；pymc 路径的 logp 与
   独立重算 **差 0.00e+00**
3. **遗忘数对账**：进入似然的遗漏数 4095 = 遗漏文件 4095，无未覆盖格子

### 未决
- **三臂正式对比未跑**（只跑了 400 draws 冒烟）：需在无争抢的机器上按 2–4 链跑齐 8 组，
  再套 §5 步骤 4 的四项判据（逐条件遗漏率 / responded 正确率 / RT 分位 / 三臂参数差异）
- **`T+200` 点质量项未做**（规格文档 §4.3 阶段 2）：g1 有效窗口仅 100 ms，该项缺席对 g1 影响最大
- **未做 PPC**：需用新口径复核 v0.16 的"仿真高估正确率"是否部分来自 √dt 偏差
- 模型比较（M0/M1/M2）按用户决定暂缓

### 文件变更
- 修改: `1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py`（`--chains` / `--spec-file` / arviz R̂+ESS / 链数核对）
- 修改: `1_Code/Python_HDDM_Nonmatching/step3_extract_params.py`（读 `stem` 字段）
- 新增: `1_Code/Python_HDDM_Nonmatching/omission_likelihood.py`（解析 P(遗漏) + 双口径自检）
- 新增: `1_Code/Python_HDDM_Nonmatching/omission_potential.py`（逐格势函数 + 接线自检）
- 新增: `1_Code/Python_HDDM_Nonmatching/step4_omission_aware_fit.py`（三臂对比）
- 新增（spike）: `_scratch/spike_hddm_potential.py`
- 更新（拟合产物）: `2_Data/Real_Data/HDDM_Traces_Nonmatching/modelM3_*{stats.csv,traces.npz,traces.pkl,_conv.csv}`、`model_spec.json`
- 新增（三臂产物）: `2_Data/Real_Data/HDDM_Traces_Nonmatching/omission_arms/`（冒烟）

---

## v0.16 (2026-10-01)

**责任人**：蔡振辛

### 执行结果：M3 全量拟合完成（87 人 / 8 个条件组）

在 Docker HDDM 1.0.1RC 中跑完 `step2_hddm_fit.py --model M3`（8 组 × 3000 draws / 500 burn，单链，**Drop 口径**），本机跑 step3 + 后验预测检验。

**派生量（后验均值 ± 跨组 SD）**

| 量 | 均值 | 逐组 | 8/8 同号 |
|---|---|---|---|
| **Δv**（证据优势） | **+0.407 ± 0.195** | +0.12 / +0.50 / +0.46 / +0.73 / +0.54 / +0.19 / +0.38 / +0.33 | ✅ 全为正 |
| **Δb**（匹配键偏向差） | **+0.042 ± 0.029** | +0.01 / +0.01 / +0.01 / +0.07 / +0.08 / +0.04 / +0.06 / +0.06 | ✅ 全为正 |
| b 自我 | +0.075 ± 0.024 | — | — |
| b 陌生人 | +0.033 ± 0.023 | — | — |

**与独立 SDT 旁证对账（v0.10/v0.11 的 87 人数据）**

- **Δv = +0.407 vs Δd′ = +0.410** —— 两个完全独立的方法（层级 DDM vs 描述性 SDT）给出几乎相同的数字
- Δb = +0.042 vs Δc = −0.24（方向一致：自我更偏向匹配键）
- **b 陌生人 = +0.033 > 0** —— 即使陌生人条件下也偏向匹配键，**实测确认 `z0` 不能钉在 0.5**（规格文档 §3.2 第 3 条）

**后验预测检验（`_scratch/ppc_m3.py`，用 `sim_utils` 仿真 4000 试次/格）**

- 四格正确率绝对误差：**均值 0.060、最大 0.126**
- **`P(正确|匹配) + P(正确|不匹配)`**：观测 1.315（陌生人）/ 1.433（自我），仿真 1.375 / 1.510
  → 模型能产生 > 1 的和（**旧单 v 设定在数学上被强制为 1.000**），修复生效 ✅
- **残留系统性偏差**：仿真一致地略微**高估正确率**（多数格 +0.03 ~ +0.10）——
  与 Drop 口径的已知偏差方向一致（丢弃遗漏截断了 RT 右尾 → 拟合出偏大的 v → 过度自信）。
  **这正是 §5 阶段 1（遗漏进似然）的实证动机。**

### 执行阶段修掉的两个 bug
- **`step2` 调用点参数错位**：改了 `fit_one` 签名却漏改调用点（`fit_one(df, gid, ...)` vs `(gid, df, ...)`），启动即崩。已修。
- **🔴 HDDM 会就地改写传入的 `depends_on` dict**（`'identity'` → `['identity']`）。
  step2 传的是模块级常量本身，常量被污染后 `derive` 里 `z_key == 'cell'` 永远为假，
  **Δb 被静默丢弃且不报任何错**。这是最危险的一类 bug——若未发现，论文里只会剩下 Δv 一个成分。
  修法：step2 传 `copy.deepcopy`（`model_spec.json` 现正确记录为字符串）、step3 加 `single()` 归一化，
  并补 `M3_list` 回归用例进离线自检 `_scratch/selftest_step3_derive.py`。

### 我自己检验脚本的一处错误（记录以备复核）
`ppc_m3.py` 初版在非匹配试次上直接传了 `z_N`，漏了坐标反射。HDDM 拟合用的是「正确界」坐标，
非匹配试次的正确界是下界，搬到物理按键界（上界=匹配键）时须取 `1 − z_N`。
修正后四格绝对误差从 **0.126 → 0.060**。**注意：这是检验脚本的错，不是拟合流程的错。**
（物理上两者表达同一份匹配键偏向：`z_phys = z_M = 1 − z_N` ⟹ `b = (z_M − z_N)/2`，与 step3 一致。）

### 验证
- 全部产物：`HDDM_Traces_Nonmatching/modelM3_{1..8}_{stats.csv,traces.npz,traces.pkl}` + `model_spec.json`（8 条）+ `all_groups_ddm_params.csv`
- 图：`3_Figures/HDDM_Results_Nonmatching/ddm_params_M3.png`
- 旧设定产物仍在 `HDDM_Traces_Nonmatching/_invalid_20260930_M0旧设定/`（25 个文件，作废保留）

### 未决
- **收敛诊断未做**：单链 3000/500。定稿前需升到配置 C 口径（4 链 × 8000/2000）并报 R-hat / ESS
- **逐组 CI 较宽**（每组仅 10–12 人）：结论应建立在「8/8 同号」上，跨组汇总而非单组显著性
- **遗漏仍未进似然**：PPC 的残留高估正确率即其代价；下一步是 §5 阶段 1–2
- 模型比较（M0/M1/M2）按用户决定暂缓

### 文件变更
- 修改: `1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py`（`deepcopy` 修复 + 调用点参数修正 + `single()` 归一化）
- 修改: `1_Code/Python_HDDM_Nonmatching/step3_extract_params.py`（`single()` 归一化 + `z(N)→z_trans(N)` 还原）
- 修改: `_scratch/selftest_step3_derive.py`（新增 `M3_list` 回归用例）
- 新增: `_scratch/ppc_m3.py`、`_scratch/docker_check_spec.py`、`_scratch/docker_smoke_m3.py`、`_scratch/docker_probe_derive.py`、`_scratch/docker_probe2.py`
- 新增（拟合产物）: `2_Data/Real_Data/HDDM_Traces_Nonmatching/modelM3_*`、`model_spec.json`、`all_groups_ddm_params.csv`
- 新增（图）: `3_Figures/HDDM_Results_Nonmatching/ddm_params_M3.png`
- 修改: `5_Reference/README.md`（§七）、`Log.md`（本条目）

---

## v0.15 (2026-10-01)

**责任人**：蔡振辛

> 本条目是 `5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md` §5 **步骤 0** 的执行记录
> （四个阻断级错误：`v` 依 `condition`、消除遗漏伪造、`p_outlier` 归零、重生成 87 人数据）。

### 问题修复（本次主线：`1_Code/Python_HDDM_Nonmatching/` 的两处阻断级错误）

**修复 1｜模型设定与数据不相容**
- 旧：`depends_on={"v": "identity"}` —— 匹配与不匹配**共用同一个 `v`**，硬性推论 `P(正确|匹配) + P(正确|不匹配) ≡ 1`；实测（87 人）为 **1.458**（self 1.516 / stranger 1.395）
- 新：引入 **M0–M3 规格阶梯**（`--model`），默认 **M3** = 正确性编码 + `v` 按身份 + `z` 按 cell
  - 正确性编码使漂移方向随刺激自动翻转，两个正确率不再互补（1.458 才可被解释）
  - `z` 仍按按键编码，于是 `b = (z_匹配 − z_不匹配)/2`、`Δb = b_self − b_stranger`
- M0 保留可复现（旧结论存档），M1/M2 作为中间消融

**修复 2｜遗漏试次被伪造**
- 旧：`rt = deadline`、`response = 1 − Correct` ⇒ 遗漏恒为"错误侧"；实测 group3 有 **1978/5200 = 38.0%** 的试次被伪造
- 新：遗漏的 `rt` / `response` / `correct` 一律留空，只由 `omission` 标记；主文件改为 **Drop 口径**（有反应试次），并另存 `hddm_omission_group*.csv` 保留后续 omission-aware 似然所需的全部信息

**修复 3｜`p_outlier` 归零**（§5 步骤 0 第三项）
- `0.05` → **`0.00`**，对齐论文主口径配置 C。依据 v0.12 的判断：HDDM 的均匀污染分布与 OPN 遗漏项语义重叠，两者叠加会双重计入，接 OPN 前必须归零

### 工程加固
- `step1_prepare_data.py` 新增**永久化按键映射自检**：设计规则 vs 记录值逐行比对（这道检查正是查出 `EXP_data_group2_11.csv` 的那一个）。实测 45,240 行全部一致 ✅
- `generate_notebook.py` 重写：旧版把 step1/2/3 代码**整份复制**进 notebook，四处副本各自漂移且其中一段缩进已坏（会生成语法错误的 cell）。现改为 notebook 只调用脚本，**脚本为唯一事实来源**
- `step3_extract_params.py` 重写：按规格解释参数，新增 `Val` 类在后验 draws 上做代数运算，派生量 Δv / b / Δb **带正确的不确定度**；同时修掉旧版"用 v_self 的 CI 当 SPE_v 误差棒"的错误

### 数据变更
- `HDDM_Ready_Nonmatching/` 用 87 人重新生成（8 组有反应文件 + 8 组 omissions 文件，新列结构含 `correct` / `cell` / `deadline`）
- 旧迹线 25 个文件移入 `HDDM_Traces_Nonmatching/_invalid_20260930_M0旧设定/`（作废但保留，Step 3 的非递归 glob 不会再读到）

### 验证
- `step1_prepare_data.py` 实跑通过：87 文件 / 45,240 正式试次 / 遗漏 14,063（31.1%）/ 映射自检 100% 一致
- `_scratch/selftest_step3_derive.py`：用构造后验 draws 离线验证 M0–M3 四个规格的派生量，**全部通过**（含"无 traces 仅有 stats"的退化路径）
- 四个脚本 `py_compile` 全部通过
- **未启动 Docker**（按用户要求由其在容器内运行 Step 2）

### 未决
- **M3 全量拟合尚未运行**：需在 Docker HDDM 中执行 step2（建议先 `--groups 3 --draws 300` 冒烟）。跑出结果后 spec 文档 §2.2 的模型比较（M0–M3）即可落地
- 遗漏正式纳入似然（§5 步骤 1–4）仍未实施；阶段 1 的主口径已由 v0.12/v0.13 定为「解析 Wiener CDF + 论文 `ddm_opn.onnx` 独立校验」
- Step 3 的派生量自检只覆盖"解析代数"，尚未用真实后验做端到端验证（依赖上一项）

### 文件变更
- 修改: `1_Code/Python_HDDM_Nonmatching/step1_prepare_data.py`（重写）
- 修改: `1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py`（重写）
- 修改: `1_Code/Python_HDDM_Nonmatching/step3_extract_params.py`（重写）
- 修改: `1_Code/Python_HDDM_Nonmatching/generate_notebook.py`（重写）
- 修改: `1_Code/Python_HDDM_Nonmatching/Docker_Run_Nonmatching.ipynb`（重新生成）
- 修改: `1_Code/Python_HDDM_Nonmatching/README.md`（重写）
- 新增: `_scratch/selftest_step3_derive.py`
- 重新生成: `2_Data/Real_Data/HDDM_Ready_Nonmatching/`（16 个文件）
- 移动: `2_Data/Real_Data/HDDM_Traces_Nonmatching/*` → `_invalid_20260930_M0旧设定/`
- 修改: `5_Reference/README.md`（§七 待办：重生成/修正两项更新为完成状态）、`5_Reference/AGENTS.md`（§三 真实数据 88 → **87** 人）、`Log.md`（本条目）

---

## v0.14 (2026-10-01)

**责任人**：蔡振辛

### 新增方案
- **遗漏建模的完整落地操作手册**：把原「实施清单」（条目级表格）升级为**分步可执行路线**（`路线B模型规格与遗漏建模路线_20260930.md` §5，原 §5 顺延为 §6）
  - **步骤 0**：先修四个阻断级错误（`v` 依 `condition`、消除遗漏伪造、`p_outlier` 归零、重生成 87 人数据）
  - **步骤 1**：实现 `P_遗漏(θ,d)` 三选一 —— **A 解析 Wiener CDF（主口径）/ B `sim_utils` 查表 / C 论文 `ddm_opn.onnx`（独立校验器）**
  - **步骤 2**：**在 HDDM 的 `pm.Model` 上加一个 `pm.Potential`**（含伪代码骨架），而非用 PyMC 重写整套 DDM 似然；附两个必须先验证的 spike 点
  - **步骤 3**：三条硬约束（逐格 / 口径 / `T+200` 点质量）
  - **步骤 4**：三臂验收（Drop / Censor / Omission-aware）+ 四项判据
  - **步骤 5**：可选升级到塌缩边界（复用论文 ANGLE / WEIBULL 网络，但需先标定）
  - 附依赖关系图

### 关键澄清（对用户疑问的回应）
- **"接口"≠"模型没上传"**。三个 ONNX 均已上传且可运行；缺的是**使用说明**，具体为三件事：① 5 个输入的**顺序** ② 每个输入的**标度** ③ 输出的**语义**。三者已全部通过三轮实证确定（见 v0.13）。搞错的代价有实测数字：顺序错 → 输出无意义；标度错 → MAE 0.274；语义错 → MAE 0.75

### 文档一致性修复
- **发现并记录一处适用范围冲突**（按 `AGENTS.md` §四 规则 4 处理）：`AGENTS.md` §三 把「lapse 不建模」列为硬事实，但其三次否证针对的是**"机制化 lapse（`v←0`）"**，而论文用的是**"均匀 RT 分布混合"**——后者本项目从未测过。已在 `README.md` §五 新增「⚠️ 一处需要限定适用范围」小节
- 修正 `路线B模型规格与遗漏建模路线` 的章节编号重复（两个「## 6」）

### 文件变更
- 修改: `5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`（§5 重写为操作手册、§7 资产表更新、§8 可视化清单、编号修正）
- 修改: `5_Reference/README.md`（§五 新增 lapse 适用范围限定）
- 修改: `Log.md`（本条目）

---

## v0.13 (2026-09-30)

**责任人**：蔡振辛

### 新增方案
- **论文官方网络的可用性审计**：对本地副本 `D:\GitHub_programe\GitHub\opn`（上游 `github.com/Jasonleng/opn`）做资产盘点、接口反推与精度实测
  - **结论：可以直接用，且比自家 OPN 更准（MAE 0.0104 vs 0.0247，差 2.4 倍）**
  - 资产：`ddm_opn.onnx`(5维) / `angle_opn.onnx`(6维) / `weibull_opn.onnx`(7维) 三个网络可用；`runModel*.py` **不可运行**（依赖仓库中不存在的 `../network/**/*.jax`）；**无 LICENSE**
  - **最大价值在 ANGLE / WEIBULL**（阶段 3 塌缩边界），恒定边界阶段 1 用解析 CDF 即可

### 关键发现
- **接口无文档，靠三轮实证反推**（三次脚本均只读、可重跑）：
  1. **差值不变性**（利用 `F(d,t)=F(d−t)`）：槽 (3,4) 变化 **0.000161**，次优对是它的 130 倍 → `(t, deadline)` 位置确定；**输入未标准化**
  2. **相关性扫描**（12 种布局 × 输出变换）：`(v,a,z,t,dl)` 得 ρ=**0.958**，其余全部 ≤0.78 → 顺序与 `runModelDDM.py` 一致，但**输出语义相反**
  3. **标度搜索**：**`a/2`** 使 MAE 从 0.2736 → **0.0033**，ρ=**0.9970**
  - 最终契约：**输入 `(v, a/2, z, t0, deadline)`，输出 `exp(raw) = P(omission)`，batch 固定 1**
- **`a/2` 暴露上游仓库的内部不一致**：`runModelDDM.py` 给 ssms 仿真器与 CPN 传同一个 `a`；论文 Methods 却明写边界在 `±a`（分离度 = 2a）
- **独立复检**（20 组全新参数，确认非过拟合）：MAE **0.0055**、Pearson r **0.9996**、Spearman ρ **0.9981**

### 决策
- **阶段 1**：改用「解析 Wiener CDF（主口径）+ 论文 `ddm_opn.onnx`（独立校验器）」；自家 OPN 的"收窄先验重训"优先级**下调为备选**
- **阶段 3**：从"可选"**升级为强烈推荐**——直接用 `angle_opn.onnx` / `weibull_opn.onnx`，省掉自训 LAN+OPN 的全部工作
- **P0-1（numba bug）仍须修**：只要自家 OPN 还有被使用的可能，这个静默污染源就要堵上
- 新增五条使用条款 **P1–P5**（接口固化为 adapter、每次用前对账 MAE≤0.01/r≥0.99、不分发 ONNX、阶段 1 双实现互校、阶段 3 直用）

### 环境
- GitHub 直连仍不可用（DNS 失败），改用本地副本 `D:\GitHub_programe\GitHub\opn`
- 在 `1_Code/.venv` 安装 `onnxruntime 1.30.0`（用于接口验证与精度实测）

### 文件变更
- 修改: `5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`（新增 §4.6 官方网络审计，含 4.6.1–4.6.6）
- 新增: `_scratch/check_paper_repo_assets.py`、`_scratch/identify_paper_opn_layout.py`、`_scratch/identify_paper_opn_layout2.py`、`_scratch/identify_paper_opn_layout3.py`、`_scratch/verify_paper_opn_final.py`
- 修改: `5_Reference/README.md`（§三 补 §4.6）、`Log.md`（本条目）

---

## v0.12 (2026-09-30)

**责任人**：蔡振辛

### 新增方案
- **OPN 现状审计与接入似然的接口约定**：对照 Leng et al. *The Perils of Omitting Omissions*（本地 PDF 全文精读），系统审计 `1_Code/Python_for_Check/Omission/OPN_Training/`
  - 论文的三条接口契约：① LAN 只在无解析似然时才必需（恒定边界下解析似然等价）② OPN 输入 = `θ_SSM` + deadline，输出 = 遗漏对数似然 ③ lapse 是「均匀 RT 分布 `1/(2T)`」与 SSM 混合
  - **进度定位：原计划 Part 1–8，实际完成 Part 3–4，Part 5（联合似然）–Part 7（三臂对比）一行未写**
  - 产出 **C1–C8 八条可执行接口约定**（逐格而非逐块、参数口径三件套、求解器必须无梯度、门控只管 RT 不管遗漏、`p_outlier` 须归零等）
  - 关键修正：原计划「PyMC + NUTS」走不通（sklearn MLP 无梯度）；**在 `Python_HDDM_Nonmatching` 上挂 `pm.Potential` 优于用 PyMC 重写整套 DDM 似然**

### 问题修复（发现两处，均经实测确认）
- **🔴 P0-1｜numba 路径遗漏计数 bug**：`_simulate_ddm_batch_numba_kernel` 在**下边界命中**处 `omission_count += 1`，把正常反应计入遗漏
  实测同参数：vectorized **2.26%** vs numba **27.42%**，多算的 5032 恰为下边界命中数
  **当前潜伏**（系统 Python 无 numba，存档数据用的是正确路径：随机 25 组重算差值均值 +0.0001）**但已上膛**——`1_Code/.venv` 装着 numba 0.65.1，README 还"强烈推荐"装它
- **🔴 P0-2｜训练先验零膨胀 → 项目关心区系统性低估**：56.6% 训练样本落在 `y<0.01` 区，导致报告的 test R²=0.986 主要是"零区蒙对"
  - 分区精度：`y<0.01` 区 MAE 0.0046；**项目关心的 `0.2–0.8` 区 MAE 0.032（7 倍）**
  - 在 6 个真实条件上误差**几乎全为负**（g7 self −0.051、g4 stranger −0.044、g5 stranger −0.031）
  - OPN vs 仿真真值 MAE = 0.0224，约为蒙特卡洛噪声底（0.0071）的 3 倍 → 属真实模型误差

### 附带发现
- 🟠 `plot_training_diagnostics` 是坏代码（传 `opn=None, scaler=None` 必抛 AttributeError；主入口用的是另一个函数，其 try/except 兜住了）
- 🟠 **论文的 lapse 形式本项目从未测过**：项目三次否证的是"机制化 lapse（v←0）"，论文用的是"均匀 RT 分布混合"，两者不同。而 g3 的遗漏缺口（观测 .386 vs 仿真 .165）恰是论文声称 lapse 混合能处理的那类问题 → 应作为并列模型臂纳入
- 🟡 `Python_HDDM_Nonmatching` 用 `p_outlier=0.05`，与配置 C 的 0 冲突；且 HDDM 的均匀污染分布与 OPN 遗漏项语义重叠，叠加会双重计入 → 接 OPN 前须归零

### 验证
- `_scratch/check_opn_data_provenance.py`（只读）：判定存档训练数据来自正确代码路径，差值均值 +0.0001 / 标准差 0.0021
- `_scratch/check_opn_interface_fitness.py`（只读）：分区精度报告 + 6 个真实条件上 OPN/仿真/观测三方对比（仿真真值用 60,000 试次）
- 论文全文抽取至 `_scratch/omission_paper.txt`（21 页 / 44,873 字符），便于后续复核引用

### 未决
- 阶段 1 的遗漏概率用**重训的 OPN** 还是**`sim_utils` 网格+插值查表**（后者可逐点对账，无循环论证；OPN 的价值在阶段 3 塌缩边界才真正体现）
- 是否纳入论文式 lapse 混合（需先跑模型比较）

### 文件变更
- 修改: `5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`（新增 §4.5 OPN 现状审计，含 4.5.1–4.5.7 七个小节）
- 新增: `_scratch/check_opn_data_provenance.py`、`_scratch/check_opn_interface_fitness.py`、`_scratch/omission_paper.txt`
- 修改: `5_Reference/README.md`（§三 规格文档条目补 OPN 审计）、`Log.md`（本条目）

---

## v0.11 (2026-09-30)

**责任人**：蔡振辛

### 数据变更
- **剔除被试 `EXP_data_group2_11.csv`**（原因：中途实验卡死、重新进入后按键映射记录错误，`CorrectKey` 100% 落在错误模式上）
  - 两份副本一并移出数据树：`UnExtact/raw/` → `Excluded/`；`UnExtact/emp_data/` → `Excluded/EXP_data_group2_11.emp_data_copy.csv`
  - 可用被试 **88 → 87**；正式试次 45,760 → **45,240**；四格各 11,310 试次（仍完全平衡）
  - 新增 `2_Data/Real_Data/Excluded/README.md`（剔除依据、影响范围、恢复方式、下游同步清单）；`UnExtact/README.md` 顶部加警示
- 87 人口径下重算 §3 全部描述统计与 SDT 数字，已回填 `生成模型编码约定审查_20260930.md`

### 新增方案
- **路线 B 模型规格**：新建 `5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`
  - 逐试次生成规则（身份 × 刺激 → `v` 按正确性编码、`z` 按按键编码、`μ = v × sign(S)`）
  - 完整参数表 + **四个必定的参数化选择**：身份项加性、`Δz` 取常数、**`z0` 必须自由（不能钉在 a/2）**、`Δa`/`sv` 由模型比较决定
  - `Δv`/`Δz` 分离公式：`(SPE匹配 ± SPE不匹配)/2`（代入数据得 证据 ≈ +6.4 pt、偏向 ≈ +7.8 pt）
  - M0–M5 逐层消融清单 + 四格 PPC 验收标准
  - **落地成本极低**：`sim_utils.simulate_trials` 已支持逐试次 `v`，刺激编码**零改动**即可实现

### 问题修复（发现两处既有错误，均为阻断级）
- **`Python_HDDM_Nonmatching` 的模型设定与数据数学上不相容**
  `depends_on={"v":"identity"}` 使匹配与不匹配共用同一个 `v`，其硬性推论是 `P(正确|匹配) + P(正确|不匹配) ≡ 1`；
  实测（87 人）为 **1.458**（self 1.516 / stranger 1.395）。偏离 0.46，远超估计噪声。
  → 必须改为 `v` 依 `condition`，或改用刺激编码。复核脚本：`_scratch/check_single_v_consistency.py`
- **遗漏试次被伪造为"恰在 deadline 按了错误键"**
  `step1_prepare_data.py` 对遗漏行设 `rt = deadline`、`response = 1 − Correct`（恒为错误侧）。
  group3 实测 1978/5200 = **38.0%** 的试次 `rt` 精确等于 0.630 s 且方向恒为错。
  → 比"忽略遗漏"更严重（反向注入偏差）。两次拟合（匹配版恒错 / 不匹配版恒按错键）的遗漏口径还互不相同，跨版本比较本身也不成立。

### 遗漏建模路线（四阶段）
- 盘点更正：**OPN 早已训练完成**（`2_Data/Generate_Data/OPN_Training/opn_model.joblib`，fast 模式，5 特征，**test R² = 0.986 / MAE = 0.017**，2026-07-21）；缺的是**接入似然**，不是训练
- 关键判断：恒定边界 DDM 的遗漏概率有解析式（Wiener 首达时 CDF），或可用**自家仿真器预计算查表**——两者都可与 `sim_utils` 逐点对账。**OPN 真正被需要的地方是阶段 3 的塌缩边界**（ANGLE / WEIBULL，post-deadline 质量无解析式）
- 四阶段：0 deadline 口径修正（已完成，遗漏率 MAE 0.072）→ 1 遗漏进似然 + 三臂对比（Drop / Censor / Omission-aware）→ 2 补 `T+200` 点质量项（观测 RT = max(τ, T+200)）→ 3 塌缩边界 + LAN/OPN（可选）

### 验证
- `_scratch/check_nonmatch_quality.py`：剔除后 87 人全部通过映射一致性检查，四格平衡，`Correct` 列零冲突
- `_scratch/check_single_v_consistency.py`：单 `v` 设定的可证伪推论（两正确率之和 = 1）被否证，偏离 +0.458
- 本轮只出方案，未做任何代码改动；两项修复见下方"问题修复"

### 未决
- 是否将遗漏模型升级到塌缩边界（需先跑 M0–M5 与三臂对比再定）
- `Δz` 是否需要随 P/T/W 变化（建议交由 AutoRA 的设计优化回答，而非现在拍函数形式）

### 文件变更
- 新增: `5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`
- 新增: `2_Data/Real_Data/Excluded/README.md`
- 新增: `_scratch/check_single_v_consistency.py`
- 移动: `EXP_data_group2_11.csv`（raw 与 emp_data 两份 → `2_Data/Real_Data/Excluded/`）
- 修改: `2_Data/Real_Data/UnExtact/README.md`、`5_Reference/02_方法学审查/生成模型编码约定审查_20260930.md`（87 人口径回填）、`5_Reference/README.md`（§三、§七）、`_scratch/check_nonmatch_quality.py`、`Log.md`（本条目）

---

## v0.10 (2026-09-30)

> ⚠️ 本条目中的核查数字为 **88 人**口径；v0.11 已剔除 G2-11，改用 **87 人**。差异极小（Δd′ 0.42→0.41、Δc −0.23→−0.24），不改变任何结论。

**责任人**：蔡振辛

### 新增功能
- **生成模型编码约定审查**：新建方法学文档，系统审视 `S2 gen_data_jh.ipynb` 的整体思路（不改参数）
  - 定位出三个**未声明的隐含约定**：证据在 `0↔a` 间累积且 `response=1/2` ⇒ **响应编码**；`evidence = a/2` ⇒ **起点 z ≡ a/2**；`conditions` 只有身份、无刺激 ⇒ **只覆盖匹配条件**
  - 论证核心问题：SPE 的两套机制解释（H1 证据优势 Δv / H2 匹配键偏向 Δz）在"只跑匹配试次"的数据上**预测完全相同**，只有不匹配试次能让二者反号分离
  - 给出三条修复路线（A 最小改动只声明 / **B 全 2×2 + stimulus coding（推荐）** / C 响应编码拆四格），并指明仓库已有配套资产 `1_Code/Python_for_Check/ddm_stim_coding/`
  - 附带指出三处与参数无关的思路问题：循环论证定位、遗漏的"丢弃+重采样"改变分布、身份效应只被允许进入 `v`（宜改加性）
- **不匹配试次入库质量核查（一手数据）**：88 名被试 / 45,760 个正式试次，逐文件比对记录 `CorrectKey` 与编号规则推导值
  - 质量结论：**87/88 完全一致**；`Correct` 列与 `(Response == CorrectKey)` 0 冲突；`Response` 无脏值；四格各 11,440 试次**完全平衡**
  - 异常 **1 例**：`EXP_data_group2_11.csv`（G2·被试11·mod3）理论应为 SAME、实为 ALT，**100% 反转**（与 `刺激呈现期按键无法记录_原因排查与结论.md` 早前记录一致）
- **SPE 的 d′/c 分解（关键发现）**：合并口径下，自我优势**同时存在于两条通道**
  - 四格正确率：匹配·自我 80.85% / 匹配·陌生人 66.57%（+14.3 pt）；不匹配·自我 62.33% / 不匹配·陌生人 63.09%（−0.8 pt）
  - 信号检测论：**Δd′ = +0.42（辨别力更高）、Δc = −0.23（更偏向匹配键）**；口径 B（遗漏算作未按匹配键）为 Δd′ = +0.29、Δc = −0.18，方向不变
  - 结论：`z ≡ a/2` 的生成器**结构性无法表达**其中约一半的效应，故不匹配列不是"锦上添花"而是必需

### 验证
- 核查脚本 `_scratch/check_nonmatch_quality.py` 为**只读**，直接读 `2_Data/Real_Data/UnExtact/raw/` 原始 CSV，未引用任何中间产物，可随时重跑核对
- 逐被试再平均的 `d′`（口径 A：自我 1.477 / 陌生人 0.938）经确认被天花板效应放大，文档中已标注**不得单独引用**，统一以合并口径为准
- 遗漏率约 30% 且自我低于陌生人（匹配列 28.1% vs 32.7%）：口径 A/B 的差异全部来自这一点，已在文档 §3.4 作为限定条件列出

### 决策与未决
- **决策**：本轮**不改生成模型代码**，仅出方案与证据；修复路线以路线 B（stimulus coding）为推荐，待确认后实施
- **未决**：`EXP_data_group2_11.csv` 是剔除还是按实际按键规则重算
- **未决**：不匹配列纳入正式建模的时点与遗漏（第三类反应）的建模方式

### 文件变更
- 新增: `5_Reference/02_方法学审查/生成模型编码约定审查_20260930.md`
- 新增: `_scratch/check_nonmatch_quality.py`
- 修改: `5_Reference/README.md`（§三 文档清单、§七 待办）
- 修改: `Log.md`（本条目）

---

## v0.9 (2026-09-30)

**责任人**：蔡振辛

### 新增功能
- **库级运行时架构分析 + 交互式架构图**：用 archify v3.0.1 生成本库高层运行时架构图，单文件 HTML 交付（777 KB，离线可开、深浅主题切换、可搜索/导出 PNG/SVG/WebM）
  - 规范源文件与产物：`.archify/architecture-spe-runtime-20260930-122446/candidate.json` + `spe-runtime.html`
  - **11 个核心组件**：被试 / Psychtoolbox 实验程序 / SPE Database / 真实行为数据 / HDDM 数据准备 / HDDM 层次贝叶斯拟合 / DDM 参数估计 / GP 残差代理模型 / DDM 仿真引擎 / 验证链 / 候选设计点
  - **一条加粗主路径（闭环）**：实验采集 → 真实数据 → HDDM 三步 → GP 代理 → DDM 仿真 → 验证 → 候选设计点 → 建议下一轮实验
  - **三个信任边界**（虚线/隔离区）：实验采集环境（外部输入）· Docker 容器（dockerHDDM 隔离执行）· 本地分析环境（受控）
  - 4 张说明卡片：主业务路径 / 外部依赖与环境 / 关键产物与一键复现 / 设计取舍
  - 每个组件均附"仓库文件 + 行号"证据引用，绑定 revision `6d78a937`

### 环境与工具链（本次踩坑，已解决）
- **GitHub 直连不可用**（DNS 解析失败）→ 改用 jsDelivr 拉取 `archify.zip` 安装到 `~/.trae-cn/skills/archify`；未使用 `npx skills add`（其交互式安装在本环境会挂起）
- **archify 校验要求证据文件必须存在于 pinned revision**：首版候选引用了被 `.gitignore`（第 15 行 `/4_Reports/Reference`）忽略的文档 → validate 门报 `repository-evidence/file-missing`；改为引用**已提交**的 `spe_database_analysis.py` 后通过
- **本机无 Chrome/Chromium**：browser-check 被跳过（exit 2）→ 设置 `ARCHIFY_CHROME` 指向 Playwright 的 Chromium（`%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe`）后全部通过

### 验证
- `archify finalize` 四道门全部通过：validate / deliver / check / browser-check = pass，0 诊断
- `visual-check`：containment / readability / viewerChrome / themeStates / captures 均 pass；生成 4 张截图（1440×900、2048×1320 × 深浅），已人工目视复核：无标签重叠、无连线交叉、主路径为绿色加粗闭环

### 文件变更
- 新增: `.archify/architecture-spe-runtime-20260930-122446/`（candidate.json、spe-runtime.html、finalize / browser-check 回执、visual-check 截图 4 张）
- 修改: `Log.md`（本条目）

---

## v0.8 (2026-09-28)

**责任人**：蔡振辛

### 问题修复（v0.7 引入的"一进试次就崩溃"）
- **现象**：`Exp_Design_Formal` 跑到第一个试次的 `checkEscape()` 即报
  `错误使用 KbName / Key name "esc" not recognized`，整场实验在正式试次开始前退出。
- **根因**：v0.7 在文件开头加了一句 `KbName('UnifyKeyNames')`。本机 PTB 3.0.19 实测：
  开启"统一键名"后**小写 `'esc'` 立即变成无效键名**（只认 `'ESCAPE'`/`'escape'`），
  而本程序其余各处仍按未开启时的命名方案书写（`'esc'` / `'return'` / `'space'`）→ 第一个
  `checkEscape` 直接抛错。
- **同源印证**：这正是 `Exp_Design_Formal_v2.m` 当初"无法进入正式试次、txt 只有表头"的真正原因
  （v2 同样同时使用了 UnifyKeyNames + `KbName('esc')`），**与 KbQueue 无关**。
- **实测数据（本机 PTB 3.0.19，`matlab -batch`）**：

  | 键名 | 未开启 UnifyKeyNames | 开启后 |
  |---|---|---|
  | `'esc'` | 27 ✓ | **报错** |
  | `'ESCAPE'` | 报错 | 27 ✓ |
  | `'return'` / `'space'` / `'f'` / `'j'` | ✓ | ✓ |

  反向查询 `KbName(70)`→`'f'`、`KbName(74)`→`'j'` 在两种方案下完全一致，故 f/j 判定不受影响。

### 修复内容
- **撤销** `KbName('UnifyKeyNames')`，回到原版（即采集 88 人数据时）的命名方案；
  并在该位置留下醒目注释，防止以后再次加回。
- **加固** `checkEscape`：Esc 键码用 `persistent` 只解析一次，先试 `KbName('esc')`、
  失败再试 `KbName('ESCAPE')` —— 对两种命名方案都兼容，即使日后有人重新打开 UnifyKeyNames 也不会再整场崩溃。

### 验证
- `matlab -batch checkcode`：0 语法错误（仍为那 4 条既有无害告警）
- `matlab -batch` 实测修复后的键盘路径（无需开窗）：`KbName('esc')=27`、`KbCheck` 正常返回 256 长度
  `keyCode`、`checkEscape` 判定表达式求值成功、`KbName(70)='f'`、`KbName(74)='j'`、
  `KbName('return')=13`、`KbName('space')=32` → ALL_OK

### 另注（非阻塞，属环境问题）
- 该机运行时 PTB 报 `beamposition timestamping computed an impossible stimulus onset value`，
  随后 PTB **自动关闭高精度时间戳**、改用 VBL 时间戳（实测 164.87 Hz，接近系统报告的 165 Hz）；
  另有 DWM 合成器开启、Windows 11 不受支持、`libptbdrawtext_ftgl64.dll` 缺失（中文回落 GDI 渲染）等提示。
  本次均未导致中断。若需更稳的同步，可用 `ptb_switch_screen('light')`，或把
  `Screen('Preference','SkipSyncTests',0)` 改为 `1`（跳过同步自检，但同样会放宽时间精度保证）。

---

## v0.7 (2026-09-28)

**责任人**：蔡振辛

### 问题修复（正式采集程序 `Exp_Design_Formal.m`）
- **刺激呈现期/掩蔽期按键被整题丢弃**：旧版只在"掩蔽结束后的空白屏"里用 `KbCheck` 轮询，
  刺激呈现期(T)与掩蔽期(200 ms)按下的键根本不会被读取 → 表现为漏答或 RT 偏大。
  现改为在 **刺激期 / 掩蔽期 / 反应窗口** 三段全程轮询键盘，取最早的 f/j 按键作为反应。
- **W 口径错误**：旧版 deadline = `onset + T + W`，等价于"W 从刺激结束起算"。
  现修正为 **`deadline = stimulusFlipTime + W`**（W = 自刺激 onset 起算到最晚可反应时刻），
  RT 口径不变 = 按键时刻 − 刺激 onset。条件表数值按要求**保持不变**，故各组窗口绝对时长较旧版各短 T。
- **漏答被误记为错误**：旧版 `response` 初值为 `NaN`，而 `isempty(NaN)` 恒为 false，
  使漏答落到 `strcmp` 分支被记成 `Correct = 0`（错误）。现改用 `isnan(response)` 判断，
  漏答记为 `Correct = NaN`；`Response` 列仍沿用 `char(NaN)` 写法（CSV 中为缺失/NA），与旧数据一致。
- **`checkEscape` 缺陷**：按 Esc 时 `sca` 关屏后脚本仍继续执行，后续 `Screen` 调用接连崩溃；
  现补 `error()` 干净终止。
- **弃用 KbQueue**：`v2` 的 KbQueue 方案在本机运行时"无法进入正式试次"（数据文件只有表头）。
  本次回到原版的 `KbCheck` 轮询方案（最小改动、零外部依赖）。
  ~~顺手加 `KbName('UnifyKeyNames')` 统一键名~~ → **这一行是错的，已在 v0.8 撤销，它才是真正的崩溃源**。
- 新增启动自检：`W <= T + 200 ms` 时直接报错（当前 9 组均满足；**组 1 掩蔽后仅剩 70 ms 可按键**）。

### 功能完善
- `maskDuration` 由试次循环内的局部常量提到文件开头，供自检与练习/正式两段循环共用。

### 文件变更
- 修改: `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（外层唯一可运行程序）
- 归档: `Exp_Design_Formal_v2.m` → `test/Exp_Design_Formal_v2.m`；修改前的 v1 备份为 `test/Exp_Design_Formal_v1.m`
- 修改: `1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md` → v1.2（同步时间轴、W 口径、主试话术与核对清单）
- 待办: 手册 Word 版 `主试培训手册_Exp_Design_Formal.docx` 尚未同步，需人工重导

### 验证
- `matlab -batch checkcode` 通过：0 语法错误，仅 4 条既有无害告警（`isTestMode` 死分支 + 3 条预分配提示）
- 用本机 MATLAB 实测"漏答 → 表格赋值 → fprintf → writetable"全链路：
  初值若写成 `''`（0×0 char）会**直接报错**（表格元素宽度不符），故最终保留 `NaN` 初值 + `isnan` 判据
- 未做真机 PTB 运行验证（需显示器与 GStreamer 运行环境）

### 注意（数据可比性）
- 新口径下 RT 下限 ≈ 0（抢按被如实记录），而旧版数据 RT 下限恒为 `T + 200 ms`
  → **新旧数据在 RT 下限上不可直接混用**；若需对齐，分析时按 `RT < T+200ms` 剔除抢按。
- `Correct` 列：旧数据把漏答记成 `0`（上述 bug），新数据记为 `NaN`。若下游脚本按 `Correct` 直接算正确率，
  请注意旧数据需先按 `RT` 缺失剔除漏答（现有 `exp_Check` 审计脚本本就如此处理，不受影响）。

---

## v0.6 (2026-09-27)

**责任人**：蔡振辛

### 新增功能
- **三维地形响应面配图**：新增 `1_Code/Animation_Manim/make_terrain_figures.py`，一键生成 6 张 4K 静态配图
  - `01_主图_W600_纯地形.png` — W = 600 ms 截面的三维响应曲面（起伏 1.78）
  - `02_主图_W600_叠加σ透明度.png` — 同一地形叠加 σ 透明度调制
  - `03_对比_W800_现用截面.png` — 对照现有视频用截面（起伏仅 0.42）
  - `04_真实拟合ℓ0.22.png` — ℓ 取项目真实拟合值附近
  - `05_标注版_观测点与高不确定区.png` — 标注 G3/G4 观测点与高 σ 区域
  - `06_侧视角_起伏轮廓.png` — 低视角突出峰谷
- 输出目录：`3_Figures/Animation/terrain_figures/`

### 关键分析结论
- **现有 S6/S7 热力图"缺乏视觉冲击力"的根因是截面选错，不是画法问题**。实测各截面曲面起伏（μ 极差，基准：6 个观测值极差 = 0.97）：

  | 截面 | ℓ=0.22 | ℓ=0.45 | ℓ=1.20 | 观测点数 |
  |:---|:---:|:---:|:---:|:---:|
  | **W = 600**（G3 −0.22 / G4 +0.75） | 1.35 | **1.78** | 1.85 | 2 |
  | W = 800（G7 +0.44 / G8 +0.38） | 0.45 | 0.42 | 1.50 | 2 |
  | W = 1100 | 0.72 | 1.15 | 0.88 | 1 |
  | W = 1500 | 0.69 | 0.73 | 0.48 | 1 |
  | (T,W) @ P=120 | 1.39 | 2.28 | 2.19 | 4 |

  W = 800 只有两个同号观测点，曲面在数学上就不可能起伏。
- **不得靠调大 ℓ 制造起伏**：ℓ = 1.2~1.5 虽然起伏更大（1.85），但 σ 反而更低（0.85），属于"自信的外推"，与 S6 已建立的"6 个点撑不起三维空间"矛盾。
- **解法**：面片不透明度按 σ 调制，高 σ 区域淡出成幽灵——既有冲击力又不失真。

### 性能实测
- 三维曲面构造：**3.8 s / 个**（52×42 = 2184 面片）
- 动画逐帧渲染：480p15 与 1080p60 **均为 0.45 s/帧** → 瓶颈是三维投影/几何计算，与分辨率无关
- 推论：渲染时间只跟帧数走，1080p60 下 1 秒视频 ≈ 27 秒渲染；单曲面无法逐帧重建，W 滑动需预计算切片后 `Transform`

### 问题修复（Manim API）
- `ManimColor` 不支持按 hex 切片取值 → 改用 `ManimColor.to_rgb()`
- 三维坐标轴本身会被曲面遮挡 → 改用 `Line3D` 画外沿包围盒线框；刻度值写进底部图例，避免 3D 标签与图例碰撞

### 文件变更
- 新增: `1_Code/Animation_Manim/make_terrain_figures.py`
- 新增: `3_Figures/Animation/terrain_figures/`（6 张 4K PNG）
- 说明: 主视频暂未改动，等待确认后再决定是否并入

---

## v0.5 (2026-09-27)

**责任人**：蔡振辛

### 新增功能
- **动画演示补齐后 5 幕**，形成完整 9 幕成片 `GP_Demo_1080p60.mp4`（约 4 分 19 秒）
  - **S4 核函数 length_scale**：滑杆连续拖动 ℓ（0.25 → 2.0），后验曲线束与 ±2σ 带实时重算
  - **S5 升维到三维**：在三维设计空间中切出 W = 800 ms 的 (P, T) 截面，再"潜入"截面切换为二维视图
  - **S6 真实数据接入**：以 6 组真实 SPE_v 为观测值的响应面热力图 + 真实 LOCV 限制说明
  - **S7 从拟合到决策**：同一截面把底色换成 σ 不确定度雾，标出高不确定区与真实 Top 候选点（P=0, T=500, W=300）
  - **S8 收尾**：(P,T,W) → Sigmoid 先验 → GP 残差 → DDM 参数 → 行为数据的架构图

### 功能完善
- `common.py` 新增工具：PTW 归一化、多维 RBF 核 GP 回归、响应面热力图、σ 不确定度雾、matplotlib 等值线提取、色标、真实 LOCV 指标读取
- `build_video.py` 场景列表扩展为 9 幕
- S3 结尾调整：σ 插图与标注在结论出现前淡出，使 S2→S3→S4 连续拼接无跳变
- S5→S6、S6→S7 的画面状态精确对齐，已逐帧验证拼接处一致

### 问题修复（Manim API 适配）
- `ImageMobject` 的 `width` / `height` 属性是**等比缩放**，无法分别对齐两个方向 → 改用 `stretch_to_fit_width` / `stretch_to_fit_height`
- `ImageMobject` 不是 VMobject，**不能放入 `VGroup`** → 改用 `Group`
- `add_fixed_orientation_mobjects` **必须逐个对象传入**；传 VGroup 会以整体中心定向，导致文字错位与倾斜
- `csv.DictReader` 读出的值都是字符串，格式化前必须转 `float`
- 渲染被中断会留下损坏的分片缓存，导致后续 `InvalidDataError` → 清理 `partial_movie_files` 后恢复（已写入 `build_video.py` 文档字符串）
- 成片时序核对不能用 `av` 的 `seek()`（定位不准）→ 改为顺序解码定位

### 学术诚信说明（重要）
- S5–S7 的响应面是**教学示范**：为让画面可读，把 GP 直接建在 SPE_v 上并取 ℓ = 0.45；项目正式模型拟合的是 **Sigmoid 预测的残差**，ℓ 由边际似然优化到 0.16 ~ 1.78。此说明已写入 S4 页脚、S6 结论以及 S6/S7 右下角脚注
- S4 的 ℓ 取值范围取自 `step4_gp_sigmoid_model_canonical4.pkl`，S7 的候选点取自 `step6_candidate_design_points.csv`，S6 的 LOCV 指标取自 `canonical4_summary.json`——均为项目真实结果，动画中无硬编码

### 文件变更
- 新增: `1_Code/Animation_Manim/scenes/s4_kernel_length_scale.py`、`s5_higher_dimension.py`、`s6_response_surface.py`、`s7_decision.py`、`s8_closing.py`
- 修改: `1_Code/Animation_Manim/common.py`、`build_video.py`、`scenes/s3_gp_posterior.py`
- 更新: `3_Figures/Animation/GP_Demo_1080p60.mp4`、`3_Figures/Animation/GP_Demo_preview480p.mp4`
- 更新: `.trae/documents/manim_gp_animation_design.md`

---

## v0.4 (2026-09-27)

**责任人**：蔡振辛

### 新增功能
- **Manim 动画演示系统**：用 3Blue1Brown 风格的动画讲解高斯过程（GP）在本项目中的角色，面向组会汇报，让人直观理解"数据稀疏 → GP 用不确定性回答未知区域 → 不确定性指导下一轮实验"这条主线
- 新增 `1_Code/Animation_Manim/`：
  - `common.py` — 共享模块（配色、中文字体、真实数据加载、手写 RBF 核 GP 数学）
  - `scenes/s0_title.py` — S0 开场标题与核心问题
  - `scenes/s1_design_space.py` — S1 三维设计空间散点（6 个真实条件 + 未测量区域）
  - `scenes/s2_gp_prior.py` — S2 GP 先验（一族函数 + ±2σ 不确定带）
  - `scenes/s3_gp_posterior.py` — S3 条件化后验（曲线束收窄 + σ(x) 插图）
  - `build_video.py` — 一键「渲染 4 幕 + 拼接为单视频」，支持 `--quick` 出 480p 预览
- 输出视频：`3_Figures/Animation/GP_Demo_1080p60.mp4`（约 2 分钟）与 `GP_Demo_preview480p.mp4`
- 新增独立渲染环境 `.venv-manim`（Python 3.12 + Manim Community 0.21.0），与项目主环境 `.venv`（3.14）隔离

### 功能完善
- 动画中的 6 个观测点直接读取 `2_Data/Generate_Data/GP_Sigmoid_Canonical4/input_conditions_g3g8_canonical4.csv`，与主线分析口径一致（G3–G8，G1/G2 因遗漏率过高已排除）
- 新增设计文档 `.trae/documents/manim_gp_animation_design.md`：含 9 幕完整分镜（MVP 4 幕 + 后续 5 幕）、数据接入方式、风险规避、验收标准与实施偏差记录
- S2 与 S3 的画面状态精确对齐，两幕拼接处无跳变

### 问题修复（环境适配）
- **LaTeX 不可用**：本机 TeX Live 2025 缺 `standalone.cls`，导致 MathTex 编译失败。改为全部使用 `Text` + Unicode（μ、σ、→）渲染
- **无需安装 ffmpeg**：确认 Manim 0.21 内置 PyAV 编码器，不再依赖外部 ffmpeg 二进制
- **视频拼接**：逐帧重编码会因时间基不匹配报 EINVAL；改用 concat 分离器做流拷贝（Manim 内部同款方案），无损且更快
- **渲染缓存损坏**：中断渲染会留下不完整的分片缓存，导致后续 `InvalidDataError`。清理 `media/videos/*/1080p60/partial_movie_files` 后恢复

### 文件变更
- 新增: `1_Code/Animation_Manim/`（`common.py`、`manim.cfg`、`build_video.py`、`scenes/s0_title.py`、`scenes/s1_design_space.py`、`scenes/s2_gp_prior.py`、`scenes/s3_gp_posterior.py`）
- 新增: `3_Figures/Animation/GP_Demo_1080p60.mp4`、`3_Figures/Animation/GP_Demo_preview480p.mp4`
- 新增: `.trae/documents/manim_gp_animation_design.md`
- 修改: `.gitignore`（新增忽略 `.venv-manim/` 与 `Animation_Manim/media/`）

---

## v0.3 (2026-05-26)

### 问题修复
- **修复 Screen.mexw64 加载失败 (找不到指定的模块)**：
  - 根因：`LexActivator.dll`（Psychtoolbox 许可证管理 DLL）缺失。该 DLL 是 Screen.mexw64、WaitSecs.mexw64、GetSecs.mexw64 等所有 MEX 文件的静态导入依赖
  - 原因：用户使用的 `Psychtoolbox-3-master` 是 GitHub 开发者源代码仓库，不含 `LexActivator.dll` 商业组件
  - 下载了 LexActivator-Win.zip (v3.31.2) 并提取 `LexActivator.dll` (vc14/x64) 至项目目录
  - 更新 `setup_paths.m` 为完整自动化配置脚本（5步：确认目录→安装DLL→添加路径→配置运行时→保存路径）

### 功能完善
- `setup_paths.m` 现在自动处理 LexActivator.dll 的安装（优先本地复制，备选网络下载 `downloadlexactivator`）
- 脚本自动运行 `PsychStartup` 将 PsychPlugins 目录添加到系统 PATH，确保 MEX 文件能找到运行时 DLL

### 文件变更
- 修改: `1_Code/Experiment/exp_matlab/setup_paths.m`
- 新增: `1_Code/Experiment/exp_matlab/LexActivator.dll`

---

## v0.2 (2026-05-26)

### 新增功能
- 创建 `setup_paths.m` 环境配置脚本：一键将 Psychtoolbox-3 添加到 MATLAB 搜索路径并持久化保存

### 问题修复
- 确认 `Screen` 报错根因：MATLAB R2023b (E:\matlab2023b) 已安装，Psychtoolbox-3 已下载至 `D:\学习\Coding Learning\Matlab\Psychtoolbox-3-master\`，但未加入 MATLAB 搜索路径
- 确认 Psychtoolbox MEX 文件完整：Screen.mexw64、PsychHID.mexw64、GetSecs.mexw64、WaitSecs.mexw64 等均存在

### 功能完善
- 提供一键配置脚本 `setup_paths.m`，用户首次使用时运行一次即可永久配置环境

### 文件变更
- 新建: `1_Code/Experiment/exp_matlab/setup_paths.m`

---

## v0.1 (2026-05-26)

### 新增功能
- 创建 `EXP_NEW.m`，基于 `experiment_formal_newcon.m` 重命名并修复后的正式实验脚本

### 问题修复
- **Psychtoolbox 缺失检测**：脚本开头新增 `exist('Screen', 'file')` 检查，若 Psychtoolbox-3 未安装或不在 MATLAB 路径中，给出明确的中文错误提示和安装指引
- **checkEscape() 函数缺陷修复**：原函数调用 `sca` 关闭窗口后脚本仍继续执行，导致后续 `Screen()` 调用全部崩溃。修复后增加 `error()` 终止脚本，干净退出实验

### 功能完善
- 保留原 `experiment_formal_newcon.m` 的 9 组实验条件（conditions 1-9），支持 groupID 1-9

### 文件变更
- 新建: `1_Code/Experiment/exp_matlab/EXP_NEW.m`

---
