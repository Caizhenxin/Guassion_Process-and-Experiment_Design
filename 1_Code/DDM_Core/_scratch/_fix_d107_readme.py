# -*- coding: utf-8 -*-
"""README 侧 D107 修订（单行版本）。"""
from pathlib import Path

RD = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\README.md")
r = RD.read_text(encoding="utf-8")
pairs = [
    ("| oracle（`P_ref`=30、`beta_P`=0.35，四水平都有信息） | **39–40 人/组** | `4T×4W r9` × 任一 P 方案 | `tau_P` |",
     "| oracle（`P_ref`=30、`beta_P`=0.35，四水平都有信息） | **39–40 人/组** | `4T×4W r9` × 任一 P 方案 | `beta_T` |"),
    ("| design（`P_ref`=120、`beta_P`=1.5，`drift_magnitude` 取 `max(0,·)`） | **161 人/组** | 同上 | 同上 |",
     "| design（`P_ref`=120、`beta_P`=1.5，`drift_magnitude` 取 `max(0,·)`） | 现行 P 方案：**不可识别**；5 水平 0/8/24/64/120：**37 人/组** | `4T×4W r9` | `tau_P` |"),
    ("oracle 口径 **39–40 人/组**、design 口径 **161 人/组**",
     "oracle 口径 **39–40 人/组**、design 口径现行方案 **不可识别**（5 水平 37 人/组）"),
    ("剩下的有效水平只有 {32, 120} 两个 ⇒ `beta_P` 是一条两点斜率，`tau_P` 只能靠两点之间的曲率，识别极其脆弱。**这不是「人数不够」，是「设计里没有东西可估」**。",
     "剩下的有效水平只有 {32, 120} 两个 ⇒ `beta_P` 是一条两点斜率，`tau_P` 根本没有信息可用（三参数要三个以上的点）。"
     "脚本据此把这类组合直接判成「被试层漂移不可识别」，而不是给一个「N = 8 就够」的假数字——"
     "`pinv` 在秩亏时会把不可估的方向报成 0 方差，那是「估不出来」，不是「估得准」。"
     "**这不是「人数不够」，是「设计里没有东西可估」**。"),
    ("`1_Code/Experiment/design_search.py`（263 行）：7 种被试内设计 × 6 种 P 方案；",
     "`1_Code/Experiment/design_search.py`（323 行）：7 种被试内设计 × 6 种 P 方案；"),
]
for old, new in pairs:
    c = r.count(old)
    assert c == 1, (c, old[:50])
    r = r.replace(old, new)
RD.write_text(r, encoding="utf-8", newline="\n")
print("README ok")
