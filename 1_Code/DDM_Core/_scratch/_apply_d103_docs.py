"""D103 落纸：CSV 分支端到端验证（主计划四张表 + 使用说明 §6 第 5 条）。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
DOC = ROOT / "5_Reference" / "08_工作流" / "全流程一键跑通_使用说明.md"

DEC = (
    "| **D103** | 2026-10-18 | **「有 CSV 的场次」这条分支此前只跑过一场真数据，没做过可复现验证**。"
    "① 用 `1_Code/Experiment/exp_matlab/test/_full_session_out`（3 场、CSV+txt 双件：组1-1、组1-99、组2-99）"
    "跑 `run_pipeline.py --skip-stage8` ⇒ `[1/5] 3 场、KEEP 0`，三场 EXCLUDE 的理由各自可达："
    "**组1-1** 是 v4.5 时代旧产物（`stimulus_dur_actual` 与 T 差 **−14.37 帧 / 239.40 ms**，正是 D89 修的那类），"
    "**组1-99 / 组2-99** 是 PTB 桩环境、无刺激期按键 ⇒ 6-B 不可达（与 D98 合成数据同根因）；"
    "② 附带确认：该目录的 `EXP_data_group1_1.csv` 与真实交付**同键**，`intake` 的「层级最浅优先 + `shadowed`」"
    "在真实目录结构下有效（D95）；③ 结论：CSV 分支无缺陷，EXCLUDE 都是真缺陷 ⇒ 后续不必再对 CSV 分支做人工目测 "
    "| `1_Code/DDM_Core/_scratch/_pipeline_csvtest/`（产物：`intake_report.md` / `stage6_report.md` / `pipeline_report.md`）"
    "+ `5_Reference/08_工作流/全流程一键跑通_使用说明.md` §6 第 5 条 "
    "| 无（本条只固定「CSV 分支已验证」这一事实） |"
)

PROG = (
    "| 2026-10-18 | **6（CSV 分支端到端验证 → D103）** | 拿 MATLAB 冒烟产物（3 场 CSV+txt）跑"
    "`run_pipeline.py --skip-stage8`：3 场全 EXCLUDE 且理由可达（旧产物 `stimulus_dur_actual` −14.37 帧、"
    "桩环境无 6-B）；顺带在真实目录结构下复核同名遮蔽规则 "
    "| `1_Code/DDM_Core/_scratch/_pipeline_csvtest/`（3 份报告）"
    "+ `全流程一键跑通_使用说明.md`（§6 第 5 条） "
    "| 无 |"
)

CHG = (
    "| 2026-10-18 | **新增 D103（CSV 分支端到端验证）**：用 `test/_full_session_out` 的 3 场双件跑"
    "`--skip-stage8`，3 场全 EXCLUDE 且理由都是真缺陷；同时验证同名自测件与真数据同键时"
    "`intake` 的遮蔽规则有效 |"
)

EV = (
    "| `1_Code/DDM_Core/_scratch/_pipeline_csvtest/{intake_report.md、stage6_report.md、pipeline_report.md}`"
    "（D103 产物）+ `1_Code/Experiment/exp_matlab/test/_full_session_out/`（3 场 CSV+txt fixture） "
    "| D103 证据：CSV 分支无缺陷；EXCLUDE 的理由分别是「旧产物帧量化 −14.37 帧」与「桩环境无刺激期按键」 |"
)

DOCITEM = (
    "5. **CSV 分支已端到端验证（D103）**：拿 `1_Code/Experiment/exp_matlab/test/_full_session_out`"
    "（3 场、均含 CSV+txt）跑 `--skip-stage8` ⇒ 3 场全 EXCLUDE，理由都是真缺陷"
    "（组1-1 是 v4.5 旧产物：`stimulus_dur_actual` 与 T 差 −14.37 帧；组1-99/组2-99 是桩环境、无刺激期按键）。"
    "注意同名风险：该目录的 `EXP_data_group1_1.csv` 与真实交付同键，`intake` 靠「层级最浅」规则才不会挑错（D95 的 `shadowed`）。"
)


def edit(path: Path, fn):
    L = path.read_text(encoding="utf-8").split("\n")
    L = fn(L)
    path.write_text("\n".join(L), encoding="utf-8", newline="\n")
    print(path.name, "→", len(L), "行")


def plan_fn(L):
    def ins_after(prefix, row):
        idxs = [i for i, x in enumerate(L) if x.startswith(prefix)]
        assert len(idxs) == 1, (prefix, len(idxs))
        L.insert(idxs[0] + 1, row)

    ins_after("| **D102** |", DEC)
    ins_after("| 2026-10-18 | **D100 后续（最小可辨识样本量扫描）**", PROG)
    ins_after("| 2026-10-18 | **新增 D102（最小可辨识样本量扫描）**", CHG)
    L.append(EV)
    return L


def doc_fn(L):
    i = max(i for i, x in enumerate(L) if x.startswith("4. `stage8_run.py` 只吃"))
    L.insert(i + 1, DOCITEM)
    return L


edit(PLAN, plan_fn)
edit(DOC, doc_fn)
