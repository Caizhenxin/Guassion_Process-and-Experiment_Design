# -*- coding: utf-8 -*-
"""D73 落纸：被试层 PSIS-LOO 结构性不可估 ⇒ PSIS 放试次层、被试层留一用 bruteforce/K-fold。

用法：python -X utf8 -u _apply_d73.py [--apply]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

DECISION = (
    "| **D73** | 2026-10-17 | ✅ **被试层 PSIS-LOO 结构性不可估 ⇒ PSIS 放试次层，被试层留一改用 bruteforce / "
    "K-fold**。① 现象：D70 正向对照（3 人 × 96 试次、S=30）给出 `elpd_loo = −1642.940 ± 588.064`、"
    "`p_loo = 1489.098`（`p_loo/n_obs = 496`）、`k_max = 5.000`；`_s8run_an`（2 人）甚至出现**负 p_loo**"
    "（−706.371 / −2900.542）。负 p_loo 只可能来自 PSIS 权重病态，不是「模型太复杂」。② 机理："
    "`loo_matrix` 的每一列是「给定一组超参数的 **profile 边际似然**」——超参数抽样一旦走进尾部，该列就由"
    "个别荒诞抽样支配；探针实测同一构造在 S=10 时矩阵全距达 **2.3e9**、逐列 SD 7.7e8，S=20 的另一批"
    "抽样全距 27.2（逐列 SD 5.3）⇒ `p_loo` 量的是**离散度**而不是参数个数。③ 对照：同一批抽取摊到"
    "**试次层**（3 人 × 47/46/47 试次 ⇒ `n_obs = 140`）后 `p_loo = 19.273`（`p_loo/n_obs = 0.138`）、"
    "`k_max = 0.000`、`n_failed = 0` ⇒ 试次层可用；被试层同批抽取 `p_loo = 45.002`（`n_obs = 3`）。"
    "④ 顺手修掉一个真 bug：S=30 时 `subject_map_laplace` 会抛 `ValueError: 在众数处 ∂²g 非有限（28/64 个"
    "元素）`，旧 `loo_matrix` 会让 40 小时长跑崩在第 39 小时；现改为该格记 −inf、计入 `n_hessian_fail`，"
    "PSIS 记作失败（`check_loo.py` **17 → 21/21**，E1–E4 四颗牙）。⑤ 口径：§8 的 D52 守卫（`p_loo` 必须"
    "落在 `[0, n_obs]`）继续保留——它正确拦下了无效结果；新增的是**下一步怎么做**：模型比较的 ΔELPD "
    "改用试次层矩阵，被试层留一交给 `loo_bruteforce`（小 N）或 K-fold（大 N），报告必须同时印 "
    "`n_hessian_fail`。 | 探针 `_probe_loo_level.py`、`_probe_loo_draws.py`；自测 `check_loo.py` 21/21；"
    "D70 与 `_s8run_an` 的既有结果 | 被试层 `p_loo` 不再被当作「有效参数数」引用；Stage 8 §11 第 3 条的"
    "「被试太少」改口径为「被试层口径不可估」；`compare_models` 换试次层矩阵列为下一步代码任务 |"
)

PROGRESS = (
    "| 2026-10-17 | **8**（LOO 口径根因 → D73） | **把「LOO 无效」从「被试太少」改写成「口径不可估」**："
    "被试层 `p_loo` 是离散度不是参数数（`p_loo/n_obs = 496`、负 p_loo、矩阵全距 2.3e9），试次层同批抽取"
    "`p_loo/n_obs = 0.138`、`k_max = 0` ⇒ PSIS 放试次层，被试层留一用 bruteforce/K-fold；顺带修掉病态抽样"
    "中断整轮的 bug（`check_loo.py` 17 → **21/21**）。 | `1_Code/DDM_Core/hier.py`（`loo_matrix` 容错 + "
    "`n_hessian_fail`）、`stage8_run.py`（退化计数加 Hessian 非有限）、`_scratch/_probe_loo_level.py`、"
    "`_scratch/check_loo.py`（E1–E4） | 仍等用户侧 Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / "
    "定稿签批；代码侧下一步 = `compare_models` 换试次层矩阵 |"
)

CHANGELOG = (
    "| 2026-10-17 | **新增 D73：被试层 PSIS-LOO 结构性不可估**。① 证据：D70（3 人 × 96 试次、S=30）"
    "`p_loo/n_obs = 496`、`k_max = 5.000`；`_s8run_an` 出现负 p_loo（−706 / −2900）；探针实测 profile "
    "边际在抽取间全距最高 2.3e9。② 对照：同一批抽取摊到试次层后 `p_loo/n_obs = 0.138`、`k_max = 0` ⇒ "
    "PSIS 放试次层，被试层留一改 bruteforce/K-fold。③ 修 bug：`loo_matrix` 遇 Hessian 非有限记 −inf 并计 "
    "`n_hessian_fail`（不再中断整轮），`check_loo.py` **17 → 21/21**。 |"
)

FILE_ROW = (
    "| `1_Code/DDM_Core/hier.py`（**D73**：`loo_matrix` 容错 + `n_hessian_fail`） + `stage8_run.py`"
    "（退化计数） + `_scratch/_probe_loo_level.py` / `_probe_loo_draws.py` + `_scratch/check_loo.py`"
    "（**21/21**，E1–E4） | 2026-10-17（D73） |"
)

S7_ADD = [
    "- ❗ ❗ **被试层 `p_loo` 不是「有效参数数」（D73）**：`loo_matrix` 的每一列是「给定一组超参数的"
    "profile 边际似然」，超参数抽样走到尾部时该列被个别荒诞抽样支配 ⇒ `p_loo` 量的是**离散度**。"
    "实测：D70（3 人 × 96 试次、S=30）`p_loo = 1489.098`（`n_obs = 3`）、`k_max = 5.000`；"
    "`_s8run_an`（2 人）出现负 p_loo（−706.371 / −2900.542）；探针 `_probe_loo_level.py` 里同一构造"
    "（3 人 × 47/46/47 试次、S=20）被试层 `p_loo = 45.002`、试次层同批抽取 `p_loo = 19.273`"
    "（`n_obs = 140`、`p_loo/n_obs = 0.138`、`k_max = 0.000`）。",
    "- ⇒ **口径（D73）**：模型比较的 `ΔELPD` 用**试次层**矩阵（`n_obs` = 总试次）；**被试层**留一交给"
    "`loo_bruteforce`（小 N，金标准）或 K-fold（大 N）。被试层 PSIS 的数字只能作为「矩阵不可估」的证据"
    "引用，不得当作拟合优度。",
]

S9_ROW = (
    "| `1_Code/DDM_Core/hier.py`（LOO 口径根因，D73） | 同一批超参数抽取下**同时**算被试层与试次层"
    " PSIS-LOO，量两层的 `p_loo` / `k_max` / 离散度 | 被试层 `p_loo = 45.002`（`n_obs = 3`）、"
    "`k_max = 0.000`；试次层 `p_loo = 19.273`（`n_obs = 140`、比值 **0.138**）、`k_max = 0.000` ⇒ "
    "试次层可用；另一次抽样里被试层矩阵全距 **2.3e9** |"
)

S11_AND_D73 = (
    "17. ❗ **被试层 PSIS-LOO 不可估，不是「被试太少」（D73）**：`p_loo` 在被试层量的是 profile 边际"
    "在超参数抽取间的**离散度**，因此随抽样数/尾部荒诞值涨落（D70 的 3 人 × 96 试次给出 496；"
    "`_s8run_an` 的 2 人给出**负值**）。⇒ 模型比较用**试次层**矩阵（同批抽取实测 `p_loo/n_obs = 0.138`、"
    "`k_max = 0`），被试层留一用 bruteforce（小 N）/ K-fold（大 N）。报告必须同时印 `n_hessian_fail`。"
)

S8_VERSION = (
    "| v1.6 | 2026-10-17 | **§7 加「被试层 `p_loo` 是离散度」两条口径（D73）、§9 加 LOO 口径根因探针行、"
    "§11 重排编号并加第 17 条（被试层不可估）、`check_loo.py` 17 → 21/21（E1–E4：病态抽样不中断整轮）、"
    "`hier.loo_matrix` 容错 + `n_hessian_fail`、`stage8_run.py` 报 `n_degenerate_hessian`** |"
)

RD_SECTION = """### 8.48 被试层 PSIS-LOO 不可估（2026-10-17，D73）

