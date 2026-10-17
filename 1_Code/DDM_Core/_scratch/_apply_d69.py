# -*- coding: utf-8 -*-
"""D69 落纸：共享流 CRN 配对实测后不升格（四份文档 + 主计划四行）。

用法：``python -X utf8 -u _apply_d69.py [--apply]``
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S9 = REPO / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"
RA = REPO / "1_Code" / "AutoRA_SPE" / "README.md"

MARK = "D69"

# ---------------- 主计划 ----------------
D69_DECISION = (
    "| **D69** | 2026-10-17 | ✅ **「共享流 CRN 配对」实测后**不升格**为正式判据（带子只收窄 1.07–2.15 倍，"
    "而要真用必须换实验）**。① 动机：D61 的「尚未做」里登记着这一项（配对系数 2.83 → 1.1–2.0，需重做 D60 登记）；"
    "② 做法：新建 `1_Code/AutoRA_SPE/_probe_crn_pairing.py`（**137 行**，零新依赖），复用 "
    "`_scratch_anchor_seed_scan._one()` 的**共用种子表**口径，取正式件 `(A)` 最小的 **3 个可行设计 + 锚点 D4**，"
    "各在 **12 个共用种子**上评估（`n_fim = 12`、`n_subjects = 40`、`rho = 0.6`，4 × 12 次内环约 26 min），"
    "算逐设计 `sd`、与基准的 Pearson `ρ`、配对 `sd_pair` 与**实测系数 `2·sd_pair/sd`**；"
    "③ 结果：基准 `…W[1199.90/1799.90/2399.80]ms x r12` 的 `sd = 0.007185`（均值 0.383219），"
    "三对设计的 `ρ` = **+0.328 / +0.783 / +0.122**、系数 **2.332 / 1.316 / 2.650**、收窄 **1.21× / 2.15× / 1.07×**；"
    "逐设计 `sd` 0.0069–0.0090（max/min **1.30 倍**）⇒ 再次印证 D64 的同方差；"
    "④ 判定：收窄倍数**依赖具体设计对**、量级只有 1–2 倍；而 `stage9_loop.Evaluator._raw` 若要配对，"
    "种子必须改成**只依赖种子表**（不再掺设计名）⇒ 既有落盘件的 `cache` 键全变 ⇒ **是换实验不是换分析**，须事前登记；"
    "⑤ 后果：D61 的该条**结案（不采用）**，`2·√2·sd` 保持为唯一判据口径；若将来重做实验，本条给出"
    "「可收窄 1.1–2.2 倍」的量化依据与代码入口。 "
    "| `1_Code/AutoRA_SPE/_scratch_crn_pairing_nfim12_u8.txt`（4 个设计 × 12 种子，逐种子读数在 `.vals.json`）；"
    "正式件自报 `sd_A = 0.0075`（锚点、16 次重复）与本探针的 0.0069–0.0090 同量级；"
    "`check_files.py` 通过（裸 LF、无 BOM、ast OK） "
    "| Stage 9 的技术项到此**全部结案**；剩下的是用户侧 Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / "
    "定稿签批，以及真实数据到手后的 `cellmean.py` 剖面诊断。 |"
)

D69_PROGRESS = (
    "| 2026-10-17 | **9**（共享流 CRN 配对 → D69） | **把「配对口径能收窄多少」量出来，并据以拒绝升格**。"
    "新建 `_probe_crn_pairing.py`（137 行），正式件的 3 个可行设计 + 锚点在 12 个共用种子上各评估一次"
    "（`n_fim = 12`）⇒ `ρ` **+0.122 … +0.783**、实测系数 **1.316 … 2.650**（独立性是 2.828）⇒ "
    "带子只收窄 **1.07×–2.15×**。判定不升格：收益有限，且要使种子只依赖种子表 ⇒ `cache` 键全变 ⇒ 属换实验。 "
    "| `1_Code/AutoRA_SPE/_scratch_crn_pairing_nfim12_u8.txt`、`.vals.json` "
    "| Stage 9 技术项结案；下一步是用户侧 Stage 1/6/7 与定稿签批 |"
)

D69_CHANGELOG = (
    "| 2026-10-17 | **新增 D69：共享流 CRN 配对实测后不升格**。新建 `1_Code/AutoRA_SPE/_probe_crn_pairing.py`"
    "（137 行）量「同种子表下两个设计的相关性」：正式 `n_fim = 12`、12 个共用种子、3 个可行设计 + 锚点 ⇒ "
    "`ρ` **+0.122 / +0.328 / +0.783**、实测系数 **2.650 / 2.332 / 1.316**（独立口径 2.828）⇒ 判据带只收窄 "
    "**1.07× / 1.21× / 2.15×**。判定**不采用**：收益依赖设计对且只有 1–2 倍，而配对要求 `Evaluator._raw` "
    "的种子只依赖种子表 ⇒ 既有 `cache` 键全变 ⇒ 是换实验。`2·√2·sd` 保持（D60 的事前登记不变）。 |"
)

D69_EVIDENCE = (
    "| `1_Code/AutoRA_SPE/_probe_crn_pairing.py`（**新建**，137 行）+ `_scratch_crn_pairing_nfim12_u8.txt` "
    "+ `_scratch_crn_pairing_nfim12_u8.vals.json` | **D69 的实测证据（配对口径的收益上限）**："
    "口径 = 同一份种子表（`default_rng(20261016)` 取 12 个）、同一 `n_fim = 12`，逐设计调 "
    "`_scratch_anchor_seed_scan._one()`（它把种子**直接**交给 `inner_eval` ⇒ 各设计共用同一条随机流）。"
    "读数：基准 `T[33.33/149.99/249.98/449.98]ms x W[1199.90/1799.90/2399.80]ms x r12` 均值 0.383219、"
    "`sd = 0.007185`；`T[33.33/149.99/349.99]ms x W[1199.90/1799.90/2399.80]ms x r16` 均值 0.376065、"
    "`sd = 0.008995`、`ρ = +0.328`、`sd_pair = 0.009491`、系数 **2.332**；"
    "`T[33.33/149.99/349.99]ms x W[1199.90/1799.90/2399.80]ms x r12` 均值 0.383676、`sd = 0.007263`、"
    "`ρ = +0.783`、`sd_pair = 0.004755`、系数 **1.316**；锚点 D4 均值 0.340411、`sd = 0.006897`、"
    "`ρ = +0.122`、`sd_pair = 0.009331`、系数 **2.650**。⇒ 三对设计的相关性从 +0.12 到 +0.78 不等 ⇒ "
    "「配对一定大幅收窄」的直觉**不成立**。 |"
)

# ---------------- DDM README ----------------
RM_844 = """## 8.44 「共享流 CRN 配对」实测后不升格（2026-10-17，D69）

