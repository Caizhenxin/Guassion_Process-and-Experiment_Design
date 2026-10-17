"""把决策 D59 落进四份文档（主计划 / Stage 9 方案 / AutoRA README / DDM README）。

D59 = 「判据带宽的标定种子必须独立重抽；`(A)` 与 `(B)` 两根带子不许互相顶替」。

体例（与前几轮一致）：
  * 插入：`find_prefix()` 前缀定位（命中数必须为 1）+ `ins_after()` **新行分隔符数必须等于锚点行**；
  * 就地更正：`row_patch()` 在**已定位的那一行内**替换（断言命中次数）+ `tail_row()` 把文字追加到
    该行**最后一格内**（闭合竖线之前）并断言竖线数不变；
  * 幂等：`tail_row` 的 `guard` 命中即跳过；插入用 `GUARD` 全文检测；
  * 输出必须以换行结尾（`save()` 断言）。

用法：`python -u _scratch/_apply_d59.py` 只干跑；`--apply` 才写盘。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3]  # _scratch → DDM_Core → 1_Code → 仓库根
APPLY = "--apply" in sys.argv

MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
RA = ROOT / "1_Code" / "AutoRA_SPE" / "README.md"
RM = ROOT / "1_Code" / "DDM_Core" / "README.md"


# --------------------------------------------------------------------------- #
# 基础设施
# --------------------------------------------------------------------------- #
def n_sep(s: str) -> int:
    return s.count("|")


def load(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def save(p: Path, text: str) -> None:
    assert text.endswith("\n"), f"{p.name}：输出没有以换行结尾"
    if not APPLY:
        print(f"   （干跑）{p.name}：{len(text.splitlines())} 行，未写盘")
        return
    p.write_text(text, encoding="utf-8", newline="")


def find_prefix(lines: list[str], prefix: str, what: str) -> int:
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(hits) == 1, f"{what}：前缀命中 {len(hits)} 行（要求 1）：{prefix[:60]!r}"
    return hits[0]


def ins_after(lines: list[str], idx: int, new_lines: list[str], what: str) -> None:
    anchor = n_sep(lines[idx])
    for l in new_lines:
        assert n_sep(l) == anchor, f"{what}：新行分隔符数 {n_sep(l)} != 锚点 {anchor}"
    lines[idx + 1:idx + 1] = new_lines


def insert_block(lines: list[str], idx: int, new_lines: list[str], what: str) -> None:
    """把整块内容插到第 idx 行之后（用于插入**带表格**的成节内容，不做竖线数断言）。"""
    lines[idx + 1:idx + 1] = new_lines


def row_patch(line: str, old: str, new: str, what: str, expect: int = 1) -> str:
    got = line.count(old)
    assert got == expect, f"{what}：{old!r} 命中 {got} 次（要求 {expect}）"
    return line.replace(old, new)


def tail_row(line: str, suffix: str, what: str, guard: str) -> str:
    s = line.rstrip("\n")
    assert s.endswith("|"), f"{what}：行末没有闭合竖线"
    if guard in s:
        print(f"   ⏭ {what}：已含标记，跳过")
        return line
    out = s[:-1].rstrip() + " " + suffix + " |"
    assert n_sep(out) == n_sep(s), f"{what}：追加后竖线数从 {n_sep(s)} 变成 {n_sep(out)}"
    return out + "\n"


def line_list(text: str) -> list[str]:
    assert text.endswith("\n"), "输入没有以换行结尾"
    return text.split("\n")[:-1]


def join(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# 主计划
# --------------------------------------------------------------------------- #
D59_ROW = (
    '| **D59** | 2026-10-16 | ✅ **判据带宽的标定种子必须独立重抽；`(A)` 与 `(B)` 两根带子不许互相顶替**。'
    '① ❗ **缺陷一（带宽被低报）**：`1_Code/AutoRA_SPE/stage9_loop.py::measure_noise` 的标定种子原为 '
    '`cell_seed(d["name"], ev.base_seed + 791_900 + 37 * k)`，而 `cell_seed(name, base) = (base + int(sha256(name)[:12], 16)) % 2**32` '
    '⇒ `n_repeats` 次重复落在**同一个哈希值上的算术邻居**上 —— 它们是**不同的**种子，但**不是独立重抽**（同一族内部相关）。'
    '② **实测（`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`，四族对照：CRN / 旧标定族 / 另一族邻居 / 无关种子）**：'
    '`n_fim = 1` 下锚点 D4 的 CRN 读数 `A = 0.385802`；旧标定族 `sd_A = 0.004779`（均值 0.354077）；'
    '另一族邻居 `sd_A = 0.015623`；**48 个无关种子 `sd_A = 0.018933`（= 旧族的 4.0 倍）**、中位 0.352165、'
    'MAD 0.014055、IQR 0.022347、极差 `[0.298688, 0.390828]`，直方图单峰而重尾（1/1/1/3/6/14/7/5/7/3）'
    '⇒ ❗ **假设 H1「邻居种子之间相关」被否**（另一族邻居的散布接近无关族），真因是**6 个样本在重尾分布上估 `sd`**。'
    '而 `n_fim = 12` 下旧标定族 `sd_A = 0.008586` **不**偏小（12 个无关种子 0.006897）⇒ **4 倍低报是 `n_fim = 1` 特有的**。'
    '③ ❗ **缺陷二（裁决短路）**：`compare_arms` 在 `ΔA` 落在噪声带内时**借 `ΔB` 的带子**得出「被支配」或「两者不可分辨」，'
    '把两根**各自有独立不确定度**的带子搅成一句判词。'
    '④ **换带重判（离线、只读）**：新建 `1_Code/AutoRA_SPE/_scratch_reverdict.py`，用无关族的带子'
    '（`2·sd_A = 0.0379`、`2·sd_B = 0.3761`）重判 `n_fim = 1` 的四臂 ⇒ **4/4 条裁决文本都变**：'
    '`random` 与 `grid` 仍「在 (A) 与 (B) 上都不可分辨」；`manual` 由「**被 `random` 支配**」改为'
    '「**在 (B) 上显著更差**（`ΔB = −0.8885 < −0.3761`），而 (A) 分量不可分辨（`ΔA = 0.0108 ≤ 0.0379`）」；'
    '`bo` 仍是「在 **(A)** 上显著更差」（`ΔA = 0.1232`；旧带 24.5 倍、新带 3.3 倍）。'
    '⑤ ❗❗ **头条改变**：锚点 D4 与最优可行设计的 `ΔA = 0.041159` ⇒ 旧带（`2·sd_A = 0.005030`）下印 **8.18 倍**、'
    '新带（`0.037866`）下只有 **1.09 倍** ⇒ **`n_fim = 1` 下没有任何证据说「推荐点比 D4 好」**。'
    '⑥ **修法**：标定种子改为 `cell_seed(f"{d[\'name\']}#noise{k}", ev.base_seed)`（名字不同 ⇒ 哈希不同 ⇒ 与任意设计种子同分布且独立），'
    '`measure_noise` 的返回字典新增 `seeds`（逐次种子）与 `family`（生成式）；`compare_arms` 改为「两根带子各判各的」'
    '（头名四分：都不可分辨 / (A) 不可分辨但 (B) 显著更差 / (A) 不可分辨但 (B) 更好 / `ΔA` 超带且 B 不差才是「(A,B) 上最好」；'
    '非头名新增「在 (B) 上显著更差 / 更好」两条）；`stage9_report.py` §2 印出标定种子（缺失则印「本落盘件没有记录标定种子」的警告），'
    '§7 的「几倍带子」一律附带「只与标定种子样本一样可靠」的限制句。'
    '⑦ **牙齿**：`1_Code/AutoRA_SPE/check_stage9_loop.py` 新增 **E10a–E10d**（`ΔA` 在带内但 `ΔB` 超带的四条）'
    '与 **H6/H6b**（种子生成式与 `seeds`/`family` 的静态钉子）⇒ 465 → **530 行、47/47**；'
    '`1_Code/AutoRA_SPE/check_stage9_report.py` 新增 **R1p-j/k/l** ⇒ 346 → **362 行、50/50**。'
    '⑧ **待办**：正式 `n_fim = 12` 的全空间重跑（`--noise-repeats 16`）仍在进行，其读数与「`n_fim = 1` 下 123/174 病态候选是否只是 `n_fim` 的产物」一并以 D60 落纸。'
    ' | '
    '① `1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`（**新建**，222 行，四族 × `n_fim ∈ {1, 12}`）与日志 '
    '`1_Code/AutoRA_SPE/_scratch_anchor_scan_nfim1_u8.txt`（61 次评估、246.5 s）、'
    '`1_Code/AutoRA_SPE/_scratch_anchor_scan_nfim12_u8.txt`（25 次评估、965.3 s）；'
    '② `1_Code/AutoRA_SPE/_scratch_noise_repeats.py`（**新建**，61 行）：同一锚点各 6 次 —— `n_fim = 1` 六读数 '
    '`0.35864 / 0.35508 / 0.34523 / 0.35509 / 0.35290 / 0.35750`（均值 0.35408、`sd_A = 0.00478`）、'
    '`n_fim = 12` 六读数 `0.34428 / 0.33266 / 0.33432 / 0.32370 / 0.34524 / 0.34374`（均值 0.33732、`sd_A = 0.00859`），'
    '且 2 次重复给 `alpha = 0.165` 而 6 次给 **0.393（2.4 倍）**；'
    '③ `1_Code/AutoRA_SPE/_scratch_reverdict.py`（**新建**，151 行）与日志 `1_Code/AutoRA_SPE/_scratch_reverdict_nfim1_u8.txt`；'
    '④ `1_Code/AutoRA_SPE/check_stage9_loop.py` **47/47、exit 0、48.8 s**、'
    '`1_Code/AutoRA_SPE/check_stage9_report.py` **50/50、exit 0**；'
    '⑤ `python 1_Code\\AutoRA_SPE\\check_stage9.py --quick` ⇒ 8 项、未通过 0 项、1.8 s、exit 0。 '
    ' | '
    '① **任何「谁更好」的判词都必须写明它用的是哪一根带子**（`(A)` 与 `(B)` 各判各的）；'
    '② **`n_fim = 1` 档的全部裁决与「几倍带子」读数一律按 D59 的限制句读**，不得单独引用；'
    '③ **凡报出「推荐点比锚点好 N 倍带宽」的句子，必须同时报 `n_repeats` 与标定种子**；'
    '④ 标定重复数日后一律 `--noise-repeats ≥ 6`（正式跑用 16）；'
    '⑤ D55 第 18 条的三种处置仍待拍板，且本轮又添一条：**锚点 D4 与推荐点的差距在这一档下不显著** |'
)

D59_PROGRESS = (
    '| 2026-10-16 | **9**（判据带宽的标定种子 + 裁决短路 → D59） | '
    '**追查一个「锚点读数与标定族对不上」的疑点（同一次运行里 D4 的 `A = 0.385802`，标定两次却给出 0.358641 / 0.355084，'
    '差 12.6 倍 `sd_A`），结果挖出两处真缺陷**。'
    '① ❗ **标定种子是同一哈希值上的算术邻居**：`cell_seed(d["name"], base + 791_900 + 37 * k)` ⇒ `n_repeats` 次重复**不独立**；'
    '四族对照实测（`n_fim = 1`）旧族 `sd_A = 0.004779`、48 个无关种子 **0.018933（4.0 倍）**、另一族邻居 0.015623 '
    '⇒ 假设「邻居种子相关」被否，真因是**6 个样本在重尾分布上估 `sd`**；`n_fim = 12` 下旧族**不**偏小（0.008586 vs 无关 0.006897）。'
    '② ❗ **裁决短路**：`ΔA` 在带内时旧码借 `ΔB` 的带子得出「被支配 / 不可分辨」；换带重判后 **4/4 条裁决文本都变**，'
    '其中 `manual` 由「被 `random` 支配」改为「在 (B) 上显著更差、而 (A) 分量不可分辨」。'
    '③ ❗❗ **头条被推翻**：锚点与最优可行设计的 `ΔA = 0.041159` 在旧带下是 **8.18 倍**、在诚实带下只有 **1.09 倍** '
    '⇒ `n_fim = 1` 下**没有任何证据**说推荐点比 D4 好。'
    '④ **修法**：种子改 `cell_seed(f"{d[\'name\']}#noise{k}", ev.base_seed)` + 返回 `seeds`/`family`；'
    '`compare_arms` 两根带子各判各的；报告 §2 印标定种子、§7 加限制句。'
    '⑤ **牙齿**：E10a–E10d + H6/H6b（循环自测 465 → **530 行、47/47**）、R1p-j/k/l（报告自测 346 → **362 行、50/50**）。'
    ' | `1_Code/AutoRA_SPE/stage9_loop.py`（831 → **886 行**）；`1_Code/AutoRA_SPE/check_stage9_loop.py`（465 → **530 行、47/47**）；'
    '`1_Code/AutoRA_SPE/stage9_report.py`（370 → **397 行**）；`1_Code/AutoRA_SPE/check_stage9_report.py`（346 → **362 行、50/50**）；'
    '`1_Code/AutoRA_SPE/stage9_report.md`（**131 行**）；`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`（**新建**，222 行）；'
    '`1_Code/AutoRA_SPE/_scratch_noise_repeats.py`（**新建**，61 行）；`1_Code/AutoRA_SPE/_scratch_reverdict.py`（**新建**，151 行） '
    '| 🔨 **仍开放**：**(1)** 🛑 遗漏率带 `[0.05, 0.20]` 与锚点 D4 不相容（D55 第 18 条）—— 三选一，**须用户或导师拍板**；'
    '**(2)** 正式 `n_fim = 12`（`--noise-repeats 16`）的全空间重跑与可行域构成对照（D60）；'
    '**(3)** 四个用户侧 Stage（1 实机验收 N=2–3 / 6 Pilot N≈8 / 7 正式采集 4 组 × ~40 / 定稿签批）；'
    '**(4)** D41 拍板（是否装 `pymc` + `arviz`）；'
    '**(5)** 真实数据到手后的 `cellmean.py` 剖面诊断（`1_Code/DDM_Core/README.md` §9 第 19 项） |'
)

D59_CHANGELOG = (
    '| 2026-10-16 | **新增 D59：判据带宽的标定种子必须独立重抽（旧族的 `n_repeats` 次重复落在同一哈希值的算术邻居上 ⇒ '
    '`n_fim = 1` 下 `sd_A` 低报 4.0 倍）；`(A)` 与 `(B)` 两根带子不许互相顶替（换带重判后 4/4 条裁决文本都变，'
    '且「推荐点比锚点好 8.18 倍带宽」变成 **1.09 倍**）；报告必须印出标定种子与 `n_repeats`** |'
)

D59_APPENDIX = (
    '| `1_Code/AutoRA_SPE/stage9_loop.py`（831 → **886 行**） + `1_Code/AutoRA_SPE/check_stage9_loop.py`（465 → **530 行**、**47/47**） '
    '+ `1_Code/AutoRA_SPE/stage9_report.py`（370 → **397 行**） + `1_Code/AutoRA_SPE/check_stage9_report.py`（346 → **362 行**、**50/50**） '
    '+ `1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`（**新建**，222 行） + `1_Code/AutoRA_SPE/_scratch_noise_repeats.py`（**新建**，61 行） '
    '+ `1_Code/AutoRA_SPE/_scratch_reverdict.py`（**新建**，151 行） '
    '| **D59**：① 标定种子改由 `{名称}#noise{k}` 导出（独立重抽）并落盘 `seeds`/`family`；② `compare_arms` 四分支头名 + 两分支非头名，'
    '取消「借另一根带子判定」的短路；③ 报告 §2 印标定种子（缺失则警告）、§7 的倍数自带限制句；'
    '④ 四族种子探针（`n_fim = 1/12`）给出「4 倍低报是 `n_fim = 1` 特有」；⑤ 离线换带重判证明 `n_fim = 1` 的头条不成立 |'
)


def do_master_plan() -> None:
    text = load(MP)
    if "| **D59** | 2026-10-16 |" in text:
        print(f"⏭ {MP.name}：D59 已落纸，跳过")
        return
    lines = line_list(text)

    # ① 四处插入
    i = find_prefix(lines, "| **D58** | 2026-10-16 |", "主计划决策行锚点")
    ins_after(lines, i, [D59_ROW], "主计划 D59 决策行")

    i = find_prefix(lines, "| 2026-10-16 | **9**（`n_fim` 可行域重测", "主计划进度行锚点")
    ins_after(lines, i, [D59_PROGRESS], "主计划 D59 进度行")

    i = find_prefix(lines, "| 2026-10-16 | **新增 D58：", "主计划变更日志锚点")
    ins_after(lines, i, [D59_CHANGELOG], "主计划 D59 变更日志行")

    hits = [k for k, l in enumerate(lines) if l.startswith("| `1_Code/AutoRA_SPE/stage9_loop.py`（821 → **831 行**）")]
    assert len(hits) == 1, f"主计划附录锚点：命中 {len(hits)} 行（要求 1）"
    ins_after(lines, hits[0], [D59_APPENDIX], "主计划 D59 附录证据行")

    # ② 就地更正：D58 进度行「仍开放」里那句「`2·sd_A` 目前只由 2 次重复估出」
    i = find_prefix(lines, "| 2026-10-16 | **9**（`n_fim` 可行域重测", "主计划 D58 进度行（更正）")
    if "更正（见 D59）" in lines[i]:
        print("   ⏭ 主计划 D58 进度行：更正已存在")
    else:
        lines[i] = row_patch(
            lines[i],
            "重复 R 个种子组以得到配对误差棒（`2·sd_A` 目前只由 2 次重复估出）。",
            "重复 R 个种子组以得到配对误差棒（`2·sd_A` 目前只由 2 次重复估出）。 "
            "❌ **2026-10-16 更正（见 D59）**：这一句低估了问题 —— 旧标定族的 `n_repeats` 次重复落在"
            "**同一个哈希值上的算术邻居**上，`n_fim = 1` 下 `sd_A = 0.0048` 而 48 个**无关**种子给 **0.0189（4.0 倍）**；"
            "即「重复几次」之外还要问「**是不是独立重抽**」。",
            "主计划 D58 进度行更正",
        )
    save(MP, join(lines))
    print(f"✅ {MP.name}：写入 D59（决策行 / 进度行 / 变更日志 / 附录 + 一处就地更正）")


# --------------------------------------------------------------------------- #
# Stage 9 方案文档
# --------------------------------------------------------------------------- #
S9_11_24 = (
    "24. ❗ **判据带宽自己也有不确定度，而且它的来源必须被记录（D59）**：`1_Code/AutoRA_SPE/stage9_loop.py::measure_noise` "
    "原先把标定种子写成 `cell_seed(d[\"name\"], base + 791_900 + 37 * k)` —— 它们是**不同的**种子，但都落在"
    "**同一个哈希值的算术邻居**上，因此**不是独立重抽**。实测（锚点 D4）：`n_fim = 1` 下旧族 `sd_A = 0.004779`，"
    "48 个**无关**种子给 `0.018933`（**4.0 倍**）；另一族邻居 `0.015623` ⇒ **「邻居之间相关」这条假设被否**，"
    "真因是**样本少（6 个）而分布重尾**（48 个无关种子的直方图 1/1/1/3/6/14/7/5/7/3，极差 `[0.2987, 0.3908]`）。"
    "`n_fim = 12` 下旧族**不**偏小 ⇒ **4 倍低报是 `n_fim = 1` 特有的**。"
    "纪律：① 报「推荐点比锚点好 N 倍带宽」时，**必须同时报 `n_repeats` 与标定种子**；"
    "② `(A)` 与 `(B)` 两根带子**各判各的** —— `ΔA` 在带内**不等于**「两者不可分辨」，"
    "而且**不得用 `(B)` 的带子替 `(A)` 做判断**；③ 换一根诚实的带子后，`n_fim = 1` 的四臂裁决 **4/4 条文本都变**，"
    "「推荐点比 D4 好 8.18 倍带宽」变成 **1.09 倍** ⇒ 该档**没有任何证据**支持「推荐点更好」。"
)

S9_12_D59 = (
    "| 2026-10-16 | **判据带宽的标定种子与裁决短路（决策 D59）**：`measure_noise` 的标定种子由算术邻居改为由 `{名称}#noise{k}` 导出"
    "（并落盘 `seeds`/`family`）；`compare_arms` 取消「借另一根带子判定」的短路（头名四分、非头名两分）；"
    "报告 §2 印标定种子、§7 的「几倍带子」自带限制句。`1_Code/AutoRA_SPE/stage9_loop.py` 831 → **886 行**、"
    "`check_stage9_loop.py` 465 → **530 行（47/47，E10a–E10d + H6/H6b）**、`stage9_report.py` 370 → **397 行**、"
    "`check_stage9_report.py` 346 → **362 行（50/50，R1p-j/k/l）**、`stage9_report.md` **131 行** "
    "| 四族种子探针（`n_fim = 1`：旧族 0.0048 vs 48 个无关种子 0.0189）、6 次重复探针、"
    "离线换带重判（4/4 条裁决文本都变，「8.18 倍」→「1.09 倍」） |"
)


def do_stage9() -> None:
    text = load(S9)
    if "决策 D59" in text:
        print(f"⏭ {S9.name}：D59 已落纸，跳过")
        return
    lines = line_list(text)

    # ① §9 文件表：五处数字
    i = find_prefix(lines, "| `1_Code/AutoRA_SPE/stage9_loop.py` | CRN 预计算表", "Stage9 §9 loop 行")
    lines[i] = row_patch(lines[i], "**831 行**", "**886 行**", "Stage9 §9 loop 行数")
    lines[i] = row_patch(
        lines[i], "D58 前为 821 行", "D58 前为 821 行、D59 前为 831 行", "Stage9 §9 loop 历史行数"
    )

    i = find_prefix(lines, "| `1_Code/AutoRA_SPE/check_stage9_loop.py` |", "Stage9 §9 loop 自测行")
    lines[i] = row_patch(lines[i], "**465 行**", "**530 行**", "Stage9 §9 loop 自测行数")
    lines[i] = row_patch(
        lines[i], "D58 前为 423 行", "D58 前为 423 行、D59 前为 465 行", "Stage9 §9 loop 自测历史行数"
    )
    lines[i] = row_patch(lines[i], "**41/41", "**47/47", "Stage9 §9 loop 自测通过数")

    i = find_prefix(lines, "| `1_Code/AutoRA_SPE/stage9_report.py` |", "Stage9 §9 报告生成器行")
    lines[i] = row_patch(lines[i], "**370 行**", "**397 行**", "Stage9 §9 报告生成器行数")

    i = find_prefix(lines, "| `1_Code/AutoRA_SPE/check_stage9_report.py` |", "Stage9 §9 报告自测行")
    lines[i] = row_patch(lines[i], "**346 行**", "**362 行**", "Stage9 §9 报告自测行数")
    lines[i] = row_patch(lines[i], "**47/47", "**50/50", "Stage9 §9 报告自测通过数")

    i = find_prefix(lines, "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告", "Stage9 §9 落盘报告行")
    lines[i] = row_patch(lines[i], "**128 行**", "**131 行**", "Stage9 §9 落盘报告行数")

    # ② §11 新增第 24 条（插在第 23 条之后）
    i = find_prefix(lines, "23. ❗ **小预算下 BO 会退化成随机采样", "Stage9 §11 第 23 条锚点")
    ins_after(lines, i, [S9_11_24], "Stage9 §11 第 24 条")

    # ③ §12 新增 D59 行
    i = find_prefix(lines, "| 2026-10-16 | **正式 `n_fim` 下的可行域重测 + 决策 D58**", "Stage9 §12 D58 行锚点")
    ins_after(lines, i, [S9_12_D59], "Stage9 §12 D59 行")

    save(S9, join(lines))
    print(f"✅ {S9.name}：§9 五处数字 + §11 第 24 条 + §12 D59 行")


# --------------------------------------------------------------------------- #
# AutoRA README
# --------------------------------------------------------------------------- #
def do_autora() -> None:
    text = load(RA)
    if "D59" in text:
        print(f"⏭ {RA.name}：D59 已落纸，跳过")
        return
    lines = line_list(text)

    i = find_prefix(lines, "| `stage9_loop.py` |", "AutoRA §7 loop 行")
    lines[i] = row_patch(lines[i], "**831 行**", "**886 行**", "AutoRA §7 loop 行数")
    lines[i] = row_patch(
        lines[i],
        "D58 起 `arm_bo` 的 `n_init` 下限为 1",
        "D58 起 `arm_bo` 的 `n_init` 下限为 1；D59 起标定种子由 `{名称}#noise{k}` 导出（独立重抽）并落盘 `seeds`/`family`",
        "AutoRA §7 loop 说明",
    )

    i = find_prefix(lines, "| `check_stage9_loop.py` |", "AutoRA §7 loop 自测行")
    lines[i] = row_patch(lines[i], "**41/41**", "**47/47**", "AutoRA §7 loop 自测通过数")

    i = find_prefix(lines, "| `stage9_report.py` |", "AutoRA §7 报告生成器行")
    lines[i] = row_patch(lines[i], "**370 行**", "**397 行**", "AutoRA §7 报告生成器行数")
    lines[i] = row_patch(
        lines[i],
        "`build(payload_path) -> str`",
        "`build(payload_path) -> str`；D59 起 §2 印出标定种子与 `n_repeats`、§7 的「几倍带子」自带限制句",
        "AutoRA §7 报告生成器说明",
    )

    i = find_prefix(lines, "| `check_stage9_report.py` |", "AutoRA §7 报告自测行")
    lines[i] = row_patch(lines[i], "**346 行、47/47", "**362 行、50/50", "AutoRA §7 报告自测行")

    i = find_prefix(lines, "| `stage9_report.md` |", "AutoRA §7 落盘报告行")
    lines[i] = row_patch(lines[i], "**128 行**", "**131 行**", "AutoRA §7 落盘报告行数")

    save(RA, join(lines))
    print(f"✅ {RA.name}：§7 五行数字/说明")


# --------------------------------------------------------------------------- #
# DDM README
# --------------------------------------------------------------------------- #
RM_834 = """## 8.34 判据带宽的标定种子必须独立重抽；两根带子不许互相顶替（2026-10-16，D59）

