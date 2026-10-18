# -*- coding: utf-8 -*-
"""把 D100（LOO 不可引用是组层样本量问题）写进主计划四张表 + README + 使用说明。

每个锚点都断言「命中恰 1 次」，行数以实测为准（不再估算）。
用法：python -X utf8 1_Code/DDM_Core/_scratch/_apply_d100_docs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3]


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def write(p: Path, lines: list[str]) -> None:
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def replace_once(lines: list[str], anchor: str, new: list[str], *, at: int | None = None) -> list[str]:
    hits = [i for i, x in enumerate(lines) if anchor in x]
    assert len(hits) == 1, f"锚点命中 {len(hits)} 次：{anchor[:48]!r}"
    i = hits[0]
    return lines[:i] + new + lines[i + 1:]


def insert_after(lines: list[str], anchor: str, new: list[str]) -> list[str]:
    hits = [i for i, x in enumerate(lines) if anchor in x]
    assert len(hits) == 1, f"锚点命中 {len(hits)} 次：{anchor[:48]!r}"
    i = hits[0]
    return lines[:i + 1] + new + lines[i + 1:]


D100 = (
    "| **D100** | 2026-10-18 | ⚠️ **Pilot 规模（2 人/组）的组层 LOO 必然不可引用：原因是样本量，不是抽样配置**。"
    "① 探针（组 1、**1 人**、`n_em`=6、`n_draws`=25、`n_x`=41）⇒ M-T1 ELPD **−3660.142 ± 161.384**、"
    "`p_loo` **2839.686**（`n_obs` 555）、`k_max` **1.213**、Hessian **2/16 非正定**、`max|θ|` **100.782**；"
    "M-T3 **−5684.424 ± 227.353**、`p_loo` 4955.373、`k_max` 2.940、2/14、`max|θ|` 111.562 ⇒ 1/1 组 ⛔。"
    "② 对照 8 人 quick（`n_em`=3、`n_draws`=12）：4/4 组 ⛔，`p_loo`÷`n_obs` **0.009 / 2.156 / 3.221 / 2.330**、"
    "`n_flipped` **1/16、2/16、3/16、3/16**。③ 推论：把 `n_em`（3→6）与 `n_draws`（12→25）**都提上去仍红** ⇒ "
    "红的是**组层样本量**；可引用的 LOO 需要 Stage 7 的 ~40 人/组 + `--profile formal`。"
    "④ 落地：`run_pipeline.py` 新增 `MIN_N_HIER = 10` 与骨架横幅（点名「组层样本量」而不是配置），"
    "`check_run_pipeline.py` 加 **P6**（2 人/组出提示、12 人/组不出）⇒ **9/9**。"
    "⑤ 成本：quick（8 人）实测 **11594.3 s = 3.2 h**；formal（8 人）`--plan-only` **4.30 h**"
    "（层级 80.4 + LOO 176.3 + PPC 1.3 min），按 quick 估算低估 **3.08×** 外推实际约 **13 h**。"
    "⑥ Pilot 的角色因此明确为**验证机制**，不得用于模型比较结论 "
    "| `1_Code/Experiment/run_pipeline.py`（D100 增 `MIN_N_HIER` + 骨架样本量横幅）、"
    "`1_Code/Experiment/exp_Check/check_run_pipeline.py`（**9/9**，含 P6）、"
    "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_probe_health_out/`（探针证据） "
    "| 无（此条只约束「何时可以引 LOO 数字」；Stage 6/7 仍待真被试） |"
)

PROG = (
    "| 2026-10-18 | **D100（LOO 不可引用是样本量问题）** | "
    "用 1 人组探针（`n_em`=6、`n_draws`=25）推翻「加抽样就能救」的假设：`n_flipped` 2/16、"
    "`p_loo`÷`n_obs` 5.12、`k_max` 1.213、`max|θ|` 100.8 ⇒ 红的是组层样本量。"
    "落地 `MIN_N_HIER = 10` 横幅 + **P6** 自测（9/9），并测出 formal 配置 8 人 `--plan-only` = 4.30 h "
    "| `run_pipeline.py`、`check_run_pipeline.py`（9/9）、使用说明 §7 配置与成本表 "
    "| 看到「组层样本量不足」就知道要加人，别再调 `n_em`/`n_draws` |"
)

LOG = (
    "| 2026-10-18 | **新增 D100（Pilot 规模的 LOO 不可引用）**：1 人组探针（`n_em`=6、`n_draws`=25）"
    "仍是 `n_flipped` 2/16、`p_loo`÷`n_obs` 5.12、`k_max` 1.213、`max|θ|` 100.8 ⇒ "
    "红的是组层样本量而非抽样配置；`run_pipeline.py` 加 `MIN_N_HIER = 10` 与骨架横幅，"
    "`check_run_pipeline.py` 扩到 **9/9**（P6 钉死 2 人/组出提示、12 人/组不出）；"
    "并记入成本表：quick 8 人 3.2 h、formal 8 人 `--plan-only` 4.30 h（外推实际约 13 h） |"
)

EVID = (
    "| `1_Code/Experiment/run_pipeline.py`（D100 增 `MIN_N_HIER` + 骨架样本量横幅）、"
    "`1_Code/Experiment/exp_Check/check_run_pipeline.py`（**9/9**，含 P6）、"
    "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_probe_health_out/stage8_group_1.json`（1 人组探针："
    "`n_flipped` 2/16、`p_loo`÷`n_obs` 5.12、`k_max` 1.213、`max|θ|` 100.8）、"
    "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_stage8_out/`（8 人 quick：4/4 组 ⛔） | "
    "**D100**：判定「LOO 数字能不能引」时，先看人/组；2 人/组时任何抽样配置都红 |"
)


def patch_plan() -> None:
    p = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
    lines = read(p)
    lines = insert_after(lines, "| **D99** | 2026-10-18 |", [D100])
    lines = insert_after(lines, "| 2026-10-18 | **D98 复核（→ D99）**", [PROG])
    lines = insert_after(lines, "**新增 D99（LOO 闸门进流水线）**", [LOG])
    lines = insert_after(lines, "`1_Code/Experiment/run_pipeline.py`（D99 增 `assess_health`", [EVID])
    write(p, lines)
    print(f"主计划 -> {len(lines) - 1} 行")


def patch_readme() -> None:
    p = ROOT / "1_Code" / "DDM_Core" / "README.md"
    lines = read(p)
    sec = [
        "### 8.71 为什么 Pilot 规模的 LOO 一定不可引用（D100）",
        "",
        "**结论**：2 人/组的组层 LOO 健康闸门**必然红**，原因是**组层样本量**，不是 `n_em` / `n_draws`。",
        "",
        "| 配置 | 人/组 | `n_em` | `n_draws` | `p_loo`÷`n_obs` | `n_flipped` | `k_max` | `max|θ|` | 判词 |",
        "|---|---|---|---|---|---|---|---|---|",
        "| 探针（组 1） | **1** | 6 | 25 | **5.12** | **2/16** | 1.213 | 100.782 | ⛔ |",
        "| 探针（组 1）M-T3 | **1** | 6 | 25 | **8.93** | 2/14 | 2.940 | 111.562 | ⛔ |",
        "| 8 人 quick 组 1 | 2 | 3 | 12 | 0.009 | 1/16 | 0.000 | 71.9 | ⛔（只看 `p_loo` 会误判） |",
        "| 8 人 quick 组 2 | 2 | 3 | 12 | 2.156 | 2/16 | 0.000 | 71.1 | ⛔ |",
        "| 8 人 quick 组 3 | 2 | 3 | 12 | 3.221 | 3/16 | 0.000 | 68.0 | ⛔ |",
        "| 8 人 quick 组 4 | 2 | 3 | 12 | 2.330 | 3/16 | 0.000 | 72.1 | ⛔ |",
        "",
        "**为什么不是抽样配置**：探针把 `n_em` 从 3 提到 6、`n_draws` 从 12 提到 25（跨过 PSIS 的 25 门槛），"
        "判词一点没变好 —— `n_flipped` 仍是 2/16、`p_loo` 反而更离谱（2839.686 对 `n_obs` 555）、"
        "`max|θ|` 冲到 100.8（`stage8_health.MAXABS_WARN = 20`，D75 实测正定 ≤ 7.3）。"
        "组层回归要估 `beta_P`（4 个 P 水平），2 人/组时该回归欠定，超参数 Hessian 自然非正定。",
        "",
        "**落地**：`run_pipeline.py` 的 `MIN_N_HIER = 10` + 骨架 §2 横幅"
        "「⚠️ **组层样本量不足**：最少 N 人/组 < 10（D100）……」；"
        "`exp_Check/check_run_pipeline.py` 的 **P6** 钉死「2 人/组出提示、12 人/组不出」（现 **9/9**）。",
        "",
        "**成本（实测/估算分开写）**：quick（8 人、`n_em`=3、`n_draws`=12、`n_x`=21、PPC 1）**实测 11594.3 s = 3.2 h**；"
        "`--plan-only` 当时估 1.04 h ⇒ 估算低估 **3.08×**。formal（8 人、`n_em`=12、`n_draws`=50、`n_x`=81、PPC 10）"
        "`--plan-only` 给 **4.30 h**（层级 80.4 + LOO 176.3 + PPC 1.3 min）⇒ 按 3.08× 外推实际约 **13 h**。",
        "",
        "**纪律**：Pilot（N≈8）只验证**机制**；可引用的 LOO / 模型比较要等 Stage 7 的 ~40 人/组 + `--profile formal`。",
        "",
    ]
    lines = replace_once(lines, "## 9. 尚未做", sec + ["## 9. 尚未做"])
    item = ("| 83 | ❌ **未做**：`--profile formal` 的**实测**耗时（现只有 `--plan-only` 的 4.30 h 估算）；"
            "2 人/组的红是样本量（D100），但「要多少人/组才转绿」**未做扫描**（现只有 1 人与 2 人的两点证据），"
            "40 人/组的拟合也没有真跑过。 |")
    lines = insert_after(lines, "| 82 |", [item])
    write(p, lines)
    print(f"README -> {len(lines) - 1} 行")


def patch_usage() -> None:
    p = ROOT / "5_Reference" / "08_工作流" / "全流程一键跑通_使用说明.md"
    lines = read(p)
    sec = [
        "## 7. 配置与成本（实测与估算分开写）",
        "",
        "| 配置 | `n_em` | `n_draws` | `n_x` | PPC | 8 人一次跑 | 来源 |",
        "|---|---|---|---|---|---|---|",
        "| `--profile quick` | 3 | 12 | 21 | 1 | **3.2 h**（11594.3 s） | 实测 |",
        "| `--profile formal` | 12 | 50 | 81 | 10 | **4.30 h 估算 ⇒ 实际约 13 h** | `--plan-only` + quick 的 3.08× 低估比例 |",
        "",
        "> ⚠️ **quick 的数值一律不作结论**：2 人/组时组层 LOO 健康闸门**必然红**（D100 实测：1 人/组即使把 "
        "`n_em` 提到 6、`n_draws` 提到 25，仍是 `n_flipped` 2/16、`p_loo`÷`n_obs` 5.12、`max|θ|` 100.8）。"
        "所以要出可引用的模型比较，**要同时加人（~40 人/组）与换 formal**；只调抽样参数救不回来。",
        "",
        "看报告时的顺序：`pipeline_report.md` 的 3.5 行 → 若「组层样本量不足」出现，先解决人，"
        "再谈 `n_em`/`n_draws`；当 4 组全 ⛔ 时，`results_skeleton.md` §2 与 `fig3` 只能当流程验证。",
        "",
    ]
    lines = lines + sec if lines and lines[-1] == "" else lines + [""] + sec
    write(p, lines)
    print(f"使用说明 -> {len(lines) - 1} 行")


if __name__ == "__main__":
    patch_plan()
    patch_readme()
    patch_usage()
