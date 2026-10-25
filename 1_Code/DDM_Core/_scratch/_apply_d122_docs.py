"""D122 落纸：主计划（决策/进度/变更日志/证据）+ DDM_Core/README §9 第 103 项 + SOP 口径更新。

幂等：按行前缀定位，已存在则跳过；断言唯一命中，失败即报错退出。
"""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
CORE = ROOT / "1_Code" / "DDM_Core" / "README.md"
SOP = ROOT / "5_Reference" / "08_工作流" / "数据快速筛查SOP.md"

D122 = (
    "| **D122** | 2026-10-25 | "
    "**定编的两条腿补齐：N_精度（模拟 + 解析对账）+ N_区分（模型比较需要几个人），并把「参数恢复能不能定 N」这个方法论问题钉死**。"
    "新建 `1_Code/Experiment/power_recovery.py`（461 行，`--mode {precision,discriminate,all}`）："
    "① N_精度——每组模拟 100 人（4 组 400 人 / 230,400 试次，`dt=1e-4`）算三个端点量的被试间 SD，再用 `n=(SD/目标 SE)²` 定编；"
    "② N_区分——逐人 8 参数 `fit_mle`(M-T3) 与 `fit_mle_step`(M-T1) 的嵌套 LRT，ρ=1 与 ρ=0.6 各 6 人，合成 N 人总 LRT 对 χ²(2N)。"
    "读数：SD(ΔRT 中位) **37.2 ms ⇒ n=14**、SD(Δacc) 0.058 ⇒ 4、SD(分位斜率) 102.7 ⇒ 12；"
    "逐组 n_need（ΔRT / Δacc / 斜率）= P=0 15/5/14、P=8 16/5/12、P=32 13/3/12、P=120 13/4/10 ⇒ 每组取三指标最大 ⇒ **合计 57 人**，"
    "与 `intake.py` 从真实数据给的 **55 人（11–16/组）相差 2 人**——两条完全独立的路径互证，定编结论可复现。"
    "**解析 `SD/√N` 与自助 SE(N) 最大偏差 3.1%** ⇒ 筛查工具用的解析口径站得住（不必为定编再跑自助）。"
    "N_区分：null 档 **0/6** 超 3.84（均值 1.9）、alt 档 **3/6**（均值 4.02±3.08），合成后 N=3 77.9%、**N=5 92.2%**、N=8 98.7% ⇒ **80% 检验力只需 5 人（总计，非每组）**，"
    "即 **N_区分 ≪ N_精度**：卡人数的是端点量精度，不是模型比较。"
    "方法论结论（写进方法章）：恢复实验回答「参数能不能估」、功效分析回答「要几个人」，两者之间没有直达的桥；"
    "`目标 SE` 的三个阈值（10 ms / 0.03 / 30 ms）目前是人为判断，属已知空白。"
    "两条硬限制：一类错误只由 6 个 null 估（0/6 ⇒ 95% 区间上限约 39%）；这是**逐人固定效应** LRT，不等于层级 ELPD 比较可靠"
    "（Stage 8 里 M-T1 超参数 Hessian 非正定才是模型比较的真瓶颈，见 D121）。"
    "**顺带清掉两个待决定事项**："
    "① 判据同源化——`read_formal_data.py` 拆出 `tech_line_issues` 与 `validate_split`，「单行掉帧」从「整份拒收被试」降为软项，`intake.py` 与 `stage8_run.py` 共用这一份拆分"
    "（`stage8_run.py --plan-only` 由 **15 人 / 被拒 2** 变 **17 人 / 被拒 0**，两个入口不再各说一个数）；"
    "② `t0` 上界查证——上界 = 该被试 min(RT) − 0.02，minRT 小的被试界内位置 0.83–0.95 甚至顶死（2-5 恰为 0.135）；"
    "丢掉 `RT < 200 ms` 的 1–6 个试次（0.2–1.1%）后 t0 抬到 0.142–0.185，**同一批试次上的 ℓ 增益 2-5 达 +46.7**（人均 +0.084）"
    "⇒ 上界被「快反应当污染项」压死，抬 0.02–0.06 s 正好对上 D121 的 PPC RT 欠估 60–90 ms；三条处置 A（似然加污染项）/ B（拟合前把 `RT<200 ms` 记为污染，推荐）/ C（只写限制）待拍板。"
    " | 用户 2026-10-25「可以的，麻烦你先补上这条链，再去做之前的那两个待决」＋此前一问「用参数恢复判断需要多少被试，这个有依据吗、有文献吗」"
    "；标准做法分三层（可识别性 → 精度/功效 → 设计优化），本项目此前只做了第 1、3 层，第 2 层缺「模型比较要几个人」 | "
    "`1_Code/Experiment/power_recovery.py`（**新建**）+ `1_Code/Experiment/read_formal_data.py`（`tech_line_issues`/`validate_split`）+ "
    "`1_Code/Experiment/intake.py`（`layer_consistency` 用拆分）+ `1_Code/DDM_Core/stage8_run.py`（软项只警告）+ "
    "`3_Figures/_power/fig12_power_precision.png` + `fig13_power_discriminate.png` + `2_Data/Generate_Data/_power/`（6 个文件）+ "
    "`5_Reference/03_论文写作/定编依据_N精度与N区分_20261025.md`（**新建**，§5.1 检验力 + §10 t0 查证） |"
)