#### 8.44.1 动机

D61 的「尚未做」里一直挂着一条：`stage9_loop.compare_arms` 的判据带是 `2·√2·sd`，其中的 `√2` 来自
「两条臂是不同设计、各自独立抽样」；若把两条臂改成**共用同一条随机流 + 逐种子配对**，
`Var(Δ) = sd1² + sd2² − 2ρ·sd1·sd2` 会随正相关下降 ⇒ 带子可以收窄。收窄多少一直没量过。

#### 8.44.2 做法

新建 `1_Code/AutoRA_SPE/_probe_crn_pairing.py`（**137 行**，零新依赖）：读正式落盘件的 `cache`，
取 `(A)` 最小的 **3 个可行设计** + **锚点 D4**，对每个设计在**同一份 12 个种子**上各评估一次
（`n_fim = 12`、`n_subjects = 40`、`rho = 0.6`，走 `_scratch_anchor_seed_scan._one()`，
它把种子**直接**交给 `inner_eval` ⇒ 各设计共用同一条流），算逐设计 `sd`、与基准设计的 Pearson `ρ`、
配对 `sd_pair` 与**实测系数 `2·sd_pair/sd`**（独立性假设是 `2·√2 = 2.828`）。

#### 8.44.3 实测（`_scratch_crn_pairing_nfim12_u8.txt`，4 × 12 次内环、约 26 min）

| 设计（相对基准 `…W[1199.90/1799.90/2399.80]ms x r12`） | 均值 | `sd` | `ρ` | `sd_pair` | 实测系数 | 相对 `2√2` 收窄 |
|---|---|---|---|---|---|---|
| `T[33.33/149.99/349.99]ms x W[1199.90/1799.90/2399.80]ms x r16` | 0.376065 | 0.008995 | **+0.328** | 0.009491 | **2.332** | 1.21 倍 |
| `T[33.33/149.99/349.99]ms x W[1199.90/1799.90/2399.80]ms x r12` | 0.383676 | 0.007263 | **+0.783** | 0.004755 | **1.316** | 2.15 倍 |
| 锚点 D4 | 0.340411 | 0.006897 | **+0.122** | 0.009331 | **2.650** | 1.07 倍 |

