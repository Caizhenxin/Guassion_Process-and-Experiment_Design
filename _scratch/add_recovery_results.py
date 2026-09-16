# -*- coding: utf-8 -*-
"""临时：写入参数恢复结果（§6.3.3）与三张图，重建 docx。"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BODY = DOC / "_v3_正文.md"
BUILDER = DOC / "_build_docx_v3.py"
FIGV3 = ROOT / "3_Figures" / "Thesis_v3_20260912"
FIGSRC = ROOT / "3_Figures" / "TenRules_Revision_20260912"

# ---------- ① 复制三张图 ----------
for old, new in [("param_recovery_scatter.png", "F6-3_param_recovery_scatter.png"),
                 ("param_recovery_omission_bias.png", "F6-4_omission_bias_curve.png"),
                 ("param_recovery_coverage.png", "F6-5_recovery_coverage.png")]:
    src = FIGSRC / old
    if src.exists():
        shutil.copy2(src, FIGV3 / new)
        print("[fig]", new)
    else:
        print("[fig] 缺失", old)

# ---------- ② 正文 §6.3.3 ----------
s = BODY.read_text(encoding="utf-8")
new_633 = '''### 6.3.3 参数恢复结果

以冻结主口径六个条件的 HDDM 群体后验均值为参考真值，按各条件真实的被试数（10–12 人）与试次规模（每身份 130 试次）生成合成数据，并以 Censor 与 Drop 两条流程重新拟合（每条件重复 3 次，共 36 次拟合）。结果见表 6-2。

表 6-2 参数恢复结果（估计偏倚、RMSE 与 95% CI 覆盖率）

| 参数 | Censor 偏倚 | Censor RMSE | Censor 覆盖率 | Drop 偏倚 | Drop RMSE | Drop 覆盖率 |
|---|---|---|---|---|---|---|
| v_self | −1.34 | 1.64 | 17% | +0.73 | 1.67 | 0% |
| v_stranger | −1.35 | 1.64 | 17% | +0.69 | 1.69 | 0% |
| a | −0.25 | 0.49 | 17% | +0.20 | 1.02 | 11% |
| t | +0.03 | 0.04 | 28% | −0.02 | 0.08 | 11% |
| z | +0.09 | 0.11 | 17% | −0.05 | 0.10 | 6% |
| SPE_v | +0.02 | 0.08 | 100% | +0.04 | 0.19 | 100% |

三点结论。第一，**漂移率的绝对水平不可恢复**：Censor 方案系统性低估（平均偏倚 −1.34），Drop 方案系统性高估（+0.73），两者对真值的 95% CI 覆盖率分别仅为 17% 与 0%。这既直接印证了 Leng et al.（2026）"丢弃遗漏会高估漂移率"的结论，也说明**本文中 v 的绝对数值不宜作实质解释**，只能用于条件间比较。

第二，**自我优势的相对效应（SPE_v）几乎完美恢复**：两种方案下的偏倚均不超过 0.05、RMSE 不超过 0.19、95% CI 覆盖率均为 100%、跨条件相关分别为 r = .97（Censor）与 r = .91（Drop）。这一发现为全文的核心比较提供了关键辩护：即便绝对参数水平强烈依赖遗漏处理方式，"自我 vs 陌生人"的相对差异仍然稳健，因此研究一与研究三基于 SPE_v 的结论是成立的。

第三，条件间差异明显：G6（实际遗漏率 1.2%）的偏倚极小（−0.03），而 G8（v_self ≈ 2.8、a ≈ 2.4、遗漏率 30.7%）的偏倚最大（Censor −2.28 / Drop +3.67），G3、G4 亦明显偏大。高遗漏率、高漂移率与高边界的组合最容易导致估计失真，这与第 6.3.4 节的收敛诊断结果相互印证。

参数恢复的真值—恢复值对照见图 6-3。

为量化遗漏率本身的影响，另以六条件参数的均值为真值，通过二分搜索设定 deadline，使合成数据的遗漏率达到 5%、10%、15%、20%、25%、35%、50%、70% 八个目标水平（每水平 2 次重复），结果见表 6-3。

表 6-3 遗漏率与参数偏倚（按目标遗漏率分箱；曲线作业结果）

| 实际遗漏率区间 | Censor: Δv_self | Censor: Δa | Censor: ΔSPE_v | Drop: Δv_self | Drop: Δa | Drop: ΔSPE_v |
|---|---|---|---|---|---|---|
| 0–5% | −0.16 | −0.02 | −0.05 | +0.13 | −0.07 | −0.03 |
| 5–10% | −0.19 | −0.00 | +0.00 | +0.11 | −0.06 | −0.01 |
| 10–15% | −0.40 | −0.08 | +0.02 | +0.26 | −0.16 | +0.01 |
| 20–25% | −0.70 | −0.14 | −0.02 | +0.44 | −0.25 | +0.01 |
| 25–35% | −1.02 | −0.19 | +0.01 | +0.63 | −0.33 | +0.07 |
| 50–80% | −3.24 | −0.29 | −0.03 | +1.55 | −0.58 | +0.10 |

结果显示，漂移率的绝对偏倚随遗漏率**单调增大**而非在某一阈值处突变：遗漏率低于约 10% 时两种方案的 |Δv| 均小于 0.2；10%–15% 时升至 0.26–0.40；超过 25% 后达到 0.6–1.0；50% 以上则达 1.6–3.2。边界 a 的偏倚方向一致（Censor 与 Drop 均低估），幅度较小。**而 SPE_v 的偏倚在所有遗漏率水平下均不超过 0.11**，再次表明相对效应具有强稳健性。据此，本文把"约 15% / 约 35%"的经验分档修订为更准确的表述：**遗漏率低于约 10% 时绝对参数估计的偏倚可忽略，10%–35% 之间需谨慎，超过约 35% 后绝对水平不可解释；而自我优势的相对方向在任何遗漏率下都保持稳定**。

遗漏率与参数偏倚的关系见图 6-4。

各参数 95% CI 覆盖率对比见图 6-5。'''

s, n1 = re.subn(r"### 6\.3\.3 参数恢复结果\n\n⏳【待填】.*?(?=\n### 6\.3\.4)", new_633 + "\n\n", s, flags=re.S)
print("[body] §6.3.3 替换:", n1)
if n1 == 0:  # 退化匹配：直接按标题切分
    s, n1 = re.subn(r"### 6\.3\.3 参数恢复结果.*?(?=\n### 6\.3\.4)", new_633 + "\n\n", s, flags=re.S)
    print("[body] 退化替换:", n1)

# 收敛表编号 6-2 → 6-4
s = s.replace("表 6-2 收敛诊断摘要", "表 6-4 收敛诊断摘要")
BODY.write_text(s, encoding="utf-8")

# ---------- ③ 构建脚本：登记三张新图 ----------
entries = '''    ("参数恢复的真值—恢复值对照见图 6-3。", "F6-3_param_recovery_scatter.png",
     "图6-3 参数恢复：真值 vs 恢复值",
     "左列为 Censor 方案、右列为 Drop 方案；三行分别为 v_self、v_stranger 与边界 a。虚线为完美恢复线。"
     "可见漂移率的绝对水平存在系统性偏倚（Censor 低估、Drop 高估），而边界 a 的散点更分散。"
     "作为对照，SPE_v（自我与陌生人漂移率之差）在两方案下均紧密贴合对角线，覆盖率 100%。"),
    ("遗漏率与参数偏倚的关系见图 6-4。", "F6-4_omission_bias_curve.png",
     "图6-4 遗漏率 → 参数偏倚曲线",
     "横轴为实际遗漏率，纵轴为估计偏倚，红色与橙色虚线标注论文原先引用的 35% 与 15% 分档。"
     "漂移率的绝对偏倚随遗漏率单调增大（Censor 向负方向、Drop 向正方向），50% 以上达到 1.6–3.2；"
     "而 SPE_v 的偏倚在所有水平下均小于 0.11，说明相对效应稳健。"),
    ("各参数 95% CI 覆盖率对比见图 6-5。", "F6-5_recovery_coverage.png",
     "图6-5 参数恢复的 95% CI 覆盖率",
     "虚线为名义 95%。Censor 与 Drop 方案下 v、a、t、z 的覆盖率均远低于名义值（0–28%），"
     "唯独 SPE_v 达到 100%。这为"绝对参数水平不可解释、相对效应可解释"的结论提供了直接证据。"),
'''
s3 = BUILDER.read_text(encoding="utf-8")
if "F6-3_param_recovery_scatter.png" not in s3:
    marker = "]\n\n\ndef build()"
    assert s3.count(marker) == 1
    s3 = s3.replace(marker, entries + marker)
    BUILDER.write_text(s3, encoding="utf-8")
    print("[builder] 已登记 图6-3/6-4/6-5")

# ---------- ④ 重建 ----------
r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
Path(ROOT / "_scratch" / "build_log5.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""),
                                                     encoding="utf-8")
print("[build] exit:", r.returncode)
