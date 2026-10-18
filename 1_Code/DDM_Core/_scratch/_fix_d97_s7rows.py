# -*- coding: utf-8 -*-
"""把 §7 里随 2026-10-18 签批而定的 ①②③⑦ 四行改成「已定」状态，保留原始问题的删除线痕迹。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\正式采集_候选设计_v2_定稿.md")
a = p.read_text(encoding="utf-8").split("\n")

repl = {
    "| **①** | **被试预算**：160 人（4 组 × 40）是否可行？损耗余量取多少（+20% ⇒ 192 人）？":
        "| **①** | ✅ **已定（随 2026-10-18 签批）**：**160 人（4 组 × 40）**，损耗余量 **+20% ⇒ 备 192 人**（~~原始问题：160 人是否可行？损耗余量取多少？~~）",
    "| **②** | **确证性参数集**：`beta_ST` 是否**移除或降级**（⇒ 6 参数集合）？":
        "| **②** | ✅ **已定（随 2026-10-18 签批）**：**`beta_ST` 降为探索性，确证集用 6 参数**（~~原始问题：是否移除或降级？~~）",
    "| **③** | **`tau_P` 先验值**与是否报告 20/30/45":
        "| **③** | ✅ **已定（随 2026-10-18 签批）**：**主口径 `tau_P = 30`，并报 20 / 45 敏感性**（~~原始问题：先验值与是否报告 20/30/45~~）",
    "| **⑦** | **定稿签署**":
        "| **⑦** | ✅ **已签署（2026-10-18：研究者 蔡振辛、导师 hcp，均「同意」）**（~~原始状态：待签批~~）",
}

hits = 0
for i, l in enumerate(a):
    for old, new in repl.items():
        if l.startswith(old):
            a[i] = new + l[len(old):]
            hits += 1
assert hits == 4, f"命中 {hits} 行（应为 4）"
p.write_text("\n".join(a), encoding="utf-8", newline="\n")
print(f"[ok] 4 行已改；{len(a)} 行")
for i, l in enumerate(a, 1):
    if "随 2026-10-18 签批）**" in l or "已签署（2026-10-18" in l:
        print(i, l[:90])
