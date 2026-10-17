# -*- coding: utf-8 -*-
"""D56 的第二批落纸：`1_Code/DDM_Core/README.md`（新增 §8.31 + §9 第 39 项 + 两处就地更正）
与 `Stage9_设计空间优化与论文整合方案.md`（§11 第 20 条 + §12 一行）。

体例同 `_apply_d56.py`：前缀定位 + 分隔符断言 + 断表断言 + 幂等守卫 + 输出须以换行结尾。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d56_docs.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d56_docs.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RM = Path("1_Code/DDM_Core/README.md")
S9 = Path("5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md")

# ---------------------------------------------------------------- README §8.31
SECTION = """## 8.31 前沿与推荐点的作用域：`pareto_front()` 只覆盖抽样点（2026-10-14，D56）

### 1. 为什么有这一节
D55 把「payload 缺逐设计 `cache` ⇒ 落盘件无法离线复算支配关系」列为待办。补上 `cache` 之后，用 `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py` 的**离线模式**读了 `1_Code/AutoRA_SPE/_scratch_payload_check.json` 里全部 **174** 个设计的读数，结果**推翻了 D55 刚写下的两条更正**。

### 2. 代码改动（`1_Code/AutoRA_SPE/stage9_loop.py`，749 → **770 行**）
1. 新增模块级 `_jsonable(x)`：递归把 `np.ndarray` → `list`、`np.generic` → Python 标量（`inner_eval` 的 `se` / `se_sd` / `acc` 是数组，`json.dumps` 直接抛 `TypeError`）；
2. payload 新增 `"cache": {name: 记录}` ⇒ **落盘件自足**，支配关系与前沿可离线复算；
3. **算前沿之前先补全候选空间**：`run_arms` 之后调用 `ev.feasible_names()`（幂等，命中缓存不重算），并打印 `[前沿] 先补全候选空间（缓存里现有 N 个，候选共 M 个）…` 与 `[前沿] 全空间评估完毕：缓存 N 个、累计 n_evals 次内环评估、秒数`；
4. payload 新增 `"front_scope": {"n_candidates", "n_cached_before_full_eval", "n_evaluated", "n_front"}`。

### 3. ❗ 缺陷：报出的「推荐点 / 前沿」其实是四臂抽样点里的最优
`def pareto_front(ev, names=None)`（L631）的循环头是 `for n in (names or list(ev.cache)):`，`ev.best("A")` / `ev.best("J")` 也只在缓存里找；而 `main()` 原先的顺序是 `front = pareto_front(ev)`（L713）→ `best(...)`（L714–715）→ … → `n_feas = len(ev.feasible_names())`（L718，**这一步才补全空间**）⇒ 报出的推荐点**完全取决于 `--budget`**，而输出里看不出这一点。实测对照（同一 `--n-fim 1 --noise-repeats 2 --seed 0`）：`--budget 12` 报 `A = 0.3881`；补全 174 个候选空间后该空间的最优可行设计是 `A = 0.3446`。

### 4. ❗ 后果：D55 的两条更正都错 —— D4 确实被 5 个**可行**设计支配
离线探针（缓存 **174** 个：可行 **27**、不可行 **147**）：
- 锚点 D4：`A = 0.385802`、`B = 7.482412`、`C = 10.382716`、`J = 10.882716`、遗漏 **0.3611**、`feasible = False`；
- **全部**已评估设计里支配 D4 的：**25 个**（前几名 `A = 0.2309 / 0.2440 / 0.2463 / 0.2503`，全部**不可行**）；
- **可行集内**支配 D4 的：**5 个**，最强者 `T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms × r16`：`A = 0.3446 < 0.3858`、`B = 8.6729 > 7.4824`、遗漏 **0.1910（在冻结带内）**；另四个 `A = 0.3495 / 0.3614 / 0.3840 / 0.3849`；
- ⇒ `ΔA = +0.0412` 是噪声带 `2·sd_A = 0.0050` 的 **8 倍** ⇒ **D55 的「可行集内 0 个设计支配 D4」与「取消 D4 资格的是遗漏率而非精度」两句都错**。9A 的正确表述是：**D4 既不可行（遗漏 0.3611 > 0.20），也被 5 个可行设计在 (A,B) 上支配**。

