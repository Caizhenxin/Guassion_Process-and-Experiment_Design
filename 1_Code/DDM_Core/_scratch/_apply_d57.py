# -*- coding: utf-8 -*-
"""D57 落纸：无人可行点的臂不得与有可行点的臂同台排序 + 报告必须由落盘件生成。

跨四个文件工作，体例与 `_apply_d47`–`_apply_d56c` 相同：
  · 前缀定位（命中次数必须为 1）
  · 分隔符（竖线）数断言：新行的竖线数必须与锚点行**逐字相等**（否则表格列数被破坏）
  · 幂等守卫：已落纸则跳过（不重复插入）
  · 就地更正只用「子串替换 + 命中次数断言」，绝不触碰空行
  · 输出必须以换行结尾

用法：
  python -u 1_Code/DDM_Core/_scratch/_apply_d57.py            # 干跑（只打印计划与断言）
  python -u 1_Code/DDM_Core/_scratch/_apply_d57.py --apply     # 真写
"""
import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
S9 = ROOT / "5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md"
RA = ROOT / "1_Code/AutoRA_SPE/README.md"
RM = ROOT / "1_Code/DDM_Core/README.md"

APPLY = "--apply" in sys.argv


# ---------------------------------------------------------------- 基础设施
def find_line(ls, prefix, what):
    hits = [i for i, l in enumerate(ls) if l.startswith(prefix)]
    assert len(hits) == 1, f"❌ {what}：前缀 {prefix!r} 命中 {len(hits)} 行（应为 1）"
    return hits[0]


def ins_after(text, prefix, new_lines, what, guard=None):
    """在 `prefix` 开头的那一行**之后**插入 `new_lines`（不触碰其它任何行）。"""
    if guard and guard in text:
        print(f"  · 幂等跳过：{what}")
        return text
    ls = text.split("\n")
    i = find_line(ls, prefix, what)
    ref = ls[i].count("|")
    for ln in new_lines:
        assert ln.count("|") == ref, (
            f"❌ {what}：锚点 {ref} 个竖线、新行 {ln.count('|')} 个 ⇒ 列数会被破坏")
    print(f"  · 插入 {len(new_lines)} 行 → {what}（锚点 L{i + 1}，{ref} 个竖线）")
    ls[i + 1:i + 1] = new_lines
    return "\n".join(ls)


def ins_before(text, prefix, new_lines, what, guard=None):
    """在 `prefix` 开头的那一行**之前**插入 `new_lines`。"""
    if guard and guard in text:
        print(f"  · 幂等跳过：{what}")
        return text
    ls = text.split("\n")
    i = find_line(ls, prefix, what)
    print(f"  · 插入 {len(new_lines)} 行 → {what}（锚点 L{i + 1} 之前）")
    ls[i:i] = new_lines
    return "\n".join(ls)


def patch(text, old, new, what, expect=1, guard=None):
    """子串替换 + 命中次数断言（`guard` 命中视为已落纸 ⇒ 跳过）。"""
    if guard and guard in text:
        print(f"  · 幂等跳过：{what}")
        return text
    n = text.count(old)
    assert n == expect, f"❌ {what}：旧串命中 {n} 次（应为 {expect}）\n   {old[:90]!r}"
    print(f"  · 就地更正：{what}（命中 {n} 次）")
    return text.replace(old, new)


def add_tail(line, text):
    """把 `text` 追加到表格行的**最后一格内**（闭合竖线之前）。"""
    body = line.rstrip()
    assert body.endswith("|"), "❌ 只处理以闭合竖线结尾的表格行"
    return body[:-1].rstrip() + " " + text + " |"


def patch_row(text, prefix, tail, what, guard=None):
    """按前缀定位表格行，把 `tail` 追加到该行最后一格（竖线数不变）。"""
    if guard and guard in text:
        print(f"  · 幂等跳过：{what}")
        return text
    ls = text.split("\n")
    i = find_line(ls, prefix, what)
    before = ls[i].count("|")
    ls[i] = add_tail(ls[i], tail)
    assert ls[i].count("|") == before, f"❌ {what}：竖线数被改变"
    print(f"  · 行末追加 → {what}（L{i + 1}）")
    return "\n".join(ls)