### 1. 为什么要做这一节

D58 之后主计划上只剩「在正式 `n_fim` 下重测可行域构成」与几个待拍板项，于是先把长跑挂上后台，
回头核对 `1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json` 里两个**本该一致**的读数：
同一次运行的锚点 D4 在 `cache` 里是 `A = 0.3858017952097037`，而 `noise` 段的两次标定重复给出
`0.358641 / 0.355084`。差 `0.0317` = `sd_A = 0.0025152` 的 **12.6 倍**。

先排除了两个机制：`1_Code/DDM_Core` 侧的 `stage9_objective.evaluate()` 与 `stage9_loop._anchor_of()`
**同路**（都用 `component_A(res)`、`params=None` ⇒ `FROZEN["params_C6"]`），所以不是参数集不同；
`Evaluator._raw()` 记的 `seed=cell_seed(d["name"], base_seed)` 与缓存记录也一致，所以不是种子记录错位。
剩下唯一可疑的是**标定那两次用的种子**。

### 2. 代码改动清单（5 处）

1. `1_Code/AutoRA_SPE/stage9_loop.py::measure_noise`：标定种子由
   `cell_seed(d["name"], ev.base_seed + 791_900 + 37 * k)` 改为
   `cell_seed(f"{d['name']}#noise{k}", ev.base_seed)`，并在 docstring 里写入实测数字与「不是邻居相关」的结论。