逐设计 `sd` = 0.0069–0.0090（max/min **1.30 倍**）⇒ 与 D64 的同方差结论一致；
正式件自报的锚点 `sd_A = 0.0075`（16 次重复）也在这个量级。

#### 8.44.4 判定：不升格

1. **收益有限且不稳定**：相关性从 +0.12 到 +0.78 不等，带子只收窄 1.07–2.15 倍；换成「1/2.83」的直觉是错的。
2. **要真用就是换实验**：`stage9_loop.Evaluator._raw` 现在用 `seed = cell_seed(d["name"], base_seed)`
   ⇒ 各设计各一条流。改成「只依赖种子表」会让**所有既有落盘件的 `cache` 键全变** ⇒ 必须重跑内环、重新登记，
   不是换分析。
3. **事前登记的价值更大**：`2·√2·sd` 已写进交付件与论文方法段（D60）；为了 1–2 倍的带宽去动口径，
   会把「事前登记」变成「看到结果再改规则」。

#### 8.44.5 与 D60/D61 的关系

* D60（带宽系数 `2·√2`）**不变**，仍是唯一判据口径。
* D61 的「尚未做」里那条**结案（不采用）**，但量化依据留在这里：若将来重做实验，
  应事前登记配对口径，并知道收益上限在 1.1–2.2 倍。

#### 8.44.6 尚未做

1. 若真要收窄带宽，更有效的路子是**增加 `n_fim`**（`sd_A` 按 `1/√n_fim` 缩小），而不是改配对口径 ——
   这条本轮未测（`n_fim = 12 → 24` 的内环成本约 ×2）。
2. Stage 9 的其余技术项已全部结案：剩下的都是用户侧（Stage 1 实机验收 / Stage 6 Pilot / Stage 7 采集 / 定稿签批）。

