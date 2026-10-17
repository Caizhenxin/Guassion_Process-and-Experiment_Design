# -*- coding: utf-8 -*-
"""D68 回填：把「非正定是不是 N 依赖」的实测结果写进三份文档。

用法：``python -X utf8 -u _patch_d68_n.py [--apply]``
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

#: A 组四档（DDM、M-T1、seed 7）的归一化最小特征值与 n_flipped
SEQ = ("归一化最小特征值 **−4.202e-03（N=3，1/16）→ −1.362e-03（N=6，1/16）"
       "→ +1.394e-03（N=12，0/16）→ +1.184e-03（N=24，0/16）**")

MP_OLD = ("④ 未测：非正定**是不是 N 依赖**（扫描探针 `_scratch/_probe_hess_scaling.py` 在跑 "
          "N ∈ {3,6,12,24}），结果尚未回填 ⇒ 只能写「N=3 实测不正定」，不能写「N 大了就会好」。")
MP_NEW = (
    "④ ✅ **非正定是不是 N 依赖 = 不是「小样本就会好」**（D68 回填；探针 "
    "`_scratch/_probe_hess_scaling.py` 与 `_scratch/_probe_hess_seedcheck.py`，144 试次/人、"
    "`n_x = 21`、`n_em = 5`、M-T1）：A 组（DDM 数据、seed 7）" + SEQ
    + " ⇒ **符号翻了、量级没变**（四档都在 1e-3），即最平的那个方向一直在，「N 大了」只是让它暂时翻正；"
    "B 组（非 DDM 数据、N=3）三个种子（7/11/99）非正 **1/16、1/16、2/16** 全非正；"
    "而 **A 组 N=3 换 seed=99 即成 0/16** ⇒ 这是**逐数据集的偶发事件**，不是确定的 N 效应。"
    "⇒ 正式数据上必须**逐模型读 `n_flipped`**（= 0 才报 σ），不得凭 N 推断。"
)

S8_OLD = "报告已按此打印（`stage8_run.py::render_group` 的「超参数 Hessian」行）。"
S8_NEW = (
    S8_OLD
    + "**N 依赖实测（D68 回填）**：A 组（DDM、seed 7）" + SEQ
    + " ⇒ 符号翻、量级不变；B 组（非 DDM、N=3）种子 7/11/99 = 1/16、1/16、2/16；"
    "A 组 N=3 换 seed=99 = 0/16 ⇒ **逐数据集偶发**。结论：不得写「小样本现象、N≈40 安全」，"
    "只能写「最平方向随时可能翻负 ⇒ 正式数据上逐模型按 `n_flipped` 判」。"
)

S8_LOG_OLD = "、`check_hier.py` 加 C 组 4 项机制断言（`cov` 该方向 = `1/floor`、负曲率方向众数发散）；"
S8_LOG_NEW = (
    "、`check_hier.py` 加 C 组 4 项机制断言（`cov` 该方向 = `1/floor`、负曲率方向众数发散）、"
    "实测非正定的 N 依赖（A 组归一化最小特征值 **−4.202e-03 → −1.362e-03 → +1.394e-03 → +1.184e-03**，"
    "符号翻而量级不变；换 seed 会翻 ⇒ 逐数据集偶发）；"
)

RD_HEAD = "1. **非正定是不是 N 依赖**：探针"
RD_STOP = "   代价见 D47/D65 的成本表）。"
RD_NEW = [
    "1. ✅ **非正定是不是 N 依赖 = 不是「小样本就会好」**（D68 回填）：探针 "
    "`_scratch/_probe_hess_scaling.py`（A 组 DDM、seed 7）" + SEQ,
    "   ⇒ **符号翻、量级不变**（四档都 1e-3）⇒ 最平方向一直在；B 组（非 DDM、N=3）种子 7/11/99 = "
    "**1/16、1/16、2/16** 全非正；`_scratch/_probe_hess_seedcheck.py` 的 A 组 N=3 换 seed=99 变 **0/16** "
    "⇒ 逐数据集偶发。⇒ 只能「逐模型读 `n_flipped`」，不得凭 N 承诺 σ 可解读。",
    "2. 若正式数据上 `n_flipped ≠ 0`（完全可能，见第 1 条），那一组的 σ 整列作废；"
    "备选是改 `hyper_method=\"fd\"` 重算超参数协方差，代价见 D47/D65 的成本表。",
]

bad = 0


def patch_once(path: Path, what: str, old: str, new: str) -> None:
    global bad
    txt = path.read_text(encoding="utf-8")
    if new in txt:
        print(f"[跳过] {path.name}：{what}（已回填）")
        return
    n = txt.count(old)
    if n != 1:
        print(f"❌ {path.name}：{what} 锚点命中 {n} 次")
        bad += 1
        return
    if APPLY:
        path.write_text(txt.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")


patch_once(MP, "D68 决策行第 ④ 条", MP_OLD, MP_NEW)
patch_once(S8, "§11 第 13 条", S8_OLD, S8_NEW)
patch_once(S8, "§12 v1.4 行", S8_LOG_OLD, S8_LOG_NEW)

# README：整块替换「五、尚未做」的第 1–2 条（跨多行，按行处理）
lines = RD.read_text(encoding="utf-8").split("\n")
start = next((i for i, ln in enumerate(lines) if ln.startswith(RD_HEAD)), None)
if start is None:
    if any(ln.startswith("1. ✅ **非正定是不是 N 依赖") for ln in lines):
        print(f"[跳过] {RD.name}：§8.43 五、尚未做 第 1–2 条（已回填）")
    else:
        print(f"❌ {RD.name}：找不到「五、尚未做」第 1 条")
        bad += 1
else:
    stop = next((i for i, ln in enumerate(lines[start:], start) if ln == RD_STOP), None)
    if stop is None:
        print(f"❌ {RD.name}：找不到第 2 条的结尾行")
        bad += 1
    else:
        if APPLY:
            lines[start:stop + 1] = RD_NEW
            RD.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"[{'写入' if APPLY else '干跑'}] {RD.name}："
              f"§8.43 五、尚未做 第 1–2 条（行 {start + 1}–{stop + 1}）")

sys.exit(1 if bad else 0)
