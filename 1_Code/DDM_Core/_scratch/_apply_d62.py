"""把决策 **D62**（交付件依据件换档）与 **D63**（D41 用事实核查结案）写进四份文档。

D62 的内容（本轮）：
  ① 正式 `--budget 12 --n-fim 12 --noise-repeats 16` 落盘件到场（`stage9_payload_nfim12_budget12.json`，
     375296 B、`n_evals = 190`、5815 s、`n_repeats = 16`、`sd_A = 0.00746192`、`sd_B = 0.0492737`、
     `cache` 174、`pareto` 6、带外 98 / 可行 30、`manual` 臂无可行点）。
  ② 新工具 `_scratch_restamp_payload.py` 把旧判词**离线**按当前规则重算（不重跑内环）⇒ `_restamped` 件
     （377131 B、3/4 条判词变、方向不变）；交付件依据件改指它；`R1j` 从硬编码改为按 payload 现算。
  ③ ❗ 锚点在正式 `n_fim` 下 `(A)` **期望最优**（0.3401 vs 候选 0.3747–0.3852、配对 t = +25.5…+41.1）
     ⇒ 推荐点的 CRN 优势是**选择偏差方向的产物**；但锚点被 D54 带排斥 ⇒ 「更好但不可执行」。
  ④ 遗漏率带敏感性（`n_fim = 12`）：现行带下**支配锚点的可行设计 0 个**；D4 进带需上界 ≥ 0.3611。
  ⑤ 用户拍板：D55 第 18 条选 **(a)+(c)**。
  ⑥ 报告里三处「`n_fim = 1` 时代」的过时说法修正 + 牙齿 R1p-t / R1p-r2 改写 ⇒ `check_stage9_report.py` **62/62**。

D63 的内容（本轮）：
  ① 事实核查推翻 D41 的前提：本机**有**贝叶斯栈 —— `D:\\Conda\\envs\\hssm\\python.exe`
     （py3.11.15 + pymc 5.28.5 + pytensor 2.38.3 + arviz 0.23.4 + **hssm 0.3.0**）；
     默认 `python`（`D:\\Conda\\python.exe`）确实没有，这才是「没有 PPL」的来源。
  ② 用 ArviZ 在同一份逐点对数似然矩阵上**独立复核** `1_Code/DDM_Core/loo.py`：相对差 **3.54e-05**。
  ③ `pm.sample` **不可用**（`OSError [WinError -1066598273] 0xc06d007f`，缺 g++/MSVC）⇒ 主路线仍零依赖，
     ArviZ 只作外部复核；要跑 MCMC 得先装 `gxx`/MSVC Build Tools。
  ④ 牙齿：`1_Code/DDM_Core/_scratch/check_loo.py` 新增 `[D]` 三条 ⇒ **14 → 17/17**。

体例同 D61 脚本：前缀定位 + 命中数断言 + 竖线数不变 + 幂等守卫 + `--apply` 闸（写在 `save()` 里）。
"""

from __future__ import annotations

import sys
from pathlib import Path

APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
RA = ROOT / "1_Code" / "AutoRA_SPE" / "README.md"
RM = ROOT / "1_Code" / "DDM_Core" / "README.md"


def n_sep(line: str) -> int:
    return line.count("|")


def load(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def save(p: Path, text: str) -> None:
    if not APPLY:
        print(f"[干跑] 不写盘：{p.relative_to(ROOT)}")
        return
    assert text.endswith("\n"), f"{p.name}：输出必须以换行结尾"
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"✅  已写盘：{p.relative_to(ROOT)}")


def idx_of(lines: list[str], prefix: str, what: str, start: int = 0) -> int:
    hits = [i for i, l in enumerate(lines) if i >= start and l.startswith(prefix)]
    assert len(hits) == 1, f"{what}：前缀命中 {len(hits)} 行（期望 1）：{prefix[:70]!r}"
    return hits[0]


def patch_row(lines: list[str], prefix: str, old: str, new: str, what: str, expect: int = 1) -> None:
    i = idx_of(lines, prefix, what)
    line = lines[i]
    assert line.count(old) == expect, (f"{what}：行内 {old!r} 命中 {line.count(old)} 次"
                                       f"（期望 {expect}）")
    lines[i] = line.replace(old, new)
    print(f"  ✏️  {what}")


def append_in_row(lines: list[str], prefix: str, suffix: str, what: str, guard: str | None = None) -> None:
    i = idx_of(lines, prefix, what)
    line = lines[i]
    if guard and guard in line:
        print(f"  ⏭️  {what}：已含 {guard!r} ⇒ 跳过")
        return
    assert "|" not in suffix, f"{what}：后缀不得含竖线"
    n0 = n_sep(line)
    head, sep, tail = line.rpartition("|")
    assert sep and tail.strip() == "", f"{what}：行末不是闭合竖线：…{line[-40:]!r}"
    lines[i] = head.rstrip() + " " + suffix + " |"
    assert n_sep(lines[i]) == n0, f"{what}：竖线数变了 {n0} → {n_sep(lines[i])}"
    print(f"  ➕ {what}")


def ins_after(lines: list[str], anchor_prefix: str, new_lines: list[str], what: str) -> None:
    i = idx_of(lines, anchor_prefix, what)
    assert n_sep(new_lines[0]) == n_sep(lines[i]), (
        f"{what}：新行竖线数 {n_sep(new_lines[0])} != 锚点 {n_sep(lines[i])}")
    lines[i + 1:i + 1] = new_lines
    print(f"  ➕ {what}（插在第 {i + 2} 行）")


def ins_before(lines: list[str], anchor_prefix: str, block: list[str], what: str) -> None:
    i = idx_of(lines, anchor_prefix, what)
    assert lines[i - 1].strip() == "", f"{what}：锚点前一行不是空行"
    lines[i:i] = block
    print(f"  ➕ {what}（插在第 {i + 1} 行）")


# ---------------------------------------------------------------- 主计划

