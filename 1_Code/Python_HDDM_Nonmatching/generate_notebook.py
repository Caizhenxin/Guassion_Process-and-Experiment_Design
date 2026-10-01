r"""生成 Docker_Run_Nonmatching.ipynb（只做导航，不再复制 step1/2/3 的代码）。

2026-09-30 重写
==============
旧版本把 step1/step2/step3 的代码**整份复制**进 notebook cell，结果四处代码各自漂移：
`depends_on={"v":"identity"}` 与"遗漏 = 1 − Correct"这两个错误在脚本和 notebook 里各存一份，
且其中一段缩进已经坏掉（会生成语法错误的 cell）。

改为：notebook 只负责**调用脚本**，脚本是唯一事实来源。
"""
import sys
from pathlib import Path

import nbformat as nbf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
OUT = HERE / "Docker_Run_Nonmatching.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}

cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s))


def code(s):
    cells.append(nbf.v4.new_code_cell(s))


md("""# Docker HDDM 参数拟合工作流 — NonMatching 版本

**项目**：GP-SPE 实验设计优化 — Self-Matching Task DDM 参数提取（Matching + NonMatching 全试次）

> ⚠️ **2026-09-30 修订**：本 notebook 不再内嵌代码，改为调用同目录下的三个脚本。
> 脚本是唯一事实来源，避免多处副本漂移。

## 本次修订修掉了两个阻断级问题

| # | 问题 | 旧行为 | 新行为 |
|---|---|---|---|
| 1 | **模型设定与数据不相容** | `depends_on={"v":"identity"}`：匹配与不匹配共用同一个 `v`，其硬性推论是 `P(正确\\|匹配)+P(正确\\|不匹配) ≡ 1`，而实测为 **1.458** | 提供 M0–M3 规格阶梯，默认 **M3**（正确性编码 + `v` 按身份 + `z` 按 cell） |
| 2 | **遗漏被伪造** | 遗漏试次 `rt = deadline`、`response = 1 − Correct`（恒为"错误"）；group3 有 38.0% 的试次被这样伪造 | 遗漏的 `rt`/`response` 一律留空，只由 `omission` 标记；另存 omissions 文件供后续 omission-aware 似然使用 |

依据：`5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md`

---

## Docker 启动方式

```bash
docker pull hcp4715/hddm

docker run -it --rm --cpus=4 ^
  -v /d/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work ^
  -p 8888:8888 ^
  hcp4715/hddm ^
  jupyter notebook
```

> 挂载路径是**项目根目录**，脚本会自行由文件位置推算 `BASE_DIR`，无需改任何路径。

---

## 工作流

| 步骤 | 内容 | 预估 |
|---|---|---|
| Step 1 | 数据预处理 → HDDM 就绪 CSV（含按键映射自检） | 秒级 |
| Step 2 | HDDM 层级 MCMC 拟合（默认 M3，8 组） | 25–60 分钟 |
| Step 3 | 参数提取 + 派生量 Δv / b / Δb + 绘图 | 秒级 |

> Step 1 与 Step 3 也可以直接在**本机**用 `python` 跑；Step 2 必须在容器内。
""")

md("""---
## Step 1：数据预处理

- 过滤 `stage='formal'`
- 按「设计规则」推导 Matching/NonMatching，并与「记录值」逐行比对（**按键映射自检**）
- 遗漏试次不再伪造反应方向：`rt` / `response` / `correct` 留空

**输出**
- `HDDM_Ready_Nonmatching/hddm_data_group*.csv`：有反应试次（Drop 口径，HDDM 直接可用）
- `HDDM_Ready_Nonmatching/hddm_omission_group*.csv`：遗漏试次（供 omission-aware 阶段）
""")
code("""%run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step1_prepare_data.py""")