2. `1_Code/AutoRA_SPE/stage9_loop.py::measure_noise`：返回字典新增 `seeds`（逐次种子）与 `family`（生成式字符串）
   ⇒ 落盘件**自己**能证明「这几次重复是不是独立重抽」。
3. `1_Code/AutoRA_SPE/stage9_loop.py::compare_arms`：取消「`ΔA` 在带内时借 `ΔB` 的带子判定」的短路 ——
   头名四分（都不可分辨／(A) 不可分辨但 (B) 显著更差／(A) 不可分辨但 (B) 更好／`ΔA` 超带且 B 不差才是「(A,B) 上最好」），
   非头名新增「在 (B) 上显著更差／更好」两条。「在 (A) 上不可分辨」**不再**被写成「两者不可分辨」。
4. `1_Code/AutoRA_SPE/stage9_report.py` §2：有 `noise["seeds"]` 就印出标定种子族与全部种子；
   没有（D59 之前的落盘件）就印警告「本落盘件没有记录标定种子 ⇒ 无法复核 `sd` 是独立重抽还是同一族算术邻居，
   后者实测会把 `sd_A` 低报约 4 倍」。
5. `1_Code/AutoRA_SPE/stage9_report.py` §7：「推荐点比锚点好 N 倍带宽」这一行后面一律加限制句
   （分母来自 `n_repeats` 次重抽；`n_fim = 1` 下同一份 `ΔA = 0.0412` 可印成 8.2 倍或 1.1 倍）。

