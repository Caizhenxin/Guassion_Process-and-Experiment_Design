# -*- coding: utf-8 -*-
"""D105 落纸：论文级模拟图（CRLB / P 方案 oracle / 试次级生成数据）+ 三处口径落差。

一次改三份文档，每个锚点断言「命中恰 1 次」，并核对表格列数（cells = line.count('|') - 1）。
"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MASTER = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
STAGE9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"

DECISION = (
    "| **D105** | 2026-10-18 | **把「没有真实数据时能写进论文的东西」做成三张模拟图 + 一条口径纪律**。"
    "① 新工具 `1_Code/Experiment/make_sim_figures.py`（462 行）一次产出三图：`fig_sim_crlb.png`"
    "（CRLB：9 个被试层参数「组层 SE / 真值」随组人数变化，标 10% 与 25% 两条参考线）、"
    "`fig_sim_p_design.png`（oracle 识别力：三种 P 方案的 `beta_P` / `tau_P` 相对 RMSE 与判据线）、"
    "`fig_sim_trials.png`（模型生成的试次级数据：RT 分位数、RT 密度、正确率/遗漏率随 T）；"
    "另出 `figures_index.md` 与 4 份 CSV/JSON。"
    "② 关键数字（实算）：**`d_ref` 10% 需 N=3、`beta_T` 需 41、`beta_S` 需 51、`tau_T` 需 169、"
    "`delta_a` 需 658、`tau_a` 需 1307、`beta_ST` 需 2248、`a_ref` / `t0` 需 1**；"
    "oracle 下 `beta_P` 在 n=12 时 0.243、n=20 时 0.150（判据 0.30），`tau_P` 在 n=20 时 0.513（判据 0.50）"
    "⇒ **40 人/组稳、20 人/组是下限**；`beta_ST` 要 2248 人 ⇒ 与「降级为探索性」的决定互相印证。"
    "③ **抓出三处口径落差**：CRLB 用 `design_fim.TRUTH`（exp 形式）、试次图用 `design_grid.TRUTH_LIN`、"
    "合成数据集用 `_make_ddm_pilot.QC_TRUTH`（lin，`beta_T = 0.45`，T 的漂移跨度只有 0.098，"
    "比设计前提弱 3–4 倍 ⇒ 恢复验证偏保守）；且设计真值下 **P=0 组漂移≈0.0005 ⇒ 期望正确率 0.50，"
    "与 S6-5 的 0.45 下限不相容**（首场真实数据 0.440 正落在这一位置）、设计真值遗漏率 0.32–0.35 "
    "高于 S6-1 的 20% ⇒ 两条采集判据须与设计真值一起复核。"
    "④ 顺带修掉 `oracle_power.py` 与 `recover_group.fit_between` 返回值（三元组）不符的 bug —— "
    "该脚本此前跑不起来。 | "
    "`1_Code/Experiment/make_sim_figures.py`（**新建**，462 行）+ `5_Reference/03_论文写作/figures_sim/`"
    "（三图 + `figures_index.md` + `sim_crlb.csv` / `sim_oracle.csv` / `sim_trials_conditions.csv` / "
    "`sim_trials_truth.json`）+ `1_Code/DDM_Core/oracle_power.py`（**修 bug**，126 行） | "
    "无（模拟图不需要真实数据；但 ③ 的两条判据冲突须与 Stage 9 一起裁定） |"
)

PROGRESS = (
    "| 2026-10-18 | **9（论文级模拟图 → D105）** | **把「没有数据时能写出什么」变成三张图**："
    "CRLB 说清「多少人/组才把参数压到 10%」（`d_ref` 3、`beta_T` 41、`beta_ST` 2248），"
    "oracle 说清 P 方案（40 人/组稳、20 人/组下限），试次图说清「模型能生成什么」；"
    "同时抓出合成数据真值比设计前提弱 3–4 倍、S6-5 下限与设计真值不相容两处口径落差 | "
    "`make_sim_figures.py` + `figures_sim/` | 无 |"
)

CHANGELOG = (
    "| 2026-10-18 | **新增 D105（论文级模拟图）**：`make_sim_figures.py`（462 行）出三图 + 索引 + 4 份 CSV/JSON；"
    "CRLB 给出「10% 精度所需组人数」（`d_ref` 3 / `beta_T` 41 / `beta_ST` 2248），oracle 给出 P 方案识别力"
    "（40 人/组稳、20 人/组下限）；抓出三处真值口径落差与两条判据冲突（S6-5 下限 0.45 vs 设计真值 0.50、"
    "S6-1 20% vs 设计遗漏 32–35%）；修 `oracle_power.py` 与 `fit_between` 三元组不符的 bug |"
)

EVIDENCE = (
    "| `1_Code/Experiment/make_sim_figures.py`（**新建**，D105，462 行）+ `5_Reference/03_论文写作/figures_sim/"
    "`（`fig_sim_crlb.png` / `fig_sim_p_design.png` / `fig_sim_trials.png` / `figures_index.md` / "
    "`sim_crlb.csv` / `sim_oracle.csv` / `sim_trials_conditions.csv` / `sim_trials_truth.json`） | "
    "D105 证据：三张图都不含任何真实被试数据，按 D104 纪律一只能进方法章 / 识别性与功效章；"
    "`fig_sim_trials.png` 已改为 3 名被试合并（单人会话只有 576 试次 ⇒ 分单元噪声太大） |"
)

README_SEC = """### 8.75 论文级模拟图（D105）

