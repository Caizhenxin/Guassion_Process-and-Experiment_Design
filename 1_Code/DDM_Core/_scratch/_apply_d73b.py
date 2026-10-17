# -*- coding: utf-8 -*-
"""D73 ⑧ + D74 落纸：试次层 LOO 的代码化，以及**「层不是充分条件」**这条实测前提。

用法：python -X utf8 -u _apply_d73b.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

# ---------------------------------------------------------------- 主计划
D73_CODE_TAIL = (
    "⑥ ❗ **代码已可切换（同轮）**：`stage8_run.py` 新增 `--loo-level {participant,trial}`"
    "（**默认 `participant`，保持全部历史日志与结论可复现**）、`hier.loo_matrix_trials`"
    "（返回 `(S, 总试次)`，逐试次似然非有限时该试次记 −inf 并计 `n_trial_ll_fail`）、"
    "`compare_models` 加层/形状守卫；`check_loo.py` **21 → 26/26**（F1–F5）、"
    "`check_stage8_run.py` **31 → 32/32**（E17：透传给拟合 + 写进报告头 + **进缓存配置键**，"
    "否则同目录换口径 `--resume` 会静默混用两层矩阵）。"
)
D73_LASTCELL_OLD = "`compare_models` 换试次层矩阵列为下一步代码任务 |"
D73_LASTCELL_NEW = "`compare_models` 的层已可由 `--loo-level trial` 切换（默认 `participant`） |"

D74 = (
    "| **D74** | 2026-10-17 | ❗ **「换到试次层」不是 LOO 可用的充分条件 —— 前置条件是超参数 "
    "Hessian 正定**。① 触发：D73 之后试次层第一次端到端跑（2 人 × 93 试次、`n_em=1`、"
    "`n_draws=15`、`n_x=11`、analytic）仍被判无效 —— `p_loo/n_obs` = **8.57**（M-T1）/ **12.7**"
    "（M-T3）、`k_max = 0.000`、越界 0/93。② 根因：该配置的 `hyper.eigval` 各有两个负特征值"
    "（−0.825 / −0.947），`theta` 逐维 SD 最高 **134**、|θ| 最高 **303** ⇒ 矩阵的每一列都被荒诞"
    "尾部抽样支配，摊到试次层只是把同一份病态除以更大的 `n_obs`（`n_obs` 从 2 变 93，比值从 496 "
    "级降到 8.57 级，仍越界）。③ 对照（同一份代码）：把配置换成 3 人、`n_em=2`、`n_x=21`、S=20 后 "
    "Hessian **正定**（min eig 0.026544、负特征值 0/16、`n_flipped` = 0、θ 逐维 SD ≤ 3.88、|θ| ≤ 9.32）"
    "⇒ 试次层 `p_loo/n_obs = 0.138`、`k_max = 0`。④ 判据顺序因此固定为：**先查 Hessian 正定"
    "（`n_flipped == 0`），再查层与 `p_loo/n_obs`**。`render_group` 的 LOO 判词新增一条独立理由"
    "「超参数 Hessian **非正定** ⇒ 抽取含荒诞尾部值，`p_loo` 不可解读」，报告表头的口径行也标注该"
    "前置条件；`check_stage8_run.py` **32 → 34/34**（A7f：`p_loo` 健康但 `n_flipped` > 0 ⇒ 必须判无效；"
    "A7g：正定时不得误伤）。⑤ 端到端：同一小配置重跑的报告逐行命中该判词（exit 0）。 "
    "| 探针 `_scratch/_probe_hyper_pd.py`（正定侧实测）+ `_scratch/stage8_trial_s15/`（非正定侧实测，"
    "eig/θ 两栏由 `stage8_results.json` 读出）；自测 `check_stage8_run.py` 34/34（A7f/A7g） | "
    "引用 `p_loo` 前必须先报 `n_flipped`；小样本干跑（2 人、`n_x=11`、S=15）的 LOO 一律按"
    "「Hessian 不正定、不可解读」处理，不得用来论证「试次层也不行」 |"
)

D74_PROGRESS = (
    "| 2026-10-17 | **8**（试次层 LOO 落地 → D73⑧/D74） | **把试次层 LOO 落成可切换口径，并发现"
    "「层」不是充分条件**：`--loo-level {participant,trial}`（默认保持历史行为）+ `loo_matrix_trials` + "
    "`compare_models` 层/形状守卫；端到端实测显示换层后仍越界（`p_loo/n_obs` 8.57 / 12.7），根因是"
    "超参数 Hessian 非正定（θ 逐维 SD 达 134），对照正定配置得到 0.138 ⇒ 判据顺序改为「先 Hessian 正定、"
    "再看层与比值」。 | `1_Code/DDM_Core/stage8_run.py`（`--loo-level`、LOO 判词 D74 理由、口径行）、"
    "`hier.py`（`loo_matrix_trials`）、`_scratch/_probe_hyper_pd.py`、`_scratch/check_loo.py`（26/26）、"
    "`_scratch/check_stage8_run.py`（34/34，A7f/A7g） | 仍等用户侧 Stage 1 实机验收 / Stage 6 Pilot / "
    "Stage 7 正式采集 / 定稿签批；正式数据到手后先看各组 `n_flipped`，再决定该组 LOO 是否可报 |"
)

D74_CHANGELOG = (
    "| 2026-10-17 | **新增 D74：超参数 Hessian 正定是 LOO 可用的前置条件（层不是充分条件）**。"
    "① 试次层端到端（2 人 × 93 试次、`n_x=11`、S=15）仍越界：`p_loo/n_obs` 8.57 / 12.7，"
    "而 `k_max = 0`、越界 0/93；② 同一份 json 里 `n_flipped` = 2、`eigval` 各 2 个负值、θ 逐维 SD 达 134；"
    "③ 对照正定配置（3 人、`n_x=21`、S=20：min eig 0.026544、0/16 负、θ SD ≤ 3.88）得 `p_loo/n_obs` = 0.138；"
    "④ `render_group` 的 LOO 判词加「非正定 ⇒ `p_loo` 不可解读」，`check_stage8_run.py` 32 → 34/34。 |"
)

D74_FILE_ROW = (
    "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（正定侧：3 人/n_em=2/n_x=21/S=20 ⇒ min eig 0.026544、"
    "`n_flipped` 0/16）+ `_scratch/stage8_trial_s15/`（非正定侧：`p_loo/n_obs` 8.57/12.7、θ SD 134）+ "
    "`1_Code/DDM_Core/stage8_run.py`（LOO 判词 D74 理由 + 口径行前置条件） + `_scratch/check_stage8_run.py`"
    "（**34/34**，A7f/A7g） | 2026-10-17（D74） |"
)

# ---------------------------------------------------------------- Stage 8
S8_CODE_BULLET = (
    "- ✅ **已落成可切换口径（D73 ⑧）**：`python stage8_run.py ... --loo-level trial`（默认 "
    "`participant`，全部历史日志与结论保持不变）；`hier.loo_matrix_trials` 返回 `(S, 总试次)`，"
    "逐试次似然非有限时该试次记 −inf 并计 `n_trial_ll_fail`；`compare_models` 会拒绝形状或层不一致的矩阵；"
    "`--loo-level` **进缓存配置键**（同 `--out` 换口径 `--resume` 会报配置不一致，不会静默混用）。"
)

S8_S9_ROWS = [
    "| `1_Code/DDM_Core/stage8_run.py --loo-level trial`（D73 ⑧） | 试次层口径**端到端**跑通并落纸："
    "`--synthetic 2 --synth-n-rep 1 --n-em 1 --n-draws 15 --n-x 11 --hyper-method analytic` ⇒ "
    "报告印「LOO 口径 = `trial`」「`n_obs` = 总试次」，`check_loo.py` 26/26（F1–F5）、"
    "`check_stage8_run.py` 32/32（E17） | 该次运行 `p_loo/n_obs` = 8.57 / 12.7、`k_max` = 0、越界 0/93 "
    "⇒ 换层本身不保证可用（见下一条 D74） |",
    "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（D74） | 同一份代码、只改配置，直接读 `hyper.eigval` 与 θ "
    "的逐维 SD | 正定侧（3 人、`n_em=2`、`n_x=21`、S=20）：min eig **0.026544**、负特征值 **0/16**、"
    "θ SD ≤ 3.88、\\|θ\\| ≤ 9.32 ⇒ 试次层 `p_loo/n_obs` = **0.138**；非正定侧（2 人、`n_em=1`、`n_x=11`、"
    "S=15）：2 个负特征值（−0.825 / −0.947）、θ SD 达 **134**、\\|θ\\| 达 **303** ⇒ `p_loo/n_obs` = 8.57 / 12.7 "
    "⇒ **判据顺序 = 先 `n_flipped`，再看层与比值** |",
]

S8_S11_18 = (
    "18. ❗ **「试次层」不是 LOO 可用的充分条件（D74）**：超参数 Hessian 非正定（`n_flipped` > 0）时，"
    "抽样里混着 |θ| 达数百的荒诞尾部值 ⇒ 两层都会越界（实测同一份代码：正定配置试次层 `p_loo/n_obs` = "
    "0.138，非正定配置 8.57 / 12.7）。因此引用任何 `p_loo`/`ELPD` 前**必须先报 `n_flipped` 与特征值谱**。"
)

S8_VERSION = (
    "| v1.7 | 2026-10-17 | **试次层 LOO 落成代码**（`--loo-level {participant,trial}`、`hier.loo_matrix_trials`、"
    "`compare_models` 层/形状守卫；`check_loo.py` 21 → 26/26、`check_stage8_run.py` 31 → 32/32）；**新增 D74**："
    "超参数 Hessian 正定是前置条件（`render_group` 判词加「非正定 ⇒ `p_loo` 不可解读」，"
    "`check_stage8_run.py` 32 → **34/34**）；§7 加「已落成可切换口径」、§9 加两行端到端与正定/非正定对照、"
    "§11 加第 18 条 |"
)

# ---------------------------------------------------------------- README
RD_ITEMS = (
    "6. **已落成可切换口径（D73 ⑧）**：`stage8_run.py` 新增 `--loo-level {participant,trial}`，"
    "**默认 `participant`**（历史日志与结论逐位可复现）；`hier.loo_matrix_trials` 返回 `(S, 总试次)`，"
    "逐试次似然非有限时记 −inf 并计 `n_trial_ll_fail`；`compare_models` 拒绝形状/层不一致的矩阵；"
    "`--loo-level` 也进了缓存配置键（换口径 `--resume` 会报「配置不一致」）。牙齿："
    "`_scratch/check_loo.py` **21 → 26/26**（F1–F5）、`_scratch/check_stage8_run.py` **31 → 32/32**（E17）。\n"
    "7. ❗ **「换到试次层」不是充分条件（D74）**：2 人 × 93 试次、`n_em=1`、`n_draws=15`、`n_x=11` 的"
    "端到端实跑，`k_max = 0.000`、越界 0/93，但 `p_loo/n_obs` 仍是 **8.57**（M-T1）/ **12.7**（M-T3）。"
    "根因在 `stage8_results.json` 里直接可读：`hyper.eigval` 各有两个负特征值（−0.825 / −0.947）、"
    "`theta` 逐维 SD 最高 **134**、|θ| 最高 **303** ⇒ 每列都被荒诞尾部抽样支配，摊到试次层只是把同一份病态"
    "除以更大的 `n_obs`。8. **判据顺序（D74）**：先看超参数 Hessian 是否正定（`n_flipped == 0`），"
    "再看层与 `p_loo/n_obs`。对照实测（`_scratch/_probe_hyper_pd.py`，同一份代码、只改配置）："
    "3 人、`n_em=2`、`n_x=21`、S=20 ⇒ min eig **0.026544**、负特征值 **0/16**、θ SD ≤ 3.88 ⇒ "
    "试次层 `p_loo/n_obs` = **0.138**。`render_group` 的 LOO 判词已加「非正定 ⇒ `p_loo` 不可解读」，"
    "牙齿 `check_stage8_run.py` **32 → 34/34**（A7f 必须拦、A7g 不误伤）。"
)

RD_ITEM58 = (
    "| 58 | ✅ **超参数 Hessian 正定是 LOO 可用的前置条件（D74，§8.48 第 6–8 条）** | "
    "试次层第一次端到端实跑仍越界（`p_loo/n_obs` 8.57 / 12.7），而同一次运行里 `hyper.eigval` 有 2 个负特征值、"
    "θ 逐维 SD 达 **134**、|θ| 达 **303** ⇒ 病态来自超参数抽样而不是「层」；正定对照配置（min eig 0.026544、"
    "`n_flipped` 0/16、θ SD ≤ 3.88）下试次层 `p_loo/n_obs` = **0.138**。`stage8_run.render_group` 的 LOO 判词"
    "新增独立理由「超参数 Hessian **非正定** ⇒ `p_loo` 不可解读（D74）」，报告口径行标注该前置条件；"
    "`check_stage8_run.py` **32 → 34/34**（A7f/A7g）。⚠️ 引用任何 `p_loo`/`ELPD` 前必须先报 `n_flipped` "
    "与特征值谱 |"
)


def insert_after(text: str, prefix: str, new: str) -> str:
    lines = text.split("\n")
    hit = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hit) == 1, f"{prefix[:40]}… 命中 {len(hit)} 行"
    lines.insert(hit[0] + 1, new)
    return "\n".join(lines)


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}")

    t = MP.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D74" in t:
        print("  [跳过] 工作流_主计划.md（已落）")
    else:
        # ⑧ 追加到 D73 决策行 + 末格改写
        assert t.count("报告必须同时印 `n_hessian_fail`。 | 探针") == 1
        t = t.replace("报告必须同时印 `n_hessian_fail`。 | 探针",
                      "报告必须同时印 `n_hessian_fail`。" + D73_CODE_TAIL + " | 探针")
        assert t.count(D73_LASTCELL_OLD) == 1
        t = t.replace(D73_LASTCELL_OLD, D73_LASTCELL_NEW)
        t = insert_after(t, "| **D73** | 2026-10-17 |", D74)
        t = insert_after(t, "| 2026-10-17 | **8**（LOO 口径根因 → D73） |", D74_PROGRESS)
        t = insert_after(t, "| 2026-10-17 | **新增 D73：被试层 PSIS-LOO 结构性不可估**", D74_CHANGELOG)
        t = insert_after(t, "| `1_Code/DDM_Core/hier.py`（**D73**：", D74_FILE_ROW)
        if APPLY:
            MP.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] 工作流_主计划.md")

    t = S8.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D74" in t:
        print("  [跳过] Stage8_建模与验证方案.md（已落）")
    else:
        anchor = ("- ⇒ **口径（D73）**：模型比较的 `ΔELPD` 用**试次层**矩阵（`n_obs` = 总试次）；"
                  "**被试层**留一交给`loo_bruteforce`（小 N，金标准）或 K-fold（大 N）。")
        assert t.count(anchor) == 1
        # 口径行末句之后追加「已落成可切换口径」
        t = t.replace(anchor, anchor + "\n" + S8_CODE_BULLET, 1)
        t = insert_after(t, "| `1_Code/DDM_Core/hier.py`（LOO 口径根因，D73） |", S8_S9_ROWS[0])
        t = insert_after(t, "| `1_Code/DDM_Core/stage8_run.py --loo-level trial`（D73 ⑧） |", S8_S9_ROWS[1])
        t = insert_after(t, "17. ❗ **被试层 PSIS-LOO 不可估，不是「被试太少」（D73）**", S8_S11_18)
        t = insert_after(t, "| v1.6 | 2026-10-17 |", S8_VERSION)
        if APPLY:
            S8.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] Stage8_建模与验证方案.md")

    t = RD.read_text(encoding="utf-8")
    assert "\r" not in t
    if "| 58 |" in t:
        print("  [跳过] README.md（已落）")
    else:
        old5 = ("   `n_hessian_fail`，PSIS 记为失败。牙齿 `_scratch/check_loo.py` **17 → 21/21**（E1 不抛异常、\n"
                "   E2 记 −inf、E3 计数逐格累加、E4 该列被计为失败且不污染其他列）。")
        assert t.count(old5) == 1
        t = t.replace(old5, old5 + "\n" + RD_ITEMS)
        lines = t.split("\n")
        i57 = [i for i, ln in enumerate(lines) if ln.startswith("| 57 | ✅")]
        assert len(i57) == 1
        lines.insert(i57[0] + 1, RD_ITEM58)
        t = "\n".join(lines)
        if APPLY:
            RD.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
