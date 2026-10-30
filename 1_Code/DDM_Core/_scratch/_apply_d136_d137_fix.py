# -*- coding: utf-8 -*-
"""补齐 D136/D137 在证据表的两行，并去掉进度表的重复行（幂等）。"""
import io
from pathlib import Path

PLAN = Path(__file__).resolve().parents[3] / "5_Reference" / "08_工作流" / "工作流_主计划.md"
lines = io.open(PLAN, encoding="utf-8").read().splitlines()

# 1) 去掉重复的进度行（保留第一次出现）
seen, out = set(), []
for l in lines:
    if l.startswith("| 2026-10-28 | **33（"):
        if "33" in seen:
            continue
        seen.add("33")
    if l.startswith("| 2026-10-30 | **34（"):
        if "34" in seen:
            continue
        seen.add("34")
    out.append(l)
lines = out

# 2) 证据表两行
EV1 = ("| `5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md` §十一 + "
       "`_scratch/_probe_spe_{interaction,source}.py` + `3_Figures/_real_check/fig_spe_interaction.png` | "
       "D136 证据：① 四格中位 RT/ACC（643/0.878、732/0.776、724/0.743、750/0.761）② 交互配对 t"
       "（RT 匹配 +59.3±10.6 t=5.59、非匹配 +16.3±7.9 p=0.055、交互 t=4.40 p=0.00045；"
       "ACC 匹配 +14.4 pt t=4.21、非匹配 −0.9 p=0.67、交互 t=5.90 p=2.3e-5）③ 被试内 ANOVA "
       "Identity×Matching F=19.36 p=0.0004 ④ SDT 命中 0.862/0.718、虚报 0.230/0.221、Δd′ +0.496 p=0.0095、"
       "Δc −0.286 p=1.4e-5 ⑤ 通道关闭表（全通道 −19/+18 → `dz_S`=0 时 +9/−2；`beta_S`=0 时 −16/+19）"
       "⑥ 生成侧 `dz_S` 0/0.02/0.04/0.06 扫描表 |")
EV2 = ("| `5_Reference/05_交付件/毕业论文_蔡振辛_初稿v4_图版_20261030.docx` + "
       "`5_Reference/03_论文写作/论文_整体逻辑v4_20261030.md` + `_build_docx_v4.py` | "
       "D137 证据：① docx 实测 24 内嵌图 / 16 表 / 103 标题 / 468 段 / 42,470 字符 / 11.0 MB "
       "② 装配链 `_v31_export.md` 49,240 字符 → `_v4_正文.md` 48,027 字符 ③ 第 5–7 章逐字保留（GP 七图全在）"
       "④ 逻辑说明 8 节，含「答辩五问」 |")

has136 = any(l.startswith("| `5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md` §十一") for l in lines)
if not has136:
    i = next(i for i, l in enumerate(lines)
             if l.startswith("| `5_Reference/03_论文写作/SPE_真实分布_基准_20261027.md`"))
    lines[i + 1:i + 1] = [EV1, EV2]
    print("证据表已追加 D136/D137 两行")
else:
    print("证据表已存在，跳过")

io.open(PLAN, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("总行数", len(lines))