D62_ROW = (
    "| **D62** | 2026-10-17 | ✅ **交付件依据件换到正式 `n_fim = 12` 的 budget-12 运行；同时实测出「锚点 D4 在 `(A)` 上"
    "**期望最优**」—— 推荐点的单点优势是选择偏差方向的产物；锚点则因 D54 的带而「更好但不可执行」**。"
    "① ❗ **正式件到场**：`--budget 12 --n-fim 12 --noise-repeats 16 --seed 0` ⇒ "
    "`1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12.json`（**375296 B**、`n_evals = 190`、5815 s）；"
    "`n_repeats = 16`、`sd_A = 0.00746192`、`sd_B = 0.0492737`、`sd_omission = 0.00425987`；`cache` 174、`pareto` 6、"
    "`front_scope` 全空间（`n_evaluated == n_candidates == 174`）、`d54` 带外 98 / 可行 **30**；"
    "锚点 `A = 0.338437`、`B = 7.707485`、`feasible = False`；推荐点 "
    "`T[33.33/149.99/249.98/449.98]ms x W[1199.90/1799.90/2399.80]ms x r12`（`A = 0.376187`、`B = 8.735884`）；"
    "四臂 `random` 0.380122（5 可行）/ `grid` 0.387396（3）/ `bo` 0.480407（4）/ **`manual` `A_best = inf`（0 可行）**；"
    "该件启动早于 D60 的 `VERDICT_LOGIC` ⇒ **无 `verdict_logic` 键**、转印判词带的是旧带 0.0149 / 0.0985。"
    "② **新工具 `1_Code/AutoRA_SPE/_scratch_restamp_payload.py`（124 行）**：读源件的 `histories` + `noise`，"
    "用当前 `stage9_loop.compare_arms(_norm_histories(...))` **离线重算** `compare` 段并写 `provenance`"
    "（`source` / `source_verdict_logic` / `band_factor` / `n_verdicts_changed` / `old_verdicts`），"
    "其余字段逐字继承、**不重跑任何内环** ⇒ `stage9_payload_nfim12_budget12_restamped.json`（**377131 B**）："
    "旧带 0.0149 / 0.0985 → 新带 **0.0211 / 0.1394**、**3/4 条判词不同**（`random`/`grid`/`bo` 的阈值数字变，"
    "**方向一条都没变**；`manual` 的 `∞` 分支逐字相同）。干跑还验过机制在「本该不变」处确实不变（budget-1 件 0 条变）。"
    "③ **依据件换档**（换的是「以哪一次运行为准」，不是判据）：`1_Code/AutoRA_SPE/check_stage9_report.py::_REAL` "
    "改指 **`_restamped`** 件（`provenance` 记明来路）；`R1j` 从硬编码「旧版措辞告警**不得**出现」改为**按 payload 现算**"
    "（`_has_inf_arm = any(not math.isfinite(float(r.get(\"A_best\", inf))) for r in d[\"compare\"])`）——"
    "因为正式件里 `manual` 没有可行点、这条告警**应该**出现；原先的硬编码只对 `n_fim = 1` 那批成立。"
    "④ ❗❗ **锚点在 `(A)` 上期望最优（与 `n_fim = 1` 那轮结论相反）**：`_scratch_mean_A_rank.py` 在正式件上跑 "
    "32 个无关种子（7769.9 s）⇒ 按**种子均值**升序 ① **锚点 D4 = 0.340119 ± 0.001394**（CRN 读数 0.338437、偏差 **−0.21σ**）"
    "② 0.374739 ③ 0.375209 ④ 0.383809 ⑤ 0.383816 ⑥ 0.384073（= 推荐点）⑦ 0.385240；**按 CRN 排序锚点也是第 1**；"
    "6 个候选的**配对均值差全部为正且显著**：`+0.034620 ± 0.001242`（t = +27.87）、`+0.035089 ± 0.001376`（t = +25.49）、"
    "`+0.043690 ± 0.001208`（t = +36.18）、`+0.043697 ± 0.001063`（t = +41.10）、`+0.043954 ± 0.001240`（t = +35.43）、"
    "`+0.045121 ± 0.001235`（t = +36.52）⇒ **期望意义上锚点比全部候选好 0.035–0.045**；`n_fim = 1` 那档同向"
    "（锚点 0.357344 vs 推荐点 0.386742）⇒ **「推荐点 `(A)` 比锚点小 0.0378」是 CRN 单点 + 选择偏差的合成结果**。"
    "⚠️ 但这**不改变推荐点**：锚点被 D54 的遗漏率带排斥（**0.3546** 远在 `[0.05, 0.2]` 外）⇒ 它是「`(A)` 更好但"
    "**不可执行**」，推荐点仍是**可行集**内 `(A)` 最小者；论文必须**同时**报这两个事实。"
    "⑤ **遗漏率带敏感性（`n_fim = 12`）**：现行带下可行 30（遗漏 0.1788 / 中位 0.1908 / 0.1975）、只被带否决 21"
    "（0.2005–0.3647）、全 174 个 0.1102–0.4644；**支配锚点的可行设计 0 个**（`n_fim = 1` 那档是 5 个 ⇒ "
    "「支配数」本身对 `n_fim` 敏感）；上界放到 0.20/0.25/0.30 时最优 `A` = 0.3762/0.3717/0.3497 且支配数仍 0、"
    "0.35 ⇒ 0.3162（2 个）、**0.3611 ⇒ D4 进带**（3 个）；**下界 0.05 从未生效**（候选最小值 0.1102）；"
    "比值口径 (c)：推荐点 `A/A(D4) = 1.1115`、`B/B(D4) = 1.1334`。"
    "⑥ **用户拍板（本轮输入）**：D55 第 18 条选 **(a)+(c)** —— 保持冻结规格不动、把「锚点落在带外」作为 **9A 头条结论**报出，"
    "并同时给 D4 归一化的比值口径（⇒ 🛑 该待办**关闭**）。"
    "⑦ **报告里三处「`n_fim = 1` 时代」的过时说法修正** + 牙齿：§3 的「`n_fim = 1` 这批候选里两者恰好重合」改为 D61 的"
    "「两档逐设计相同 ⇒ 结构性质」、§3 的「**须在正式 `n_fim` 下重测这一节**」改为「D61 已重测：仍 123/174、"
    "`cond` 2.231e15 → 2.013e15」、§8 第 4 条「病态比例是本次 `n_fim` 的产物」**翻转为「不是」**；§7 新增 D62 段"
    "（锚点种子均值 + 「换 payload 须另算」边界）；`check_stage9_report.py` 新增 **R1p-t**（这两句不得再出现、须说「结构性质」）"
    "并把 **R1p-r2** 从「必须自认没算过」改写为「必须同时给实测与边界」⇒ **61/61 → 62/62**；交付件 `stage9_report.md` "
    "**152 → 154 行**。"
    "⑧ **尚未做**：「共享流 CRN 配对」是否升格为正式判据（会把系数从 2.83 收到 1.1–2.0，需重做 D60 登记）、"
    "四个用户侧 Stage、真实数据到手后的 `cellmean.py` 剖面诊断。"
    " | 正式件（375296 B、`n_evals = 190`、`sd_A = 0.00746192`、`manual` 无可行点）、"
    "`1_Code/AutoRA_SPE/_scratch_restamp_payload.py`（**新建**，124 行）+ `_scratch_restamp_formal_u8.txt`"
    "（3/4 条判词变、方向不变）、`_restamped` 件（377131 B）、"
    "`1_Code/AutoRA_SPE/_scratch_mean_A_rank_nfim12_u8.txt`（32 种子、措点均值 0.340119 ± 0.001394、配对 t +25.5…+41.1）、"
    "`_scratch_probe_band_sensitivity_nfim12_u8.txt`（带敏感性）、"
    "`python -X utf8 -u 1_Code\\AutoRA_SPE\\check_stage9_report.py` ⇒ **62/62、未通过 0 项**、`_scratch_check_stage9_report_d62_u8.txt`"
    " | 交付件依据件 = `stage9_payload_nfim12_budget12_restamped.json`；**设计读数一个都没动**（换档只改「以哪一次运行为准」）；"
    "判词方向不变（3/4 条只是阈值数字变）；🛑 D55 第 18 条**关闭**（用户选 (a)+(c)）"
    " |"
)