没有真实数据时，能进论文的图只有一种：**由模型假设生成的模拟图**。`1_Code/Experiment/make_sim_figures.py`
（462 行）一次产出三张 + 索引，全部落在 `5_Reference/03_论文写作/figures_sim/`。

| 图 | 回答什么 | 关键读数 |
|---|---|---|
| `fig_sim_crlb.png` | 每组要多少人才能把参数压到 10% | `d_ref` **3**、`beta_T` **41**、`beta_S` **51**、`tau_T` **169**、`delta_a` **658**、`tau_a` **1307**、`beta_ST` **2248**、`a_ref` / `t0` **1** |
| `fig_sim_p_design.png` | P 水平怎么选 | `beta_P` 判据 0.30：n=12 时 0.243、n=20 时 0.150；`tau_P` 判据 0.50：n=20 时 0.513 ⇒ 40 人/组稳、20 人/组下限 |
| `fig_sim_trials.png` | 模型能生成什么样的试次数据 | 正确率随 T 从 0.58 升到 0.75、遗漏率随 W 从 0.56 降到 0.20（3 名被试合并） |

三处真值口径必须分清（`figures_index.md` 里也写了）：

* CRLB 图用 `design_fim.TRUTH`（**exp** 形式，`beta_P = 1.5`、`P_ref = 120`）；
* 试次图用 `design_grid.TRUTH_LIN`（同一设计前提的线性近似，`mapping.match_lin_to_exp` 残差 0.045）；
* 合成数据集 `_SYNTHETIC_DEMO_v1` 用 `_make_ddm_pilot.QC_TRUTH`（**lin**，`beta_T = 0.45`）⇒ T 的漂移跨度只有 0.098，比设计前提弱 3–4 倍，**恢复验证因此偏保守**。

两条已发现的判据冲突（未决，须与 Stage 9 一起裁定）：设计真值在 P=0 组的漂移≈0.0005 ⇒
期望正确率 0.50，而 S6-5 的下限是 0.45（首场真实数据 0.440 正落在这一位置）；设计真值的遗漏率
0.32–0.35 高于 S6-1 的 20%。⇒ **先把「设计真值」与「验收判据」对齐，再谈 Pilot 是否达标**。