### 3. 缺陷一：标定种子是「算术邻居」

`1_Code/AutoRA_SPE/stage9_loop.py::cell_seed(name, base) = (base + int(sha256(name.encode()).hexdigest()[:12], 16)) % 2**32`。
旧式 `base + 791_900 + 37 * k` 因此是**同一个哈希值加一个小偏移** —— 每次的种子确实不同，
但它们不是独立抽样。四族对照（`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`，222 行）：

| 族 | `n_fim = 1` 的 `sd_A` | `n_fim = 12` 的 `sd_A` |
|---|---|---|
| 旧标定族（`+791_900 + 37k`，6 个） | 0.004779 | 0.008586 |
| 另一族邻居（`+4_000_000 + 37k`，6 个） | 0.015623 | 0.004341 |
| **无关种子**（`default_rng(20261016).integers`） | **0.018933**（n = 48） | 0.006897（n = 12） |

- `n_fim = 1`：旧族把 `sd_A` 低报 **4.0 倍**（0.0048 vs 0.0189）。48 个无关种子的均值 0.354149、
  中位 0.352165、MAD 0.014055、IQR 0.022347、极差 `[0.298688, 0.390828]`，直方图单峰而重尾
  （1/1/1/3/6/14/7/5/7/3）⇒ ❗ **假设「邻居种子之间相关」被否**（间隔同样为 37 的另一族散布正常），
  真因是**6 个样本在重尾分布上估 `sd`**。
