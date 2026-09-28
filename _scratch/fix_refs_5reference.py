# -*- coding: utf-8 -*-
"""修复 5_Reference 整理后失效的跨文档路径引用。

只改「活文档」（00–07 目录下的 .md），不动 `_历史版本/`、`_旧稿/`、`99_归档/`
——那些是冻结的历史产物，保留原样才看得出当时的状态。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
REF = ROOT / "5_Reference"

# 原路径片段 -> 新路径片段（按长度降序应用，避免前缀互相覆盖）
REPL = [
    # ---- 原 5_Reference/ 根目录 ----
    ("5_Reference/理论逻辑链评估与修正建议.md", "5_Reference/02_方法学审查/理论逻辑链评估与修正建议.md"),
    ("5_Reference/项目脉络梳理与行动清单_20260916.md", "5_Reference/02_方法学审查/项目脉络梳理与行动清单_20260916.md"),
    ("5_Reference/生成模型与GP探索_代码审计_20260916.md", "5_Reference/02_方法学审查/生成模型与GP探索_代码审计_20260916.md"),
    ("5_Reference/项目现状与答辩可靠性评估.md", "5_Reference/02_方法学审查/项目现状与答辩可靠性评估.md"),
    ("5_Reference/论文核查与行动清单_20260902.md", "5_Reference/02_方法学审查/论文核查与行动清单_20260902.md"),
    ("5_Reference/Omission建模可行性分析.md", "5_Reference/07_文献与技术路线/Omission建模可行性分析.md"),
    ("5_Reference/Omission_LAN_OPN_实施作战计划.md", "5_Reference/07_文献与技术路线/Omission_LAN_OPN_实施作战计划.md"),
    ("5_Reference/OPN_training_summary.md", "5_Reference/07_文献与技术路线/OPN_training_summary.md"),
    ("5_Reference/SPE_Database_README.md", "5_Reference/07_文献与技术路线/SPE_Database_README.md"),
    ("5_Reference/Omission_v2.md", "5_Reference/07_文献与技术路线/Omission_v2.md"),
    ("5_Reference/可行性分析.md", "5_Reference/01_选题与方案/可行性分析.md"),
    ("5_Reference/RoadMap.md", "5_Reference/01_选题与方案/RoadMap.md"),
    ("5_Reference/Log.md", "5_Reference/06_进展与汇报/Log.md"),
    ("5_Reference/Aim.md", "5_Reference/01_选题与方案/Aim.md"),
    # ---- 原 Other/ ----
    ("Other/毕业论文大纲_v3_自我优势效应的实验设计空间优化.md", "5_Reference/01_选题与方案/毕业论文大纲_v3_20260902.md"),
    ("Other/冻结规格书_v1_20260902.md", "5_Reference/02_方法学审查/冻结规格书_v1_20260902.md"),
    ("Other/项目科普介绍_给外行_20260902.md", "5_Reference/06_进展与汇报/项目科普介绍_给外行_20260902.md"),
    ("Other/导师会议_", "5_Reference/06_进展与汇报/导师会议_"),
    ("Other/outline_v1_extracted.txt", "5_Reference/01_选题与方案/_历史版本/outline_v1_extracted.txt"),
    ("Other/outline_v2_extracted.txt", "5_Reference/01_选题与方案/_历史版本/outline_v2_extracted.txt"),
    # ---- 原 终版论文格式及要求/ ----
    ("终版论文格式及要求/_v3_正文.md", "5_Reference/03_论文写作/_v3_正文.md"),
    ("终版论文格式及要求/_v3_front_摘要.md", "5_Reference/03_论文写作/_v3_front_摘要.md"),
    ("终版论文格式及要求/重跑与数据库更新说明_20260913.md", "5_Reference/02_方法学审查/重跑与数据库更新说明_20260913.md"),
    ("终版论文格式及要求/计算建模十条规则核对报告_初稿v2_20260912.md", "5_Reference/02_方法学审查/计算建模十条规则核对报告_初稿v2_20260912.md"),
    ("终版论文格式及要求/答辩问答_高斯过程的两问_20260913.md", "5_Reference/02_方法学审查/答辩问答_高斯过程的两问_20260913.md"),
    ("终版论文格式及要求/样本量扩充至20人的分析计划_20260912.md", "5_Reference/02_方法学审查/样本量扩充至20人的分析计划_20260912.md"),
    ("终版论文格式及要求/图表与指标说明书_面向同门_20260912.md", "5_Reference/03_论文写作/图表与指标说明书_面向同门_20260912.md"),
    ("终版论文格式及要求/必须补的表清单_20260912.md", "5_Reference/03_论文写作/必须补的表清单_20260912.md"),
    ("终版论文格式及要求/规则5与规则7_Methods与Results段落_20260912.md", "5_Reference/03_论文写作/规则5与规则7_Methods与Results段落_20260912.md"),
    ("终版论文格式及要求/干净章节骨架_v3_20260912.md", "5_Reference/03_论文写作/干净章节骨架_v3_20260912.md"),
    ("终版论文格式及要求/v3交付说明_20260912.md", "5_Reference/03_论文写作/v3交付说明_20260912.md"),
    ("终版论文格式及要求/", "5_Reference/（已拆分：03_论文写作 / 02_方法学审查 / 04_格式与模板 / 05_交付件）/"),
    # ---- 原 Plan/markdown/ ----
    ("Plan/markdown/", "5_Reference/（已分发到各子目录）/"),
]
REPL.sort(key=lambda p: -len(p[0]))

SKIP_DIRS = {"_历史版本", "_旧稿", "_抽取文本", "99_归档"}


def is_living(p: Path) -> bool:
    if p.suffix.lower() not in {".md", ".py", ".csv", ".txt"}:
        return False
    parts = set(p.relative_to(REF).parts)
    return not (parts & SKIP_DIRS)


def main():
    changed = []
    for f in sorted(REF.rglob("*")):
        if not f.is_file() or f.name == "AGENTS.md" or not is_living(f):
            continue
        try:
            txt = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        orig = txt
        hits = {}
        for old, new in REPL:
            if old in txt:
                hits[old] = txt.count(old)
                txt = txt.replace(old, new)
        if txt != orig:
            f.write_text(txt, encoding="utf-8")
            changed.append((f.relative_to(ROOT), sum(hits.values())))

    print(f"已修改 {len(changed)} 个文件：")
    for rel, n in changed:
        print(f"  {n:3d} 处  {rel}")


if __name__ == "__main__":
    main()