D63_ROW = (
    "| **D63** | 2026-10-17 | ✅ **D41 用「事实核查」结案（不是拍板）：本机其实有完整贝叶斯栈，`pymc`/`arviz` 的缺席只发生在"
    "默认解释器上；已用 ArviZ 在**同一份逐点对数似然矩阵**上独立复核 `loo.py` 的手写 PSIS-LOO（相对差 3.54e-05）；"
    "但 `pm.sample` 不可用（缺 g++/MSVC）⇒ 主路线仍零依赖**。"
    "① ❗ **前提被推翻**：默认 `python` = `D:\\Conda\\python.exe`（确实无 `pymc`/`arviz`/`pytensor`）—— D41 当初只查了这一个"
    "解释器；实测另有两个环境装了贝叶斯栈：**`D:\\Conda\\envs\\hssm\\python.exe`**（Python **3.11.15**、"
    "**pymc 5.28.5**、pytensor 2.38.3、**arviz 0.23.4**、**hssm 0.3.0**、numpy 2.4.6、scipy 1.17.1、pandas 2.3.3）与 "
    "`C:\\Users\\蔡振辛\\AppData\\Local\\Programs\\Python\\Python313\\python.exe`（pymc 5.25.1、arviz 0.20.0，无 `hssm`）。"
    "定位手段：`Get-Command python`/`py -0p`/`where.exe python` + 在 8 个候选根上按目录名 `pymc` 扫（`D:\\Conda\\envs\\*`、"
    "`C:\\Python314`、Python313/312 用户安装、`D:\\psychopy`）。"
    "② ✅ **ArviZ 独立复核通过**（`_probe_bayes_stack.py`，79 行）：同一 `(S = 2000, N = 40)` 矩阵上，"
    "本仓库 `psis_loo` 给 `elpd_loo = -53.814882`、`se = 4.082616`、`p_loo = 0.778425`、`k_max = 0.0591`；"
    "`az.loo` 给 `-53.816786`、`4.031690`、`0.780329`、`k_max = 0.1208` ⇒ **`elpd_loo` 相对差 3.54e-05**"
    "（`p_loo` 差 0.0019；`k_max` 差 0.062 是两条 GPD 尾部截断/平滑实现不同所致，两者都远低于 0.7）⇒ "
    "手写 PSIS-LOO **不是自说自话**。（`az.loo` 需要 `posterior` 组在场，占位即可：`TypeError: Must be able to extract "
    "a posterior group from data.` 是缺该组。）"
    "③ ❗ **`pm.sample` 不可用**：`OSError: [WinError -1066598273] Windows Error 0xc06d007f`；"
    "`pytensor.config.cxx = ''`、`g++` 未安装 ⇒ C 实现不可用、Python 回退时 DLL 加载失败 ⇒ **本机不能跑 MCMC**"
    "（`hssm` 拟合也跑不了）。⇒ 主路线仍走**零依赖**（§8.22 + §8.28），ArviZ 只作**外部复核**；若要 MCMC，"
    "先装 `conda install -n hssm gxx` 或 MSVC Build Tools，再重跑本探针。"
    "④ **牙齿**：`1_Code/DDM_Core/_scratch/check_loo.py` 新增 `[D]` 三条 —— **D1** 交叉复核日志必须在场且自报一致、"
    "**D2** 相对差 < 1e-3、**D3** 日志必须记下 pymc 版本与「采样能否用」⇒ **14 → 17/17、exit 0**；"
    "守的是「文档里那句『ArviZ 复核一致』指得到的文件确实存在且结论如此」。"
    "⑤ **结案口径**：D41 从「🛑 需拍板」改为「✅ 已核查结案」—— 主路线不变（零依赖），"
    "「装不装 pymc」这个**拍板项消失**（它已经在别的环境里装好了，只是本机跑不了采样）。"
    " | `1_Code/DDM_Core/_scratch/_probe_bayes_stack.py`（**新建**，79 行）+ `_probe_bayes_stack_u8.txt`、"
    "`1_Code/DDM_Core/_scratch/check_loo.py`（**17/17**）+ `_scratch_check_loo_d63_u8.txt`、"
    "环境清单（`hssm` env：pymc 5.28.5 / pytensor 2.38.3 / arviz 0.23.4 / hssm 0.3.0） "
    " | `1_Code/DDM_Core/loo.py` **一行未改**（复核是外部证据，不是改代码）；"
    "Stage 8 的模型比较结论不变；`1_Code/DDM_Core/README.md` §9 第 28 项（D41）关闭"
    " |"
)