PROG = (
    "| 2026-10-25 | **19（定编两条腿 → D122）** | "
    "**补上了「要几个人」的另一半**：模拟定编 57 人 vs 真实数据 55 人（差 2 人，两条独立路径互证）；解析 `SD/√N` 与自助 SE 差 ≤3.1%；"
    "N_区分 只要 5 人 ⇒ 卡人的是精度不是模型比较；判据同源化后 stage8 可用被试 15 → 17 人；t0 上界被快反应压死的证据到手（ℓ 增益 +46.7）。 "
    "| `5_Reference/03_论文写作/定编依据_N精度与N区分_20261025.md`；`3_Figures/_power/fig12、fig13` | "
    "`power_recovery.py`；`2_Data/Generate_Data/_power/*.csv`；`read_formal_data.validate_split` |"
)

CHANGE = (
    "| 2026-10-25 | **新增 D122（定编两条腿：N_精度 + N_区分）**：`power_recovery.py`（`--mode precision|discriminate`）"
    "——模拟 400 人算三个端点量的被试间 SD 定编（57 人，与真实数据 55 人互证）、逐人嵌套 LRT 合成检验力曲线（N_区分 80% 只要 5 人）；"
    "同时把「单行掉帧」的拒收口径统一到 `validate_split`（stage8 15 → 17 人），并查清 `t0` 上界被 `RT<200 ms` 压死（2-5 的 ℓ 增益 +46.7） |"
)

EVID = (
    "| `1_Code/Experiment/power_recovery.py` + `3_Figures/_power/fig12_power_precision.png` + `fig13_power_discriminate.png` + "
    "`2_Data/Generate_Data/_power/*.csv` | D122 证据：① 三个端点量的模拟 SD 与逐组定编（ΔRT 37.2 ms/14 人、Δacc 0.058/4 人、斜率 102.7/12 人；逐组最大 16 人 ⇒ 57 人）；"
    "② 解析 `SD/√N` 与自助 SE 的最大偏差 3.1%（ΔRT N=50 +1.6%、Δacc N=10 −2.4%、斜率 N=40 −3.1%）；"
    "③ 单人 LRT 两个真值下的 6+6 个点（null 0/6 超临界、alt 3/6）与合成检验力（N=5 → 92.2%）；"
    "④ `validate_split` 前后 stage8 可用被试 15 → 17 人；⑤ t0 上界查证的三张对照表（有界位置 / 截尾后重拟合 / 同批试次 ℓ 增益） |"
)

README_ITEM = (
    "| 103 | ✅ **定编的两条腿：N_精度 + N_区分（D122）** | `1_Code/Experiment/power_recovery.py`："
    "`--mode precision` 模拟 400 人（4 组 × 100 人 × 576 试次）算 ΔRT 中位 / Δacc / 分位斜率的被试间 SD，再按 `n=(SD/目标 SE)²` 定编"
    "（全体 14/4/12，逐组最大 16 人 ⇒ **57 人**，与 `intake.py` 用真实数据的 55 人差 2 人）；`--mode discriminate` 逐人拟 M-T3 与 M-T1 "
    "求嵌套 LRT，合成检验力 80% 只需 **5 人** ⇒ N_区分 ≪ N_精度。顺带把「单行掉帧」的拒收口径统一成 `read_formal_data.validate_split`"
    "（stage8 可用被试 15 → 17 人），并查清 `t0` 上界被 `RT<200 ms` 的污染试次压死（2-5 的 ℓ 增益 +46.7，正好对应 PPC 的 RT 欠估 60–90 ms） |"
)

SOP_OLD = (
    "**已知口径不一致（待决策，2026-10-25）**：`read_formal_data` 的读取器对\"单行 `stimulus_dur_actual`\n"
    "超 T + 1 帧\"是**整份拒收被试**；而本 SOP 的口径（D120）把同一现象记为**信息项、被试照收**。\n"
    "20 人批上两者的差是 17 人 vs 15 人。在改成\"丢坏试次、留被试\"之前，**报告人数时必须写清是哪一层的人数**。"
)

