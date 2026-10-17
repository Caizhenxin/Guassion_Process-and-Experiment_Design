"""把决策 **D48**（时序口径冲突定案）写进 `5_Reference/08_工作流/工作流_主计划.md` 四处。

为什么用脚本而不是 `edit`：决策表 / 进度表 / 变更日志的行都是数千字符的单行，
`edit` 追加必须一字不差匹配**整行行尾**（含可能的尾随空格）；本脚本按**行首前缀**定位再插入，
不依赖行尾形状。并且每一处都**先量出锚点行自己的分隔符个数**，再断言新行与之相等 ——
这正是前面两次（D46 决策行 5 个分隔符、进度行缺"下一步"列、变更日志未转义 `|`）栽的地方。

跑法：`python 1_Code/DDM_Core/_scratch/_apply_d48.py [--apply]`
"""

from __future__ import annotations

import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
PLAN = os.path.join(_ROOT, "5_Reference", "08_工作流", "工作流_主计划.md")

# ---------------------------------------------------------------- 新行内容
D48_DECISION = (
    "| **D48** | 2026-10-14 | ✅ **时序口径冲突定案：`1_Code/AutoRA_SPE/spe_design_model.py` 编码的是 "
    "**v2** 口径（`deadline = T + W`），与当前程序 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` "
    "v4.1（`deadline = onset + W`，且**自刺激 onset 即采集按键**）相差恰好 `T + 200 ms`；"
    "该目录的历史函数**不得直接用于 v4.1 设计点**。同一对数字在两套口径下相差 `T`："
    "D4 网格（T = 33.33–249.98 ms、W = 799.98–1799.9 ms）上 deadline 相对误差 **1.85%–31.25%**，"
    "**最大误差落在最短 deadline（T=249.98, W=799.98）**，且固定 W 时随 T 严格单调增 "
    "⇒ 纯口径错误会伪装成 **T 的主效应**；`M_ms` 与 `boundary_a(M_ms)` 同样多算 `T`。"
    "❗ 第二处：`apply_window_gate` **不是删行，而是** `rt = np.maximum(rt, T + 0.2)`，"
    "把任何 `rt < T + 200 ms` 的 v4.1 反应**静默改写成 `T + 200 ms`**，刺激期内按键"
    "（D5 存在的全部理由：实际呈现时长 = min(T, RT)）**不再可被识别**，并人为复现 legacy 的"
    "「min RT ≈ T + 203 ms」伪迹 ⇒ **v4.1 数据上不得施加该门控**。第三处：legacy 的 D2 下界"
    "（`min RT − T` = 202.8–203.1 ms、intercept 203.0）只是 v2 在 `T + 200` 才开窗口的产物，"
    "**在 v4.1 上不存在**，不得当作验收判据。✅ **哪一边对**：`1_Code/DDM_Core/likelihood.py` 的 "
    "`per_trial_loglik` 用 `t = rt − t0`、`t_max = W − t0`，而 `rt` 自刺激 onset 起算 "
    "⇒ **DDM_Core 与 v4.1 程序、`1_Code/Experiment/read_formal_data.py` 一致，`AutoRA_SPE` 是唯一异类**。"
    "**处置**：**不改动**历史文件与历史结论（它们的数值是旧数据诊断的证据，动了证据就失效），"
    "改为新增显式口径桥 `1_Code/AutoRA_SPE/spe_timing_convention.py` + 自测 "
    "`1_Code/AutoRA_SPE/check_timing_convention.py`（**25/25**）"
    " | ① v4.1 程序头部逐字：L18 `deadline = stimulusFlipTime + W`（并自陈\"旧版误为 onset + T + W\"）、"
    "L14–17 自【刺激 onset】起全程轮询、L22 `W 必须 > T + 200ms` 与 `W − T − 200ms`、"
    "L600/L651 `responseTime = respAbs - stimulusFlipTime;`、L656/L984 `responseTime <= W`；"
    "② `spe_design_model.py` L112–119 `return float(T_ms) + float(W_ms)`、L122–124 `window_open_ms = T + MASK`、"
    "L127–129 `window_duration_ms = W − MASK`、L326–330 `rt[mask_ok] = np.maximum(rt[mask_ok], floor)`、"
    "L294 `boundary_a(T_ms + W_ms, ...)`；③ `1_Code/AutoRA_SPE/README.md` §3 的 8 组表"
    "（T / W / 最大 RT / T+W / W−200）—— 换算后**逐组保物理量**；"
    "④ `1_Code/AutoRA_SPE/check_timing_convention.py` **25/25、exit 0**；⑤ F 组源码锚点 6+3 处全部命中"
    " | ① Stage 9 复用 `AutoRA_SPE` 前**必须先过桥**；直接复用＝把口径错误写成 **T 主效应**；"
    "② 桥已把 L22 的启动自检做成 `assert_current_design`，不可实现的候选点在**进仿真前**就被拒；"
    "③ `1_Code/AutoRA_SPE/README.md` 新增 **§3.0 作用域警告**（v2/v4.1 五维对照 + 换算 + 两处失真），"
    "§7 文件清单补两行；④ D2 闸门（Stage 1/6/7 曾用作验收口径之一）在 v4.1 上**作废**；"
    "⑤ 待办：写 `Stage9_设计空间优化与论文整合方案.md` 并把桥接进 `spe_runner.py` 的参数构造"
    " |"
)