D62_PROGRESS = (
    "| 2026-10-17 | **9**（交付件依据件换档 + 锚点的期望排名 + 带敏感性 → D62） | "
    "**把交付件的依据件从 `n_fim = 1` 换到正式 `n_fim = 12`，并在换档过程中发现「锚点在 `(A)` 上其实期望最优」**。"
    "① 正式 budget-12 件到场（375296 B、`n_evals = 190`、5815 s、`n_repeats = 16`、`sd_A = 0.00746192`、"
    "`cache` 174、可行 30、`manual` 无可行点）；"
    "② 新工具 `_scratch_restamp_payload.py` 离线重算 `compare` 段 ⇒ `_restamped` 件（377131 B、3/4 条判词变、方向不变）；"
    "③ 依据件换档 + `R1j` 改按 payload 现算（`manual` 无可行点 ⇒ 告警**应该**出现）；"
    "④ ❗ 32 种子的均值排名：锚点 **0.340119 ± 0.001394** 居首、6 个候选 0.374739–0.385240 全部更差"
    "（配对 t = +25.5…+41.1）⇒ 推荐点的单点优势是选择偏差方向的产物，但锚点被 D54 带排斥 ⇒「更好但不可执行」；"
    "⑤ 带敏感性：现行带下**支配锚点的可行设计 0 个**、D4 进带需上界 ≥ 0.3611；"
    "⑥ 用户拍板 D55 第 18 条 = (a)+(c) ⇒ **该待办关闭** | "
    "`1_Code/AutoRA_SPE/stage9_report.py`（**546 行**）、`1_Code/AutoRA_SPE/stage9_report.md`（**154 行**）、"
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（**460 行、62/62**）、"
    "`1_Code/AutoRA_SPE/_scratch_restamp_payload.py`（**新**，124 行）、"
    "`1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12_restamped.json`（**新**，377131 B） | "
    "**(1)** 「共享流 CRN 配对」是否升格为正式判据（系数 2.83 → 1.1–2.0，需重做 D60 登记）；"
    "**(2)** 四个用户侧 Stage（1 实机验收 / 6 Pilot / 7 正式采集 / 定稿签批）；"
    "**(3)** 真实数据到手后的 `cellmean.py` 剖面诊断 |"
)

D63_PROGRESS = (
    "| 2026-10-17 | **8**（D41 的依赖问题 → 事实核查结案 → D63） | "
    "**D41 不靠拍板、靠核查：本机有完整贝叶斯栈，只是不在默认解释器上**。"
    "① `D:\\Conda\\envs\\hssm`：py3.11.15 + pymc 5.28.5 + pytensor 2.38.3 + arviz 0.23.4 + **hssm 0.3.0**；"
    "另一处 Python313 用户安装有 pymc 5.25.1 / arviz 0.20.0；"
    "② 用 ArviZ 在同一矩阵上复核 `loo.py`：`elpd_loo` −53.814882 vs −53.816786 ⇒ **相对差 3.54e-05**；"
    "③ `pm.sample` 不可用（`0xc06d007f`、无 g++）⇒ 主路线仍零依赖、ArviZ 只作外部复核；"
    "④ 牙齿：`check_loo.py` **14 → 17/17** | "
    "`1_Code/DDM_Core/_scratch/_probe_bayes_stack.py`（**新**，79 行）、"
    "`1_Code/DDM_Core/_scratch/check_loo.py`（**17/17**） | "
    "**(1)** 若要 MCMC：装 `gxx`/MSVC Build Tools 后重跑探针；**(2)** 用户侧四个 Stage |"
)

D62_CHANGELOG = (
    "| 2026-10-17 | **新增 D62：交付件依据件换到正式 `n_fim = 12` 的 budget-12 件（`_restamped`、375296 → 377131 B）；"
    "实测锚点 D4 在 `(A)` 上**期望最优**（0.340119 ± 0.001394，6 个候选 0.374739–0.385240 全部更差、配对 t = +25.5…+41.1）"
    "⇒ 推荐点的单点优势是选择偏差方向的产物（但锚点被 D54 带排斥 ⇒「更好但不可执行」）；带敏感性：现行带下支配锚点的可行设计 **0** 个、"
    "D4 进带需上界 ≥ 0.3611；新工具 `_scratch_restamp_payload.py`（124 行）离线重算判词；报告三处过时说法修正 + R1p-t/R1p-r2**："
    "`stage9_report.py` 529 → **546 行**、`check_stage9_report.py` 427 → **460 行（61/61 → 62/62）**、"
    "`stage9_report.md` 149 → **154 行**；§11 新增第 27 条；证据：`_scratch_restamp_formal_u8.txt`、"
    "`_scratch_mean_A_rank_nfim12_u8.txt`、`_scratch_probe_band_sensitivity_nfim12_u8.txt`、"
    "`_scratch_check_stage9_report_d62_u8.txt`、`1_Code/DDM_Core/README.md` §8.37、§9 第 46 项 |"
)

D63_CHANGELOG = (
    "| 2026-10-17 | **新增 D63：D41 用事实核查结案 —— 本机 `D:\\Conda\\envs\\hssm` 里有 pymc 5.28.5 + arviz 0.23.4 + hssm 0.3.0"
    "（默认 `D:\\Conda\\python.exe` 没有）；用 ArviZ 独立复核 `loo.py` 的手写 PSIS-LOO（`elpd_loo` 相对差 **3.54e-05**）；"
    "`pm.sample` 不可用（`0xc06d007f`、无 g++）⇒ 主路线仍零依赖；`check_loo.py` 新增 `[D]` 三条 ⇒ 14 → **17/17**；"
    "§11 新增第 28 条；证据：`1_Code/DDM_Core/_scratch/_probe_bayes_stack_u8.txt`、`_scratch_check_loo_d63_u8.txt`、"
    "`1_Code/DDM_Core/README.md` §8.38、§9 第 47 项** |"
)