"""

RM_ITEM53 = (
    "| 53 | ✅ **「共享流 CRN 配对」实测后不升格（D69，§8.44）** | 正式 `n_fim = 12`、12 个共用种子、"
    "3 个可行设计 + 锚点：`ρ` **+0.122 / +0.328 / +0.783**、实测系数 **2.650 / 2.332 / 1.316**"
    "（独立性 2.828）⇒ 带子只收窄 **1.07–2.15 倍**；且要真用必须让种子只依赖种子表 ⇒ `cache` 键全变 ⇒ "
    "不采用 |"
)

# ---------------- Stage 9 ----------------
S9_ROW9 = (
    "| `1_Code/AutoRA_SPE/_probe_crn_pairing.py` | 量「同一份种子表下两个设计的相关性」⇒ 配对判据的收益上限 | "
    "✅ **已建**（137 行、裸 LF）。D69 结论：`ρ` **+0.122 / +0.328 / +0.783**、实测系数 "
    "**2.650 / 2.332 / 1.316** ⇒ 带子只收窄 **1.07× / 1.21× / 2.15×**、**不升格** |"
)

S9_ITEM30 = (
    "30. ❗ **「共享流 CRN 配对」量过了、不采用（D69）**：正式 `n_fim = 12`、12 个共用种子、"
    "3 个可行设计 + 锚点 ⇒ `ρ` **+0.122 / +0.328 / +0.783**、实测系数 **2.650 / 2.332 / 1.316**"
    "（独立口径 2.828）⇒ 判据带只收窄 **1.07–2.15 倍**；要实现必须让 `Evaluator._raw` 的种子只依赖种子表"
    "（`cache` 键全变 ⇒ 换实验）。`2·√2·sd` 保持为唯一口径。"
)

S9_CHANGELOG = (
    "| 2026-10-17 | **共享流 CRN 配对：实测后不升格（决策 D69）**：新建 `_probe_crn_pairing.py`（137 行），"
    "正式件 3 个可行设计 + 锚点在 12 个共用种子上各评估一次（`n_fim = 12`）⇒ `ρ` **+0.122 … +0.783**、"
    "实测系数 **1.316 … 2.650**（独立性 2.828）⇒ 带子只收窄 **1.07×–2.15×**。判定：不采用，理由是收益有限"
    "且换配对即换实验（`cache` 键全变）；量化依据留给「将来重做实验」的事前登记。 |"
)

# ---------------- AutoRA README ----------------
RA_ROW = (
    "| `_probe_crn_pairing.py` | 「共享流 CRN 配对」收益实测（D69）：同一份 12 个种子下 3 个可行设计 + 锚点"
    "（`n_fim = 12`）⇒ `ρ` **+0.122 … +0.783**、实测系数 **1.316 … 2.650** ⇒ 判据带只收窄 "
    "**1.07×–2.15×**，故 `2·√2·sd` 不升格 |"
)


def patch(path: Path, what: str, old: str, new: str) -> bool:
    txt = path.read_text(encoding="utf-8")
    if MARK in txt.split("## 9. 尚未做")[0] and what.startswith("README"):
        pass
    if new in txt:
        print(f"[跳过] {path.name}：{what}（已落纸）")
        return True
    n = txt.count(old)
    if n != 1:
        print(f"❌ {path.name}：{what} 锚点命中 {n} 次")
        return False
    if APPLY:
        path.write_text(txt.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")
    return True


def ins_after(path: Path, what: str, prefix: str, new_line: str, guard: str) -> bool:
    """在 `prefix` 开头的**唯一**一行之后插入 `new_line`（幂等：`guard` 已存在则跳过）。"""
    txt = path.read_text(encoding="utf-8")
    if guard in txt:
        print(f"[跳过] {path.name}：{what}（已落纸）")
        return True
    lines = txt.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(idx) != 1:
        print(f"❌ {path.name}：{what} 的前缀命中 {len(idx)} 次（{prefix[:40]}…）")
        return False
    lines[idx[0] + 1:idx[0] + 1] = [new_line]
    if APPLY:
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")
    return True


def ins_before(path: Path, what: str, prefix: str, block: str, guard: str) -> bool:
    txt = path.read_text(encoding="utf-8")
    if guard in txt:
        print(f"[跳过] {path.name}：{what}（已落纸）")
        return True
    lines = txt.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(idx) != 1:
        print(f"❌ {path.name}：{what} 的前缀命中 {len(idx)} 次")
        return False
    lines[idx[0]:idx[0]] = block.split("\n")
    if APPLY:
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")
    return True


bad = 0
bad += not ins_after(MP, "§5 D69 决策行", "| **D68** | 2026-10-17 |", D69_DECISION, "| **D69** |")
bad += not ins_after(MP, "§6 D69 进度行", "| 2026-10-17 | **8**（报告里的 Hessian 判据 → D68） |",
                     D69_PROGRESS, "**9**（共享流 CRN 配对 → D69）")
bad += not ins_after(MP, "§7 D69 变更日志", "| 2026-10-17 | **新增 D68：", D69_CHANGELOG, "新增 D69：")
bad += not ins_after(MP, "§8 D69 附录", "| `1_Code/DDM_Core/stage8_run.py::render_group`（D68）",
                     D69_EVIDENCE, "**D69 的实测证据")
bad += not ins_before(RD, "§8.44 整节", "## 9. 尚未做", RM_844, "## 8.44 ")
bad += not ins_after(RD, "§9 第 53 项", "| 52 | ✅ **超参数 Hessian 非正定", RM_ITEM53,
                     "| 53 | ✅ **「共享流 CRN 配对」实测后不升格")
bad += not ins_after(S9, "§9 探针行", "| `1_Code/AutoRA_SPE/check_stage9_report.py` |", S9_ROW9,
                     "_probe_crn_pairing.py` | 量「同一份种子表下两个设计的相关性」")
bad += not ins_after(S9, "§11 第 30 条", "29. ❗ **`2·√2·sd` 里的 `√2` 取常数是有依据的（D64）**",
                     S9_ITEM30, "30. ❗ **「共享流 CRN 配对」量过了、不采用（D69）**")
bad += not ins_after(S9, "§12 D69 行", "| 2026-10-17 | **D41 用事实核查结案（决策 D63）**",
                     S9_CHANGELOG, "**共享流 CRN 配对：实测后不升格（决策 D69）**")
bad += not ins_after(RA, "§7 探针行", "| `stage9_report.py` | **Stage 9 落盘报告生成器**", RA_ROW,
                     "| `_probe_crn_pairing.py` |")

sys.exit(1 if bad else 0)