D48_PROGRESS = (
    "| 2026-10-14 | **9**（时序口径桥 → D48） | **把 `AutoRA_SPE` 的口径与当前程序的冲突定案，"
    "并交付机器可检的桥与守卫**。① 逐字核对 v4.1 头部：L18 `deadline = stimulusFlipTime + W`、"
    "L14–17 自刺激 onset 起全程轮询（刺激期也采集按键）、L22 约束 `W > T + 200ms` 与掩蔽后可按键 "
    "`W − T − 200ms`；② 核对 `spe_design_model.py` 的时序函数族：`deadline_ms = T + W`、"
    "`window_open_ms = T + 200`、`window_duration_ms = W − 200`、`apply_window_gate` 的 "
    "`np.maximum(rt, floor)`；③ 用**历史 8 组**验证换算**保物理量**：v4.1 的 "
    "`current_postmask_pressable_ms(T, T + W_legacy)` 逐组等于 README 的 `W−200`，"
    "`current_deadline_ms` 逐组等于 README 的 `T+W`；④ 量化两处失真：deadline 相对误差 "
    "1.85%–31.25%（最大在最短 deadline、固定 W 时随 T 单调增）；门控在 T=249.98 时把 "
    "`RT ∈ {0.040, 0.120, 0.300, 0.449}` 全部抬到 **0.450 s = T+200 ms**，"
    "刺激期内按键从 2 个变 0 个；⑤ 交付桥与自测 | `1_Code/AutoRA_SPE/spe_timing_convention.py`（新建）、"
    "`1_Code/AutoRA_SPE/check_timing_convention.py`（新建，**25/25、exit 0**）、"
    "`1_Code/AutoRA_SPE/README.md` §3.0 + §7、`5_Reference/08_工作流/工作流_主计划.md`（D48） "
    "| 写 `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`：冻结 Objective 定义、"
    "**共同随机数 CRN**、预计算 `design × truth × rep` 充分统计量、以及"
    "**BO vs 随机 vs 网格 vs 人工补点**的四分消融；把桥接进 `spe_runner.py` 的参数构造 "
    "|"
)

D48_CHANGELOG = (
    "| 2026-10-14 | **新增 D48：时序口径冲突定案 —— `1_Code/AutoRA_SPE/spe_design_model.py` 是 **v2** 口径，"
    "与当前程序 v4.1 相差 `T + 200 ms`，该目录历史函数不得直接用于 v4.1 设计点**。"
    "① 同一对数字在两套口径下相差 `T`：D4 网格上 deadline 相对误差 **1.85%–31.25%**、"
    "最大在最短 deadline、固定 W 时随 T 严格单调 ⇒ 会伪装成 **T 主效应**；`M_ms`/`boundary_a` 同样多算 T。"
    "② ❗ `apply_window_gate` 是 `np.maximum(rt, T + 0.2)`：把 `rt < T + 200 ms` 的 v4.1 反应"
    "**静默改写**成 `T + 200 ms`（实测 T=249.98 下 4 个 RT 全被抬到 0.450 s），"
    "刺激期内按键不再可被识别，并人为复现「min RT ≈ T + 203 ms」伪迹 ⇒ v4.1 数据上不得施加该门控。"
    "③ legacy 的 D2 下界（`min RT − T` = 202.8–203.1 ms）只是 v2 在 `T+200` 才开窗口的产物，v4.1 上不存在。"
    "④ `1_Code/DDM_Core/likelihood.py`（`t_max = W − t0`）与 v4.1 程序、`read_formal_data.py` 一致，"
    "`AutoRA_SPE` 是唯一异类。⑤ 处置：**不改动**历史文件与历史结论，新增口径桥 "
    "`1_Code/AutoRA_SPE/spe_timing_convention.py` + `check_timing_convention.py`（**25/25**，含 6+3 处源码锚点），"
    "`1_Code/AutoRA_SPE/README.md` 加 **§3.0 作用域警告** |"
)