D62_APPENDIX = (
    "| `1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12.json`（**新**，375296 B）"
    " + `1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12_restamped.json`（**新**，377131 B）"
    " + `1_Code/AutoRA_SPE/_scratch_restamp_payload.py`（**新**，124 行）"
    " + `1_Code/AutoRA_SPE/stage9_report.py`（529 → **546 行**） + `1_Code/AutoRA_SPE/stage9_report.md`（149 → **154 行**）"
    " + `1_Code/AutoRA_SPE/check_stage9_report.py`（427 → **460 行**、61/61 → **62/62**） | "
    "依据件换档（`_REAL` 改指 `_restamped`、`R1j` 按 payload 现算）；锚点种子均值排名（0.340119 ± 0.001394 居首、"
    "6 个候选配对 t = +25.49…+41.10）；带敏感性（现行带支配锚点 0 个、D4 进带需 ≥ 0.3611、下界 0.05 从未生效）；"
    "报告过时说法修正三处 + R1p-t/R1p-r2 |"
)

D63_APPENDIX = (
    "| `1_Code/DDM_Core/_scratch/_probe_bayes_stack.py`（**新建**，79 行）"
    " + `1_Code/DDM_Core/_scratch/check_loo.py`（14 → **17/17**） | "
    "`hssm` env 版本清单（py3.11.15 / pymc 5.28.5 / pytensor 2.38.3 / arviz 0.23.4 / hssm 0.3.0 / numpy 2.4.6 / scipy 1.17.1）；"
    "`az.loo` 与 `psis_loo` 在同一矩阵上的逐项差（`elpd_loo` 3.54e-05 相对、`p_loo` 0.0019、`k_max` 0.062）；"
    "`pm.sample` 的 `OSError [WinError -1066598273] 0xc06d007f` |"
)


def do_master_plan() -> None:
    text = load(MP)
    if "| **D62** | 2026-10-17 |" in text:
        print(f"[跳过] {MP.name}：D62/D63 已落纸")
        return
    lines = text.splitlines()
    ins_after(lines, "| **D61** | 2026-10-16 |", [D62_ROW], "主计划 §5 决策行 D62")
    i62 = idx_of(lines, "| **D62** | 2026-10-17 |", "主计划 §5 决策行 D62（定位）")
    ins_after(lines, "| **D62** | 2026-10-17 |", [D63_ROW], "主计划 §5 决策行 D63")
    assert idx_of(lines, "| **D63** | 2026-10-17 |", "决策行 D63 定位") == i62 + 1
    ins_after(lines, "| 2026-10-16 | **9**（可行域铺开度与「推荐点」的身份 → D61） |",
              [D62_PROGRESS], "主计划 §6 进度行 D62")
    ins_after(lines, "| 2026-10-17 | **9**（交付件依据件换档", [D63_PROGRESS], "主计划 §6 进度行 D63")
    ins_after(lines, "| 2026-10-16 | **新增 D61：", [D62_CHANGELOG], "主计划 §7 变更日志 D62")
    ins_after(lines, "| 2026-10-17 | **新增 D62：交付件依据件换到正式", [D63_CHANGELOG], "主计划 §7 变更日志 D63")
    ins_after(lines, "| `1_Code/AutoRA_SPE/stage9_report.py`（494 → **529 行**）", [D62_APPENDIX],
              "主计划 §8 附录证据 D62")
    ins_after(lines, "| `1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12.json`（**新**，375296 B）", [D63_APPENDIX],
              "主计划 §8 附录证据 D63")
    save(MP, "\n".join(lines) + "\n")


def do_stage9() -> None:
    text = load(S9)
    if "（决策 D62）" in text:
        print(f"[跳过] {S9.name}：D62/D63 已落纸")
        return
    lines = text.splitlines()
    P_MD = "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告"
    P_GEN = "| `1_Code/AutoRA_SPE/stage9_report.py` | 落盘报告生成器"
    P_CG = "| `1_Code/AutoRA_SPE/check_stage9_report.py` | 报告生成器自测"
    P_AGG = "| `1_Code/AutoRA_SPE/check_stage9.py` | 汇总自测"
    patch_row(lines, P_MD, "**149 行**", "**154 行**", "Stage9 §9：stage9_report.md 149 → 154")
    append_in_row(lines, P_MD, "D62 起依据件 = 正式 `n_fim = 12` 的 budget-12 件（`_restamped`）",
                  "Stage9 §9：stage9_report.md 的 D62 注记")
    patch_row(lines, P_GEN, "**529 行**", "**546 行**", "Stage9 §9：stage9_report.py 529 → 546")
    append_in_row(lines, P_GEN,
                  "D62 起 §3/§8 的「病态比例是 `n_fim` 的产物」改为「结构性质」，§7 补锚点种子均值实测",
                  "Stage9 §9：stage9_report.py 的 D62 注记")
    patch_row(lines, P_CG, "**427 行**", "**460 行**", "Stage9 §9：check_stage9_report 427 → 460")
    patch_row(lines, P_CG, "**61/61 通过、exit 0**", "**62/62 通过、exit 0**",
              "Stage9 §9：check_stage9_report 61/61 → 62/62")
    append_in_row(lines, P_CG,
                  "D62 新增 R1p-t（过时说法不得再出现）并改写 R1p-r2（实测 + 边界两条都在）",
                  "Stage9 §9：check_stage9_report 的 D62 注记")
    append_in_row(lines, P_AGG, "（`S5` 的计数沿革：D57 47/47 ⇒ D60 57/57 ⇒ D61 61/61 ⇒ D62 **62/62**）",
                  "Stage9 §9：check_stage9 的 S5 计数沿革（D62）", guard="D62 **62/62**")
    ins_after(lines, "26. ❗ **「推荐点」不是唯一解", [S9_11_27], "Stage9 §11 第 27 条（D62）")
    ins_after(lines, "27. ❗ **交付件的依据件是「正式 `n_fim = 12`", [S9_11_28], "Stage9 §11 第 28 条（D63）")
    ins_after(lines, "| 2026-10-16 | **可行集铺开度与「推荐点」的身份（决策 D61）**", [S9_12_D62],
              "Stage9 §12 D62 行")
    ins_after(lines, "| 2026-10-17 | **交付件依据件换档", [S9_12_D63], "Stage9 §12 D63 行")
    save(S9, "\n".join(lines) + "\n")


