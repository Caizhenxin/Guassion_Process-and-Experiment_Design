# -*- coding: utf-8 -*-
"""D56 第四批落纸：把「全空间冒烟」（后台作业 pwsh-170）的一手读数写进文档。

一手读数（`1_Code/AutoRA_SPE/_scratch_smoke_scope_u8.txt` + `_scratch_smoke_scope.json`，
`--budget 2 --n-fim 1 --noise-repeats 2 --seed 0`，exit 0、内环 762 s / 墙钟 771 s、
`n_evals = 176`、`cache = 174`）：
- `[前沿] 先补全候选空间（缓存里现有 7 个，候选共 174 个）` → `[前沿] 全空间评估完毕：缓存 174 个、累计 176 次内环评估、762s`；
- **推荐点从 `A = 0.3881`（`--budget 12` 的抽样最优）变成 `A = 0.3446 / B = 8.6729 / 遗漏 0.1910`**，
  与离线探针的可行集最小点（`0.344643…`）一致；锚点 D4 `A = 0.3858` ⇒ `ΔA = 0.0412`（噪声带 0.0050 的 8 倍）；
- `front_scope = {n_candidates: 174, n_cached_before_full_eval: 7, n_evaluated: 174, n_front: 6}`
  ⇒ **`n_evaluated == n_candidates` 为真**（H1 的诚实边界由这次实跑补上）；
- ❗ **同一缺陷的另一个受害者**：payload `d54.n_band_rejected` 这次是 **93**，而 D55 那次
  `--budget 12` 报的是 **22** —— 因为 `n_band` 原先也在**补全空间之前**统计。全空间真值 = **93**。
- ❗ **新读数（不是我事先预期的）**：174 个候选里 **27 可行 / 24 只被 D54 带否决 / 123 数值病态**
  （`cond > 1e10`、相关矩阵不可逆 + 有坏试次；其中 69 个同时落在带外）。⇒ 在 **`n_fim = 1`** 下，
  **70.7%（123/174）的候选是被数值条件数刷掉的，不是被遗漏率带刷掉的**。⚠️ 这个比例**是 `n_fim = 1`
  的读数**，必须在正式 `n_fim` 下重测（`n_fim = 12` 时 D4 的 `(A)` 已从 0.3858 降到 0.268，
  提示条件数随 `n_fim` 改善）。

体例：锚行前缀定位 + `n_inline_sep()` 断言 + 幂等守卫。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d56c.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d56c.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RM = Path("1_Code/DDM_Core/README.md")
MP = Path("5_Reference/08_工作流/工作流_主计划.md")
S9 = Path("5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md")

SMOKE = "`1_Code/AutoRA_SPE/_scratch_smoke_scope_u8.txt`（exit 0、内环 762 s / 墙钟 771 s、`n_evals = 176`、`cache = 174`）"

EV_BULLETS = [
    f"- **全空间冒烟（后台作业 pwsh-170，验证本节的修法）**：{SMOKE} + JSON "
    "`1_Code/AutoRA_SPE/_scratch_smoke_scope.json`。打印 `[前沿] 先补全候选空间（缓存里现有 7 个，"
    "候选共 174 个）` → `[前沿] 全空间评估完毕：缓存 174 个、累计 176 次内环评估、762s`。",
    "- **推荐点确实被修好了**：同一个脚本、同一套设置，`--budget 12` 时报 `A = 0.3881`，"
    "这次全空间报 **`A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`**，与离线探针的可行集最小点"
    "（`0.344643…`）一致；锚点 D4 `A = 0.3858` ⇒ `ΔA = 0.0412`（噪声带 `2·sd_A = 0.0050` 的 8 倍）。",
    "- **H1 的诚实边界已被补上**：`front_scope = {n_candidates: 174, "
    "n_cached_before_full_eval: 7, n_evaluated: 174, n_front: 6}` ⇒ "
    "**`n_evaluated == n_candidates` 为真**（H1 只钉源码顺序，这条等式原先没人验证过）。",
]

# 新增小节 §8.31 第 8 节（插在「### 7. 尚未做」之前）
NEW_SEC = [
    "### 8. 同一缺陷的另一个受害者：`n_band = 22` 也是部分空间的读数（全空间真值 93）",
    "",
    "`1_Code/AutoRA_SPE/stage9_loop.py` 里 `n_band` 原先与 `pareto_front()` 同批计算（都在",
    "`ev.feasible_names()` **之前**），所以 D55 那次 `--budget 12` 报的「带外 22 个」只在 49 个",
    "已评估点上成立。全空间冒烟（pwsh-170）把 174 个候选都算完后，payload 的",
    "`d54.n_band_rejected` 是 **93**。",
    "",
    "❗ **新读数（不是事先预期的）**：把 174 个候选按闸门归类 ——",
    "",
    "| 类别 | 个数 | 判据 |",
    "|---|---|---|",
    "| 可行 | 27 | 遗漏率在冻结带 `[0.05, 0.20]` 内、`cond ≤ 1e10`、无坏试次 |",
    "| 只被 D54 带否决 | 24 | 遗漏率带外，数值健康 |",
    "| **数值病态** | **123** | `cond > 1e10`（相关矩阵不可逆）+ 有坏试次；其中 69 个同时落在带外 |",
    "",
    "⇒ 在 **`n_fim = 1`** 下，**70.7%（123/174）的候选是被数值条件数刷掉的，不是被遗漏率带刷掉的**。",
    "⚠️ **这个比例是 `n_fim = 1` 的读数**，必须在正式 `n_fim` 下重测：同一设计 D4 的 `(A)` 在",
    "`n_fim = 1 / 2 / 12` 下是 `0.3858 / 0.3519 / 0.268`，提示条件数随 `n_fim` 改善，",
    "而「哪些设计可行」也会随之变化 ⇒ **不要把这个 70.7% 当成设计空间的固有属性**。",
    "",
    "**元教训（与第 5 节同一类）**：凡是从 `ev.cache` 现算的**计数**（`n_band`、`n_feasible`、",
    "`n_front`、`best`）都隐含一个作用域。作用域没落盘的计数，事后无法判断它对不对 ——",
    "这次是两个数字里**一个对、一个错**（`n_feas = 27` 碰巧是在补全空间之后算的，",
    "`n_band = 22` 不是）。",
    "",
]

REPLACEMENTS = [
    # ② §8.31 §7 第 1 条：牙齿已补
    (RM,
     "1. 给 `1_Code/AutoRA_SPE/check_stage9_loop.py` 补一个新牙齿：断言「补全空间发生在算前沿之前」"
     "且 `front_scope.n_evaluated == front_scope.n_candidates`；",
     "1. ~~给 `1_Code/AutoRA_SPE/check_stage9_loop.py` 补一个新牙齿~~ ✅ **已完成（D56 当轮）**："
     "`check_stage9_loop.py` 261 → **374 行**，新增 **H 组**三条**静态源码判据**（`H1` `main()` 里 "
     "`ev.feasible_names()` 必须早于 `pareto_front(ev)` 与 `ev.best(\"A\")`；`H2` payload 有 "
     "`\"front_scope\"` 且四键齐全；`H3` `\"cache\"` 段存在且经 `_jsonable()`）⇒ "
     "**31/31、exit 0、63.0 s**。⚠️ **边界**：H1 钉的是**源码顺序**，运行期的 "
     "`front_scope.n_evaluated == front_scope.n_candidates` 由**全空间冒烟**（见第 6 节）覆盖，"
     "自测里没有（那要跑 13 分钟）；",
    ),
    # ③ §8.31 §7：新增第 3 条
    (RM,
     "2. **全空间评估与四臂搜索分开计时**并写进报告，否则「10–15 min」这个下限会在正式跑里被误读成搜索成本。",
     "2. **全空间评估与四臂搜索分开计时**并写进报告，否则「10–15 min」这个下限会在正式跑里被误读成搜索成本；\n"
     "3. ⚠️ 在**正式 `n_fim`** 下重测「可行集是怎么构成的」（第 8 节那三类的比例），并据此决定"
     "「数值病态」是设计空间的性质、还是 `n_fim = 1` 这个大 SE 的产物。",
    ),
]

# ④ §9 新增第 40 项（插在 `| 39 |` 行之后）
ROW40 = (
    "| 40 | ✅ **「先补全候选空间再算前沿」已被一次全空间实跑验证（D56，§8.31 §6/§8）** | "
    "后台作业 pwsh-170：`--budget 2 --n-fim 1 --noise-repeats 2 --seed 0`，"
    f"{SMOKE}，JSON `1_Code/AutoRA_SPE/_scratch_smoke_scope.json`。"
    "**推荐点**：`--budget 12` 报的 `A = 0.3881` → 全空间 **`A = 0.3446 / B = 8.6729 / 遗漏 = 0.1910`**"
    "（与离线探针一致）；锚点 D4 `A = 0.3858` ⇒ `ΔA = 0.0412`；`front_scope = "
    "{n_candidates: 174, n_cached_before_full_eval: 7, n_evaluated: 174, n_front: 6}` ⇒ "
    "`n_evaluated == n_candidates` **为真**。❗ **并发现同一缺陷的另一个受害者**："
    "`d54.n_band_rejected` 全空间真值是 **93**（D55 那次报的 **22** 同样是部分空间读数）。"
    "❗ **新读数**：174 个候选 = **27 可行 / 24 只被 D54 带否决 / 123 数值病态**"
    "（`cond > 1e10` + 坏试次，其中 69 个同时带外）⇒ **`n_fim = 1` 下 70.7% 的候选是被条件数刷掉的**；"
    "⚠️ 该比例须在正式 `n_fim` 下重测（D4 的 `(A)` 随 `n_fim = 1/2/12` 为 `0.3858/0.3519/0.268`） "
    "证据：`1_Code/AutoRA_SPE/_scratch_smoke_scope_u8.txt`、`1_Code/AutoRA_SPE/_scratch_smoke_scope.json`；"
    "§8.31 §8；遗传自第 39 项 |"
)

# ⑤ 主计划 D56 进度行追加验证
MP_ANCHOR = "后台作业 pwsh-170（验证修法） |"
MP_TAIL = (
    " ❗ **2026-10-14 已验证（pwsh-170，exit 0、内环 762 s）**：终端打印 `[前沿] 先补全候选空间"
    "（缓存里现有 7 个，候选共 174 个）` → `[前沿] 全空间评估完毕：缓存 174 个、累计 176 次内环评估、762s`；"
    "**推荐点 `A = 0.3881` → `0.3446`**（`B = 8.6729`、遗漏 `0.1910`，与离线探针一致），"
    "锚点 D4 `ΔA = 0.0412`；`front_scope.n_evaluated == n_candidates`（174 = 174）**为真**。"
    "❕ **顺带发现同一缺陷的另一个受害者**：`d54.n_band_rejected` 全空间真值 **93**（那次报的 22 是部分空间读数）；"
    "且 **174 个候选 = 27 可行 / 24 只被带否决 / 123 数值病态（`cond > 1e10`）** ⇒ `n_fim = 1` 下 "
    "**70.7% 是条件数刷掉的**，须在正式 `n_fim` 下重测。 |"
)

# ⑥ Stage 9 §12 的 D56 行证据列追加验证
S9_ANCHOR = "`1_Code/AutoRA_SPE/stage9_loop.py`（787 行）；主计划 D56；`1_Code/DDM_Core/README.md` §8.31、§9 第 39 项 |"
S9_TAIL = (
    " ❗ **已验证（pwsh-170 全空间冒烟，exit 0、内环 762 s）**：推荐点 `A = 0.3881` → **`0.3446`**"
    "（`B = 8.6729`、遗漏 `0.1910`）、锚点 `ΔA = 0.0412`、`n_evaluated == n_candidates`（174 = 174）**为真**；"
    "❗ 同一缺陷的另一个受害者：`n_band_rejected` 全空间 **93**（那次报 22）；❗ 新读数："
    "**27 可行 / 24 只被带否决 / 123 数值病态**（`cond > 1e10`）⇒ `n_fim = 1` 下 70.7% 被条件数刷掉，"
    "须在正式 `n_fim` 下重测 |"
)


def n_inline_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    text0 = {p: p.read_text(encoding="utf-8") for p in (RM, MP, S9)}
    if "n_band_rejected` 全空间真值" in text0[RM]:
        print("❌ README 已含本次验证（幂等守卫）")
        return 2
    lines = {p: t[:-1].split("\n") for p, t in text0.items()}
    for p, t in text0.items():
        if not t.endswith("\n"):
            print(f"❌ {p} 不以换行结尾")
            return 2

    # ① 子串替换（每条必须命中且仅命中一次；整行竖线数不变）
    for path, old, new in REPLACEMENTS:
        ls = lines[path]
        hits = [i for i, s in enumerate(ls) if old in s]
        if len(hits) != 1:
            print(f"❌ {path.name}：锚文本命中 {len(hits)} 行（期望 1）\n   {old[:70]!r}")
            return 2
        i = hits[0]
        out = ls[i].replace(old, new)
        if n_inline_sep(out) != n_inline_sep(ls[i]):
            print(f"❌ {path.name} L{i + 1} 竖线数变化 {n_inline_sep(ls[i])} → {n_inline_sep(out)}")
            return 2
        ls[i] = out
        print(f"✅ {path.name} L{i + 1}：更新（竖线数不变 = {n_inline_sep(out)}）")

    # ① §8.31 §6 校验证据：三条实测插在 §8.31 的「### 7. 尚未做」**之前**
    #    ⚠️ `### 7. 尚未做` 在 README 里有 4 处（各节都有自己的第 7 小节）⇒
    #    锚点必须带上**下一行**才唯一（第一版只按标题定位，命中 4 行被拦）。
    ls = lines[RM]
    hits = [i for i, s in enumerate(ls)
            if s.strip() == "### 7. 尚未做" and i + 1 < len(ls) and "补一个新牙齿" in ls[i + 1]]
    if len(hits) != 1:
        print(f"❌ README §8.31 的「### 7. 尚未做」命中 {len(hits)} 处（期望 1）")
        return 2
    i = hits[0]
    ls[i:i] = EV_BULLETS + [""]
    print(f"✅ README §8.31 §6 追加 {len(EV_BULLETS)} 条校验证据（L{i + 1} 之前）")

    # ⑧ §8.31 新增第 8 节：插在顶层「## 9. 尚未做」**之前**（即 §8.31 §7 之后）
    hits = [i for i, s in enumerate(ls) if s.strip() == "## 9. 尚未做"]
    if len(hits) != 1:
        print(f"❌ README 顶层「## 9. 尚未做」命中 {len(hits)} 处（期望 1）")
        return 2
    j = hits[0]
    ls[j:j] = NEW_SEC
    print(f"✅ README §8.31 新增第 8 节（{len(NEW_SEC)} 行，插在 L{j + 1} 之前）")

    # ④ README §9 插入第 40 项
    ls = lines[RM]
    hits = [i for i, s in enumerate(ls) if s.startswith("| 39 | ✅ **前沿与推荐点的作用域缺陷已修")]
    if len(hits) != 1:
        print(f"❌ README §9 第 39 项命中 {len(hits)} 行")
        return 2
    i = hits[0]
    if n_inline_sep(ROW40) != n_inline_sep(ls[i]):
        print(f"❌ 第 40 项竖线数 {n_inline_sep(ROW40)} ≠ 第 39 项 {n_inline_sep(ls[i])}")
        return 2
    ls[i + 1:i + 1] = [ROW40]
    print(f"✅ README §9 插入第 40 项（L{i + 2}，竖线数 = {n_inline_sep(ROW40)}）")

    # ⑤⑥ 主计划 / Stage9 的证据列追加（行末闭合竖线之前）
    for path, anchor, tail in ((MP, MP_ANCHOR, MP_TAIL), (S9, S9_ANCHOR, S9_TAIL)):
        ls = lines[path]
        hits = [i for i, s in enumerate(ls) if anchor in s]
        if len(hits) != 1:
            print(f"❌ {path.name}：证据锚命中 {len(hits)} 行（期望 1）\n   {anchor[:60]!r}")
            return 2
        i = hits[0]
        new = ls[i].rstrip()[:-1].rstrip() + tail
        if n_inline_sep(new) != n_inline_sep(ls[i]):
            print(f"❌ {path.name} L{i + 1} 竖线数变化 {n_inline_sep(ls[i])} → {n_inline_sep(new)}")
            return 2
        ls[i] = new
        print(f"✅ {path.name} L{i + 1}：证据列追加（竖线数不变 = {n_inline_sep(new)}）")

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
