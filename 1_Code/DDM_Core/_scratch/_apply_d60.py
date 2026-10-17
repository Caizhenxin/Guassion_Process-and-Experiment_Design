"""把决策 **D60** 写进四份文档（干跑优先，`--apply` 才写盘）。

D60 的内容（本轮）：
  ① 缺陷一：`1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 的判据带宽用了**单设计**的
     `2·sd`（`band_a = 2.0 * float(noise.get("sd_A", 0.0))`），而两条臂比的是**两个不同设计**
     ⇒ `Var(差) = 2·sd²` ⇒ 带宽应为 `2·√2·sd`（旧值窄 √2 ≈ 1.41 倍、偏宽松）。
  ② 同族第五处：`(A)` 是 MC 估计量 ⇒ 推荐点（可行集内 `(A)` 最小）自带 *winner's curse*；
     逐设计实测 σ（`n_fim = 1`、32 个无关种子）同量级 ⇒ 同方差假设可接受。
  ③ 修法与牙齿：`DIFF_BAND_FACTOR`、`VERDICT_LOGIC` 文案、报告 §2/§5/§7（§5 改为**自己重算判词**）、
     新探针 `_scratch_mean_A_rank.py`、`check_stage9_loop.py` 53/53、`check_stage9_report.py` 57/57。

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
    print(f"✍️  已写盘：{p.relative_to(ROOT)}")


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


def append_text(lines: list[str], prefix: str, suffix: str, what: str, guard: str | None = None) -> None:
    """在**非表格行**（编号条目、段落）行末追加后缀。

    与 `append_in_row` 的区别：编号条目没有闭合竖线 ⇒ 不能要求「行末是 `|`」。
    D56 那轮就踩过一次相反方向的坑（把列表项当表格行 ⇒ `rfind("|")` 返回 −1 而静默放弃整文件）。
    """
    i = idx_of(lines, prefix, what)
    line = lines[i]
    if guard and guard in line:
        print(f"  ⏭️  {what}：已含 {guard!r} ⇒ 跳过")
        return
    assert "|" not in suffix, f"{what}：后缀不得含竖线"
    lines[i] = line.rstrip() + " " + suffix
    print(f"  ➕ {what}（非表格行）")


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


# ---------------------------------------------------------------- 文本常量

D60_ROW = (
    "| **D60** | 2026-10-16 | ✅ **跨设计比较的带宽必须是「差」的噪声带 `2·√2·sd`（不是单设计的 `2·sd`）；"
    "判词不许由落盘件单方面自报，报告必须自己重算；推荐点自带选择偏差，必须另做种子平均**。"
    "① ❗ **缺陷一（带宽系数少 √2）**：`1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 原写 "
    "`band_a = 2.0 * float(noise.get(\"sd_A\", 0.0))`，而 `sd_A` 是**同一个设计**（锚点 D4）在不同种子下的标准差、"
    "两条臂比的是**两个不同设计**（CRN 种子由名字哈希导出 ⇒ 独立）⇒ `Var(差) = 2·sd²` ⇒ 系数应为 `2·√2`；"
    "旧值**窄 √2 ≈ 1.41 倍**，方向是**偏宽松**（更容易自称显著）。"
    "② **同族第五处（选择偏差）**：`(A)` 是 MC 估计量，而推荐点是「可行集内 `(A)` 最小的那个」⇒ 极值统计量、"
    "*winner's curse*。逐设计实测（`n_fim = 1`、32 个无关种子、`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`）："
    "锚点 `sd_A = 0.017976`（CRN 读数 0.385802 比自己的种子均值 0.357344 **高 1.58σ**）、"
    "推荐点 `sd_A = 0.018638`（CRN 0.344643 比自己的均值 0.386742 **低 2.26σ**）、"
    "病态样例 `sd_A = 0.021285`（CRN 0.289613 比均值 0.318175 低 1.34σ）⇒ "
    "**σ 同量级（最大/最小 1.18 倍）⇒ 同方差假设可接受**（只略低估病态设计），"
    "但**单种子 CRN 下的先后可能是抽签结果**。"
    "③ **修法**：`1_Code/AutoRA_SPE/stage9_loop.py` 新增模块常量 "
    "`DIFF_BAND_FACTOR = 2.0 * float(np.sqrt(2.0))`（= 2.8284271247461903）并改 `band_a/band_b`；"
    "`VERDICT_LOGIC` 文案改为「带宽 = **差**的噪声带 `2·√2·sd`」；`1_Code/AutoRA_SPE/stage9_report.py` 同名常量"
    "（暂不 import 生产模块，**由自测钉住两处相等**），§2 把 `2·sd` 标注为「**单设计**读数带，⚠️不是判据带」并"
    "新增判据带、§5 改为**自己用当前规则重算判词**并与转印的判词比对（一致 / 不一致 ⇒ 以复核为准 / 复核失败 ⇒ 明说"
    "「未经复核」三种打印）、§7 的倍数改用新带并新增**选择偏差**段（含 `_scratch_mean_A_rank.py` 的做法）。"
    "④ **新工具**：`1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`（对 CRN 口径前 N 名逐个做种子平均、给出按均值的排名"
    "与每个设计的偏差 σ）、`_scratch_pick_designs.py`（打印锚点 / 推荐点 / 病态样例的设计名）；"
    "`_scratch_anchor_seed_scan.py` 新增第 4 参数（指定设计名、默认锚点）。"
    "⑤ **牙齿**：`check_stage9_loop.py` 新增 `[E 组·续 3]` E11/E11a/E11b/E11c + H8（新带 0.0565685424949238、"
    "`ΔA` 落在两根带之间必须判不可分辨、**放大 1.2 倍仍须允许说「最好」**、两处常量相等、旧写法不得出现）=> **53/53**；"
    "`check_stage9_report.py` 新增 R1p-o/p/q/r/r2（不一致分支 / 一致分支 / 复核失败分支 / 选择偏差段 / 自认「本落盘件的"
    "种子均值没有在本报告里算过」）=> **57/57**。"
    "⑥ **影响**：判词口径变化**不影响任何设计读数**（`(A)/(B)/J` 一个都没动）⇒ 正在跑的两次 `n_fim = 12` 运行仍可用于"
    "可行域构成对照；且报告现在会自己重算判词 ⇒ 不必因「判词过时」重跑。"
    "⑦ **尚未做**：判读 `_scratch_payload_nfim12.json`（`--budget 1 --n-fim 12`）与 "
    "`stage9_payload_nfim12_budget12.json`（`--budget 12 --n-fim 12 --noise-repeats 16`）、把交付件依据件换到 "
    "`n_fim = 12` 的落盘件、`1_Code/DDM_Core/README.md` §9 第 18 项（D55 的遗漏率带与锚点 D4 不相容）仍待拍板 |"
    " `1_Code/AutoRA_SPE/stage9_loop.py` 的 `DIFF_BAND_FACTOR` 与 `compare_arms` 带宽行、`stage9_report.py` §2/§5/§7、"
    "`_scratch_anchor_seed_scan.py` 三份 σ 实测（`_scratch_sigma_anchor_u8.txt` / `_scratch_sigma_best_u8.txt` / "
    "`_scratch_sigma_ill_u8.txt`）、`check_stage9_loop.py` 53/53（`_scratch_check_stage9_loop_d60_u8.txt`）、"
    "`check_stage9_report.py` 57/57 | 判据带宽变 √2 倍 ⇒ `2·sd_A` 从 0.0050 变 0.0071（`n_fim = 1` 那份 payload）；"
    "同一份 `ΔA = 0.0412` 的倍数由 8.18 倍（旧族 `2·sd`）/ 1.09 倍（无关族 `2·sd`）改为 **3.0 倍 / 0.77 倍**（新的 `2·√2·sd`），"
    "结论方向不变（仍不可分辨）；「推荐点比锚点好」在 `n_fim = 1` 下无证据 |"
)

D60_PROGRESS = (
    "| 2026-10-16 | **9**（判据带宽的 √2 缺口 + 推荐点的选择偏差 → D60） | "
    "**核对交付链的最后一环「判据本身对不对」，抓出带宽系数少 √2 与推荐点的选择偏差**。"
    "① ❗ 带宽：`compare_arms` 用单设计的 `2·sd` 判**两个不同设计**的差 ⇒ 应为 `2·√2·sd`（窄了 1.41 倍、偏宽松）；"
    "② ❗ 选择偏差：推荐点是「可行集内 `(A)` 最小」⇒ *winner's curse*，实测其 CRN 读数比自己的种子均值低 "
    "**2.26σ**、锚点高 1.58σ，而 σ 逐设计同量级（0.0180 / 0.0186 / 0.0213 ⇒ 同方差假设可接受）；"
    "③ 报告升级：§5 从「转印判词」改为**自己用当前规则重算**并与转印比对（三种打印），§2 把 `2·sd` 标为单设计带、"
    "§7 加选择偏差段；④ 牙齿：循环自测 48/48 → **53/53**、报告自测 52/52 → **57/57**；"
    "⑤ 新探针 `_scratch_mean_A_rank.py`（种子平均排名）与 `_scratch_pick_designs.py` | "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（**917 行**）、`1_Code/AutoRA_SPE/stage9_report.py`（**494 行**）、"
    "`1_Code/AutoRA_SPE/stage9_report.md`（**145 行**）、`1_Code/AutoRA_SPE/check_stage9_loop.py`（**593 行、53/53**）、"
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（**400 行、57/57**）、"
    "`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`（229 行）、"
    "`1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`（**新**）、`_scratch_pick_designs.py`（**新**） | "
    "**(1)** 判读两次 `n_fim = 12` 长跑并把交付件依据件换过去；**(2)** 用 `_scratch_mean_A_rank.py` 的种子平均排名"
    "回答「推荐点是否真的最好」（`n_fim = 1` 已显示排序可能是抽签结果）；**(3)** 🛑 D55 第 18 项待拍板；"
    "**(4)** 四个用户侧 Stage（1 实机验收 / 6 Pilot / 7 正式采集 / 定稿签批） |"
)

D60_CHANGELOG = (
    "| 2026-10-16 | **新增 D60：跨设计比较的带宽系数少 √2（`2·sd` → `2·√2·sd`，旧的偏宽松 1.41 倍）；"
    "报告的第 5 节必须自己重算判词而不是转印；推荐点自带 *winner's curse*（实测其 CRN 读数比自己的种子均值低 2.26σ，"
    "逐设计 σ 同量级 ⇒ 同方差假设可接受），判断「哪个设计真好」必须做种子平均（`_scratch_mean_A_rank.py`）** |"
)

D60_APPENDIX = (
    "| `1_Code/AutoRA_SPE/stage9_loop.py`（896 → **917 行**） + `1_Code/AutoRA_SPE/stage9_report.py`"
    "（408 → **494 行**） + `1_Code/AutoRA_SPE/stage9_report.md`（133 → **145 行**） + "
    "`1_Code/AutoRA_SPE/check_stage9_loop.py`（536 → **593 行**、**53/53**） + "
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（372 → **400 行**、**57/57**） + "
    "`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py`（支持第 4 参数：指定设计名） + "
    "`1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`（**新建**：种子平均排名） + "
    "`1_Code/AutoRA_SPE/_scratch_pick_designs.py`（**新建**：打印设计名） | 带宽系数 `2·√2` 的推导"
    "（`Var(差) = 2·sd²`）与三条逐设计 σ 实测（`_scratch_sigma_{anchor,best,ill}_u8.txt`）；"
    "「推荐点低 2.26σ / 锚点高 1.58σ」的选择偏差读数 |"
)

D60_CORR = (
    "❌ **2026-10-16 更正（见 D60）**：本行「换带重判」用的两根带子是**单设计**的 `2·sd`"
    "（旧族 0.0050 / 无关族 0.0379）；跨设计比较的正确系数是 `2·√2` ⇒ 同一份 `ΔA = 0.0412` 应读作"
    "**3.0 倍 / 0.77 倍**（而不是 8.18 / 1.09），结论方向不变（都判「不可分辨」）；"
    "另外「推荐点比锚点好」这句话在 `n_fim = 1` 下**没有证据**（推荐点的 CRN 读数比自己的种子均值低 2.26σ，"
    "而锚点高 1.58σ ⇒ 单种子先后可能是抽签）"
)

S9_11_25 = (
    "25. ❗ **判据带宽的系数是 `2·√2`，因为比的是「两个设计」的差（D60）**：`sd_A` 只在**一个设计**"
    "（锚点）上量过，而 `1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 比的是两条臂各自选中的"
    "**不同设计**（CRN 种子由名字哈希导出 ⇒ 独立）⇒ `Var(差) = 2·sd²` ⇒ 带宽 = `2·√2·sd`"
    "（`DIFF_BAND_FACTOR`）。旧写法 `2·sd` **窄 1.41 倍**、偏宽松。配套：`stage9_report.py` §2 必须把"
    "`2·sd` 标注为「单设计读数带、不是判据带」，§7 的「几倍带宽」改用新系数。"
    "**同一节的第二个读数**：推荐点是「可行集内 `(A)` 最小」⇒ *winner's curse*（实测其 CRN 读数比自己的"
    "种子均值低 2.26σ、锚点高 1.58σ，而逐设计 σ 同量级 0.0180 / 0.0186 / 0.0213）⇒ 单种子 CRN 下的"
    "设计排序**可能是抽签结果**；要判「哪个设计真好」必须做种子平均"
    "（`python -u 1_Code/AutoRA_SPE/_scratch_mean_A_rank.py <payload.json> [n_seeds] [n_fim]`）。"
)

S9_12_D60 = (
    "| 2026-10-16 | **判据带宽的 √2 缺口 + 推荐点的选择偏差（决策 D60）**：`compare_arms` 的带宽由"
    "`2·sd` 改为 `2·√2·sd`（`DIFF_BAND_FACTOR`，旧值偏宽松 1.41 倍）；报告 §5 改为**自己用当前规则重算判词**"
    "并与转印比对；报告 §7 新增选择偏差段 | 逐设计 σ 实测（`_scratch_sigma_anchor_u8.txt` 等三份）、"
    "`1_Code/AutoRA_SPE/check_stage9_loop.py` **53/53**（E11/E11a/E11b/E11c + H8）、"
    "`1_Code/AutoRA_SPE/check_stage9_report.py` **57/57**（R1p-o/p/q/r/r2）、"
    "`1_Code/DDM_Core/README.md` §8.35 |"
)

RM_835 = [
    "## 8.35 跨设计比较的带宽系数少 √2；推荐点自带选择偏差（2026-10-16，D60）",
    "",
    "### 1. 为什么有这一节",
    "",
    "`1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 的每一条判词（不可分辨 / 显著更差 / 被支配 /",
    "权衡）都以一根**噪声带**为门槛，而 `(A)` 是 MC 估计量。前几轮（D59、§8.34）已经把带宽的**估计来源**",
    "钉住了（标定种子必须独立重抽），但**系数**本身还有一处错：`sd_A` 是**同一个设计**在不同种子下的",
    "标准差，而判词比的是**两条臂各自选中的不同设计**（CRN 种子由名字哈希导出 ⇒ 独立）⇒",
    "`Var(差) = 2·sd²` ⇒ 系数的正确值是 `2·√2`，而代码里写的是 `2·sd` ⇒ **窄 1.41 倍、方向偏宽松**",
    "（更容易自称显著）。这一处属「**事前登记的判据有缺陷**」，所以作为一次显式决策（D60）落纸，而不是静默改码。",
    "",
    "### 2. 代码改动清单（5 处）",
    "",
    "1. `1_Code/AutoRA_SPE/stage9_loop.py`：新增模块常量 `DIFF_BAND_FACTOR = 2.0 * float(np.sqrt(2.0))`",
    "   （= `2.8284271247461903`，紧跟 `VERDICT_LOGIC` 之后，含推导与两条未解决限制的注释）；",
    "   `compare_arms` 的 `band_a/band_b` 改用它；docstring 新增第 5 条纪律。",
    "2. 同文件：`VERDICT_LOGIC` 文案改为「带宽 = **差**的噪声带 `2·√2·sd`（不是单设计的 `2·sd`）」",
    "   ⇒ 落盘件自报的规则版本随之更新。",
    "3. `1_Code/AutoRA_SPE/stage9_report.py`：同名常量 `DIFF_BAND_FACTOR = 2.0 * math.sqrt(2.0)`",
    "   （**不 import 生产模块**，两处相等由自测钉住）；§2 把 `2·sd` 标注为「**单设计**读数带，⚠️不是判据带」",
    "   并新增判据带一节。",
    "4. 同文件 §5：从「逐字转印落盘件里的判词」改为**自己用当前规则重算一遍**（延迟 `sys.path` 插入后",
    "   `import stage9_loop` 调 `compare_arms`），三种打印：全等 ⇒ `✅ 与上面**转印**的判词逐字一致`；",
    "   不等 ⇒ `⚠️ **与上面转印的判词不一致的臂：…** ⇒ 以本节的复核文本为准`；异常 ⇒",
    "   `⚠️ **离线复核失败**（ExcType: msg）⇒ 上面的判词**未经复核**`（绝不静默）。",
    "5. 同文件 §7：`离最优多远` 的倍数改用 `2·√2·sd_A`；新增**选择偏差**段；→ 共 5 处。",
    "",
    "### 3. 缺陷一：带宽系数少 √2（影响面 = 全部判词）",
    "",
    "| 量 | 代码里的写法 | 正确写法 | 差 |",
    "|---|---|---|---|",
    "| `(A)` 的判据带宽 | `2.0 * sd_A` | `2·√2 · sd_A` | 旧值窄 **1.41 倍**（偏宽松） |",
    "| `(B)` 的判据带宽 | `2.0 * sd_B` | `2·√2 · sd_B` | 同上 |",
    "",
    "`n_fim = 1` 那份 payload（`stage9_payload_nfim1_budget12.json`）的实读：`sd_A = 0.0025152`",
    "（旧标定族）⇒ 旧带 `0.0050`、新带 `0.0071`；`sd_B = 0.1332437` ⇒ 旧带 `0.2665`、新带 `0.3768`。",
    "同一份 `ΔA = 0.041159`（锚点 vs 推荐点）在四种口径下的倍数：旧族 `2·sd` = **8.18 倍**、",
    "无关族 `2·sd` = **1.09 倍**（D59）、旧族 `2·√2·sd` = **3.0 倍**、无关族 `2·√2·sd` = **0.77 倍** ⇒",
    "**换哪一根带子都不构成「推荐点更好」的证据**（这也顺带更正了 §8.34 里「8.18 倍 / 1.09 倍」那两句）。",
    "",
    "### 4. 同族第五处：推荐点自带选择偏差（本轮最要紧的读数）",
    "",
    "判据带宽只解决「一个设计自己的读数有多准」；而报出的**推荐点**是「**可行集内 `(A)` 最小的那个**」",
    "⇒ 它是**极值统计量**，系统性偏低（*winner's curse*）。逐设计实测（`n_fim = 1`、",
    "`_scratch_anchor_seed_scan.py`、32 个无关种子 `default_rng(20261016)`）：",
    "",
    "| 设计 | CRN 读数 `(A)` | 32 个无关种子的均值 | `sd_A` | CRN 的 z |",
    "|---|---|---|---|---|",
    "| 锚点 D4 `T[33.33/83.33/149.99/249.98]ms x W[799.98/1199.90/1799.90]ms x r12` | 0.385802 | 0.357344 | 0.017976 | **+1.58** |",
    "| 推荐点 `T[33.33/149.99/349.99]ms x W[1199.90/1799.90/2399.80]ms x r16` | 0.344643 | 0.386742 | 0.018638 | **−2.26** |",
    "| 病态样例 `T[83.33/149.99/249.98]ms x W[799.98/1799.90]ms x r24` | 0.289613 | 0.318175 | 0.021285 | −1.34 |",
    "",
    "三条读数：",
    "",
    "1. **σ 逐设计同量级**（0.017976 / 0.018638 / 0.021285，最大是最小的 1.18 倍）⇒ 用锚点的 σ 当共同 σ",
    "   **可接受**（只略低估病态设计约 14–18%）；**同方差假设不必推翻**，但要写在报告的限制里。",
    "2. **推荐点的 CRN 读数比它自己的种子均值低 2.26σ**（锚点高 1.58σ）⇒ 单种子 CRN 下的「谁更好」",
    "   **可能是抽签结果**。两设计的种子均值差 `0.386742 − 0.357344 = 0.0294`（均值标准误 ≈ 0.0033，",
    "   约 **9 个标准误**）⇒ 那次按均值比，**锚点反而更优**。这不改 D54 的结论（D4 因遗漏率 0.3611 > 0.20",
    "   仍不可行），但**「推荐点比锚点好」这句话在 `n_fim = 1` 下没有证据**。",
    "3. ⇒ 要判断「哪个设计真的好」，必须做**种子平均**：新增探针",
    "   `python -u 1_Code/AutoRA_SPE/_scratch_mean_A_rank.py <payload.json> [n_seeds] [n_fim]`",
    "   （对 CRN 口径前 N 名逐个扫种子，给出按均值的排名与每个设计的偏差 σ）；",
    "   `_scratch_pick_designs.py` 用来从 payload 里取设计名。",
    "",
    "### 5. 报告的三处新呈现",
    "",
    "1. §2：`2·sd` 表头标注为「**单设计**读数带，⚠️不是判据带」，并单独列出 `2·√2·sd` 的判据带；",
    "2. §5：判词复核（一致 / 不一致 / 复核失败三种打印）——落盘件自报的规则版本只作**线索**，",
    "   结论以复核文本为准；",
    "3. §7：倍数用新带，并明确写出「**推荐点自身带有选择偏差**」与种子平均的做法，",
    "   且**自认**「本落盘件的种子均值没有在本报告里算过」（举例不得当结论）。",
    "",
    "### 6. 校验证据",
    "",
    "1. `python -u 1_Code\\AutoRA_SPE\\check_stage9_loop.py 1 _scratch_check_stage9_loop_d60_u8.txt`",
    "   ⇒ **53/53、未通过 0 项、exit 0、58.2 s**（新增 `[E 组·续 3]` E11/E11a/E11b/E11c + H8）；",
    "2. `python -u 1_Code\\AutoRA_SPE\\check_stage9_report.py` ⇒ **57/57、未通过 0 项、exit 0**",
    "   （新增 R1p-o/p/q/r/r2）；",
    "3. 三份 σ 实测日志：`1_Code/AutoRA_SPE/_scratch_sigma_anchor_u8.txt`（188.1 s）、",
    "   `_scratch_sigma_best_u8.txt`（183.0 s）、`_scratch_sigma_ill_u8.txt`（130.2 s）；",
    "4. `python -u 1_Code\\AutoRA_SPE\\stage9_report.py 1_Code\\AutoRA_SPE\\stage9_payload_nfim1_budget12.json`",
    "   ⇒ 交付件 **145 行**，§5 点出四条臂的判词都与转印的不一致、§7 印出选择偏差段；",
    "5. `python -u 1_Code\\AutoRA_SPE\\check_stage9.py --quick` ⇒ **8 项、未通过 0 项、exit 0**",
    "   （`check_stage9_report.py` 57/57）；",
    "6. `python -u 1_Code\\DDM_Core\\_scratch\\check_files.py` ⇒ 全部裸 LF、无 BOM、`ast=OK`。",
    "",
    "### 7. 尚未做",
    "",
    "1. 判读两次 `n_fim = 12` 长跑（`--budget 1` 与 `--budget 12 --noise-repeats 16`），",
    "   把交付件依据件换到 `n_fim = 12` 的落盘件；",
    "2. 用 `_scratch_mean_A_rank.py` 在 `n_fim = 12` 下重做种子平均排名（`n_fim = 1` 下 7 个设计 × 32 种子",
    "   ≈ 13 min；`n_fim = 12` 约 ×6）⇒ 用**期望意义上的** `(A)` 重排可行集；",
    "3. `(B)` 一侧的选择偏差没有单独量（`B = |mu−1|/se_group` 含 `n_subjects` 折算，σ 与 `(A)` 不同源）。",
    "",
]

RM_ITEM44 = (
    "| 44 | ✅ **跨设计比较的带宽系数是 `2·√2`（差的口径），且推荐点自带选择偏差（D60，§8.35）** | "
    "旧写法用**单设计**的 `2·sd` 判两个不同设计的差 ⇒ 窄 1.41 倍；逐设计 σ 实测（`n_fim = 1`、32 个无关种子）"
    "0.017976 / 0.018638 / 0.021285 ⇒ 同方差假设可接受；推荐点的 CRN 读数比自己的种子均值低 **2.26σ**、锚点高 1.58σ "
    "⇒ 单种子 CRN 排序可能是抽签结果；报告 §5 改为**自己重算判词**并与转印比对（新增 R1p-o/p/q/r/r2）；"
    "新探针 `1_Code/AutoRA_SPE/_scratch_mean_A_rank.py`（种子平均排名） |"
)


def do_master_plan() -> None:
    text = load(MP)
    if "| **D60** | 2026-10-16 |" in text:
        print(f"[跳过] {MP.name}：D60 已落纸")
        return
    lines = text.splitlines()
    ins_after(lines, "| **D59** | 2026-10-16 |", [D60_ROW], "主计划 §5 决策行 D60")
    ins_after(lines, "| 2026-10-16 | **9**（判据带宽的标定种子 + 裁决短路 → D59） |",
              [D60_PROGRESS], "主计划 §6 进度行 D60")
    ins_after(lines, "| 2026-10-16 | **新增 D59：", [D60_CHANGELOG], "主计划 §7 变更日志 D60")
    ins_after(lines, "| `1_Code/AutoRA_SPE/stage9_loop.py`（831 → **896 行**）",
              [D60_APPENDIX], "主计划 §8 附录证据 D60")
    for pref in ("| **D59** | 2026-10-16 |",
                 "| 2026-10-16 | **9**（判据带宽的标定种子 + 裁决短路 → D59） |",
                 "| 2026-10-16 | **新增 D59："):
        append_in_row(lines, pref, D60_CORR, f"D59 行就地更正（{pref[:34]}…）", guard="见 D60")
    save(MP, "\n".join(lines) + "\n")


def do_stage9() -> None:
    text = load(S9)
    if "（决策 D60）" in text:
        print(f"[跳过] {S9.name}：D60 已落纸")
        return
    lines = text.splitlines()
    P_LOOP = "| `1_Code/AutoRA_SPE/stage9_loop.py` | CRN 预计算表"
    P_CHK = "| `1_Code/AutoRA_SPE/check_stage9_loop.py` | 优化循环自测"
    P_MD = "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告"
    P_GEN = "| `1_Code/AutoRA_SPE/stage9_report.py` | 落盘报告生成器"
    P_CG = "| `1_Code/AutoRA_SPE/check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, P_LOOP, "**896 行**", "**917 行**", "Stage9 §9：stage9_loop 896 → 917")
    patch_row(lines, P_LOOP, "D59 前为 831 行", "D59 前为 831 行、D60 前为 896 行",
              "Stage9 §9：stage9_loop 行数沿革")
    append_in_row(lines, P_LOOP, "D60 起判据带宽 = `2·√2·sd`（`DIFF_BAND_FACTOR`）",
                  "Stage9 §9：stage9_loop 的 D60 注记")
    patch_row(lines, P_CHK, "**536 行**", "**593 行**", "Stage9 §9：check_stage9_loop 536 → 593")
    patch_row(lines, P_CHK, "**48/48 通过、exit 0、47.8 s**", "**53/53 通过、exit 0、58.2 s**",
              "Stage9 §9：check_stage9_loop 的项数与耗时")
    patch_row(lines, P_CHK, "D59 前为 465 行", "D59 前为 465 行、D60 前为 536 行",
              "Stage9 §9：check_stage9_loop 行数沿革")
    append_in_row(lines, P_CHK, "D60 新增 `[E 组·续 3]`（E11/E11a/E11b/E11c）+ H8：判据带宽必须是 `2·√2·sd`",
                  "Stage9 §9：check_stage9_loop 的 D60 注记")
    patch_row(lines, P_MD, "**133 行**", "**145 行**", "Stage9 §9：stage9_report.md 133 → 145")
    append_in_row(lines, P_MD, "D60 起 §2 把 `2·sd` 标为「单设计读数带、不是判据带」并**单列判据带** `2·√2·sd`、"
                               "§5 **自己重算判词**并与转印比对、§7 改用新带并新增选择偏差段",
                  "Stage9 §9：stage9_report.md 的 D60 注记")
    patch_row(lines, P_GEN, "**408 行**", "**494 行**", "Stage9 §9：stage9_report.py 408 → 494")
    append_in_row(lines, P_GEN,
                  "D60 起 §2 把 `2·sd` 标为「单设计读数带、不是判据带」并单列判据带、§5 **自己重算判词**"
                  "并与转印比对（一致 / 不一致 / 复核失败三种打印）、§7 改用 `2·√2·sd_A` 并新增选择偏差段",
                  "Stage9 §9：stage9_report.py 的 D60 注记")
    patch_row(lines, P_CG, "**372 行**", "**400 行**", "Stage9 §9：check_stage9_report 372 → 400")
    patch_row(lines, P_CG, "**52/52 通过、exit 0**", "**57/57 通过、exit 0**",
              "Stage9 §9：check_stage9_report 52/52 → 57/57")
    append_in_row(lines, P_CG, "D60 新增 R1p-o/p/q/r/r2（判词不一致 / 一致 / 复核失败 / 选择偏差 / 自认未算种子均值）",
                  "Stage9 §9：check_stage9_report 的 D60 注记")
    ins_after(lines, "24. ❗ **判据带宽自己也有不确定度", [S9_11_25], "Stage9 §11 第 25 条（D60）")
    ins_after(lines, "| 2026-10-16 | **判据带宽的标定种子与裁决短路（决策 D59）**", [S9_12_D60],
              "Stage9 §12 D60 行")
    append_text(lines, "24. ❗ **判据带宽自己也有不确定度",
                "❌ **2026-10-16 更正（见 D60）**：本条的「换带」按**单设计**的 `2·sd` 算；跨设计的差应"
                "用 `2·√2·sd` ⇒ 8.18 / 1.09 倍改为 **3.0 / 0.77 倍**，结论方向不变",
                "Stage9 §11 第 24 条就地更正", guard="见 D60")
    append_in_row(lines, "| 2026-10-16 | **判据带宽的标定种子与裁决短路（决策 D59）**",
                  "❌ **2026-10-16 更正（见 D60）**：本条的两根带子按**单设计** `2·sd` 计；跨设计比较应乘 "
                  "`√2`（`DIFF_BAND_FACTOR`）", "Stage9 §12 D59 行就地更正", guard="见 D60")
    save(S9, "\n".join(lines) + "\n")


def do_autora_readme() -> None:
    text = load(RA)
    if "D60 起判据带宽" in text:
        print(f"[跳过] {RA.name}：D60 已落纸")
        return
    lines = text.splitlines()
    # ⚠️ 前缀**不得含被替换的数字**：先 `patch_row` 把 896 改成 917 之后，含 896 的前缀就再也匹配不上
    #    （D59b 那轮踩过同一个坑：前缀必须对漂移免疫）。
    P_LOOP = "| `stage9_loop.py` | **优化循环**"
    P_CHK = "| `check_stage9_loop.py` | 循环自测"
    P_GEN = "| `stage9_report.py` | **Stage 9 落盘报告生成器**"
    P_CG = "| `check_stage9_report.py` | 报告生成器自测"
    patch_row(lines, P_LOOP, "**896 行**", "**917 行**", "AutoRA README §7：stage9_loop 896 → 917")
    append_in_row(lines, P_LOOP, "D60 起判据带宽 = `2·√2·sd`（`DIFF_BAND_FACTOR`，旧值偏宽松 1.41 倍）",
                  "AutoRA README §7：stage9_loop 的 D60 注记")
    patch_row(lines, P_CHK, "**48/48**", "**53/53**", "AutoRA README §7：check_stage9_loop 48/48 → 53/53")
    append_in_row(lines, P_CHK, "D60 新增 E11/E11a/E11b/E11c + H8（带宽必须是 `2·√2·sd`）",
                  "AutoRA README §7：check_stage9_loop 的 D60 注记")
    patch_row(lines, P_GEN, "**408 行**", "**494 行**", "AutoRA README §7：stage9_report.py 408 → 494")
    append_in_row(lines, P_GEN, "D60 起 §5 **自己重算判词**并与转印比对、§7 新增选择偏差段",
                  "AutoRA README §7：stage9_report.py 的 D60 注记")
    patch_row(lines, P_CG, "**372 行、52/52", "**400 行、57/57", "AutoRA README §7：check_stage9_report")
    append_in_row(lines, P_CG, "D60 新增 R1p-o/p/q/r/r2", "AutoRA README §7：check_stage9_report 的 D60 注记")
    save(RA, "\n".join(lines) + "\n")


def do_ddm_readme() -> None:
    text = load(RM)
    if "## 8.35 " in text:
        print(f"[跳过] {RM.name}：D60 已落纸")
        return
    lines = text.splitlines()
    ins_before(lines, "## 9. 尚未做", RM_835, "DDM README §8.35")
    ins_after(lines, "| 43 | ✅ **判据带宽的标定种子必须独立重抽", [RM_ITEM44], "DDM README §9 第 44 项")
    # §8.34 里「8.18 倍 / 1.09 倍」那两句是**散文段落**（不是表格行）⇒ 只能在段落**之后**插一行更正
    # （先用 append_in_row 会被「行末必须是闭合竖线」的断言拦住 —— 这正是那条约束存在的意义）。
    ins_after(lines, "在诚实带下只有 **1.09 倍**", [D60_CORR], "DDM README §8.34 段落更正（D60）")
    save(RM, "\n".join(lines) + "\n")


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
