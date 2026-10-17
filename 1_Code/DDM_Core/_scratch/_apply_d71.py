# -*- coding: utf-8 -*-
"""把 D71（Stage 6/7 真实规模就绪实测）落进四份文档。

用法：
    python -X utf8 -u _apply_d71.py            # 干跑，只打印每个插入点命中情况
    python -X utf8 -u _apply_d71.py --apply    # 真写
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S6 = REPO / "5_Reference" / "08_工作流" / "Stage6_Pilot方案.md"
S7 = REPO / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

APPLY = "--apply" in sys.argv

# ---------------------------------------------------------------- 主计划 §5
D71_DECISION = (
    "| **D71** | 2026-10-17 | ✅ **Stage 6/7 的真实规模就绪实测：合法 DDM 数据跑不跑得通，以及"
    "「待复核」到底有多重**。① 动机：Stage 6 的自测只有 6 例小数据、Stage 7 的 `qc_group.py` 只有 10 例自测，"
    "**两者都没在真实规模（8 人 × 576 试次）上跑过一遍** —— 而「脚本能跑」是用户侧开跑前的最后一道自证。"
    "② 做法：用 D70 的生成器 `_make_ddm_pilot.py --preset qc --n-subjects 8`（seed 31，5.2 s）生成 8 人 v4.1 数据，"
    "依次跑 `qc_group.py --expect-n 8` 与 `analyze_pilot.py`。"
    "③ 结果：`qc_group.py` 的 **G1–G9 全 PASS**（组层 timeout 7.38%、正确率 0.570、`RT < T` 2.23%、帧长 16.667 ms）、"
    "**剔除 0**；`analyze_pilot.py` 的 **S1-1 与 S6-1…S6-6 全 PASS、0 项 WARN**（`RT < T` 2.37%、刺激内 2.37%、"
    "timeout 最差单元 14.58%、注视期抢按 0%、自洽 0 行矛盾）。"
    "④ ❗ 新发现（写进两份 Stage 文档的限制）：**逐被试判据会把合法数据标成「待复核」** —— 8 人里 **5 人**被标"
    "（4 人 **S6-5 FAIL**：正确率 0.493–0.550 < 0.55；1 人 **S6-1 FAIL**：最差单元 timeout 41.7% > 40%），"
    "而组层全 PASS。机理：S6-1/S6-5 本来是**组层**判据，下沉到被试层后个体差异与截断效应会让边界频繁触发"
    "（正确率跨被试 0.493–0.616，与被试 `t0` 相关的 timeout 率 0.4%–18.4% 负相关：deadline 截断掉的更多是慢错误）。"
    "⑤ 处置：**不删判据、不放宽阈值**（Stage 7 §8「采集中途不得改判据」），只把语义钉死 —— "
    "「待复核」= 人工看一眼，**不等于剔除**（`qc_group.py` 里两个分支本不共用累加器）；论文里报「复核率」而不是「剔除率」。"
    "⑥ 牙齿：新建 `1_Code/Experiment/exp_Check/check_pilot_ready.py`（**9/9**）：P1/P1b 组层全 PASS 且剔除 0、"
    "P2/P2b 待复核 5 人的依据分布钉死（S6-5 × 4 + S6-1 × 1）、P2c 不升级为剔除、P3 Pilot 分析 0 WARN、"
    "P4/P5 静态（两分支不共用累加器；S6-2c 仍与 S6-2 分开判）。 | "
    "`1_Code/DDM_Core/_scratch/_qc_group_n8.txt`、`_pilot_analysis_n8.txt`、`_check_pilot_ready_console.txt`；"
    "`1_Code/Experiment/exp_Check/check_pilot_ready.py`（9/9） | "
    "等用户侧 Stage 1 实机验收与 Stage 6 Pilot；真数据上的「复核率」是本条的实测对象 |"
)
D71_PROGRESS = (
    "| 2026-10-17 | **6/7**（真实规模就绪实测 → D71） | **在用户开跑前把 Stage 6/7 真跑一遍**："
    "用 DDM 生成的 8 人 × 576 试次数据跑 `qc_group.py`（G1–G9 全 PASS、剔除 0）与 `analyze_pilot.py`"
    "（S1/S6 全 PASS、0 WARN），并量出逐被试判据的**复核负担**（5/8 人被标「待复核」，依据 S6-5 × 4 + S6-1 × 1）。 | "
    "`1_Code/DDM_Core/_scratch/_qc_group_n8.txt`、`_pilot_analysis_n8.txt`；`1_Code/Experiment/exp_Check/check_pilot_ready.py`（9/9） | "
    "等用户侧 Stage 1 实机验收与 Stage 6 Pilot |"
)
D71_CHANGELOG = (
    "| 2026-10-17 | **新增 D71：Stage 6/7 真实规模就绪实测**。用 D70 的生成器造 8 人 × 576 试次合法数据，"
    "跑通 `qc_group.py`（G1–G9 全 PASS、剔除 0）与 `analyze_pilot.py`（0 WARN）；"
    "并量出「合法数据上仍有 5/8 人被标待复核」的负担与机理，新建 `check_pilot_ready.py`（9/9）把它钉住。 |"
)
D71_APPENDIX = (
    "| `1_Code/Experiment/exp_Check/check_pilot_ready.py`（**新建**，9/9）+ `1_Code/DDM_Core/_scratch/_qc_group_n8.txt`"
    "（8 人质控日志：G1–G9 全 PASS、剔除 0、待复核 5）+ `_pilot_analysis_n8.txt`（Pilot 分析日志：0 WARN）"
    " + `_check_pilot_ready_console.txt` | 2026-10-17（D71） |"
)

# ---------------------------------------------------------------- Stage 6 §7.1
S6_71 = """
### 7.2 真实规模就绪实测（D71，2026-10-17）

