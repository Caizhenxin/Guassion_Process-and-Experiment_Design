"""把决策 D52 写进 `5_Reference/08_工作流/工作流_主计划.md`（四处插入 + 两处就地更正）。

体例照 `_apply_d47/48/49/50/51.py`：按**前缀/子串**定位再插入，每处都先量锚点行的
分隔符个数再断言新行相等；摘除表格末行之后的空行再连续插入；插入后做断表断言；
带幂等守卫。

为什么用脚本而不是 `edit`：主计划的表格行是**数千字符的单行**，`edit` 必须一字不差
匹配行尾（含可能的尾随空格）；前缀定位不依赖行尾形状。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MASTER = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "工作流_主计划.md"

DECISION_ANCHOR = "| **D51** | 2026-10-14 |"
DECISION_ROW = (
    "| **D52** | 2026-10-14 | ✅ **LOO 可用性必须同时看 `p_loo`：`max k` 单独没有分辨力**。"
    "判据改为「理由清单」：`max k` 非有限 / `n_failed ≥ n_obs` / **`p_loo` 不在 `[0, n_obs]`** "
    "任一条成立即判「⛔ 本组 LOO 无效」，不得引用 `ELPD`/`ΔELPD`；报告行**必须**打印 `p_loo` "
    "与 **`p_loo`/`n_obs` 这个比值** | "
    "① 4 人 analytic 端到端干跑（`--n-x 31 --n-draws 32`）的 M-T1 给出 `max k = 0.000`、"
    "`n_failed = 0`、`越界 0/4` ⇒ **两条既有判据 + `Stage8_建模与验证方案.md` §8 的三档事前登记规则"
    "（全部以 `max k` 为键）会把它判成「可用」**；② 而同一行的 `p_loo = 2816.26` 对 **`n_obs = 4`** "
    "⇒ **有效参数数是观测数的 704 倍**，结构性崩坏；③ **为什么 `n_obs = 4` 而不是 756**："
    "`1_Code/DDM_Core/hier.py:494 loo_matrix` 返回 `(S, N)`（每个抽取 × 每个被试的边际对数似然），"
    "`1_Code/DDM_Core/loo.py:238` 的 `n_obs = N` 是列数 ⇒ 本项目 LOO 单位 = **被试**"
    "（`hier.loo_bruteforce` docstring 明写「主计划要求 LOO 单位 = 被试」）；"
    "④ **为什么 `max k = 0.000` 不是健康证明**：同一个 0.000 在**健康**矩阵上也会出现"
    "（实测 `rng.normal(-3.0, 0.3, size=(30, 3))` 的另一次抽样：`p_loo = 0.222`、`max k = 0.000`）"
    "⇒ 0 既可能是「权重近似均匀」也可能是「权重彻底退化」，**它没有分辨力**；"
    "⑤ **这个洞是 N=4 才暴露的**：N=2 的旧干跑 `p_loo` = −706.37 / −2900.54，"
    "但那一档 `n_failed = 2 = n_obs`，被旧判据拦住了 | "
    "① `1_Code/DDM_Core/stage8_run.py::render_group` 的判据改为收集理由清单并打印 "
    "`p_loo`/`n_obs`；② `5_Reference/08_工作流/Stage8_建模与验证方案.md` §8 顶部加一行"
    "「`p_loo` 不在 `[0, n_obs]` ⇒ 本组 LOO 无效」+ 一条 D52 说明块，§11 加第 9、10 条已知限制，"
    "§12 记 v1.1；③ 自测 `_scratch/check_stage8_run.py` **15 → 18 项**（新增 A7c/A7d 两颗牙齿 + "
    "A7e 反向对照）；④ **凡报出 LOO 结果的表格，必须同时报 `p_loo`、`n_obs` 与 `p_loo`/`n_obs`**，"
    "只报 `max k` 与 `n_k_gt_bad` 的表格**不得**用来支持模型比较 |"
)

PROGRESS_ANCHOR = "| 2026-10-14 | **8**（退化记账 + `_numdiff` 根因 → D51） |"
PROGRESS_ROW = (
    "| 2026-10-14 | **8/9**（N=4 干跑判读 → D52） | "
    "**把长期挂着的 4 人 analytic 端到端干跑判读到底，结果发现事前登记的模型比较规则有一个洞**。"
    "① M-T1 完成 **4501.7 s（75 min，远超 0.67 h 的投影**，因为我同时在跑两个探针抢 CPU）："
    "`ELPD −3526.254 ± 32.997`、`p_loo 2816.26`、`k_max 0.000`、越界 0/4、不可用 0、失败 0、非有限 0；"
    "M-T3 在范围结束时仍在跑；② `_numdiff` 警告在 M-T1 开始处**如期出现**（`--n-x 31`，与 D51 一致）；"
    "③ ⚠️ **投影行有一处标注不准**：`project()` 打印「实测标定：48 试次/人、`n_x=41`、单次似然 34 ms」，"
    "而本次跑的是 `--n-x 31` ⇒ **标定网格与实际运行网格不是同一个数**（又一次「报范围必须连同它的"
    "适用网格一起报」）；④ ❗ **`k_max = 0.000` 是假阴性**：`n_obs = 4`（LOO 单位 = 被试，"
    "见 `hier.loo_matrix` 的 `(S, N)` 与 `loo.psis_loo` 的 `n_obs = N`），"
    "`p_loo/n_obs = 704` ⇒ 被判成「可用」；⑤ 已修 `stage8_run.render_group` 并把判据写进 "
    "Stage 8 §8（新增 `p_loo` 闸门），自测升到 **18/18** | "
    "`1_Code/DDM_Core/stage8_run.py`（修改）、`1_Code/DDM_Core/_scratch/check_stage8_run.py`"
    "（升为 18/18：新增 A7c/A7d/A7e）、`5_Reference/08_工作流/Stage8_建模与验证方案.md`（§8 + §11 + §12）、"
    "`1_Code/DDM_Core/README.md`（§8.28 + §9 第 33 项）、日志 "
    "`1_Code/DDM_Core/_scratch/stage8_run_an4_u8.txt` 与 "
    "`1_Code/DDM_Core/_scratch/check_stage8_run_d52_u8.txt` | "
    "🔨 **仍开放**：**(1)** 正式规模（~40 人/组）上 `p_loo`/`n_obs` 的实际取值范围——需要真实数据，"
    "届时 `[0, n_obs]` 这条界要不要收紧（例如再加「`p_loo`/`n_obs` 应远小于 1」）由实测决定；"
    "**(2)** `n_draws` 与 `N` 对 `p_loo`/`n_obs` 的联合影响（这一档 `n_draws = 32`、`N = 4`）；"
    "**(3)** M-T3 的同一档结果（干跑仍在跑）；**(4)** Stage 9 剩余文件 "
    "`stage9_loop.py` / `check_stage9.py` / `stage9_report.md` |"
)

CHANGELOG_ANCHOR = "| 2026-10-14 | **新增 D51：退化必须逐项显式记账"
CHANGELOG_ROW = (
    "| 2026-10-14 | **新增 D52：LOO 可用性必须同时看 `p_loo`（`max k` 单独没有分辨力）**。"
    "① 4 人 analytic 干跑的 M-T1 给出 `max k = 0.000`、`n_failed = 0`、越界 0/4 ——"
    "按当时判据与 `Stage8_建模与验证方案.md` §8 的三档事前登记规则会被判成**可用**，"
    "而 `p_loo = 2816.26` 对 `n_obs = 4`（LOO 单位 = 被试）⇒ 有效参数数是观测数的 **704 倍**；"
    "② **为什么 `k_max = 0.000` 不是健康证明**：同一个 0.000 在健康矩阵上也会出现"
    "（实测 `p_loo = 0.222`、`max k = 0.000`）⇒ 0 既可能是「权重近似均匀」也可能是「权重彻底退化」；"
    "③ **洞是 N=4 才暴露的**（N=2 被 `n_failed = n_obs` 拦住）；"
    "④ 判据改为理由清单（`max k` 非有限 / `n_failed ≥ n_obs` / `p_loo ∉ [0, n_obs]`），"
    "报告行强制打印 `p_loo`/`n_obs`；⑤ 自测 **15 → 18 项**（A7c/A7d 两颗牙齿 + A7e 反向对照） |"
)

APPENDIX_ANCHOR = "| `1_Code/DDM_Core/hier.py`（修改，+182/−12 行）"
APPENDIX_ROW = (
    "| `1_Code/DDM_Core/stage8_run.py`（修改：`render_group` 的判据）+ "
    "`1_Code/DDM_Core/_scratch/check_stage8_run.py`（**升为 18/18、exit 0**） | "
    "**D52 的一手证据（`max k` 没有分辨力）**。① **触发实例**：4 人 analytic 干跑 M-T1 "
    "`ELPD −3526.254 ± 32.997；p_loo 2816.26；k_max 0.000；越界 0/4；不可用 0；失败 0；非有限 0`"
    "（`1_Code/DDM_Core/_scratch/stage8_run_an4_u8.txt`，4501.7 s）；② **`n_obs` 的语义**："
    "`1_Code/DDM_Core/hier.py:494 loo_matrix` 返回 `(S, N)`、`1_Code/DDM_Core/loo.py:238` 的 "
    "`n_obs = int(N)` 是列数 ⇒ `n_obs = 4`（被试数），不是 756（试次数）；"
    "③ **`max k = 0.000` 的不可分辨性实测**：`rng.normal(-3.0, 0.3, size=(30, 3))` 的另一抽样给出 "
    "`p_loo = 0.222`、`max k = 0.000`、`ELPD = −9.183`（健康），而同分布 `sd = 0.001` 时 "
    "`p_loo = 2.42e−06`、`max k = 0.000`、`ELPD = −9.000` ⇒ 0 出现于两种完全不同的状态；"
    "④ **反向实例（N=2）**：`1_Code/DDM_Core/_scratch/_s8run_an/stage8_results.json` 实测 "
    "`n_obs = 2`、`p_loo = −706.37`（M-T1）/ `−2900.54`（M-T3）、`k_max = nan`、`n_failed = 2` "
    "⇒ 这一档被 `n_failed ≥ n_obs` 拦住，**所以洞只在 N=4 暴露**；"
    "⑤ **新增三颗牙齿**：A7c（`max k = 0` + `n_failed = 0` + `p_loo`/`n_obs = 704` ⇒ 必须报「LOO 无效」）、"
    "A7d（负 `p_loo` = −353.0 ⇒ 必须报）、A7e（反向对照：`0 < p_loo`/`n_obs < 1` 时**不得**误伤，"
    "仍须给「可报 ΔELPD」）⇒ `共 18 项，未通过 0 项`，日志 "
    "`1_Code/DDM_Core/_scratch/check_stage8_run_d52_u8.txt` |"
)

# 就地更正：过期数字（项目规矩「忘记同步数字」的防法）
FIXES = [
    ("`1_Code/DDM_Core/_scratch/check_stage8_run.py`（新建，**15/15、exit 0**）",
     "`1_Code/DDM_Core/_scratch/check_stage8_run.py`（新建；**D46 时 15/15 → D52 后 18/18**、exit 0）"),
    ("`1_Code/DDM_Core/_scratch/check_stage8_run.py`（**升为 15/15**）",
     "`1_Code/DDM_Core/_scratch/check_stage8_run.py`（**D47 升为 15/15 → D52 升为 18/18**）"),
]


def n_sep(line: str) -> int:
    return line.count("|") - line.count("\\|")


def find_one(lines: list[str], prefix: str) -> int:
    hits = [i for i, t in enumerate(lines) if t.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ 锚点 {prefix[:40]!r} 命中 {len(hits)} 次（期望 1）")
    return hits[0]


def insert_after(lines: list[str], anchor_prefix: str, row: str, want_sep: int) -> None:
    """在锚点行之后插入一行。

    ❗ **踩过的坑**：第一版照抄 `_apply_d47`–`_apply_d51` 里"摘除锚点之后的所有空行再插入"
    的逻辑。那个逻辑是为**一次连续追加多行**设计的（若不摘，第 2 行会被插到空行之后 ⇒
    `split_rows`）。本轮每个锚点**只插一行**，于是它把表格与 `---` 之间的空行吃掉了 3 处、
    还吃掉了文件末尾的换行 ⇒ 用 `_fix_d52_blanks.py` 补回。**插一行时不要碰空行。**
    """
    i = find_one(lines, anchor_prefix)
    if n_sep(lines[i]) != want_sep:
        raise SystemExit(f"❌ 锚点 {anchor_prefix[:30]!r} 分隔符 {n_sep(lines[i])} ≠ {want_sep}")
    if n_sep(row) != want_sep:
        raise SystemExit(f"❌ 新行分隔符 {n_sep(row)} ≠ {want_sep}（表格里出现裸 `|`？）")
    lines.insert(i + 1, row)


def main() -> int:
    text = MASTER.read_text(encoding="utf-8")
    lines = text.split("\n")
    if any(t.startswith("| **D52** |") for t in lines):
        raise SystemExit("❌ 幂等守卫：已存在 `| **D52** |`，拒绝写回")
    n0 = len(text.splitlines())

    insert_after(lines, DECISION_ANCHOR, DECISION_ROW, 6)
    insert_after(lines, PROGRESS_ANCHOR, PROGRESS_ROW, 6)
    insert_after(lines, CHANGELOG_ANCHOR, CHANGELOG_ROW, 3)
    insert_after(lines, APPENDIX_ANCHOR, APPENDIX_ROW, 3)

    # 断表断言：新行前后不能出现「空行夹在两条表格行之间」
    for k, t in enumerate(lines):
        if t.strip() == "" and 0 < k < len(lines) - 1:
            if lines[k - 1].startswith("|") and lines[k + 1].startswith("|"):
                raise SystemExit(f"❌ 断表断言失败：L{k + 1} 是夹在两行表格之间的空行")

    n_fix = 0
    for old, new in FIXES:
        if old not in text:
            raise SystemExit(f"❌ 就地更正找不到目标：{old[:60]!r}")
        if new in text:
            raise SystemExit(f"❌ 就地更正已是目标状态：{new[:60]!r}")
        n_fix += sum(1 for t in lines if old in t)
        lines = [t.replace(old, new) for t in lines]
    if n_fix == 0:
        raise SystemExit("❌ 就地更正一处也没命中")

    out = "\n".join(lines)
    if not out.endswith("\n"):
        raise SystemExit("❌ 输出不以换行结尾（空行被误摘过？），拒绝写回")
    MASTER.write_text(out, encoding="utf-8", newline="")
    print(f"✅ D52 已写入 {MASTER}")
    print(f"   行数 {n0} → {len(out.splitlines())}；就地更正 {n_fix} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