1. **现象**：D70 正向对照（3 人 × 96 试次、S=30）`elpd_loo = −1642.940 ± 588.064`、
   `p_loo = 1489.098`（`p_loo/n_obs = 496`）、`k_max = 5.000`；`_s8run_an`（2 人）出现**负 p_loo**
   （−706.371 / −2900.542）。负 p_loo 只可能来自 PSIS 权重病态。
2. **机理**：`hier.loo_matrix` 每一列是「给定一组超参数的 **profile 边际似然**」；超参数抽样走到尾部，
   该列就被个别荒诞抽样支配 —— 探针实测同一构造在 S=10 时矩阵全距 **2.3e9**、逐列 SD 7.7e8。
   ⇒ `p_loo` 量的是**离散度**，不是有效参数个数。
3. **对照**：同一批抽取摊到**试次层**（3 人 × 47/46/47 试次 ⇒ `n_obs = 140`）后 `p_loo = 19.273`
   （比值 **0.138**）、`k_max = 0.000`、`n_failed = 0` ⇒ 试次层可用。
4. **口径**：模型比较的 `ΔELPD` 用**试次层**矩阵；**被试层**留一用 `loo_bruteforce`（小 N，金标准）
   或 K-fold（大 N）。被试层 PSIS 的数字只能当「矩阵不可估」的证据，不得当拟合优度。
