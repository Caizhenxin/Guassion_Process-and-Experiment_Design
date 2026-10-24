from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
plan = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
readme = ROOT / "1_Code" / "DDM_Core" / "README.md"

s = plan.read_text(encoding="utf-8")
lines = s.split("\n")

# ---------- 1) 决策表：D119 插在 D117 行之后（D118 是更早日期、插在后面了）
d119 = (
    "| **D119** | 2026-10-24 | **20 人新数据到手：首轮分析把「模型缺 SPE」的疑问关掉——SPE 在数据里很强，是漂移型，缺的是速率通道而不是结构**。"
    "新建 `1_Code/Experiment/real_data_check.py`：读 `2_Data/Real_Data/New_Design`（4 组 × 5 人 = 20 人 / 12,320 试次），"
    "清洗口径 `responded_by_deadline==1 且 120 ms < RT <= W+50 ms`（→ 8,992 试次），T/W 先归设计档位（`T_lvl` 33.3/83.3/150/250 ms、`W_lvl` 800/1200/1800 ms）再分组。"
    "读数（20 人配对，t 近似 CI + 自举 20,000）：**Δacc +5.9 pp**（CI 1.6–10.3，t=2.66）、**ΔRT 中位 +38.2 ms**（CI 22.7–53.8，t=4.81）、"
    "**分位斜率 q90−q10 = +47.2 ms**（CI 11.5–82.9，t=2.59），ΔRT 从 q10 的 −0.6 ms 单调升到 q90 的 +46.6 ms ⇒ 按 D114 判别规则落在**漂移型**第 ① 支。"
    "按 P：Δacc 0.144/0.056/0.016/0.020、ΔRT 59.7/34.2/18.6/40.4（P=0 最强、P=120 回抬；每组 5 人且四组总正确率本身就不同 ⇒ 不可作剂量-反应推断）。"
    "设计变量：T↑ 正确率 0.65→0.77 而 **RT 中位不变**（687–699 ms）、W↑ 正确率 0.63→0.78 且 RT 变长（586→759 ms）⇒ 与模型一致。"
    "**与 8 支候选（D117）对照**：真实点（可见度 |ΔRT|/SD = 0.16、Δacc 5.9 pp）；`const` 可见度只 0.077、`gate` Δacc≈0，"
    "「每 1 pp 正确率换多少 ms」真实 **6.5 ms/pp**、`const` 3.5、`gate_drift` 15.6 ⇒ 真实值夹在中间，**约 1/4 的 RT 优势来自不改正确率的速率通道 `r_S`**。"
    "质检：超时 26.1%、提前按键 9.6%、`|dur−T|` 均值 2.71 ms（最大 240 ms，每场 1–2 个掉帧试次）；"
    "异常场次 `3-1`（RT q50 = 230 ms、两条件正确率 0.484/0.500、84 个掉帧试次）判为疑似无效，**主统计保留 n=20、另出剔除后敏感性**（Δacc 0.059→0.062、ΔRT 38.2→40.3 ⇒ 剔除后更强，非效应来源）。"
    "**处置**：主模型结构不改（漂移型被数据支持）；`r_S` 进似然列为下一轮，需照 D118 做逐位回归 + 通路检查；"
    "结果章必须同时报**分位斜率与个体分布**（12/20 为正、个别 −134 ms ⇒ 斜率异质，均值靠几个大正值拉动）。"
    " | 用户 2026-10-24「我带来了20人数据……请问现在能做啥」；前两轮已确认「模型是不是没能体现 SPE」是待答问题（D114 判别规则已就位但缺实测数据）"
    " | `1_Code/Experiment/real_data_check.py`（**新建**）+ `3_Figures/_real_check/fig_r1..r6` + `2_Data/Generate_Data/_real_check/`（9 个 CSV + `meta.json`）"
    "+ `2_Data/Real_Data/New_Design/README.md`（**新建**，列字典 + 清洗口径 + 质检）+ `5_Reference/03_论文写作/真实数据分析_首轮结果_20261024.md`（**新建**） |"
)

idx = next(i for i, ln in enumerate(lines) if ln.startswith("| **D117** |"))
lines.insert(idx + 1, d119)

