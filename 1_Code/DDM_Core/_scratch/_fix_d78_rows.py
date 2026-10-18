# -*- coding: utf-8 -*-
"""_fix_d78_rows.py —— 把 D78 的决策行/进度行补成 5 列（决策表与进度表都是 5 列）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"

t = MP.read_text(encoding="utf-8")
lines = t.split("\n")

# --- 决策行（L503，index 502）
i = next(k for k, ln in enumerate(lines) if ln.startswith("| **D78** | 2026-10-18 |"))
old = lines[i]
core = old.rstrip()
if not core.endswith("|"):
    raise SystemExit("决策行不是完整表格行")
body = core[:-1].rstrip()  # 去掉结尾竖线
if body.count("|") != 3:
    raise SystemExit(f"决策行竖线数异常：{body.count('|')}")
new = (
    body
    + " | `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（**v4.4**，1357 行）+ `exp_new_data.m`（**新建**，1120 B）"
    " + `exp_data_table.m`（**新建**，1519 B）+ `test/check_data_accum.m`（**新建**，7896 B，24/24）；"
    "日志 `test/_check_data_accum.txt`（通过 24 / 未通过 0） "
    "| 采集前 `check_data_accum` 必须是四条自测之一；改输出列或改响应取值必须同步该自测；"
    "现场若再出现「跑到一半突然关屏」，先看 `Exp_Design_Formal.m` 头部版本是否 v4.4 |"
)
lines[i] = new

# --- 进度行（原 L572，index 571）
j = next(k for k, ln in enumerate(lines) if ln.startswith("| 2026-10-18 | **1/7**（数据写入防线 → D78） |"))
lines[j] = (
    "| 2026-10-18 | **1/7**（数据写入防线 → D78） | **修掉「第一个未响应试次必崩」**：v4.3 用 `data = table()` 逐行追加，"
    "`Response` 列宽被首行 `f`（1 字符）锁死，第一个 timeout 写 `NA`（2 字符）即 `赋值右侧的值的宽度错误` 整场退出。"
    "v4.4 改为 `exp_new_data.m` 的 0×25 cell 累积 + `exp_data_table.m` 一次性 `cell2table`（char 列转 `string` 去补齐空格），"
    "保存前核对 `size(data,1) == trialIndex-1`；新增 `test/check_data_accum.m` **24/24**（含「先 f 后 NA」崩溃复现、"
    "不等长标签、静态守卫、写读回环），手册 v2.2 与 Stage 1/Stage 7 现场清单同步改为**四条**自测。 "
    "| 见 D78 决策行 | 用户侧 Stage 1 实机验收（先跑四条自测）/ Stage 6 Pilot / Stage 7 正式采集 / 定稿签批 |"
)

MP.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("已修正 D78 决策行与进度行为 5 列")
