"""D115：图文数据三分 + 文件结构待办 + λ 天花板敏感性分析。

列数一律「跟锚点行自动对齐」，不再手写期望值（这是本项目反复踩的坑）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"


def insert_after(lines: list[str], anchor_sub: str, new_line: str) -> list[str]:
    """在含 anchor_sub 的最后一行之后插入；列数自动对齐锚点行。"""
    idx = [i for i, ln in enumerate(lines) if anchor_sub in ln]
    assert idx, f"锚点未找到：{anchor_sub}"
    i = idx[-1]
    want = lines[i].count("|")
    got = new_line.count("|")
    assert got == want, f"列数不符（锚点 {want} 个竖线，新行 {got} 个）：{new_line[:60]}"
    lines.insert(i + 1, new_line)
    return lines


DECISION = (
    "| **D115** | 2026-10-24 | **图文数据三分 + λ 天花板机制敏感性分析**。① 目录口径改为「`1_Code` 只放代码、"
    "所有图进 `3_Figures`、数据只在 `2_Data/{Generate_Data,Real_Data}`」：生成图 `2_Data/Generate_Data/M-T{1,2,3}/figures/*.png` "
    "→ `3_Figures/M-T{1,2,3}/`，对照图 → `3_Figures/_compare/`，论文级模拟图 `5_Reference/03_论文写作/figures_sim/*.png` "
    "→ `3_Figures/figures_sim/`；合成数据 `2_Data/Real_Data/_SYNTHETIC_{DEMO_v1,NOTEBOOK,SCAN}` → "
    "`2_Data/Generate_Data/_synth_datasets/`；代码侧新增 `FIG_ROOT`/`--figroot`（`gen_viz.py`）、`FIG_OUT`（`spe_locus.py`）、"
    "`--figout`（`make_sim_figures.py`）、`scan_min_n.py` 默认根改 `_synth_datasets/`。`1_Code/DDM_Core/_scratch/` **本轮不动**"
    "（完整工作流还在跑，里面是活探针），改为登记在 `5_Reference/08_工作流/文件结构整理_待办.md` 的 8 条清单里，收尾时统一梳理。"
    "② λ 天花板机制（用户提出、SPE_Database 2026-09-29 报告已给解析判据）在本项目加法口径下重算："
    "`v_self − v_other = Δ_S·[1 − (1−λ)·f_P]`，λ=1 等价现行 `β_SP=0`。模拟（15 人 × 288 试次/格）结论：**λ=1 时 SPE_RT 随练习"
    "上升（+20.5 → +31.5 → +27.6 ms），与 HuYQ Exp3 实测方向（LMM −3.30 ms/阶段，p=.00029）相反；λ=0 时衰减到 +0.3 ms，"
    "λ=0.5 时 +15.1 ms**。可辨识性上 λ 有可检验转折（约 0.5–0.75），40 人/组 SE(λ) ≈ **0.16**（80 人 0.115）。"
    "**处置**：不把 λ 加进主模型（4 档组间剂量分不清 0.5 与 0.75），写进论文作为「模型扩展 + 可检验预测」，"
    "并用实测数据检验 `β_SP = 0` 这一现行假设。 | "
    "用户 2026-10-24：「随着练习增加自我相关的刺激已经达到饱和，但练习增加了他人 v ⇒ f_Self = 1−λ(1−f_Other) ……"
    "纳入建模是不是会更好做出 SPE 的差异」+「我希望 `1_Code` 下只存放代码，所有的图放到 `3_Figures`，"
    "所有过程中产生的数据放到 `2_Data`，且 data 只在 Generate_Data 和 Real_Data 下」 | "
    "`1_Code/Experiment/practice_lambda.py`（**新建**）+ `3_Figures/_practice/fig9_practice_lambda.png` + "
    "`2_Data/Generate_Data/_practice/` 三个产物 + `5_Reference/08_工作流/文件结构整理_待办.md`（**新建**）+ "
    "`1_Code/DDM_Core/_scratch/_migrate_layout.py`（搬迁脚本） |"
)

PROGRESS = (
    "| 2026-10-24 | **13（练习 × SPE 与工程口径 → D115）** | **两条都落地了**：① 目录三分（图/数据/代码）已搬迁并改代码常量，"
    "`check_traceability` 1420 项 0 问题；`_scratch/` 暂不动，登记待办 8 条。② λ 天花板机制在本项目口径下算清了："
    "**现行模型（λ=1）预测 SPE 随练习上升，与 HuYQ 实测下降方向相反**；λ=0 则衰减到 0；40 人/组 SE(λ)≈0.16 ⇒ "
    "可做方向检验、做不了精细区间。 | 用户 2026-10-24 的机制设想 + 目录整理要求 | "
    "`1_Code/Experiment/practice_lambda.py` + `3_Figures/_practice/fig9_practice_lambda.png` + "
    "`2_Data/Generate_Data/_practice/` 三个产物 + `文件结构整理_待办.md` |"
)

CHANGELOG = (
    "| 2026-10-24 | **新增 D115（图文数据三分 + λ 天花板敏感性）**：图移 `3_Figures/`（`M-T1..3`、`_compare`、`figures_sim`、"
    "`_practice`），合成数据移 `2_Data/Generate_Data/_synth_datasets/`，代码加 `FIG_ROOT`/`--figroot`/`--figout`/`FIG_OUT`；"
    "新增 `practice_lambda.py`（λ ∈ {1,.75,.5,.25,0} × P ∈ {0,8,32,120}，含 (λ,τ_P) Fisher 信息），结论：λ=1 与实测方向相反、"
    "40 人/组 SE(λ)≈0.16 ⇒ 只加进论文作可检验预测，不改主模型；`_scratch/` 梳理登记为待办；`check_traceability` 1420 项 0 问题。 |"
)

EVIDENCE = (
    "| `1_Code/Experiment/practice_lambda.py` + `3_Figures/_practice/fig9_practice_lambda.png` + "
    "`2_Data/Generate_Data/_practice/practice_lambda.csv` + `practice_lambda_ident.csv` | D115 证据：λ 族轨迹三联图"
    "（λ 决定 SPE 随练习的方向 / 正确率侧同族 / 与 HuYQ 实测归一化对照）+ SE(λ) 表（20/40/80 人/组 = 0.230/0.162/0.115） |"
)

README_ROW = (
    "| 96 | ✅ **图文数据三分 + λ 天花板敏感性（D115）** | 图移 `3_Figures/`（`M-T1..3` / `_compare` / `figures_sim` / `_practice`）、"
    "合成数据移 `2_Data/Generate_Data/_synth_datasets/`，代码加 `FIG_ROOT`（`gen_viz`）/`--figout`（`make_sim_figures`）/`FIG_OUT`"
    "（`spe_locus`）；新增 `1_Code/Experiment/practice_lambda.py`：λ ∈ {1,.75,.5,.25,0} × P ∈ {0,8,32,120} 的 SPE_RT/SPE_ACC 轨迹 + "
    "(λ,τ_P) Fisher 信息。读数：λ=1 ⇒ SPE_RT 随练习 +20.5→+27.6 ms（**与 HuYQ 实测 −3.30 ms/阶段 方向相反**），λ=0 ⇒ 衰减到 "
    "+0.3 ms；SE(λ)=0.230/0.162/0.115（20/40/80 人/组）⇒ 只作可检验预测进论文，不改主模型。`_scratch/` 梳理见 "
    "`5_Reference/08_工作流/文件结构整理_待办.md` |"
)


def main() -> int:
    plan = PLAN.read_text(encoding="utf-8").split("\n")
    if any("**D115**" in ln for ln in plan):
        print("[skip] 主计划已有 D115")
    else:
        plan = insert_after(plan, "| **D114** | 2026-10-24 |", DECISION)
        plan = insert_after(plan, "**12（SPE 位点诊断 → D114）**", PROGRESS)
        plan = insert_after(plan, "**新增 D114（SPE 位点敏感性分析）**", CHANGELOG)
        plan = insert_after(plan, "`1_Code/Experiment/spe_locus.py` + `3_Figures/_compare/fig8_spe_locus.png`", EVIDENCE)
        PLAN.write_text("\n".join(plan), encoding="utf-8", newline="\n")
        print(f"主计划：{len(plan)} 行")

    rd = README.read_text(encoding="utf-8").split("\n")
    if any("**图文数据三分 + λ 天花板敏感性（D115）**" in ln for ln in rd):
        print("[skip] README 已有第 96 项")
    else:
        rd = insert_after(rd, "| 95 | ✅ **SPE 位点敏感性分析（D114）**", README_ROW)
        README.write_text("\n".join(rd), encoding="utf-8", newline="\n")
        print(f"README：{len(rd)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