def do_autora_readme() -> None:
    text = load(RA)
    if "D62 起 §3/§8" in text:
        print(f"[跳过] {RA.name}：D62 已落纸")
        return
    lines = text.splitlines()
    P_GEN = "| `stage9_report.py` | **Stage 9 落盘报告生成器**"
    P_CG = "| `check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, P_GEN, "**529 行**", "**546 行**", "AutoRA README §7：stage9_report.py 529 → 546")
    append_in_row(lines, P_GEN, "D62 起 §3/§8 把「病态比例是 `n_fim` 的产物」改为「结构性质」、§7 补锚点种子均值实测",
                  "AutoRA README §7：stage9_report.py 的 D62 注记")
    patch_row(lines, P_CG, "**427 行、61/61", "**460 行、62/62", "AutoRA README §7：check_stage9_report")
    append_in_row(lines, P_CG, "D62 新增 R1p-t 并改写 R1p-r2", "AutoRA README §7：check_stage9_report 的 D62 注记")
    save(RA, "\n".join(lines) + "\n")


def do_ddm_readme() -> None:
    text = load(RM)
    if "## 8.37 " in text:
        print(f"[跳过] {RM.name}：D62/D63 已落纸")
        return
    lines = text.splitlines()
    ins_before(lines, "## 9. 尚未做", RM_837 + [RM_838_hdr] + RM_838,
               "DDM README §8.37 + §8.38（插在「## 9. 尚未做」前）")
    ins_after(lines, "| 45 | ✅ **可行集铺开度", [RM_ITEM46], "DDM README §9 第 46 项")
    ins_after(lines, "| 46 | ✅ **交付件依据件", [RM_ITEM47], "DDM README §9 第 47 项")
    append_in_row(lines, "| 28 | 🛑 **Stage 8 的依赖决定需拍板（D41）** |",
                  "✅ **2026-10-17 结案（D63，§8.38）**：本机 `D:\\Conda\\envs\\hssm` 里其实有 pymc 5.28.5 + arviz 0.23.4 + "
                  "hssm 0.3.0（默认 `D:\\Conda\\python.exe` 没有）⇒「装不装」的拍板项消失；已用 ArviZ 在同一矩阵上复核 "
                  "`loo.py`（`elpd_loo` 相对差 **3.54e-05**）；但 `pm.sample` 不可用（`0xc06d007f`、无 g++）⇒ **主路线仍零依赖**，"
                  "ArviZ 只作外部复核。",
                  "DDM README §9 第 28 项的 D63 结案注记", guard="已用 ArviZ 在同一矩阵上复核")
    save(RM, "\n".join(lines) + "\n")


# ---------------------------------------------------------------- 文本常量（Stage9 / DDM README）

S9_11_27 = (
    "27. ❗ **交付件的依据件是「正式 `n_fim = 12` 的 budget-12 件」，而且它的判词是由 `_restamped` 件提供的（D62）**："
    "`1_Code/AutoRA_SPE/check_stage9_report.py::_REAL` 指向 `1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12_restamped.json`"
    "（377131 B）—— 原始件 `stage9_payload_nfim12_budget12.json`（375296 B）的 `compare` 段是**旧规则**生成的（无 `verdict_logic`），"
    "`_scratch_restamp_payload.py` 用当前 `compare_arms` 离线重算后写 `provenance`、其余字段逐字继承（**不重跑内环**）⇒ "
    "3/4 条判词变、方向不变。报告里三处「`n_fim = 1` 时代」的说法必须随之修正（§3 的「恰好重合」、§3 的「须在正式 `n_fim` 下重测」、"
    "§8 第 4 条），否则报告会在**它自己已经测过**的事情上说「还没测」。"
)
S9_11_28 = (
    "28. ❗ **锚点的「更好」与「可执行」是两件事：锚点在 `(A)` 上期望最优，但被 D54 的带排斥（D62）**："
    "正式 `n_fim = 12` 件上跑 32 个无关种子 ⇒ 锚点 D4 的种子均值 `(A) = 0.340119 ± 0.001394` 排第 1，"
    "6 个候选（含推荐点 0.384073）全部更差（配对 `t = +25.5…+41.1`）⇒ **单点 CRN 读数里「推荐点更好」是选择偏差方向的产物**；"
    "但锚点的遗漏率 **0.3546** 远在冻结带 `[0.05, 0.2]` 外 ⇒ 它**不可执行**。论文必须同时报这两个事实："
    "「按 `(A)` 的期望，锚点最好；按冻结的遗漏率带，锚点不可用」——只说一个都会误导。"
    "另：现行带下**支配锚点的可行设计 0 个**（`n_fim = 1` 那档是 5 个 ⇒ 支配数本身对 `n_fim` 敏感）。"
)
S9_12_D62 = (
    "| 2026-10-17 | **交付件依据件换档 + 锚点在 `(A)` 上的期望排名（决策 D62）**：依据件由 "
    "`stage9_payload_nfim1_budget12.json` 换到 `stage9_payload_nfim12_budget12_restamped.json`（原始件 375296 B → "
    "restamped 377131 B，`_scratch_restamp_payload.py` 离线重算 3/4 条判词、方向不变）；`R1j` 从硬编码改为按 payload 现算；"
    "32 种子均值排名：锚点 **0.340119 ± 0.001394** 居首、6 个候选 0.374739–0.385240 全部更差（配对 t = +25.49…+41.10）；"
    "带敏感性：现行带下支配锚点的可行设计 **0** 个、D4 进带需上界 ≥ 0.3611；报告修正三处过时说法 + R1p-t/R1p-r2 ⇒ "
    "`check_stage9_report.py` **62/62**、交付件 **154 行** "
    "| `1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12_restamped.json`（**新**，377131 B）、"
    "`1_Code/AutoRA_SPE/_scratch_restamp_payload.py`（**新**，124 行）、`_scratch_mean_A_rank_nfim12_u8.txt`、"
    "`_scratch_probe_band_sensitivity_nfim12_u8.txt`、`_scratch_check_stage9_report_d62_u8.txt` |"
)
S9_12_D63 = (
    "| 2026-10-17 | **D41 用事实核查结案（决策 D63）**：本机 `D:\\Conda\\envs\\hssm\\python.exe` 有 "
    "pymc 5.28.5 + pytensor 2.38.3 + arviz 0.23.4 + **hssm 0.3.0**（默认 `D:\\Conda\\python.exe` 没有）；"
    "用 ArviZ 在同一 `(2000, 40)` 矩阵上复核 `1_Code/DDM_Core/loo.py` 的 `psis_loo` ⇒ `elpd_loo` −53.814882 vs "
    "−53.816786（**相对差 3.54e-05**）、`p_loo` 0.778425 vs 0.780329；`pm.sample` 不可用"
    "（`OSError [WinError -1066598273] 0xc06d007f`、`pytensor.config.cxx = ''`、无 g++）⇒ 主路线仍零依赖；"
    "`check_loo.py` 新增 `[D]` 三条 ⇒ **17/17** "
    "| `1_Code/DDM_Core/_scratch/_probe_bayes_stack.py`（**新**，79 行）+ `_probe_bayes_stack_u8.txt`、"
    "`check_loo.py` **17/17**（`_scratch_check_loo_d63_u8.txt`）、环境清单（`hssm` env） |"
)