- `n_fim = 12`：旧族**不**偏小（反而略大）⇒ **4 倍低报是 `n_fim = 1` 特有的**。
- 附带读数（`1_Code/AutoRA_SPE/_scratch_noise_repeats.py`）：2 次重复给 `alpha = 0.165`、6 次给 **0.393（2.4 倍）**，
  且两次重复用的是**同一对固定种子** ⇒ 该偏差在多次运行之间是相关的，不是随机噪声。

### 4. 缺陷二：`ΔA` 在带内时借 `ΔB` 的带子判定

旧 `compare_arms` 在 `ΔA ≤ 2·sd_A` 时直接用 `ΔB` 与 `2·sd_B` 得出一句判词（「被支配」或「不可分辨」）。
但两根带子各有自己的不确定度：`ΔA` 落在 `(A)` 的带内，只说明**关于 `(A)` 没有分辨率**，
它既不支持也不否定关于 `(B)` 的结论。`n_fim = 1` 的实测里，这条短路把 `manual` 印成「被 `random` 支配」，
换成诚实的带子后判词变成「在 (B) 上显著更差，而 (A) 分量不可分辨」。

### 5. 换带重判：`n_fim = 1` 的头条被推翻

`1_Code/AutoRA_SPE/_scratch_reverdict.py`（151 行，纯离线、只读）用 payload 自己的 `histories`
与**替换后的** `sd_A`/`sd_B` 各调一次 `compare_arms()`：

