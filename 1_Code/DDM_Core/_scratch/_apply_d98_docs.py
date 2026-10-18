"""把 D98（全流程一键跑通）落进四份文档。

用法：python _apply_d98_docs.py
数字来源：2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_stage8_out/stage8_group_1.json（若无则标记为待跑）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
S8 = ROOT / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
S6 = ROOT / "5_Reference" / "08_工作流" / "Stage6_Pilot方案.md"
JSON1 = ROOT / "2_Data" / "Real_Data" / "_SYNTHETIC_DEMO_v1" / "_stage8_out" / "stage8_group_1.json"


def read_json_stats() -> str:
    if not JSON1.is_file():
        return "组 1 拟合尚未落盘"
    d = json.loads(JSON1.read_text(encoding="utf-8"))
    out = []
    for name, r in (d.get("results") or {}).items():
        fit = r.get("fit") or {}
        loo = r.get("loo") or {}
        out.append(
            f"{name} ELPD {loo.get('elpd_loo', float('nan')):.1f}"
            f"（`p_loo` {loo.get('p_loo', float('nan')):.2f}、"
            f"`n_obs` {loo.get('n_obs', 0)}、`k_max` {loo.get('k_max', float('nan')):.2f}、"
            f"`k_diag_ok` {loo.get('k_diag_ok')}、{fit.get('n_em_used', '?')} 轮 EM）"
        )
    return "；".join(out)


def patch(path: Path, subs: list[tuple[str, str]]) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for old, new in subs:
        c = text.count(old)
        if c != 1:
            print(f"[FAIL] {path.name}：锚点命中 {c} 次（应为 1）\n  {old[:80]}")
            sys.exit(1)
        text = text.replace(old, new)
        n += 1
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[ok] {path.name}：{n} 处，{len(text.splitlines())} 行")
    return n


def main() -> int:
    stats = read_json_stats()

    # ---------- 主计划：决策行 + 进度行 + 变更日志 + 证据行 ----------
    dec = (
        "| **D98** | 2026-10-18 | ✅ **全流程一键跑通（合成数据版）**：新增 "
        "`run_pipeline.py`（编排「入库 → 达标 → 层级拟合 → 出图 → 结果节骨架」）与 "
        "`make_figures.py`（行为层 / 参数 / Δelpd 三张图）；合成数据 "
        "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1`（8 名 DDM 合成被试、真值在 `synth_truth.json`）"
        "上 8/8 判 KEEP、Stage 6 判「可进入 Stage 7」。"
        f"Stage 8 quick 配置实测 **{stats}** ⇒ 单模型单人 ≈41 min，"
        "8 人 × 2 模型是**小时级批处理**，不得在交互式会话里等。"
        "顺带三处修正：① 生成器加 `--anticipation`（此前合成数据没有抢按 ⇒ 6-B 判据不可达）；"
        "② `loo.psis_loo` 增 `k_diag_ok`（`n_draws < 25` 时 `k̂` 恒 0，静默健康读数）；"
        "③ 参数图不得用单个被试的拉普拉斯协方差当组层区间。 | "
        "`1_Code/Experiment/run_pipeline.py`（**新建**，287 行）+ "
        "`1_Code/Experiment/make_figures.py`（**新建**，351 行）+ "
        "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/`（8 txt + `synth_truth.json` + README）+ "
        "`5_Reference/08_工作流/全流程一键跑通_使用说明.md`（**新建**）+ "
        "`5_Reference/03_论文写作/结果节_生成流程_20261018.md`（**新建**） | "
        "真数据到位后只做一件事：把 CSV/txt 放进 `2_Data/Real_Data/<新批次>/`，"
        "用同一条命令换目录重跑；**不改代码** |"
    )
    prog = (
        "| 2026-10-18 | **全流程跑通（合成数据 → 图 → 结果节骨架 → D98）** | "
        "把「数据目录 → 能不能用 → 达不达标 → 参数与模型比较 → 论文用的图与表」收成一条命令；"
        "合成数据 8 场全 KEEP，Stage 8 在 quick 配置上跑完组 1（2 人）并落盘，"
        "单模型单被试 ≈41 min ⇒ 正式规模必须后台批处理 | "
        "`run_pipeline.py` + `make_figures.py` + `全流程一键跑通_使用说明.md` |"
    )
    chg = (
        "| 2026-10-18 | **新增 D98（全流程一键跑通）**：`run_pipeline.py`（287 行）把 "
        "`intake.py` → `stage6_report.py` → `stage8_run.py` → `make_figures.py` → 结果节骨架串成一条命令；"
        "`make_figures.py`（351 行）出行为层 / 参数 / Δelpd 三图；"
        "合成数据 `_SYNTHETIC_DEMO_v1`（8 人）8/8 KEEP；"
        "缺陷三修：生成器 `--anticipation`、`loo.psis_loo` 的 `k_diag_ok`、参数图区间口径 |"
    )
    ev = (
        "| `1_Code/Experiment/run_pipeline.py`（**新建**，D98，287 行）+ "
        "`1_Code/Experiment/make_figures.py`（**新建**，351 行）+ "
        "`5_Reference/08_工作流/全流程一键跑通_使用说明.md`（**新建**）+ "
        "`5_Reference/03_论文写作/结果节_生成流程_20261018.md`（**新建**）+ "
        "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/`（8 名合成被试、`synth_truth.json`）+ "
        "`1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`（v2，243 行，含 `--anticipation`） | "
        "**D98**：全流程一键跑通；合成数据 8/8 KEEP、Stage 6 可进 Stage 7、"
        f"Stage 8 组 1 实测 {stats} |"
    )
    subs = []
    L = PLAN.read_text(encoding="utf-8").splitlines()
    idx = max(i for i, x in enumerate(L) if x.startswith("| **D97**"))
    subs.append((L[idx], L[idx] + "\n" + dec))
    idx = max(i for i, x in enumerate(L) if x.startswith("| 2026-10-18 | **5（定稿签批"))
    subs.append((L[idx], L[idx] + "\n" + prog))
    idx = max(i for i, x in enumerate(L) if x.startswith("| 2026-10-18 | **新增 D97"))
    subs.append((L[idx], L[idx] + "\n" + chg))
    idx = max(i for i, x in enumerate(L) if x.startswith("| `5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md`（**v2.7 定稿**"))
    subs.append((L[idx], L[idx] + "\n" + ev))
    patch(PLAN, subs)

    # ---------- README：§8.69 + §9 第 82 项 ----------
    sec = f"""### 8.69 全流程一键跑通：`run_pipeline.py`（D98，2026-10-18）

