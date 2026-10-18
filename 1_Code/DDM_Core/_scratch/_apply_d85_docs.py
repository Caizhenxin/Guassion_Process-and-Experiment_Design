# -*- coding: utf-8 -*-
"""D85 落纸：首场真实数据把 Stage 6/7 的门走了一遍 + S6-5 阈值改成两级（有历史锚点）。

六处改动，全部幂等：每处锚点断言命中恰好 1 次；写回一律 `newline="\\n"`。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
STAGE6 = REPO / "5_Reference" / "08_工作流" / "Stage6_Pilot方案.md"
STAGE7 = REPO / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md"
README = REPO / "1_Code" / "DDM_Core" / "README.md"

D85_ROW = (
    "| **D85** | 2026-10-18 | ✅ **第一场真实数据把 Stage 6/7 的门完整走了一遍：链路全通；"
    "S6-5 的两条阈值被 87 份历史真人数据证明会误伤（36% / 17%），改成两级**。"
    "① 触发：v4.5 那场 60 Hz 数据（576 正式试次）过 `read_formal_data.py` ✅、`qc_group.py` G1–G9 全 PASS、"
    "剔除 0，`analyze_pilot.py` 的 S1-1 / S1-1b / S6-2c（3.40%）/ S6-3 ✅；"
    "但 **S6-1**（timeout 23.4%、最差单元 43.8%）与 **S6-5**（RT 中位 0.069 s、过快 56.2%）FAIL ⇒ "
    "必须先回答「是数据坏了还是判据错了」。"
    "② 新建 `1_Code/Experiment/analyze_rt_baseline.py`，在 `2_Data/Real_Data/UnExtact/emp_data` 的 **87 份真人逐被试文件**上复算同一口径："
    "RT 中位 0.234–0.977 s（0.30 s 下限判掉 **15/87 = 17.2%**）、正确率 0.431–0.988（0.55 下限判掉 **31/87 = 35.6%**）、"
    "过快 **0/87** 份非零、漏答 1.2%–88.7%。"
    "③ 结论：这场是**主试按键的试跑**，不是被试——按 T 分档的正确率四条全在 **0.477 / 0.487 / 0.495 / 0.477**（= 机会水平 0.5，"
    "说明完全没有用到刺激信息），RT 中位 0.069 s 在 87/87 份历史真人里排 **P0**（最快的真人是 0.234 s）。"
    "④ 改法：S6-5 的 **FAIL** 线移到「历史真人从未出现」的位置（`RT 中位 < 0.20 s`、`正确率 < 0.45` 或 `> 0.995`、`过快 > 10%`），"
    "`0.20–0.30 s` / `0.45–0.55` / `0.98–0.995` 只给 **WARN**（历史真人分别占 15/87、31/87）。"
    "⑤ 不改 S6-1：timeout 23.4% 是同一场乱按的副产物，且没有历史锚点支持放宽。"
    "⑥ 顺带抓出**第三个**写死制表符的工具 `1_Code/Experiment/analyze_pilot.py:86`（D83b/D83c 的同一个 bug 的第三处）"
    "——它把逗号 CSV 整行读成 1 列、进而报「跳过 1 个旧版 16 列文件」；改成首行嗅探后 25 列正常识别。 | "
    "`1_Code/Experiment/analyze_rt_baseline.py`（**新建**，零依赖）；`analyze_pilot.py` 511 → **529 行**（两级裁决 + 嗅探）；"
    "`Stage6_Pilot方案.md` §5 表 + **新增 §5.3 阈值的历史锚点**；`Stage7` §6 工具链补一行；README §8.58 + §9 第 69 项。 | "
    "这场按「试跑」处理、**不计入** Pilot 的 N=8；用 v4.6 在 60.004 Hz 机器上找**没看过实验**的人跑第一场真 Pilot。 |\n"
)

D85_PROGRESS = (
    "| 2026-10-18 | **新增 D85（首场真实数据 + S6-5 阈值锚点）**：`analyze_rt_baseline.py` 在 87 份历史真人数据上复算 ⇒ "
    "0.55 正确率线误伤 31/87、0.30 s RT 线误伤 15/87、过快线 0/87；S6-5 改两级（FAIL 线移到历史从未出现处）；"
    "抓出第三个写死制表符的工具（`analyze_pilot.py:86`）；Stage6 新增 §5.3；README §8.58 + §9-69。 |\n"
)

D85_FILE = (
    "| `1_Code/Experiment/analyze_rt_baseline.py`（**新建**，D85） | **S6-5 三条阈值的历史锚点工具**（零依赖）："
    "在 `2_Data/Real_Data/UnExtact/emp_data` 的 87 份真人逐被试文件上复算 RT 中位 / 正确率 / 过快（`RT ≥ T` 口径）/ 漏答率的分布，"
    "并报告每个阈值会判掉多少份历史真人；给了 `--session` 时把待评场次放进参照分布报百分位。"
    "阈值本身写在 `analyze_pilot.py`，本工具只提供证据。 |\n"
)

S6_5_OLD = ("| **S6-5** | 正确率 / RT 中位 / 过快比例（**过快口径：只在 `RT ≥ T` 的试次里算**） | "
            "**0.55–0.98 / 0.3–2.0 s / ≤ 10%** | **FAIL** ⇒ 任务太难或被试在乱按 |")
S6_5_NEW = ("| **S6-5** | 正确率 / RT 中位 / 过快比例（**过快口径：只在 `RT ≥ T` 的试次里算**） | "
            "**正确率**：`< 0.45` 或 `> 0.995` ⇒ FAIL，`0.45–0.55` / `0.98–0.995` ⇒ WARN；"
            "**RT 中位**：`< 0.20 s` 或 `> 2.0 s` ⇒ FAIL，`0.20–0.30 s` ⇒ WARN；"
            "**过快** `> 10%` ⇒ FAIL。PASS 带：正确率 0.55–0.98、RT 中位 ≥ 0.30 s | "
            "**FAIL** ⇒ 乱按或没在用刺激（见 §5.3 的历史锚点）；**WARN** ⇒ 落在历史真人常见带内，人看一眼 |")

S5_3 = """
### 5.3 这三条阈值从哪来：87 份历史真人数据的锚点（D85，2026-10-18）