# ---------------------------------------------------------------- 内容
D57_DECISION = (
    "| **D57** | 2026-10-14 | ✅ **没有可行点的臂不得与有可行点的臂同台排序；Stage 9 的落盘报告必须由落盘件生成**。"
    "① **缺陷**：`1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 在「某臂 `A_best = inf`」（该臂在本预算内一个可行点都没抽到）时算出 "
    "`gap = second[\"A_best\"] - top[\"A_best\"] = inf`、`d_b_top = top.B - nan = nan` ⇒ 「差 ≤ 噪声带」与「被支配」两个判据**都为假** ⇒ "
    "落 else 分支，把 `--budget 2` 的冒烟印成「本预算下 (A,B) 上最好（比次好臂 `random` 的 A 小 inf > 噪声带 0.0050）」——**把「没有数据」说成「大幅领先」**，"
    "与本文件反复要防的裁决洗白同族。② **修法**：逐臂记 `has_feasible_point = bool(np.isfinite(A_best))`，三分支改判 —— (i) 全臂无可行点 ⇒ "
    "「没有任何一条臂在可行集内取到设计 ⇒ 无对照、无排序证据（这**不是**「谁更差」，是**没有数据**）」；(ii) 该臂无点 ⇒ 「可行集内没有任何设计（`A = ∞`）⇒ 不参与排序」"
    "并提示须看 `picked` 以区分「预算不足」与「该臂确实偏向不可行区」；(iii) 头名无对照（其余臂都无点）⇒ 「只有它一条臂取到设计 ⇒ 无对照、不构成排序证据，不得写成『最好』」；"
    "有真对照时三条裁决末尾一律追加「（另有 N 条臂在本预算内没有可行点）」。`main()` 的打印改为非有限值一律印 `—`（印 `inf` 会被读成极好或极差，两种读法都错）。"
    "③ **牙齿**：`check_stage9_loop.py` 新增 **E8/E8b/E8c/E8d**（1 有 + 3 无 ⇒ 头名不得写「本预算下 (A,B) 上最好」且须说「只有它一条臂」「无对照」；`inf` 臂须说「不参与排序」"
    "且 `has_feasible_point is False`；四臂全无 ⇒ 每条都须说「没有任何一条臂」「没有数据」；回归件 = 真对照时仍须写「(A,B) 上最好」**并**注明「另有 2 条臂没有可行点」）"
    "⇒ `check_stage9_loop.py` 374 → **423 行、36/36、exit 0、39.1 s**。④ **同族的第二处缺陷（键名分叉）**：同一个量在 `run_arms` 的 `histories[arm]` 里叫 `B_at_best_A`、"
    "在 `compare_arms` 造的行里叫 `B_at_A_best` ⇒ 报告生成器读错键就把「`B`@`(A)` 最优点」整列**静默印成 `—`**（`_f()` 把缺失/`inf`/`nan` 都折成 `—`，读者会当成「没数据」）；"
    "已统一为 `B_at_A_best` 并新增 **H4** 静态判据（`B_at_A_best` 出现 8 次、旧名 0 次）。⑤ **交付件**：`stage9_report.py`（**323 行**）读落盘件生成 `stage9_report.md`（**124 行**）+ "
    "`check_stage9_report.py`（**286 行、40/40**）；报告把「运行设置与作用域」印在第 1 节（`n_evaluated == n_candidates` 打 ✅ 否则打 ⚠️「前沿/推荐点只覆盖了一部分候选空间」）、"
    "表格单元里 `inf`/`nan` 一律 `—`、`(A)` 必须连 `n_fim` 一起报。⑥ **实测**（`--budget 12 --n-fim 1 --noise-repeats 2 --seed 0`，落盘件 `stage9_payload_nfim1_budget12.json`，"
    "346512 字节、`n_evals = 176`、内环 541.4 s、`n_evaluated = n_candidates = 174`）：**四臂全部取到可行点** ⇒ `random A_best = 0.3881`（与 `grid 0.3897` **不可分辨**，ΔA 0.0016 ≤ 0.0050）"
    "、`manual 0.3989`（ΔA 0.0108 > 0.0050 且 ΔB −0.8885 < −0.2665 ⇒ **被 random 支配**）、`bo 0.5113`（ΔA 0.1232 = 32% ⇒ **在 (A) 上显著更差**，B 分量不可分辨）；"
    "推荐点 `A = 0.3446 / B = 8.6729 / 遗漏 0.191`；锚点 D4 `ΔA = 0.0412`（被 5 个可行设计支配） | "
    "① `1_Code/AutoRA_SPE/_scratch_check_stage9_loop_d57c_u8.txt`（36/36、39.1 s）；② `1_Code/AutoRA_SPE/_scratch_check_stage9_report_u8.txt`（40/40）；"
    "③ `1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`（346512 字节）→ `1_Code/AutoRA_SPE/stage9_report.md`（124 行）；"
    "④ `1_Code/DDM_Core/README.md` §8.32 与 §9 第 41 项；⑤ `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9/§11 第 21 条/§12 | "
    "① 任何「谁最好」的句子必须先问「它有没有取到可行点、有几条臂取到了」；② 报告必须由落盘件生成 —— 手写报告必然出现「数字来自上一次运行而口径已经变了」；"
    "③ `inf`/`nan` 不得进表格与结论，一律印 `—`；④ `(A)` 的绝对值必须连 `n_fim` 一起报；⑤ 9A 的头条结论不变（D4 既不可行、也被 5 个可行设计支配） |"
)

