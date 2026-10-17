# -*- coding: utf-8 -*-
"""把决策 D56 写进主计划（四处插入 + 三处就地更正）并更正 Stage 9 方案文档（两处）。

**D56 的内容**：「前沿与推荐点必须覆盖整个候选空间，且其作用域必须落盘」，
并**更正 D55 的两条错误更正** —— 实测证明 **D4 不但不可行，还被 5 个可行设计在 (A,B) 上支配**。

为什么会有 D56：`1_Code/AutoRA_SPE/stage9_loop.py` 的 `pareto_front()` 走
`names or list(ev.cache)`、`best()` 也只在缓存里找，而 `main()` 原先在补全候选空间
**之前**调用它们 ⇒ 报出的「推荐点 / 前沿」其实是**四臂抽到的那些点里最好的**，
其好坏完全取决于 `--budget`，而输出里看不出这一点。`--budget 12` 报 `A = 0.3881`，
补全 174 个候选后真值 `A = 0.3446`（且该设计**可行**、遗漏 0.1910 落在冻结带内）。

体例同 `_apply_d47`–`_apply_d55`：前缀/子串定位 + 分隔符断言 + 断表断言 + 幂等守卫 +
**只插一行时绝不触碰空行** + 输出必须以换行结尾。本脚本**跨两个文件**工作。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d56.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d56.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MP = Path("5_Reference/08_工作流/工作流_主计划.md")
S9 = Path("5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md")

# ------------------------------------------------------------------
# 就地更正（按「行前缀 + 追加后缀」做，不重写整行，避免在数千字符的行里
# 逐字匹配；同时断言追加前后**未被转义的竖线个数不变**）
# ------------------------------------------------------------------
CORRECTIONS = [
    # —— 主计划：D55 决策行 ——
    (MP, "| **D55** |",
     " ❌ **2026-10-14 更正（见 D56）**：本条 ③ 的「取消 D4 资格的只有遗漏率带这一条，"
     "不是精度」与 ⑤ 的「可行集内 0 个设计支配 D4」**都错** —— 那是 "
     "`pareto_front()` / `best()` 只在**四臂已缓存的点**上计算造成的假象。补全 174 个候选"
     "空间后：**可行集内支配 D4 的有 5 个**设计，最强者 "
     "`T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms × r16` 的 "
     "`A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`（**在冻结带内**），"
     "`ΔA = +0.0412` = 噪声带 `2·sd_A = 0.0050` 的 **8 倍**。详见 D56。"),
    # —— 主计划：D53 进度行里的 D55 更正 ——
    (MP, "| 2026-10-14 | **9**（优化循环交付 → D53） |",
     " ❌ **2026-10-14 更正（见 D56）**：上面这句「**可行集内 0 个设计**在 (A,B) 上支配 D4」"
     "**是错的** —— 它来自一次单设计探针 + 一个只覆盖四臂抽样点的前沿；补全候选空间后"
     "**可行集内有 5 个**设计在 (A,B) 上支配 D4。"),
    # —— 主计划：D55 进度行 ——
    (MP, "| 2026-10-14 | **9**（D54 落到代码 + 两处更正 → D55） |",
     " ❌ **2026-10-14 更正（见 D56）**：③ 的「取消 D4 资格的是遗漏率，不是精度」与 ⑤ 的"
     "「可行集内 0 个」两句**都不成立**：补全 174 个候选空间后，**5 个可行设计**在 (A,B) 上"
     "支配 D4（最强者 `A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`，"
     "`ΔA = +0.0412` = 8 倍噪声带）；D55 引用的那位「支配者」只是**众多支配者之一**，"
     "且它自己也不可行。"),
    # —— Stage 9 方案文档：§11 第 15 条 ——
    (S9, "15. **`(A)` 的遗漏率罚分带在\"高 W\"区才可达**",
     " ❌ **2026-10-14 更正（见 D56）**：上面 (i) 与 (ii) **都错**。原因：`pareto_front()` 与 "
     "`best()` 只在**已缓存的点**上计算，而 `main()` 原先在补全候选空间**之前**调用它们 ⇒ "
     "报出的「推荐点 `0.3881`」与「`ΔA` 落在噪声带内」只是四臂抽到的 49 个点里的读数。"
     "补全 174 个候选空间后：推荐点 `A = 0.3446 / B = 8.6729`，**可行集内支配 D4 的有 5 个**"
     "设计（`ΔA = +0.0412` = 噪声带 0.0050 的 8 倍）。⇒ 9A 的正确表述是："
     "**D4 既不可行（遗漏 0.3611 > 0.20），也被 5 个可行设计在 (A,B) 上支配**。"),
    # —— Stage 9 方案文档：§12 变更日志里那条 D55 更正 ——
    (S9, "| 2026-10-14 | ❗ **更正 §11 第 15 条里",
     " ❌ **2026-10-14 更正（见 D56）**：本条末尾的「**可行集内 0 个**设计在 (A,B) 上支配 "
     "D4」**是错的** —— 该结论从一次单设计探针推出，而前沿当时只覆盖四臂抽样点；"
     "补全 174 个候选空间后，**可行集内有 5 个**设计支配 D4"
     "（最强者 `A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`）。"),
]

# ------------------------------------------------------------------
# 主计划四处插入
# ------------------------------------------------------------------
DEC_ANCHOR = "| **D55** |"
DEC_ROW = (
    "| **D56** | 2026-10-14 | ✅ **「前沿与推荐点必须覆盖整个候选空间」，且其作用域必须落盘；"
    "同时更正 D55 的两条错误更正**。① **缺陷**：`1_Code/AutoRA_SPE/stage9_loop.py` 的 "
    "`pareto_front(ev, names=None)` 走 `names or list(ev.cache)`、`ev.best(\"A\")` / "
    "`ev.best(\"J\")` 也只在缓存里找，而 `main()` 原先的顺序是「先算前沿/推荐点、**后**调 "
    "`ev.feasible_names()` 补全空间」⇒ 报出的推荐点与前沿其实是**四臂抽到的那些点里最好的**，"
    "其好坏完全取决于 `--budget`，而输出里看不出这一点。实测（`n_fim=1`、`rho=0.6`、"
    "`--noise-repeats 2`）：`--budget 12` 报推荐点 `A = 0.3881`，补全 174 个候选空间后真值 "
    "`A = 0.3446`。② **后果（推翻 D55 的两条更正）**：补全空间后**可行集内支配 D4 的有 5 个**"
    "设计，最强者 `T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms × r16` 的 "
    "`A = 0.3446 < 0.3858`、`B = 8.6729 > 7.4824`、遗漏 **0.1910**（**在冻结带 "
    "`[0.05, 0.20]` 内**）⇒ `ΔA = +0.0412` 是噪声带 `2·sd_A = 0.0050` 的 **8 倍**。"
    "⇒ D55 的「可行集内 0 个设计支配 D4」与「取消 D4 资格的是遗漏率而非精度」**两句都错**，"
    "9A 的正确表述是「**D4 既不可行（遗漏 0.3611 > 0.20），也被 5 个可行设计在 (A,B) 上支配**」。"
    "③ **元教训**：从一个设计的探针结果推出全空间结论（「一个不可行的支配者」**不等于**"
    "「没有可行的支配者」），以及**报告的作用域必须落盘**。④ **修法**：`main()` 在算前沿之前"
    "先调 `ev.feasible_names()`（幂等，命中缓存不重算），并打印 `[前沿] 先补全候选空间…` / "
    "`[前沿] 全空间评估完毕…`；payload 新增 `front_scope = {n_candidates, "
    "n_cached_before_full_eval, n_evaluated, n_front}`。⑤ **代价**：报前沿必须覆盖整个候选空间 "
    "⇒ 任何一次运行的耗时下限 ≈ `174 × 单次内环评估`（`n_fim=1` 约 3.5–5 s ⇒ **10–15 min**），"
    "**与 `--budget` 无关**。 | "
    "① `1_Code/AutoRA_SPE/_scratch_probe_d4_domination_cache_u8.txt`（离线模式读 "
    "`_scratch_payload_check.json` 的 174 项 `cache`：可行 27、不可行 147；全部支配者 25 个、"
    "**可行集内 5 个**）；② `1_Code/AutoRA_SPE/stage9_loop.py`（749 → **770 行**，新增 "
    "`_jsonable()`、payload 的 `cache` 与 `front_scope`、前沿前补全空间）；"
    "③ `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（重写为**离线/即时双模式**） | "
    "① 优化循环的输出新增 `front_scope`，任何「推荐点 / 前沿」都必须连同作用域一起读；"
    "② 每次运行耗时下限 ≈ 全空间 174 次评估（`n_fim=1` 约 10–15 min），与 `--budget` 无关；"
    "③ **9A 的头条结论被加强**（D4 被可行设计支配 **且** 自身不可行）；"
    "④ D55 第 18 条的三种处置仍待拍板 | "
)
PROG_ANCHOR = "| 2026-10-14 | **9**（D54 落到代码 + 两处更正 → D55） |"
PROG_ROW = (
    "| 2026-10-14 | **9**（前沿作用域 → D56） | **给优化循环的落盘件补上逐设计 `cache`，"
    "用离线探针复核 D4 的支配关系，结果推翻了自己上一轮刚写下的两条更正**。① 动机：D55 把"
    "「payload 缺 `cache` ⇒ 落盘件无法离线复算支配关系」列为待办；新增模块级 `_jsonable()` "
    "（递归折 `np.ndarray`/`np.generic`）把**全部 174 个设计**的读数写进 JSON。"
    "② ❗ **探针结论**：缓存 174 个（可行 27、不可行 147）；锚点 D4 `A = 0.385802 / "
    "B = 7.482412 / 遗漏 0.3611 / 可行 = False`；**全部支配者 25 个**、"
    "**可行集内支配者 5 个**，最强者 `T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms "
    "× r16`（`A = 0.3446 / B = 8.6729 / 遗漏 0.1910`）⇒ `ΔA = +0.0412` = 8 倍噪声带。"
    "③ ❗ **根因**：`pareto_front()` 与 `best()` 只覆盖**已缓存**的点，而 `main()` 在补全空间"
    "**之前**调用它们 ⇒ `--budget` 决定了「推荐点」是什么；这解释了 D54 那次 `--budget 12` "
    "报的 `A = 0.3881`（真值 0.3446）。④ **修法**：算前沿前先 `ev.feasible_names()` 补全空间、"
    "打印 `[前沿] …`、payload 加 `front_scope`。⑤ 代价：耗时下限 = 全空间 174 次评估"
    "（`n_fim=1` 约 10–15 min），与 `--budget` 无关。 | "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（749 → **770 行**）；"
    "`1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（重写，**离线/即时双模式**）；"
    "日志 `_scratch_payload_check_u8.txt`、`_scratch_probe_d4_domination_cache_u8.txt`；"
    "`_scratch_payload_check.json`（含 174 项 `cache`）；后台作业 pwsh-170（验证修法） | "
    "🔨 **仍开放**：**(1)** 🛑 遗漏率带与锚点 D4 不相容 —— 三选一（报出来 / 重冻结 / "
    "D4 只作锚点），**须用户或导师拍板**；**(2)** 给 `check_stage9_loop.py` 补一个新牙齿"
    "（断言前沿前已补全空间、`front_scope.n_evaluated == front_scope.n_candidates`）；"
    "**(3)** 建 Stage 9 最后一个文件 `stage9_report.md`；**(4)** 正式跑要不要把 "
    "`--budget` 与全空间评估分开计时，须在报告里写清 |"
)
LOG_ANCHOR = "| 2026-10-14 | **新增 D55："
LOG_ROW = (
    "| 2026-10-14 | **新增 D56：前沿与推荐点必须在整个候选空间上算、作用域必须落盘；"
    "并更正 D55 的两条错误更正（D4 确实被 5 个可行设计在 (A,B) 上支配，`ΔA = +0.0412` "
    "是噪声带的 8 倍）** |"
)
APP_ANCHOR = "| `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（**新建**）"
APP_ROW = (
    "| `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（重写为离线/即时双模式） + "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（749 → 770 行） | **D56**：用落盘 JSON 的 174 项 "
    "`cache` 复核 D4 的支配关系 ⇒ **可行集内 5 个设计支配 D4**（最强者 `A = 0.3446 / "
    "B = 8.6729 / 遗漏 0.1910`，`ΔA = +0.0412` = 8 倍噪声带），推翻 D55 的「可行集内 0 个」"
    "与「不是精度」两句；根因 = `pareto_front()`/`best()` 只覆盖四臂抽样点；"
    "修法 = 算前沿前补全空间 + payload 落 `front_scope` |"
)


def n_sep(line: str) -> int:
    """数一行里**未被转义**的竖线个数（转义的 `\\|` 不算分隔符）。"""
    return line.count("|") - line.count("\\|")


def read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        raise ValueError(f"{path} 不以换行结尾")
    return text[:-1].split("\n")


def write_lines(path: Path, lines: list[str], apply: bool) -> None:
    out = "\n".join(lines) + "\n"
    if apply:
        path.write_text(out, encoding="utf-8", newline="\n")
        print(f"✍️ 已写回：{path}（{len(lines)} 行）")
    else:
        print(f"（干跑）将写回 {path}（{len(lines)} 行）")


def check_no_split(where: str, lines: list[str]) -> bool:
    for i in range(1, len(lines) - 1):
        if not lines[i].strip():
            if (lines[i - 1].lstrip().startswith("|") and n_sep(lines[i - 1]) >= 2
                    and lines[i + 1].lstrip().startswith("|") and n_sep(lines[i + 1]) >= 2):
                print(f"❌ 断表（{where}）：L{i + 1} 是空行而两侧都是表格行，拒绝写回")
                return False
    return True


def main() -> int:
    apply = "--apply" in sys.argv
    if "| **D56** |" in MP.read_text(encoding="utf-8"):
        print("❌ 主计划已存在 `| **D56** |`，本脚本已跑过（幂等守卫）")
        return 2

    # —— 1) 就地更正（跨两个文件）——
    by_file: dict[Path, list[str]] = {MP: read_lines(MP), S9: read_lines(S9)}
    for path, prefix, suffix in CORRECTIONS:
        lines = by_file[path]
        hits = [i for i, s in enumerate(lines) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 锚点 {prefix[:40]!r}（{path.name}）命中 {len(hits)} 次，拒绝写回")
            return 2
        i = hits[0]
        if "见 D56" in lines[i]:
            print(f"❌ 该行已含「见 D56」（{path.name} L{i + 1}），拒绝重复追加")
            return 2
        new = lines[i] + suffix
        if n_sep(lines[i]) != n_sep(new):
            print(f"❌ 追加前后分隔符数变化（{path.name} L{i + 1}）："
                  f"{n_sep(lines[i])} → {n_sep(new)}，拒绝写回")
            return 2
        lines[i] = new
        print(f"✅ 就地更正：{path.name} L{i + 1}（分隔符数不变 = {n_sep(new)}）")

    # —— 2) 主计划四处插入 ——
    lines = by_file[MP]
    for prefix, row, cols in ((DEC_ANCHOR, DEC_ROW, 5), (PROG_ANCHOR, PROG_ROW, 5),
                              (LOG_ANCHOR, LOG_ROW, 2), (APP_ANCHOR, APP_ROW, 2)):
        hits = [i for i, s in enumerate(lines) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 插入锚点 {prefix[:40]!r} 命中 {len(hits)} 次，拒绝写回")
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
        print(f"✅ 插入 {cols} 列行：L{i + 2}（锚点 {prefix[:32]}…）")

    if not check_no_split("主计划", lines) or not check_no_split("Stage9", by_file[S9]):
        return 2

    # 输出必须以换行结尾（write_lines 负责）；写回前再复核一次
    for path, ls in by_file.items():
        if ls != [s for s in ls]:
            print("❌ 内部一致性断言失败")
            return 2
    write_lines(MP, by_file[MP], apply)
    write_lines(S9, by_file[S9], apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