APPENDIX_ROWS = [
    "| `1_Code/AutoRA_SPE/spe_timing_convention.py`（新建）+ `1_Code/AutoRA_SPE/check_timing_convention.py`"
    "（新建，**25/25、exit 0**） | **D48 的一手证据（时序口径桥 v2 ⇄ v4.1）**。"
    "A 组：往返换算误差 **0**、掩蔽时长单一事实来源（与 `spe_design_model.MASK_MS` 同源）、"
    "v4.1 窗口开启时刻 = **0**、同一对数字两口径相差恰好 `T`。"
    "B 组（**保物理量**，用历史 8 组）：桥恢复 README 的 `W_legacy` 列 **8/8**；"
    "v4.1 的 `current_postmask_pressable_ms` 逐组等于 README 的 `W−200` **8/8**；"
    "`current_deadline_ms` 逐组等于 README 的 `T+W`；误用会让后掩蔽窗口少算 `T`（最大 group 6，500 ms）。"
    "C 组（D4 网格）：12 点全部满足程序 L22 的 `W > T+200`；误用相对误差 **1.85%–31.25%**，"
    "最大在 (T=249.98, W=799.98)，固定 W 时随 T 严格单调（3/3 列）；`M_ms` 799.98 → 1049.96。"
    "D 组（**门控损害可复现**）：T=249.98 时 legacy `apply_window_gate` 把 "
    "`{0.040, 0.120, 0.300, 0.449}` 全部抬到 **0.450 s**，`min(gated) == T + 0.2` 精确成立，"
    "`RT < T` 的试次 **2 → 0**；v4.1 恒等门控原样保留 **2/2**。"
    "E 组：守卫 6 项有牙齿（`W == T+200` 边界、`W < T+200`、`T ≤ 0`、负 RT 全部拒绝）。"
    "F 组：**源码锚点**（`Exp_Design_Formal.m` 6 处 + `spe_design_model.py` 3 处）全部命中，防引用漂移 |",
    "| `1_Code/AutoRA_SPE/README.md`（新增 §3.0；§7 文件清单补 2 行） | **D48 的作用域警告**：把该文件原来的"
    "「权威口径 `deadline = T + W`」**限定为只对 v2 成立**，并给出 v2/v4.1 的五维对照表（W 语义 / deadline / "
    "窗口开启 / 掩蔽后可按键时长 / 同一物理量）、换算 `W_current = T + W_legacy`、两处失真的可复现描述，"
    "以及「**历史结论一律保留、不修改**」的理由（改动会让旧数据诊断的证据失效） |",
]


def n_sep(line: str) -> int:
    """表格行的分隔符个数（`|` 减去被转义的 `\\|`）。"""
    return line.count("|") - line.count("\\|")


def find_prefix(lines, prefix: str):
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❗ 锚点 `{prefix[:40]}…` 命中 {len(hits)} 行（要求恰好 1 行）")
    return hits[0]


