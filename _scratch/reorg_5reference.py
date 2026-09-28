# -*- coding: utf-8 -*-
"""5_Reference 目录整理（2026-09-21）

只操作磁盘，不调用任何会修改 git 状态的命令。
用 Python 而非 PowerShell，因为文件名含中文，PS 5.1 读取无 BOM 的 .ps1 会乱码。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference")

DIRS = [
    "00_索引与思路历程",
    "01_选题与方案", "01_选题与方案/_历史版本",
    "02_方法学审查",
    "03_论文写作", "03_论文写作/_旧稿",
    "04_格式与模板", "04_格式与模板/_抽取文本",
    "05_交付件", "05_交付件/_历史版本",
    "06_进展与汇报",
    "07_文献与技术路线",
    "99_归档",
]

MOVES = [
    # ---- Plan/markdown ----
    ("Plan/markdown/AGENTS.md", "AGENTS.md"),
    ("Plan/markdown/Aim.md", "01_选题与方案/Aim.md"),
    ("Plan/markdown/可行性分析.md", "01_选题与方案/可行性分析.md"),
    ("Plan/markdown/RoadMap.md", "01_选题与方案/RoadMap.md"),
    ("Plan/markdown/拟开展工作_研究计划.md", "01_选题与方案/拟开展工作_研究计划.md"),
    ("Plan/markdown/Auto-Reseach.md", "07_文献与技术路线/Auto-Reseach.md"),
    ("Plan/markdown/Log.md", "06_进展与汇报/Log.md"),
    ("Plan/markdown/Omission_LAN_OPN_实施作战计划.md", "07_文献与技术路线/Omission_LAN_OPN_实施作战计划.md"),
    ("Plan/markdown/Omission_v2.md", "07_文献与技术路线/Omission_v2.md"),
    ("Plan/markdown/Omission建模可行性分析.md", "07_文献与技术路线/Omission建模可行性分析.md"),
    ("Plan/markdown/OPN_training_summary.md", "07_文献与技术路线/OPN_training_summary.md"),
    ("Plan/markdown/SPE_Database_README.md", "07_文献与技术路线/SPE_Database_README.md"),
    ("Plan/markdown/理论逻辑链评估与修正建议.md", "02_方法学审查/理论逻辑链评估与修正建议.md"),
    ("Plan/markdown/论文核查与行动清单_20260902.md", "02_方法学审查/论文核查与行动清单_20260902.md"),
    ("Plan/markdown/项目现状与答辩可靠性评估.md", "02_方法学审查/项目现状与答辩可靠性评估.md"),
    ("Plan/markdown/项目脉络梳理与行动清单_20260916.md", "02_方法学审查/项目脉络梳理与行动清单_20260916.md"),
    ("Plan/markdown/生成模型与GP探索_代码审计_20260916.md", "02_方法学审查/生成模型与GP探索_代码审计_20260916.md"),

    # ---- Plan/docx ----
    ("Plan/docx/拟开展工作.docx", "01_选题与方案/_历史版本/拟开展工作.docx"),
    ("Plan/docx/拟开展工作v2.docx", "01_选题与方案/拟开展工作v2.docx"),
    ("Plan/docx/毕业论文大纲_自我优势效应的实验设计空间优化.docx", "01_选题与方案/_历史版本/毕业论文大纲_v1_20260617.docx"),
    ("Plan/docx/毕业论文大纲_v2_自我优势效应的实验设计空间优化.docx", "01_选题与方案/_历史版本/毕业论文大纲_v2_20260722.docx"),

    # ---- Other ----
    ("Other/毕业论文大纲_v3_自我优势效应的实验设计空间优化.md", "01_选题与方案/毕业论文大纲_v3_20260902.md"),
    ("Other/outline_v1_extracted.txt", "01_选题与方案/_历史版本/outline_v1_extracted.txt"),
    ("Other/outline_v2_extracted.txt", "01_选题与方案/_历史版本/outline_v2_extracted.txt"),
    ("Other/冻结规格书_v1_20260902.md", "02_方法学审查/冻结规格书_v1_20260902.md"),
    ("Other/lock_BF_ANOVA_20260902.csv", "02_方法学审查/lock_BF_ANOVA_20260902.csv"),
    ("Other/lock_S01_S02_20260902.csv", "02_方法学审查/lock_S01_S02_20260902.csv"),
    ("Other/毕业论文初稿_第1-2章_绪论与文献综述_20260902.md", "03_论文写作/_旧稿/毕业论文初稿_第1-2章_20260902.md"),
    ("Other/毕业论文初稿_第3-5章_已完成研究_20260902.md", "03_论文写作/_旧稿/毕业论文初稿_第3-5章_20260902.md"),
    ("Other/导师会议_论文大纲简版_20260902.md", "06_进展与汇报/导师会议_论文大纲简版_20260902.md"),
    ("Other/导师会议_我的汇报_第一人称版_20260902.md", "06_进展与汇报/导师会议_我的汇报_第一人称版_20260902.md"),
    ("Other/导师会议_详细解释与预期问答_20260902.md", "06_进展与汇报/导师会议_详细解释与预期问答_20260902.md"),
    ("Other/今日总结与明日计划_20260902.md", "06_进展与汇报/今日总结与明日计划_20260902.md"),
    ("Other/项目科普介绍_给外行_20260902.md", "06_进展与汇报/项目科普介绍_给外行_20260902.md"),
    ("Other/_bf_nb_code_dump.txt", "99_归档/_bf_nb_code_dump.txt"),
    ("Other/generate_outline_v2.py", "99_归档/generate_outline_v2.py"),
    ("Other/文件分类清单.xlsx", "99_归档/文件分类清单_20260508.xlsx"),
    ("Other/文件夹分析摘要.txt", "99_归档/文件夹分析摘要_20260508.txt"),

    # ---- 终版论文格式及要求 ----
    ("终版论文格式及要求/_v3_正文.md", "03_论文写作/_v3_正文.md"),
    ("终版论文格式及要求/_v3_front_摘要.md", "03_论文写作/_v3_front_摘要.md"),
    ("终版论文格式及要求/干净章节骨架_v3_20260912.md", "03_论文写作/干净章节骨架_v3_20260912.md"),
    ("终版论文格式及要求/必须补的表清单_20260912.md", "03_论文写作/必须补的表清单_20260912.md"),
    ("终版论文格式及要求/图表与指标说明书_面向同门_20260912.md", "03_论文写作/图表与指标说明书_面向同门_20260912.md"),
    ("终版论文格式及要求/规则5与规则7_Methods与Results段落_20260912.md", "03_论文写作/规则5与规则7_Methods与Results段落_20260912.md"),
    ("终版论文格式及要求/v3交付说明_20260912.md", "03_论文写作/v3交付说明_20260912.md"),
    ("终版论文格式及要求/_build_docx_v3.py", "03_论文写作/_build_docx_v3.py"),
    ("终版论文格式及要求/_b_ch1_引言.md", "03_论文写作/_旧稿/_b_ch1_引言.md"),
    ("终版论文格式及要求/_b_ch4_研究框架.md", "03_论文写作/_旧稿/_b_ch4_研究框架.md"),
    ("终版论文格式及要求/_b_ch8_研究四_多源验证.md", "03_论文写作/_旧稿/_b_ch8_研究四_多源验证.md"),
    ("终版论文格式及要求/_b_ch9_总讨论.md", "03_论文写作/_旧稿/_b_ch9_总讨论.md"),
    ("终版论文格式及要求/_b_ch10_结论.md", "03_论文写作/_旧稿/_b_ch10_结论.md"),
    ("终版论文格式及要求/_b_front_摘要.md", "03_论文写作/_旧稿/_b_front_摘要.md"),
    ("终版论文格式及要求/_b_refs_backmatter.md", "03_论文写作/_旧稿/_b_refs_backmatter.md"),
    ("终版论文格式及要求/_declaration.txt", "03_论文写作/_旧稿/_declaration.txt"),
    ("终版论文格式及要求/_build_docx.py", "03_论文写作/_旧稿/_build_docx.py"),
    ("终版论文格式及要求/计算建模十条规则核对报告_初稿v2_20260912.md", "02_方法学审查/计算建模十条规则核对报告_初稿v2_20260912.md"),
    ("终版论文格式及要求/答辩问答_高斯过程的两问_20260913.md", "02_方法学审查/答辩问答_高斯过程的两问_20260913.md"),
    ("终版论文格式及要求/重跑与数据库更新说明_20260913.md", "02_方法学审查/重跑与数据库更新说明_20260913.md"),
    ("终版论文格式及要求/样本量扩充至20人的分析计划_20260912.md", "02_方法学审查/样本量扩充至20人的分析计划_20260912.md"),
    ("终版论文格式及要求/论文格式规范.pdf", "04_格式与模板/论文格式规范.pdf"),
    ("终版论文格式及要求/硕士专业学位论文封面（2025版）.doc", "04_格式与模板/硕士专业学位论文封面_2025版.doc"),
    ("终版论文格式及要求/南京师范大学学位论文原创性和使用授权声明书（2020版）.docx", "04_格式与模板/南京师范大学学位论文原创性和使用授权声明书_2020版.docx"),
    ("终版论文格式及要求/温_毕业论文_设计空间_v13最终版.docx", "04_格式与模板/范文_温_毕业论文_设计空间_v13最终版.docx"),
    ("终版论文格式及要求/_pdf_spec_raw.txt", "04_格式与模板/_抽取文本/_格式规范_raw.txt"),
    ("终版论文格式及要求/_sample_thesis.txt", "04_格式与模板/_抽取文本/_范本论文_raw.txt"),
    ("终版论文格式及要求/蔡振辛_自我优势效应的实验设计空间优化：基于Ω的 DDM 参数预测与验证.pptx",
     "06_进展与汇报/汇报_基于Ω的DDM参数预测与验证_20260120.pptx"),
    ("终版论文格式及要求/毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx", "05_交付件/毕业论文_蔡振辛_初稿v3.1_图版_20260913.docx"),
    ("终版论文格式及要求/毕业论文_蔡振辛_初稿v3_图版_20260912.docx", "05_交付件/_历史版本/毕业论文_蔡振辛_初稿v3_图版_20260912.docx"),
    ("终版论文格式及要求/毕业论文_蔡振辛_初稿v2_图版_20260902.docx", "05_交付件/_历史版本/毕业论文_蔡振辛_初稿v2_图版_20260902.docx"),
    ("终版论文格式及要求/毕业论文_蔡振辛_初稿v1_20260902.docx", "05_交付件/_历史版本/毕业论文_蔡振辛_初稿v1_20260902.docx"),
    ("终版论文格式及要求/毕业论文_蔡振辛_初稿v0_20260902.docx", "05_交付件/_历史版本/毕业论文_蔡振辛_初稿v0_20260902.docx"),
]


def main():
    for d in DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    ok, miss = 0, []
    for src_rel, dst_rel in MOVES:
        src, dst = ROOT / src_rel, ROOT / dst_rel
        if not src.exists():
            miss.append(src_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            print(f"!! 目标已存在，跳过：{dst_rel}")
            miss.append(src_rel)
            continue
        shutil.move(str(src), str(dst))
        ok += 1

    print(f"移动完成：成功 {ok} 项")
    if miss:
        print(f"未找到/跳过 {len(miss)} 项：")
        for m in miss:
            print("   MISS " + m)

    # 清理空目录
    for d in ["Plan/markdown", "Plan/docx", "Plan", "Other", "终版论文格式及要求"]:
        p = ROOT / d
        if not p.exists():
            continue
        left = [f for f in p.rglob("*") if f.is_file()]
        if not left:
            shutil.rmtree(p)
            print(f"移除空目录：{d}")
        else:
            print(f"保留目录 {d}（仍有 {len(left)} 个文件）")
            for f in left:
                print("     " + str(f.relative_to(ROOT)))


if __name__ == "__main__":
    main()
