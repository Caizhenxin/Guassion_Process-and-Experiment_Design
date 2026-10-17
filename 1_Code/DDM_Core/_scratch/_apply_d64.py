"""把决策 **D64**（`2·√2·sd` 的 `√2` 能取常数：同方差在正式 `n_fim` 下实测成立）写进四份文档。

来路：D62 那份 32 种子的逐设计读数（`_scratch_mean_A_rank_nfim12_u8.vals.json`）里，
`_scratch_pair_corr.py` 抽出的 7 个设计逐种子 `sd_A` 落在 0.0068–0.0085（最大/最小 1.24 倍）；
`n_fim = 1` 那档 3 个设计是 1.18 倍。⇒ D60 的 `2·√2·sd` 里那个 `√2` 取**常数**是有依据的，
不是裸假设。同一次输出里的 ρ = +0.22…+0.80 是**共用随机流**的口径（D61 已纠错），不能用来说明
循环里两条臂相关。

体例同 D61/D62 脚本：前缀定位 + 命中数断言 + 竖线数不变 + 幂等守卫 + `--apply` 闸（在 `save()`）。
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
    if new == old:
        print(f"  ⏭️  {what}：值未变 ⇒ 跳过")
        return
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


D64_ROW = (
    "| **D64** | 2026-10-17 | ✅ **`2·√2·sd` 里的 `√2` 取常数是有依据的：同方差假定在正式 `n_fim = 12` 下实测成立**"
    "（逐设计逐种子 `sd_A` 落在 **0.0068–0.0085**、最大/最小 **1.24 倍**；`n_fim = 1` 那档 3 个设计 1.18 倍）。"
    "来路：D62 那份 32 种子的逐设计读数（`_scratch_mean_A_rank_nfim12_u8.vals.json`）本来就含 7 个设计 × 32 种子，"
    "`_scratch_pair_corr.py` 从中抽出每个设计的 `sd`（`_scratch_pair_corr_nfim12_u8.txt`）⇒ 同一批计算既给了"
    "「配对 vs 非配对」的口径差，也顺手给了同方差的直接证据。**这不是新判据**：若 σ 在各设计间差几倍，"
    "`√2` 就得逐对算、带宽不能是单一常数；现在两档（1.18 倍 / 1.24 倍）都不支持「差几倍」⇒ D60 的常数形式成立。"
    "⚠️ 同一份输出里 `ρ = +0.22…+0.80` 是**探针共用随机流**的口径（D61 已纠错），**不能**用来说明循环里两条臂相关；"
    "循环用 `cell_seed(name, base_seed)` ⇒ 各设计各一条流。"
    " | `1_Code/AutoRA_SPE/_scratch_pair_corr_nfim12_u8.txt`（7 个设计：sd 0.0068–0.0085、ρ +0.22…+0.80）；"
    "`python -X utf8 -u 1_Code\\AutoRA_SPE\\check_stage9_report.py` ⇒ **63/63、未通过 0 项**；"
    "`1_Code/AutoRA_SPE/stage9_report.md` **154 → 155 行** | 判据带宽、推荐点、可行集读数**一个都没动**"
    "（只补一条经验支持进报告 §7 与 `1_Code/DDM_Core/README.md` §8.39）；ρ 的正面读数**不改变**任何判词 |"
)

D64_PROGRESS = (
    "| 2026-10-17 | **9**（`√2` 的同方差前提在正式 `n_fim` 下实测成立 → D64） | "
    "**D60 的带宽 `2·√2·sd` 一直有个裸假设：不同设计的 σ 同量级。本轮用已有数据把它验了**。"
    "① 数据来源 = D62 那份 32 种子逐设计读数（7 个设计 × 32）；`_scratch_pair_corr.py` 抽出每个设计的 `sd`；"
    "② 结果：`n_fim = 12` 下 `sd_A` **0.0068–0.0085**（max/min **1.24 倍**）、`n_fim = 1` 档 3 个设计 1.18 倍；"
    "③ 报告 §7 新增 D64 段 + 牙齿 R1p-u（`check_stage9_report.py` **62/62 → 63/63**，交付件 **155 行**）；"
    "④ 同一输出里的 ρ = +0.22…+0.80 是**共用随机流**口径，已在段内注明不得用来判断循环里两条臂的相关性 | "
    "`1_Code/AutoRA_SPE/_scratch_pair_corr_nfim12_u8.txt`（**新日志**）、`1_Code/AutoRA_SPE/stage9_report.py`（**554 行**）、"
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（**466 行**、63/63）、`1_Code/AutoRA_SPE/stage9_report.md`（**155 行**） | "
    "**(1)** 「共享流 CRN 配对」是否升格为正式判据（还需重跑内环，本轮**不做**）；"
    "**(2)** 四个用户侧 Stage；**(3)** `cellmean.py` 剖面诊断（真实数据） |"
)

D64_CHANGELOG = (
    "| 2026-10-17 | **新增 D64：`2·√2·sd` 的 `√2` 取常数有依据 —— 同方差在正式 `n_fim` 下实测成立"
    "（7 个设计、`sd_A` 0.0068–0.0085、1.24 倍；`n_fim = 1` 档 1.18 倍）**：报告 §7 新增 D64 段、"
    "牙齿 R1p-u ⇒ `check_stage9_report.py` **460 → 466 行（62/62 → 63/63）**、`stage9_report.py` 546 → **554 行**、"
    "`stage9_report.md` 154 → **155 行**；新日志 `_scratch_pair_corr_nfim12_u8.txt`；§11 新增第 29 条；"
    "证据：`1_Code/DDM_Core/README.md` §8.39、§9 第 48 项 |"
)

D64_APPENDIX = (
    "| `1_Code/AutoRA_SPE/_scratch_pair_corr_nfim12_u8.txt`（**新**） + `1_Code/AutoRA_SPE/stage9_report.py`"
    "（546 → **554 行**） + `1_Code/AutoRA_SPE/check_stage9_report.py`（460 → **466 行**、62/62 → **63/63**）"
    " + `1_Code/AutoRA_SPE/stage9_report.md`（154 → **155 行**） | "
    "同方差实测（7 个设计 sd 0.0068–0.0085、1.24 倍；`n_fim = 1` 档 1.18 倍）；ρ = +0.22…+0.80 是共用随机流口径、"
    "不得用来判断循环里两条臂的相关性；报告 §7 D64 段 + R1p-u |"
)

S9_11_29 = (
    "29. ❗ **`2·√2·sd` 里的 `√2` 取常数是有依据的（D64）**：同方差假定原先只在 `n_fim = 1` 上用 3 个设计验过"
    "（1.18 倍）；D64 用 D62 那份 32 种子读数的 7 个设计在正式 `n_fim = 12` 上复验 ⇒ `sd_A` **0.0068–0.0085**、"
    "最大/最小 **1.24 倍** ⇒ 若 σ 真在各设计间差几倍，`√2` 就得逐对算、带宽不能是单一常数。"
    "⚠️ 同一份输出里的 `ρ = +0.22…+0.80` 是**探针共用随机流**的口径（D61 已纠错），**不能**用来说明"
    "循环里两条臂相关 —— 循环用 `cell_seed(name, base_seed)`，各设计各一条流。"
)

S9_12_D64 = (
    "| 2026-10-17 | **`√2` 的同方差前提在正式 `n_fim` 下实测成立（决策 D64）**：7 个设计的逐种子 `sd_A` "
    "0.0068–0.0085（max/min **1.24 倍**）、`n_fim = 1` 档 3 个设计 1.18 倍 ⇒ `2·√2·sd` 的常数形式成立；"
    "报告 §7 新增 D64 段 + R1p-u ⇒ `check_stage9_report.py` **63/63**、交付件 **155 行**；ρ 的正面读数是共用随机流口径、"
    "不改变任何判词 "
    "| `1_Code/AutoRA_SPE/_scratch_pair_corr_nfim12_u8.txt`、`_scratch_check_stage9_report_d64_u8.txt`、"
    "`1_Code/DDM_Core/README.md` §8.39、§9 第 48 项 |"
)

RM_839 = [
    "## 8.39 `2·√2·sd` 的 `√2` 取常数：同方差在正式 `n_fim` 下实测成立（2026-10-17，D64）",
    "",
    "**动机**：D60 把跨设计比较的带宽从 `2·sd` 改成 `2·√2·sd`，依据是 `Var(ΔA) = 2·sd²`。但那个式子的前提是"
    "**两条臂的 σ 同量级**（同方差）；当时只在 `n_fim = 1` 上用 3 个设计验过（`sd_A` 0.0180 / 0.0186 / 0.0213，"
    "最大/最小 1.18 倍）。若 σ 在各设计间差几倍，`√2` 就得逐对算、带宽不能是单一常数。",
    "",
    "**做法（零新计算）**：D62 那份 32 种子的逐设计读数（`_scratch_mean_A_rank_nfim12_u8.vals.json`）本来就含"
    "7 个设计 × 32 个种子；`_scratch_pair_corr.py` 从中抽出每个设计的逐种子 `sd`（输出 "
    "`_scratch_pair_corr_nfim12_u8.txt`）。",
    "",
    "**结果**：`n_fim = 12` 的 7 个可行设计 `sd_A` = **0.0068 / 0.0076 / 0.0068 / 0.0070 / 0.0069 / 0.0085 / 0.0079**"
    "（最大/最小 **1.24 倍**）；`n_fim = 1` 那档 3 个设计 1.18 倍 ⇒ 两档都不支持「不同设计的 σ 差好几倍」"
    "⇒ `2·√2·sd` 里那个 `√2` 取**常数**是有依据的，不是裸假设。",
    "",
    "**边界**：同一份输出里 `ρ = +0.22…+0.80` 是**探针共用随机流**的口径（`_scratch_anchor_seed_scan._one()` "
    "把种子直接交给 `inner_eval`），**不能**用来说明循环里两条臂相关 —— 循环用 `cell_seed(name, base_seed)`，"
    "各设计各一条流（D61 已纠错）。这条只补经验支持，**不改**任何判据、带宽或推荐点。",
    "",
    "**牙齿**：`1_Code/AutoRA_SPE/check_stage9_report.py` 新增 **R1p-u**（报告必须给出「同方差」+ `1.24` + "
    "`0.0068` + `1.18` 四项）⇒ **62/62 → 63/63**；交付件 `stage9_report.md` **154 → 155 行**。",
    "",
]

RM_ITEM48 = (
    "| 48 | ✅ **`2·√2·sd` 的 `√2` 取常数：同方差在正式 `n_fim` 下实测成立（D64，§8.39）** | "
    "同一批 32 种子读数里抽出 7 个设计的逐种子 `sd_A` = 0.0068–0.0085（max/min **1.24 倍**）、"
    "`n_fim = 1` 档 3 个设计 1.18 倍 ⇒ 若 σ 差几倍则 `√2` 需逐对算；`ρ = +0.22…+0.80` 是共用随机流口径、"
    "不得用来判断循环里两条臂相关；报告 §7 新增 D64 段 + R1p-u ⇒ `check_stage9_report.py` **63/63**、"
    "交付件 **155 行** |"
)


def do_master_plan() -> None:
    text = load(MP)
    if "| **D64** | 2026-10-17 |" in text:
        print(f"[跳过] {MP.name}：D64 已落纸")
        return
    lines = text.splitlines()
    ins_after(lines, "| **D63** | 2026-10-17 |", [D64_ROW], "主计划 §5 决策行 D64")
    ins_after(lines, "| 2026-10-17 | **8**（D41 的依赖问题", [D64_PROGRESS], "主计划 §6 进度行 D64")
    ins_after(lines, "| 2026-10-17 | **新增 D63：D41 用事实核查结案", [D64_CHANGELOG], "主计划 §7 变更日志 D64")
    ins_after(lines, "| `1_Code/DDM_Core/_scratch/_probe_bayes_stack.py`（**新建**，79 行）", [D64_APPENDIX],
              "主计划 §8 附录证据 D64")
    save(MP, "\n".join(lines) + "\n")


def do_stage9() -> None:
    text = load(S9)
    if "（决策 D64）" in text:
        print(f"[跳过] {S9.name}：D64 已落纸")
        return
    lines = text.splitlines()
    P_MD = "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告"
    P_GEN = "| `1_Code/AutoRA_SPE/stage9_report.py` | 落盘报告生成器"
    P_CG = "| `1_Code/AutoRA_SPE/check_stage9_report.py` | 报告生成器自测"
    P_AGG = "| `1_Code/AutoRA_SPE/check_stage9.py` | 汇总自测"
    patch_row(lines, P_MD, "**154 行**", "**155 行**", "Stage9 §9：stage9_report.md 154 → 155")
    patch_row(lines, P_GEN, "**546 行**", "**554 行**", "Stage9 §9：stage9_report.py 546 → 554")
    patch_row(lines, P_CG, "**460 行**", "**466 行**", "Stage9 §9：check_stage9_report 460 → 466")
    patch_row(lines, P_CG, "**62/62 通过、exit 0**", "**63/63 通过、exit 0**",
              "Stage9 §9：check_stage9_report 62/62 → 63/63")
    append_in_row(lines, P_CG, "D64 新增 R1p-u（同方差的实测支持）",
                  "Stage9 §9：check_stage9_report 的 D64 注记", guard="R1p-u")
    append_in_row(lines, P_AGG, "（`S5` 的计数沿革：D57 47/47 ⇒ D60 57/57 ⇒ D61 61/61 ⇒ D62 **62/62** ⇒ D64 **63/63**）",
                  "Stage9 §9：check_stage9 的 S5 计数沿革（D64）", guard="D64 **63/63**")
    ins_after(lines, "28. ❗ **锚点的「更好」与「可执行」是两件事", [S9_11_29], "Stage9 §11 第 29 条（D64）")
    ins_after(lines, "| 2026-10-17 | **交付件依据件换档", [S9_12_D64], "Stage9 §12 D64 行")
    save(S9, "\n".join(lines) + "\n")


def do_autora_readme() -> None:
    text = load(RA)
    if "R1p-u" in text:
        print(f"[跳过] {RA.name}：D64 已落纸")
        return
    lines = text.splitlines()
    P_GEN = "| `stage9_report.py` | **Stage 9 落盘报告生成器**"
    P_CG = "| `check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, P_GEN, "**546 行**", "**554 行**", "AutoRA README §7：stage9_report.py 546 → 554")
    patch_row(lines, P_CG, "**460 行、62/62", "**466 行、63/63", "AutoRA README §7：check_stage9_report")
    append_in_row(lines, P_CG, "D64 新增 R1p-u（同方差的实测支持）", "AutoRA README §7：check_stage9_report 的 D64 注记",
                  guard="R1p-u")
    save(RA, "\n".join(lines) + "\n")


def do_ddm_readme() -> None:
    text = load(RM)
    if "## 8.39 " in text:
        print(f"[跳过] {RM.name}：D64 已落纸")
        return
    lines = text.splitlines()
    ins_before(lines, "## 9. 尚未做", RM_839, "DDM README §8.39")
    ins_after(lines, "| 47 | ✅ **本机 ", [RM_ITEM48], "DDM README §9 第 48 项")
    save(RM, "\n".join(lines) + "\n")


def main() -> int:
    for fn in (do_master_plan, do_stage9, do_autora_readme, do_ddm_readme):
        print(f"\n===== {fn.__name__} =====")
        fn()
    print(f"\n{'✅ 已应用' if APPLY else 'ℹ️ 干跑完成（加 --apply 写盘）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
