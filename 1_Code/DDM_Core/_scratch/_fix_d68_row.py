# -*- coding: utf-8 -*-
"""把主计划里 D68 决策行补成 5 列（`# | 日期 | 决策 | 依据 | 影响`）。

原行只有 3 列 ⇒ `check_table_integrity.py` 报 L493「竖线数不一致（表头 6，本行 4）」。
"""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MP = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "工作流_主计划.md"

OLD_MARK = "| **D68** | 2026-10-17 |"
DECISION = (
    "✅ **把「超参数 Hessian 正不正定」从一句提醒变成报告里的判据行，并量出「不正定」对 σ 的实际破坏："
    "本次收敛 σ 的末轮区间含 2.27e+03**。"
    "① 缺口：D65 的 §11 第 13 条只写「必须同报特征值谱与 `n_flipped`」，**没说后果**，读者会以为记一笔就行；"
    "而 `1_Code/DDM_Core/hier.py::subject_map_laplace` 把非正特征值抬到 "
    "`floor = max(1e-8·max abs(λ), 1e-12)` 再取逆 ⇒ 该方向方差 ≈ 1/floor（可到 1e5 量级），"
    "而层级 σ² 的定义就是 `mean[(x − μ)² + Cov_kk]` ⇒ **一个被抬过的方向就能把 σ 撑到没有意义**。"
    "② 代码：`1_Code/DDM_Core/stage8_run.py::render_group` 每个模型多印一行「超参数 Hessian」——"
    "正定 ⇒ 报特征值区间并写「**正定**」；非正定 ⇒ ⛔ 写「**本次的 σ（被试间 SD）不得解读**」"
    "+ `floor` 公式 + `1/floor` 的数 + **本次收敛 σ 的末轮区间**。"
    "③ 牙齿：`_scratch/check_stage8_run.py` 加 **A11**（非正定 ⇒ 必须含「1/4」「不得解读」「1/floor」）"
    "与 **A12**（正定 ⇒ 只许报「正定」），**23/23 → 25/25**。"
    "④ 未测：非正定**是不是 N 依赖**（扫描探针 `_scratch/_probe_hess_scaling.py` 在跑 N ∈ {3,6,12,24}），"
    "结果尚未回填 ⇒ 只能写「N=3 实测不正定」，不能写「N 大了就会好」。"
)
BASIS = (
    "干跑件 `_scratch/stage8_synth3_dryrun/stage8_results.json` 实测：M-T1 `n_flipped` = **1/16**、"
    "特征值 ∈ [−0.203, 229] ⇒ `floor` = 2.29e-06、`1/floor` ≈ **4.37e+05**、收敛 σ ∈ [**0.0127, 2.27e+03**]"
    "（σ 已无意义）；M-T3 `n_flipped` = 0/14、特征值 ∈ [0.0199, 231]、σ ∈ [6.65e-06, 2.95]。"
    "自测日志 `_scratch/_check_stage8_run_console.txt`（25/25、exit 0）"
)
IMPACT = (
    "论文里凡要报「被试间 SD（σ）」的地方，必须先看报告的「超参数 Hessian」行；"
    "若它是 ⛔ 档，则 σ 整列不得报（改 `hyper_method` 或加人数后重算）。"
    "LOO/ELPD 不受影响（抬升发生在被试层协方差，边际是逐被试 log-lik）"
)
ROW = f"| **D68** | 2026-10-17 | {DECISION} | {BASIS} | {IMPACT} |"

lines = MP.read_text(encoding="utf-8").split("\n")
hits = [i for i, ln in enumerate(lines) if ln.startswith(OLD_MARK)]
assert len(hits) == 1, f"命中 {len(hits)} 次"
i = hits[0]
if lines[i] == ROW:
    print("[跳过] 已是 5 列")
else:
    assert lines[i].count("|") == 4, f"原行竖线数 {lines[i].count('|')}（预期 4）"
    lines[i] = ROW
    MP.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[替换] L{i+1} 补成 5 列（新行竖线数 = {ROW.count('|')}）")
assert ROW.count("|") == 6, ROW.count("|")
