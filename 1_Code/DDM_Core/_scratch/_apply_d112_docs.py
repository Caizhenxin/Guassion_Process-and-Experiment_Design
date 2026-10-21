"""D112 落纸：主计划（决策行 / 进度行 / 变更日志 / 证据行）+ README §9 第 93 项。

列数一律按锚点行实测，不凭印象（D101/D104/D105 都踩过「以为几列」的坑）。
"""
import re
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RD = ROOT / "1_Code" / "DDM_Core" / "README.md"


def cells(line: str) -> int:
    return line.strip().strip("|").count("|") + 1


def insert_after(lines: list[str], anchor: str, new: str, expect_cols: int | None = None) -> list[str]:
    idx = [i for i, ln in enumerate(lines) if anchor in ln]
    assert len(idx) == 1, f"锚点不唯一/不存在：{anchor!r} -> {idx}"
    a = lines[idx[0]]
    if expect_cols is not None:
        assert cells(a) == expect_cols, f"列数不符：锚点 {cells(a)} 列 vs 期望 {expect_cols} 列"
    assert cells(new) == cells(a), f"新行 {cells(new)} 列 ≠ 锚点 {cells(a)} 列"
    lines.insert(idx[0] + 1, new)
    return lines


# ---------------------------------------------------------------- 主计划
plan = PLAN.read_text(encoding="utf-8").split("\n")
n0 = len(plan)

D112 = (
    "| **D112** | 2026-10-21 | **模型章接进渲染：模板 → `manuscript_model_draft.md`（第 5 步写两份草稿）**。"
    "`1_Code/Experiment/manuscript.py`（154 → 约 440 行）新增模型章管线：`subject_points` 从 stage8 逐被试众数取 "
    "`(P, d_ref, beta_S)`、`group_between` 做「先估被试层漂移、再做组间回归」并**按被试自举 200 次**给区间"
    "（守卫：≥2 个 P 水平且 ≥4 人，否则返回 `None` 而不是给假数字）、`model_values` 填 `rho`/`sigma`/`elpd`/健康表、"
    "`render_model` 整篇替换占位符、`tidy_preamble` 把模板的「用法」段降级为说明、`write_model_draft` 落盘草稿。"
    "未填项**不静默留白**：替换成 `【待数据：<中文原因>】` 并在文首点名。`run_pipeline.py` 第 5 步现在写两份"
    "（`manuscript_draft.md` + `manuscript_model_draft.md`）。实跑 n8（`--reuse-stage8`）：251 行 / 15.8 KB / "
    "8 处【待数据】/ 0 处残留占位；`rho` 1.325、ELPD −3526.4（M-T1）vs −3562.5（M-T3）、`beta_T` 0.909，"
    "`beta_P` 因该批数据只有 1 档 P 而正确留空。**顺带修两个真 bug**：① `MARK_RE` 原写 `[a-z0-9_]+`，"
    "`{{beta_T}}`、`{{sigma_*}}` 从来匹配不到；② `--reuse-stage8` 只认 `<out>/stage8`，在扫描布局"
    "（`<scan>/n8/data` 与 `n8/stage8` 平级）下误判「无可复用 JSON」而重跑 2.5 h 拟合 ⇒ 加 `<data>/stage8` 与 "
    "`<data>/../stage8` 两级回退，`step_figures` 改用同一目录。 | 用户 2026-10-21：「请你继续，有进展随时告诉我」；"
    "D110 的模板只留占位符却没人填，手填会重演「同一张表两处各自渲染」的老毛病（D101）。 | "
    "`1_Code/Experiment/manuscript.py`（扩写）+ `1_Code/Experiment/run_pipeline.py`（第 5 步两份草稿 + `resolve_stage8`）"
    "+ `1_Code/Experiment/_scratch_check_model_chapter.py`（**新建**，12 项自测）+ "
    "`1_Code/Experiment/exp_Check/check_run_pipeline.py`（P9 三条，11 → 14 项） |"
)
plan = insert_after(plan, "| **D111** | 2026-10-21 |", D112)