S6-5 的 `0.55` / `0.30 s` / `10%` 一开始是**判断**，不是数据推出来的。第一场真实场次把它们顶到台面上（S6-5 FAIL），
所以补了校准：`1_Code/Experiment/analyze_rt_baseline.py` 在 `2_Data/Real_Data/UnExtact/emp_data` 的
**87 份真人逐被试文件**上复算同一口径。

| 量 | min | q05 | 中位 | q95 | max | 原阈值会判 FAIL |
|---|---|---|---|---|---|---|
| RT 中位（s） | 0.234 | 0.236 | 0.552 | 0.877 | 0.977 | **15/87 = 17.2%**（`< 0.30`） |
| 正确率（已响应内） | 0.431 | 0.451 | 0.645 | 0.941 | 0.988 | **31/87 = 35.6%**（`< 0.55`） |
| 过快（`RT ≥ T` 口径） | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **0/87 = 0%** |
| 漏答率（占正式试次） | 0.012 | 0.022 | 0.256 | 0.792 | 0.887 | —（S6-1 另有判据） |

**读法（三条都要记住）**：

1. **正确率 `0.55` 会判掉三分之一的真人数据**——旧设计最短 T 档只有 30 ms，正确率本来就贴着机会水平。
   这条线是**筛查器**，不是判决器。
2. **RT 中位 `0.30 s` 也偏高**：旧设计的 `RT` 下限被「掩蔽期不读队列」这条物理限制抬到 `T + 200 ms ≈ 0.23 s`；
   新设计（v4.6 在刺激期内读队列）下限更低，所以 `0.30 s` **不能**当生理下界用。
