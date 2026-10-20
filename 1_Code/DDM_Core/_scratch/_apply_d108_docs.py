# -*- coding: utf-8 -*-
"""② 扫描收尾落纸：N=4 BAD(1/16 flipped) / N=8 OK(0/16) ⇒ 8 人/组是可辨识下限。"""
from pathlib import Path

ROOT = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
RD = ROOT / "1_Code/DDM_Core/README.md"


def ncol(line):
    return line.count("|") - 1


def rows_of(line, cells):
    k = ncol(line)
    cells = list(cells)[:k]
    while len(cells) < k:
        cells.append("—")
    return "| " + " | ".join(cells) + " |"


# ------------------------------------------------------------------ 主计划
s = MP.read_text(encoding="utf-8")
L = s.split("\n")
d107 = next(i for i, x in enumerate(L) if x.startswith("| **D107** |"))
p10 = next(i for i, x in enumerate(L) if x.startswith("| 2026-10-20 | **10（③ 设计空间优化 → D107）**"))
lg = next(i for i, x in enumerate(L) if x.startswith("| 2026-10-20 | **新增 D106（峰谷闸门）+ D107"))

D108 = rows_of(L[d107], [
    "**D108**", "2026-10-21",
    "**层级模型的样本量下限 = 8 人/组（4 人/组不够）**。后台扫描（`scan_min_n.py --n-list 4 8 --group 1 --reuse`，"
    "合成数据、quick 配置、analytic 超参数、trial 级 LOO）跑完：**N=4 ⇒ BAD**（`n_flipped` = 1/16，`max_abs_theta` = 61.2，"
    "107.3 min）；**N=8 ⇒ OK**（`n_flipped` = 0/16，`max_abs_theta` = 4.0，153.2 min）。",
    "D100 的机制更正（组层超参数维数 2K=16 vs 被试数）预测「人太少会把 Hessian 顶翻」，这次实测把「太少」定量成 4；"
    "D102 的 N=4/8 扫描中途丢过一次作业，这轮补跑才拿到结果",
    "`2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md` / `scan_min_n.json` / `n4`、`n8` 输出树",
    "只测了组 1、quick 配置、每个 N 只跑 1 次 ⇒ 「8」是粗估下限，不是精确阈值；N=6 未测",
])

prog = rows_of(L[p10], [
    "2026-10-21",
    "**10（② 样本量扫描 → D108）**",
    "**跑完并定论**：N=4 BAD、N=8 OK ⇒ 层级可辨识下限 8 人/组；4 人/组的失败点是超参数 Hessian 非正定（1/16 翻转）。"
    "未做：N=6 中间档、多组重复、把「8 人/组」写进招募与样本量论证。",
    "`2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md`（含两档耗时 107.3 / 153.2 min）",
])

log = rows_of(L[lg], [
    "2026-10-21",
    "**新增 D108（8 人/组是可辨识下限）**：`scan_min_n.py` 补跑 N=4/8 两档，N=4 ⇒ BAD（`n_flipped` 1/16、"
    "`max_abs_theta` 61.2）、N=8 ⇒ OK（0/16、4.0）；两档各耗 107.3 / 153.2 min，报告 `_SYNTHETIC_SCAN/scan_min_n.md`。",
    "`2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md` / `scan_min_n.json`",
])

for off, new in ((lg, log), (p10, prog), (d107, D108)):
    L.insert(off + 1, new)

anchor = next(i for i, x in enumerate(L)
              if x.startswith("| `1_Code/Experiment/design_search.py`（**新建**，D107"))
L.insert(anchor + 1, rows_of(L[anchor], [
    "`1_Code/Experiment/scan_min_n.py`（D102）+ `2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md`（**新**，D108）",
    "② 的补跑：N=4 vs 8 两档，判词取 `stage8_health.assess_group`",
    "✅ N=4 BAD（`n_flipped` 1/16、`max_abs_theta` 61.2、107.3 min）、N=8 OK（0/16、4.0、153.2 min）"
    "⇒ 层级可辨识下限 8 人/组；未做 N=6 与多组重复",
]))
MP.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("主计划", len(L))

# ------------------------------------------------------------------ README
r = RD.read_text(encoding="utf-8")
R = r.split("\n")
i85 = next(i for i, x in enumerate(R) if x.startswith("| 85 |"))
R[i85] = ("| 85 | ✅ **样本量下限（D108）** | `2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md`：**N=4 ⇒ BAD**"
          "（`n_flipped` 1/16、`max_abs_theta` 61.2、107.3 min）、**N=8 ⇒ OK**（0/16、4.0、153.2 min）"
          "⇒ 层级模型可辨识下限 **8 人/组**；**未做**：N=6 中间档、多组重复、把结论写进招募与样本量论证 |")
sec = next(i for i, x in enumerate(R) if x.startswith("## 9. 尚未做"))
block = [
    "## 8.77 ② 的可辨识下限：4 人/组不够，8 人/组合格（D108）",
    "",
    "**一句话**：组层超参数 Hessian 在 N=4 时被顶翻 1/16，N=8 时全绿 ⇒ 「最少多少人/组」这条问句有了合成数据上的答案。",
    "",
    "### 跑法",
    "",
    "`1_Code/Experiment/scan_min_n.py --n-list 4 8 --group 1 --root 2_Data/Real_Data/_SYNTHETIC_SCAN --reuse`，"
    "数据由 `_make_ddm_pilot.py` 合成（组 1，`--anticipation 0.03`），"
    "stage8 用 quick 配置（`n_em`=3、`n_draws`=12、`n_x`=21、PPC=1）、`--hyper-method analytic`、`--loo-level trial`，"
    "判词取 `stage8_health.assess_group`。",
    "",
    "### 结果",
    "",
    "| N（人/组） | 判词 | `n_flipped` | `p_loo`÷`n_obs` | `max_abs_theta` | 拟合耗时 |",
    "|---|---|---|---|---|---|",
    "| 4 | **BAD** | 1/16 | 0.001 | 61.2 | 107.3 min |",
    "| 8 | **OK** | 0/16 | 0.001 | 4.0 | 153.2 min |",
    "",
    "### 怎么读",
    "",
    "* 失败点不是 LOO（两档 `p_loo`÷`n_obs` 都是 0.001），而是**超参数 Hessian 非正定**——这正是 D100 更正后的机制："
    "组层超参数维数 `2K = 16`（每个被试层参数两头算），被试数 N=4 时 16 个约束悬在 4 个人身上，"
    "`n_flipped` 就是「翻转的超参数个数」。",
    "* `max_abs_theta` 从 61.2 掉到 4.0，说明 4 人组的不只是不显著，而是**数值上已经跑飞**。",
    "* 代价要写进论文：quick 配置下 8 人/组也要 **2.5 小时**拟合；正式配置（`n_em`/`n_draws` 提高）会更慢，"
    "所以「40 人/组」的拟合成本必须提前估。",
    "",
    "### 边界",
    "",
    "* 只测了**组 1**、每个 N 只跑 **1 次**、`N=6` 没测 ⇒ 「8」是粗估下限，不是精确阈值。",
    "* 「可辨识下限 8」与「识别力需要 37–41 人/组」（D105/D107）是**两件事**：前者是拟合能不能收敛，后者是效应能不能估准。",
    "",
]
R[sec:sec] = block
RD.write_text("\n".join(R), encoding="utf-8", newline="\n")
print("README", len(R))
