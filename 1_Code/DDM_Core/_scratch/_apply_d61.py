"""把决策 **D61** 写进四份文档（干跑优先，`--apply` 才写盘）。

D61 的内容（本轮）：
  ① `n_fim` 两档对照：`n_bad > 0` 的候选两档都是 **123 / 174** 且**逐设计完全相同**
     ⇒ 病态集是**设计空间的结构性质**，不是 `n_fim = 1` 的产物；随 `n_fim` 移动的是
     **遗漏率带内的成员**（可行 27 → 30）。
  ② 可行集**铺开度**：`(A)` 极差 = 105.03 倍（`n_fim = 1`）/ 80.23 倍（`n_fim = 12`）判据带；
     与最优**不可分辨**的设计 2 / 27 与 11 / 30 ⇒ 「推荐点」只是**可行带内的一个点**。
  ③ **族稳健、点不稳健**：不可分辨者全部落在最大 W 档 + `T` 3–6 档 + `r8–r16`；
     两档点名的推荐点是**两个不同设计** ⇒ 论文只能写「族」，不能写「确切点」。
  ④ 报告 §7 新增「身份是否唯一」段 + 牙齿 R1p-s/s2/s3 ⇒ `check_stage9_report.py` **61/61**。
  ⑤ **D60 的 `2·√2` 得到实测支持（含一次自我纠错）**：`_scratch_pair_corr.py` 量到
     ρ = +0.486…+0.848、实测系数 1.085…1.991 < 2.828 —— 但那是**探针口径**
     （`_one()` 把种子直接交给 `inner_eval` ⇒ 所有设计**共用同一条随机流**）；
     循环里是 `seed=cell_seed(d["name"], base_seed)` ⇒ 各设计各一条流 ⇒ 独立性成立。
     附带结论：「共享流 CRN 配对」是**候选改进**，两个口径**不可混用**。
  ⑥ 环境坑：控制台 GBK ⇒ 含 `⇒`/`✅` 的探针必须 `python -X utf8`；日志必须用
     `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`（`Tee-Object` 写出 UTF-16）。

体例：前缀定位 + 命中数断言 + 表格行竖线数不变 + 幂等守卫 + `--apply` 闸（写在 `save()` 里）。
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

D61_ROW = (
    "| **D61** | 2026-10-16 | ✅ **病态集在两档 `n_fim` 下逐设计完全相同（结构性，不是 `n_fim = 1` 的产物）；"
    "但可行集内部铺开度极大 ⇒「推荐点」不是唯一解，论文只能写「设计族」不能写「确切点」；"
    "顺带给 D60 的 `2·√2` 补上实测支持（含一次自我纠错）**。"
    "① ❗ **病态集是结构性质**：`n_bad > 0` 的候选在 `n_fim = 1` 与 `n_fim = 12` 下都是 **123 / 174**，"
    "且**逐设计完全相同**（只有基线有 0 个、只有新件有 0 个；`n_bad == 0` 但 `cond > 1e10` 两档都是 0）"
    "⇒ 上一轮挂着的「123 个病态是不是 `n_fim = 1` 的产物」的答案是**否**；随 `n_fim` 移动的是**"
    "**遗漏率带内的成员**（可行 27 → **30**、只被带否决 24 → 21、只被数值病态否决 54 → 46、两者兼有 69 → **77**；"
    "逐设计迁移：只病态→兼有 10、只带→可行 9、可行→只带 6、兼有→只病态 2）。"
    "② ❗ **可行集铺开度**（新探针 `1_Code/AutoRA_SPE/_scratch_feasible_spread.py`）："
    "`n_fim = 1` 可行 27 个、`(A)` 0.344643 / 中位 0.424855 / 最大 1.091866 ⇒ 极差 **0.747223 = 105.03 倍**判据带"
    "（`sd_A = 0.00251523`、`band_a = 0.00711415`），与最优**不可分辨**（`ΔA < 2·√2·sd_A`）**2 / 27**、"
    "`(B)` 上 17 / 27；`n_fim = 12` 可行 30 个、`(A)` 0.376187 / 0.462762 / 2.240307 ⇒ 极差 "
    "**1.864119 = 80.23 倍**带（`sd_A = 0.00821428`、`band_a = 0.0232335`），不可分辨 **11 / 30**、`(B)` 上 10 / 30。"
    "③ ❗ **族稳健、点不稳健**：那 11 个不可分辨设计**全部**是最大 W 档 "
    "`W[1199.90/1799.90/2399.80]ms` + `T` 3–6 档 + `r8–r16`（`n_fim = 1` 的 2 个也是最大 W 档 + `r16`）"
    "⇒ 站得住的说法是「**该设计族**稳健」，不是「这个点最优」；两档点名的推荐点是**两个不同设计**"
    "（`T[33.33/149.99/349.99]ms x W[1199.90/1799.90/2399.80]ms x r16` @`n_fim = 1` → "
    "`T[33.33/149.99/249.98/449.98]ms x W[1199.90/1799.90/2399.80]ms x r12` @`n_fim = 12`）。"
    "④ **报告新增 §7「身份是否唯一」段**：印出可行数与 `(A)` 的最小/中位/最大、「极差 = k 倍判据带」、"
    "「与最优不可分辨的可行设计 m / N」、「`(B)` 上与推荐点不可分辨的 m2 / N」，并明说**不得**写成「唯一最优」；"
    "只有 1 个可行设计时改印「可行集只有 1 个设计」。"
    "⑤ **牙齿**：`1_Code/AutoRA_SPE/check_stage9_report.py` 新增 R1p-s（注入第 3 个可行设计 ⇒ 必须印 `2 / 3`）、"
    "R1p-s2（必须出现「唯一最优」「不得」「两个不同设计」）、R1p-s3（只有 1 个可行设计 ⇒ 印「可行集只有」且不得出现 `2 / 3`）、"
    "R1p-r3（探针「共用随机流」口径 ≠ 循环判据带）⇒ **57/57 → 61/61**；交付件重新生成 **149 行**。"
    "⑥ ❗ **D60 的 `2·√2` 得到实测支持（含一次自我纠错）**：新探针 "
    "`1_Code/AutoRA_SPE/_scratch_pair_corr.py` 在 `n_fim = 1` 的 32 种子读数上量到逐设计 "
    "`ρ = +0.486…+0.848`、实测判据系数 `2·sd_pair/sd = 1.085…1.991`（< `2·√2 = 2.828`）—— "
    "一度以为这推翻了 D60 的独立性假设；读码确认是**探针口径**：`_scratch_anchor_seed_scan._one()` 把种子"
    "**直接**交给 `inner_eval` ⇒ 同一份种子表下**所有设计共用同一条随机流**（共享 CRN），而循环里 "
    "`stage9_loop.Evaluator._raw` 用 `seed=cell_seed(d[\"name\"], base_seed)` ⇒ **各设计各自一条流** ⇒ "
    "独立性成立、**`2·√2` 不改**；⇒ 附带结论：「共享流 CRN 配对」是一条**候选改进**"
    "（判据系数可收到 1.1–2.0、约 1.6 倍灵敏度），不是现有判据的缺陷，且两个口径**不可混用**"
    "（报告 §7 与两个探针都写明）。"
    "⑦ **环境坑**：本机控制台编码 = GBK ⇒ 含 `⇒`/`✅` 的探针必须 `python -X utf8` 运行；"
    "日志必须用 `[System.IO.File]::WriteAllText($p, ($t -replace \"`r`n\", \"`n\"), "
    "(New-Object System.Text.UTF8Encoding($false)))` 写（`Tee-Object` 会写出 **UTF-16** ⇒ "
    "`1_Code/DDM_Core/_scratch/check_files.py` 报 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff`）。"
    "⑧ **尚未做**：`n_fim = 12` 的种子平均排名（`_scratch_mean_A_rank.py ... 32 12`，约 1.9 h）、"
    "正式 `--budget 12 --n-fim 12 --noise-repeats 16` 落盘件的判读与交付件依据件切换、"
    "🛑 D55 第 18 项（**新证据**：D4 的遗漏率在 `n_fim = 1`（0.3507 / 0.3819）与 `n_fim = 12`（0.3565 / 0.3521）"
    "两档都在 0.35 左右 ⇒ 带 `[0.05, 0.20]` 对 D4 的排斥是稳健的，不是小样本产物）"
    " | `1_Code/AutoRA_SPE/_scratch_cmp_nfim.py` 两档对照（`_scratch_cmp_nfim_u8.txt`，`n_evaluated == 174` 两边相同）、"
    "`1_Code/AutoRA_SPE/_scratch_feasible_spread.py`（**新建**：可行集铺开度 + 不可分辨计数）、"
    "`1_Code/AutoRA_SPE/_scratch_pair_corr.py`（**新建**：逐设计 ρ 与实测判据系数）、"
    "`1_Code/AutoRA_SPE/_scratch_mean_A_rank_v2_u8.txt` + `.vals.json`（32 种子 × 7 设计、配对 SE 0.64 × 非配对）、"
    "`python -X utf8 -u 1_Code\\AutoRA_SPE\\check_stage9_report.py` ⇒ **61/61、未通过 0 项**、"
    "`check_stage9.py --n-fim-inner 2` 全套（`_scratch_agg_console_d61_u8.txt`）、"
    "`1_Code/AutoRA_SPE/_scratch_report_nfim12_preview.md`（135 行，锚点遗漏率逐次 0.3565 / 0.3521）"
    " | 判词口径没动、**设计读数一个都没动** ⇒ 两档对照只改「谁进可行集」与「谁与最优不可分辨」；"
    "交付件依据件仍是 `n_fim = 1` 的 `1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`（正式 budget-12 落盘件未到）"
    " |"
)

D61_PROGRESS = (
    "| 2026-10-16 | **9**（可行域铺开度与「推荐点」的身份 → D61） | "
    "**回答「123 个病态候选是不是 `n_fim = 1` 的产物」，并把「推荐点」这个词的可信度钉住**。"
    "① 病态集**逐设计完全相同**（两档都 123 / 174、`n_bad == 0` 但 `cond > 1e10` 都是 0）⇒ 结构性；"
    "随 `n_fim` 移动的是遗漏率带内成员（可行 27 → 30）；"
    "② 铺开度：`(A)` 极差 = **105.03 倍**（`n_fim = 1`）/ **80.23 倍**（`n_fim = 12`）判据带，"
    "与最优不可分辨 **2 / 27** 与 **11 / 30** ⇒ 推荐点不唯一；"
    "③ 不可分辨者**全在最大 W 档 + `T` 3–6 档 + `r8–r16`** ⇒「族稳健、点不稳健」，两档推荐点是两个不同设计；"
    "④ 报告 §7 新增「身份是否唯一」段 + R1p-s/s2/s3 ⇒ 报告自测 57/57 → **61/61**、交付件 149 行；"
    "⑤ 带宽 `2·√2` 的实测支持（`_scratch_pair_corr.py`：ρ = +0.486…+0.848 是**探针共用随机流**所致，"
    "循环里各设计各一条流 ⇒ 独立性成立 ⇒ D60 不改） | "
    "`1_Code/AutoRA_SPE/stage9_report.py`（**529 行**）、`1_Code/AutoRA_SPE/stage9_report.md`（**149 行**）、"
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（**427 行、61/61**）、"
    "`1_Code/AutoRA_SPE/_scratch_feasible_spread.py`（**新**，129 行）、"
    "`1_Code/AutoRA_SPE/_scratch_pair_corr.py`（**新**，68 行）、"
    "`1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`（207 行，配对段加口径告警） | "
    "**(1)** 读 `n_fim = 12` 的种子平均排名（在跑）与正式 budget-12 落盘件，并把交付件依据件换过去；"
    "**(2)** 「共享流 CRN 配对」是否升格为正式判据（会把带宽系数从 2.83 收到 1.1–2.0 ⇒ 需重做 D60 的登记）；"
    "**(3)** 🛑 D55 第 18 项待拍板；**(4)** 四个用户侧 Stage（1 实机验收 / 6 Pilot / 7 正式采集 / 定稿签批） |"
)

D61_CHANGELOG = (
    "| 2026-10-16 | **新增 D61：病态集在 `n_fim = 1/12` 下逐设计完全相同（结构性）；可行集铺开度 = 105.03 / 80.23 倍判据带"
    " ⇒「推荐点」不是唯一解（只可说「设计族」）；报告 §7 新增「身份是否唯一」段；D60 的 `2·√2` 得到实测支持"
    "（ρ = +0.486…+0.848 是探针共用随机流的口径）**：`stage9_report.py` 494 → **529 行**、`check_stage9_report.py` "
    "400 → **427 行（57/57 → 61/61）**、`stage9_report.md` 145 → **149 行**；新建探针 "
    "`1_Code/AutoRA_SPE/_scratch_feasible_spread.py`（129 行）与 `_scratch_pair_corr.py`（68 行）；§11 新增第 26 条；"
    "证据：`_scratch_cmp_nfim_u8.txt`、`_scratch_feasible_spread_u8.txt`、`_scratch_pair_corr_u8.txt`、"
    "`_scratch_check_stage9_report_d61_u8.txt`、`_scratch_agg_console_d61_u8.txt`、`1_Code/DDM_Core/README.md` §8.36、"
    "§9 第 45 项 |"
)

D61_APPENDIX = (
    "| `1_Code/AutoRA_SPE/stage9_report.py`（494 → **529 行**） + `1_Code/AutoRA_SPE/stage9_report.md`（145 → **149 行**）"
    " + `1_Code/AutoRA_SPE/check_stage9_report.py`（400 → **427 行**、57/57 → **61/61**）"
    " + `1_Code/AutoRA_SPE/_scratch_feasible_spread.py`（**新建**：可行集铺开度）"
    " + `1_Code/AutoRA_SPE/_scratch_pair_corr.py`（**新建**：逐设计 ρ 与实测判据系数）"
    " + `1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`（配对段加「共用随机流 ≠ 循环判据」告警） | "
    "两档对照：病态集 123 / 174 **逐设计完全相同**、可行 27 → 30；铺开度：极差 0.747223（105.03 倍带）与 "
    "1.864119（80.23 倍带），不可分辨 2 / 27 与 11 / 30，全部落在最大 W 档 + `T` 3–6 档 + `r8–r16`；"
    "带宽支持：ρ = +0.486…+0.848、实测系数 1.085…1.991（**探针共用随机流**所致；循环里各设计各一条流 ⇒ D60 不改） |"
)


def do_master_plan() -> None:
    text = load(MP)
    if "| **D61** | 2026-10-16 |" in text:
        print(f"[跳过] {MP.name}：D61 已落纸")
        return
    lines = text.splitlines()
    ins_after(lines, "| **D60** | 2026-10-16 |", [D61_ROW], "主计划 §5 决策行 D61")
    ins_after(lines, "| 2026-10-16 | **9**（判据带宽的 √2 缺口 + 推荐点的选择偏差 → D60） |",
              [D61_PROGRESS], "主计划 §6 进度行 D61")
    ins_after(lines, "| 2026-10-16 | **新增 D60：", [D61_CHANGELOG], "主计划 §7 变更日志 D61")
    ins_after(lines, "| `1_Code/AutoRA_SPE/stage9_loop.py`（896 → **917 行**）", [D61_APPENDIX],
              "主计划 §8 附录证据 D61")
    save(MP, "\n".join(lines) + "\n")


def do_stage9() -> None:
    text = load(S9)
    if "（决策 D61）" in text:
        print(f"[跳过] {S9.name}：D61 已落纸")
        return
    lines = text.splitlines()
    P_MD = "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告"
    P_GEN = "| `1_Code/AutoRA_SPE/stage9_report.py` | 落盘报告生成器"
    P_CG = "| `1_Code/AutoRA_SPE/check_stage9_report.py` | 报告生成器自测"
    P_AGG = "| `1_Code/AutoRA_SPE/check_stage9.py` | 汇总自测"
    patch_row(lines, P_MD, "**145 行**", "**149 行**", "Stage9 §9：stage9_report.md 145 → 149")
    append_in_row(lines, P_MD, "D61 起 §7 新增「身份是否唯一」段（可行集 `(A)` 铺开度、与最优不可分辨的个数）",
                  "Stage9 §9：stage9_report.md 的 D61 注记")
    patch_row(lines, P_GEN, "**494 行**", "**529 行**", "Stage9 §9：stage9_report.py 494 → 529")
    append_in_row(lines, P_GEN,
                  "D61 起 §7 新增「身份是否唯一」段与「种子平均探针的配对口径 ≠ 本报告的判据带」提醒",
                  "Stage9 §9：stage9_report.py 的 D61 注记")
    patch_row(lines, P_CG, "**400 行**", "**427 行**", "Stage9 §9：check_stage9_report 400 → 427")
    patch_row(lines, P_CG, "**57/57 通过、exit 0**", "**61/61 通过、exit 0**",
              "Stage9 §9：check_stage9_report 57/57 → 61/61")
    append_in_row(lines, P_CG,
                  "D61 新增 R1p-s/s2/s3（身份是否唯一 / 不得写成唯一最优 / 只有一个可行设计时不硬报）"
                  "与 R1p-r3（探针共用随机流的口径 ≠ 循环判据带）",
                  "Stage9 §9：check_stage9_report 的 D61 注记")
    append_in_row(lines, P_AGG, "（`S5` 的计数沿革：D57 47/47 ⇒ D60 57/57 ⇒ D61 **61/61**）",
                  "Stage9 §9：check_stage9 的 S5 计数沿革（D61）", guard="D61 **61/61**")
    ins_after(lines, "25. ❗ **判据带宽的系数是 `2·√2`", [S9_11_26], "Stage9 §11 第 26 条（D61）")
    ins_after(lines, "| 2026-10-16 | **判据带宽的 √2 缺口 + 推荐点的选择偏差（决策 D60）**", [S9_12_D61],
              "Stage9 §12 D61 行")
    save(S9, "\n".join(lines) + "\n")


def do_autora_readme() -> None:
    text = load(RA)
    if "D61 起 §7 新增" in text:
        print(f"[跳过] {RA.name}：D61 已落纸")
        return
    lines = text.splitlines()
    P_GEN = "| `stage9_report.py` | **Stage 9 落盘报告生成器**"
    P_CG = "| `check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, P_GEN, "**494 行**", "**529 行**", "AutoRA README §7：stage9_report.py 494 → 529")
    append_in_row(lines, P_GEN, "D61 起 §7 新增「身份是否唯一」段（可行集铺开度 + 不可分辨计数）",
                  "AutoRA README §7：stage9_report.py 的 D61 注记")
    patch_row(lines, P_CG, "**400 行、57/57", "**427 行、61/61", "AutoRA README §7：check_stage9_report")
    append_in_row(lines, P_CG, "D61 新增 R1p-s/s2/s3 与 R1p-r3", "AutoRA README §7：check_stage9_report 的 D61 注记")
    save(RA, "\n".join(lines) + "\n")


def do_ddm_readme() -> None:
    text = load(RM)
    if "## 8.36 " in text:
        print(f"[跳过] {RM.name}：D61 已落纸")
        return
    lines = text.splitlines()
    ins_before(lines, "## 9. 尚未做", RM_836, "DDM README §8.36")
    ins_after(lines, "| 44 | ✅ **跨设计比较的带宽系数是 `2·√2`", [RM_ITEM45], "DDM README §9 第 45 项")
    save(RM, "\n".join(lines) + "\n")


# ---------------------------------------------------------------- 文本常量

S9_11_26 = (
    "26. ❗ **「推荐点」不是唯一解：可行集内部铺开度极大，而病态集是结构性质（D61）**："
    "`(A)` 在可行集内的**极差** = **105.03 倍**判据带（`n_fim = 1`，27 个可行）与 **80.23 倍**（`n_fim = 12`，30 个可行）；"
    "与最优**不可分辨**（`ΔA < 2·√2·sd_A`）的可行设计有 **2 / 27** 与 **11 / 30**，且它们**全部**落在最大 W 档 "
    "`W[1199.90/1799.90/2399.80]ms` + `T` 3–6 档 + `r8–r16` ⇒ **族稳健、点不稳健**（两档 `n_fim` 点名的推荐点是"
    "**两个不同设计**）。因此报告 §7 必须印「身份是否唯一」而论文只可写「该设计族」。"
    "另：`n_bad > 0` 的候选在两档 `n_fim` 下都是 **123 / 174** 且**逐设计完全相同** ⇒ 病态集是**设计空间的结构性质**；"
    "随 `n_fim` 移动的只是**遗漏率带内的成员**（可行 27 → 30）。"
    "**附带的自我纠错**：`_scratch_pair_corr.py` 量到的 `ρ = +0.486…+0.848`（判据系数实测 1.085…1.991 < 2.828）"
    "来自**探针口径**（`_one()` 把种子直接交给 `inner_eval` ⇒ 所有设计共用同一条随机流），"
    "而循环里 `Evaluator._raw` 用 `seed=cell_seed(d[\"name\"], base_seed)` ⇒ 各设计各自一条流 ⇒ D60 的 `2·√2` **不改**；"
    "「共享流 CRN 配对」可作为**候选改进**（系数可收到 1.1–2.0），但两个口径**不可混用**。"
)

S9_12_D61 = (
    "| 2026-10-16 | **可行集铺开度与「推荐点」的身份（决策 D61）**：报告 §7 新增「身份是否唯一」段（`(A)` 极差 = k 倍判据带、"
    "与最优不可分辨的个数、`(B)` 上的个数，并明说不得写成「唯一最优」）；`stage9_report.py` 494 → **529 行**、"
    "`stage9_report.md` 145 → **149 行**、`check_stage9_report.py` 400 → **427 行（57/57 → 61/61，R1p-s/s2/s3 + R1p-r3）**；"
    "新建探针 `_scratch_feasible_spread.py`（129 行）与 `_scratch_pair_corr.py`（68 行） | "
    "两档对照（`n_fim = 1` vs `12`：病态集逐设计相同、可行 27 → 30、铺开度 105.03 / 80.23 倍带、不可分辨 2 / 27 与 11 / 30、"
    "不可分辨者全在最大 W 档）、带宽实测支持（ρ = +0.486…+0.848 是**探针共用随机流**的口径 ⇒ D60 的 `2·√2` 不改）、"
    "`1_Code/DDM_Core/README.md` §8.36、§9 第 45 项 |"
)

RM_836 = [
    "## 8.36 可行集的铺开度与「推荐点」的身份；病态集是结构性质（2026-10-16，D61）",
    "",
    "### 1. 动机",
    "",
    "D60 把跨设计比较的带宽改成了**差**的口径（`2·√2·sd`）。带宽一变，紧接着的问题就是：",
    "**那根带子相对可行集内部的铺开度有多宽**——如果可行集里与「最优」不可分辨的设计不止一个，",
    "那么报告里点名的「推荐点」就只是**可行带内的一个点**，论文里就不能写「唯一最优」。",
    "同时还要回答上一轮挂着的那个问题：`n_fim = 1` 下出现的 123 个数值病态候选，",
    "是不是**只在小 `n_fim` 下才病态**（即 `n_fim = 1` 的产物）。",
    "",
    "### 2. 两档对照：病态集是**设计空间的结构性质**",
    "",
    "`python -u 1_Code\\AutoRA_SPE\\_scratch_cmp_nfim.py 1_Code\\AutoRA_SPE\\stage9_payload_nfim1_budget12.json "
    "1_Code\\AutoRA_SPE\\_scratch_payload_nfim12.json`（日志 `1_Code\\AutoRA_SPE\\_scratch_cmp_nfim_u8.txt`，两档 `n_evaluated = 176`）：",
    "",
    "| 类别 | `n_fim = 1` | `n_fim = 12` |",
    "| --- | --- | --- |",
    "| 可行 | 27 | **30** |",
    "| 只被遗漏率带否决 | 24 | 21 |",
    "| 只被数值病态否决 | 54 | 46 |",
    "| 两者兼有 | 69 | **77** |",
    "| `n_bad > 0`（数值病态集） | **123** | **123** |",
    "| `n_bad == 0` 但 `cond > 1e10` | 0 | 0 |",
    "",
    "❗ **病态集逐设计完全相同**（只有基线有、只有新件有 ⇒ 两边都是 0 个）⇒ **123 / 174 是设计空间的结构性质**，",
    "不是 `n_fim = 1` 的产物；随 `n_fim` 移动的只是**遗漏率带内的成员**（逐设计迁移：只病态→兼有 10、只带→可行 9、",
    "可行→只带 6、兼有→只病态 2）。带宽本身也随 `n_fim` 变：`2·sd_A` 0.0050 → **0.0164**、`2·sd_B` 0.2665 → **0.0771**。",
    "",
    "### 3. 铺开度：`(A)` 的极差是**几十到上百倍**判据带",
    "",
    "`python -u 1_Code\\AutoRA_SPE\\_scratch_feasible_spread.py <payload.json>`（日志 `_scratch_feasible_spread_u8.txt`）：",
    "",
    "| 落盘件 | 可行 | `(A)` 最小 / 中位 / 最大 | 极差 | 极差 ÷ 判据带 | 与最优不可分辨 | `(B)` 上不可分辨 |",
    "| --- | --- | --- | --- | --- | --- | --- |",
    "| `stage9_payload_nfim1_budget12.json` | 27 | 0.344643 / 0.424855 / 1.091866 | 0.747223 | **105.03 倍** | **2 / 27** | 17 / 27 |",
    "| `_scratch_payload_nfim12.json` | 30 | 0.376187 / 0.462762 / 2.240307 | 1.864119 | **80.23 倍** | **11 / 30** | 10 / 30 |",
    "",
    "❗ **族稳健、点不稳健**：`n_fim = 12` 那 11 个不可分辨设计**全部**是最大 W 档",
    "`W[1199.90/1799.90/2399.80]ms` + `T` 3–6 档 + `r8–r16`（`n_fim = 1` 的 2 个也是最大 W 档 + `r16`）⇒",
    "可以说「**该设计族**稳健」，**不可以**说「这个点最优」；两档点名的推荐点是**两个不同设计**",
    "（`...r16` → `T[33.33/149.99/249.98/449.98]ms x W[1199.90/1799.90/2399.80]ms x r12`）。",
    "",
    "### 4. 带宽 `2·√2` 的实测支持（含一次自我纠错）",
    "",
    "`python -u 1_Code\\AutoRA_SPE\\_scratch_pair_corr.py 1_Code\\AutoRA_SPE\\_scratch_mean_A_rank_v2_u8.vals.json`：",
    "逐设计 `ρ = +0.486 / +0.487 / +0.496 / +0.603 / +0.763 / +0.848`、配对 `sd_pair` = 0.0101–0.0186（< `√2·sd ≈ 0.0255`）",
    "⇒ 实测判据系数 `2·sd_pair/sd` = **1.085 / 1.374 / 1.837 / 1.945 / 1.979 / 1.991**，全部小于独立性假设的 `2·√2 = 2.828`。",
    "",
    "❗ 一度以为这**推翻**了 D60 的独立性假设（即 `2·√2` 偏宽）。读码后确认是**探针口径**造成的：",
    "`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py::_one()` 把种子**直接**交给 `inner_eval` ⇒",
    "同一份种子表下**所有设计共用同一条随机流**（共享 CRN）⇒ 正相关是当然的。而循环里",
    "`1_Code/AutoRA_SPE/stage9_loop.py::Evaluator._raw` 用 `seed=cell_seed(d[\"name\"], base_seed)`",
    "（`cell_seed(name, base_seed) = (base_seed + sha256(name)[:12]) mod 2**32`）⇒ **每个设计各自一条流** ⇒",
    "两条臂相互独立 ⇒ `Var(ΔA) = 2·sd²` ⇒ **`2·√2` 不改**。",
    "",
    "附带结论：「**共享流 CRN 配对**」是一条**候选改进**（判据系数可收到 1.1–2.0，配对 SE ≈ 0.64 × 非配对），",
    "不是现有判据的缺陷；两个口径**不可混用**（报告 §7 与两个探针都写明；探针的配对 t 值不能替代第 5 节的判词）。",
    "",
    "### 5. 报告与探针的新呈现",
    "",
    "1. `1_Code/AutoRA_SPE/stage9_report.py` §7 新增「**可行集里「最优设计」的身份是否唯一**」段：",
    "   印出可行数与 `(A)` 的最小/中位/最大、「极差 = k 倍判据带 `2·√2·sd_A`」、「与最优不可分辨的可行设计 m / N」、",
    "   「`(B)` 上与推荐点不可分辨的 m2 / N」，并明说**不得**写成「唯一最优」；只有 1 个可行设计时改印「可行集只有 1 个设计」；",
    "2. §7 的选择偏差段补一行**口径提醒**：种子平均探针的**配对**口径（共用随机流）≠ 本报告的判据带（各设计各一条流）；",
    "3. 新建两个探针：`_scratch_feasible_spread.py`（可行集铺开度 + 不可分辨计数 + 全列）与",
    "   `_scratch_pair_corr.py`（逐设计 ρ、配对 `sd_pair`、实测判据系数）。",
    "",
    "### 6. 校验证据",
    "",
    "1. `python -X utf8 -u 1_Code\\AutoRA_SPE\\check_stage9_report.py` ⇒ **61/61、未通过 0 项、exit 0**",
    "   （`_scratch_check_stage9_report_d61_u8.txt`；新增 R1p-s/s2/s3 + R1p-r3）；",
    "2. 交付件 `1_Code/AutoRA_SPE/stage9_report.md` **149 行**，且 R1l 要求它与生成器现输出**逐字相同**（已重生成）；",
    "3. `python -X utf8 -u 1_Code\\AutoRA_SPE\\check_stage9.py --n-fim-inner 2` 全套 ⇒ **10 项、未通过 0 项、exit 0**",
    "   （`_scratch_agg_console_d61_u8.txt`）；",
    "4. 两档对照日志 `_scratch_cmp_nfim_u8.txt`（⚠️ 与 D58 时期的同名文件，已被本轮内容覆盖；",
    "   D58 只在文档里引用了脚本名，未引用该日志内容）；",
    "5. 铺开度日志 `_scratch_feasible_spread_u8.txt`（42 行）、配对相关日志 `_scratch_pair_corr_u8.txt`；",
    "6. ❗ **环境坑**：本机控制台编码 = GBK（`sys.stdout.encoding == 'gbk'`）⇒ 含 `⇒`/`✅` 的探针必须 `python -X utf8` 运行，",
    "   否则 `UnicodeEncodeError: 'gbk' codec can't encode character '\\u21d2'`；日志必须用",
    "   `[System.IO.File]::WriteAllText(..., (New-Object System.Text.UTF8Encoding($false)))` 写",
    "   （`Tee-Object` 会写出 **UTF-16**，首字节 `FF FE` ⇒ `check_files.py` 直接 `UnicodeDecodeError`）。",
    "",
    "### 7. 尚未做",
    "",
    "1. `n_fim = 12` 的种子平均排名（`python -u 1_Code\\AutoRA_SPE\\_scratch_mean_A_rank.py "
    "1_Code\\AutoRA_SPE\\_scratch_payload_nfim12.json 32 12`，约 1.9 h）⇒ 判断「锚点在正式 `n_fim` 下是否也最优」；",
    "2. 正式 `--budget 12 --n-fim 12 --noise-repeats 16` 落盘件的判读（`pwsh-345`）与**交付件依据件**切换；",
    "3. 🛑 `1_Code/DDM_Core/README.md` §9 第 18 项（D55 的遗漏率带与锚点 D4 不相容）仍待拍板 ——",
    "   **新证据**：D4 的遗漏率在 `n_fim = 1`（0.3507 / 0.3819）与 `n_fim = 12`（0.3565 / 0.3521）两档都在 0.35 左右",
    "   ⇒ 带 `[0.05, 0.20]` 对 D4 的排斥是**稳健的**，不是小样本产物；",
    "4. 「共享流 CRN 配对」是否升格为正式判据（需重做 D60 的登记与报告措辞）。",
    "",
]

RM_ITEM45 = (
    "| 45 | ✅ **可行集铺开度 = 几十到上百倍判据带 ⇒「推荐点」不是唯一解；病态集是设计空间的结构性质（D61，§8.36）** | "
    "`n_bad > 0` 的候选在 `n_fim = 1` 与 `12` 下都是 **123 / 174** 且**逐设计完全相同** ⇒ 结构性（随 `n_fim` 移动的只是"
    "遗漏率带内成员，可行 27 → 30）；`(A)` 极差 = **105.03 倍**（`n_fim = 1`）/ **80.23 倍**（`n_fim = 12`）判据带，"
    "与最优不可分辨 **2 / 27** 与 **11 / 30**，且全部落在最大 W 档 + `T` 3–6 档 + `r8–r16` ⇒ **族稳健、点不稳健**；"
    "报告 §7 新增「身份是否唯一」段 + R1p-s/s2/s3 + R1p-r3 ⇒ `check_stage9_report.py` **61/61**；"
    "带宽 `2·√2` 的实测支持（ρ = +0.486…+0.848 是探针**共用随机流**的口径 ⇒ 循环里各设计各一条流 ⇒ D60 不改） |"
)


def main() -> int:
    print(f"{'应用' if APPLY else '干跑'}模式（{'--apply' if APPLY else '加 --apply 才写盘'}）")
    do_master_plan()
    do_stage9()
    do_autora_readme()
    do_ddm_readme()
    print("完成。" + ("" if APPLY else "（干跑：未写任何文件）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