Stage 6 的六条自测（§7）都是**小数据、非 DDM 生成**。为了让「脚本能跑」在真实规模上也有证据，用
`1_Code/DDM_Core/_scratch/_make_ddm_pilot.py --preset qc`（M-T1 真值 `rho = 0.8`、`QC_TRUTH`）生成
**8 人 × 576 试次**的 v4.1 数据（seed 31，5.2 s），然后跑 `analyze_pilot.py`：

| 读数 | 实测 | 判据 | 结果 |
|---|---|---|---|
| 正式段试次数 | 576 | S1-1（齐） | ✅ PASS |
| T/W 精度 | 6 位小数 | S1-1 | ✅ PASS |
| `RT < T` 比例 | 2.37% | S6-2c ≤ 20% | ✅ PASS |
| 刺激内按键比例 | 2.37% | S6-2c | ✅ PASS |
| timeout 最差单元 | 14.58% | S6-1 ≤ 40% | ✅ PASS |
| 注视期抢按 | 0% | S6-6 | ✅ PASS |
| 自洽矛盾行 | 0 | S6-3 | ✅ PASS |

**结论：0 项 WARN。** 同一批数据交给 `qc_group.py`（Stage 7 的组层判据）也是 G1–G9 全 PASS、剔除 0
（见 `Stage7_数据采集执行与质控方案.md` §6.3）。

⚠️ 但同一批数据在**被试层**留下了 5/8 人的「待复核」标记（S6-5 × 4、S6-1 × 1）—— 原因与处置见 §11 第 7 条。
"""

S6_LIMIT7 = (
    "7. **逐被试判据的「复核负担」是真实存在的**（D71 实测）：在 8 人合法 DDM 数据上，"
    "`analyze_pilot.py` 的逐被试裁决把 **5/8 人**标成「待复核」（4 人 S6-5 正确率 0.493–0.550 < 0.55、"
    "1 人 S6-1 最差单元 timeout 41.7% > 40%），而**组层判据全 PASS**。"
    "S6-1/S6-5 的分母（576 试次）与被试个体差异叠在一起时，边界会频繁触发：正确率跨被试 0.493–0.616，"
    "与 timeout 率（0.4%–18.4%）负相关 —— deadline 截断掉的更多是**慢错误**，所以「慢的被试」看起来正确率更高。"
    "**处置（不删判据、不放宽阈值）**：把「待复核」当**人工看一眼**的信号，不等于剔除；"
    "论文与质控报告里报「复核率」而不是「剔除率」。机器断言见 `1_Code/Experiment/exp_Check/check_pilot_ready.py`（9/9）。"
)

S6_CHANGELOG = "| v1.2 | 2026-10-17 | 新增 §7.1（真实规模就绪实测，D71）：8 人 × 576 试次 DDM 数据上 S1/S6 全 PASS、0 项 WARN；新增 §11 第 7 条（逐被试判据的复核负担与处置）。 |"

# ---------------------------------------------------------------- Stage 7 §6.3
S7_63 = """
### 6.3 真实规模就绪实测（D71，2026-10-17）

用 `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py --preset qc --n-subjects 8`（seed 31）生成的 8 人 × 576 试次
v4.1 数据跑本 Stage 的判据实现（`--expect-n 8`）：