| 臂 | 旧带（`2·sd_A = 0.0050`、`2·sd_B = 0.2665`） | 诚实带（`0.0379`、`0.3761`） |
|---|---|---|
| `random`（0.3881） | 在 (A) 与 (B) 上都不可分辨 | 同 |
| `grid`（0.3897） | 在 (A) 与 (B) 上都不可分辨 | 同 |
| `manual`（0.3989） | **被 `random` 支配** | **在 (B) 上显著更差**（(A) 分量不可分辨） |
| `bo`（0.5113） | 在 (A) 上显著更差 | 同（倍数由 24.5 降到 3.3） |

❗❗ 最关键的是第 7 节那个「锚点离最优多远」：`ΔA = 0.041159` 在旧带下是 **8.18 倍**带宽，
在诚实带下只有 **1.09 倍** ⇒ **`n_fim = 1` 档没有任何证据说推荐点比锚点 D4 好**。

### 6. 校验证据

1. `python -u 1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py 1 48 1_Code/AutoRA_SPE/_scratch_anchor_scan_nfim1_u8.txt`
   ⇒ 61 次评估、246.5 s；`... 12 12 ...` ⇒ 25 次评估、965.3 s（两条日志都在 `1_Code/AutoRA_SPE/`）。
2. `python -u 1_Code/AutoRA_SPE/_scratch_noise_repeats.py` ⇒ 两条短日志 `_scratch_noise_repeats_u8.txt`。
3. `python -u 1_Code/AutoRA_SPE/_scratch_reverdict.py 1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json 0.018933 0.188060`
   ⇒ `_scratch_reverdict_nfim1_u8.txt`（exit 0）。
