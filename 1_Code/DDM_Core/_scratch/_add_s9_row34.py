# -*- coding: utf-8 -*-
"""把 `1_Code/DDM_Core/README.md` §9 的第 34 项追加到第 33 项之后。

锚点限定在 `## 9. ` 节内（历史上 ``| 32 |`` 曾在别处出现，D52 就因此被守卫拦过一次）。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path("1_Code/DDM_Core/README.md")
ROW = (
    "| 34 | ✅ **Stage 9 的优化循环已交付（D53，含一条会改变结论口径的实测）** | "
    "新建 `1_Code/AutoRA_SPE/stage9_loop.py`（617 行、裸 LF）与 "
    "`1_Code/AutoRA_SPE/check_stage9_loop.py`（261 行、裸 LF，A–G 七组，"
    "**21/21 通过、exit 0、67.2 s**）。**候选空间**：`T_POOL_MS`（2/5/9/15/21/27 帧）"
    "× `W_POOL_MS`（48/72/108/144 帧）× `n_rep ∈ {8,12,16,18,24}`，受 "
    "`len(T)·len(W)·n_rep = 576/4 = 144`（第 21 项：576 试次/人 ⇒ 四类刺激单元）与程序自检 C3"
    "（`W − T − 200 ms ≥ 300 ms`，`Exp_Design_Formal.m` L250-256）双约束 ⇒ "
    "**枚举实测 174 个可行设计、186 个被 C3 否决（C1 一个都没否决）**，"
    "每个候选 `n_trials == 576` 逐字成立。**CRN 种子由设计内容（名字的 sha256 前 12 位）导出**，"
    "不由候选表下标导出 —— 实测完整表（下标 0）与截断表（下标 20）里同一设计种子与读数"
    "**逐位相同**，174 个设计 → 174 个不同种子（这是处方④在代码里的形态）。"
    "**四臂同预算有牙齿**：`run_arms` 在 `len(names) != budget` 时抛 `RuntimeError`"
    "（D2b 人为让一臂超支 ⇒ 确实抛）。❗ **交付时改掉两处自己的缺陷**："
    "① `arm_grid` 原先取「候选表前 N 个」，而候选表按 `(n_t, n_w, 组合)` 字典序排 ⇒ "
    "前 6 个**全是 `r24` / `T` 最短 / `W` 最短的不可行角落**，那是把有偏角落样本冒充网格 ⇒ "
    "改为等距空间填充扫掠；② ❗❗ **单位坑**：`inner_eval` 收**秒**、桥模块收**毫秒**，"
    "而候选表存的是毫秒 ⇒ 首跑把毫秒当秒喂进去，**不报任何错**，只是静默给出 `omission = 0.0`、"
    "`cond = 3.96e+17`、`relative_se` 量级 10⁴；症状是冻结 Objective 的三道闸门**全部拒绝**"
    "（`RuntimeError: 缓存里没有任何可行设计` —— 闸门尽职了）。修法：**单位只在 `levels_sec()` "
    "一处换算**，两个 `inner_eval` 调用点都走它；B1/B1b 断言缓存路径与直接调用**逐位相同**"
    "（`max\\|Δ\\| = 0.000e+00`），**B2 专门把毫秒当秒再喂一次**（Δ遗漏 = 0.361、"
    "`cond` 8.91e15 vs 5.4e4）作为这条坑的回归钉。❗ **冒烟的四条读数**"
    "（budget 12、`n_fim=1`、`rho = 0.6`，40 次评估 / 182 s）：(a) 锚点 D4 "
    "`A = 0.3851 / B = 7.4007 / J = 10.4400`，四臂 best J = `grid 0.4673 < manual 0.5112 "
    "< random 0.5405 < bo 0.6382` ⇒ **该预算下 BO 没赢过空间填充网格**；"
    "(b) **锚点 D4 被 `T[33.33/83.33/249.98]ms × W[799.98/1199.90/2399.80]ms × r16` "
    "在 (A,B) 两维上同时支配**（A 0.3324 < 0.3851、B 7.9303 > 7.4007）⇒ "
    "**「D4 不是 Pareto 最优」与遗漏率罚分无关**，这是 Stage 9 局部审计最稳的一句话；"
    "(c) 进入前沿的设计**全部取 W 高档**且 `C = 0`，而 D4 在 `rho = 0.6` 下遗漏 0.356 ⇒ "
    "`C ≈ 9.7` ⇒ **罚分带只在「高 W」区可达**，而 Objective **没有「会话总时长」成本项** ⇒ "
    "它会系统性把 W 推向池上限（2399.8 ms）；(d) ❗ **`n_fim=1` 时内环 MC 噪声"
    "（`sd_J = 2.92`，两次重算 `J = 9.5112 / 13.6474`）大于设计之间的差异（0.47–0.64）** ⇒ "
    "**该配置下的臂间比较不可解释**；`--noise-repeats 2` 的 SD 只有 1 个自由度"
    "（同一指标另一次冒烟为 `sd_J = 0.074`）⇒ 进论文的消融必须提高 `n_fim` 且 "
    "`--noise-repeats ≥ 5`，并**重复整个消融（R 个种子组）**才能得到配对误差棒。"
    "**遗传自**：第 7 / 17 / 31 项（`design_fim` 的 CRN 天然性；M-T1 内环仪器；"
    "`stage9_inner` / `stage9_objective`）；限制与口径见 "
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §11 第 12–15 条 |"
)

lines = P.read_text(encoding="utf-8").split("\n")
start = next(i for i, s in enumerate(lines) if s.startswith("## 9."))
hits = [i for i, s in enumerate(lines) if i >= start and s.startswith("| 33 |")]
if len(hits) != 1:
    print(f"❌ 锚点 | 33 | 在 §9 内命中 {len(hits)} 次，拒绝写回")
    raise SystemExit(2)
i33 = hits[0]
if lines[i33 + 1].strip():
    print(f"❌ 第 33 项之后不是空行（是 {lines[i33 + 1][:40]!r}），拒绝写回")
    raise SystemExit(2)
n_sep = lines[i33].count("|") - lines[i33].count("\\|")
n_sep_new = ROW.count("|") - ROW.count("\\|")
if n_sep != n_sep_new:
    print(f"❌ 分隔符数不一致：第 33 项 {n_sep}、新行 {n_sep_new}，拒绝写回")
    raise SystemExit(2)
print(f"锚点 L{i33 + 1}、分隔符 {n_sep}、新行分隔符 {n_sep_new} —— 一致")
lines.insert(i33 + 1, ROW)
if lines[i33 + 1] != ROW or lines[i33 + 2].strip() != "":
    print("❌ 插入后断言失败")
    raise SystemExit(2)
out = "\n".join(lines)
if not out.endswith("\n"):
    print("❌ 输出不以换行结尾")
    raise SystemExit(2)
P.write_text(out, encoding="utf-8", newline="\n")
print(f"✅ 已写入：{P}（{len(lines) - 1} 行、新行在第 {i33 + 2} 行）")