D57_PROGRESS = (
    "| 2026-10-14 | **9**（无人可行点混排 + 落盘报告 → D57） | "
    "**修掉「没有可行点的臂被印成大幅领先」，并交出 Stage 9 最后一件交付：由落盘件生成的报告**。"
    "① **缺陷**：`compare_arms` 在 `A_best = inf` 时 `gap = inf`、`ΔB = nan` ⇒ 两个判据都为假 ⇒ 落 else ⇒ 印「本预算下 (A,B) 上最好」（`--budget 2` 冒烟实测）；"
    "② **修法**：`has_feasible_point` + 三分支（全无 / 本臂无 / 头名无对照）+ 有对照时追加「另有 N 条臂没有可行点」；`main()` 非有限值印 `—`；"
    "③ **同族第二处**：`histories[arm].B_at_best_A` 与 `compare[i].B_at_A_best` 键名分叉 ⇒ 报告把「`B`@`(A)` 最优点」整列**静默印成 `—`**；已统一并用 H4 钉住（8 次 / 旧名 0 次）；"
    "④ **交付件**：`1_Code/AutoRA_SPE/stage9_report.py`（323 行）+ `1_Code/AutoRA_SPE/stage9_report.md`（124 行）+ `1_Code/AutoRA_SPE/check_stage9_report.py`（286 行、40/40）；"
    "⑤ **实测**（`--budget 12` 全空间、`n_evals = 176`、内环 541.4 s、`n_evaluated = 174 = n_candidates`）：四臂全部取到可行点 ⇒ `random 0.3881`（与 `grid 0.3897` 不可分辨）"
    "｜`manual 0.3989`（被 random 支配）｜`bo 0.5113`（(A) 上显著更差 32%）；推荐点 `A = 0.3446 / B = 8.6729 / 遗漏 0.191`；锚点 D4 `ΔA = 0.0412` 被 5 个可行设计支配 | "
    "`1_Code/AutoRA_SPE/_scratch_check_stage9_loop_d57c_u8.txt`（36/36）、`1_Code/AutoRA_SPE/_scratch_check_stage9_report_u8.txt`（40/40）、"
    "`1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`（346512 字节）、`1_Code/AutoRA_SPE/stage9_report.md`（124 行）、`1_Code/AutoRA_SPE/check_stage9.py`（193 行、七个文件、S1–S5） | "
    "✅ **本轮完成**（四件全部落地并各有实测证据）。🔨 **仍开放**：**(1)** 🛑 遗漏率带 `[0.05, 0.20]` 与锚点 D4 不相容 —— 三选一（报出来 / 重冻结 / D4 只作锚点），"
    "**须用户或导师拍板**（D55 第 18 条，未变）；**(2)** 正式 `n_fim` 下重测可行域构成（`n_fim = 1` 下 174 个候选里 123 个被数值条件数刷掉）；"
    "**(3)** `1_Code/DDM_Core/README.md` §9 第 19 项的 `cellmean.py` 剖面诊断要等真实数据 |"
)

D57_CHANGELOG = (
    "| 2026-10-14 | **新增 D57：没有可行点的臂不得与有可行点的臂同台排序（`A_best = inf` 时旧码把「没有数据」印成「大幅领先」）；"
    "Stage 9 的落盘报告必须由落盘件生成（`stage9_report.py` → `stage9_report.md`）；同一量一个键名（`B_at_A_best`）** |"
)

D57_APPENDIX = (
    "| `1_Code/AutoRA_SPE/stage9_loop.py`（787 → **821 行**） + `1_Code/AutoRA_SPE/check_stage9_loop.py`（374 → **423 行**、36/36） + "
    "`1_Code/AutoRA_SPE/stage9_report.py`（**新建**，323 行） + `1_Code/AutoRA_SPE/stage9_report.md`（**新建**，124 行） + "
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（**新建**，286 行、40/40） | "
    "**D57**：`compare_arms` 的 `inf` 臂不再参与排序（`has_feasible_point` 三分支 + `main()` 印 `—`），新增 E8 四条牙齿与 H4 静态判据，"
    "键名统一为 `B_at_A_best`；交付由落盘件生成的八节报告（作用域 ✅/⚠️、`inf` 一律 `—`、`(A)` 连 `n_fim` 报、含「D4 离最优多远」） |"
)

S9_LOOP_TAIL = (
    "❗ **D57**：`compare_arms` 在 `A_best = inf`（该臂在本预算内没抽到可行点）时**不再参与排序** —— 新增 `has_feasible_point` 与三分支"
    "（全臂无点 ⇒「没有任何一条臂…没有数据」；该臂无点 ⇒「不参与排序」；头名无对照 ⇒「只有它一条臂…不得写成『最好』」），有真对照时每条裁决末尾追加"
    "「另有 N 条臂在本预算内没有可行点」；`main()` 非有限值一律印 `—`。另：`histories[arm]` 的键名 `B_at_best_A` → **`B_at_A_best`**（与 `compare_arms` 同名，"
    "否则报告把「`B`@`(A)` 最优点」整列静默印成 `—`；H4 钉住：8 次 / 旧名 0 次）。787 → **821 行**"
)

S9_REPORT_ROW = (
    "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告 | ✅ **已建**（**124 行**；由 `1_Code/AutoRA_SPE/stage9_report.py` 从落盘件 "
    "`1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`（346512 字节）生成，报告头写该 payload 的路径/字节数/`sha256[:16]`）。**八节**："
    "1 运行设置与作用域（`n_evaluated == n_candidates` ⇒ ✅ 否则 ⚠️「前沿/推荐点只覆盖了一部分候选空间」）/ 2 噪声标定（逐次读数 + `2·sd`）/ "
    "3 可行域构成（三类；作用域不全时必须标注「不是全空间真值」）/ 4 四路曲线 / 5 四臂裁决（`inf` 一律印 `—`）/ 6 Pareto 前沿 / "
    "7 推荐点与「D4 离最优多远」（`ΔA / (2·sd_A)` 倍数 + 从 `cache` 现算支配锚点的**可行**设计个数与最强者）/ 8 本次运行的四条局限 |"
)