| 判据 | 实测 | 结果 |
|---|---|---|
| G1 组内人数 | 8（`--expect-n 8`） | ✅ PASS |
| G2/G3 每单元试次数 | 576 | ✅ PASS |
| G4 T/W 精度 | 6 位小数 | ✅ PASS |
| G5 组层 timeout | 7.38% | ✅ PASS |
| G6 组层正确率 | 0.570 | ✅ PASS |
| G7 `RT < T` | 2.23% | ✅ PASS |
| G8 P 组映射 | 全 0 | ✅ PASS |
| G9 帧长一致 | 16.667 ms | ✅ PASS |
| 处置 | 剔除 **0**、待复核 **5** | — |

⚠️ 「待复核 5 人」的依据是**被试层**的 S6-5（4 人）与 S6-1（1 人）；组层全 PASS。
语义与处置见 `Stage6_Pilot方案.md` §11 第 7 条与本文档 §10 第 6 条。
"""

S7_LIMIT6 = (
    "6. **「待复核」不等于「剔除」，且合法数据上也会有复核负担**（D71 实测）：8 人合法 DDM 数据上"
    "`qc_group.py` 的组层判据全 PASS、剔除 0，但被试层仍有 5 人被标「待复核」。"
    "这两个标记在代码里本就不共用累加器（`check_pilot_ready.py` 的 P4 静态断言钉住），"
    "现场不得把「待复核」当剔除用，也不得为了让复核人数好看而放宽阈值。"
)

S7_CHANGELOG = "| v1.1 | 2026-10-17 | 新增 §6.3（真实规模就绪实测，D71）：8 人 × 576 试次合法数据上 G1–G9 全 PASS、剔除 0、待复核 5；新增 §10 第 6 条（复核负担与语义）。 |"

# ---------------------------------------------------------------- README §8.46
RM_846 = """### 8.46 Stage 6/7 的真实规模就绪实测（2026-10-17，D71）

1. **动机**：Stage 6 的六条自测与 Stage 7 的 `qc_group.py` 十例自测都是**小数据、非 DDM 生成**；
   「脚本能跑」在真实规模（8 人 × 576 试次）上从未被验过，而这是用户开跑前最后一道自证。
2. **做法**：用 D70 的生成器 `_make_ddm_pilot.py --preset qc --n-subjects 8`（seed 31，**5.2 s**）
   生成 v4.1 25 列 txt，跑 `qc_group.py --expect-n 8` 与 `analyze_pilot.py`。
3. **组层全绿**：`qc_group.py` 的 G1–G9 全 PASS（组层 timeout 7.38%、正确率 0.570、`RT < T` 2.23%、
   帧长 16.667 ms），**剔除 0**。
4. **被试层 0 WARN**：`analyze_pilot.py` 的 S1-1 与 S6-1…S6-6 全 PASS（`RT < T` 2.37%、刺激内 2.37%、
   timeout 最差单元 14.58%、注视期抢按 0%、自洽 0 行矛盾）。
5. ❗ **复核负担是真实存在的**：同一批合法数据上 **5/8 人**被标「待复核」
   （4 人 S6-5 正确率 0.493–0.550 < 0.55；1 人 S6-1 最差单元 timeout 41.7% > 40%）。
   机理：这两个判据本是**组层**口径，下沉到被试层后个体差异与 deadline 截断叠加
   （正确率跨被试 0.493–0.616，与 timeout 率 0.4%–18.4% **负相关** —— 截断掉的更多是慢错误）。
   处置：**不删判据、不放宽阈值**，把「待复核」当人工复核信号，报告里报「复核率」而非「剔除率」。
6. **牙齿**：`1_Code/Experiment/exp_Check/check_pilot_ready.py`（**9/9**）读两份落盘日志做 P1–P3 断言，
   并做 P4/P5 静态断言（`qc_group.py` 的待复核与剔除不共用累加器；`analyze_pilot.py` 仍把 S6-2c 与 S6-2 分开判）。
7. **未做**：真实某台机器上的帧长、真实被试的正确率分布、以及「待复核」在真实数据上的发生率 —— 三者都只能
   等 Stage 6/7 实跑，本节的数字来自 DDM 合成数据。