3. **唯独「过快 > 10%」在 87 份真人里一次都没触发**（历史最小 RT 中位 0.234 s）⇒ 它对「乱按」零误伤，
   是这三条里最硬的一条。

因此 S6-5 改成两级：**FAIL** 线落在历史真人**从未出现**的位置（`RT 中位 < 0.20 s`、`正确率 < 0.45` 或 `> 0.995`、
`过快 > 10%`）；`0.20–0.30 s` / `0.45–0.55` / `0.98–0.995` 只给 **WARN**（"要人看一眼"，历史真人分别占 15/87、31/87）。

⚠️ 参照集是 **D4 之前**的设计（T/W 取值不同、无掩蔽），只能校准「像不像人在做任务」的量级，
**不能**当作新设计的性能预期（新设计 T 最长 250 ms、掩蔽 200 ms，正确率本就该更高）。

**这场试跑的判读示例**（可以直接照此读）：RT 中位 `0.069 s` ⇒ P0（87/87 份真人比它慢）；过快 `56.17%` ⇒ P100（真人 0/87）；
按 T 分档正确率 `0.477 / 0.487 / 0.495 / 0.477` ⇒ 四条都贴着 0.5，说明**没有用到刺激信息**，
而不是「任务太难」（太难会随 T 变长明显回升）。
"""

STAGE7_ROW = (
    "| `1_Code/Experiment/analyze_rt_baseline.py`（**新建**，D85） | S6-5 三条阈值的**历史锚点**：在 87 份真人数据上"
    "复算 RT 中位 / 正确率 / 过快 / 漏答的分布，报每个阈值会判掉多少份真人，并给待评场次的百分位。"
    "判据本身不在这里（在 `analyze_pilot.py`），本工具只出证据。 |\n"
)

README_858 = """
### 8.58 阈值是从哪来的：87 份历史真人数据把 S6-5 的两条线顶翻了（2026-10-18，D85）

1. **现象**：第一场真实数据（576 试次、60 Hz、v4.5）走完 Stage 6/7 全链路——`read_formal_data.py` ✅、
   `qc_group.py` G1–G9 全 PASS 且剔除 0、`analyze_pilot.py` 的 S1-1 / S1-1b / S6-3 / S6-2c ✅；
   但 **S6-1**（timeout 23.4%、最差单元 43.8%）与 **S6-5**（RT 中位 0.069 s、过快 56.2%）FAIL。
   于是问题变成：**是数据坏了，还是判据错了？**
2. **做法**：新建 `1_Code/Experiment/analyze_rt_baseline.py`（零依赖），把 S6-5 关心的四个量在
   `2_Data/Real_Data/UnExtact/emp_data` 的 **87 份真人逐被试文件**上重算一遍，并统计每个阈值会判掉多少份真人。
3. **三个数字**：正确率 `0.55` 下限判掉 **31/87 = 35.6%**（历史 q05 = 0.451）；RT 中位 `0.30 s` 下限判掉
   **15/87 = 17.2%**（历史 min = 0.234 s）；「过快 > 10%」**0/87**（历史真人这份数据里一个都没有）。
4. **改法**：S6-5 改两级——**FAIL** 线放在「历史真人从未出现」的位置（`RT 中位 < 0.20 s`、`正确率 < 0.45` 或 `> 0.995`、
   `过快 > 10%`），模糊带 `0.20–0.30 s` / `0.45–0.55` / `0.98–0.995` 只 WARN。
   改完这一场**仍然 FAIL**（0.069 s < 0.20 s、56.17% > 10%）⇒ 这次调整不是为了让数据过关。