S9_REPORTGEN_ROW = (
    "| `1_Code/AutoRA_SPE/stage9_report.py` | 落盘报告生成器（`build(payload_path: Path) -> str`） | ✅ **已建**（**323 行**、裸 LF）。"
    "CLI `python stage9_report.py <payload.json> [输出 .md 路径]`（默认 `_HERE / \"stage9_report.md\"`；无参 ⇒ 用法 + exit 2）。"
    "`_f(v, nd=4)` 把 `inf`/`nan`/缺失/非数一律印成 `—`；`_dominates(a, b, tol=1e-12)`；`_composition(cache)` 按闸门分 "
    "`feasible` / `band_only` / `ill_cond` / `band_and_ill` / `other`。**报告必须由落盘件生成**（手写报告必然出现「数字来自上一次运行而口径已变」）"
    "；`anchor` 段只带 `name/A/B/J/feasible` ⇒ 锚点的遗漏率与闸门文本必须去 `cache[anchor[\"name\"]]` 取 |"
)

S9_REPORTCHK_ROW = (
    "| `1_Code/AutoRA_SPE/check_stage9_report.py` | 报告生成器自测（R1–R5 五组） | ✅ **已建**（**286 行**、裸 LF）。**40/40 通过、exit 0**"
    "（日志 `1_Code/AutoRA_SPE/_scratch_check_stage9_report_u8.txt`）。R1a–k 真实落盘件端到端（可生成、作用域 ✅、不得打 ⚠️、表格单元无 `inf`/`nan`、"
    "头部含 payload 的 `sha256` 前缀、推荐点 == `cache` 现算的可行集 `(A)` 最小点、支配锚点的**可行**设计个数 == 现算 5 个、锚点遗漏率与闸门文本印出、"
    "四臂都有可行点时**不得**出现旧版措辞告警、第 5 节 `B`@同一点列必须印真值）；R1p-a…g 用**合成 payload** 覆盖同一路径（不依赖一次性落盘件）；"
    "R2a–h `_f`/`_dominates` 单元；R3a–d 作用域不全 ⇒ ⚠️ 且不得打 ✅；R4a–g `inf` 臂（verdict 原样带出、旧版措辞告警出现、单元仍 `—`、两次生成完全相同）；"
    "R5a–c CLI（退出码 0、写出内容 == `build()`、无参 exit 2）。⚠️ 两个坑：表格行必须**先切节**再找（同一臂名在第 4/5 节都是表格行）；"
    "自测里调私有函数必须写 `R._f(...)` |"
)

S9_11_21 = (
    "21. ❗ **裁决与报告的呈现纪律（D57）**：**(a)** 任何「谁最好」的句子必须先问「它有没有取到**可行**点、有几条臂取到了」——"
    "`A_best = inf` 的臂**不参与排序**，而且「臂没有取到可行点」**不是**「这条臂比谁更差」的证据（要区分「预算不足」与「该臂偏向不可行区」，"
    "得看它的 `picked` 里有多少点被 D54 带判为不可行）；**(b)** 表格与结论里 `inf`/`nan` 一律印 `—`（印 `inf` 会被读成极好或极差，两种读法都错）；"
    "**(c)** 报告**必须由落盘件生成**并写明 payload 的 `sha256` 前缀与作用域（`n_evaluated == n_candidates`），"
    "因为手写报告必然出现「数字来自上一次运行而口径已经变了」；**(d)** `(A)` 的绝对值必须连 `n_fim` 一起报；**(e)** 同一个量只能有一个键名（D57 的 H4）。"
)

S9_12_D57 = (
    "| 2026-10-14 | **无人可行点的臂不得混排 + 报告必须由落盘件生成（决策 D57）**：`stage9_loop.py` 787 → **821 行**（`compare_arms` 的 `has_feasible_point` 三分支、"
    "`main()` 非有限值印 `—`、键名统一 `B_at_A_best`）；`check_stage9_loop.py` 374 → **423 行**、31 → **36/36、exit 0、39.1 s**（新增 E8/E8b/E8c/E8d + H4）；"
    "新建 `1_Code/AutoRA_SPE/stage9_report.py`（323 行）、`1_Code/AutoRA_SPE/stage9_report.md`（124 行，由落盘件生成）、`1_Code/AutoRA_SPE/check_stage9_report.py`"
    "（286 行、**40/40**）；`check_stage9.py` 185 → **193 行**并把登记文件由五个改**七个**、子自测 S1–S4 → **S1–S5**；§9 该三行 🔨 → ✅ 并新增两行；§11 新增第 21 条"
    " | `1_Code/AutoRA_SPE/_scratch_check_stage9_loop_d57c_u8.txt`、`1_Code/AutoRA_SPE/_scratch_check_stage9_report_u8.txt`、"
    "`1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`（346512 字节）、`1_Code/AutoRA_SPE/stage9_report.md`；主计划 D57；`1_Code/DDM_Core/README.md` §8.32、§9 第 41 项 |"
)

RA_LOOP_TAIL = (
    "❗ **D57**：`compare_arms` 在 `A_best = inf` 时**不再参与排序**（`has_feasible_point` + 三分支；旧码会把「没有数据」印成「大幅领先」），"
    "`main()` 非有限值印 `—`；键名 `B_at_best_A` → **`B_at_A_best`**"
)