把「这一批数据能不能用 → 达不达标 → 参数与模型比较 → 论文的图与表」收成一条命令，
每步都调用既有工具（**不复制判据**），只新增编排、出图与结果节骨架。

| 步 | 命令 | 产物 |
|---|---|---|
| 1 | `intake.py`（D95） | `intake_report.md`：逐场次 KEEP / REVIEW / EXCLUDE |
| 2 | `stage6_report.py`（D96） | `stage6_report.md`：S6-1…S6-6 汇总 + §8 决策分支 |
| 3 | `stage8_run.py`（D72/D74） | `stage8/stage8_group_<组>.json` + `stage8.log` |
| 4 | `make_figures.py`（D98） | `figures/fig1_behavior_by_P.png`、`fig2_param_recovery.png`、`fig3_model_comparison.png` + `figures_index.md` |
| 5 | `run_pipeline.py` | `results_skeleton.md`（表已填、论述留 `【待写】`）+ `pipeline_report.md` |

- **实测（合成数据 8 人、quick 配置）**：`{stats}`；单模型单人 ≈41 min ⇒
  8 人 × 2 模型是**小时级批处理**，正式规模按 §11 第 5/12 条留余量。
- **三个自坑**：① `stage8_run.py` 只吃 txt（CSV 只够过前两步）；② `--profile quick` 的
  参数不可解释（EM 3 轮远未收敛），`k_diag_ok = false` 时 Δelpd 只能作流程验证；
  ③ 早前 `make_figures.py` 拿 `fit.covs[s]`（**单个被试**的拉普拉斯协方差）当组层区间，
  现改为「被试层众数灰点 + 组均值 ± 被试间 SEM」。