5. **顺手修的 bug**：S=30 时 `subject_map_laplace` 会抛 `ValueError: 在众数处 ∂²g 非有限
   （28/64 个元素）`，旧 `loo_matrix` 会让 40 小时长跑崩在第 39 小时；现在该格记 −inf、计入
   `n_hessian_fail`，PSIS 记为失败。牙齿 `_scratch/check_loo.py` **17 → 21/21**（E1 不抛异常、
   E2 记 −inf、E3 计数逐格累加、E4 该列被计为失败且不污染其他列）。
"""

RD_ITEM = (
    "| 57 | ✅ **被试层 PSIS-LOO 不可估（D73，§8.48）** | 被试层 `p_loo` 是「profile 边际在超参数抽取间的"
    "离散度」而非参数数（`p_loo/n_obs = 496`、负 p_loo、矩阵全距 2.3e9）；试次层同批抽取 `0.138`、"
    "`k_max = 0` ⇒ PSIS 放试次层、被试层留一用 bruteforce/K-fold；`loo_matrix` 遇 Hessian 非有限记 −inf "
    "并计 `n_hessian_fail`（`check_loo.py` 21/21） |"
)


def insert_after(text: str, prefix: str, new: str) -> str:
    lines = text.split("\n")
    hit = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hit) == 1, f"{prefix[:40]}… 命中 {len(hit)} 行"
    lines.insert(hit[0] + 1, new)
    return "\n".join(lines)


def renumber_s11(t: str) -> str:
    """把 §11 的有序列表重排成 1..N（原文有两条 7.）。"""
    lines = t.split("\n")
    i0 = lines.index("## 11. 已知限制（**必须随结果一起报**）")
    i1 = i0 + 1
    while not lines[i1].startswith("---"):
        i1 += 1
    n = 0
    for i in range(i0 + 2, i1):
        ln = lines[i]
        m = re.match(r"^(\d+)\. (.*)$", ln)
        if m:
            n += 1
            lines[i] = f"{n}. {m.group(2)}"
    return "\n".join(lines)


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}")

    t = MP.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D73" in t:
        print("  [跳过] 工作流_主计划.md（已落）")
    else:
        t = insert_after(t, "| **D72** | 2026-10-17 |", DECISION)
        t = insert_after(t, "| 2026-10-17 | **8**（长跑可恢复 → D72） |", PROGRESS)
        t = insert_after(t, "| 2026-10-17 | **新增 D72：", CHANGELOG)
        t = insert_after(t, "| `1_Code/DDM_Core/stage8_run.py`（**D72**：", FILE_ROW)
        if APPLY:
            MP.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] 工作流_主计划.md")

    t = S8.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D73" in t:
        print("  [跳过] Stage8_建模与验证方案.md（已落）")
    else:
        anchor = ("- ⚠️ **单个 `k̂` 的噪声很大（实测 SD 0.096–0.129），不得逐点解读**。"
                  "判断\"是否该换 `k`-fold CV\"看 **`n_k_gt_bad / N` 这个比例**与 **`k_max`**，"
                  "而不是某个观测的 `k̂` 是否刚好越过 0.7。")
        assert t.count(anchor) == 1
        t = t.replace(anchor, anchor + "\n" + "\n".join(S7_ADD))
        t = insert_after(t, "| `1_Code/DDM_Core/stage8_run.py`（组级缓存/续跑，D72） |", S9_ROW)
        t = renumber_s11(t)
        t = insert_after(t, "16. ❗ **正向对照只在 N=3 / 96 试次上做过（D70）**", S11_AND_D73)
        t = insert_after(t, "| v1.5 | 2026-10-17 |", S8_VERSION)
        if APPLY:
            S8.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] Stage8_建模与验证方案.md")

    t = RD.read_text(encoding="utf-8")
    assert "\r" not in t
    if "### 8.48" in t:
        print("  [跳过] README.md（已落）")
    else:
        lines = t.split("\n")
        hits = [i for i, ln in enumerate(lines) if ln.startswith("## 9. 尚未做")]
        assert len(hits) == 1
        lines[hits[0]:hits[0]] = RD_SECTION.split("\n") + [""]
        i56 = [i for i, ln in enumerate(lines) if ln.startswith("| 56 | ✅")]
        assert len(i56) == 1
        lines.insert(i56[0] + 1, RD_ITEM)
        if APPLY:
            RD.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
