"""把决策 D65 落进四份文档（Stage 8 合成数据端到端干跑）。

D65 的事实（全部来自两次实跑，可复现）：

1. `stage8_run.py` 在**合成数据**上**端到端跑通**：读数据 → 两个模型层级拟合
   （analytic 超参数 Hessian）→ 被试层 PSIS-LOO → 模型比较 → 分单元 PPC →
   写 `stage8_report.md` + `stage8_results.json`。两次运行（主配置 / 小配置）
   均正常结束，无异常退出。
2. ❗ **成本预估器低估 3–4 倍**：主配置预估 29.4 min、实测 5597.9 s（93.3 min，
   ×3.2）；小配置预估 13.2 min、实测 3013.2 s（50.2 min，×3.8）。
3. ❗ **D52 的 `p_loo` 闸门在真实运行器里是承重的**：小配置两个模型
   `k_max` 全 **0.000**、`n_k_gt_bad` 全 **0/3**（只看 `k_max` 会判「可报」），
   而 `p_loo/n_obs` = **72.7 / 48.2** ⇒ 报告判「⛔ 本组 LOO 无效」。
4. ❗ **新数值健康事实**：主配置 `n_degenerate_nonfinite` = **54**（M-T1）/
   **16**（M-T3），而 `n_nonfinite_loglik` 是 **0** —— 非有限的目标函数求值
   不进那个计数；同时 scipy `_numdiff` 报 `RuntimeWarning: invalid value
   encountered in subtract`（D51 同族，但在 `n_x = 25` 就出现）。
5. ❗ **analytic 超参数 Hessian 在 N=3 上并非必正定**：M-T1 最小特征值
   **−0.2031**、`n_flipped = 1`（协方差被抬过）；M-T3 最小特征值 **+0.0199**、
   `n_flipped = 0`。
6. **合成数据不是 DDM 生成的**（`_scratch/make_fake_pilot.py` 是按
   `Exp_Design_Formal.m` 规则表转录的：对数正态 RT、正确率固定 0.75、
   刺激内按键均匀分布）⇒ PPC 的系统性失配（遗漏率观测 0.06–0.09 vs 预测
   0.19–0.26、`rt_p50` 观测 0.70 vs 预测 0.60）是**阴性对照成功**，
   不得当作模型批评的证据。
7. `stage8_manifest.json` 只在「人数超过批量闸门」时才写（`stage8_run.py`
   L425–434）；正常运行的产物是报告 + 结果 JSON 两件 —— 干跑目录里没有
   manifest 是**设计如此**。

用法
----
    python -X utf8 -u 1_Code/DDM_Core/_scratch/_apply_d65.py            # 干跑
    python -X utf8 -u 1_Code/DDM_Core/_scratch/_apply_d65.py --apply    # 真写
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RDM = REPO / "1_Code" / "DDM_Core" / "README.md"

APPLY = "--apply" in sys.argv


def load(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def save(p: Path, lines: list[str]) -> None:
    if not APPLY:
        print(f"  [干跑] 将写 {p.relative_to(REPO)}（{len(lines)} 行）")
        return
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"  [写入] {p.relative_to(REPO)}（{len(lines)} 行）")


def n_sep(line: str) -> int:
    return line.count("|")


def idx_of(lines: list[str], needle: str, what: str) -> int:
    for i, ln in enumerate(lines):
        if needle in ln:
            return i
    raise SystemExit(f"❗ 找不到锚点：{what}（needle={needle!r}）")


def ins_after(lines: list[str], anchor_i: int, new: list[str], what: str) -> None:
    """在 anchor 后插入若干行；新行竖线数必须与锚点相同（表格行）。"""
    if not isinstance(new, list):
        raise SystemExit(f"❗ {what}：new 必须是 list，收到 {type(new).__name__}")
    base = n_sep(lines[anchor_i])
    for ln in new:
        if n_sep(ln) != base:
            raise SystemExit(
                f"❗ {what}：新行竖线数 {n_sep(ln)} != 锚点 {base} -> {ln[:80]}")
    lines[anchor_i + 1:anchor_i + 1] = new


def append_in_row(lines: list[str], row_i: int, suffix: str, what: str) -> None:
    """把 suffix 追加到某个表格行最后一个单元格里。"""
    if "|" in suffix:
        raise SystemExit(f"❗ {what}：后缀不得含竖线")
    ln = lines[row_i].rstrip()
    if not ln.endswith("|"):
        raise SystemExit(f"❗ {what}：目标行不以竖线结尾")
    lines[row_i] = ln[:-1] + suffix + "|"


# ---------------------------------------------------------------- 主计划
D65_DECISION = (
    "| **D65** | 2026-10-17 | ✅ **Stage 8 全量运行器在合成数据上端到端跑通，"
    "并抓出四处「只在实跑里才现形」的事实**。① 链路：读数据 → 两模型层级拟合"
    "（analytic 超参数 Hessian）→ 被试层 PSIS-LOO → 模型比较 → 分单元 PPC → "
    "报告 + 结果 JSON，主配置 **5597.9 s**、小配置 **3013.2 s**，两次都正常结束。"
    "② ❗ **成本预估器低估 3–4 倍**（29.4 → 93.3 min、13.2 → 50.2 min）⇒ "
    "正式采集前的时间计划必须按 ×4 留余量。③ ❗ **D52 的 `p_loo` 闸门在真实"
    "运行器里承重**：小配置 `k_max` 全 **0.000**、`n_k_gt_bad` 全 0，而 "
    "`p_loo/n_obs` = **72.7 / 48.2** ⇒ 只看 `k_max` 会误判「可报」。"
    "④ ❗ `n_degenerate_nonfinite` = **54 / 16** 而 `n_nonfinite_loglik` = **0** "
    "⇒ 非有限目标函数求值不进那个计数（D51 同族，`n_x = 25` 即出现）；"
    "analytic 超参数 Hessian 在 N=3 上**并非必正定**（M-T1 最小特征值 −0.2031、"
    "`n_flipped = 1`）。⑤ **合成数据不是 DDM 生成的**（规则表：对数正态 RT、"
    "正确率固定 0.75）⇒ PPC 的系统性失配是**阴性对照成功**，不得当模型批评。"
    "⑥ `stage8_manifest.json` 只在人数超批量闸门时才写 ⇒ 干跑目录里没有它是设计如此。"
    " | `1_Code/DDM_Core/_scratch/stage8_synth3_dryrun/`（干跑 I 产物）与 "
    "`1_Code/DDM_Core/_scratch/stage8_synth3_lean/`（干跑 II 产物）；落纸见 "
    "`1_Code/DDM_Core/README.md` §8.40 与 `Stage8_建模与验证方案.md` §9/§11/§12 "
    " | 判据带宽、推荐点、交付件依据件**一个都没动**（只加 Stage 8 的运行证据与三条限制）；"
    "用户侧 Stage 1/6/7 仍在等 |"
)

D65_PROGRESS = (
    "| 2026-10-17 | **8**（全量运行器合成干跑 → D65） | **把 Stage 8 的"
    "「能不能在真实数据到手后跑起来」从「应该能」变成「实测跑过」**。主配置"
    "（3 人、`n_em` 5、`n_draws` 30、`n_x` 25、PPC 2）**5597.9 s**、小配置"
    "（`n_em` 3、`n_draws` 12、`n_x` 21、PPC 1）**3013.2 s**，产物齐全；"
    "同时抓出四条只在实跑里现形的事实（成本低估 3–4 倍、`p_loo` 闸门承重、"
    "`n_degenerate_nonfinite` 隐形、N=3 的 Hessian 非正定）与一条判读纪律"
    "（合成数据非 DDM ⇒ PPC 失配是阴性对照）。 | 见 D65 决策行；"
    "证据 = 两次运行目录 + `1_Code/DDM_Core/README.md` §8.40 | 下一步：真实数据到手后"
    "按 §10 的四步回填；用户侧 Stage 1/6/7 仍在等 |"
)

D65_CHANGELOG = (
    "| 2026-10-17 | **新增 D65：Stage 8 全量运行器在合成数据上端到端跑通"
    "（5597.9 s / 3013.2 s），并实测成本低估 3–4 倍、`p_loo` 闸门承重、"
    "`n_degenerate_nonfinite` 隐形、N=3 的 analytic Hessian 可非正定；"
    "合成数据非 DDM ⇒ PPC 失配只作阴性对照（§8.40；落点 = "
    "`5_Reference/08_工作流/Stage8_建模与验证方案.md` §9/§11/§12 + "
    "`1_Code/DDM_Core/README.md` §8.40 与 §9 第 49 项）** |"
)

D65_EVIDENCE = (
    "| `1_Code/DDM_Core/_scratch/stage8_synth3_dryrun/stage8_report.md`（**新**，331 行）"
    " + `stage8_results.json`（**新**） + `1_Code/DDM_Core/_scratch/"
    "stage8_synth3_lean/stage8_report.md`（**新**） + `_stage8_lean_console.txt`（**新**） | "
    "Stage 8 两次合成干跑的产物：主配置 5597.9 s（M-T1 3015.1 s / M-T3 2553.8 s）、"
    "小配置 3013.2 s（1696.1 / 1305.9）；两次的四条 LOO 行都是「⛔ 本组 LOO 无效」 |"
)


def do_master_plan() -> None:
    p = MP
    lines = load(p)
    i_dec = idx_of(lines, "| **D64** | 2026-10-17 |", "主计划 §5 D64 决策行")
    ins_after(lines, i_dec, [D65_DECISION], "主计划 §5 D65 决策行")
    save(p, lines)
    lines = load(p)
    i_prg = idx_of(lines, "| 2026-10-17 | **9**（`√2` 的同方差前提", "主计划 §6 D64 进度行")
    ins_after(lines, i_prg, [D65_PROGRESS], "主计划 §6 D65 进度行")
    save(p, lines)
    lines = load(p)
    i_chg = idx_of(lines, "| 2026-10-17 | **新增 D64：", "主计划 §7 D64 变更日志")
    ins_after(lines, i_chg, [D65_CHANGELOG], "主计划 §7 D65 变更日志")
    save(p, lines)
    lines = load(p)
    i_ev = idx_of(lines, "`1_Code/AutoRA_SPE/_scratch_pair_corr_nfim12_u8.txt`（**新**）",
                  "主计划附录 D64 证据行")
    ins_after(lines, i_ev, [D65_EVIDENCE], "主计划附录 D65 证据行")
    save(p, lines)


# ---------------------------------------------------------------- Stage 8 方案
S8_TABLE_ROWS = [
    "| `1_Code/DDM_Core/stage8_run.py`（干跑 I） | 全链路端到端：读数据 → 两模型层级拟合"
    " → 被试层 LOO → 模型比较 → 分单元 PPC → 报告 | 3 人（142/143/141 试次）、"
    "`n_em` 5、`n_draws` 30、`n_x` 25、PPC 2、`analytic`：**5597.9 s**；M-T1 "
    "ELPD −521.183 ± 7.258、`p_loo` 185.369、`k_max` 5.000；M-T3 −350.223 ± 16.448、"
    "36.221、4.825；两行都被判「⛔ 本组 LOO 无效」（`p_loo/n_obs` 61.8 / 12.1） |",
    "| `1_Code/DDM_Core/stage8_run.py`（干跑 II） | 同上（更小配置，用来量成本与查闸门） | "
    "3 人、`n_em` 3、`n_draws` 12、`n_x` 21、PPC 1：**3013.2 s**；两个模型 `k_max` "
    "全 **0.000**、`n_k_gt_bad` 全 0，而 `p_loo/n_obs` = **72.7 / 48.2** ⇒ 被判无效 "
    "——**只读 `k_max` 会误判「可报」**（D52 在真实运行器里的现场证据） |",
]

S8_LIMITS = [
    "11. ❗ **成本预估器低估 3–4 倍**（D65）：主配置预估 29.4 min / 实测 5597.9 s（93.3 min，"
    "×3.2）；小配置预估 13.2 min / 实测 3013.2 s（50.2 min，×3.8）。它的标定口径是"
    "「48 试次/人、`n_x=41`、单次似然 34 ms」，而合成干跑每人 141–143 试次、正式数据是 "
    "576 试次/人 ⇒ **正式采集的时间计划必须按预估 ×4 留余量**，且这还不含重复运行的次数。",
    "12. ❗ **合成干跑的数据不是 DDM 生成的**（D65）：`_scratch/make_fake_pilot.py` 按 "
    "`Exp_Design_Formal.m` 的规则表转录（RT = `T + lognormvariate(−0.5, 0.45)`、正确率固定 "
    "0.75、刺激内按键均匀分布）。因此干跑里 PPC 的系统性失配（遗漏率观测 0.06–0.09 vs "
    "预测 0.19–0.26、`rt_p50` 观测 0.70 vs 预测 0.60）是**阴性对照成功**：它说明 PPC 能"
    "认出「这份数据不是这个模型生成的」，**不能**反过来当作对模型的批评。要在 DDM 数据上验"
    "模型恢复，必须用 `1_Code/DDM_Core/simulate.py` 那一套生成器。",
    "13. ❗ **报数值健康时必须同时报 `n_degenerate_nonfinite`**（D65）：主配置它是 "
    "**54**（M-T1）/ **16**（M-T3），而 `n_nonfinite_loglik` = **0** —— 非有限的目标函数"
    "求值不进那个计数，并伴 scipy `_numdiff` 的 `RuntimeWarning: invalid value encountered "
    "in subtract`（D51 同族，但 `n_x = 25` 就出现）。另：`analytic` 超参数 Hessian 在 N=3 上"
    "**并非必正定**（M-T1 最小特征值 −0.2031、`n_flipped = 1`；M-T3 +0.0199、0）⇒ §11 第 2 条"
    "的「必须同报特征值谱与 `n_flipped`」不是仪式。",
]

S8_V12 = (
    "| v1.2 | 2026-10-17 | **§9 加两行合成数据端到端干跑证据**（`stage8_run.py` 全链路跑通，"
    "5597.9 s / 3013.2 s，产物含报告与结果 JSON）；`check_loo.py` 行补记 D63 的 "
    "**17/17**（新增 D1–D3 三条 ArviZ 复核断言）。**§11 加第 11–13 条限制**（成本低估 3–4 倍、"
    "合成数据非 DDM ⇒ PPC 失配只作阴性对照、必须同报 `n_degenerate_nonfinite` 与 Hessian "
    "特征值谱）。决策 D65 |"
)


def do_stage8() -> None:
    p = S8
    lines = load(p)
    i_row = idx_of(lines, "| `_scratch/diag_gpd_bias.py` |", "Stage8 §9 末行")
    ins_after(lines, i_row, S8_TABLE_ROWS, "Stage8 §9 两条干跑行")
    save(p, lines)
    lines = load(p)
    i_loo = idx_of(lines, "| `1_Code/DDM_Core/loo.py` |", "Stage8 §9 loo 行")
    append_in_row(lines, i_loo, "；D63 加 D1–D3 三条 ArviZ 复核断言后 **17/17**",
                  "Stage8 §9 loo 行补记")
    save(p, lines)
    lines = load(p)
    i_lim = idx_of(lines, "10. **`n_x`（似然网格分辨率）必须写进任何性能/退化结论**",
                   "Stage8 §11 第 10 条")
    ins_after(lines, i_lim, S8_LIMITS, "Stage8 §11 第 11–13 条")
    save(p, lines)
    lines = load(p)
    i_v = idx_of(lines, "| v1.1 | 2026-10-14 |", "Stage8 §12 v1.1 行")
    ins_after(lines, i_v, [S8_V12], "Stage8 §12 v1.2 行")
    save(p, lines)


# ---------------------------------------------------------------- DDM README
RM_840 = [
    "## 8.40 Stage 8 全量运行器在合成数据上端到端跑通（2026-10-17，D65）",
    "",
    "### 8.40.1 动机",
    "",
    "Stage 8 的代码（`1_Code/DDM_Core/hier.py`、`stage8.py`、`loo.py`、"
    "`stage8_run.py`）此前只有**分段自测**（`check_hier.py` / `check_stage8.py` / "
    "`check_loo.py` / `check_stage8_run.py` 18/18），从来没有**把整条链路在"
    "同一份数据上跑通过**：拟合 → LOO → 模型比较 → PPC → 报告。真实数据到手前"
    "必须知道「跑得起来吗、要多久、闸门会不会响」。",
    "",
    "### 8.40.2 两次运行",
    "",
    "| 项 | 干跑 I（主配置） | 干跑 II（小配置） |",
    "|---|---|---|",
    "| 数据 | `--synthetic 3 --synth-n-rep 3 --seed 7`，142/143/141 试次 | 同左，`--seed 11` |",
    "| 配置 | `n_em` 5、`n_draws` 30、`n_x` 25、PPC 2、`analytic` | `n_em` 3、`n_draws` 12、"
    "`n_x` 21、PPC 1、`analytic` |",
    "| 预估 | 0.49 h（29.4 min） | 0.22 h（13.2 min） |",
    "| **实测** | **5597.9 s（93.3 min，×3.2）** | **3013.2 s（50.2 min，×3.8）** |",
    "| M-T1 | 3015.1 s、ELPD −521.183 ± 7.258、`p_loo` 185.369、`k_max` 5.000 | "
    "1696.1 s、−541.007 ± 17.573、218.05、0.000 |",
    "| M-T3 | 2553.8 s、−350.223 ± 16.448、36.221、4.825 | 1305.9 s、−462.861 ± 17.618、"
    "144.57、0.000 |",
    "| 判词 | 两模型都「⛔ 本组 LOO 无效」 | 同左 |",
    "| PPC | 全局 6–7/12 在带内、分单元 15–17/20 | 6–7/12、13–16/20 |",
    "",
    "产物：`stage8_report.md`（1.9–9.2 万字符）+ `stage8_results.json`。"
    "**没有 `stage8_manifest.json` 是设计如此** —— 它只在「人数超过批量闸门"
    "（`_BATCH_WARN_N`）」时才写（`stage8_run.py` L425–434）。",
    "",
    "### 8.40.3 四条只在实跑里现形的事实",
    "",
    "1. ❗ **成本预估器低估 3–4 倍**。预估口径是「48 试次/人、`n_x=41`、单次似然 34 ms」，"
    "而干跑每人 141–143 试次、正式数据 576 试次/人 ⇒ 时间计划按 ×4 留余量。",
    "2. ❗ **D52 的 `p_loo` 闸门承重**。小配置两个模型 `k_max` 全 **0.000**、"
    "`n_k_gt_bad` 全 **0/3**（只看这两条会判「可报 ΔELPD」），而 `p_loo/n_obs` = "
    "**72.7 / 48.2** ⇒ 判无效。这是 D52 第一次在**真实运行器**（而不是自测夹具）里"
    "救回一次误判。",
    "3. ❗ **`n_degenerate_nonfinite` 是隐形的**：主配置 **54**（M-T1）/ **16**（M-T3），"
    "而 `n_nonfinite_loglik` = **0**；同时 scipy `_numdiff` 报 "
    "`RuntimeWarning: invalid value encountered in subtract`（D51 同族，`n_x = 25` 即出现）。",
    "4. ❗ **`analytic` 超参数 Hessian 在 N=3 上并非必正定**：M-T1 最小特征值 **−0.2031**、"
    "`n_flipped = 1`（协方差被抬过）；M-T3 **+0.0199**、`n_flipped = 0`。"
    "§11 第 2 条要求「必须同报谱与 `n_flipped`」因此是硬要求。",
    "",
    "### 8.40.4 一条判读纪律：合成数据不是 DDM 生成的",
    "",
    "`_scratch/make_fake_pilot.py` 按 `Exp_Design_Formal.m` 的**规则表转录**生成数据："
    "RT = `T + lognormvariate(−0.5, 0.45)`、正确率固定 0.75、刺激内按键均匀分布 —— "
    "**没有 DDM 证据累积过程**。所以干跑里 PPC 的系统性失配（遗漏率观测 0.06–0.09 vs "
    "预测 0.19–0.26；`rt_p50` 观测 0.70 vs 预测 0.60）是**阴性对照成功**：PPC 认出了"
    "「这份数据不是这个模型生成的」。**不得**反过来把这几张表当作对 M-T1/M-T3 的批评；"
    "要验模型恢复，必须用 `1_Code/DDM_Core/simulate.py` 那一套生成器。",
    "",
    "### 8.40.5 尚未做",
    "",
    "1. **在 DDM 生成的数据上**做同一套端到端干跑（合成数据换成 `simulate.py`，"
    "可同时验参数恢复与 PPC 的**正确阳性**能力）。",
    "2. 正式数据（4 组 × ~40 人）的批处理时间表：按 ×4 余量估，576 试次/人远超本次"
    "干跑，需在真实规模上再测一次。",
    "3. `n_degenerate_nonfinite` 目前只**计数**，没有定位到「哪一步、哪个参数方向」；"
    "若要修 `_numdiff` 退化（D51 同族），应先把计数拆细。",
    "",
]

RM_ITEM_49 = (
    "| 49 | ✅ **Stage 8 全量运行器在合成数据上端到端跑通；成本低估 3–4 倍、`p_loo` 闸门"
    "承重、`n_degenerate_nonfinite` 隐形、N=3 的 analytic Hessian 可非正定（D65，§8.40）** | "
    "干跑 I 5597.9 s（M-T1 3015.1 s / M-T3 2553.8 s）、干跑 II 3013.2 s（1696.1 / 1305.9）；"
    "干跑 II 的 `k_max` 全 0.000 而 `p_loo/n_obs` 72.7 / 48.2 ⇒ 判无效；"
    "`n_degenerate_nonfinite` 54 / 16 而 `n_nonfinite_loglik` 0；M-T1 最小特征值 −0.2031、"
    "`n_flipped` 1 |"
)


def do_ddm_readme() -> None:
    p = RDM
    lines = load(p)
    i9 = idx_of(lines, "## 9. 尚未做", "DDM README §9 标题")
    lines[i9:i9] = RM_840
    save(p, lines)
    lines = load(p)
    i48 = idx_of(lines, "| 48 | ✅ **`2·√2·sd` 的 `√2` 取常数", "DDM README §9 第 48 项")
    ins_after(lines, i48, [RM_ITEM_49], "DDM README §9 第 49 项")
    save(p, lines)


def main() -> int:
    print(f"{'=' * 92}\nD65 落纸{'（--apply）' if APPLY else '（干跑）'}\n{'=' * 92}")
    # 幂等闸：四份文档里只要主计划已经有 D65 决策行，就整体跳过
    if "| **D65** | 2026-10-17 |" in MP.read_text(encoding="utf-8"):
        print("  [跳过] 主计划里已有 D65 —— 本次什么都不写（幂等）")
        return 0
    do_master_plan()
    do_stage8()
    do_ddm_readme()
    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