SOP_NEW = (
    "**口径已统一（D122，2026-10-25）**：`read_formal_data.py` 拆出 `tech_line_issues` 与 `validate_split`，\n"
    "\"单行 `stimulus_dur_actual` 超 T + 1 帧\"归**软项**——`intake.py` 记信息项、`stage8_run.py` 打 ⚠ 但继续收人，只有\n"
    "缺列 / 整段坏这类**硬项**才拒收被试。20 人批上的效果：stage8 可用被试 **15 → 17 人**（`2-4`、`4-4` 回队）。\n"
    "两个入口现在共用一个判据，**报告人数不必再区分是哪一层的人数**。\n"
    "\n"
    "## 十、下一轮要拍板的一件事：`t0` 上界\n"
    "\n"
    "`t0` 的拟合上界 = 该被试的 `min(RT) − 0.02`。数据里若有 1–6 个 `RT < 200 ms` 的抢跑试次（占 0.2–1.1%），\n"
    "上界就被压到真实非决策时间以下：minRT 小的被试**界内位置 0.83–0.95、甚至顶死在上界**（`2-5` 恰为 0.135 s），\n"
    "而 Stage 8 的 PPC 正是「RT 中位系统性欠估 60–90 ms」——两者对得上。\n"
    "把 `RT < 200 ms` 的试次当污染项丢掉后重拟合，`t0` 抬到 0.142–0.185 s，**同一批试次上的似然增益 2-5 达 +46.7**。\n"
    "三条处置：**A** 似然里加 `λ·Uniform(0, W)` 污染项（最正确，要改 `likelihood.py` 并重跑 Stage 8）；\n"
    "**B** 拟合前把 `RT < 200 ms` 记为污染试次（便宜，推荐先做）；**C** 只写进限制节。\n"
    "详见 `5_Reference/03_论文写作/定编依据_N精度与N区分_20261025.md` §10。"
)


def insert_after(lines: list[str], anchor_prefix: str, new_row: str, label: str) -> list[str]:
    if any(ln.startswith(new_row[:60]) for ln in lines):
        print(f"[skip] {label} 已存在")
        return lines
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    assert len(hits) == 1, f"{label}: 锚点命中 {len(hits)} 次"
    lines.insert(hits[0] + 1, new_row)
    print(f"[ok] {label} 插在第 {hits[0] + 2} 行")
    return lines


def insert_before(lines: list[str], anchor_prefix: str, new_row: str, label: str) -> list[str]:
    if any(ln.startswith(new_row[:60]) for ln in lines):
        print(f"[skip] {label} 已存在")
        return lines
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    assert len(hits) == 1, f"{label}: 锚点命中 {len(hits)} 次"
    lines.insert(hits[0], new_row)
    print(f"[ok] {label} 插在第 {hits[0] + 1} 行")
    return lines


def rewrite(path: Path, fn) -> None:
    text = io.open(path, encoding="utf-8").read()
    lines = text.split("\n")
    lines = fn(lines)
    out = "\n".join(lines)
    if not out.endswith("\n"):
        out += "\n"
    io.open(path, "w", encoding="utf-8", newline="\n").write(out)
    print(f"    -> {path.name}: {len(out.split(chr(10))) - 1} 行")


def plan_fn(lines):
    lines = insert_before(lines, "| **D121** | 2026-10-25 |", D122, "决策行 D122")
    lines = insert_after(lines, "| 2026-10-25 | **18（Stage 8 真实数据首轮 → D121）** |", PROG, "进度行")
    lines = insert_after(lines, "| 2026-10-25 | **新增 D121（Stage 8 真实数据首轮）**", CHANGE, "变更日志行")
    # 证据行：追加在 D121 证据行后（表尾）
    lines = insert_after(lines, "| `5_Reference/03_论文写作/Stage8_真实数据首轮_20261025.md`", EVID, "证据行")
    return lines


def core_fn(lines):
    return insert_after(lines, "| 102 | ✅ **Stage 8 真实数据首轮（D121）**", README_ITEM, "README §9 第 103 项")


def sop_fn(lines):
    text = "\n".join(lines)
    if "口径已统一（D122" in text:
        print("[skip] SOP 已更新")
        return lines
    assert text.count(SOP_OLD) == 1, "SOP 锚点不唯一"
    return text.replace(SOP_OLD, SOP_NEW).split("\n")


if __name__ == "__main__":
    rewrite(PLAN, plan_fn)
    rewrite(CORE, core_fn)
    rewrite(SOP, sop_fn)
