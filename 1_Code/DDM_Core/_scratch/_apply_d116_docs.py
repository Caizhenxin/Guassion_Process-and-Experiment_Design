"""D116：③ 设计空间优化（成本—精度前沿图）落纸。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
STAGE9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
FIGREADME = ROOT / "3_Figures" / "README.md"


def insert_after(lines: list[str], anchor_sub: str, new_line: str) -> list[str]:
    idx = [i for i, ln in enumerate(lines) if anchor_sub in ln]
    assert idx, f"锚点未找到：{anchor_sub}"
    i = idx[-1]
    want, got = lines[i].count("|"), new_line.count("|")
    assert got == want, f"列数不符（锚点 {want}，新行 {got}）：{new_line[:50]}"
    lines.insert(i + 1, new_line)
    return lines


DECISION = (
    "| **D116** | 2026-10-24 | **③ 设计空间优化收口：把 43 行排名表变成一张成本—精度前沿图**（关闭 Stage9 §13.4 第 1 条）。"
    "新建 `1_Code/Experiment/design_frontier.py`：读 `2_Data/Generate_Data/_design_search/design_search_{oracle,design}.csv`，"
    "按 1/√N 还原精度曲线，画三联图（① 精度 vs N ② 等预算前沿 + 帕累托 ③ 判据分解）。读数（oracle 口径、现行 P 方案）："
    "现行 `4T×3W r12` 需 **45 人 / 25,920 试次**；`4T×4W r9`（加 W=1400）需 **39 人 / 22,464 试次**（−6 人 −13%，**人均试次不变**）；"
    "`4T×2W r18` 需 40 人；`3T×3W r16` 48 人、`5T×2W r14` 50 人、`4T×3W W-wide` 51 人、`5T×3W r9` 53 人（都要多付试次）。"
    "30 人/组时 `beta_T` 相对 SE：现行 **12.2%**、`4T×4W r9` 11.3% ⇒ 交稿约束下只能报区间、不能报「达标」。"
    "三条结论：① **被试内设计（换 W/T 结构）的杠杆大于 P 方案**（P 方案只动 `beta_P` 6 人、`tau_P` 15–16 人；设计动 `beta_T` 45→39）；"
    "② 「加一个 W 水平（1400 ms）」是唯一**免费**的改进；③ 判据分解图显示卡住人数的一直是 `beta_T`，"
    "而在 design 组层真值下现行 P 方案的 `beta_P`/`tau_P` 直接**不可识别**（与 D109 一致）。"
    "**处置**：不推翻 D109（交稿前不改采集程序），本图只把「如果还能改设计，改哪个最便宜」写成可查的一页，进论文方法章的设计论证一节。 | "
    "用户 2026-10-24「都同意了，你继续就行」批准执行 ③；Stage9 §13.4 第 1 条「把 §13.2 的表画成图」一直挂着 | "
    "`1_Code/Experiment/design_frontier.py`（**新建**）+ `3_Figures/_design/fig10_design_frontier.png` + "
    "`2_Data/Generate_Data/_design_search/design_frontier.csv` + Stage9 **§14**（新增） |"
)

PROGRESS = (
    "| 2026-10-24 | **14（③ 设计空间优化 → D116）** | **收口了**：43 行排名表 → 一张成本—精度前沿图（三联）。"
    "关键读数：加一个 W 水平（1400 ms）⇒ 45→39 人且**人均试次不变**；加重复/加 T 水平要多付 14–18% 试次；"
    "30 人/组时 `beta_T` ≈ 12.2%（现行）⇒ 只能报区间。Stage9 §13.4 第 1 条关闭。 | 用户 2026-10-24 批准执行 ③ | "
    "`1_Code/Experiment/design_frontier.py` + `3_Figures/_design/fig10_design_frontier.png` + Stage9 §14 |"
)

CHANGELOG = (
    "| 2026-10-24 | **新增 D116（③ 成本—精度前沿图）**：`design_frontier.py` 读 design_search 两个 CSV，按 1/√N 还原精度，"
    "出三图（精度 vs N / 等预算帕累托 / 判据分解）；`design_search` 的 CSV/MD 一并从 `5_Reference/03_论文写作/figures_sim/` "
    "迁到 `2_Data/Generate_Data/_design_search/`。读数：现行 45 人 vs 加 W 水平 39 人（试次不变）；30 人/组 `beta_T` 12.2%；"
    "Stage9 §14、§13.4 第 1 条关闭。 |"
)

EVIDENCE = (
    "| `1_Code/Experiment/design_frontier.py` + `3_Figures/_design/fig10_design_frontier.png` + "
    "`2_Data/Generate_Data/_design_search/design_frontier.csv` | D116 证据：① 精度曲线（7 种被试内设计，`beta_T` 相对 SE vs N）、"
    "② 等预算前沿（人均 540–576 试次，总试次 22.4k–29.4k）、③ 判据分解（`beta_T` 43 vs `beta_P` 9 vs `tau_P` 8） |"
)

README_ROW = (
    "| 97 | ✅ **③ 成本—精度前沿图（D116）** | `1_Code/Experiment/design_frontier.py` 把 `design_search` 的 43 行排名表画成三联图"
    "（精度 vs N / 等预算前沿 + 帕累托 / 判据分解），输出 `3_Figures/_design/fig10_design_frontier.png` 与 "
    "`2_Data/Generate_Data/_design_search/design_frontier.csv`。读数（oracle）：现行 `4T×3W r12` **45 人 / 25.9k 试次**；"
    "`4T×4W r9`（加 W=1400）**39 人 / 22.5k 试次**且人均试次不变（−13%）；加重复或加 T 水平都要多付 14–18% 试次。"
    "30 人/组时 `beta_T` 相对 SE 12.2%（现行）/ 11.3%（加 W）⇒ 交稿约束下报区间而非「达标」。design 组层真值下现行 P 方案的 "
    "`beta_P`/`tau_P` 仍不可识别（与 D109 一致） |"
)

SEC14 = """
## 14. 成本—精度前沿图（D116，关闭 §13.4 第 1 条）

