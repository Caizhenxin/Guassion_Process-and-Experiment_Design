"""给失败记录追加「再次触发记录（2026-10-18，Δelpd 的 SE 口径）」。

同一根因（口径错但读数看起来完整）：把两个 LOO 的 SE 平方相加当作 Δelpd 的 SE。
"""
from pathlib import Path

REC = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement"
           r"\2026-10-18_工具在能力不足时静默输出健康读数.md")

BLOCK = """
---

## 再次触发记录（2026-10-18，Δelpd 的 SE 口径）

**同一根因**：口径错了，但输出的数字看起来很正常，检查器也不会报。

- **情境**：D98 全流程出图（`1_Code/Experiment/make_figures.py`）与结果节骨架
  （`1_Code/Experiment/run_pipeline.py`）都要报 Δelpd 的标准误。
- **当时的写法**：`se = sqrt(se_a^2 + se_b^2)` —— 把两个模型各自的 LOO SE 当独立量相加。
- **为什么错**：两个模型在**同一批观测**上算 LOO，`elpd_i` 是逐观测贡献，两个模型共享
  同一批数据的变异。正确口径是配对差：`SE = sqrt(n) * sd(elpd_i^A − elpd_i^B)`
  （Vehtari 等 2017 的 `se_diff`）。
- **实测放大**：同一份 `stage8_group_1.json` 上，独立相加给 **38.2**，配对口径给 **1.1**
  —— 放大 **约 35 倍**，方向是「把显著的结果说成不显著」（保守但失真）。
- **谁抓到的**：不是检查器，是我自己并排核对 `figures_index.md`（38.2）与
  `results_skeleton.md`（7.4）两个数字对不上，才发现两处都错、且错法不同
  （骨架那处是另一个更早的写法）。
- **修法**：两处统一成同一个配对口径；`paired_se()` 在 `make_figures.py` 与
  `PAIRED_SE()` 在 `run_pipeline.py` 各一份（**已知技术债**：同一判据两处实现，
  应合并成一个模块，理由与 D94 相同——重复实现必然分叉）。
- **新增教训（第 5 条）**：**同一张报告里出现的同一个量，必须由同一个函数产出**。
  两个工具各自算一次 Δelpd 的 SE，就一定会给出两个不同的数；不一致本身就是缺陷信号，
  不能靠「取其中一个」掩盖。
- **检查动作**：出图后并排看 `figures_index.md` 与 `results_skeleton.md` 的同一行数字；
  不一致先停下查口径，不要挑一个顺眼的。

`#配对口径` `#se_diff` `#PSIS-LOO` `#Δelpd` `#重复实现分叉` `#Stage8` `#图表陷阱`
"""

text = REC.read_text(encoding="utf-8")
assert "再次触发记录（2026-10-18，Δelpd 的 SE 口径）" not in text
REC.write_text(text.rstrip("\n") + "\n" + BLOCK, encoding="utf-8", newline="\n")
print("ok", len(REC.read_text(encoding='utf-8').splitlines()), "lines")