RA_LOOPCHK_TAIL = (
    "❗ **D57** 新增 **E8 组**（1 有 + 3 无 ⇒ 头名不得写「最好」；`inf` 臂 ⇒「不参与排序」；四臂全无 ⇒「没有数据」；回归件 = 真对照时仍写「(A,B) 上最好」并注明几条臂无点）"
    "与 **H4**（同一量只能有一个键名）⇒ **423 行、36/36、exit 0、39.1 s**"
)

RA_AGG_TAIL = (
    "❗ **D57**：`STAGE9_FILES` 由五个改**七个**（新增 `stage9_report.py`、`check_stage9_report.py`），新增 **S5**（报告生成器自测，`quick` 与全套**都跑**，"
    "因为它是交付件的唯一守卫）⇒ **193 行**、`--quick` 跑 W 组 5/5"
)

RA_NEW_ROWS = [
    "| `stage9_report.py` | **Stage 9 落盘报告生成器**（**323 行**）：`build(payload_path) -> str` + CLI；头部写 payload 的路径/字节数/`sha256[:16]`；"
    "`_f()` 把 `inf`/`nan`/缺失一律印 `—`；八节（运行设置与作用域 / 噪声标定 / 可行域构成 / 四路曲线 / 四臂裁决 / Pareto 前沿 / 推荐点与「D4 离最优多远」/ 四条局限）。"
    "**报告必须由落盘件生成**，不得手写 |",
    "| `check_stage9_report.py` | 报告生成器自测（R1–R5 五组，**286 行、40/40、exit 0**）：真实落盘件端到端 + 合成 payload 覆盖同一路径 + `_f`/`_dominates` 单元 + "
    "作用域 ⚠️ 分支 + `inf` 臂渲染 + CLI 退出码 |",
    "| `stage9_report.md` | **落盘报告**（**124 行**，由 `stage9_report.py` 从 `stage9_payload_nfim1_budget12.json`（346512 字节）生成）："
    "含 payload 哈希、预算与作用域、四路曲线、四臂裁决、Pareto 前沿、「D4 离最优多远」 |",
]

