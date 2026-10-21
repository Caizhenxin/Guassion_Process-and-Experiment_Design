# -*- coding: utf-8 -*-
"""登记 论文_模型章_模板.md（D110）：主计划证据行 + README §9 第 91 项 + 决策行。"""
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


# ---------------- 主计划：决策行 D110（插在 D109 后）
s = MP.read_text(encoding="utf-8")
L = s.split("\n")
d109 = next(i for i, x in enumerate(L) if x.startswith("| **D109** |"))
D110 = rows_of(L[d109], [
    "**D110**", "2026-10-21",
    "**模型章先写完，只留数据占位符**：新建 `5_Reference/03_论文写作/论文_模型章_模板.md`（249 行、15 KB），"
    "把第三章拆成 12 节——任务与观测、三层结构、两阶段漂移模型（M-T1，`ρ=1` 即嵌套 M-T3）、映射方程、"
    "参数表（9 个被试层 + `ρ` + 3 个组层 + `mu/sigma`）、组层估计与 LOO、模型比较能问什么、"
    "可辨识性表（CRLB：`d_ref` 3 / `β_T` 41 / `β_ST` 2248 / `Δa` 658 / `τ_a` 1307）、"
    "生成模型能造什么（含 9 格模拟试次读数）、写作纪律（D104 阶梯）、**待填清单 10 个占位符**、产物索引。"
    "真实数据到手后只需替换 §3.11 的占位符，正文结构不再动。",
    "用户 2026-10-21：「模型的部分请你先完成撰写，后续真实数据来我直接更新写入即可」",
    "`5_Reference/03_论文写作/论文_模型章_模板.md`（**新建**，249 行）",
    "占位符清单与 `manuscript.py` 的 `{{...}}` 渲染口径尚未打通（现在只有结果章模板接了渲染）",
])
L.insert(d109 + 1, D110)

# 证据行：插在「论文_结果章_模板.md（D101）」那行之后
ev = next(i for i, x in enumerate(L)
          if x.startswith("| `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，D101"))
L.insert(ev + 1, rows_of(L[ev], [
    "`5_Reference/03_论文写作/论文_模型章_模板.md`（**新建**，D110，249 行）",
    "第三章（计算模型）全文骨架：三层结构 + 两阶段漂移方程 + 参数表 + 可辨识性 + 生成物 + 10 个数据占位符",
    "✅ 数字均来自 CRLB/oracle/模拟（已标注口径）；待真实数据回填 §3.11",
]))
MP.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("主计划", len(L))

# ---------------- README：§9 第 91 项
r = RD.read_text(encoding="utf-8")
R = r.split("\n")
i90 = next(i for i, x in enumerate(R) if x.startswith("| 90 |"))
R.insert(i90 + 1, "| 91 | ✅ **论文模型章模板（D110）** | `5_Reference/03_论文写作/论文_模型章_模板.md`（249 行）："
                  "三层结构 / M-T1 两阶段漂移（`ρ=1` 即 M-T3）/ 映射方程 / 9+1+3 参数表 / "
                  "CRLB 可辨识性 / 生成物与 9 格模拟试次 / D104 写作纪律 / **10 个待填占位符**；"
                  "**未做**：把它接进 `manuscript.py` 的渲染（现在只有结果章接） |")
RD.write_text("\n".join(R), encoding="utf-8", newline="\n")
print("README", len(R))