5. **这一场到底是什么**：按 T 分档正确率 `0.477 / 0.487 / 0.495 / 0.477`——四条都贴着机会水平 0.5，
   且**不随 T 变长而回升**（"任务太难"会回升）；RT 中位 0.069 s 在 87 份真人里排 **P0**。
   ⇒ 是**主试按键的试跑**，不是被试数据；按「试跑」处理、不计入 Pilot 的 N=8。
6. **顺带抓出的第三个制表符 bug**：`1_Code/Experiment/analyze_pilot.py:86` 也是 `split("\\t")` 写死，
   传逗号 CSV 时整行读成 1 列 ⇒ 表头退化成 `col1` ⇒ 报「跳过 1 个旧版 16 列文件 / 没有任何 25 列数据文件」。
   D83b（`check_stage1_acceptance.py`）、D83c（`read_formal_data.py`）改的是前两处，这是**第三处**；
   同一处修法（首行嗅探 + `csv.reader`）已套用。**教训：凡是读产物的工具，都必须先确认它认哪种分隔符。**
7. **边界**：参照集是 D4 之前的设计（T/W 不同、无掩蔽），只能校准「像不像人在做任务」；`RT 中位` 在旧设计里
   被「掩蔽期不读队列」抬到 `T + 200 ms`，新设计下限更低 ⇒ `0.30 s` 不能当生理下界。
"""

README_ITEM = (
    "| 69 | ✅ **S6-5 阈值的 87 份历史真人锚点 + 首场真实数据过门（D85，§8.58）** | "
    "正确率 0.55 线误伤 31/87 = 35.6%、RT 中位 0.30 s 线误伤 15/87 = 17.2%、过快线 0/87；"
    "S6-5 改两级（FAIL 线 = 历史从未出现处），改完这一场仍 FAIL；抓出第三个写死制表符的工具。 |\n"
)


def apply_replace(path: Path, old: str, new: str, tag: str) -> None:
    text = path.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        sys.exit(f"[FAIL] {tag}: 命中 {n} 次（应为 1）")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[OK] {tag}")


def insert_after(path: Path, pred, new_text: str, tag: str) -> None:
    lines = path.read_text(encoding="utf-8").split("\n")
    idx = [i for i, ln in enumerate(lines) if pred(ln)]
    if len(idx) != 1:
        sys.exit(f"[FAIL] {tag}: 锚点命中 {len(idx)} 次（应为 1）")
    i = idx[0]
    lines[i + 1:i + 1] = new_text.rstrip("\n").split("\n")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[OK] {tag}（插在第 {i + 1} 行之后）")


def main() -> int:
    insert_after(PLAN, lambda s: s.startswith("| **D84** |"), D85_ROW, "主计划 D85 决策行")
    insert_after(PLAN, lambda s: s.startswith("| 2026-10-18 | **新增 D84"),
                 D85_PROGRESS, "主计划 D85 进度行")
    insert_after(PLAN, lambda s: s.startswith("| `1_Code/Experiment/analyze_pilot.py`（新建）"),
                 D85_FILE, "主计划 §8 文件行")
    apply_replace(STAGE6, S6_5_OLD, S6_5_NEW, "Stage6 S6-5 阈值行")
    insert_after(STAGE6, lambda s: s.startswith("同一个理由：短 T 下 `RT < 0.15 s` 是设计使然"),
                 S5_3, "Stage6 新增 §5.3")
    insert_after(STAGE7, lambda s: s.startswith("| `1_Code/Experiment/exp_Check/check_consent_pack.py`"),
                 STAGE7_ROW, "Stage7 工具链补一行")
    insert_after(README, lambda s: "### 8.57 `onset` 之前的按键" in s,
                 README_858, "README §8.58")
    insert_after(README, lambda s: s.startswith("| 68 | ✅"),
                 README_ITEM, "README §9 第 69 项")

    for p in (PLAN, STAGE6, STAGE7, README):
        t = p.read_text(encoding="utf-8")
        print(f"[LINE] {p.name} = {len(t.splitlines())} 行, CRLF={t.count(chr(13))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
