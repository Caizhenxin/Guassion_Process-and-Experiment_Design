# -*- coding: utf-8 -*-
"""_apply_d76.py — 把 D76（Stage 8 组级健康判据一键报告）落进四份文档。

落点：
* `5_Reference/08_工作流/工作流_主计划.md`：§5 决策行、§6 进度行、§7 变更日志、§8 文件行，
  并把 Stage 8 状态段里三处过时表述（「不用 trial-level LOO 冒充」、自测计数、状态日期）改掉。
* `5_Reference/08_工作流/Stage8_建模与验证方案.md`：§9 工具行、§10 第 1 条补「拟合完立刻跑」、
  §11 第 20 条、§12 v1.9。
* `1_Code/DDM_Core/README.md`：§8.50（六小节）+ §9 第 60 项。

幂等：每处插入前先查 `has()`，已存在则打印「跳过」。

    python -X utf8 -u 1_Code\\DDM_Core\\_scratch\\_apply_d76.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
S8 = ROOT / "5_Reference/08_工作流/Stage8_建模与验证方案.md"
README = ROOT / "1_Code/DDM_Core/README.md"

DONE: list[str] = []
SKIP: list[str] = []


def has(text: str, needle: str) -> bool:
    return needle in text


def insert_after(text: str, prefix: str, new: str) -> str:
    """在唯一一条以 `prefix` 开头的行之后插入 `new`（多行用 \\n 分隔）。"""
    lines = text.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(idx) == 1, f"锚点不唯一：{prefix!r} 命中 {len(idx)} 行"
    lines.insert(idx[0] + 1, new)
    return "\n".join(lines)


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"待替换文本命中 {text.count(old)} 次：{old[:60]!r}"
    return text.replace(old, new)


# ---------------------------------------------------------------- 主计划
D76_ROW = (
    "| **D76** | 2026-10-17 | ❗ **「这组 LOO 能不能引用」从报告里的判词收敛成可批量执行的检查器**"
    "（`stage8_health.py`）。① 动机：D73/D74/D75 的三组判据此前只活在报告正文与 §11 的文字里，"
    "而正式数据是「4 组 × ~40 人」的批处理 ⇒ 人要逐份翻报告才知道哪组能引用；"
    "「同 tag 不同目录 / 两层口径混用 / `max_abs_theta` 缺失」这三类情形在报告里尤其不显眼。"
    "② 实现：`1_Code/DDM_Core/stage8_health.py`（267 行，零依赖）："
    "三条硬闸 H1 `n_flipped > 0`、H2 `loo_level != trial`、"
    "H3 `p_loo ∉ [0, n_obs]` 或 `k_max` 非有限或失败率 > 20%、H4 `n_draws < 10`；"
    "两条软告警 W1 `max\\|θ\\| ≥ 20`（D75 实测分离 7.3 vs 33.6–303）或缺该字段 ⇒ 按「未落盘」告警、"
    "W2 `0.7 < k_max ≤ 1.0`；同组内两种口径混用 ⇒ `comparable = False`、整组判「不可比较」。"
    "③ 输出：Markdown 概览表（含「来源目录」列，避免同 tag 撞名）+ 逐组明细"
    "（ELPD/`p_loo`/`n_obs`/`k_max`/失败数/Hessian/`max\\|θ\\|`/逐条理由）+ `--json` 汇总 + "
    "`--strict`（有不可引用即退出 1，CI 用）。④ 实测：`_scratch/stage8_trial_s15`"
    "（试次层、`n_flipped` 2/16、`p_loo` 797 / `n_obs` 93）与 `_scratch/stage8_d75_gate`"
    "（`p_loo` −242.9、`k_max` nan、`max\\|θ\\|` 269.1）都判「⛔ 不可引用」，"
    "理由与报告判词逐条对应。⑤ 牙齿：`_scratch/check_stage8_health.py`（**27/27**；"
    "A 12 项单块判据、B 混口径与渲染、C `--strict`/`--json` 端到端、D 坏输入必须响亮）。"
    " | 新建 `1_Code/DDM_Core/stage8_health.py` + `_scratch/check_stage8_health.py`（**27/27**、exit 0）；"
    "实测日志 `_scratch/_health_probe.txt`、`_scratch/_check_stage8_health.txt` "
    " | 正式数据回填时**每组拟合完就能跑一次**，不必等四组齐；Stage 8 §10 第 1 条的「逐组事后判」"
    "从人工改为可执行；D74/D75 的判据从此只有一个代码出口 |"
)

D76_PROGRESS = (
    "| 2026-10-17 | **8**（组级健康判据 → D76） | **把「哪组 LOO 能引用」做成一条命令**："
    "`stage8_health.py` 三条硬闸（非正定 / 非试次层 / 数值越界 / 抽取不足）+ 两条软告警 + 混口径判定，"
    "`--json`/`--strict` 可进 CI；两组病态缓存（`stage8_trial_s15`、`stage8_d75_gate`）都判「不可引用」，"
    "且理由与报告判词逐条对得上。 "
    "| `1_Code/DDM_Core/stage8_health.py`（267 行）+ `_scratch/check_stage8_health.py`（**27/27**） "
    "| 正式数据到手后每组拟合完即跑；用户侧 Stage 1/6/7 与定稿 |"
)

D76_LOG = (
    "| 2026-10-17 | **新增 D76：Stage 8 组级健康判据一键报告**。① 新建 `1_Code/DDM_Core/stage8_health.py`"
    "（267 行、零依赖）：三条硬闸（`n_flipped` > 0 / 口径非 trial / `p_loo` 越界·`k_max` 非有限·失败率 > 20% / "
    "`n_draws` < 10）+ 两条软告警（`max_abs_theta` ≥ 20 或缺失 / `0.7 < k_max` ≤ 1.0）+ 同组混口径 ⇒ 不可比较；"
    "② 输出 Markdown 概览表（带「来源目录」列）+ 逐组明细 + `--json` + `--strict`（有不可引用即 exit 1）；"
    "③ 实测两组病态缓存均判「⛔ 不可引用」；④ 牙齿 `_scratch/check_stage8_health.py` **27/27**；"
    "⑤ 主计划 Stage 8 状态段三处过时表述同步改掉（「不用 trial-level LOO 冒充」与 D73 相反、"
    "自测计数停在 14/14·17/17、状态日期停在 2026-10-14） |"
)

D76_FILES = (
    "| `1_Code/DDM_Core/stage8_health.py`（**新建**，267 行） + "
    "`1_Code/DDM_Core/_scratch/check_stage8_health.py`（**新建**，**27/27**） + "
    "`1_Code/DDM_Core/_scratch/_health_probe.txt` / `_check_stage8_health.txt`（实测日志） "
    "| **D76 的一手证据（组级健康判据）**。判据逐条有出处：H1 ← D74（非正定两层都越界）、"
    "H2 ← D73（被试层 `p_loo` 不可估）、H3 ← D52/D73（`p_loo` 的健康区间是 `[0, n_obs]`）、"
    "H4 ← `loo.psis_one`（S < 10 不做 GPD 平滑）、W1 ← D75（正定 ≤ 7.3 vs 非正定 33.6–303）、"
    "W2 ← `loo.K_BAD`/`K_UNUSABLE`。实测：`stage8_trial_s15` 判「非正定 2/16 + `p_loo` 797 越界 [0, 93]」、"
    "`stage8_d75_gate` 判「非正定 2/16 + `p_loo` −242.9 + `k_max` nan」，与两次报告里的判词一致"
    "（**D76**，2026-10-17） |"
)

S8_TOOL_ROW = (
    "| `1_Code/DDM_Core/stage8_health.py`（D76：组级健康判据） | 扫 `stage8_group_*.json`，"
    "把「这组 LOO 能不能引用」收敛成一条命令：三条硬闸（`n_flipped` > 0 / 口径非 trial / "
    "`p_loo` 越界·`k_max` 非有限·失败率 > 20% / `n_draws` < 10）+ 两条软告警"
    "（`max_abs_theta` ≥ 20 或缺失 ⇒ 按未落盘告警；`0.7 < k_max` ≤ 1.0）+ 混口径 ⇒ 不可比较 "
    "| `_scratch/check_stage8_health.py` **27/27 通过**（A 12 项单块判据、B 混口径与渲染、"
    "C `--strict`/`--json` 端到端、D 坏输入必须响亮）；实测两组病态缓存都判「⛔ 不可引用」："
    "`stage8_trial_s15`（`n_flipped` 2/16、`p_loo` 797 / `n_obs` 93）、"
    "`stage8_d75_gate`（`p_loo` −242.9、`k_max` nan、`max\\|θ\\|` 269.1） |"
)

S8_ITEM20 = (
    "20. ❗ **「能不能引用 LOO」有唯一代码出口**（D76）：`stage8_health.py` 的硬闸"
    "（`n_flipped` > 0、口径非 trial、`p_loo ∉ [0, n_obs]` 或 `k_max` 非有限或失败率 > 20%、"
    "`n_draws` < 10）与软告警（`max_abs_theta` ≥ 20 或缺失、`0.7 < k_max ≤ 1.0`）逐条对应 D73–D75；"
    "**同组内混用两种口径 ⇒ 模型比较不成立**。人读报告与跑检查器必须给出同一结论；若不一致，"
    "以检查器为准并修报告判词，不得反过来放宽判据。"
)

S8_V19 = (
    "| v1.9 | 2026-10-17 | **新增 D76**：`1_Code/DDM_Core/stage8_health.py`（组级健康判据一键报告："
    "三条硬闸 + 两条软告警 + 混口径判定，`--json`/`--strict`）+ `_scratch/check_stage8_health.py` "
    "**27/27**；§10 第 1 条补「拟合完立刻跑 `--strict`」；§11 加第 20 条 |"
)

README_SECTION = """### 8.50 Stage 8 组级健康判据的一键报告（2026-10-17，D76）

