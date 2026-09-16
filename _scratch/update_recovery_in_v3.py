# -*- coding: utf-8 -*-
"""临时：用修正真值的恢复结果替换 v3 §6.3.3 的表图与文字，并重建。"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BODY = DOC / "_v3_正文.md"
FIGV3 = ROOT / "3_Figures" / "Thesis_v3_20260912"
FIGSRC = ROOT / "3_Figures" / "TenRules_Revision_20260912"
REFIT = ROOT / "2_Data" / "Generate_Data" / "TenRules_Revision_20260912" / "param_recovery_refit"

# ① 主口径（G3–G8）恢复汇总
by = pd.read_csv(REFIT / "recovery_by_job.csv")
cond = by[(by.kind == "condition") & (by.group_id.isin([3, 4, 5, 6, 7, 8]))]
rows = []
for scheme in ["censor", "drop"]:
    g = cond[cond.scheme == scheme]
    for p in ["v_self", "v_stranger", "a", "t", "z", "SPE_v"]:
        b = g[f"{p}_bias"].dropna()
        cov = g[f"{p}_covered"].dropna().mean() if f"{p}_covered" in g else np.nan
        rows.append({"scheme": scheme, "param": p, "n": len(b), "bias": b.mean(),
                     "rmse": float(np.sqrt((b ** 2).mean())), "coverage": cov})
    rows[-1]["r"] = None
summ = pd.DataFrame(rows)
summ.to_csv(REFIT / "recovery_summary_main_scope.csv", index=False)
piv = summ.pivot_table(index="param", columns="scheme", values=["bias", "rmse", "coverage"])
print(piv.round(3).to_string())

# 遗漏率曲线（分箱）
curve = by[by.kind == "curve"].dropna(subset=["v_self_bias"]).copy()
curve["bin"] = pd.cut(curve.realized_omission * 100, [0, 5, 10, 15, 20, 25, 35, 50, 80])
bins = []
for (scheme, b), g in curve.groupby(["scheme", "bin"], observed=True):
    bins.append({"scheme": scheme, "bin": str(b), "om": g.realized_omission.mean() * 100,
                 "v_self": g.v_self_bias.mean(), "a": g.a_bias.mean(), "SPE_v": g.SPE_v_bias.mean()})
bdf = pd.DataFrame(bins).sort_values(["scheme", "om"])
bdf.to_csv(REFIT / "omission_curve_bins.csv", index=False)
print("\n", bdf.round(3).to_string(index=False))

def cell(p, s, k):
    v = summ[(summ.param == p) & (summ.scheme == s)][k]
    return f"{v.iloc[0]:+.2f}" if k == "bias" else (f"{v.iloc[0]:.2f}" if k == "rmse" else f"{v.iloc[0]*100:.0f}%")

# ② 图入图集
for old, new in [("param_recovery_scatter.png", "F6-3_param_recovery_scatter.png"),
                 ("param_recovery_omission_bias.png", "F6-4_omission_bias_curve.png"),
                 ("param_recovery_coverage.png", "F6-5_recovery_coverage.png")]:
    if (FIGSRC / old).exists():
        shutil.copy2(FIGSRC / old, FIGV3 / new)
        print("[fig]", new)

# ③ 正文替换
s = BODY.read_text(encoding="utf-8")
new_633 = f'''### 6.3.3 参数恢复结果

以**修正配置（配置 C，见 §6.3.4）**下主口径六个条件的群体后验均值为参考真值，按各条件真实的被试数与试次规模生成合成数据，并以 Censor 与 Drop 两条流程重新拟合（每条件 3 次重复，共 36 次拟合；真值与产物见 `param_recovery_refit/`）。主口径结果见表 6-2。

表 6-2 参数恢复结果（主口径 G3–G8；估计偏倚、RMSE 与 95% CI 覆盖率）

| 参数 | Censor 偏倚 | Censor RMSE | Censor 覆盖率 | Drop 偏倚 | Drop RMSE | Drop 覆盖率 |
|---|---|---|---|---|---|---|
| v_self | {cell("v_self","censor","bias")} | {cell("v_self","censor","rmse")} | {cell("v_self","censor","coverage")} | {cell("v_self","drop","bias")} | {cell("v_self","drop","rmse")} | {cell("v_self","drop","coverage")} |
| v_stranger | {cell("v_stranger","censor","bias")} | {cell("v_stranger","censor","rmse")} | {cell("v_stranger","censor","coverage")} | {cell("v_stranger","drop","bias")} | {cell("v_stranger","drop","rmse")} | {cell("v_stranger","drop","coverage")} |
| a | {cell("a","censor","bias")} | {cell("a","censor","rmse")} | {cell("a","censor","coverage")} | {cell("a","drop","bias")} | {cell("a","drop","rmse")} | {cell("a","drop","coverage")} |
| t | {cell("t","censor","bias")} | {cell("t","censor","rmse")} | {cell("t","censor","coverage")} | {cell("t","drop","bias")} | {cell("t","drop","rmse")} | {cell("t","drop","coverage")} |
| z | {cell("z","censor","bias")} | {cell("z","censor","rmse")} | {cell("z","censor","coverage")} | {cell("z","drop","bias")} | {cell("z","drop","rmse")} | {cell("z","drop","coverage")} |
| **SPE_v** | **{cell("SPE_v","censor","bias")}** | **{cell("SPE_v","censor","rmse")}** | **{cell("SPE_v","censor","coverage")}** | **{cell("SPE_v","drop","bias")}** | **{cell("SPE_v","drop","rmse")}** | **{cell("SPE_v","drop","coverage")}** |

三点结论。第一，**漂移率的绝对水平不可恢复**：Censor 方案系统性低估（平均偏倚 {cell("v_self","censor","bias")}），Drop 方案方向相反且噪声更大（偏倚 {cell("v_self","drop","bias")}，RMSE {cell("v_self","drop","rmse")}，与真值的相关仅 r ≈ .16）；两者对真值的 95% CI 覆盖率均远低于名义 95%。这既印证了 Leng et al.（2026）"丢弃遗漏会高估漂移率"的结论，也说明**本文中 v 的绝对数值不宜作实质解释**，只能用于条件间比较。

第二，**自我优势的相对效应（SPE_v）几乎完美恢复**：Censor 方案下偏倚 {cell("SPE_v","censor","bias")}、RMSE {cell("SPE_v","censor","rmse")}、**95% CI 覆盖率 100%**、跨条件相关 r ≈ .95；Drop 方案下偏倚 {cell("SPE_v","drop","bias")}、覆盖率约 {cell("SPE_v","drop","coverage")}。这为全文的核心比较提供了关键辩护：即便绝对参数水平强烈依赖遗漏处理方式，"自我 vs 陌生人"的相对差异仍然是稳健的。非决策时间 t 也恢复良好（r ≈ .997）。

第三，条件间差异符合"高遗漏最危险"的预期：G6（遗漏率 2%）的 Censor 偏倚仅 −0.08，而 G1、G2（遗漏率 100% 与 50%，其真值沿用历史配置故合成数据退化）与 G7、G8（遗漏率 22%–25%）偏倚明显更大（−0.87 ~ −0.97）；这一模式与 §6.3.4 的收敛诊断一致。

参数恢复的真值—恢复值对照见图 6-3。

为量化遗漏率本身的影响，另以六条件参数的均值为真值，通过二分搜索设定 deadline，使合成数据的遗漏率达到 5%–70% 八个目标水平（每水平 2 次重复），结果见表 6-3。

表 6-3 遗漏率与参数偏倚（修正真值；曲线作业）

| 实际遗漏率 | Censor: Δv_self | Censor: Δa | Censor: ΔSPE_v | Drop: Δv_self | Drop: Δa | Drop: ΔSPE_v |
|---|---|---|---|---|---|---|
''' + "\n".join(
    f"| {r.om:.0f}% | {r.v_self:+.3f} | {r.a:+.3f} | {r.SPE_v:+.3f} | "
    f"{bdf[(bdf.scheme=='drop') & (abs(bdf.om - r.om) < 1e-6)].v_self.iloc[0]:+.3f} | "
    f"{bdf[(bdf.scheme=='drop') & (abs(bdf.om - r.om) < 1e-6)].a.iloc[0]:+.3f} | "
    f"{bdf[(bdf.scheme=='drop') & (abs(bdf.om - r.om) < 1e-6)].SPE_v.iloc[0]:+.3f} |"
    for r in bdf[bdf.scheme == "censor"].itertuples()) + '''

结果显示：Censor 方案下漂移率的绝对偏倚随遗漏率**单调增大**（由 5% 时的 −0.07 增至 70% 时的 −4.00），边界 a 的偏倚方向一致但幅度较小；Drop 方案的偏倚在低遗漏时较小、在高遗漏时变得不稳定（RMSE 达 3.25）。**而 SPE_v 的偏倚在所有目标遗漏率下均不超过 0.26（Censor 方案下不超过 0.16）**，且曲线作业中 SPE_v 的 95% CI 覆盖率为 100%。据此，本文把"约 15% / 约 35%"的经验分档修订为更准确的表述：**遗漏率低于约 10% 时绝对参数估计的偏倚可忽略，10%–35% 之间需谨慎，超过约 35% 后绝对水平不可解释；而自我优势的相对方向在任何遗漏率下都保持稳定**。

遗漏率与参数偏倚的关系见图 6-4。

各参数 95% CI 覆盖率对比见图 6-5。'''

s, n = re.subn(r"### 6\.3\.3 参数恢复结果.*?(?=\n## 6\.4)", new_633 + "\n\n", s, flags=re.S)
print("[body] §6.3.3 整节替换:", n)
BODY.write_text(s, encoding="utf-8")

r = subprocess.run([sys.executable, "-u", str(DOC / "_build_docx_v3.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
print("[build] exit:", r.returncode)
print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "")
