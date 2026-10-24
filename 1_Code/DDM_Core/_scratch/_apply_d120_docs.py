"""D120 落纸：数据快速筛查一条命令。幂等：已插入的行不再插第二次。"""
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


intake_n = len((ROOT / "1_Code/Experiment/intake.py").read_text(encoding="utf-8").split("\n"))
rdc_n = len((ROOT / "1_Code/Experiment/real_data_check.py").read_text(encoding="utf-8").split("\n"))

# ---------------------------------------------------------------- 主计划
plan = rd(PLAN)

d120 = (
    "| **D120** | 2026-10-24 | **数据快速筛查收成一条命令：`intake.py` 从「单场入库判定」扩成五层 + 三档裁决 + "
    "统计层定编 + 报告落盘**。用户目标是「边收数据边查质量，再看是该补还是达标」。仓里原本是三件套"
    "（`intake.py` 三层、`qc_group.py` 结构层、`check_stage1_acceptance.py` 技术层），要连着跑再人工合并；"
    "现在一条命令出 Markdown/CSV/JSON。**四处口径修正**：① 练习段期望值 `max(4,P)` → `P`（P=0 组 5/5 曾被误判 EXCLUDE，"
    "旧快照 4 行仍兼容并记信息项）；② `6-B KbQueue 刺激期按键` 降为信息项——它是 Stage 1 实机验收「至少 1 例 `RT < T`」"
    "的取证检查，20 人批次必然 0 例（数据 RT 最小 72 ms）；③ `6-C` 单行级异常、一致层逐行取值异常降为信息项，成片失败仍硬；"
    "④ **行为类偏离（超时/正确率/提前按键）一律只记录不阻塞**——拿行为当剔除理由等于按结果挑被试，会把组间比较挑成"
    "「好被试 vs 差被试」。**新增统计层**：ΔRT 中位 / Δacc / 分位斜率三个端点量，`n = (SD/目标 SE)²` 定编（目标 SE = "
    "10 ms / 0.03 / 30 ms），按 P 四组分别算再求和——P 是组间因子，把 20 人当一个大样本会低估缺口。跑 20 人批次："
    "**计入 17 / 待复核 1 / 不计入 2**；两个 EXCLUDE 都有据（`3-1` 正确率 0.520 + RT 中位 228 ms；`4-3` 正确率 0.378），"
    "1 个 REVIEW 是 `1-5`（txt 追加写导致 14 行重复，CSV 只能计一次）。统计层判 **需补**：每组需 11–16 人、四组共 55 人，"
    "现有 18 人 ⇒ 差 37 人（按 20% 损耗应再招 45）。**顺带修数据口径**：`stage` 只有 practice/formal，练习段固定 "
    "T=83.3/W=1200 且行数 = P，混进统计会把 (T,W) 单元计数与 SPE 一起带偏 ⇒ `clean(formal_only=True)`，D119 的数字更正为 "
    "**Δacc +5.2 pp / ΔRT 中位 +38.8 ms / 分位斜率 +44.0 ms**（方向与结论不变，见 D119 行末更正）；`d_timeout` 原本是占位 0，"
    "改为在**原始正式段**上算（`responded` 只在清洗前有区分度），得 +2.4 pp、13/20 人同向。 | 用户 2026-10-24："
    "「所有流程有一套可信可重复的就行了，可以整合成完整一套……做成数据快速筛查（边收数据便检查数据质量，再看数据质量是"
    "需要补还是达标）」 | `1_Code/Experiment/intake.py`（251 → "
    f"{intake_n} 行）+ `1_Code/Experiment/real_data_check.py`（`load_files`/`_derive`/`formal_only`/`d_timeout` 四处改）"
    "+ `4_Reports/筛查_New_Design_20261024.{md,csv,json}` + `5_Reference/08_工作流/数据快速筛查SOP.md`（**新建**） |"
)

i119 = index_of(plan, "| **D119** |")
if not any(s.startswith("| **D120** |") for s in plan):
    # D119 行末补口径更正
    tail = "（**新建**） |"
    assert plan[i119].endswith(tail), plan[i119][-80:]
    plan[i119] = plan[i119][: -len(tail)] + (
        "（**新建**）。"
        "**口径更正（2026-10-24 晚，见 D120）**：练习段混入统计的问题已修（只取正式段 576 行），数字更正为 "
        "**Δacc +5.2 pp（t=2.10）、ΔRT 中位 +38.8 ms（t=5.45）、分位斜率 +44.0 ms（t=2.22）**，"
        "「每 1 pp 换 6.5 ms ⇒ 约 1/4 来自速率通道」随之更正为 **7.5 ms/pp ⇒ 约 1/3**；方向与结论不变。 |"
    )
    plan.insert(i119 + 1, d120)

