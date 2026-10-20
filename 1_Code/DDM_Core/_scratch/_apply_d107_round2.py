# -*- coding: utf-8 -*-
"""D107 第二轮：中段 P 方案没有更省，答案稳定在「144 试次/人 + 40 人/组」。"""
from pathlib import Path

ROOT = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
RD = ROOT / "1_Code/DDM_Core/README.md"

mp_old = "把 P 改成 5 水平（0/8/24/64/120）后才回到 37 人/组。"
mp_new = ("把 P 改成 5 水平（0/8/24/64/120）后才回到 37 人/组。**第二轮**又试了三套「中段」方案"
          "（40/60/90/120、40/80/120/180/240、40/55/70/90/120，全部 ≥40 以避开截断），"
          "结果都比 5 水平更贵 ⇒ 曲率信息主要来自 24–120 这一段，P 不是越靠中越好。"
          "**稳态答案：`4T×4W r9`（144 试次/人，加一个 W=1400 ms 水平）+ P 五水平 ⇒ 37 人/组**"
          "（oracle 口径 39 人/组，两口径都卡在 `beta_T`）。")
s = MP.read_text(encoding="utf-8")
assert s.count(mp_old) == 1
MP.write_text(s.replace(mp_old, mp_new), encoding="utf-8", newline="\n")
print("主计划 ok")

rd_old = "3. 未做：改 P 方案重跑、把这轮结果画成图、把 (a)/(b) 的选择写进方法章。"
rd_new = """3. **第二轮（已做）**：三套「中段」方案（40/60/90/120、40/80/120/180/240、40/55/70/90/120，全部 ≥40 以避开截断）
   都比 5 水平更贵 ⇒ 曲率信息主要来自 24–120 这一段，**P 不是越靠中越好**。
4. **稳态答案**：`4T×4W r9`（144 试次/人，加 W=1400 ms 水平）× P 五水平 0/8/24/64/120 ⇒ **37 人/组**（design 口径）、
   **39 人/组**（oracle 口径），两口径都卡在 `beta_T`；现行 `4T×3W r12` 同方案要 43 人 ⇒ **加一个 W 水平比加人便宜**。
5. 未做：把这轮结果画成图、把 (a)/(b) 的选择写进方法章。"""
r = RD.read_text(encoding="utf-8")
assert r.count(rd_old) == 1
RD.write_text(r.replace(rd_old, rd_new), encoding="utf-8", newline="\n")
print("README ok")