- 换真数据：CSV/txt 放进 `2_Data/Real_Data/<新批次>/`，同一条命令换目录重跑，
  **不改代码**；目录里没有 `synth_truth.json` 时图里不画真值线、骨架不带合成数据声明。
- 单独重出图用 `--reuse-stage8`（跳过拟合，只跑第 4、5 步），避免几十小时的重跑。
"""
    rtext = README.read_text(encoding="utf-8")
    anchor = "## 9. 尚未做"
    assert rtext.count(anchor) == 1
    rtext = rtext.replace(anchor, sec + "\n" + anchor)
    item = ("| 82 | ✅ **全流程一键跑通（D98）**：`run_pipeline.py` 串起 intake → stage6 → "
            "stage8 → 出图 → 结果节骨架；合成数据 8/8 KEEP；三图 + 骨架已产出 |")
    last = max(i for i, x in enumerate(rtext.splitlines()) if x.startswith("| 81 |"))
    lines = rtext.splitlines()
    lines.insert(last + 1, item)
    README.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"[ok] README：§8.69 + §9 第 82 项，{len(lines)} 行")

    # ---------- Stage 8 方案：§9 工具链行 + 变更日志 ----------
    patch(S8, [(
        "| `1_Code/DDM_Core/stage8_run.py`（**输入契约**，D66） |",
        "| `1_Code/Experiment/run_pipeline.py`（D98） | 把本项目整条分析链串成一条命令，"
        "并用合成数据（8 人 × 576 试次）端到端验证；出图与结果节骨架也在此收口 | "
        f"`_stage8_out/stage8_group_1.json` 实测 **{stats}**；"
        "`intake.py` 8/8 KEEP、`stage6_report.py` 判「可进入 Stage 7」 |\n"
        "| `1_Code/DDM_Core/stage8_run.py`（**输入契约**，D66） |",
    )])
    patch(S8, [(
        "| v1.8 | 2026-10-17 |",
        "| v1.9 | 2026-10-18 | **§9 加 `run_pipeline.py` 一行（D98）**：全流程一键跑通，"
        "合成数据 8 人端到端；`loo.psis_loo` 增 `k_diag_ok`（`n_draws < 25` 时 `k̂` 恒 0，"
        "此前是静默的健康读数，`check_loo.py` 26/26 仍全过）。 |\n"
        "| v1.8 | 2026-10-17 |",
    )])

    # ---------- Stage 6 方案：§9 现场清单加一条 + 变更日志 ----------
    patch(S6, [(
        "8. ☐ 按 §8 决策，并把结果回填到 §10 指定的三处。",
        "8. ☐ 一条命令跑完全链路（入库 → 达标 → 拟合 → 图 → 结果节骨架）："
        "`python -X utf8 1_Code\\Experiment\\run_pipeline.py 1_Code\\Experiment\\pilot_data --profile formal`；"
        "只重出图时加 `--reuse-stage8`。用法见 `5_Reference/08_工作流/全流程一键跑通_使用说明.md`。\n"
        "9. ☐ 按 §8 决策，并把结果回填到 §10 指定的三处。",
    )])
    patch(S6, [(
        "| v1.3 | 2026-10-18 | 新增 §6.3",
        "| v1.4 | 2026-10-18 | 新增 §9 第 8 条（D98：`run_pipeline.py` 一条命令跑完全链路，"
        "原第 8/9 条顺延）；判据本身未变 |\n"
        "| v1.3 | 2026-10-18 | 新增 §6.3",
    )])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
