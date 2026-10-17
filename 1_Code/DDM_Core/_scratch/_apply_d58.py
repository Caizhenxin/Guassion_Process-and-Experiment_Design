# -*- coding: utf-8 -*-
"""把决策 **D58** 写进主计划、Stage 9 方案与 `1_Code/DDM_Core/README.md`。

D58 的内容（本轮，2026-10-16）：
  ① `1_Code/AutoRA_SPE/stage9_loop.py::arm_bo` 的 `n_init` 下限写成 2 ⇒ `--budget 1` 时
     BO 臂取 2 个点 ⇒ `run_arms` 的「四路消融必须同预算」守卫抛 `RuntimeError` ⇒ **整轮跑不完**
     （实测：`--budget 1 --n-fim 12` 跑到臂 bo 中断，7 次评估白跑）。守卫是对的，错的是下限。
     修法 = 下限改 1 + 预算 ≤ `n_init` 时**自报**退化为随机采样；自测加 E 组·续三条 + H5/H5b。
  ② `1_Code/AutoRA_SPE/stage9_report.py::_composition` 只认 `cond` 那一段闸门文本 ⇒
     「只被 `n_bad` 否决」的设计会被算成「其它闸门」。`n_fim = 1` 下两个集合恰好重合 ⇒ 漏判看不出来。
     修法 = 两段文本都认 + `n_bad > 0` 兜底；自测加 R2j / R2j-2。
  ③ `n_bad` 的释义要在文档与报告里统一成「**不可识别方向条数**」（`likelihood.py::fim_diagnostics`：
     `ev < max(ev_max*1e-8, 1e-300)` 的个数），**不是「坏试次」**；报告里加 R1m 措辞判据。
  ④ Stage 9 方案 §3 依赖表两处**过时状态**就地更正（EI 采集函数早已实现；M-T1 期望信息量早已提升为
     生产文件）；内环的 `n_fim = 12` 就是 `design_fim.N_FIM`，所以「正式 `n_fim`」= 12。
  ⑤ 遗漏率带的敏感性读数（为 §11 第 18 条的三种处置备料）。

用法：``python -u 1_Code/DDM_Core/_scratch/_apply_d58.py [--apply]``（缺省干跑，只打印）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                       # 1_Code/DDM_Core/_scratch -> 仓库根
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
S9 = ROOT / "5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md"
RA = ROOT / "1_Code/AutoRA_SPE/README.md"
RM = ROOT / "1_Code/DDM_Core/README.md"


def n_sep(line: str) -> int:
    """未转义的竖线数（表格列的判据）。"""
    return line.replace("\\|", "").count("|")


def load(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def save(p: Path, ls: list[str], apply: bool) -> None:
    text = "\n".join(ls)
    if not text.endswith("\n"):
        text += "\n"
    if apply:
        p.write_text(text, encoding="utf-8", newline="\n")


def find(ls: list[str], prefix: str, what: str) -> int:
    hit = [i for i, s in enumerate(ls) if s.startswith(prefix)]
    if len(hit) != 1:
        raise SystemExit(f"❌ {what}：前缀 {prefix[:60]!r} 命中 {len(hit)} 行（要求 1）")
    return hit[0]


def ins_after(ls: list[str], prefix: str, rows: list[str], what: str,
              guard: str | None = None) -> None:
    """在锚点行之后插入若干行；新行竖线数必须与锚点一致（表格列对齐）。"""
    if guard and any(guard in s for s in ls):
        print(f"  ⏭ {what}：幂等守卫命中，跳过")
        return
    i = find(ls, prefix, what)
    k = n_sep(ls[i])
    for r in rows:
        if n_sep(r) != k:
            raise SystemExit(f"❌ {what}：新行竖线数 {n_sep(r)} != 锚点 {k}")
    ls[i + 1:i + 1] = rows
    print(f"  ✅ {what}：在 L{i + 1} 之后插入 {len(rows)} 行")


def ins_before(ls: list[str], prefix: str, rows: list[str], what: str,
               guard: str | None = None) -> None:
    if guard and any(guard in s for s in ls):
        print(f"  ⏭ {what}：幂等守卫命中，跳过")
        return
    i = find(ls, prefix, what)
    k = n_sep(ls[i])
    for r in rows:
        if n_sep(r) != k:
            raise SystemExit(f"❌ {what}：新行竖线数 {n_sep(r)} != 锚点 {k}")
    ls[i:i] = rows
    print(f"  ✅ {what}：在 L{i + 1} 之前插入 {len(rows)} 行")


def rep(ls: list[str], old: str, new: str, what: str, expect: int = 1,
        guard: str | None = None) -> None:
    """全文件子串替换（命中数必须逐字相等）。"""
    if guard and any(guard in s for s in ls):
        print(f"  ⏭ {what}：幂等守卫命中，跳过")
        return
    hit = [i for i, s in enumerate(ls) if old in s]
    if len(hit) != expect:
        raise SystemExit(f"❌ {what}：{old[:50]!r} 命中 {len(hit)} 行（要求 {expect}）")
    for i in hit:
        if n_sep(ls[i].replace(old, new)) != n_sep(ls[i]):
            raise SystemExit(f"❌ {what}：替换改变了 L{i + 1} 的竖线数")
        ls[i] = ls[i].replace(old, new)
    print(f"  ✅ {what}：{len(hit)} 处")


# ---------------------------------------------------------------- 文本常量

D58_ROW = (
    "| **D58** | 2026-10-16 | ✅ **落实「在正式 `n_fim` 下重测可行域构成」，"
    "顺带抓出三处真缺陷：小预算下 BO 臂超支、报告的分类只认一段闸门文本、`n_bad` 被写成「坏试次」**。"
    "① ❗ **缺陷一（阻断级）**：`1_Code/AutoRA_SPE/stage9_loop.py::arm_bo` 里 `n_init = max(2, "
    "min(int(n_init), int(budget)))` 的下限写成 **2** ⇒ `--budget 1` 时 BO 臂评估 **2** 个点 ⇒ "
    "`run_arms` 的「四路消融必须同预算，否则结论无效」守卫抛 `RuntimeError` ⇒ **整轮跑不完**"
    "（实测 `--budget 1 --n-fim 12` 在臂 bo 处中断，已花掉的 7 次评估全废）。**守卫是对的、错的是下限**："
    "改为 `max(1, …)`，并在 `n_init >= budget`（GP 一次都不会拟合）时**自报**"
    "「本臂退化为随机采样，其读数不能作为 BO 的证据」。② ❗ **缺陷二**：`stage9_report.py::_composition` "
    "的 `ill` 只认闸门文本里的 `cond` ⇒ 「只被 `n_bad` 否决」的设计被算成「其它闸门」；`n_fim = 1` 这批候选里"
    "两段闸门**恰好重合**（123 == 123）⇒ 漏判**看不出来**。修法 = 两段文本都认 + `n_bad > 0` 兜底。"
    "③ ❗ **缺陷三**：`n_bad` 的定义是 `1_Code/DDM_Core/likelihood.py::fim_diagnostics` 数出的"
    "**不可识别方向条数**（`ev < max(ev_max*1e-8, 1e-300)`），**不是「坏试次」**；文档与报告统一改口，"
    "并加报告措辞判据 R1m（全文不得出现该错词）。④ **正式 `n_fim` = 12**：`design_fim.N_FIM = 12`"
    "（`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §3），内环 `UNIT_PER_CELL = 4`、"
    "`CELL_BUDGET = 144` ⇒ **每个候选都是 576 试次**；`n_fim = 12` 下 `sd_J` 由 2.9247 降到 0.4056"
    "（−86%），满足 D54 第 (1) 件的「噪声小于设计差异」。⑤ **牙齿**：E 组·续三条（预算 1/2/3 必须逐字相等）"
    "+ H5/H5b（下限与退化提示的静态钉子）+ R2j/R2j-2（分类的两段闸门）+ R1m（措辞）⇒ "
    "`check_stage9_loop.py` **41/41**、`check_stage9_report.py` **47/47**。"
    "⑥ **待办**：D55 第 18 条的三种处置仍待拍板，但本轮已把**量化读数**备齐（见 §11 第 23 条与 "
    "`1_Code/DDM_Core/README.md` §8.33 §5）。 | 代码：`1_Code/AutoRA_SPE/stage9_loop.py` "
    "821 → **831 行**（`n_init` 下限、退化自报）、`1_Code/AutoRA_SPE/stage9_report.py` 337 → **370 行**"
    "（`_composition` 两段闸门 + `n_bad` 释义 + 措辞）、`1_Code/AutoRA_SPE/check_stage9_loop.py` "
    "423 → **465 行**（E 组·续 + H5/H5b）、`1_Code/AutoRA_SPE/check_stage9_report.py` 304 → **346 行**"
    "（R1m/R2j/R2j-2）、`1_Code/AutoRA_SPE/stage9_report.md` 124 → **128 行**（重生成，交付件与生成器逐字一致）；"
    "文档：本表 D58 行、`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §3/§9/§11 第 23 条/§12、"
    "`1_Code/DDM_Core/README.md` §8.33 + §9 第 42 项、`1_Code/AutoRA_SPE/README.md` §7 | "
    "`1_Code/AutoRA_SPE/_scratch_smoke_nfim12u8_v2.txt`（`--budget 1 --n-fim 12`：修前崩溃、修后跑完并打印退化提示）；"
    "`1_Code/AutoRA_SPE/_scratch_time_nfim.py`（同设计在 `n_fim = 1/2/4/12` 的耗时与病态读数）；"
    "`1_Code/AutoRA_SPE/_scratch_probe_band_sensitivity.py`（遗漏率带敏感性，只读 payload）；"
    "`1_Code/AutoRA_SPE/_scratch_cmp_nfim.py`（两个 payload 的逐设计对照）；"
    "`1_Code/AutoRA_SPE/_scratch_payload_nfim12.json`（全空间 `n_fim = 12`）；"
    "`check_stage9.py` 全套 **10 项、未通过 0 项、99.0 s** |"
)

D58_PROGRESS = (
    "| 2026-10-16 | **9**（`n_fim` 可行域重测 + 三处真缺陷 → D58） | "
    "**主计划上仍开放的第 (2) 件「在正式 `n_fim` 下重测可行域构成」落地，过程中抓到一处阻断级缺陷与两处"
    "「静默漏判」缺陷**。① ❗ 阻断级：`--budget 1 --n-fim 12` 跑到臂 bo 时 `RuntimeError: 臂 bo 用了 2 次评估，"
    "预算 1`（`arm_bo` 的 `n_init` 下限是 2）⇒ 整轮中断、7 次评估白跑；守卫**正确地**拦住了超支，但**没有**"
    "拦住「配置矛盾」⇒ 下限改 1 + 退化自报，自测加 E 组·续与 H5/H5b。② ❗ `stage9_report.py::_composition` "
    "只认 `cond` 那段闸门 ⇒「只被 `n_bad` 否决」被算成「其它闸门」；`n_fim = 1` 下两段闸门恰好重合 ⇒ 看不出来；"
    "加 R2j/R2j-2 后用合成 payload 覆盖该路径。③ ❗ `n_bad` 被写成「坏试次」共 3 处（报告 §3/§5、"
    "`1_Code/DDM_Core/README.md` §8.31、Stage 9 方案 §3 依赖表）；改为「不可识别方向条数」并加 R1m。"
    "④ **正式 `n_fim` = 12**（= `design_fim.N_FIM`，方案 §3）；`n_fim = 12` 下 `sd_J` 0.4056（`n_fim = 1` 为 2.9247）、"
    "`2·sd_A = 0.0163`、锚点 `A = 0.3384 / B = 7.7075`。⑤ **全空间重测读数**见本轮证据与 "
    "`1_Code/AutoRA_SPE/_scratch_payload_nfim12.json`。 | "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（821 → **831 行**）；`1_Code/AutoRA_SPE/stage9_report.py`"
    "（337 → **370 行**）；`1_Code/AutoRA_SPE/check_stage9_loop.py`（423 → **465 行**、**41/41**）；"
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（304 → **346 行**、**47/47**）；"
    "`1_Code/AutoRA_SPE/stage9_report.md`（**128 行**）；`1_Code/AutoRA_SPE/_scratch_agg_console_u8.txt`"
    "（**10 项、未通过 0 项、99.0 s**） | 🔨 **仍开放**：**(1)** 🛑 遗漏率带 `[0.05, 0.20]` 与锚点 D4 不相容 —— "
    "三选一（作为 9A 头条结论报出 / 显式重冻结 / D4 仅作归一化锚点），**须用户或导师拍板**"
    "（本轮已备齐量化读数：现行口径下 27 个可行设计的遗漏率全部紧贴上界 `0.1615–0.1962`，"
    "下界 0.05 从未生效；放开上界到含 D4 需要 **0.37**，届时最优设计从 `A = 0.3446` 变到 `0.3043`，"
    "而支配 D4 的数值可用设计从 5 个增到 **12** 个 ⇒ **重冻结并不能让 D4 变好，只是让它可比**）；"
    "**(2)** 四个用户侧 Stage（1 实机验收 N=2–3 / 6 Pilot N≈8 / 7 正式采集 4 组 × ~40 / 定稿签批）；"
    "**(3)** D41 拍板（是否装 `pymc` + `arviz`）；**(4)** 真实数据到手后的 `cellmean.py` 剖面诊断"
    "（`1_Code/DDM_Core/README.md` §9 第 19 项）；**(5)** 重复 R 个种子组以得到配对误差棒"
    "（`2·sd_A` 目前只由 2 次重复估出）。 |"
)

D58_CHANGELOG = (
    "| 2026-10-16 | **新增 D58：小预算下 BO 臂超支会中断整轮（`n_init` 下限 2 → 1 + 退化自报）；"
    "报告的分类必须认两段数值闸门文本（只认 `cond` 会静默漏判 `n_bad`）；`n_bad` 是「不可识别方向条数」"
    "而不是「坏试次」；正式 `n_fim` = `design_fim.N_FIM` = 12** |"
)

D58_APPENDIX = (
    "| `1_Code/AutoRA_SPE/stage9_loop.py`（821 → **831 行**） + `1_Code/AutoRA_SPE/stage9_report.py`"
    "（337 → **370 行**） + `1_Code/AutoRA_SPE/check_stage9_loop.py`（423 → **465 行**、**41/41**） + "
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（304 → **346 行**、**47/47**） + "
    "`1_Code/AutoRA_SPE/_scratch_time_nfim.py`（**新建**） + "
    "`1_Code/AutoRA_SPE/_scratch_cmp_nfim.py`（**新建**） + "
    "`1_Code/AutoRA_SPE/_scratch_probe_band_sensitivity.py`（**新建**） | **D58**："
    "① `arm_bo` 的 `n_init` 下限（`--budget 1` 时取 2 个点 ⇒ 同预算守卫抛错 ⇒ 整轮中断）+ 退化自报；"
    "② `_composition` 必须同时认 `cond` 与 `n_bad` 两段闸门文本；③ `n_bad` 释义更正；"
    "④ 正式 `n_fim` = `design_fim.N_FIM` = 12（方案 §3）下的全空间重测；"
    "⑤ 遗漏率带敏感性（为 §11 第 18 条备料） |"
)

S9_ITEM23 = (
    "23. ❗ **小预算下 BO 会退化成随机采样；而「守卫拦住超支」不等于「配置没问题」（D58）**："
    "`1_Code/AutoRA_SPE/stage9_loop.py::arm_bo` 的 `n_init` 原本是 `max(2, min(n_init, budget))` ⇒ "
    "`--budget 1` 时它取 **2** 个点 ⇒ `run_arms` 的「四路消融必须同预算」守卫抛 `RuntimeError` 并**中断整轮**"
    "（2026-10-16 实测：`--budget 1 --n-fim 12` 在臂 bo 处崩，已花的 7 次评估全废）。"
    "⇒ ① 下限改 **1**；② 当 `n_init >= budget` 时 GP 一次都不会拟合（BO 需要「初始点 + 至少一步」），"
    "此时臂**必须自报**「本臂退化为随机采样，其读数不能作为 BO 的证据」—— 否则读者会把「bo 与 random "
    "在小预算下差不多」当成「BO 没用」的证据；③ **教训**：超支守卫拦的是「结果不可比」，"
    "拦不住「这个预算下这条臂根本不成立」；凡是「某条臂在某个参数区间退化」的情形，都要**自己说出来**，"
    "不能靠守卫抛错来间接暴露。自测牙齿：E 组·续三条（预算 1/2/3 必须逐字相等）+ H5/H5b（静态钉子）。"
)

RM_833 = [
    "## 8.33 正式 `n_fim` 下的可行域重测，以及三处「静默漏判」缺陷（2026-10-16，D58）",
    "",
    "### 1. 为什么要做这一节",
    "",
    "主计划上仍开放的第 (2) 件是「在正式 `n_fim` 下重测可行域构成」：`n_fim = 1` 下 174 个候选里"
    "**123 个（70.7%）被数值闸门刷掉**，而这个比例是不是 `n_fim = 1` 的产物、当时无法回答。"
    "**正式 `n_fim` = 12** —— 这不是拍脑袋：`1_Code/DDM_Core/design_fim.py::N_FIM = 12`，"
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §3 以此为准，"
    "`_scratch/_c6_baseline.py` 也是在 `n_fim = 12` 上量到 D4 的 `A = 0.268`。"
    "内环另有 `UNIT_PER_CELL = 4`、`CELL_BUDGET = 144` ⇒ **174 个候选每个都是 576 试次**（`n_trials` 逐字相等）。",
    "",
    "### 2. 代码改动清单（5 处）",
    "",
    "1. `1_Code/AutoRA_SPE/stage9_loop.py::arm_bo`：`n_init = max(2, …)` → **`max(1, …)`**，"
    "并在 `n_init >= budget` 时打印退化提示（该预算下 GP 一次都不拟合）。",
    "2. `1_Code/AutoRA_SPE/stage9_report.py::_composition`：`ill` 由「只认 `cond` 那一段闸门文本」改为"
    "**两段都认** + `n_bad > 0` 兜底。",
    "3. `1_Code/AutoRA_SPE/stage9_report.py` 的 `n_bad` 措辞：由「坏试次」改为「**不可识别方向 N 条**」"
    "并加一处定义脚注（指向 `1_Code/DDM_Core/likelihood.py::fim_diagnostics`）。",
    "4. 自测牙齿：`1_Code/AutoRA_SPE/check_stage9_loop.py` 加 **E 组·续**（预算 1/2/3 的取点数必须逐字相等）"
    "与 **H5/H5b**（下限与退化提示的静态钉子）；`1_Code/AutoRA_SPE/check_stage9_report.py` 加 "
    "**R1m**（全文不得把 `n_bad` 说成「坏试次」）、**R2j/R2j-2**（分类必须认两段闸门文本，正例 + 反向对照）。",
    "5. `1_Code/AutoRA_SPE/stage9_report.py` §2：按 payload 自报的 `n_repeats` 打出 `sd` **自身**的不确定度"
    "（≈ `1/√(2(n−1))`；2 次重复 ⇒ `sd` 约 71%、`alpha = sd_J²` 约 141%），`n_repeats < 4` 时先警；"
    "牙齿 **R1p-h/R1p-i**。理由：`sd` 是估计量，不把重复数印出来，读者会把 `2·sd_A` 当成精确门槛。",
    "",
    "### 3. 缺陷一：小预算下 BO 臂超支，整轮跑不完（阻断级）",
    "",
    "`--budget 1 --n-fim 12` 跑到臂 bo 时抛",
    "`RuntimeError: 臂 bo 用了 2 次评估，预算 1 —— 四路消融必须同预算，否则结论无效`，"
    "**整轮中止、已花的 7 次评估（约 4 min）全部作废**。根因是 `n_init` 的下限写成了 2。"
    "守卫本身是对的（它拦的是超支），错的是下限；而且**守卫能拦住超支，拦不住「这个预算下这条臂不成立」**"
    "⇒ 修法必须同时加「退化自报」，否则读者会把退化当成 BO 的证据。",
    "",
    "### 4. 缺陷二：报告的分类只认一段闸门文本",
    "",
    "`gates` 里的两段数值文本是**不同的字符串**：`cond=… > 1e+10（病态，相关不可信）` 与 "
    "`n_bad=… > 0（有不可识别方向）`（各出现 123 次）。`_composition` 原先只看 `cond` 段 ⇒ "
    "「只被 `n_bad` 否决」的设计被算进「其它闸门」。❗ **在 `n_fim = 1` 这批候选里两个集合恰好重合**"
    "（`n_bad > 0` 的 123 个 == `cond > 1e10` 的 123 个；`n_bad == 0` 但 `cond > 1e10` 的 **0** 个）"
    "⇒ 漏判**看不出来**，直到在正式 `n_fim` 下两段文本不再重合时才可能暴露。"
    "修法 = 两段都认 + `n_bad > 0` 兜底；牙齿 R2j（只被 `n_bad` 否决的必须算数值病态）+ R2j-2（反向对照）。",
    "",
    "### 5. 缺陷三：`n_bad` 被写成「坏试次」",
    "",
    "`1_Code/DDM_Core/likelihood.py::fim_diagnostics` 的定义是"
    "`ev = eigvalsh((I + I.T) / 2)`、`n_bad = sum(ev < max(ev_max * 1e-8, 1e-300))` ⇒ 它数的是"
    "**平均信息矩阵里不可识别的方向条数**，**不是「坏试次」**。两种读法要采取的行动完全不同"
    "（前者改设计、后者查采集）。共 3 处改口：报告 §3/§5（由 `stage9_report.py` 生成）、"
    "`1_Code/DDM_Core/README.md` §8.31 的分类表、"
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §3 依赖表。"
    "报告侧加 **R1m**（全文不得出现该错词）。⚠️ 该判据**第一次跑就红**：因为我在报告的免责声明里写了"
    "「不是「坏试次」」，而判据是全文子串匹配 ⇒ 写成「不是「数据里有若干试次坏了」」才通过。"
    "**全文子串式措辞判据会连「否定式声明」一起禁掉**，这是它的固有代价。",
    "",
    "### 6. 校验证据",
    "",
    "1. `1_Code/AutoRA_SPE/_scratch_time_nfim.py`（63 行）：同一设计在 `n_fim = 1/2/4/12` 上的耗时与病态 ——"
    "`n_fim = 12` 单次评估 16.1–31.2 s（`n_fim = 1` 为 1.5–5.1 s，≈ ×6.1）；"
    "**`r24 / T=3档 W=2档` 型设计的 `cond` 不随 `n_fim` 改善**（`n_fim = 1/4/12` 为 2.231e15 / 2.191e15 / 2.013e15，"
    "`n_bad` 一直是 **1**），`r16 / T=3档 W=3档` 型为 5.513e5 → 3.213e5。",
    "2. `1_Code/AutoRA_SPE/_scratch_cmp_nfim.py`（164 行）：两个 payload 的逐设计对照（构成表 / 迁移矩阵 / "
    "病态成因 / 判据带宽与锚点 / 各档可行集 `(A)` 最小点）。用两个 `n_fim = 1` 的落盘件自检通过 —— "
    "**可行 27 / 只被带否决 24 / 只被数值病态否决 54 / 两者兼有 69 / 其它 0**，且两段闸门的集合完全重合。",
    "3. 噪声标定随 `n_fim` 的变化（`--noise-repeats 2`）：`n_fim = 1` → `sd_J = 2.9247`、`sd_A = 0.0025`、"
    "`sd_B = 0.1332`；**`n_fim = 12` → `sd_J = 0.4056`（−86%）、`sd_A = 0.0082`、`sd_B = 0.0386`、"
    "`sd_omission = 0.00307`** ⇒ D54 第 (1) 件「`n_fim` 提高到噪声小于设计差异」在 `sd_J` 上成立；"
    "⚠️ 但 `2·sd_A` 反而由 0.0050 变 **0.0163** ⇒ **判据带宽必须随 `n_fim` 一起报**（同 §11 第 19 条）；"
    "⚠️ 这两个读数都来自 **2 次重复**，6 次重复的版本见下第 7 条（`alpha` 差 **2.4 倍**）。",
    "4. 锚点 D4 在 `n_fim = 12` 下：`A = 0.3384 / B = 7.7075`（`n_fim = 1` 为 `0.3858 / 7.4824`）。",
    "5. `check_stage9_loop.py` ⇒ **41/41、未通过 0 项、exit 0、44.1 s**；`check_stage9_report.py` ⇒ "
    "**45/45、未通过 0 项、exit 0**；`check_stage9.py` 全套 ⇒ **共 10 项、未通过 0 项、99.0 s**"
    "（`S4` 41/41、`S5` 45/45）。",
    "6. ❗ **文档侧的过时状态更正**（`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §3 依赖表）："
    "EI 采集函数原写 `🔨 待写（§7.2）`，而 `1_Code/AutoRA_SPE/stage9_loop.py::arm_bo` 早已实现（`z`/`ei`、"
    "`alpha = ev.noise_alpha`）；M-T1 期望信息量原写「已在 `_scratch` 跑通但未提升为生产文件」，"
    "前半句在 D50 当天就被推翻（`stage9_inner.py::opg_information_step` / `se_from_information`、"
    "`check_stage9_inner.py` 29/29），后半句（未接进 `design_fim.design_se`）**仍成立且是有意的**。"
    "两处都用 `~~…~~` + `❌ **2026-10-16 更正（见 D58）**` 就地更正。",
    "7. `1_Code/AutoRA_SPE/_scratch_noise_repeats.py`（61 行，**只读、不写任何落盘件**）：同一锚点在"
    "`n_fim = 1` 与 `n_fim = 12` 上各换种子重算 **6** 次 —— `n_fim = 1`：`A` 逐次 "
    "0.35864 / 0.35508 / 0.34523 / 0.35509 / 0.35290 / 0.35750（均值 0.35408）、`sd_A = 0.00478`"
    "（相对离散 1.350%）、`sd_B = 0.14050`、`sd_J = 1.63356`、`sd_omission = 0.01239`、`alpha = 2.6685`；"
    "`n_fim = 12`：`A` 逐次 0.34428 / 0.33266 / 0.33432 / 0.32370 / 0.34524 / 0.34374（均值 0.33732）、"
    "**`sd_A = 0.00859`（相对离散 2.545%）**、`sd_B = 0.05094`、`sd_J = 0.62719`、"
    "`sd_omission = 0.00504`、`alpha = 0.39336`。两条结论：**(i)** `2·sd_A` 随 `n_fim` **变大**"
    "（0.00956 → 0.01717），而 `2·sd_B`、`sd_J`、`sd_omission` 都变小（0.28100 → 0.10188、"
    "1.63356 → 0.62719、0.01239 → 0.00504）—— `sd_A` 的增大在 2 次与 6 次重复下都出现 ⇒ "
    "**不是取样偶然**（机制待查；`(A)` 是 `relative_se` 的**几何平均**，对个别方向的病态比算术平均更敏感）；"
    "**(ii)** 2 次重复估 `sd` 会**系统偏**（`alpha` 0.165 vs 0.393 = 2.4 倍），因为两次重复用的是"
    "**同一对固定种子**（`base_seed + 791_900 + 37k`，`k = 0, 1`）⇒ 这个误差在多次运行之间是**相关的**，"
    "不是随机噪声。⇒ **正式跑改用 `--noise-repeats 6`** 重跑（先前的 2 次重复版本就地作废、未落盘）。",
    "",
    "### 7. 尚未做",
    "",
    "1. 🛑 **D55 第 18 条的三种处置仍待拍板**；本节与 §11 第 23 条已把决策读数备齐（见下）。",
    "2. **遗漏率带的敏感性**（`1_Code/AutoRA_SPE/_scratch_probe_band_sensitivity.py`，只读 payload、"
    "不改任何冻结量）：现行口径下**可行 27 个的遗漏率全都紧贴上界**（min 0.1615 / 中位 0.1892 / max 0.1962），"
    "只被带否决的 24 个是 0.2014–0.3733 ⇒ **下界 0.05 从未生效**；把上界放宽到 0.25 / 0.30 时最优设计不变"
    "（`A = 0.3446`），但 **0.35 时跳到 `0.3043`**，而**要含进锚点 D4（遗漏率 0.361111…）必须放到 0.37** ——"
    "届时数值可用设计 49 个、**支配 D4 的设计由 5 个增到 12 个**；锚点归一化口径（处置 (c)）下推荐点"
    "`A/A(D4) = 0.8933`（比 D4 小 **10.7%**）、四臂为 `random 1.0060`、`grid 1.0101`、`manual 1.0340`、"
    "`bo 1.3253`。⇒ **处置 (b)「重冻结到含 D4」并不能让 D4 变好，只是让它可比**。",
    "3. **正式 `n_fim = 12` 的四路消融**（`--budget 12 --n-fim 12`，约 1.5–2 h）尚未跑："
    "本轮的 `n_fim = 12` 跑是 `--budget 1`（只为一趟补齐 174 个候选空间），四臂在预算 1 下**必然退化**"
    "（E 组·续的读数就是这件事），不能作为消融结论。",
    "4. 重复 **R 个种子组**以得到配对误差棒（`2·sd_A` 目前只由 2 次重复估出）。",
    "",
]

RM_ITEM42 = (
    "| 42 | ✅ **正式 `n_fim` 下的可行域重测 + 三处「静默漏判」缺陷（D58，§8.33）** | "
    "① 阻断级：`1_Code/AutoRA_SPE/stage9_loop.py::arm_bo` 的 `n_init` 下限写成 2 ⇒ `--budget 1` 时"
    "取 2 个点 ⇒ 同预算守卫抛错、**整轮中断**；改为 `max(1, …)` + 「预算 ≤ `n_init` 时自报退化为随机采样」。"
    "② `1_Code/AutoRA_SPE/stage9_report.py::_composition` 只认 `cond` 闸门文本 ⇒「只被 `n_bad` 否决」"
    "被算成「其它闸门」，而 `n_fim = 1` 下两个集合恰好重合（123 == 123）⇒ **漏判看不出来**；改为两段都认。"
    "③ `n_bad` = **不可识别方向条数**（`likelihood.py::fim_diagnostics`），不是「坏试次」；3 处改口 + 加 R1m。"
    "④ **正式 `n_fim` = `design_fim.N_FIM` = 12**：`sd_J` 2.9247 → **0.4056**（−86%），"
    "但 `2·sd_A` 0.0050 → **0.0163** ⇒ 带宽必须随 `n_fim` 一起报。"
    "⑤ 牙齿：E 组·续 + H5/H5b + R2j/R2j-2 + R1m + R1p-h/R1p-i ⇒ `check_stage9_loop.py` **41/41**、"
    "`check_stage9_report.py` **47/47**、全套 `check_stage9.py` **10 项、99.0 s**。证据："
    "`1_Code/AutoRA_SPE/_scratch_time_nfim.py`、`1_Code/AutoRA_SPE/_scratch_cmp_nfim.py`、"
    "`1_Code/AutoRA_SPE/_scratch_probe_band_sensitivity.py`、`1_Code/AutoRA_SPE/_scratch_noise_repeats.py`"
    "（均**新建**）、`1_Code/AutoRA_SPE/_scratch_payload_nfim12.json`、"
    "`1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12.json`；主计划 D58；"
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §11 第 23 条 |"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    print(f"仓库根：{ROOT}")
    print(f"{'应用' if a.apply else '干跑'}：D58 落纸\n")

    # ---------------- 主计划 ----------------
    print("[1/4] 5_Reference/08_工作流/工作流_主计划.md")
    ls = load(MP)
    ins_after(ls, "| **D57** | 2026-10-14 |", [D58_ROW], "决策行 D58",
              guard="| **D58** |")
    ins_after(ls, "| 2026-10-14 | **9**（无人可行点混排 + 落盘报告 → D57） |",
              [D58_PROGRESS], "进度行 D58",
              guard="（`n_fim` 可行域重测 + 三处真缺陷 → D58）")
    ins_after(ls, "| 2026-10-14 | **新增 D57：", [D58_CHANGELOG], "变更日志 D58",
              guard="**新增 D58：")
    ins_after(ls, "| `1_Code/AutoRA_SPE/stage9_loop.py`（787 → **821 行**）",
              [D58_APPENDIX], "附录证据 D58", guard="`_scratch_time_nfim.py`（**新建**）")
    save(MP, ls, a.apply)

    # ---------------- Stage 9 方案 ----------------
    print("\n[2/4] 5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md")
    ls = load(S9)
    rep(ls, "✅ **已建**（**821 行**、裸 LF —— D55 前为 618 行、D56 前为 749 行、D57 前为 787 行；",
        "✅ **已建**（**831 行**、裸 LF —— D55 前为 618 行、D56 前为 749 行、D57 前为 787 行、"
        "D58 前为 821 行；", "§9 `stage9_loop.py` 行数", guard="**831 行**、裸 LF")
    rep(ls, "| 优化循环自测（A–H 八组） | ✅ **已建**（**423 行**、裸 LF —— D55 前为 261 行、"
            "D56 前为 340 行、D57 前为 374 行）。**36/36 通过、exit 0、39.1 s**（D56 新增 H 组三条静态源码判据 + "
            "D57 新增 E8 组四条与 H4）",
        "| 优化循环自测（A–H 八组） | ✅ **已建**（**465 行**、裸 LF —— D55 前为 261 行、"
        "D56 前为 340 行、D57 前为 374 行、D58 前为 423 行）。**41/41 通过、exit 0、44.1 s**"
        "（D56 新增 H 组三条静态源码判据 + D57 新增 E8 组四条与 H4 + **D58 新增 E 组·续三条与 H5/H5b 两条**）",
        "§9 `check_stage9_loop.py` 行数/项数", guard="**465 行**、裸 LF")
    rep(ls, "全套跑（`--n-fim-inner 2`，111.9 s、日志 `1_Code/AutoRA_SPE/_scratch_agg_console_u8.txt`）："
            "`S1` 25/25、`S2` exit 0、`S3` 29/29、`S4` 21/21、`S5` **42/42**（报告生成器自测）",
        "全套跑（`--n-fim-inner 2`，110.7 s、日志 `1_Code/AutoRA_SPE/_scratch_agg_console_u8.txt`）："
        "`S1` 25/25、`S2` exit 0、`S3` 29/29、`S4` 41/41、`S5` **47/47**（报告生成器自测）",
        "§9 `check_stage9.py` 全套读数", guard="110.7 s、日志")
    rep(ls, "| 落盘报告 | ✅ **已建**（**124 行**；", "| 落盘报告 | ✅ **已建**（**128 行**；",
        "§9 `stage9_report.md` 行数", guard="✅ **已建**（**128 行**；")
    rep(ls, "| 落盘报告生成器（`build(payload_path: Path) -> str`） | ✅ **已建**（**337 行**、裸 LF）。",
        "| 落盘报告生成器（`build(payload_path: Path) -> str`） | ✅ **已建**（**370 行**、裸 LF；"
        "D58 起 `_composition` **同时认 `cond` 与 `n_bad` 两段闸门文本**，并把 `n_bad` 的释义写成"
        "「不可识别方向条数」）。",
        "§9 `stage9_report.py` 行数", guard="**370 行**、裸 LF")
    rep(ls, "| 报告生成器自测（R1–R5 五组） | ✅ **已建**（**304 行**、裸 LF）。**42/42 通过、exit 0**",
        "| 报告生成器自测（R1–R5 五组） | ✅ **已建**（**346 行**、裸 LF）。**47/47 通过、exit 0**"
        "（D58 新增 R1m 措辞判据 + R2j/R2j-2 两段闸门分类判据 + R1p-h/R1p-i 的 `n_repeats` 先警判据）",
        "§9 `check_stage9_report.py` 行数", guard="**346 行**、裸 LF")
    ins_after(ls, "22. **报告是交付件 ⇒ 两件事必须成对**", [S9_ITEM23], "§11 第 23 条",
              guard="23. ❗ **小预算下 BO 会退化成随机采样")
    ls.append(  # §12 表尾追加 D58 行（表在文件末尾，直接 append 后补一行空行）
        "| 2026-10-16 | **正式 `n_fim` 下的可行域重测 + 决策 D58**：`--budget 1 --n-fim 12` 在臂 bo 处因"
        "`n_init` 下限 2 而 `RuntimeError` 中断整轮（守卫拦住了超支、但拦不住「配置矛盾」）⇒ "
        "`1_Code/AutoRA_SPE/stage9_loop.py` 821 → **831 行**（下限改 1 + 退化自报）；"
        "`1_Code/AutoRA_SPE/stage9_report.py::_composition` 只认 `cond` 段闸门 ⇒「只被 `n_bad` 否决」被静默"
        "算成「其它闸门」（`n_fim = 1` 下两集合重合 ⇒ 看不出来），改为两段都认（337 → **370 行**）；"
        "`n_bad` 由「坏试次」改口为「**不可识别方向条数**」；**正式 `n_fim` = `design_fim.N_FIM` = 12** "
        "（6 次重复的标定：`sd_J` 2.9247 → **0.6272**、`sd_B` 0.1332 → **0.0509**，但 `2·sd_A` "
        "0.0050 → **0.0172**）；牙齿 E 组·续 + H5/H5b + R1m/R2j/R2j-2 + R1p-h/R1p-i ⇒ "
        "`check_stage9_loop.py` **41/41**（423 → **465 行**）、"
        "`check_stage9_report.py` **47/47**（304 → **346 行**）；§11 新增第 23 条 | "
        "`1_Code/AutoRA_SPE/_scratch_time_nfim.py`、`1_Code/AutoRA_SPE/_scratch_cmp_nfim.py`、"
        "`1_Code/AutoRA_SPE/_scratch_probe_band_sensitivity.py`、"
        "`1_Code/AutoRA_SPE/_scratch_noise_repeats.py`、"
        "`1_Code/AutoRA_SPE/_scratch_payload_nfim12.json`、"
        "`1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12.json`、"
        "`1_Code/AutoRA_SPE/_scratch_agg_console_u8.txt`（10 项、110.7 s）、主计划 D58、"
        "`1_Code/DDM_Core/README.md` §8.33、§9 第 42 项 |")
    save(S9, ls, a.apply)

    # ---------------- AutoRA README ----------------
    print("\n[3/4] 1_Code/AutoRA_SPE/README.md")
    ls = load(RA)
    rep(ls, "| **优化循环**（**821 行**）", "| **优化循环**（**831 行**；D58 起 `arm_bo` 的 `n_init` 下限为 1，"
        "预算 ≤ `n_init` 时自报「退化为随机采样」）", "§7 `stage9_loop.py` 行数",
        guard="**831 行**；D58 起")
    rep(ls, "| 循环自测（A–H 八组，**36/36**）", "| 循环自测（A–H 八组，**41/41**）",
        "§7 `check_stage9_loop.py` 项数", guard="A–H 八组，**41/41**")
    rep(ls, "⇒ **423 行、36/36、exit 0、39.1 s** |", "⇒ **465 行、41/41、exit 0、44.1 s**；"
        "❗ **D58** 再加 **E 组·续**（预算 1/2/3 的取点数必须逐字相等）与 **H5/H5b**（`n_init` 下限与退化提示的静态钉子） |",
        "§7 `check_stage9_loop.py` 行尾", guard="**465 行、41/41")
    rep(ls, "| **Stage 9 落盘报告生成器**（**337 行**）", "| **Stage 9 落盘报告生成器**（**370 行**）",
        "§7 `stage9_report.py` 行数", guard="生成器**（**370 行**）")
    rep(ls, "报告生成器自测（R1–R5 五组，**304 行、42/42、exit 0**）",
        "报告生成器自测（R1–R5 五组，**346 行、47/47、exit 0**）",
        "§7 `check_stage9_report.py` 行数", guard="**346 行、47/47")
    rep(ls, "（`_canonical()`）⇒ **42/42** |", "（`_canonical()`）；❗ **D58** 再加 **R1m**（全文不得把 `n_bad` "
        "说成「坏试次」）、**R2j/R2j-2**（分类必须同时认 `cond` 与 `n_bad` 两段闸门文本，正例 + 反向对照）、"
        "**R1p-h/R1p-i**（`n_repeats < 4` 时报告必须先警 `sd` 自身的不确定度）"
        "⇒ **47/47** |", "§7 `check_stage9_report.py` 行尾", guard="**R1m**")
    rep(ls, "| **落盘报告**（**124 行**，", "| **落盘报告**（**128 行**，",
        "§7 `stage9_report.md` 行数", guard="落盘报告**（**128 行**")
    save(RA, ls, a.apply)

    # ---------------- DDM README ----------------
    print("\n[4/4] 1_Code/DDM_Core/README.md")
    ls = load(RM)
    ins_before(ls, "## 9. 尚未做", RM_833, "§8.33", guard="## 8.33 正式 `n_fim` 下的可行域重测")
    ins_after(ls, "| 41 | ✅ **「没有可行点的臂不得混排」与「报告必须由落盘件生成」已落地（D57，§8.32）**",
              [RM_ITEM42], "§9 第 42 项", guard="| 42 | ✅ **正式 `n_fim` 下的可行域重测")
    save(RM, ls, a.apply)

    print("\n" + ("✅ 已写盘" if a.apply else "（干跑：未写盘；加 --apply 才写）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