PROG = (
    "| 2026-10-21 | **10（模型章自动化 → D112）** | **接上了**：`manuscript.py` 从模板生成 "
    "`manuscript_model_draft.md`（251 行 / 8 处【待数据】/ 0 残留占位），流水线第 5 步同时产出结果章与模型章两份草稿；"
    "自测 `check_run_pipeline.py` 14/14、模型章专项 12/12。未做：`bic` / `rho` 区间 / `se_elpd` 三项仍缺（stage8 JSON 未落盘）。 | "
    "`1_Code/Experiment/manuscript.py`；`run_pipeline.py` 第 5 步；`_e2e_n8/manuscript_model_draft.md` | — |"
)
plan = insert_after(plan, "| 2026-10-21 | **10（③ 设计空间 → D109 定稿）** |", PROG)

LOG = (
    "| 2026-10-21 | **新增 D112（模型章接进渲染）**：`manuscript.py` 加模型章管线（`subject_points` / "
    "`group_between` 自举 / `model_values` / `render_model` / `write_model_draft`），`run_pipeline.py` 第 5 步写两份草稿；"
    "修 `MARK_RE` 匹配不到 `{{beta_T}}` 与 `--reuse-stage8` 在扫描布局下重跑拟合两个真 bug；"
    "`check_run_pipeline.py` 11 → 14 项（P9 三条），模型章专项自测 12/12。 |"
)
plan = insert_after(plan, "| 2026-10-21 | **新增 D109（保留 P 方案 + tau_P 探索性）**", LOG)

EVID = (
    "| `1_Code/Experiment/manuscript.py`（D112 扩写至约 440 行）+ `run_pipeline.py` 第 5 步 + "
    "`1_Code/Experiment/_scratch_check_model_chapter.py`（**新建**）+ `1_Code/DDM_Core/_scratch/_e2e_n8/manuscript_model_draft.md`（251 行） | "
    "D112 证据：模板 → 草稿全自动，缺值带中文原因；n8 端到端 0.1 min（复用 stage8）跑出结果章 + 模型章两份草稿 |"
)
# 证据表在文件末尾：追加到最后一个表行之后
j = max(i for i, ln in enumerate(plan) if ln.startswith("| `") and ln.rstrip().endswith("|"))
assert cells(plan[j]) == 2, f"证据表列数 {cells(plan[j])}"
assert cells(EVID) == 2
plan.insert(j + 1, EVID)

PLAN.write_text("\n".join(plan), encoding="utf-8", newline="\n")
print(f"主计划 {n0} -> {len(plan)} 行")

# ---------------------------------------------------------------- README
rd = RD.read_text(encoding="utf-8").split("\n")
m0 = len(rd)
ITEM = (
    "| 93 | ✅ **模型章自动生成（D112）** | `1_Code/Experiment/manuscript.py` 把 "
    "`5_Reference/03_论文写作/论文_模型章_模板.md` 渲染成 `manuscript_model_draft.md`：`subject_points` 取逐被试众数、"
    "`group_between` 做组间回归并按被试自举 200 次给 `beta_P` 区间（守卫 ≥2 档 P、≥4 人）、`model_values` 填 "
    "`rho`/`sigma`/`elpd`/健康表；未填项写 `【待数据：<原因>】` 并在文首点名。`run_pipeline.py` 第 5 步同时产出结果章与"
    "模型章两份草稿。顺带修两 bug：`MARK_RE` 匹配不到 `{{beta_T}}`、`--reuse-stage8` 在扫描布局下重跑 2.5 h 拟合。 |"
)
rd = insert_after(rd, "| 92 | ✅ **对外预览三件套（D111）**", ITEM)
RD.write_text("\n".join(rd), encoding="utf-8", newline="\n")
print(f"README {m0} -> {len(rd)} 行")
