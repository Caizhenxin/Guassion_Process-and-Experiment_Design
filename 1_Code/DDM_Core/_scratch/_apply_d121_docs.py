"""D121 落纸：Stage 8 真实数据首轮（15 人 quick 档）。幂等。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"


def rd(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def wr(p: Path, lines: list[str]) -> None:
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def index_of(lines: list[str], prefix: str) -> int:
    hits = [i for i, s in enumerate(lines) if s.startswith(prefix)]
    assert len(hits) == 1, f"anchor {prefix!r} -> {hits}"
    return hits[0]


plan = rd(PLAN)

d121 = (
    "| **D121** | 2026-10-25 | **Stage 8 在真实数据上第一次跑通（15 人 / quick 档），并抓到一条必须先解决的模型—数据不符**。"
    "先是 `run_pipeline` 第 3 步 0.0 min 就失败：`stage8_run.py` 只吃「同一目录下 N 个 `exp_group<g>_subject<s>.txt`」，"
    "而正式数据是 `Condition 1..4/` 分层布局 ⇒ 报「目录里没有 *.txt」。加转接层 `_stage8_stage_in.py`（按筛查快照的 KEEP "
    "硬链接到 `_stage8_in/`，不改字节），17 份进得去、读取器再拒 2 份（`2-4`、`4-4`：「`stimulus_dur_actual` 超 T+1 帧 1 行」）"
    "⇒ **实际入模 15 人**，耗时 18,752 s（≈5.2 h，两模型 × 四人组 × trial 级 LOO）。**模型比较给不出结论**："
    "ρ 自由（M-T1）在 **4/4 组**超参数 Hessian 非正定（`n_flipped` = 1/1/2/1）⇒ LOO 不可引用（组 1 抽样 `|θ|` 最大 79.3）；"
    "ρ 固定（M-T3）4/4 组全部有效（`k_max` 全 0、越界 0、`p_loo`/`n_obs` = 0.00135/0.00151/0.00311/0.00261），"
    "相对 M-T1 在组 3/4 高 62.0/49.6，但基准不可靠 ⇒ 只能记「ρ 固定更稳」，不能说「ρ 不该有」。**PPC 抓到真问题**："
    "有效模型下正确率与超时率基本复现，但**RT 中位 15 人里 12 人偏短、中位欠 60–90 ms**（极端 4-5 欠 168 ms、唯一大正偏 3-5 +17 ms），"
    "三个候选原因（`t0` 上界被顶住 / 时间基准 onset vs 掩蔽 / 输入延迟）本轮无法区分，quick 档的 `n_em=3`、`n_draws=12` 也贡献一部分。"
    "**顺带暴露两套严重性**：同一「单行掉帧」，筛查按 D120 记信息项、被试照收，`read_formal_data` 却整份拒收 ⇒ 17 人 vs 15 人；"
    "已写进 SOP §9，改成「丢坏试次、留被试」需单独决策。 | 用户 2026-10-24：「按主计划逐阶段完成……直到完成目标」——"
    "本轮推进 Stage 8（🟡 等正式数据 → 已在 15 人上跑通并定位问题） | "
    "`5_Reference/03_论文写作/Stage8_真实数据首轮_20261025.md`（**新建**）+ `2_Data/Real_Data/New_Design/_pipeline/stage8/"
    "stage8_report.md`（1417 行）+ `1_Code/DDM_Core/_scratch/_stage8_stage_in.py`（转接层）+ "
    "`5_Reference/08_工作流/数据快速筛查SOP.md` §9 |"
)

i120 = index_of(plan, "| **D120** |")
if not any(s.startswith("| **D121** |") for s in plan):
    plan.insert(i120, d121)

prog_row = (
    "| 2026-10-25 | **18（Stage 8 真实数据首轮 → D121）** | 15 人 quick 档跑通（5.2 h）：ρ 自由模型 4/4 组 LOO 无效 ⇒ "
    "模型比较无结论；ρ 固定模型 4/4 组有效；PPC 显示 RT 中位 12/15 人偏短 60–90 ms（acc/超时基本复现）。新建扁平转接层 "
    "`_stage8_stage_in.py`；暴露「单行掉帧」两套严重性（17 人 vs 15 人）。未做：formal 档 PPC 复核、`t0` 上界查证、"
    "判据对齐、组层 P 效应（需 ≥10 人/组）。 | `Stage8_真实数据首轮_20261025.md`；`_pipeline/stage8/stage8_report.md` | — |"
)
if not any("Stage 8 真实数据首轮 → D121" in s for s in plan):
    i = index_of(plan, "| 2026-10-24 | **17（数据快速筛查 → D120）** |")
    plan.insert(i + 1, prog_row)

log_row = (
    "| 2026-10-25 | **新增 D121（Stage 8 真实数据首轮）**：加 `_stage8_stage_in.py` 扁平转接层（stage8 只吃同层 txt）；"
    "15 人 quick 档 5.2 h 跑通；ρ 自由模型 4/4 组 LOO 无效、ρ 固定模型 4/4 组有效；PPC 抓到 RT 欠预测 60–90 ms；"
    "记录「单行掉帧」两套严重性（SOP §9）。 |"
)
if not any("新增 D121" in s for s in plan):
    i = index_of(plan, "| 2026-10-24 | **新增 D120（数据快速筛查一条命令）**")
    plan.insert(i + 1, log_row)

ev_row = (
    "| `5_Reference/03_论文写作/Stage8_真实数据首轮_20261025.md` + `_pipeline/stage8/stage8_report.md` | D121 证据："
    "Stage 8 首次在真实数据上跑通的完整读数（4 组 × 2 模型的 ELPD/`p_loo`/`n_flipped`）+ 逐人 PPC 表 + 复现命令 + "
    "两处口径冲突的处置状态。 |"
)
if not any("D121 证据" in s for s in plan):
    plan.append(ev_row)

wr(PLAN, plan)
print(f"[plan] {len(plan)} 行")

rd_lines = rd(README)
item = (
    "| 102 | ✅ **Stage 8 真实数据首轮（D121）** | `1_Code/DDM_Core/_scratch/_stage8_stage_in.py` 把 `Condition 1..4/` 的 "
    "KEEP 场次硬链接成扁平 `_stage8_in/`（stage8 只吃同层 txt，否则报「目录里没有 *.txt」）。15 人 quick 档 5.2 h："
    "**ρ 自由模型 4/4 组超参数 Hessian 非正定 ⇒ LOO 不可引用**；ρ 固定模型 4/4 组有效（`p_loo`/`n_obs` 0.0014–0.0031）。"
    "PPC：acc/超时基本复现，**RT 中位 12/15 人偏短 60–90 ms**（`t0` 上界/时间基准/输入延迟三候选未区分）。"
    "暴露「单行掉帧」两套严重性（筛查 17 人 vs stage8 15 人），见 SOP §9。 |"
)
if not any(s.startswith("| 102 |") for s in rd_lines):
    i = index_of(rd_lines, "| 101 | ✅ **数据快速筛查一条命令（D120）**")
    rd_lines.insert(i + 1, item)
    wr(README, rd_lines)
print(f"[readme] {len(rd_lines)} 行")