RM_837 = [
    "## 8.37 交付件依据件换到正式 `n_fim = 12`；锚点在 `(A)` 上其实期望最优（2026-10-17，D62）",
    "",
    "**动机**：D60/D61 之后判词与带宽都改过，但交付件的依据件仍是 `n_fim = 1` 那一批。正式 budget-12 运行"
    "（`--budget 12 --n-fim 12 --noise-repeats 16`）落盘后，必须换档并重判「锚点 vs 推荐点」。",
    "",
    "**① 正式件与 `_restamped` 件**：`1_Code/AutoRA_SPE/stage9_payload_nfim12_budget12.json`（375296 B、`n_evals = 190`、"
    "5815 s、`n_repeats = 16`、`sd_A = 0.00746192`、`sd_B = 0.0492737`、`sd_omission = 0.00425987`、`cache` 174、"
    "`pareto` 6、带外 98 / 可行 **30**、`manual` 臂 `A_best = inf`）；它启动早于 `VERDICT_LOGIC` ⇒ 无该键。"
    "`1_Code/AutoRA_SPE/_scratch_restamp_payload.py`（124 行）读 `histories` + `noise`、用当前 `compare_arms` **离线重算** "
    "`compare` 段并写 `provenance`，其余字段逐字继承 ⇒ `stage9_payload_nfim12_budget12_restamped.json`（377131 B）："
    "旧带 0.0149 / 0.0985 → 新带 **0.0211 / 0.1394**、**3/4 条判词不同**（只是阈值数字变，**方向一条都没变**）。",
    "",
    "**② 依据件换档**：`check_stage9_report.py::_REAL` 改指 `_restamped` 件；`R1j` 从「旧版措辞告警**不得**出现」"
    "改为**按 payload 现算**（`_has_inf_arm = any(not math.isfinite(float(r.get(\"A_best\", inf))) for r in d[\"compare\"])`）"
    "—— 正式件里 `manual` 没有可行点，这条告警**应该**出现；旧硬编码只对 `n_fim = 1` 那批成立。",
    "",
    "**③ ❗ 锚点在 `(A)` 上期望最优**（`_scratch_mean_A_rank_nfim12_u8.txt`，32 个无关种子、7769.9 s）："
    "锚点 D4 种子均值 **0.340119 ± 0.001394**（CRN 0.338437、偏差 −0.21σ）> 候选 0.374739 / 0.375209 / 0.383809 / "
    "0.383816 / 0.384073（推荐点）/ 0.385240；6 个配对差全部为正且显著（`t = +25.49…+41.10`）⇒ "
    "**期望意义上锚点好 0.035–0.045**；`n_fim = 1` 那档同向（0.357344 vs 0.386742）。"
    "⚠️ 锚点被 D54 的带排斥（遗漏 **0.3546**）⇒「`(A)` 更好但**不可执行**」，推荐点仍是可行集内 `(A)` 最小者。",
    "",
    "**④ 遗漏率带敏感性（`n_fim = 12`）**：现行带 30 可行（遗漏 0.1788 / 中位 0.1908 / 0.1975）、只被带否决 21、"
    "全 174 个 0.1102–0.4644；**支配锚点的可行设计 0 个**（`n_fim = 1` 档 5 个）；上界 0.20/0.25/0.30 ⇒ 最优 `A` "
    "0.3762/0.3717/0.3497（支配数仍 0）、0.35 ⇒ 0.3162（2 个）、**0.3611 ⇒ D4 进带**（3 个）；下界 0.05 从未生效；"
    "比值口径：`A/A(D4) = 1.1115`、`B/B(D4) = 1.1334`。用户拍板 D55 第 18 条 = **(a)+(c)** ⇒ 该待办关闭。",
    "",
    "**⑤ 报告修正与牙齿**：§3 的「`n_fim = 1` 这批候选里两者恰好重合」→ D61 的「两档逐设计相同 ⇒ 结构性质」；"
    "§3 的「须在正式 `n_fim` 下重测这一节」→「D61 已重测：仍 123/174、`cond` 2.231e15 → 2.013e15」；"
    "§8 第 4 条「病态比例是本次 `n_fim` 的产物」**翻转为「不是」**；§7 新增 D62 段。"
    "牙齿 **R1p-t**（这两句不得再出现、须说「结构性质」）+ **R1p-r2** 改写（实测与边界两条都在）⇒ **61/61 → 62/62**；"
    "交付件 **152 → 154 行**。",
    "",
    "**⑥ 尚未做**：「共享流 CRN 配对」是否升格为正式判据（系数 2.83 → 1.1–2.0，需重做 D60 登记）；四个用户侧 Stage；"
    "真实数据到手后的 `cellmean.py` 剖面诊断。",
    "",
]