RM_832 = [
    "## 8.32 没有可行点的臂不得与有可行点的臂同台排序；报告必须由落盘件生成（2026-10-14，D57）",
    "",
    "### 1. 为何有这一节",
    "",
    "上一节（§8.31）修的是「前沿只覆盖抽样点」。这一节修的是同一个虚荣心的另一个出口：**当一条臂在本预算内一个可行点都没抽到时，`A_best = inf`**。"
    "旧码在这个输入上算 `gap = second[\"A_best\"] - top[\"A_best\"] = inf`、`d_b_top = top.B - nan = nan`，"
    "于是「差 ≤ 噪声带」与「被支配」两个判据**都为假** ⇒ 落 else 分支 ⇒ 把 `--budget 2` 的冒烟输出印成",
    "",
    "> 本预算下 (A,B) 上最好（比次好臂 `random` 的 A 小 inf > 噪声带 0.0050）",
    "",
    "**「没有数据」被印成了「大幅领先」。** 这与 §8.30 记录的那次洗白（把「A 差 32%」印成「不可分辨」）是同一族："
    "**判据只在它真正测量到的范围内成立，而「测量不到」必须被显式命名。**",
    "",
    "### 2. 代码改动清单（`1_Code/AutoRA_SPE/stage9_loop.py`，787 → 821 行）",
    "",
    "1. `compare_arms(histories, noise)`：排完序后逐臂 `r[\"has_feasible_point\"] = bool(np.isfinite(r[\"A_best\"]))`；"
    "`with_pt = [r for r in rows if r[\"has_feasible_point\"]]`、`top = with_pt[0] if with_pt else None`、`n_no_pt = len(rows) - len(with_pt)`。",
    "2. 三分支改判：(i) `top is None` ⇒ 没有任何一条臂取到可行点 ⇒ **无对照、无排序证据**；"
    "(ii) 该臂无点 ⇒ 「可行集内没有任何设计（`A = ∞`）⇒ 不参与排序」+ 提示看 `picked` 以区分「预算不足」与「该臂偏向不可行区」；"
    "(iii) `rest` 空（头名无对照）⇒ 「只有它一条臂取到设计 ⇒ 不得写成『最好』」；有真对照时按原 D54 三分支，并在三条裁决末尾追加「（另有 N 条臂在本预算内没有可行点）」。",
    "3. `main()` 的臂表与摘要：`a_s = f\"{r['A_best']:.4f}\" if np.isfinite(r[\"A_best\"]) else \"—\"`（`b_s` / `j_s` 同理）⇒ 不再印 `inf` / `nan`。",
    "4. 键名统一：`run_arms` 的 `histories[arm]` 里 `B_at_best_A` → **`B_at_A_best`**（与 `compare_arms` 造的行同名）。",
    "",
    "### 3. 同一族的第二处缺陷：一个量两个键名（静默印 `—`）",
    "",
    "「`B`@`(A)` 最优点」这个量在 `run_arms` 的历史字典里叫 `B_at_best_A`，在 `compare_arms` 的行里叫 `B_at_A_best`。"
    "报告生成器的第 5 节读的是 `compare` 行 —— 但只要读错一个键，`_f()` 就会把整列**印成 `—`**，而 `—` 恰好也是「这个量是 `inf`/`nan`」的合法呈现 ⇒ "
    "**错误看起来与诚实的数据缺失一模一样**。这正是 §8.31 那条教训的翻版：**呈现层的默认值不能兼任错误信号。**",
    "",
    "修法 = 统一为 `B_at_A_best` + 新增 **H4** 静态判据（`1_Code/AutoRA_SPE/check_stage9_loop.py`）：`'\"B_at_best_A\"' not in 源码` 且 `源码.count('\"B_at_A_best\"') >= 3`"
    "（实测 **8 次** / 旧名 **0 次**）。",
    "",
    "### 4. 交付件：由落盘件生成的报告",
    "",
    "`1_Code/AutoRA_SPE/stage9_report.py`（323 行）读 payload 生成 `1_Code/AutoRA_SPE/stage9_report.md`（124 行）："
    "头部写 payload 路径、字节数与 `sha256(raw)[:16]`；**八节** = 运行设置与作用域（`n_evaluated == n_candidates` ⇒ ✅ / ⚠️）/ 噪声标定 / 可行域构成 / 四路曲线 / "
    "四臂裁决（`inf` 一律 `—`）/ Pareto 前沿 / 推荐点与「D4 离最优多远」（含 `ΔA / (2·sd_A)` 倍数与支配它的**可行**设计个数）/ 本次运行的四条局限。",
    "",
    "**为什么必须由落盘件生成**：手写报告必然出现「数字来自上一次运行，而口径已经变了」—— §8.30 与 §8.31 两节里被推翻的更正，全都是这么产生的。",
    "",
    "### 5. 校验证据",
    "",
    "1. `python -u 1_Code/AutoRA_SPE/check_stage9_loop.py 1 1_Code/AutoRA_SPE/_scratch_check_stage9_loop_d57c_u8.txt` ⇒ **36/36、未通过 0 项、exit 0、39.1 s**"
    "（E7 实测：锚点 D4 遗漏率 0.3611、`feasible = False`）。",
    "2. `python -u 1_Code/AutoRA_SPE/check_stage9_report.py` ⇒ **40/40、未通过 0 项、exit 0**（日志 `1_Code/AutoRA_SPE/_scratch_check_stage9_report_u8.txt`）。",
    "3. 落盘件 `1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`（**346512 字节**）：`settings = {budget: 12, n_fim: 1, n_subjects: 40, P: null, rho: 0.6, seed: 0}`、"
    "`n_evals = 176`、`seconds = 541.4`、`front_scope = {n_candidates: 174, n_cached_before_full_eval: 36, n_evaluated: 174, n_front: 6}`、"
    "`d54 = {omission_band: [0.05, 0.2], n_band_rejected: 93, n_feasible: 27, criterion: [A, B]}`。",
    "4. 四臂（`compare` 行，本次**四臂全部取到可行点** ⇒ 没有触发那条新分支）：`random A_best = 0.3881 / B_at_A_best = 8.7653 / 5 个`、`grid 0.3897 / 8.6711 / 3`、"
    "`manual 0.3989 / 7.8768 / 2`、`bo 0.5113 / 8.8142 / 4`；`2·sd_A = 0.0050`、`2·sd_B = 0.2665` ⇒ `random` 与 `grid` **不可分辨**（ΔA 0.0016）、"
    "`manual` **被 random 支配**（ΔA 0.0108 > 0.0050、ΔB −0.8885 < −0.2665）、`bo` **在 (A) 上显著更差**（ΔA 0.1232 = 32%；B 分量不可分辨）。",
    "5. 报告第 7 节：推荐点 `A = 0.3446 / B = 8.6729 / 遗漏 0.191 / J = 0.3138`（`T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms × r16`）；"
    "锚点 D4 `A = 0.3858` ⇒ `ΔA = 0.0412` = 噪声带的 **8 倍**，被 **5** 个可行设计支配。",
    "",
    "### 6. 元教训",
    "",
    "1. **「没有数据」必须被命名。** 一个判据的两个分支都不成立时，最危险的写法是「落到 else = 最好」。",
    "2. **呈现层的缺省值不能兼任错误信号。** `—` 既表示「`inf`/`nan`」也表示「键读错」，读者无法区分 ⇒ 键名必须唯一（H4），且报告必须能自证作用域。",
    "3. **报告必须由落盘件生成。** 手写报告把「上一次运行的数字」与「这一次的口径」混在一起，而这种错误在文本里看不出来。",
    "",
    "### 7. 尚未做",
    "",
    "1. 上面第 4 条的实测是 `--budget 2` 那次冒烟触发的分支；**四臂都有可行点的路径**由本次 `--budget 12` 覆盖，两条路径都有证据，但**「部分臂无可行点」的真实运行**仍未出现（现有证据来自自测造的夹具）。",
    "2. `(A)` 仍依赖 `n_fim`（D4：`n_fim = 1/2/12` ⇒ `0.3858/0.3519/0.268`）⇒ 报告的每个 `(A)` 读数都必须连 `n_fim` 一起读。",
    "3. 可行域构成（27 可行 / 24 只被带否决 / 123 数值病态）是 `n_fim = 1` 的产物，须在正式 `n_fim` 下重测。",
    "",
]

