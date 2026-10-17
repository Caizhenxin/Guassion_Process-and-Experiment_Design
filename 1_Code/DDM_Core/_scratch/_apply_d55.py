# -*- coding: utf-8 -*-
"""把决策 D55 写进 `5_Reference/08_工作流/工作流_主计划.md`（四处插入 + 两处就地更正）。

**D55 的内容**：D54 的决定**落到代码**（`stage9_loop.py` 的 `OMISSION_BAND` 约束 +
只比较 `(A)/(B)` 的裁决），交付时抓到**一次裁决洗白**（把「(A) 差 32%」说成「不可分辨」），
并**更正两条我自己写错的记录**：① 内环**不依赖** `n_x`（全符号 grep 无 `n_x`/`hier`/`ddm_subject`）；
② 「D4 被某设计在 (A,B) 上支配」在**有可行域时是错的**（那位"支配者"自己也在遗漏率带外）。
另立一条**待拍板**事项：事前登记的遗漏率带 `[0.05, 0.20]` 与已定稿的锚点 D4（遗漏 0.3611）不相容。

体例同 `_apply_d47`–`_apply_d54`：前缀定位 + 分隔符断言 + 断表断言 + 幂等守卫 +
**只插一行时绝不触碰空行** + 输出必须以换行结尾。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d55.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d55.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path("5_Reference/08_工作流/工作流_主计划.md")

# —— 就地更正之一：D53 进度行里的「D4 被支配」在 D54 之后不成立 ——
STALE_1 = ("④ **锚点 D4 被 `T[33.33/83.33/249.98]ms × W[799.98/1199.90/2399.80]ms × r16` "
           "在 (A,B) 两维上同时支配** ⇒ 「D4 不是 Pareto 最优」与遗漏率罚分无关；")
FIXED_1 = (STALE_1 + " ❌ **2026-10-14 更正（见 D55）**：这句在有可行域时是错的 —— 那位"
           "「支配者」自己的遗漏率实测 **0.3220**，**也在冻结带（上界 0.20）之外** ⇒ "
           "不能用不可执行的设计去否定可执行的设计；**可行集内 0 个设计**在 (A,B) 上支配 D4。")

# —— 就地更正之二：D54 进度行的「仍开放」第 (1) 件已完成 ——
STALE_2 = ("**(1)** 把 (C) 改成约束并重新评估四臂（改动冻结 Objective 的**使用方式**而非"
           "其数值定义，须记录）；")
FIXED_2 = ("~~**(1)** 把 (C) 改成约束并重新评估四臂（改动冻结 Objective 的**使用方式**而非"
           "其数值定义，须记录）；~~ ✅ **2026-10-14 已完成（见 D55）**：`OMISSION_BAND` 读自 "
           "`S9O.FROZEN[\"omission_band\"]`（**与冻结 Objective 同源 ⇒ 不动哈希**）、"
           "`CRITERION = (\"A\",\"B\")`、四臂重跑。另新增第 (5) 件：🛑 **带与 D4 不相容须拍板**；")

DEC_PREFIX = "| **D54** |"
DEC_ROW = (
    "| **D55** | 2026-10-14 | ✅ **D54 已落到代码；同时更正两条我自己写错的记录，"
    "并把「冻结带与锚点不相容」立为待拍板事项**。① **代码落地**：`1_Code/AutoRA_SPE/stage9_loop.py`"
    "（618 → **749 行**）新增 `OMISSION_BAND`（读自 `S9O.FROZEN[\"omission_band\"]`，"
    "**与冻结 Objective 同源 ⇒ 不动哈希**，带改由搜索层执行）与 `CRITERION = (\"A\",\"B\")`；"
    "`_objective_record` 把带外设计置 `feasible=False` 并把理由写进 `gates`"
    "（**罚分照算但不进判据**）；`best(key=\"A\")` 成为推荐点；`run_arms` 增记 `curve_a` / "
    "`best_A` / `B_at_best_A`（同一点 ⇒ 配对）；`compare_arms` 只看 `(A_best, B_at_A_best)` "
    "并用两根噪声带。② **裁决必须反「洗白」**：首版把「ΔA 超带但 ΔB 在带内」判成「不可分辨」，"
    "于是 BO 在 (A) 上差 **32%** 被印成「不可分辨」—— 这正是处方⑥「GP 必须自己证明配得上」"
    "要防的洗白。改判为「**在 (A) 上显著更差（而 B 分量不可分辨）⇒ 不是『两者不可分辨』**」。"
    "③ **D54 后冒烟**（176 次评估、内环 803–808 s）：**带外 22 个 / 可行 27 个**；"
    "`2·sd_A = 0.0050`、`2·sd_B = 0.2665`；推荐点 `A = 0.3881 / B = 8.7653 / 遗漏 0.168`；"
    "**锚点 D4 `A = 0.3858 / B = 7.4824 / 可行 = False / ΔA = −0.0023`（在噪声带内）⇒ "
    "取消 D4 资格的只有遗漏率带这一条，不是精度**；四臂 `random 0.3881`（top）｜"
    "`grid 0.3897`（ΔA 0.0016 ≤ 0.0050 ⇒ 不可分辨）｜`manual 0.3989`（被 random **支配**）｜"
    "**`bo 0.5113`（在 (A) 上显著更差 32%）**。④ ❗ **更正一（内环不依赖 `n_x`）**：曾写"
    "「`stage9_inner` 走 `hier.ddm_subject` 的默认 `n_x`」—— 全符号 grep 证明 "
    "`stage9_inner.py` **不含 `n_x` / `hier` / `ddm_subject`**，内环用 `simulate_subject` / "
    "`simulate_euler_subject` + `trials_from_arrays` 造试次、用 `likelihood.opg_information` / "
    "`twophase.opg_information_step` 算信息量，**根本没有似然网格**（真正的分辨率旋钮是 "
    "`DT_GEN = 5e-5` 与 `REL_STEP_FD = 1e-3`，这两个必须连同结论一起报）。"
    "⑤ ❗ **更正二（「支配」必须连着可行域说）**：§11 第 15 条曾写「D4 被某设计在 (A,B) 上同时支配、"
    "与罚分带无关」；实测那位「支配者」自己的遗漏率 **0.3220** 也在带（上界 0.20）之外 ⇒ "
    "**不能用不可执行的设计否定可执行的设计**，可行集内 **0 个**设计支配 D4。"
    "⑥ 🛑 **待拍板**：带 `[0.05, 0.20]` 与已定稿的 D4（遗漏 0.3611）不相容，三种处置 "
    "(a) 作为 9A 头条结论报出（本轮采用）/ (b) 显式重冻结 / (c) D4 仅作归一化锚点。 | "
    "① `1_Code/AutoRA_SPE/_scratch_stage9_loop_smoke12_d54_u8.txt` 与同名 `.json`"
    "（176 次评估 / 内环 803–808 s / 墙钟 819 s）；`1_Code/AutoRA_SPE/check_stage9_loop.py` "
    "**28/28、exit 0、58.8 s**（原 21 项；E 组重写 + 新增 E′ 组 E2b/E6/E6b/E7）；"
    "`1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（**一次 `inner_eval` 即够**，因为 "
    "`stage9_objective.component_A(res)` 与锚点无关）日志 `_scratch_probe_d4_domination_u8.txt`；"
    "② 更正依据 = 对 `1_Code/AutoRA_SPE/stage9_inner.py` 的**全符号 grep**（无 `n_x` / `hier` / "
    "`ddm_subject`）与 `_objective_record` 的 `OMISSION_BAND` 断言；"
    "③ **新读数：`(A)` 依赖 `n_fim`**（同一设计 D4：`n_fim=1` → **0.3858**、`n_fim=2` → **0.3519**、"
    "`n_fim=12` → **0.268**）⇒ **任何 (A) 值必须连同 `n_fim` 一起报**。 | "
    "① `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9 三行、"
    "§11 第 10 / 15 条**就地更正** + 新增第 **18** 条（带与 D4 不相容、待拍板）与第 **19** 条"
    "（(A) 依赖 `n_fim`）、§12 三行；② `1_Code/DDM_Core/README.md` §8.30 + §9 第 37 / 38 项 + "
    "§8.27 末条更正；③ `1_Code/AutoRA_SPE/README.md` §7；④ **D53 进度行的「D4 被支配」被更正**"
    "（本脚本的就地更正之一）；⑤ **本轮起凡报 (A) 必须同时报 `n_fim` 与可行域口径** |"
)

PROG_PREFIX = "| 2026-10-14 | **9**（Objective 标量化被噪声支配 → D54）"
PROG_ROW = (
    "| 2026-10-14 | **9**（D54 落到代码 + 两处更正 → D55） | "
    "**把 D54 从「文档上的决定」变成代码里的约束与裁决，并在交付过程中抓到一次裁决洗白与"
    "两条我自己写错的记录**。① 代码：`OMISSION_BAND` 与冻结 Objective **同源**（不动哈希）、"
    "带外设计 `feasible = False`、`best(key=\"A\")` 为推荐点、四臂只比 `(A, B@A_best)`；"
    "② **裁决洗白**：首版把「(A) 差 32%」印成「不可分辨」（因为 B 分量不可分辨就吞掉了 A 的"
    "显著差异）⇒ 改判为「在 (A) 上显著更差，而 B 分量不可分辨」，并把「头名 A 更好但 B 明显更差」"
    "改判为「权衡…不得宣称最好」；③ **D54 后冒烟**：带外 22 / 可行 27，推荐点 "
    "`A = 0.3881 / B = 8.7653 / 遗漏 0.168`，**锚点 D4 `A = 0.3858 / 可行 = False / "
    "ΔA = −0.0023`（在噪声带内）⇒ 取消 D4 资格的是遗漏率，不是精度**；四臂 `random` 最好、"
    "`grid` 不可分辨、`manual` 被 random 支配、**`bo` 在 (A) 上差 32%**；"
    "④ ❗ 更正「内环依赖 `n_x`」（全符号 grep 反证）；⑤ ❗ 更正「D4 被某设计支配」"
    "（那位支配者自己也在带外）；⑥ 🛑 新增待拍板：**带与 D4 不相容**。 | "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（618 → **749 行**）；`1_Code/AutoRA_SPE/check_stage9_loop.py`"
    "（261 → **340 行**，**28/28、exit 0、58.8 s**）；`1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`"
    "（新建，一次 `inner_eval` 反证「支配」）；日志 `1_Code/AutoRA_SPE/"
    "_scratch_stage9_loop_smoke12_d54_u8.txt`、`_scratch_check_stage9_loop_u8.txt`、"
    "`_scratch_probe_d4_domination_u8.txt`；`1_Code/DDM_Core/README.md` §8.30、§9 第 37 / 38 项；"
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9 / §11 / §12 | "
    "🔨 **仍开放**：**(1)** 🛑 遗漏率带与锚点 D4 不相容 —— 三选一（报出来 / 重冻结 / D4 只作锚点），"
    "**须用户或导师拍板**；**(2)** 把逐设计的 `cache` 写进 `stage9_loop` 的 JSON 载荷"
    "（现在落盘件无法离线复算支配关系，要靠探针补一次评估）；**(3)** 重复 **R 个种子组**"
    "以得到配对误差棒（现在只有 1 个种子组、`2·sd_A` 只由 2 次重复估出）；"
    "**(4)** Stage 9 最后一个文件 `stage9_report.md`；**(5)** **`beta_ST` 不在确证集**、"
    "但 `stage9_inner` 默认 `param_set=\"exp\"`（9 参数）—— 论文报 (A) 时必须写明用的是哪一套 |"
)

LOG_PREFIX = "| 2026-10-14 | **新增 D54："
LOG_ROW = (
    "| 2026-10-14 | **新增 D55：D54 落到代码（`OMISSION_BAND` 约束 + 只比 `(A)/(B)` 的裁决）；"
    "抓到一次「把 A 差 32% 说成不可分辨」的裁决洗白并改判；更正两条写错的记录（内环不依赖 "
    "`n_x`；「D4 被支配」在有可行域时是错的）；立一条待拍板（冻结带与 D4 不相容）。"
    "新读数：`(A)` 依赖 `n_fim`** |"
)

APP_PREFIX = ("| `1_Code/AutoRA_SPE/_scratch_probe_noise_curve.py`（**新建**，80 行）")
APP_ROW = (
    "| `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（**新建**） + "
    "`1_Code/AutoRA_SPE/check_stage9_loop.py`（261 → 340 行，28/28） + "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（618 → 749 行） | **D55**：`OMISSION_BAND` 约束落地；"
    "裁决只建立在 `(A)/(B)` 上并拒绝「把 A 差 32% 说成不可分辨」；用一次 `inner_eval` 证明"
    "「支配 D4」的那位设计自己也在遗漏率带外（0.3220 > 0.20）⇒ 可行集内无设计支配 D4；"
    "更正「内环依赖 `n_x`」与「D4 被支配」两条错记 |"
)


def n_sep(line: str) -> int:
    """数一行里**未被转义**的竖线个数（转义的 `\\|` 不算分隔符）。"""
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    text = P.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        print("❌ 输入文件不以换行结尾，拒绝写回")
        return 2
    if "| **D55** |" in text:
        print("❌ 已存在 `| **D55** |`，本脚本已跑过（幂等守卫）")
        return 2
    lines = text[:-1].split("\n")
    print(f"读入 {P}：{len(lines)} 行")

    for tag, stale, fixed in (("D53 进度行的「D4 被支配」", STALE_1, FIXED_1),
                              ("D54 进度行的「仍开放」第 (1) 件", STALE_2, FIXED_2)):
        hits = [i for i, s in enumerate(lines) if stale in s]
        if len(hits) != 1:
            print(f"❌ 待更正的句子（{tag}）命中 {len(hits)} 次（期望 1 次），拒绝写回")
            return 2
        i = hits[0]
        new = lines[i].replace(stale, fixed)
        if n_sep(lines[i]) != n_sep(new):
            print(f"❌ 更正前后分隔符数变化（{tag}）：{n_sep(lines[i])} → {n_sep(new)}，拒绝写回")
            return 2
        lines[i] = new
        print(f"✅ 就地更正：L{i + 1}（{tag}，分隔符数不变 = {n_sep(new)}）")

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
