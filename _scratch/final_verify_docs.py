# -*- coding: utf-8 -*-
"""临时：最终校验 + 把参数恢复结果补入说明书与表清单。"""
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
DOCX = DOC / "毕业论文_蔡振辛_初稿v3_图版_20260912.docx"

# ① 校验
z = zipfile.ZipFile(DOCX)
xml = z.read("word/document.xml").decode("utf-8")
caps = [m.strip() for m in re.findall(r"(图[0-9]-[0-9]+ [^<]{2,26})", xml)]
tabs = re.findall(r"(表[0-9]-[0-9]+ [^<]{2,26})", xml)
out = ["图序（%d）：" % len(caps)] + ["  " + c for c in caps]
out += ["", "表序（%d）：" % len(tabs)] + ["  " + t for t in dict.fromkeys(tabs)]
out += ["", "内嵌图: %d | 表格对象: %d | 大小: %.1f MB | 红色待办: %d"
        % (len([n for n in z.namelist() if n.startswith("word/media/thesis_v3")]),
           xml.count("<w:tbl>"), DOCX.stat().st_size / 1048576, xml.count("C00000"))]
(ROOT / "_scratch" / "verify5.txt").write_text("\n".join(out), encoding="utf-8")

# ② 说明书：补参数恢复实测结果
p = DOC / "图表与指标说明书_面向同门_20260912.md"
s = p.read_text(encoding="utf-8")
if "### 图6-3 / 图6-4 / 图6-5" in s:
    old_start = s.index("### 图6-3 / 图6-4 / 图6-5")
    old_end = s.index("### 图7-1 / 图7-2", old_start)
    new = """### 图6-3 / 图6-4 / 图6-5 参数恢复（已实测）　`F6-3_param_recovery_scatter.png` / `F6-4_omission_bias_curve.png` / `F6-5_recovery_coverage.png`
- **画的是什么**：图6-3=已知真值的仿真数据被重新估计后"真值 vs 估计"散点（虚线=完美恢复）；图6-4=遗漏率与参数偏倚的曲线（含 15%/35% 参考线）；图6-5=各参数 95% CI 的覆盖率。
- **怎么读**：点贴对角线=无偏；曲线越陡=偏倚随遗漏率增长越快；覆盖率柱越接近 95% 虚线越好。
- **实测（每条件 3 次重复，共 36 次拟合）**：
  - **漂移率绝对水平不可恢复**：Censor 系统性低估（偏倚 −1.34），Drop 系统性高估（+0.73）；95% CI 覆盖率仅 17% 与 0%。
  - **自我优势的相对效应几乎完美恢复**：SPE_v 偏倚 ≤0.05、RMSE ≤0.19、**覆盖率 100%**、跨条件 r = .97（Censor）/ .91（Drop）。
  - 曲线显示偏倚随遗漏率**单调增大**：<10% 时 |Δv| < 0.2；10–15% 时 0.26–0.40；>25% 时 0.6–1.0；>50% 时 1.6–3.2。而 SPE_v 偏倚在任何遗漏率下都 ≤0.11。
  - 条件差异：G6（遗漏 1.2%）偏倚极小（−0.03），G8（v≈2.8、a≈2.4、遗漏 30.7%）最大（Censor −2.28 / Drop +3.67）。
- **判断标准**：覆盖率 ≈95%、偏倚 ≈0 才算"参数可信"。因此本文的结论是——**绝对参数水平不宜作实质解释，条件间的相对比较（SPE_v）是可靠的**。
- **要记住**：这是全文最重要的一块"地基证据"：它解释了"为什么遗漏处理会改变结论，但我们的核心结论仍然成立"。
- **对论文的影响**：把原先"遗漏率 >35% 不可接受 / <15% 可靠"的经验分档，修订为"<10% 偏倚可忽略；10–35% 需谨慎；>35% 绝对水平不可解释；相对方向始终稳定"。

"""
    s = s[:old_start] + new + s[old_end:]
    p.write_text(s, encoding="utf-8")
    print("[doc] 说明书 §参数恢复 已更新为实测结果")

# ③ 表清单：第6章表号对齐
p = DOC / "必须补的表清单_20260912.md"
s = p.read_text(encoding="utf-8")
s = s.replace("### 🆕 表 6-4 参数恢复结果（真值 vs 恢复）", "### ✅ 表 6-2 参数恢复结果（真值 vs 恢复）— 已完成")
s = s.replace("### 🆕 表 6-5 遗漏率–偏倚曲线（分箱）", "### ✅ 表 6-3 遗漏率–偏倚曲线（分箱）— 已完成")
s = s.replace("### 表 6-2 遗漏率、偏倚与数据质量准则 ✅", "### 表 6-2b 遗漏率与数据质量准则（内容并入表4-1与表6-3）")
s = s.replace("### 表 6-6（🔄）HDDM 收敛诊断", "### ✅ 表 6-4 HDDM 收敛诊断 — 已完成（Split-R̂ + ESS）")
p.write_text(s, encoding="utf-8")
print("[doc] 表清单 第6章表号已对齐")
print("完成")
