# -*- coding: utf-8 -*-
"""D91：把「不加无掩蔽对照」的裁定与理由落纸（幂等、逐处断言命中 1 次）。

落纸位置：
  1. 5_Reference/08_工作流/工作流_主计划.md          —— 决策表 D91 行 + 进度行 + 变更日志行
  2. 5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md —— §7 待确认表第 ⑨ 行（已裁定）
  3. 1_Code/DDM_Core/README.md                      —— §8.62 + §9 第 75 项
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
DESIGN = ROOT / "5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md"
README = ROOT / "1_Code/DDM_Core/README.md"


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def write(p: Path, lines: list[str]) -> None:
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def insert_after(lines: list[str], prefix: str, new: list[str], tag: str) -> list[str]:
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, f"{tag}: 期望命中 1 次，实际 {len(hits)} 次（prefix={prefix!r}）"
    i = hits[0]
    return lines[: i + 1] + new + lines[i + 1 :]


# ---------------------------------------------------------------- 主计划
D91 = (
    "| **D91** | 2026-10-18 | ✅ **不加无掩蔽对照：掩蔽是范式常量，不是待估因子**。"
    "① 用户问「是否有必要全部都有掩蔽、要不要新增几组无掩蔽做对比」；"
    "② 模型侧：`1_Code/DDM_Core/twophase.py:5-8` 的两阶段相位边界在 **T（刺激 offset）**，"
    "掩蔽 200 ms 只作设计约束（`1_Code/DDM_Core/design_grid.py:75 MASK = 0.200`、`:193` 硬约束 `W > T + MASK`），"
    "似然里**没有 M 参数**；掩蔽效力被 `rho` 吸收，`rho = 1` 正好退化为单阶段（`twophase.py:15-17`）"
    "⇒ 加对照不是「让参数可估」的需要；"
    "③ 可识别性已有（n=30/档，`H0: rho=1`）：rho=0 → 96.7%、0.5 → 40.0%、0.75 → 16.7%"
    "（`正式采集_候选设计_v2_定稿.md` §3.1）；"
    "④ 无掩蔽组能换到的三件事（同一 T 下的直接因果对照 / 检验「rho 与 T 无关」 / 论文泛化性声明）"
    "都不进主估计量 P\\|T\\|W → SPE；"
    "⑤ 代价：24 格 × 24 试次 ⇒ 每格减半、SE ×1.41（`delta_a` 条件 SE 30.8% → ~43.5%，恰好削弱 W 那条最重要的结论）；"
    "或 24 格 × 48 = 1152 试次 ≈ 33 min，超出现场 17 min 预算；或被试间 M 使 N 从 160 翻到 320；"
    "⑥ 历史数据无免费对照：`2_Data/Real_Data/UnExtact/emp_data` 87 份 CSV 的 `groupID` 只有 1/2/3/4/5/6/8/9，"
    "**0 例 group 7（无掩蔽）**；旧程序 `1_Code/Experiment/exp_matlab/test/experiment_formal_newcon.m:398-424` "
    "每个试次无条件画掩蔽（`:419 maskDuration = 0.2`）；"
    "⑦ **用户裁定（2026-10-18）：不加**——主设计保持 12 格全掩蔽；论文限制节写明「SPE 在 200 ms 噪声掩蔽、"
    "33–250 ms 短呈现范式下测得（沿用 Sui et al., 2012）」；若日后审稿要求，另做独立小验证"
    "（2 个 T × {噪声掩蔽, 空白 200 ms} × W=1800，96 试次/人、约 12 min），该变体程序**尚不存在**"
    "（现有程序无 M 开关） | `5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md` §7 第 ⑨ 行；"
    "`1_Code/DDM_Core/README.md` §8.62 | 主设计不动；Stage 6 Pilot 照原计划 |"
)

PROGRESS = (
    "| 2026-10-18 | **6（Pilot 前）** | 掩蔽对照取舍（D91）：不加无掩蔽组，掩蔽效力交给 `rho` 与论文限制节；"
    "另把手册 docx 重生成（WPS 释放后）⇒ `check_manual_d4.py` 回到 40/40 | "
    "`正式采集_候选设计_v2_定稿.md` §7-⑨、`1_Code/DDM_Core/README.md` §8.62 | "
    "Stage 6 Pilot（N≈8，真被试，v4.7） |"
)

CHANGELOG = (
    "| 2026-10-18 | **新增 D91（不加无掩蔽对照）**：用户裁定主设计保持 12 格全掩蔽。理由："
    "`twophase.py:5-8` 相位边界在 T、似然无 M 参数、掩蔽效力由 `rho` 吸收；`rho` 检验力已有"
    "（0 → 96.7%、0.5 → 40.0%、0.75 → 16.7%）；加对照的代价是 SE ×1.41 或 33 min 场次；"
    "87 份历史 CSV 无 group 7 ⇒ 无免费对照。落纸：设计文档 §7-⑨、README §8.62 + §9 第 75 项 |"
)

lines = read(PLAN)
lines = insert_after(lines, "| **D90** |", [D91], "主计划 D91")
lines = insert_after(lines, "| 2026-10-18 | **1 → 6**", [PROGRESS], "主计划 进度行")
lines = insert_after(lines, "| 2026-10-18 | 新增 **D90**", [CHANGELOG], "主计划 变更日志")
write(PLAN, lines)

# ---------------------------------------------------------------- 设计文档 §7
ROW9 = (
    "| **⑨** | ✅ **是否新增「无掩蔽」对照？已裁定：不加（D91，2026-10-18）** | "
    "模型里没有 M 参数（`twophase.py:5-8` 相位边界在 T；掩蔽 200 ms 只是设计约束），"
    "掩蔽效力由 `rho` 吸收；加对照只买「直接因果对照 / rho×T 假设检验 / 泛化性声明」三项，都不进主估计量；"
    "代价是每格试次减半（SE ×1.41）或场次翻倍到 33 min；87 份历史 CSV 无 group 7 ⇒ 无免费对照 | "
    "主设计不动；论文限制节写明「200 ms 噪声掩蔽、33–250 ms 短呈现」范式；"
    "需要泛化声明时另做 12 min 独立小验证（2 个 T × {掩蔽, 空白} × W=1800），该变体程序尚不存在 |"
)

lines = read(DESIGN)
lines = insert_after(lines, "| **⑧** |", [ROW9], "设计文档 §7-⑨")
write(DESIGN, lines)

# ---------------------------------------------------------------- README §8.62 + §9-75
S862 = [
    "### 8.62 掩蔽要不要做成因子：不做（2026-10-18，D91）",
    "",
    "**问题**：主设计 12 个 (T,W) 单元全部带 200 ms 噪声掩蔽。要不要新增几组「无掩蔽」做对照，"
    "以证明 SPE 不是掩蔽造出来的？",
    "",
    "**模型侧的事实（决定性的那一条）**：`1_Code/DDM_Core/twophase.py:5-8` 的两阶段漂移相位边界在 "
    "**T（刺激 offset）**：`d(t) = d_stim(T)`（0 ≤ t ≤ T）、`d(t) = rho · d_stim(T)`（t > T）。"
    "掩蔽 200 ms 只作为**设计约束**出现（`1_Code/DDM_Core/design_grid.py:75 MASK = 0.200`、"
    "`:193` 硬约束 `W > T + MASK`），**似然里没有任何 M 参数**；掩蔽效力被 `rho` 吸收，"
    "`rho = 1` 正好退化为单阶段（`twophase.py:15-17`）⇒ 加无掩蔽组不是「让参数可估」的需要。",
    "",
    "**可识别性已经有**（n=30/档，`H0: rho = 1`）：rho=0 → 96.7%、0.5 → 40.0%、0.75 → 16.7%"
    "（`5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md` §3.1）。",
    "",
    "**无掩蔽组能换到的三件事**（按价值排）：① 同一 T、同 W 下的直接因果对照；"
    "② 检验模型「rho 与 T 无关」这条假设；③ 论文的泛化性声明。三者都**不进主估计量** P|T|W → SPE。",
    "",
    "**代价**：24 格 × 24 试次 ⇒ 每格减半、SE ×1.41（`delta_a` 条件 SE 30.8% → ~43.5%，"
    "恰好削弱 W 那条最重要的结论）；或 24 格 × 48 = 1152 试次 ≈ 33 min，超出现场 17 min 预算；"
    "或被试间 M 使 N 从 160 翻到 320。",
    "",
    "**历史数据没有免费对照**：`2_Data/Real_Data/UnExtact/emp_data` 87 份 CSV 的 `groupID` 只出现 "
    "1/2/3/4/5/6/8/9，**0 例 group 7（D38 记的「无掩蔽」组）**；旧程序 "
    "`1_Code/Experiment/exp_matlab/test/experiment_formal_newcon.m:398-424` 每个试次无条件画掩蔽"
    "（`:419 maskDuration = 0.2`）。",
    "",
    "**裁定（2026-10-18，用户）**：不加。主设计保持 12 格全掩蔽；论文限制节写明"
    "「SPE 在 200 ms 噪声掩蔽、33–250 ms 短呈现范式下测得（沿用 Sui et al., 2012）」；"
    "若日后审稿要求，另做独立小验证（2 个 T × {噪声掩蔽, 空白 200 ms} × W=1800，96 试次/人、约 12 min），"
    "该变体程序**尚不存在**（现有程序无 M 开关）。",
    "",
    "**教训**：先问「这个因子进不进模型的似然」。进，就必须有对照；不进，对照只能买泛化声明与假设检验，"
    "价格要按它对主估计量的伤害来算。",
    "",
]

ITEM75 = (
    "| 75 | ✅ **掩蔽要不要做成因子：不做（D91，§8.62）** | `twophase.py:5-8` 的相位边界在 T、"
    "似然里没有 M 参数、掩蔽效力由 `rho` 吸收；加无掩蔽组只买泛化声明，代价是 SE ×1.41 或 33 min 场次；"
    "87 份历史 CSV 无 group 7 ⇒ 无免费对照 |"
)

lines = read(README)
hits = [i for i, ln in enumerate(lines) if ln.startswith("## 9. 尚未做")]
assert len(hits) == 1, f"README ## 9 命中 {len(hits)} 次"
lines = lines[: hits[0]] + S862 + lines[hits[0] :]
lines = insert_after(lines, "| 74 |", [ITEM75], "README §9-75")
write(README, lines)

print("D91 落纸完成：主计划（决策行 + 进度行 + 变更日志）、设计文档 §7-⑨、README §8.62 + §9-75")