prog_row = (
    "| 2026-10-24 | **17（数据快速筛查 → D120）** | **一条命令跑完**：`intake.py` 五层（技术/结构/一致/质量/统计）"
    "+ 三档裁决（KEEP/REVIEW/EXCLUDE）+ 报告三件套落盘。20 人批次读数：计入 17 / 待复核 1 / 不计入 2；统计层判「需补」，"
    "每组需 11–16 人、四组共 55 人、现有 18 人 ⇒ 差 37 人（按 20% 损耗应招 45）。未做：`r_S` 接进似然、LMM 复核。 | "
    "`4_Reports/筛查_New_Design_20261024.md`；`5_Reference/08_工作流/数据快速筛查SOP.md` | — |"
)
if not any("数据快速筛查 → D120" in s for s in plan):
    i = index_of(plan, "| 2026-10-24 | **16（20 人真实数据首轮 → D119）** |")
    plan.insert(i + 1, prog_row)

log_row = (
    "| 2026-10-24 | **新增 D120（数据快速筛查一条命令）**：`intake.py` 扩成五层 + 三档裁决 + 统计层定编 + 报告落盘；"
    "四处口径修正（练习段期望 = P、6-B/单行 6-C/一致层逐行降为信息项、行为偏离只记录不阻塞）；修正练习段混入统计"
    "（`clean(formal_only=True)`）并把 D119 数字更正为 +5.2 pp / +38.8 ms / +44.0 ms；`d_timeout` 由占位 0 改为按原始"
    "正式段计算（+2.4 pp，13/20 人同向）。 |"
)
if not any("新增 D120" in s for s in plan):
    i = index_of(plan, "| 2026-10-22 | **新增 D118（SPE 判据通道 `Δz_S`）**")
    plan.insert(i + 1, log_row)

ev_row = (
    "| `1_Code/Experiment/intake.py` + `5_Reference/08_工作流/数据快速筛查SOP.md` + "
    "`4_Reports/筛查_New_Design_20261024.{md,csv,json}` | D120 证据：一条命令的入口与判据说明书；三件套报告是 20 人批次的"
    "可复现快照（含生成命令、阈值表、五层口径）。读数：计入 17 / 待复核 1 / 不计入 2；统计层「需补」（每组 11–16 人、"
    "四组 55 人、现有 18 人）。 |"
)
if not any("D120 证据" in s for s in plan):
    plan.append(ev_row)

wr(PLAN, plan)
print(f"[plan] {len(plan)} 行")

# ---------------------------------------------------------------- README §9
rd_lines = rd(README)
item = (
    "| 101 | ✅ **数据快速筛查一条命令（D120）** | `1_Code/Experiment/intake.py` 从 D95 的三层入库判定扩成**五层**"
    "（技术/结构/一致/质量/统计）+ **三档裁决**（`KEEP`/`REVIEW`/`EXCLUDE`）+ 报告三件套（`--out/--csv/--json`）。"
    "统计层按 P 四组分别算 `n = (SD/目标 SE)²`（目标 SE = 10 ms / 0.03 / 30 ms）再求和：20 人批次 **计入 17 / 待复核 1 / "
    "不计入 2**，判**需补**（每组 11–16 人、四组 55 人、现有 18 人 ⇒ 差 37 人，按 20% 损耗应招 45）。口径修正：练习段期望 = P"
    "（非 `max(4,P)`）、`6-B`/单行 `6-C`/一致层逐行异常降为信息项、**行为偏离只记录不阻塞**；`real_data_check.py` 改为只统计"
    "正式段（练习段固定 T=83.3/W=1200）并把 `d_timeout` 由占位 0 改为原始正式段口径（+2.4 pp、13/20 人同向）。"
    f"说明见 `5_Reference/08_工作流/数据快速筛查SOP.md`；`real_data_check.py` 现 {rdc_n} 行。 |"
)
if not any(s.startswith("| 101 |") for s in rd_lines):
    i = index_of(rd_lines, "| 100 | ✅ **20 人真实数据首轮分析（D119）**")
    rd_lines.insert(i + 1, item)
    wr(README, rd_lines)
print(f"[readme] {len(rd_lines)} 行")