4. `python -u 1_Code/AutoRA_SPE/check_stage9_loop.py 1 1_Code/AutoRA_SPE/_scratch_check_stage9_loop_d59_u8.txt`
   ⇒ **47/47、未通过 0 项、exit 0、48.8 s**（新增 E10a–E10d + H6/H6b）。
5. `python -u 1_Code/AutoRA_SPE/check_stage9_report.py` ⇒ **50/50、未通过 0 项、exit 0**
   （新增 R1p-j/k/l）；`stage9_report.md` 重新生成 ⇒ **131 行**。
6. `python 1_Code\\AutoRA_SPE\\check_stage9.py --quick` ⇒ 8 项、未通过 0 项、1.8 s、exit 0。

### 7. 尚未做

1. **正式 `n_fim = 12` 的全空间重跑**（`--noise-repeats 16`，后台作业）尚未落盘 ⇒ 「`n_fim = 1` 下
   174 个候选里 123 个被数值条件数刷掉」是不是 `n_fim` 的产物，要等它与 `_scratch_payload_nfim12.json`
   用 `1_Code/AutoRA_SPE/_scratch_cmp_nfim.py` 对照后才有答案。
2. 交付件 `1_Code/AutoRA_SPE/stage9_report.md` 的依据件仍是 `n_fim = 1` 那份 ——
   D59 已证明该档的裁决带宽不可用，换依据件要等第 1 条落盘。
