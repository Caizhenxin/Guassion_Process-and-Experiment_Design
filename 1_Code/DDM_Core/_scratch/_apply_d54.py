# -*- coding: utf-8 -*-
"""把决策 D54 写进 `5_Reference/08_工作流/工作流_主计划.md`（四处插入 + 一处就地更正）。

**D54 的内容**：冻结 Objective 的标量 `J` 的噪声被**遗漏率罚分 (C)** 支配 —— 实测
`sd_C²/sd_J²` = **95–101%**（`n_fim = 1/2/4/8` 四档），而科学信号 (A)/(B) 只贡献约 0；
根因是 (C) 的斜率 `dC/d(omission) ≈ 125`（在 D4 的遗漏率 0.35 处）把遗漏率的 MC 噪声
（`sd ≈ 0.006–0.014`）放大成 `sd_C ≈ 0.8–1.8`。⇒ **罚分改为约束**（带外直接剔除），
**任何基于 `J` 的臂间比较都不可解释**；四路消融只能建立在 (A)/(B) 上。

体例同 `_apply_d47`–`_apply_d53`：前缀定位 + 分隔符断言 + 断表断言 + 幂等守卫 +
**只插一行时绝不触碰空行** + 输出必须以换行结尾。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d54.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d54.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path("5_Reference/08_工作流/工作流_主计划.md")

# 就地更正：D53 写下的"仍开放"里，第 (2) 件的措辞要按 D54 的实测收紧
STALE = ("**(2)** 重复整个消融（R 个种子组）以得到配对误差棒 —— 在那之前不得宣称"
         "「BO 优于随机/网格」")
FIXED = ("**(2)** 重复整个消融（R 个种子组）以得到配对误差棒 —— 在那之前不得宣称"
         "「BO 优于随机/网格」；⚠️ **但 D54 已把这条的必要性提升为「先修标量化」**："
         "在 `J` 的噪声被遗漏率罚分支配的情况下，重复种子组只会把一个噪声支配的量测得更准")

DEC_PREFIX = "| **D53** |"
DEC_ROW = (
    "| **D54** | 2026-10-14 | 🛑 **冻结 Objective 的标量 `J` 被遗漏率罚分支配 ⇒ 罚分改为约束，"
    "任何基于 `J` 的臂间比较都不可解释**。实测（锚点 D4、`rho = 0.6`、`n_repeats = 5`、"
    "`n_fim ∈ {1,2,4,8}`）：**`sd_C² / sd_J²` = 100.7% / 97.8% / 95.0% / 96.8%**，而科学信号 "
    "(A)/(B) 的 `sd_A = 0.005–0.008`、`sd_B = 0.10–0.15` 贡献约 0。**根因**：(C) 是关于遗漏率的"
    "**二次罚分**，在 D4 的遗漏率 0.35 处 `dC/d(omission) ≈ 125`，把遗漏率的 MC 噪声"
    "（实测 `sd = 0.014 → 0.006`）放大成 `sd_C = 1.81 → 0.82`；而遗漏率**不是**按 `1/sqrt(n_fim)` "
    "收敛（`n_fim` 从 1 到 8 只降 0.55 倍，不是 0.35 倍）⇒ **靠加大 `n_fim` 解决不现实**"
    "（按 `1/sqrt` 外推需 `n_fim ≈ 59`，而观测到的平坦化说明实际还要更多）。**处置**："
    "① 把 (C) **从事后罚分改为事前约束**（遗漏率落在 `[0.05, 0.20]` 之外的设计**直接移出可行集**，"
    "而不是给一个陡峭的二次罚分；带外的设计本来也不该被推荐）；② 四路消融的判据**建立在 (A)/(B) 上**"
    "（它们的噪声比 (C) 小两个数量级），`J` 若保留只用于**报告**，不得用于宣称最好；"
    "③ 更好的修法是让遗漏率**解析化**（DDM 的存活函数已经存在：`1_Code/DDM_Core/twophase.py::survival_step`、"
    "`1_Code/DDM_Core/wfpt.py`），但那会改动冻结 Objective 的输入 ⇒ **必须重新冻结哈希**，"
    "不能事后加权。 | "
    "新建 `1_Code/AutoRA_SPE/_scratch_probe_noise_curve.py`（80 行）并实跑两轮：第一轮 "
    "`n_fim ∈ {1,2,4,8}`、`n_repeats = 5`，得 `sd_J = 1.808 / 0.978 / 0.919 / 0.831` ⇒ "
    "`2·sd_J = 1.66–3.62`，**全部远大于臂间差异 0.47–0.64**；第二轮加上 C 的分项，得 "
    "`sd_omission = 0.0137 / 0.0077 / 0.0072 / 0.0062`、`sd_C = 1.815 / 0.967 / 0.895 / 0.818` ⇒ "
    "**C 占 J 方差 95–101%**。日志 `1_Code/AutoRA_SPE/_scratch_probe_noise_curve_u8.txt`。"
    "配套：`stage9_loop.measure_noise` 现在同时返回 `omission` / `C` / `sd_omission` / `sd_C`"
    "（这是把\"噪声来自哪一项\"变成可读数的前提）。 | "
    "① `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §11（把第 12–13 条重写为"
    "「噪声已被定位到 (C)」并新增\"罚分改约束\"一条）、§9（新增探针行）、§12 加行；"
    "② `1_Code/DDM_Core/README.md` §9 **第 35 项**；③ `1_Code/AutoRA_SPE/README.md` §7 补一行；"
    "④ **D53 的「仍开放」第 (2) 件被提升**：先修标量化，再谈重复种子组；"
    "⑤ **本轮起，凡出现 `J` 的表格都必须同时给 (A)/(B) 与 `sd_C` 的量级**，"
    "否则读者会把一条噪声读数当成设计优劣。 |"
)

PROG_PREFIX = "| 2026-10-14 | **9**（优化循环交付 → D53）"
PROG_ROW = (
    "| 2026-10-14 | **9**（Objective 标量化被噪声支配 → D54） | "
    "**D53 留下一条「内环 MC 噪声大于设计差异」的观察，本轮把它追到根因并发现是 Objective 的"
    "标量化本身有问题**。① 先量标度：`n_fim ∈ {1,2,4,8}`、`n_repeats = 5` ⇒ "
    "`sd_J = 1.808 / 0.978 / 0.919 / 0.831`，`2·sd_J = 1.66–3.62` **全部大于臂间差异 0.47–0.64**；"
    "② 再拆分项：`sd_omission = 0.0137 → 0.0062`、`sd_C = 1.815 → 0.818` ⇒ "
    "**`sd_C²/sd_J²` = 95–101%** ⇒ `J` 的噪声**全部来自遗漏率罚分 (C)**，而 (A)/(B) 的噪声"
    "（`sd_A = 0.005–0.008`、`sd_B = 0.10–0.15`）贡献约 0；③ **根因**是 (C) 的斜率 "
    "`dC/d(omission) ≈ 125`（D4 的遗漏率 0.35 处）把一个小 MC 噪声放大两个数量级；"
    "④ **遗漏率不按 `1/sqrt(n_fim)` 收敛**（1→8 只降 0.55 倍）⇒ 加大 `n_fim` 不现实；"
    "⑤ **处置**：罚分改成**约束**（带外剔出可行集）、消融判据只建立在 (A)/(B) 上、"
    "更长远的修法是让遗漏率解析化（存活函数已存在）并**重新冻结哈希**。 | "
    "`1_Code/AutoRA_SPE/_scratch_probe_noise_curve.py`（新建，80 行）；"
    "日志 `1_Code/AutoRA_SPE/_scratch_probe_noise_curve_u8.txt`；"
    "`1_Code/AutoRA_SPE/stage9_loop.py`（`measure_noise` 增加 `omission`/`C`/`sd_omission`/`sd_C` 读数）；"
    "`1_Code/DDM_Core/README.md` §9 第 35 项；"
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9 / §11 / §12 | "
    "🔨 **仍开放**：**(1)** 把 (C) 改成约束并重新评估四臂（改动冻结 Objective 的**使用方式**"
    "而非其数值定义，须记录）；**(2)** 是否改成解析遗漏率并**重新冻结哈希**；"
    "**(3)** Stage 9 剩余文件 `stage9_report.md`；**(4)** `check_stage9.py` 的总跑（已建、正在跑） |"
)

LOG_PREFIX = "| 2026-10-14 | **新增 D53：Stage 9 的优化循环已交付"
LOG_ROW = (
    "| 2026-10-14 | **新增 D54：冻结 Objective 的标量 `J` 被遗漏率罚分支配 ⇒ 罚分改为约束，"
    "基于 `J` 的臂间比较不可解释**。① 噪声标度实测 `sd_J = 1.808 / 0.978 / 0.919 / 0.831`"
    "（`n_fim = 1/2/4/8`，`n_repeats = 5`）⇒ `2·sd_J = 1.66–3.62` 全部大于臂间差异 0.47–0.64；"
    "② 分项拆解 `sd_C = 1.815 / 0.967 / 0.895 / 0.818` ⇒ **`sd_C²/sd_J²` = 95–101%**，"
    "而 (A)/(B) 贡献约 0；③ 根因是 (C) 的斜率 `dC/d(omission) ≈ 125`；"
    "④ 遗漏率不按 `1/sqrt(n_fim)` 收敛 ⇒ 加大 `n_fim` 不现实；"
    "⑤ 处置：罚分改约束 + 消融判据建立在 (A)/(B) 上 + 长远改解析遗漏率并重新冻结哈希 |"
)

APP_PREFIX = "| `1_Code/AutoRA_SPE/stage9_loop.py`（**新建**，617 行）"
APP_ROW = (
    "| `1_Code/AutoRA_SPE/_scratch_probe_noise_curve.py`（**新建**，80 行） + "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（`measure_noise` 增记 `omission`/`C`） | "
    "**D54**：`J` 的噪声被遗漏率罚分支配（占方差 95–101%），(A)/(B) 贡献约 0 ⇒ "
    "罚分改约束、消融判据只建立在 (A)/(B) 上 |"
)


def n_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    text = P.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        print("❌ 输入文件不以换行结尾，拒绝写回")
        return 2
    if "| **D54** |" in text:
        print("❌ 已存在 `| **D54** |`，本脚本已跑过（幂等守卫）")
        return 2
    lines = text[:-1].split("\n")
    print(f"读入 {P}：{len(lines)} 行")

    hits = [i for i, s in enumerate(lines) if STALE in s]
    if len(hits) != 1:
        print(f"❌ 待更正的句子命中 {len(hits)} 次（期望 1 次），拒绝写回")
        return 2
    i = hits[0]
    if n_sep(lines[i]) != n_sep(lines[i].replace(STALE, FIXED)):
        print("❌ 更正前后分隔符数变化，拒绝写回")
        return 2
    lines[i] = lines[i].replace(STALE, FIXED)
    print(f"✅ 就地更正：L{i + 1}（分隔符数不变）")

    for prefix, row, cols in ((DEC_PREFIX, DEC_ROW, 5),
                              (PROG_PREFIX, PROG_ROW, 5),
                              (LOG_PREFIX, LOG_ROW, 2),
                              (APP_PREFIX, APP_ROW, 2)):
        hits = [i for i, s in enumerate(lines) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 锚点 {prefix!r} 命中 {len(hits)} 次（期望 1 次），拒绝写回")
            return 2
        i = hits[0]
        want = cols + 1
        if n_sep(lines[i]) != want or n_sep(row) != want:
            print(f"❌ 分隔符数不一致：锚点 L{i + 1} 有 {n_sep(lines[i])}、"
                  f"新行有 {n_sep(row)}、期望 {want}，拒绝写回")
            return 2
        lines.insert(i + 1, row)
        if lines[i + 1] != row:
            print("❌ 插入后断言失败")
            return 2
        print(f"✅ 插入 {cols} 列行：L{i + 2}（锚点 {prefix[:30]}…）")

    for i in range(1, len(lines) - 1):
        if not lines[i].strip():
            if (lines[i - 1].lstrip().startswith("|") and n_sep(lines[i - 1]) >= 2
                    and lines[i + 1].lstrip().startswith("|") and n_sep(lines[i + 1]) >= 2):
                print(f"❌ 断表：L{i + 1} 是空行而两侧都是表格行，拒绝写回")
                return 2

    out = "\n".join(lines) + "\n"
    if apply:
        P.write_text(out, encoding="utf-8", newline="\n")
        print(f"✍️ 已写回：{P}（{len(lines)} 行）")
    else:
        print(f"（干跑）将写回 {P}（{len(lines)} 行）—— 加 --apply 才落盘")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
