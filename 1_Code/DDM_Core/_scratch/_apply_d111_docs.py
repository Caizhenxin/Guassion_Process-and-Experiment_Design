# -*- coding: utf-8 -*-
"""D111：三件交付（全景预览 md+html / S3 notebook / 论文预览 docx）登记。"""
from pathlib import Path

ROOT = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
RD = ROOT / "1_Code/DDM_Core/README.md"


def ncol(line):
    return line.count("|") - 1


def rows_of(line, cells):
    k = ncol(line)
    cells = list(cells)[:k]
    while len(cells) < k:
        cells.append("—")
    return "| " + " | ".join(cells) + " |"


s = MP.read_text(encoding="utf-8")
L = s.split("\n")
d110 = next(i for i, x in enumerate(L) if x.startswith("| **D110** |"))
D111 = rows_of(L[d110], [
    "**D111**", "2026-10-21",
    "**三件对外交付落地**（可直接给导师看、也可直接进论文）："
    "① `5_Reference/06_进展与汇报/项目全景预览_v1.md` + 同名 `.html`（自包含、无 CDN、含 4 个手写公式卡、"
    "1 张 SVG 结构图、4 张图、22 条目录）；② `1_Code/Python_for_Generate/S3_两阶段DDM_模拟数据生成.ipynb`"
    "（13 个 cell，从头跑到尾 exit 0，产出 4608 行 trial_level.csv + 707 KB 实验同列 CSV + 三图）；"
    "③ `5_Reference/05_交付件/论文预览_可写部分_v1_20261021.docx`（11 页：封面/摘要/引言/方法/计算模型/"
    "计划分析/讨论/附录，需真实数据处统一标 `【待数据】`）。",
    "用户 2026-10-21：要求「完整预览写得更完整（含公式/模型，md + html）」「trial-level 数据用 CSV 保存并写详细 notebook」"
    "「文章能写的部分做成 docx 放交付件」",
    "`5_Reference/06_进展与汇报/项目全景预览_v1.{md,html}`；`1_Code/Python_for_Generate/S3_两阶段DDM_模拟数据生成.ipynb`；"
    "`5_Reference/05_交付件/论文预览_可写部分_v1_20261021.docx`",
    "三件的生成器都在 `1_Code/DDM_Core/_scratch/`（`build_preview_html.py`、`_build_s3_notebook.py`、"
    "`build_thesis_preview_docx.py`），尚未提升为 `1_Code/Experiment/` 的正式脚本",
])
L.insert(d110 + 1, D111)

ev = next(i for i, x in enumerate(L)
          if x.startswith("| `5_Reference/03_论文写作/论文_模型章_模板.md`（**新建**，D110"))
L.insert(ev + 1, rows_of(L[ev], [
    "`5_Reference/06_进展与汇报/项目全景预览_v1.html` + `5_Reference/05_交付件/论文预览_可写部分_v1_20261021.docx`"
    " + `1_Code/Python_for_Generate/S3_两阶段DDM_模拟数据生成.ipynb`（**新建**，D111）",
    "对外预览三件套：HTML 全景（25 482 字符、13 表、4 公式卡、4 图、22 条目录、0 断链）；"
    "docx 论文预览（11 页、769 353 B、经 Word COM 导 PDF 逐页核对）；notebook 13 cells（实跑 exit 0）",
    "✅ 三件均已肉眼验收（Edge 截图 4 段 / PDF 11 页）；待做：生成器提升为正式脚本",
]))
MP.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("主计划", len(L))

r = RD.read_text(encoding="utf-8")
R = r.split("\n")
i91 = next(i for i, x in enumerate(R) if x.startswith("| 91 |"))
R.insert(i91 + 1, "| 92 | ✅ **对外预览三件套（D111）** | ① `5_Reference/06_进展与汇报/项目全景预览_v1.html`"
                  "（自包含，公式卡 + SVG 结构图 + 4 图）；② `论文预览_可写部分_v1_20261021.docx`（11 页，"
                  "`【待数据】` 统一标注）；③ `1_Code/Python_for_Generate/S3_两阶段DDM_模拟数据生成.ipynb`"
                  "（13 cells，exit 0）。**未做**：生成器仍在 `_scratch/`，未提升为正式脚本 |")
RD.write_text("\n".join(R), encoding="utf-8", newline="\n")
print("README", len(R))