RM_41 = (
    "| 41 | ✅ **「没有可行点的臂不得混排」与「报告必须由落盘件生成」已落地（D57，§8.32）** | "
    "`1_Code/AutoRA_SPE/stage9_loop.py` 787 → **821 行**：`compare_arms` 新增 `has_feasible_point` 与三分支（全臂无点 ⇒「没有任何一条臂…没有数据」；"
    "该臂无点 ⇒「不参与排序」；头名无对照 ⇒「只有它一条臂…不得写成『最好』」），有真对照时每条裁决末尾追加「另有 N 条臂没有可行点」；"
    "`main()` 非有限值印 `—`；`histories[arm]` 的 `B_at_best_A` → **`B_at_A_best`**（读错会把「`B`@`(A)` 最优点」整列静默印成 `—`）。"
    "**交付件**：`1_Code/AutoRA_SPE/stage9_report.py`（**323 行**）→ `1_Code/AutoRA_SPE/stage9_report.md`（**124 行**）+ "
    "`1_Code/AutoRA_SPE/check_stage9_report.py`（**286 行、40/40、exit 0**）；`check_stage9_loop.py` 374 → **423 行、36/36、39.1 s**（新增 E8 四条 + H4）。"
    "**实测**（`--budget 12` 全空间、`n_evals = 176`、内环 541.4 s、`n_evaluated = 174 = n_candidates`、落盘件 346512 字节）：四臂全部取到可行点 ⇒ "
    "`random 0.3881`（与 `grid 0.3897` 不可分辨）｜`manual 0.3989`（被 random 支配）｜`bo 0.5113`（(A) 上显著更差 32%）；"
    "推荐点 `A = 0.3446 / B = 8.6729 / 遗漏 0.191`；锚点 D4 `ΔA = 0.0412` 被 5 个可行设计支配 "
    "证据：`1_Code/AutoRA_SPE/_scratch_check_stage9_loop_d57c_u8.txt`、`1_Code/AutoRA_SPE/_scratch_check_stage9_report_u8.txt`、"
    "`1_Code/AutoRA_SPE/stage9_payload_nfim1_budget12.json`；§8.32 §5；遗传自第 40 项 |"
)