### 5. 元教训
1. **一个不可行的支配者 ≠ 没有可行的支配者**：D55 从**一次单设计探针**推出**全空间结论**，是又一次「结论超出测量范围」（同族：§8.29、§9 第 30 / 33 项）；
2. **报告的作用域必须落盘**：`front_scope` 就是这条纪律的代码形态 —— 今后任何「前沿 / 推荐点」都必须连同它一起读；
3. 报前沿必须覆盖整个候选空间 ⇒ **任何一次运行的耗时下限 ≈ `174 × 单次内环评估`**（`n_fim=1` 约 3.5–5 s ⇒ **10–15 min**），**与 `--budget` 无关**。

### 6. 校验证据
- `python -u 1_Code\\AutoRA_SPE\\_scratch_probe_d4_domination.py 1_Code\\AutoRA_SPE\\_scratch_payload_check.json` → exit 0，日志 `1_Code/AutoRA_SPE/_scratch_probe_d4_domination_cache_u8.txt`；
- `1_Code/AutoRA_SPE/_scratch_payload_check.json` 的 `cache` 段（174 项）与 `front_scope` 段；
- `1_Code/AutoRA_SPE/stage9_loop.py` 770 行（裸 LF、无 BOM、`ast=OK`）；探针已重写为**离线 / 即时双模式**。

### 7. 尚未做
1. 给 `1_Code/AutoRA_SPE/check_stage9_loop.py` 补一个新牙齿：断言「补全空间发生在算前沿之前」且 `front_scope.n_evaluated == front_scope.n_candidates`；
2. **全空间评估与四臂搜索分开计时**并写进报告，否则「10–15 min」这个下限会在正式跑里被误读成搜索成本。