"""
RM_ITEM = (
    "| 55 | ✅ **Stage 6/7 的真实规模就绪实测（D71，§8.46）** | "
    "`_make_ddm_pilot.py --preset qc` 生成 8 人 × 576 试次 → `qc_group.py` G1–G9 全 PASS / 剔除 0、"
    "`analyze_pilot.py` 0 WARN；量出「待复核 5/8 人」的负担与机理；`check_pilot_ready.py` 9/9（2026-10-17） |"
)


def load(p: Path) -> list[str]:
    t = p.read_text(encoding="utf-8")
    assert "\r" not in t, f"{p.name} 含 CRLF"
    return t.split("\n")


def save(p: Path, lines: list[str], touched: int) -> None:
    if not APPLY:
        print(f"  [干跑] {p.name}：命中 {touched} 处")
        return
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"  [写入] {p.name}")


def idx_of(lines: list[str], needle: str) -> int:
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    assert len(hits) == 1, f"锚点命中 {len(hits)} 处：{needle[:60]}"
    return hits[0]


def ins_after(lines: list[str], needle: str, new: list[str], where: str) -> int:
    i = idx_of(lines, needle)
    n_pipe = lines[i].count("|")
    for row in new:
        assert row.count("|") == n_pipe, (
            f"{where}：新行竖线数 {row.count('|')} != 锚点 {n_pipe}")
    guard = not any(r in lines for r in new)
    if guard:
        lines[i + 1:i + 1] = new
        return 1
    print(f"  [跳过] {where}（已存在）")
    return 0


def replace_once(lines: list[str], old: str, new: str, where: str) -> int:
    hits = [i for i, ln in enumerate(lines) if old in ln]
    if not hits:
        assert any(new in ln for ln in lines), f"{where}：旧片段与目标片段都没有"
        print(f"  [跳过] {where}（已是目标状态）")
        return 0
    assert len(hits) == 1, f"{where}：旧片段命中 {len(hits)} 处"
    lines[hits[0]] = lines[hits[0]].replace(old, new)
    return 1


def do_master_plan() -> None:
    print(f"[主计划] {MP.relative_to(REPO)}")
    lines = load(MP)
    n = 0
    n += ins_after(lines, "| **D70** | 2026-10-17 |", [D71_DECISION], "§5 决策行")
    n += ins_after(lines, "| 2026-10-17 | **8**（正向对照：DDM 生成数据 → PPC 认不认得出 → D70） |",
                   [D71_PROGRESS], "§6 进度行")
    n += ins_after(lines, "| 2026-10-17 | **新增 D70：Stage 8 正向对照**", [D71_CHANGELOG], "§7 变更日志")
    n += ins_after(lines, "| `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`（**新建**，223 行）",
                   [D71_APPENDIX], "§8 附录证据")
    save(MP, lines, n)


def do_stage6() -> None:
    print(f"[Stage 6] {S6.relative_to(REPO)}")
    lines = load(S6)
    n = 0
    anchor = '2. **S6-5 的"过快"口径**：见 §5.2，短 T 下与 `RT < T` 循环重叠。'
    i = idx_of(lines, anchor)
    if S6_71.strip().split("\n")[0] in lines:
        print("  [跳过] §7.2（已存在）")
    else:
        lines[i + 1:i + 1] = [""] + S6_71.rstrip("\n").split("\n")
        n += 1
    n += ins_after(lines, "6. **S6-2c 的 20% 阈值沿用主计划给 S6-2 的阈值**", [S6_LIMIT7], "§11 第 7 条")
    n += ins_after(lines, "| v1.1 | 2026-10-14 | 补登 **S6-2b**", [S6_CHANGELOG], "§12 变更日志")
    save(S6, lines, n)


def do_stage7() -> None:
    print(f"[Stage 7] {S7.relative_to(REPO)}")
    lines = load(S7)
    n = 0
    anchor = "2. ❗ **空可用池会假通过**：`all(...)` 对空序列返回 `True`，"
    i = idx_of(lines, anchor)
    # 插在 §6.2 的两条教训之后（下一条是空行 + ---）
    j = i
    while j < len(lines) and not lines[j].startswith("---"):
        j += 1
    if S7_63.strip().split("\n")[0] in lines:
        print("  [跳过] §6.3（已存在）")
    else:
        lines[j:j] = S7_63.rstrip("\n").split("\n") + [""]
        n += 1
    n += ins_after(lines, "5. **`--no-subject-check` 会跳过 S1/S6**", [S7_LIMIT6], "§10 第 6 条")
    n += ins_after(lines, "| v1 | 2026-10-14 | 新建。把主计划 §3 Stage 7（L315–318）",
                   [S7_CHANGELOG], "§11 变更日志")
    save(S7, lines, n)


def do_readme() -> None:
    print(f"[README] {RD.relative_to(REPO)}")
    lines = load(RD)
    n = 0
    i = idx_of(lines, "## 9. 尚未做")
    if any(ln.startswith("### 8.46 Stage 6/7") for ln in lines):
        print("  [跳过] §8.46（已存在）")
    else:
        lines[i:i] = RM_846.rstrip("\n").split("\n") + [""]
        n += 1
    n += ins_after(lines, "| 54 | ✅ **Stage 8 的正向对照（D70，§8.45）** |", [RM_ITEM], "§9 第 55 项")
    save(RD, lines, n)


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}\n")
    do_master_plan()
    do_stage6()
    do_stage7()
    do_readme()
    print("\n完成。" + ("" if APPLY else "（干跑，未写盘；加 --apply 生效）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