RM_838_hdr = "## 8.38 本机其实有完整贝叶斯栈；ArviZ 独立复核了手写 PSIS-LOO（2026-10-17，D63）"
RM_838 = [
    "",
    "**结论**：`D:\\Conda\\envs\\hssm\\python.exe` 里装着 **pymc 5.28.5 + pytensor 2.38.3 + arviz 0.23.4 + hssm 0.3.0**"
    "（Python 3.11.15、numpy 2.4.6、scipy 1.17.1）；另一处 `C:\\Users\\蔡振辛\\AppData\\Local\\Programs\\Python\\Python313`"
    "有 pymc 5.25.1 / arviz 0.20.0（无 `hssm`）。**默认 `python`（`D:\\Conda\\python.exe`）确实没有**——D41 当初只查了它，"
    "所以「本机没有任何贝叶斯栈」这个前提是**错的**。",
    "",
    "**交叉复核**（`1_Code/DDM_Core/_scratch/_probe_bayes_stack.py`，79 行）：同一 `(S = 2000, N = 40)` 逐点对数似然矩阵上，"
    "`loo.psis_loo` 给 `elpd_loo = -53.814882`、`se = 4.082616`、`p_loo = 0.778425`、`k_max = 0.0591`；"
    "`arviz.loo`（需一个占位 `posterior` 组）给 `-53.816786`、`4.031690`、`0.780329`、`k_max = 0.1208` ⇒ "
    "**`elpd_loo` 相对差 3.54e-05**；`k_max` 差 0.062 是两条 GPD 尾部截断/平滑实现的差别，两者都远低于 0.7。",
    "",
    "**不能做的事**：`pm.sample` 抛 `OSError: [WinError -1066598273] Windows Error 0xc06d007f`；"
    "`pytensor.config.cxx = ''` 且 `g++` 未安装 ⇒ C 实现不可用、Python 回退时 DLL 加载失败 ⇒ **本机跑不了 MCMC**"
    "（`hssm` 拟合同样跑不了）。要跑就得先装 `conda install -n hssm gxx` 或 MSVC Build Tools。",
    "",
    "**⇒ 决定（D63）**：主路线仍走**零依赖**（§8.22 + §8.28），ArviZ 只作**外部复核**；D41 从「🛑 需拍板」改为"
    "「✅ 已核查结案」——「装不装 pymc」这个拍板项消失。",
    "",
    "**牙齿**：`1_Code/DDM_Core/_scratch/check_loo.py` 新增 `[D]` 三条 —— **D1** 复核日志在场且自报一致、"
    "**D2** 相对差 < 1e-3、**D3** 日志记下 pymc 版本与采样可用性 ⇒ **14 → 17/17、exit 0**。",
    "",
]

RM_ITEM46 = (
    "| 46 | ✅ **交付件依据件 = 正式 `n_fim = 12` 的 budget-12 件（`_restamped`）；锚点在 `(A)` 上期望最优但被 D54 带排斥（D62，§8.37）** | "
    "原始件 375296 B → `_restamped` 377131 B（离线重算 3/4 条判词、方向不变）；32 种子均值：锚点 **0.340119 ± 0.001394** 居首、"
    "6 个候选 0.374739–0.385240 全部更差（配对 t = +25.49…+41.10）⇒ 推荐点的单点优势是选择偏差方向的产物，"
    "而锚点遗漏率 0.3546 在带外 ⇒「更好但不可执行」；带敏感性：现行带支配锚点 **0** 个、D4 进带需 ≥ 0.3611；"
    "报告修正三处过时说法 + R1p-t/R1p-r2 ⇒ `check_stage9_report.py` **62/62**、交付件 **154 行**；用户拍板 D55 第 18 条 = (a)+(c) |"
)
RM_ITEM47 = (
    "| 47 | ✅ **本机 `D:\\Conda\\envs\\hssm` 里有完整贝叶斯栈；ArviZ 独立复核了 `loo.py` 的 PSIS-LOO（D63，§8.38）** | "
    "pymc 5.28.5 / pytensor 2.38.3 / arviz 0.23.4 / hssm 0.3.0（py3.11.15）；同一 `(2000, 40)` 矩阵上 "
    "`elpd_loo` −53.814882 vs −53.816786（**相对差 3.54e-05**）、`p_loo` 0.778425 vs 0.780329；"
    "`pm.sample` 不可用（`0xc06d007f`、无 g++）⇒ 主路线仍零依赖；`check_loo.py` 新增 `[D]` 三条 ⇒ **17/17**；"
    "D41 拍板项关闭 |"
)


def do_close_55_18() -> None:
    """用户已在 D62 拍板：D55 第 18 条选 (a)+(c) ⇒ §9 第 38 项从「🛑 需拍板」改为 ✅ 结案。"""
    text = load(RM)
    if "用户拍板（D62 ⑥）" in text:
        print(f"[跳过] {RM.name}：§9 第 38 项已关闭")
        return
    lines = text.splitlines()
    patch_row(lines,
              "| 38 | 🛑 **事前登记的遗漏率带与已定稿的锚点 D4 不相容（D55，需拍板）** |",
              "🛑 **事前登记的遗漏率带与已定稿的锚点 D4 不相容（D55，需拍板）**",
              "✅ **事前登记的遗漏率带与已定稿的锚点 D4 不相容 —— 已由用户拍板 (a)+(c) 结案（D55 / D62）**",
              "DDM README §9 第 38 项状态")
    append_in_row(lines, "| 38 | ✅ **事前登记的遗漏率带与已定稿的锚点 D4 不相容",
                  "✅ **2026-10-17 用户拍板（D62 ⑥）＝ (a)+(c)**：保持冻结规格不动、把「锚点落在带外」作为 **9A 头条结论**"
                  "报出，并同时给 D4 归一化的比值口径（正式件上推荐点 `A/A(D4) = 1.1115`、`B/B(D4) = 1.1334`）。"
                  "补强证据：正式 `n_fim = 12` 件上 D4 的遗漏率 **0.3546**（`n_fim = 1` 档 0.3507 / 0.3819）⇒ 两档都 ≈ 0.35，"
                  "不是小样本产物；现行带下**支配 D4 的可行设计 0 个**、D4 进带需上界 ≥ 0.3611",
                  "DDM README §9 第 38 项的 (a)+(c) 结案注记", guard="用户拍板（D62 ⑥）")
    save(RM, "\n".join(lines) + "\n")


def main() -> int:
    for fn in (do_master_plan, do_stage9, do_autora_readme, do_ddm_readme, do_close_55_18):
        print(f"\n===== {fn.__name__} =====")
        fn()
    print(f"\n{'✅ 已应用' if APPLY else 'ℹ️ 干跑完成（加 --apply 写盘）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