"""

ITEM_39 = (
    "| 39 | ✅ **前沿与推荐点的作用域缺陷已修（D56，§8.31）** | "
    "`1_Code/AutoRA_SPE/stage9_loop.py` 749 → **770 行**：新增 `_jsonable()`（`inner_eval` 的 "
    "`se`/`se_sd`/`acc` 是 numpy 数组，`json.dumps` 直接抛 `TypeError`）与 payload 的 "
    "`\"cache\"`（逐设计读数 ⇒ 落盘件自足）、`\"front_scope\"`；**算前沿之前先调 "
    "`ev.feasible_names()` 补全整个候选空间**并打印 `[前沿] …`。**根因**：`pareto_front()` "
    "（L631 的 `for n in (names or list(ev.cache)):`）与 `best()` 只覆盖**已缓存**的点，而 "
    "`main()` 原先在补全空间**之前**调用它们 ⇒ 推荐点/前沿取决于 `--budget`"
    "（`--budget 12` 报 `A = 0.3881`，全空间真值 `A = 0.3446`）。❗❗ **并据此推翻 D55 的"
    "两条更正**：离线读 174 项 `cache`（可行 27 / 不可行 147）⇒ **可行集内有 5 个**设计在 "
    "(A,B) 上支配锚点 D4，最强者 `T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms × "
    "r16` 的 `A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`（**在冻结带内**），"
    "`ΔA = +0.0412` = 噪声带 `2·sd_A = 0.0050` 的 **8 倍** ⇒ D4「既不可行、也被可行设计支配」。"
    "⇒ 第 38 项里「取消 D4 资格的只有遗漏率带这一条，不是精度」**作废**。"
    "**遗传自**第 38 项与 `1_Code/AutoRA_SPE/_scratch_probe_d4_domination.py`（离线/即时双模式） |"
)

S9_ITEM_20 = (
    "20. ❗ **「前沿 / 推荐点」的作用域必须先钉住再读**：`pareto_front(ev)` 与 `ev.best(key)` "
    "都只遍历 **`ev.cache`**（`for n in (names or list(ev.cache)):`），而 `main()` 原先在调用 "
    "`ev.feasible_names()` **之前**就算前沿 ⇒ 报出的推荐点是**四臂抽到的那些点里最好的**，"
    "其好坏完全取决于 `--budget`，输出里看不出来。实测同一配置（`--n-fim 1 --noise-repeats 2 "
    "--seed 0`）：`--budget 12` 报 `A = 0.3881`；补全 174 个候选空间后最优可行设计是 "
    "`A = 0.3446`，且它**支配**锚点 D4（`ΔA = +0.0412` = 噪声带 `2·sd_A = 0.0050` 的 **8 倍**）。"
    "⇒ ① 代码已改为**算前沿前先补全空间**并打印 `[前沿] …`；② payload 落 "
    "`front_scope = {n_candidates, n_cached_before_full_eval, n_evaluated, n_front}`；"
    "③ **今后引用「前沿 / 推荐点」必须连同作用域一起报**。**代价**：报前沿的耗时下限 ≈ "
    "`174 × 单次内环评估`（`n_fim=1` 约 10–15 min），**与 `--budget` 无关**。"
)

S9_LOG_ROW = (
    "| 2026-10-14 | **前沿作用域缺陷 + 决策 D56**：给 `stage9_loop.main()` 的 payload 补上"
    "逐设计的 `\"cache\"`（经 `_jsonable()` 折算 numpy 数组/标量），用离线探针读全部 **174** "
    "个设计 ⇒ **推翻 D55 的两条更正**：**可行集内有 5 个**设计在 (A,B) 上支配锚点 D4"
    "（最强者 `A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`，`ΔA = +0.0412` = 噪声带 0.0050 的 "
    "**8 倍**）。**根因**：`pareto_front()` 与 `best()` 只遍历 `ev.cache`，而 `main()` 在 "
    "`ev.feasible_names()` 之前调用它们 ⇒ 推荐点/前沿取决于 `--budget`"
    "（`--budget 12` 报 0.3881，全空间真值 0.3446）。**修法**：算前沿前先补全空间 + payload "
    "落 `front_scope`；`stage9_loop.py` 749 → **770 行**。§11 新增第 20 条 | "
    "`1_Code/AutoRA_SPE/_scratch_probe_d4_domination_cache_u8.txt`（exit 0）；"
    "`1_Code/AutoRA_SPE/_scratch_payload_check.json`（174 项 `cache` + `front_scope`）；"
    "`1_Code/AutoRA_SPE/stage9_loop.py`（770 行）；主计划 D56；"
    "`1_Code/DDM_Core/README.md` §8.31、§9 第 39 项 |"
)

# 就地更正（行前缀 + 追加后缀）
CORRECTIONS = [
    (RM, "| 38 | 🛑 **事前登记的遗漏率带与已定稿的锚点 D4 不相容（D55，需拍板）** |",
     " ❌ **2026-10-14 更正（见 D56 / §8.31）**：本条末尾「取消 D4 资格的**只有**遗漏率带这一条、"
     "不是精度」**作废**。离线读全部 174 个设计的 `cache` 后：**可行集内有 5 个**设计在 (A,B) 上"
     "支配 D4，最强者 `T[33.33/149.99/349.99]ms × W[1199.90/1799.90/2399.80]ms × r16` 的 "
     "`A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`（**在冻结带内**）⇒ `ΔA = +0.0412` = 噪声带 "
     "`2·sd_A = 0.0050` 的 **8 倍**。D55 那句「`ΔA = −0.0023` 落在噪声带内」比较的是**推荐点**"
     "（当时只是四臂抽样点里的最优，`A = 0.3881`），不是空间最优。⇒ 正确表述是："
     "**D4 既不可行（0.3611 > 0.20），也被 5 个可行设计在 (A,B) 上支配**。",
     "见 D56"),
    (RM, "| 37 | ✅ **D54 已落到代码：遗漏率罚分 → 可行域约束**",
     " ⚠️ **2026-10-14 补注（见 D56 / §8.31）**：本项里的「推荐点 `A = 0.3881`」是**四臂抽样点"
     "里的最优**（当时前沿/推荐点只在 `ev.cache` 上算），**不是整个候选空间的最优**；补全 174 "
     "个候选后空间最优可行设计为 `A = 0.3446`。今后引用推荐点必须连同 `front_scope` 一起报。",
     "见 D56"),
]

# 插入（锚点前缀 → 要插进去的行；表中行会断言竖线数与锚点一致）
INSERTS_BEFORE = [
    (RM, "## 9. 尚未做", SECTION.rstrip("\n").split("\n")),
]
INSERTS_AFTER = [
    (S9, "19. ❗ **`(A)` 依赖 `n_fim`，必须连着 `n_fim` 一起报**", [S9_ITEM_20]),
    (S9, "| 2026-10-14 | ❗ **更正 §11 第 15 条里", [S9_LOG_ROW]),
    (RM, "| 38 | 🛑 **事前登记的遗漏率带与已定稿的锚点 D4 不相容（D55，需拍板）** |", [ITEM_39]),
]


def n_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    if "## 8.31 " in RM.read_text(encoding="utf-8"):
        print("❌ README 已含 `## 8.31 `（幂等守卫）")
        return 2

    files = {RM: RM.read_text(encoding="utf-8"), S9: S9.read_text(encoding="utf-8")}
    for p, t in files.items():
        if not t.endswith("\n"):
            print(f"❌ {p} 不以换行结尾")
            return 2
    lines = {p: t[:-1].split("\n") for p, t in files.items()}

    # 1) 就地更正
    for path, prefix, suffix, guard in CORRECTIONS:
        ls = lines[path]
        hits = [i for i, s in enumerate(ls) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 更正锚点 {prefix[:44]!r}（{path.name}）命中 {len(hits)} 次")
            return 2
        i = hits[0]
        if guard in ls[i]:
            print(f"❌ {path.name} L{i + 1} 已含「{guard}」，拒绝重复追加")
            return 2
        new = ls[i].rstrip()[:-1].rstrip() + suffix + " |"
        if n_sep(new) != n_sep(ls[i]):
            print(f"❌ {path.name} L{i + 1} 竖线数变化 {n_sep(ls[i])} → {n_sep(new)}")
            return 2
        ls[i] = new
        print(f"✅ 就地更正：{path.name} L{i + 1}（竖线数不变 = {n_sep(new)}）")

    # 2) 段/行插入
    for path, prefix, block in INSERTS_BEFORE:
        ls = lines[path]
        hits = [i for i, s in enumerate(ls) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 插入锚点 {prefix[:44]!r}（{path.name}）命中 {len(hits)} 次")
            return 2
        i = hits[0]
        ls[i:i] = block
        print(f"✅ 插入 {len(block)} 行段：{path.name} L{i + 1}–L{i + len(block)}")

    for path, prefix, block in INSERTS_AFTER:
        ls = lines[path]
        hits = [i for i, s in enumerate(ls) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 插入锚点 {prefix[:44]!r}（{path.name}）命中 {len(hits)} 次")
            return 2
        i = hits[0]
        for k, row in enumerate(block):
            if row.lstrip().startswith("|") and n_sep(ls[i]) != n_sep(row):
                print(f"❌ {path.name} L{i + 1} 竖线数不一致：锚点 {n_sep(ls[i])}、"
                      f"新行 {n_sep(row)}")
                return 2
            ls.insert(i + 1 + k, row)
        print(f"✅ 插入 {len(block)} 行：{path.name} L{i + 2}–L{i + 1 + len(block)}")

    # 3) 断表断言
    for path, ls in lines.items():
        for i in range(1, len(ls) - 1):
            if not ls[i].strip():
                if (ls[i - 1].lstrip().startswith("|") and n_sep(ls[i - 1]) >= 2
                        and ls[i + 1].lstrip().startswith("|") and n_sep(ls[i + 1]) >= 2):
                    print(f"❌ 断表：{path.name} L{i + 1}")
                    return 2

    for path, ls in lines.items():
        out = "\n".join(ls) + "\n"
        if apply:
            path.write_text(out, encoding="utf-8", newline="\n")
            print(f"✍️ 已写回：{path}（{len(ls)} 行）")
        else:
            print(f"（干跑）将写回 {path}（{len(ls)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
