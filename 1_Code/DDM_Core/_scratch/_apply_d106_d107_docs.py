# -*- coding: utf-8 -*-
"""落纸 D106（峰谷闸门）与 D107（③ 设计空间第一轮）到主计划与 README。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RD = ROOT / "1_Code" / "DDM_Core" / "README.md"


def ncol(line: str) -> int:
    return line.count("|") - 1


def rows_of(line: str, cells) -> str:
    """按锚点行的列数把 cells 补齐成一行 markdown。"""
    k = ncol(line)
    cells = list(cells)[:k]
    while len(cells) < k:
        cells.append("—")
    return "| " + " | ".join(cells) + " |"


# ------------------------------------------------------------ 主计划
s = MP.read_text(encoding="utf-8")
L = s.split("\n")

d105 = next(i for i, x in enumerate(L) if x.startswith("| **D105** |"))
prog105 = next(i for i, x in enumerate(L) if x.startswith("| 2026-10-18 | **9（论文级模拟图 → D105）**"))
log105 = next(i for i, x in enumerate(L) if x.startswith("| 2026-10-18 | **新增 D105（论文级模拟图）**"))

D106 = rows_of(L[d105], [
    "**D106**", "2026-10-20",
    "**只在 DeepSeek 空闲时段开工（用户指定的硬规则）**。闸门 "
    "`C:\\Users\\蔡振辛\\AppData\\Roaming\\dsh-desktop\\harness\\offpeak_gate.py`"
    "（+ 同目录 `offpeak_holidays.json`）按北京时间判定：**周一至周五（不含法定节假日）"
    "09:00–12:00 / 14:00–18:00 = 高峰**，其余全天空闲；退出码 0 = 可开工、3 = 立即停"
    "（不发起、不续跑、不起后台作业）。规则本体写进 `$DSH_HOME/AGENTS.md` §6，"
    "边界测试覆盖 08:59/09:00/11:59/12:00/13:59/14:00/18:00/周末/法定节假日/夜间 共 10 个时刻。",
    "空闲单价为高峰一半；用户 2026-10-20 要求「下次在空闲时段再继续，超时就别再发起，等我自己来」",
    "全局（`$DSH_HOME/AGENTS.md` §6 + `offpeak_gate.py` + `offpeak_holidays.json`）",
    "❌ 未接入自动续跑的强制拦截（闸门只能被「读取规则的一方」调用；若某轮不读 AGENTS.md 就会漏检）",
])

D107 = rows_of(L[d105], [
    "**D107**", "2026-10-20",
    "**③ 设计空间第一轮：把「被试内 T/W × 被试间 P 方案」放进同一个搜索**。新工具 "
    "`1_Code/Experiment/design_search.py`（263 行）：7 种被试内设计 × 6 种 P 方案，"
    "判据 `beta_T` 10% / `beta_P` 0.30 / `tau_P` 0.50，总需人 = 三者最大值。"
    "结果：**oracle 真值下 39–40 人/组**（`4T×4W r9` 最优）；**design 真值下 161 人/组**。"
    "落差根因：`drift_magnitude` 对幅度取 `max(0,·)`，design 真值（P_ref=120、beta_P=1.5）"
    "的 P≤32 漂移被截到 0 ⇒ **P 设计实际只剩 2 个有效水平**，`tau_P` 只能靠曲率识别 ⇒ 人数爆炸。",
    "`beta_T` 41 人（D105 CRLB）与「40 人/组」的现行方案一致；但 `tau_P` 才是真正的稀缺资源，"
    "而它是否可估**完全取决于 P 水平怎么放**——这条在 D105 的 oracle 图里被「四水平都有信息」的"
    "真值掩盖了",
    "`1_Code/Experiment/design_search.py` + `5_Reference/03_论文写作/figures_sim/design_search.md`/`.csv`",
    "① 改 P 水平为中段更密（0/60/120/240 等）重跑；② 把 `tau_P` 在论文里降级为「仅粗解释」；"
    "③ 还没画图",
])

prog = rows_of(L[prog105], [
    "2026-10-20",
    "**10（③ 设计空间优化 → D107）**",
    "**第一轮跑完、结论已定**：oracle 口径 39–40 人/组、design 口径 161 人/组；抓出「P≤32 漂移被截到 0 ⇒ "
    "只剩两个有效水平」这一结构性问题。未做：改 P 方案重跑、出图、把结论回写论文方法章。",
    "`1_Code/Experiment/design_search.py`；报告 `figures_sim/design_search.md`",
])

log = rows_of(L[log105], [
    "2026-10-20",
    "**新增 D106（峰谷闸门）+ D107（③ 设计空间第一轮）**：`offpeak_gate.py` 按北京时间判峰谷、"
    "退出码 3 即停，规则写进 `$DSH_HOME/AGENTS.md` §6；`design_search.py`（263 行）把被试内 T/W 与"
    "被试间 P 方案放进同一搜索，oracle 口径 39–40 人/组 vs design 口径 161 人/组，"
    "根因是 design 真值的低 P 水平漂移被截到 0（只剩 2 个有效水平）。",
    "`1_Code/Experiment/design_search.py`；`figures_sim/design_search.md`；`$DSH_HOME/offpeak_gate.py`",
])

for off, new in ((log105, log), (prog105, prog), (d105, D107), (d105, D106)):
    L.insert(off + 1, new)
# 先插 D107 再插 D106 会导致顺序反转，这里保证 D106 在前
i106 = L.index(D106)
i107 = L.index(D107)
if i106 > i107:
    L[i106], L[i107] = L[i107], L[i106]

# 证据表：追加一行
anchor = next(i for i, x in enumerate(L)
              if x.startswith("| `1_Code/Experiment/make_sim_figures.py`（**新建**，D105"))
ev = rows_of(L[anchor], [
    "`1_Code/Experiment/design_search.py`（**新建**，D107，263 行）+ "
    "`5_Reference/03_论文写作/figures_sim/design_search.md` / `design_search.csv`",
    "③ 设计空间第一轮：7 种被试内设计 × 6 种 P 方案，判据 `beta_T` 10% / `beta_P` 0.30 / `tau_P` 0.50",
    "✅ 两种组层真值各跑一遍：oracle 39–40 人/组（`4T×4W r9`）、design 161 人/组；"
    "**已暴露**「P≤32 漂移被 `max(0,·)` 截到 0 ⇒ 只剩 2 个有效水平」；未做：改 P 方案重跑、出图",
])
L.insert(anchor + 1, ev)

MP.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("主计划 lines", len(L))

# ------------------------------------------------------------ README
r = RD.read_text(encoding="utf-8")
R = r.split("\n")

item87 = next(i for i, x in enumerate(R) if x.startswith("| 87 | ✅ **论文级模拟图（D105）**"))
I88 = ("| 88 | ✅ **峰谷闸门（D106）** | `$DSH_HOME/offpeak_gate.py` + `offpeak_holidays.json`："
       "北京时间判「工作日 09:00–12:00 / 14:00–18:00 = 高峰」，退出码 3 即停；"
       "规则落在 `$DSH_HOME/AGENTS.md` §6；10 个边界时刻全部对（09:00/12:00/14:00/18:00、周末、节假日、夜间）。"
       "**未做**：闸门不是强制拦截，只有读取规则的一方才会调用它 |")
I89 = ("| 89 | 🟡 **设计空间第一轮（D107）** | `1_Code/Experiment/design_search.py`（263 行）："
       "7 种被试内设计 × 6 种 P 方案；oracle 口径 **39–40 人/组**、design 口径 **161 人/组**；"
       "**未做**：改 P 水平（中段加密）重跑、画图、把「`tau_P` 不可估」的决定写进论文 |")
R.insert(item87 + 1, I88)
R.insert(item87 + 2, I89)

# §8.76 小节，插在 “## 9. 尚未做” 之前
sec = next(i for i, x in enumerate(R) if x.startswith("## 9. 尚未做"))
block = [
    "## 8.76 ③ 设计空间第一轮：把「多少人」换成「怎么放 P」（D107）",
    "",
    "**一句话**：在给定试次预算内，真正决定「要多少人才够」的不是 `beta_T`（41 人，D105 已算过），"
    "而是 `tau_P`；而 `tau_P` 能不能估，完全取决于 P 水平放在哪。",
    "",
    "### 做了什么",
    "",
    "`1_Code/Experiment/design_search.py`（263 行）把两件事放进同一个搜索：",
    "",
    "* **被试内**：7 种 (T 水平 × W 水平 × 每单元重复) ≈ 135–144 试次/人，用 OPG CRLB 算 `beta_T` 相对 SE；",
    "* **被试间**：6 种 P 方案（3/4/5/6 水平、加宽到 240），用三参数 Jacobian"
    "（`d_ref`、`beta_P`、`tau_P`）加权回归算相对 RMSE，权重同时含被试间 SD 与该水平的试次噪声。",
    "",
    "判据：`beta_T` ≤ 10%、`beta_P` ≤ 0.30、`tau_P` ≤ 0.50；总需人 = 三者最大值。",
    "",
    "### 结果（同一份代码、两种组层真值）",
    "",
    "| 组层真值 | 最省人数 | 最优组合 | 卡在哪 |",
    "|---|---|---|---|",
    "| oracle（`P_ref`=30、`beta_P`=0.35，四水平都有信息） | **39–40 人/组** | `4T×4W r9` × 任一 P 方案 | `tau_P` |",
    "| design（`P_ref`=120、`beta_P`=1.5，`drift_magnitude` 取 `max(0,·)`） | **161 人/组** | 同上 | 同上 |",
    "",
    "### 为什么差 4 倍（这才是要写进论文的那一半）",
    "",
    "`design_fim.TRUTH` 的 `beta_P = 1.5`、`P_ref = 120`，而 `mapping.drift_magnitude` 对幅度取 `max(0, ·)`。"
    "于是 P = 0 / 8 / 32 的漂移分别被算成 **0.000 / 0.000 / 0.211**（P = 120 才是 0.700）——"
    "**低 P 三个水平在实际数据里几乎都是「零证据」条件**，被试层 CRLB 在漂移簇上直接奇异"
    "（`pinv` 给出的 SE 恰好为 0，这是「无信息」不是「完美精度」，脚本里按 `SE > 1e-9` 剔除）。",
    "",
    "剩下的有效水平只有 {32, 120} 两个 ⇒ `beta_P` 是一条两点斜率，`tau_P` 只能靠两点之间的曲率，"
    "识别极其脆弱。**这不是「人数不够」，是「设计里没有东西可估」**。",
    "",
    "### 结论与待办",
    "",
    "1. `tau_P` 是真正的稀缺资源；`beta_T` 的 41 人已经是三者里最容易满足的。",
    "2. 两条出路：**(a)** 把 P 水平改到中段更密（如 0 / 60 / 120 / 240，让每个水平都有非零漂移）；"
    "**(b)** 在论文里把 `tau_P` 降级为「仅粗解释」，主检验只报 `beta_P`。",
    "3. 未做：改 P 方案重跑、把这轮结果画成图、把 (a)/(b) 的选择写进方法章。",
    "",
]
R[sec:sec] = block
RD.write_text("\n".join(R), encoding="utf-8", newline="\n")
print("README lines", len(R))