1. **问题**：D73/D74/D75 把「哪种 LOO 结果不可引用」讲清了三层，但这些判据只活在 `stage8_report.md` 的判词行与 Stage 8 §11 的文字里。正式数据是「4 组 × ~40 人」的批处理，每组落一个 `stage8_group_<组>.json` ⇒ 人要逐份翻报告才知道哪组能引用；尤其三类情形不显眼：**同 tag 落在不同目录**（概览表会撞名）、**同组内两个模型用了不同口径**（数字都在「健康」区间，却不可比）、**旧缓存缺 `max_abs_theta`**（D75 之后才有该字段，缺失时若不告警就等于默认「跑得近」）。
2. **实现**：`1_Code/DDM_Core/stage8_health.py`（267 行，零依赖，`assess_mode` / `assess_group` / `collect` / `render` / `main`）。三条硬闸：H1 `n_flipped > 0`（D74）、H2 `loo_level != trial`（D73）、H3 `p_loo ∉ [0, n_obs]` 或 `k_max` 非有限或失败率 > 20%（D52/D73）、H4 `n_draws < 10`（`loo.psis_one` 不做 GPD 平滑）；两条软告警：W1 `max_abs_theta ≥ 20`（D75 实测分离：正定 ≤ 7.3 vs 非正定 33.6–303）或该字段缺失 ⇒ 按「未落盘」告警、W2 `0.7 < k_max ≤ 1.0`（降级为提示性）。
3. **混口径**：`levels` 有多个值 ⇒ `comparable = False` 且整组直接判「不可引用」——因为 `ΔELPD` 在两个口径的 `n_obs` 语义下不是同一个量（D73）。
4. **输出**：Markdown 概览表（列含**来源目录**，避免同 tag 撞名）+ 逐组明细（ELPD ± SE、`p_loo`、`n_obs`、`k_max`、失败数、Hessian、`max\\|θ\\|`、逐条理由）+ `--json` 机器可读汇总；`--strict` 时有任一「不可引用」就以 1 退出（CI/批处理用）。
5. **实测**：两组病态缓存都判「⛔ 不可引用」，理由与两次报告里的判词逐条对得上 —— `_scratch/stage8_trial_s15`（试次层、`n_flipped` 2/16、`p_loo` 797 / `n_obs` 93）、`_scratch/stage8_d75_gate`（`p_loo` −242.9、`k_max` nan、`max|θ|` 269.1）。
6. **牙齿**：`1_Code/DDM_Core/_scratch/check_stage8_health.py` **27/27、exit 0** —— A 组 12 项单块判据（健康 / 非正定 / 被试层 / `p_loo` < 0 / `p_loo` > `n_obs` / `k_max` nan / 失败率 / `n_draws` / `max|θ|` / 缺字段 / `k_max` 0.85 / 缺 loo·hyper）、B 组混口径与渲染、C 组 `--strict`·`--json` 端到端、D 组坏输入必须响亮（`FileNotFoundError` / `ValueError` 含「缺字段」）。
"""

README_ITEM60 = (
    "| 60 | ✅ **Stage 8 组级健康判据一键报告（D76，§8.50）** | `1_Code/DDM_Core/stage8_health.py`（267 行）："
    "三条硬闸（`n_flipped` > 0 / 非 trial 口径 / `p_loo` 越界·`k_max` 非有限·失败率 > 20% / `n_draws` < 10）"
    "+ 两条软告警（`max_abs_theta` ≥ 20 或缺失 / `0.7 < k_max` ≤ 1.0）+ 混口径 ⇒ 不可比较；"
    "输出 Markdown 概览表（含「来源目录」列）+ 逐组明细 + `--json` + `--strict`；"
    "`_scratch/check_stage8_health.py` **27/27**；实测 `stage8_trial_s15` 与 `stage8_d75_gate` 都判「不可引用」 |"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的写盘（默认只自检）")
    args = ap.parse_args()

    edits = {MP: [], S8: [], README: []}
    texts = {p: p.read_text(encoding="utf-8") for p in edits}

    # ---- 主计划 §5 决策行（锚 D75 行） ----
    if has(texts[MP], "| **D76** | 2026-10-17 |"):
        SKIP.append("主计划 §5 D76 决策行")
    else:
        texts[MP] = insert_after(texts[MP], "| **D75** | 2026-10-17 |", D76_ROW)
        DONE.append("主计划 §5 D76 决策行")

    # ---- 主计划 §6 进度行 ----
    if has(texts[MP], "（组级健康判据 → D76）"):
        SKIP.append("主计划 §6 D76 进度行")
    else:
        texts[MP] = insert_after(
            texts[MP], "| 2026-10-17 | **8**（Hessian 正定性 vs 样本量 → D75） |", D76_PROGRESS)
        DONE.append("主计划 §6 D76 进度行")

    # ---- 主计划 §7 变更日志 ----
    if has(texts[MP], "**新增 D76：Stage 8 组级健康判据一键报告**"):
        SKIP.append("主计划 §7 D76 变更日志")
    else:
        texts[MP] = insert_after(texts[MP], "| 2026-10-17 | **新增 D75：", D76_LOG)
        DONE.append("主计划 §7 D76 变更日志")

    # ---- 主计划 §8 文件行 ----
    if has(texts[MP], "**D76 的一手证据（组级健康判据）**"):
        SKIP.append("主计划 §8 D76 文件行")
    else:
        texts[MP] = insert_after(
            texts[MP],
            "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（N=2…6 扫描 + N=4 加试次，D75）",
            D76_FILES)
        DONE.append("主计划 §8 D76 文件行")

    # ---- 主计划 Stage 8 状态段：三处过时表述 ----
    old_goal = ("→ PSIS-LOO（含 Pareto k 诊断）→ 模型比较 → **leave-one-participant-out**"
                "（不用 trial-level LOO 冒充跨被试泛化）。")
    new_goal = ("→ PSIS-LOO（含 Pareto k 诊断；**模型比较用试次层矩阵**，见 D73）→ 模型比较 → "
                "**以被试为单位的留一**（bruteforce / K-fold；被试层 PSIS-LOO 结构性不可估）。")
    if has(texts[MP], new_goal):
        SKIP.append("Stage 8 目的句（D73 口径）")
    else:
        texts[MP] = replace_once(texts[MP], old_goal, new_goal)
        DONE.append("Stage 8 目的句（D73 口径）")

    old_date = "**状态（2026-10-14）**：🟡 进行中 —— **核心件已交付且带基准证据**"
    new_date = "**状态（2026-10-17）**：🟡 进行中 —— **核心件已交付且带基准证据**"
    if has(texts[MP], new_date):
        SKIP.append("Stage 8 状态日期")
    else:
        texts[MP] = replace_once(texts[MP], old_date, new_date)
        DONE.append("Stage 8 状态日期")

    old_deliv = ("- **三个交付件**：`loo.py`（PSIS-LOO，14/14 自测通过）、`stage8.py`"
                 "（拉普拉斯抽样 + PPC，17/17 通过）、`hier.py`（拉普拉斯-EM 层级拟合 + "
                 "以被试为单位的 LOO，0 项未通过）。")
    new_deliv = ("- **交付件（计数已于 D76 同步）**：`loo.py`（PSIS-LOO，**26/26**）、`stage8.py`"
                 "（拉普拉斯抽样 + PPC，**24/24**）、`hier.py`（拉普拉斯-EM 层级拟合 + "
                 "两层 LOO 矩阵，**0 项未通过**）、`stage8_run.py`（全量运行器，**37/37**）、"
                 "`stage8_health.py`（组级健康判据，**27/27**）。")
    if has(texts[MP], new_deliv):
        SKIP.append("Stage 8 交付件计数")
    else:
        texts[MP] = replace_once(texts[MP], old_deliv, new_deliv)
        DONE.append("Stage 8 交付件计数")

    # ---- Stage 8 §9 工具行 ----
    if has(texts[S8], "`1_Code/DDM_Core/stage8_health.py`（D76：组级健康判据）"):
        SKIP.append("Stage8 §9 D76 工具行")
    else:
        texts[S8] = insert_after(
            texts[S8],
            "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（D75 扫描）", S8_TOOL_ROW)
        DONE.append("Stage8 §9 D76 工具行")

    # ---- Stage 8 §10 第 1 条补「拟合完立刻跑」 ----
    old_tail = "⚠️ 不得因为「每组 ~40 人」就预先承"
    if has(texts[S8], "stage8_health.py <该组的 --out 目录> --strict"):
        SKIP.append("Stage8 §10 第 1 条补注")
    else:
        lines = texts[S8].split("\n")
        hit = [i for i, ln in enumerate(lines) if ln.startswith("1. ❗ **先判 LOO 可用性")]
        assert len(hit) == 1, f"§10 第 1 条命中 {len(hit)} 行"
        add = ("此外，**拟合完立刻跑** `python -X utf8 1_Code\\DDM_Core\\stage8_health.py "
               "<该组的 --out 目录> --strict`（D76）：有任一组「不可引用」即非零退出，"
               "`--json` 留一份机器可读汇总；人读报告与检查器结论不一致时以检查器为准。")
        lines[hit[0]] = lines[hit[0]] + add
        texts[S8] = "\n".join(lines)
        DONE.append("Stage8 §10 第 1 条补注")

    # ---- Stage 8 §11 第 20 条 ----
    if has(texts[S8], "20. ❗ **「能不能引用 LOO」有唯一代码出口**"):
        SKIP.append("Stage8 §11 第 20 条")
    else:
        texts[S8] = insert_after(texts[S8], "19. ❗ **不得写「人够了 LOO 就可用」（D75）**",
                                 S8_ITEM20)
        DONE.append("Stage8 §11 第 20 条")

    # ---- Stage 8 §12 v1.9 ----
    if has(texts[S8], "| v1.9 |"):
        SKIP.append("Stage8 §12 v1.9")
    else:
        texts[S8] = insert_after(texts[S8], "| v1.8 | 2026-10-17 |", S8_V19)
        DONE.append("Stage8 §12 v1.9")

    # ---- README §8.50 ----
    if has(texts[README], "### 8.50 "):
        SKIP.append("README §8.50")
    else:
        texts[README] = replace_once(texts[README], "## 9. 尚未做",
                                     README_SECTION + "\n## 9. 尚未做")
        DONE.append("README §8.50")

    # ---- README §9 第 60 项 ----
    if has(texts[README], "| 60 | ✅ **Stage 8 组级健康判据一键报告"):
        SKIP.append("README §9 第 60 项")
    else:
        texts[README] = insert_after(
            texts[README], "| 59 | ✅ **超参数 Hessian 正定性不是样本量的函数", README_ITEM60)
        DONE.append("README §9 第 60 项")

    for what in DONE:
        print(f"[应用] {what}")
    for what in SKIP:
        print(f"[跳过] {what}（已存在）")

    if not args.apply:
        print("\n（自检模式：未写盘。加 --apply 落地。）")
        return 0
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"已写盘：{path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