# ---------- 2) 进度表
progress = (
    "| 2026-10-24 | **16（20 人真实数据首轮 → D119）** | **把「模型缺 SPE」改成「模型缺通道」**：SPE 实测 +5.9 pp 且快 38 ms，"
    "分位斜率 +47 ms（漂移型）；`const` 只能出 22 ms、`gate` 出 64 ms 但没有正确率差 ⇒ 真实值夹在两者之间（6.5 ms/pp vs 3.5 / 15.6），"
    "**约 1/4 的 RT 优势来自速率通道**。这同时把 D117 的推荐从「图上的候选」推进到「有数据支撑的下一步」；"
    "也解释了此前「模拟里 SPE 只有 22 ms、肉眼看不出」不是机制失效而是**参数与通道都偏保守**。 |"
)
idx = next(i for i, ln in enumerate(lines) if ln.startswith("| 2026-10-25 | **15（SPE 机制候选集"))
lines.insert(idx + 1, progress)

# ---------- 3) 变更日志
changelog = (
    "| 2026-10-24 | **新增 D119（20 人真实数据首轮分析）**：`real_data_check.py` 一条管线出质检 → 描述统计 → 逐被试 SPE → 六张图 → 取舍平面；"
    "顺手修三个真坑：① `plt.rcParams[\"axes.spines\"][\"top\"]` 抛 `KeyError`（应为 `axes.spines.top`）；"
    "② `T`/`W` 列存的是**逐试次实际值**（如 0.033328736），直接 `groupby` 会把 20 人拆成 80 个伪档位 ⇒ 加 `T_lvl`/`W_lvl` 归位；"
    "③ W 的正确率方向原先按错误口径写成「越长越不准」，按设计档位重算后是**越长越准**（提交里已改正）。 |"
)
idx = next(i for i, ln in enumerate(lines) if ln.startswith("| 2026-10-25 | **新增 D117（8 支 SPE 候选机制比较）**"))
lines.insert(idx + 1, changelog)

# ---------- 4) 证据表
evidence = (
    "| `1_Code/Experiment/real_data_check.py` + `3_Figures/_real_check/fig_r1..r6` + `2_Data/Generate_Data/_real_check/*.csv` | "
    "D119 证据：20 人 SPE 的**全部分位读数与质检数字**都在这条管线里（Δacc +5.9 pp / ΔRT 中位 +38.2 ms / 斜率 +47.2 ms；"
    "超时 26.1%、掉帧均值 2.71 ms、`3-1` 异常场次、剔除后敏感性 `spe_summary_drop.csv`）。重跑一次约 20 s，"
    "改 `--drop` 可换敏感性口径；改 `--data/--out/--figout` 可指向新一批数据。 |"
)
last = len(lines) - 1
while last >= 0 and not lines[last].startswith("| `1_Code/Experiment/spe_families.py`"):
    last -= 1
lines.insert(last + 1, evidence)

plan.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("plan lines:", len(lines))

# ---------- 5) 1_Code/DDM_Core/README.md 第 9 节加第 100 项
r = readme.read_text(encoding="utf-8")
rl = r.split("\n")
new_row = (
    "| 100 | ✅ **20 人真实数据首轮分析（D119）** | `1_Code/Experiment/real_data_check.py`：一次跑完质检 → 描述统计 → 逐被试 SPE → 六图 → 取舍平面。"
    "结论：SPE 在数据里很强（Δacc +5.9 pp、ΔRT 中位 +38.2 ms、分位斜率 +47.2 ms，20 人配对）且是**漂移型**；"
    "`const` 只给 22 ms、`gate` 给 64 ms 但无正确率差，真实 6.5 ms/pp 夹在 3.5 与 15.6 之间 ⇒ **约 1/4 的 RT 优势来自速率通道 `r_S`**。"
    "产物 `2_Data/Generate_Data/_real_check/` + `3_Figures/_real_check/`；数据字典见 `2_Data/Real_Data/New_Design/README.md`。 |"
)
i100 = next(i for i, ln in enumerate(rl) if ln.startswith("| 99 | ✅ **判据通道"))
rl.insert(i100 + 1, new_row)
readme.write_text("\n".join(rl), encoding="utf-8", newline="\n")
print("readme lines:", len(rl))