**问题**：§13.2 那张 43 行的排名表能查，但不能决策。真正要回答的是三件事——
①「加条件 / 加重复 / 加人」哪个便宜？② 30 人/组时我在前沿的哪个位置？③ 卡住人数的到底是谁？

**产物**：`1_Code/Experiment/design_frontier.py` → `3_Figures/_design/fig10_design_frontier.png`
（数据 `2_Data/Generate_Data/_design_search/design_frontier.csv`；精度按 1/√N 从 `rel_beta_T` 还原）

### 14.1 读数（组层真值 = oracle、P 方案 = 现行 `0/8/32/120`）

| 被试内设计 | 人均试次 | 达到 `beta_T`≤10% 需人数 | 总试次 | 相对现行 |
|---|---|---|---|---|
| `4T×4W r9`（加 W=1400） | 576 | **39** | 22,464 | **−6 人 / −13%，人均试次不变** |
| `4T×2W r18`（省 W） | 576 | 40 | 23,040 | −5 人 |
| **`4T×3W r12`（现行）** | 576 | **45** | 25,920 | — |
| `3T×3W r16`（省一个 T） | 576 | 48 | 27,648 | +3 人 |
| `5T×2W r14`（窄 W 换 T） | 560 | 50 | 28,000 | +5 人 |
| `4T×3W r12 W-wide` | 576 | 51 | 29,376 | +6 人 |
| `5T×3W r9`（加 T=200） | 540 | 53 | 28,620 | +8 人 |

30 人/组时的 `beta_T` 相对 SE：`4T×4W r9` **11.3%**、`4T×2W r18` 11.5%、现行 **12.2%**、其余 12.6–13.2%。

### 14.2 三条结论

1. **被试内设计的杠杆比 P 方案大。** P 方案换来换去只动 `beta_P`（6→4 人）和 `tau_P`（15→11 人），
   始终远低于 `beta_T`；真正压低总人数的是被试内结构（45 → 39）。
2. **「加一个 W 水平（1400 ms）」是唯一免费的改进**：人均试次不变（576），人数少 6（−13%）。
   加重复（`r12→r18`）或加 T 水平都要多付 14–18% 试次，反而更贵。
3. **30 人/组落在判据线上方 2 个百分点**（12.2% vs 10%）。这个差距是「区间宽度」而不是「研究没意义」——
   与 D109 的口径一致：报区间、报效应量，不报「达标/显著」。

### 14.3 与 D109 的关系

D109 已决定**交稿前不改采集程序**（保留 `0/8/32/120`、30 人/组规划）。本图**不推翻**它，只把
「如果还能改设计，改哪个最便宜」做成可查的一页，进论文方法章的设计论证；§13.4 第 1 条（"把表画成图"）据此关闭。
"""


def main() -> int:
    plan = PLAN.read_text(encoding="utf-8").split("\n")
    if any("**D116**" in ln for ln in plan):
        print("[skip] 主计划已有 D116")
    else:
        plan = insert_after(plan, "| **D115** | 2026-10-24 |", DECISION)
        plan = insert_after(plan, "**13（练习 × SPE 与工程口径 → D115）**", PROGRESS)
        plan = insert_after(plan, "**新增 D115（图文数据三分 + λ 天花板敏感性）**", CHANGELOG)
        plan = insert_after(plan, "`1_Code/Experiment/practice_lambda.py` + `3_Figures/_practice/fig9_practice_lambda.png`",
                            EVIDENCE)
        PLAN.write_text("\n".join(plan), encoding="utf-8", newline="\n")
        print(f"主计划：{len(plan)} 行")

    rd = README.read_text(encoding="utf-8").split("\n")
    if any("**③ 成本—精度前沿图（D116）**" in ln for ln in rd):
        print("[skip] README 已有第 97 项")
    else:
        rd = insert_after(rd, "| 96 | ✅ **图文数据三分 + λ 天花板敏感性（D115）**", README_ROW)
        README.write_text("\n".join(rd), encoding="utf-8", newline="\n")
        print(f"README：{len(rd)} 行")

    s9 = STAGE9.read_text(encoding="utf-8")
    if "## 14. 成本—精度前沿图" in s9:
        print("[skip] Stage9 已有 §14")
    else:
        s9 = s9.rstrip("\n") + "\n" + SEC14
        STAGE9.write_text(s9, encoding="utf-8", newline="\n")
        print(f"Stage9：{len(s9.split(chr(10)))} 行")

    fr = FIGREADME.read_text(encoding="utf-8")
    row = ("| `_design/` | `fig10_design_frontier` 成本—精度前沿（三联） | "
           "`python 1_Code/Experiment/design_frontier.py` | "
           "`2_Data/Generate_Data/_design_search/design_frontier.csv` |\n")
    if "fig10_design_frontier" in fr:
        print("[skip] 3_Figures README 已有 fig10")
    else:
        anchor = "| `_practice/` |"
        i = fr.index(anchor)
        j = fr.index("\n", i) + 1
        fr = fr[:j] + row + fr[j:]
        FIGREADME.write_text(fr, encoding="utf-8", newline="\n")
        print("3_Figures/README 已加 fig10 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
