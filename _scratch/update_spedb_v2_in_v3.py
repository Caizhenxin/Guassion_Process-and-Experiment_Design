# -*- coding: utf-8 -*-
"""临时：用数据库本体（SPE_Database）结果更新 v3 §8.3，并替换图8-4。"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BODY = DOC / "_v3_正文.md"
FIGV3 = ROOT / "3_Figures" / "Thesis_v3_20260912"
FIGSRC = ROOT / "3_Figures" / "TenRules_Revision_20260912"

# ① 新图覆盖
src = FIGSRC / "F8-4_spe_database.png"
if src.exists():
    shutil.copy2(src, FIGV3 / "F8-4_spe_database.png")
    print("[fig] 已用数据库本体版本覆盖 F8-4")

# ② 正文 §8.3 数据库段
new_db = '''数据库层面。截至 2026-09-02，数据库主索引（`1_Data/Dataset_inf.csv`）共 108 行、50 个研究，索引口径的合计有效被试为 4,841 人。本文按统一清洗规则（仅匹配试次、身份限定为自我与陌生人、正确率编码限 0/1、RT 限 150–3,000 ms、每名被试在两种身份各需 ≥5 个正确试次、数据集需 ≥10 名有效被试）**实际可分析子集为 25 个数据集（来自 18 个研究）、2,488 名被试、337,050 个试次**。

在该子集上，数据集层面的自我优势合并均值为 −93.8 ms（按数据集 bootstrap 的 95% CI：−113.6 ~ −74.5 ms），中位数 −88.3 ms；**全部 25 个数据集方向一致（自我更快）**，数据集间标准差 50.2 ms。这一量级与数据库自身的身份层分析相互印证：数据库对 46 个数据集、2,483 名被试的 Self vs Stranger 比较给出平均 Cohen's d_z ≈ 1.01（加权 0.95，大效应），对应 RT 平均差约 60–70 ms。敏感性分析进一步显示该量级稳健：改用形状身份（k = 26，−90.7 ms）、收窄 RT 窗口至 200–1,500 ms（k = 25，−85.6 ms）、提高每被试试次门槛（k = 25，−95.4 ms）时结果基本不变。因此，本文报告的外部 SPE 量级并非清洗规则或少数数据集的产物。

需要说明的局限有两点。第一，数据库元数据对实验设计参数的记录不完整：可用于调节分析的只有练习试次数（k = 15：ρ = −0.21，95% CI −0.76 ~ +0.45，不显著）与总试次数（k = 24：ρ = +0.31，95% CI −0.09 ~ +0.60，p = .14），而刺激呈现时间与反应窗口在索引中缺失、需逐篇从 JSON 抽取，因此"设计参数如何调制 SPE"的跨研究检验在本文中仅为探索性，无法与内部实验结果做严格的方向性对照。第二，跨研究的任务结构异质性（身份类别、刺激类型、试次数、是否含截止时间）会使效应量不可直接比较，这也是本文把外部验证定位为"支持方向性与量级合理性"、而非"逐条件复现"的原因。

SPE 数据库可获得子集的跨研究分布及其与设计变量的关系见图 8-4。'''

s = BODY.read_text(encoding="utf-8")
s2, n = re.subn(r"数据库层面。.*?(?=\n\nSPE 数据库可获得子集)", new_db, s, flags=re.S)
print("[body] 数据库段替换:", n)
if n == 0:  # 退化：整段替换
    s2, n = re.subn(r"数据库层面。.*?(?=\n\n)", new_db, s, flags=re.S)
    print("[body] 退化替换:", n)
BODY.write_text(s2, encoding="utf-8")

# ③ 说明书：更新图8-4 说明
p = DOC / "图表与指标说明书_面向同门_20260912.md"
t = p.read_text(encoding="utf-8")
old_key = "- **判断标准**：**实测**：44 个数据集全部为自我更快；合并均值 −98.0 ms（95% CI −116.0 ~ −82.1），数据集间 SD 56.7 ms（异质性大）；调节效应均不显著（呈现时间 ρ=−0.19、练习 ρ=+0.21）。"
new_key = ("- **判断标准**：**实测（数据库本体最新版）**：主索引 108 行 / 50 个研究 / 4,841 名有效被试；"
           "本文可分析子集 25 个数据集 / 2,488 人 / 337,050 试次，全部方向为自我更快；合并均值 **−93.8 ms**"
           "（95% CI −113.6 ~ −74.5），数据集间 SD 50.2 ms；与数据库自身身份层分析一致"
           "（Self vs Stranger：k=46、2,483 人、d_z ≈ 1.01 大效应）；调节效应不显著（练习 ρ=−0.21，总试次数 ρ=+0.31）。")
if old_key in t:
    t = t.replace(old_key, new_key)
    print("[doc] 说明书图8-4 说明已更新")
else:
    print("[doc] 说明书图8-4 说明未匹配（跳过）")
p.write_text(t, encoding="utf-8")

# ④ 重建
r = subprocess.run([sys.executable, "-u", str(DOC / "_build_docx_v3.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log7.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