def main():
    apply_ = "--apply" in sys.argv
    with io.open(PLAN, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    if "\r\n" in text:
        raise SystemExit("❗ 文件含 CRLF；全线约定为裸 LF")
    lines = text.split("\n")
    n0 = len(lines)
    print(f"文件：{PLAN}\n原始行数：{n0}")

    # 幂等守卫：已经写过就拒绝，避免重复插入
    if any(ln.startswith("| **D48** |") for ln in lines):
        raise SystemExit("❗ 文件里已存在 D48 决策行；本脚本不幂等，拒绝重复执行")

    edits = []
    # --- ① 决策表：插在 D47 之后 ---
    i = find_prefix(lines, "| **D47** |")
    sep = n_sep(lines[i])
    if n_sep(D48_DECISION) != sep:
        raise SystemExit(
            f"❗ D48 决策行分隔符 {n_sep(D48_DECISION)} != D47 行的 {sep}（决策表列数不符）"
        )
    edits.append((i + 1, D48_DECISION, "决策表（D47 之后）"))

    # --- ② 进度表：插在"**8**（超参数 Hessian 解析化 → D47）"之后 ---
    j = find_prefix(lines, "| 2026-10-14 | **8**（超参数 Hessian 解析化 → D47）")
    if n_sep(D48_PROGRESS) != n_sep(lines[j]):
        raise SystemExit(
            f"❗ D48 进度行分隔符 {n_sep(D48_PROGRESS)} != 锚点行的 {n_sep(lines[j])}"
        )
    edits.append((j + 1, D48_PROGRESS, "进度表（D47 之后）"))

    # --- ③ 变更日志：插在 D47 之后 ---
    k = find_prefix(lines, "| 2026-10-14 | **新增 D47：")
    if n_sep(D48_CHANGELOG) != n_sep(lines[k]):
        raise SystemExit(
            f"❗ D48 变更日志行分隔符 {n_sep(D48_CHANGELOG)} != 锚点行的 {n_sep(lines[k])}"
        )
    edits.append((k + 1, D48_CHANGELOG, "变更日志（D47 之后）"))

    # --- ④ 附录：追加证据行（紧随最后一个表格行，**不得夹进空行**） ---
    ap = find_prefix(lines, "## 附：本文核对过的一手证据")
    last = ap
    for t in range(ap + 1, len(lines)):
        if lines[t].startswith("|"):
            last = t
    if n_sep(APPENDIX_ROWS[0]) != n_sep(lines[last]):
        raise SystemExit(
            f"❗ 附录行分隔符 {n_sep(APPENDIX_ROWS[0])} != 附录末行的 {n_sep(lines[last])}"
        )
    # ⚠️ 踩过的坑：本文件在表格末行之后**本来就有空行**（到 EOF）。若按"末行之后逐行插入"，
    #    第 1 行会落在这个空行之前、第 2 行落在之后 ⇒ 表格内部多出一个空行（断表）。
    #    处置：先把末行之后的所有空行摘掉，再连续插入，最后补回一个换行。
    tail_blank = []
    while last + 1 < len(lines) and lines[last + 1] == "":
        tail_blank.append(lines.pop(last + 1))
    for off, row in enumerate(APPENDIX_ROWS):
        edits.append((last + 1 + off, row, f"附录（第 {off + 1} 行）"))
    print(f"  附录末尾原有 {len(tail_blank)} 个空行，已摘除以保证新行连续")

    # --- ⑤ 顺手更正过期行数（v4 → v4.1，1313 → 1325） ---
    stale = "新程序 v4（1313 行）"
    hits = [t for t, ln in enumerate(lines) if stale in ln]
    if len(hits) == 1:
        t = hits[0]
        lines[t] = lines[t].replace(stale, "新程序 v4.1（1325 行）")
        print(f"  更正过期描述：第 {t + 1} 行 `{stale}` → `新程序 v4.1（1325 行）`")
    else:
        print(f"  ⚠ 未找到（或找到 {len(hits)} 处）过期描述 `{stale}`，跳过")

    # 从后往前插，避免行号漂移
    for pos, row, why in sorted(edits, key=lambda x: -x[0]):
        lines.insert(pos, row)
        print(f"  插入 {why}：新第 {pos + 1} 行")

    out = "\n".join(lines)
    if "\r\n" in out:
        raise SystemExit("❗ 结果含 CRLF")

    # 后置断言：断表空行（空行前后都是表格行）—— 与 check_table_integrity.py 同款判据
    breaks = [
        t + 1
        for t in range(1, len(lines) - 1)
        if lines[t] == "" and lines[t - 1].startswith("|") and lines[t + 1].startswith("|")
    ]
    if breaks:
        raise SystemExit(f"❗ 结果出现断表空行（行号 {breaks}）；拒绝写回")

    print(f"新行数：{len(lines)}（+{len(lines) - n0}）；断表空行 0")

    if not apply_:
        print("\n（dry-run；加 --apply 才写回）")
        return 0
    with io.open(PLAN, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("\n✅ 已写回")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