md("""---
## Step 2：HDDM 层级模型拟合

### 模型规格阶梯（`--model`）

| 规格 | response 编码 | depends_on | 说明 |
|---|---|---|---|
| `M0` | 按键 | `v: identity` | 旧设定，**已证明与数据不相容**，仅用于复现 |
| `M1` | 按键 | `v: cell` | 四格漂移，能拟合但解释性差 |
| `M2` | **正确性** | `v: identity`, `z: condition` | 起点按条件；不含身份差异 |
| `M3` | **正确性** | `v: identity`, `z: cell` | **默认主模型** |

### 为什么 M2/M3 才对

`response` 改为正确性编码后，上界 = "正确"边界，于是

- `v` = 朝正确方向积累证据的速率 → **漂移方向随刺激自动翻转**，两个正确率不再互补（1.458 才能被解释）
- `z` 仍是**按键**偏向：在"正确界"坐标下，一份恒定的匹配键偏向 b 表现为
  匹配试次 `z = 0.5 + b`，不匹配试次 `z = 0.5 − b`
  → `b = (z_匹配 − z_不匹配)/2`，再让 `z` 依 `cell` 变化就得到 **Δb**（SPE 的偏向成分）

派生量在 Step 3 自动计算：`Δv = v_self − v_stranger`、`b_i = (z(匹配,i) − z(不匹配,i))/2`、`Δb = b_self − b_stranger`。
""")
code("""# 主模型（推荐）
%run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M3

# 复现旧设定（被否证，仅存档用）：
# %run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M0

# 一次跑完 M0–M3 做模型比较（耗时 ×4）：
# %run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model all

# 只跑某几组做冒烟测试：
# %run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M3 --groups 3 --draws 300 --burn 100""")

md("""---
## Step 3：参数提取与派生量

读取 `model_spec.json` 判断每个结果用的是哪个规格，逐 draws 计算
`Δv`、`b_self`、`b_stranger`、`Δb`（因此带正确的不确定度），并绘图。

此步骤**建议在本机运行** `python step3_extract_params.py`，避免容器内缺中文字体。
""")
code("""%run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step3_extract_params.py""")

md("""---
## 输出文件

| 文件 | 位置 | 内容 |
|---|---|---|
| `hddm_data_group*.csv` | `2_Data/Real_Data/HDDM_Ready_Nonmatching/` | 有反应试次（Drop 口径） |
| `hddm_omission_group*.csv` | `2_Data/Real_Data/HDDM_Ready_Nonmatching/` | 遗漏试次（供 omission-aware 阶段） |
| `model{M}_{组号}_stats.csv` | `2_Data/Real_Data/HDDM_Traces_Nonmatching/` | 后验摘要 |
| `model{M}_{组号}_traces.npz / .pkl` | `2_Data/Real_Data/HDDM_Traces_Nonmatching/` | 完整迹线 |
| `model_spec.json` | `2_Data/Real_Data/HDDM_Traces_Nonmatching/` | 每组用了哪个规格（Step 3 依赖） |
| `all_groups_ddm_params.csv` | `2_Data/Real_Data/HDDM_Traces_Nonmatching/` | 汇总（含 Δv / b / Δb） |
| `ddm_params_{M}.png` | `3_Figures/HDDM_Results_Nonmatching/` | 参数图 |

---

## 编码说明

```
response（按键编码，供 M0/M1）: 1 = 判断为 Matching（上界）, 0 = 判断为 NonMatching（下界）
correct （正确性编码，供 M2/M3）: 1 = 作答正确, 0 = 作答错误
condition: 1 = Matching 试次, 0 = NonMatching 试次
cell     : identity * 2 + condition  → 0..3
deadline : T + W（秒，自刺激起点计）
```

⚠️ 遗漏试次**不赋予任何反应方向**。忽略遗漏本身就有偏（Leng et al., 2025），
伪造方向则是在反向注入偏差。完整的遗漏似然方案见规格文档 §4 的四阶段路线。
""")

nb["cells"] = cells
nbf.write(nb, str(OUT))
print(f"已生成: {OUT}")
print(f"cells: {len(cells)}")