自坑一条：`oracle_power.py` 此前跑不起来——`fit, _ = fit_between(...)` 与现在的三元组返回值不符，
`ValueError` 被当成「工具没写好」。修成 `fit, _rms, _wrms = fit_between(...)`。
"""

README_ITEM = (
    "| 87 | ✅ **论文级模拟图（D105）** | `1_Code/Experiment/make_sim_figures.py`（462 行）+ "
    "`5_Reference/03_论文写作/figures_sim/`（三图 + 索引 + 4 份 CSV/JSON）；**未做**：把这套图接进 "
    "`run_pipeline.py`（它们是「无数据」产物，不属于流水线）、未做 P 方案的完整设计空间搜索（Stage 9） |"
)

STAGE9_ROW = (
    "| `1_Code/Experiment/make_sim_figures.py` | 论文级模拟图：CRLB（10% 精度所需组人数）、"
    "P 方案 oracle 识别力、试次级生成数据 | ✅ **已建**（462 行、裸 LF）。证据：三图 + `figures_index.md` + "
    "4 份 CSV/JSON 全部生成（`python -X utf8 1_Code/Experiment/make_sim_figures.py` 退出 0，~2 min）；"
    "数字见主计划 D105 |"
)

STAGE9_LOG = (
    "| 2026-10-18 | **论文级模拟图落成（决策 D105）**：`make_sim_figures.py` 出 CRLB（`d_ref` 3 / "
    "`beta_T` 41 / `beta_ST` 2248 人才能到 10%）、P 方案 oracle（40 人/组稳、20 人/组下限）、试次生成图；"
    "顺带修 `oracle_power.py` 与 `fit_between` 三元组不符的 bug |"
)


def cells(line: str) -> int:
    return line.count("|") - 1


def patch(path: Path, edits) -> int:
    lines = path.read_text(encoding="utf-8").split("\n")
    for kind, anchor, new in edits:
        idx = [i for i, ln in enumerate(lines) if anchor in ln]
        assert len(idx) == 1, (path.name, anchor, len(idx))
        i = idx[0]
        if kind == "after":
            want = new.count("|") - 1
            got = cells(lines[i])
            assert want == got, (path.name, anchor, "new", want, "anchor", got, lines[i][:80])
            lines.insert(i + 1, new)
        else:
            raise AssertionError(kind)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return len(lines)


n1 = patch(MASTER, [
    ("after", "| **D104** | 2026-10-18 |", DECISION),
    ("after", "**9（证据阶梯落纸 → D104）**", PROGRESS),
    ("after", "**新增 D101（结果章模板 + 自动填表）**", CHANGELOG),
])
# 证据行在文件末尾（表格最后一行），单独 append
m = MASTER.read_text(encoding="utf-8").rstrip("\n")
assert cells(m.split("\n")[-1]) == cells(EVIDENCE), (cells(m.split("\n")[-1]), cells(EVIDENCE))
MASTER.write_text(m + "\n" + EVIDENCE + "\n", encoding="utf-8", newline="\n")
print("主计划", n1, "->", len(MASTER.read_text(encoding='utf-8').split('\n')))

# README：§8.75 插在 `## 9. 尚未做` 前，§9 第 87 项插在 item 86 后
s = README.read_text(encoding="utf-8")
assert s.count("## 9. 尚未做") == 1
s = s.replace("## 9. 尚未做", README_SEC + "\n## 9. 尚未做")
lines = s.split("\n")
i86 = [i for i, ln in enumerate(lines) if ln.startswith("| 86 |")]
assert len(i86) == 1
assert cells(lines[i86[0]]) == cells(README_ITEM), (cells(lines[i86[0]]), cells(README_ITEM))
lines.insert(i86[0] + 1, README_ITEM)
README.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("README", len(lines))

n3 = patch(STAGE9, [
    ("after", "`1_Code/AutoRA_SPE/check_stage9_inner.py`", STAGE9_ROW),
    ("after", "**共享流 CRN 配对：实测后不升格（决策 D69）**", STAGE9_LOG),
])
print("Stage9", n3)
