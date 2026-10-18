# -*- coding: utf-8 -*-
"""§3 详述的小修：Stage 3 重名标题去重、Stage 6 补 2026-10-18 状态块、变更日志追加。"""
import io
from pathlib import Path

P = Path("5_Reference/08_工作流/工作流_主计划.md")
L = io.open(P, encoding="utf-8").read().splitlines()

# 1) Stage 3 出现两个同名三级标题：第二个是「实现与自测」，且状态早已被 Stage 3b 收口
old = "### Stage 3 ｜映射函数 + 参数恢复（我做）🟡 2026-10-13 第一块完成"
assert sum(1 for x in L if x == old) == 1
L[L.index(old)] = "### Stage 3（实现与自测）｜映射函数 + 参数恢复（我做）✅ 2026-10-13 完成"

# 2) Stage 6 详述补状态块（放在「验收标准」段之后、下一个三级标题之前）
anchor = "**验收标准**：Pilot 数据能通过 Stage 1 的技术验收，且行为量级合理。"
assert sum(1 for x in L if x == anchor) == 1
i = L.index(anchor)
block = [
    "",
    "**状态（2026-10-18）｜🟡 工具链全部就绪，只等真被试**：",
    "",
    "- 方案：[`Stage6_Pilot方案.md`](Stage6_Pilot方案.md)（N=8 推荐、每人完整 576 试次、9 条事前登记判据）。",
    "- 判据阈值已用 **87 份历史真人数据**锚定（D85）；本场 → 质量的「不认真」不再是主观判断，"
    "而是「正确率落在历史第 2 百分位」这类可复算的陈述。",
    "- **两场都不计入 N=8**：2026-10-18 的 60 Hz 主试按键试跑（RT 中位 0.069 s、过快 56.2%）；"
    "同日「组 1 被试 1」的 v4.8 一场（正确率 0.440 = 历史最低 2%、S6-1 最差单元漏答 56.25%、S6-5 平坦）。",
    "- 该场换出两个**程序侧**缺陷并已修：**D93** 组 1 练习段被 `loopCount = P / 4` 跳过 0 试次 ⇒ "
    "v4.9 改 `max(4, P)`；**D94** `qc_group.py` 把「同一编号跑了两遍」判成试次不符 ⇒ 按 `(stage, trialID)` 去重。",
    "- 现场执行顺序见 [`Stage7_数据采集执行与质控方案.md`](Stage7_数据采集执行与质控方案.md) §现场纪律；"
    "每名被试一场、中断换编号重来（`fopen(...,'a+')` 是追加写）。",
]
L[i + 1:i + 1] = block

# 3) 变更日志
start = L.index("## 7. 变更日志")
end = next(k for k in range(start + 1, len(L)) if L[k].startswith("## "))
last = max(k for k in range(start, end) if L[k].startswith("| 2026-"))
L.insert(last + 1, "| 2026-10-18 | §3 详述：Stage 3 重名标题去重（第二个改为「Stage 3（实现与自测）」并置 ✅）；"
                   "Stage 6 补 2026-10-18 状态块（两场均不计入 N=8、D93/D94 已修） |")

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("ok, lines =", len(L))