# ---------------------------------------------------------------- 主流程
def main():
    plan = []

    # ---- 文件 1：主计划 ----
    t = MP.read_text(encoding="utf-8")
    t = ins_after(t, "| **D56** | 2026-10-14 |", [D57_DECISION], "主计划 D57 决策行", guard="| **D57** |")
    t = ins_after(t, "| 2026-10-14 | **9**（前沿作用域 → D56） |", [D57_PROGRESS], "主计划 D57 进度行", guard="（无人可行点混排 + 落盘报告 → D57）")
    t = ins_after(t, "| 2026-10-14 | **新增 D56：", [D57_CHANGELOG], "主计划 变更日志 D57", guard="**新增 D57：")
    t = ins_after(t, "| `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（重写为离线/即时双模式）", [D57_APPENDIX], "主计划 附录证据 D57", guard="`1_Code/AutoRA_SPE/stage9_report.py`（**新建**，323 行）")
    t = patch(
        t,
        "**(3)** 建 Stage 9 最后一个文件 `stage9_report.md`；**(4)** 正式跑要不要把 `--budget` 与全空间评估分开计时，须在报告里写清",
        "~~**(3)** 建 Stage 9 最后一个文件 `stage9_report.md`；**(4)** 正式跑要不要把 `--budget` 与全空间评估分开计时，须在报告里写清~~ "
        "✅ **2026-10-14 已完成（D57 当轮）**：新建 `1_Code/AutoRA_SPE/stage9_report.py`（**323 行**）+ `1_Code/AutoRA_SPE/stage9_report.md`（**124 行**）+ "
        "`1_Code/AutoRA_SPE/check_stage9_report.py`（**286 行、40/40、exit 0**）；八节**一律由落盘件生成**（头部写 payload 的 `sha256` 前缀），"
        "作用域与运行设置印在第 1 节 ⇒ (4) 由第 1/8 节回答",
        "主计划 D56 进度行「仍开放」第 (3)(4) 件划掉",
        guard="已完成（D57 当轮）**：新建 `1_Code/AutoRA_SPE/stage9_report.py`",
    )
    plan.append(("工作流_主计划.md", t, MP))

    # ---- 文件 2：Stage 9 方案 ----
    t = S9.read_text(encoding="utf-8")
    t = patch_row(t, "| `1_Code/AutoRA_SPE/stage9_loop.py` |", S9_LOOP_TAIL, "Stage9 §9 stage9_loop.py 行末追加 D57", guard="❗ **D57**：`compare_arms` 在 `A_best = inf`")
    t = patch(t, "**787 行**、裸 LF —— D55 前为 618 行、D56 前为 749 行；", "**821 行**、裸 LF —— D55 前为 618 行、D56 前为 749 行、D57 前为 787 行；",
              "Stage9 §9 stage9_loop.py 行数")
    t = patch(t, "优化循环自测（A–G 七组）", "优化循环自测（A–H 八组）", "Stage9 §9 check_stage9_loop.py 组数")
    t = patch(t, "（**374 行**、裸 LF —— D55 前为 261 行、D56 前为 340 行）", "（**423 行**、裸 LF —— D55 前为 261 行、D56 前为 340 行、D57 前为 374 行）",
              "Stage9 §9 check_stage9_loop.py 行数")
    t = patch(t, "**31/31 通过、exit 0、63.0 s**（D56 新增 H 组三条静态源码判据）",
              "**36/36 通过、exit 0、39.1 s**（D56 新增 H 组三条静态源码判据 + D57 新增 E8 组四条与 H4）",
              "Stage9 §9 check_stage9_loop.py 判据数")
    t = patch(t, "E5 ΔA 超带但 ΔB 在带内 ⇒ 不可分辨；",
              "E5 ΔA 超带但 ΔB 在带内 ⇒ **「在 (A) 上显著更差」、不是「不可分辨」**（D55 洗白修正）；",
              "Stage9 §9 E5 的旧（洗白）措辞")
    t = patch(t, "汇总自测（W 组漂移守卫 + S1–S4 子自测）", "汇总自测（W 组漂移守卫 + S1–S5 子自测）", "Stage9 §9 check_stage9.py 子自测范围")
    t = patch(t, "✅ **已建**（185 行、裸 LF）。**W 组 5/5、exit 0**", "✅ **已建**（**193 行**、裸 LF —— D57 前为 185 行）。**W 组 5/5、exit 0**",
              "Stage9 §9 check_stage9.py 行数")
    t = patch(t, "`W2`/`W3` 五个文件**同时**登记", "`W2`/`W3` **七个文件**同时登记", "Stage9 §9 W2/W3 文件数")
    t = patch(t, "`W4` 五个文件真的在磁盘上", "`W4` **七个文件**真的在磁盘上", "Stage9 §9 W4 文件数")
    t = patch(t, "`S3` 29/29、`S4` 21/21。", "`S3` 29/29、`S4` 21/21、`S5` **40/40**（报告生成器自测）。",
              "Stage9 §9 S5 补登记")
    t = patch(t, "| `1_Code/AutoRA_SPE/stage9_report.md` | 落盘报告 | 🔨 待建。含哈希、预算、四路曲线、Pareto 前沿、\"D4 离最优多远\" |",
              S9_REPORT_ROW + "\n" + S9_REPORTGEN_ROW + "\n" + S9_REPORTCHK_ROW, "Stage9 §9 stage9_report.md 行 🔨 → ✅ 并新增两行")
    t = ins_after(t, "20. ", [S9_11_21], "Stage9 §11 新增第 21 条", guard="21. ❗ **裁决与报告的呈现纪律（D57）**")
    t = ins_after(t, "| 2026-10-14 | **前沿作用域缺陷 + 决策 D56**：", [S9_12_D57], "Stage9 §12 新增 D57 行", guard="**无人可行点的臂不得混排 + 报告必须由落盘件生成（决策 D57）**")
    plan.append(("Stage9_设计空间优化与论文整合方案.md", t, S9))

    # ---- 文件 3：AutoRA_SPE/README.md §7 ----
    t = RA.read_text(encoding="utf-8")
    t = patch_row(t, "| `stage9_loop.py` |", RA_LOOP_TAIL, "README §7 stage9_loop.py 行末追加", guard="❗ **D57**：`compare_arms` 在 `A_best = inf` 时**不再参与排序**")
    t = patch(t, "**优化循环**（**749 行**）", "**优化循环**（**821 行**）", "README §7 stage9_loop.py 行数")
    t = patch_row(t, "| `check_stage9_loop.py` |", RA_LOOPCHK_TAIL, "README §7 check_stage9_loop.py 行末追加", guard="❗ **D57** 新增 **E8 组**")
    t = patch(t, "循环自测（A–H 八组，**31/31**）", "循环自测（A–H 八组，**36/36**）", "README §7 check_stage9_loop.py 判据数")
    t = patch_row(t, "| `check_stage9.py` |", RA_AGG_TAIL, "README §7 check_stage9.py 行末追加", guard="❗ **D57**：`STAGE9_FILES` 由五个改**七个**")
    t = patch(t, "**Stage 9 汇总自测**（**185 行**）", "**Stage 9 汇总自测**（**193 行**）", "README §7 check_stage9.py 行数")
    t = patch(t, "五个文件在两份文档里都登记", "**七个文件**在两份文档里都登记", "README §7 汇总自测的文件数")
    t = patch(t, "与 S1–S4 四个子自测跑一遍", "与 S1–S5 五个子自测跑一遍", "README §7 汇总自测的子自测数")
    t = ins_after(t, "| `check_stage9.py` |", RA_NEW_ROWS, "README §7 新增三行", guard="| `stage9_report.py` |")
    plan.append(("1_Code/AutoRA_SPE/README.md", t, RA))

    # ---- 文件 4：DDM_Core/README.md ----
    t = RM.read_text(encoding="utf-8")
    t = ins_before(t, "## 9. 尚未做", RM_832, "DDM README 新增 §8.32", guard="## 8.32 没有可行点的臂不得与有可行点的臂同台排序")
    t = ins_after(t, "| 40 | ✅ **「先补全候选空间再算前沿」已被一次全空间实跑验证（D56", [RM_41], "DDM README §9 新增第 41 项", guard="| 41 | ✅ **「没有可行点的臂不得混排」")
    plan.append(("1_Code/DDM_Core/README.md", t, RM))

    # ---- 写盘 ----
    for name, text, path in plan:
        if not text.endswith("\n"):
            text += "\n"
            print(f"  · {name}：补行末换行")
        if APPLY:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"✅ 写盘 {name}（{len(text.splitlines())} 行）")
        else:
            print(f"· 干跑 {name}（{len(text.splitlines())} 行，未写）")


if __name__ == "__main__":
    main()
