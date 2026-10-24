from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
lines = p.read_text(encoding="utf-8").split("\n")

i = next(k for k, ln in enumerate(lines) if ln.startswith("| 2026-10-24 | **16（20 人真实数据首轮 → D119）**"))
new = (
    "| 2026-10-24 | **16（20 人真实数据首轮 → D119）** | **把「模型缺 SPE」改成「模型缺通道」**：SPE 实测 +5.9 pp 且快 38 ms（中位），"
    "分位斜率 +47 ms ⇒ 漂移型；`const` 只能出 22 ms、`gate` 出 64 ms 但没有正确率差，真实「每 1 pp 换 6.5 ms」夹在 3.5 与 15.6 之间 ⇒ "
    "**约 1/4 的 RT 优势来自速率通道**。这同时把 D117 的推荐从「图上的候选」推进到「有数据支撑的下一步」，"
    "也解释了此前「模拟里 SPE 只有 22 ms、肉眼看不出」不是机制失效而是**参数与通道都偏保守**。 "
    "| 用户 2026-10-24「我带来了20人数据……请问现在能做啥」 | `1_Code/Experiment/real_data_check.py` + `3_Figures/_real_check/fig_r1..r6` + "
    "`2_Data/Generate_Data/_real_check/` + 备忘 `真实数据分析_首轮结果_20261024.md` |"
)
print("old pipes:", lines[i].count("|"), "-> new:", new.count("|"))
lines[i] = new
p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
