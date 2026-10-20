# -*- coding: utf-8 -*-
"""D107 收尾修订：行数 263→323、报告名按真值拆分、把「161 人/组」改成重跑结论。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RD = ROOT / "1_Code" / "DDM_Core" / "README.md"

# ------------------------------------------------------------------ 主计划
s = MP.read_text(encoding="utf-8")
pair_mp = [
    ("结果：**oracle 真值下 39–40 人/组**（`4T×4W r9` 最优）；**design 真值下 161 人/组**。",
     "结果：**oracle 真值下 39–40 人/组**（`4T×4W r9` 最优）；**design 真值下现行 0/8/32/120 被判「被试层漂移不可识别」**，"
     "把 P 改成 5 水平（0/8/24/64/120）后才回到 37 人/组。"),
    ("的 P≤32 漂移被截到 0 ⇒ **P 设计实际只剩 2 个有效水平**，`tau_P` 只能靠曲率识别 ⇒ 人数爆炸。",
     "的 P≤32 漂移被截到 0 ⇒ **P 设计实际只剩 2 个有效水平**（32 与 120），三参数（`d_ref`/`beta_P`/`tau_P`）"
     "只有两个信息点 ⇒ `tau_P` 不可识别（不是「人要得多」，是「没东西可估」）。"),
    ("oracle 口径 39–40 人/组、design 口径 161 人/组；抓出「P≤32 漂移被截到 0 ⇒ 只剩两个有效水平」这一结构性问题。",
     "oracle 口径 39–40 人/组、design 口径现行方案判「不可识别」/ 5 水平 37 人/组；"
     "抓出「P≤32 漂移被截到 0 ⇒ 只剩两个有效水平」这一结构性问题。"),
    ("oracle 口径 39–40 人/组 vs design 口径 161 人/组，根因是 design 真值的低 P 水平漂移被截到 0（只剩 2 个有效水平）。",
     "oracle 口径 39–40 人/组 vs design 口径现行方案「不可识别」、5 水平 37 人/组，"
     "根因是 design 真值的低 P 水平漂移被截到 0（只剩 2 个有效水平）。"),
    ("`design_search.py`（263 行）", "`design_search.py`（323 行）"),
    ("（**新建**，D107，263 行）", "（**新建**，D107，323 行）"),
    ("`5_Reference/03_论文写作/figures_sim/design_search.md`/`.csv`",
     "`5_Reference/03_论文写作/figures_sim/design_search_design.md`/`.csv` 与 `design_search_oracle.md`/`.csv`"),
]
for old, new in pair_mp:
    assert s.count(old) >= 1, old[:50]
    s = s.replace(old, new)

# 证据表那一行重写（原行只有两格、且没写出口径）
L = s.split("\n")
for i, x in enumerate(L):
    if x.startswith("| `1_Code/Experiment/design_search.py`（**新建**，D107"):
        L[i] = ("| `1_Code/Experiment/design_search.py`（**新建**，D107，323 行）+ "
                "`5_Reference/03_论文写作/figures_sim/design_search_design.md`/`.csv` + "
                "`design_search_oracle.md`/`.csv` | "
                "③ 设计空间第一轮：7 种被试内设计 × 6 种 P 方案，判据 `beta_T` 10% / `beta_P` 0.30 / `tau_P` 0.50 | "
                "✅ oracle 口径 39–40 人/组（`4T×4W r9` 最优）；design 口径现行方案「被试层漂移不可识别」、"
                "改 5 水平后 37 人/组；**已暴露**「P≤32 漂移被 `max(0,·)` 截到 0 ⇒ 只剩 2 个有效水平」 |")
        print("evidence row rewritten at", i + 1)
MP.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("主计划 ok", len(L))

# ------------------------------------------------------------------ README
r = RD.read_text(encoding="utf-8")
pair_rd = [
    ("| oracle（`P_ref`=30、`beta_P`=0.35，四水平都有信息） | **39–40 人/组** | `4T×4W r9` × 任一 P 方案 | `tau_P` |",
     "| oracle（`P_ref`=30、`beta_P`=0.35，四水平都有信息） | **39–40 人/组** | `4T×4W r9` × 任一 P 方案 | `beta_T` |"),
    ("| design（`P_ref`=120、`beta_P`=1.5，`drift_magnitude` 取 `max(0,·)`） | **161 人/组** | 同上 | 同上 |",
     "| design（`P_ref`=120、`beta_P`=1.5，`drift_magnitude` 取 `max(0,·)`） | 现行 P 方案：**不可识别**；5 水平 0/8/24/64/120：**37 人/组** | `4T×4W r9` | `tau_P` |"),
    ("oracle 口径 **39–40 人/组**、design 口径 **161 人/组**",
     "oracle 口径 **39–40 人/组**、design 口径现行方案 **不可识别**（5 水平 37 人/组）"),
    ("剩下的有效水平只有 {32, 120} 两个 ⇒ `beta_P` 是一条两点斜率，`tau_P` 只能靠两点之间的曲率，\n识别极其脆弱。**这不是「人数不够」，是「设计里没有东西可估」**。",
     "剩下的有效水平只有 {32, 120} 两个 ⇒ `beta_P` 是一条两点斜率，`tau_P` 根本没有信息可用（三参数要三个以上的点）。\n"
     "脚本据此把这类组合直接判成「被试层漂移不可识别」，而不是给一个「N = 8 就够」的假数字——\n"
     "`pinv` 在秩亏时会把不可估的方向报成 0 方差，那是「估不出来」，不是「估得准」。\n"
     "**这不是「人数不够」，是「设计里没有东西可估」**。"),
    ("`1_Code/Experiment/design_search.py`（263 行）：7 种被试内设计 × 6 种 P 方案；",
     "`1_Code/Experiment/design_search.py`（323 行）：7 种被试内设计 × 6 种 P 方案；"),
]
for old, new in pair_rd:
    assert r.count(old) == 1, (r.count(old), old[:50])
    r = r.replace(old, new)
RD.write_text(r, encoding="utf-8", newline="\n")
print("README ok")
