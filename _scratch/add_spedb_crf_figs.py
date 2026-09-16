# -*- coding: utf-8 -*-
"""临时：把 SPE 数据库分析与 CRF 叠加结果写入 v3 正文，并纳入图集后重建 docx。"""
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

# 1) 新图入图集
for name in ["F8-3_crf_overlay.png", "F8-4_spe_database.png"]:
    src = FIGSRC / name
    if src.exists():
        shutil.copy2(src, FIGV3 / name)
        print("[fig] 复制", name)
    else:
        print("[fig] 缺失", name)

# 2) 正文：重构 §8.3（数据库段移到仿真之后 + 补实测数字与图锚点）
s = BODY.read_text(encoding="utf-8")

new_db = """数据库层面。经统一清洗后，本文实际纳入 44 个数据集、2,480 名被试、296,240 个匹配试次（原始 63 个数据集中排除 19 个：清洗后无有效试次 12 个、缺少标准化身份列 7 个；逐数据集的规模与效应见附录 D）。数据集层面的 SPE_RT 合并均值为 −98.0 ms（按数据集 bootstrap 的 95% CI：−116.0 ~ −82.1 ms），中位数 −88.7 ms；全部 44 个数据集均呈现"自我更快"的方向，被试层面平均有 84.5% 的个体呈现该方向。数据集间标准差为 56.7 ms，说明效应量存在明显的跨研究异质性。

需要谨慎解读之处有两点。第一，该量级（约 −98 ms）大于 SMT 文献中常见的 −20 ~ −60 ms，可能与清洗规则（身份标签来源、RT 窗口、是否限定匹配试次）及部分研究的任务结构差异有关；本文在局限中如实说明，并建议在统一任务与报告标准下复核。第二，设计变量与 SPE 的关系均为探索性且不显著：练习试次数 ρ = +0.21（95% CI −0.16 ~ +0.54，k = 37）、刺激呈现时间 ρ = −0.19（−0.52 ~ +0.16，k = 40）、反应窗口 ρ = −0.24（−0.54 ~ +0.10，k = 35）。其中呈现时间的负方向与内部数据（长呈现时间条件下 SPE 更强）相反，提示任务结构异质性必须被显式建模。

SPE 数据库可获得子集的跨研究分布及其与设计变量的关系见图 8-4。"""

# 删除原"数据库层面"段（到下一个空行）
s2, n = re.subn(r"数据库层面。.*?(?=\n\n)", "", s, flags=re.S)
print("[body] 删除原数据库段:", n)
s2 = s2.replace("⚠️【待补】数据库子集精确样本量表与分析图（自举分布、设计变量散点）。", "")
s2 = s2.replace("\n\n\n", "\n\n")

# CRF 叠加的实测数字
s2 = s2.replace(
    "⚠️【待补】仿真 CRF 与真实 CRF 的叠加对比图。",
    '把仿真与实测 CRF 定量叠加后可见：实测方面，自我条件的匹配键反应比例在各 RT 分位箱均高于陌生人条件，'
    '差异在第二个分位箱（平均 RT ≈ 480 ms）达到最大（+0.14），随后递减（第 3–5 箱分别为 +0.08、+0.05、+0.02），'
    '与课题组早先的滑动窗口分析（峰值约 434–459 ms）一致；仿真方面，起始点偏向越大，快反应段的匹配键比例越高，'
    '两套引擎（Euler–Maruyama 与 HDDM 生成器）形态一致。仿真的"大偏向 − 中性"差异曲线与实测的'
    '"自我 − 陌生人"差异曲线在快反应端方向一致、在慢反应端仿真差异偏小，说明起始点偏向能解释实测自我优势的主要部分，'
    '但不足以完全复现其时间进程。\n\n模拟与实测 CRF 的定量叠加对比见图 8-3。')

# 把数据库段插到 Stim-Coding 段之后
anchor = "Stim-Coding 仿真得到的 CRF 曲线见图 8-2。"
assert s2.count(anchor) == 1, f"锚点计数异常 {s2.count(anchor)}"
s2 = s2.replace(anchor, anchor + "\n\n" + new_db)
BODY.write_text(s2, encoding="utf-8")
print("[body] 已更新 §8.3")

# 3) 构建脚本：登记两张新图
entries = '''    ("模拟与实测 CRF 的定量叠加对比见图 8-3。", "F8-3_crf_overlay.png",
     "图8-3 模拟与实测 CRF 的定量叠加对比",
     "(A) 实测 CRF（88 人，被试级 cluster bootstrap 95% CI）：自我条件的匹配键反应比例在各 RT 分位箱均高于"
     "陌生人条件，差异在 RT ≈ 480 ms 处最大（+0.14）。(B) 仿真 CRF：4 个起始点偏向（z = 0.50–0.65）× 两套引擎，"
     "并叠加实测的自我/陌生人曲线。(C) 差异曲线：仿真（大偏向 − 中性）与实测（自我 − 陌生人）在快反应端方向一致，"
     "但慢反应端仿真差异偏小，说明起点偏向只能解释实测自我优势的一部分。"),
    ("SPE 数据库可获得子集的跨研究分布及其与设计变量的关系见图 8-4。", "F8-4_spe_database.png",
     "图8-4 SPE 数据库可获得子集的跨研究分布与设计变量关系（探索性）",
     "(A) 44 个数据集的 SPE_RT 森林图（点=数据集均值，横线=被试级 95% CI，红点线=合并均值 −98.0 ms）；"
     "全部数据集均为自我更快。(B)(C) SPE 与刺激呈现时间、练习试次数的关系（点大小 ∝ 被试数）："
     "ρ 分别为 −0.19 与 +0.21，95% CI 均跨 0，属探索性且不显著。"),
'''
s3 = BUILDER.read_text(encoding="utf-8")
if "F8-3_crf_overlay.png" not in s3:
    marker = "]\n\n\ndef build()"
    assert s3.count(marker) == 1
    s3 = s3.replace(marker, entries + marker)
    BUILDER.write_text(s3, encoding="utf-8")
    print("[builder] 已登记 图8-3 / 图8-4")

# 4) 重建
r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
log = (r.stdout or "") + "\n" + (r.stderr or "")
Path(ROOT / "_scratch" / "build_log3.txt").write_text(log, encoding="utf-8")
print("[build] 退出码:", r.returncode)