3. 🛑 遗漏率带 `[0.05, 0.20]` 与锚点 D4 的 `0.361111` 不相容（D55 第 18 条）仍待拍板。
"""

RM_ITEM43 = (
    "| 43 | ✅ **判据带宽的标定种子必须独立重抽；两根带子不许互相顶替（D59，§8.34）** | 起因是同一次运行里"
    "锚点 `A = 0.385802` 与标定两次的 `0.358641 / 0.355084` 差 12.6 倍 `sd_A`。四族种子探针证明旧标定族"
    "（`+791_900 + 37k`）在 `n_fim = 1` 下把 `sd_A` 低报 **4.0 倍**（0.0048 vs 48 个无关种子的 0.0189），"
    "而 `n_fim = 12` 下不低报 ⇒ 4 倍低报是该档特有的；「邻居相关」这条假设被另一族邻居（0.0156）否掉，"
    "真因是**6 个样本估重尾分布的 `sd`**。改法：种子由 `{名称}#noise{k}` 导出 + 落盘 `seeds`/`family`；"
    "`compare_arms` 取消「借另一根带子判定」的短路（头名四分、非头名两分）；报告印标定种子与限制句。"
    "**换带重判（`_scratch_reverdict.py`）后 `n_fim = 1` 的四臂裁决 4/4 条文本都变，"
    "「推荐点比锚点好 8.18 倍带宽」变成 1.09 倍 ⇒ 该档没有任何证据支持「推荐点更好」**。"
    "`stage9_loop.py` 831 → **886 行**、`check_stage9_loop.py` 465 → **530 行（47/47）**、"
    "`stage9_report.py` 370 → **397 行**、`check_stage9_report.py` 346 → **362 行（50/50）**、`stage9_report.md` **131 行** |"
)


def do_ddm_readme() -> None:
    text = load(RM)
    if "## 8.34 " in text:
        print(f"⏭ {RM.name}：§8.34 已存在，跳过")
        return
    lines = line_list(text)

    i = find_prefix(lines, "## 9. 尚未做", "DDM README §9 标题锚点")
    assert lines[i - 1].strip() == "", "DDM README：§9 标题之前不是空行，需人工确认"
    insert_block(lines, i - 1, RM_834.rstrip("\n").split("\n") + [""], "DDM README §8.34")

    j = find_prefix(lines, "| 42 | ✅ **正式 `n_fim` 下的可行域重测", "DDM README §9 第 42 项锚点")
    ins_after(lines, j, [RM_ITEM43], "DDM README §9 第 43 项")

    # 就地更正：§8.33 §7 第 4 条那句「只由 2 次重复估出」
    k = find_prefix(lines, "4. 重复 **R 个种子组**以得到配对误差棒", "DDM README §8.33 §7 第 4 条")
    if "更正（见 D59）" not in lines[k]:
        lines[k] = row_patch(
            lines[k],
            "4. 重复 **R 个种子组**以得到配对误差棒（`2·sd_A` 目前只由 2 次重复估出）。",
            "4. 重复 **R 个种子组**以得到配对误差棒（`2·sd_A` 目前只由 2 次重复估出）。 "
            "❌ **2026-10-16 更正（见 D59、§8.34）**：这一句低估了问题 —— 旧标定族的 `n_repeats` 次重复落在"
            "**同一个哈希值上的算术邻居**上，`n_fim = 1` 下 `sd_A = 0.0048` 而 48 个**无关**种子给 **0.0189（4.0 倍）**；"
            "即除了「重复几次」，还要问「**是不是独立重抽**」。",
            "DDM README §8.33 §7 第 4 条更正",
        )
    else:
        print("   ⏭ DDM README §8.33 §7 第 4 条：更正已存在")

    save(RM, join(lines))
    print(f"✅ {RM.name}：§8.34（七小节）+ §9 第 43 项")


def main() -> int:
    print(f"模式：{'写入' if APPLY else '干跑（只报告）'}")
    do_master_plan()
    do_stage9()
    do_autora()
    do_ddm_readme()
    return 0


if __name__ == "__main__":
    sys.exit(main())
