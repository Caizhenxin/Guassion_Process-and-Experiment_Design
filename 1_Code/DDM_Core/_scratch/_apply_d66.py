"""把决策 D66 落进三份文档（Stage 8 的输入契约：只吃 v4.1 逐被试 txt）。

D66 的事实（全部可复现）：

1. ❗ **喂错格式会崩**：`python stage8_run.py --data 2_Data/Real_Data/EXP_data_combined.csv
   --plan-only` 在 D66 之前抛**未捕获的** `KeyError: 'matchKey'`
   （`read_formal_data.py:180` → `stage8_run.py:132` 的 `RF.validate` 在
   `RF.load_file` 的 try 之外），exit 1、裸 traceback。
2. **历史数据形态与契约不符**：`2_Data/Real_Data/EXP_data_combined.csv` 是
   32 列**逗号**汇总；`HEADER25` 要求的 25 列里**缺 9 列**：`block`、
   `premature_press`、`timeout`、`responded_by_deadline`、
   `stimulus_onset_actual`、`stimulus_offset_actual`、`mask_onset_actual`、
   `stimulus_dur_actual`、`stimulus_frames`。且 `2_Data/Real_Data/` 下
   **0 个 `*.txt`**。
3. ⇒ 这不是"解析/转换"问题，是**信息不存在**（反应时窗内的按键时序、抢按、
   掩蔽时序都没被记下来）。任何"补列"都是**猜测**，会伪装成数据。
4. **修法 = 入口契约**：非 `*.txt` 输入点名拒绝（逐条列出缺的 9 列）、目录里
   没有 `*.txt` 点名拒绝、`load_file` 返回空观测时用 `rep["error"]` 说明、
   `RF.validate` 包进 try、一个可用被试都没有时打印**被拒明细**并 exit 2。
5. **牙齿**：`1_Code/DDM_Core/_scratch/check_stage8_run.py` 新增 **E1–E5**
   （理由含 v4.1/HEADER25 且点名 9 列；CSV ⇒ exit 2；无 txt 目录 ⇒ exit 2；
   静态三条守卫；正路未被误伤）⇒ 自测 **18/18 → 23/23**。

用法
----
    python -X utf8 -u 1_Code/DDM_Core/_scratch/_apply_d66.py            # 干跑
    python -X utf8 -u 1_Code/DDM_Core/_scratch/_apply_d66.py --apply    # 真写
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RDM = REPO / "1_Code" / "DDM_Core" / "README.md"

APPLY = "--apply" in sys.argv


def load(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def save(p: Path, lines: list[str]) -> None:
    if not APPLY:
        print(f"  [干跑] 将写 {p.relative_to(REPO)}（{len(lines)} 行）")
        return
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    p.write_text(text, encoding="utf-8", newline="\n")
    print(f"  [写入] {p.relative_to(REPO)}（{len(lines)} 行）")


def n_sep(line: str) -> int:
    return line.count("|")


def idx_of(lines: list[str], needle: str, what: str) -> int:
    for i, ln in enumerate(lines):
        if needle in ln:
            return i
    raise SystemExit(f"❗ 找不到锚点：{what}（needle={needle!r}）")


def ins_after(lines: list[str], anchor_i: int, new: list[str], what: str) -> None:
    if not isinstance(new, list):
        raise SystemExit(f"❗ {what}：new 必须是 list，收到 {type(new).__name__}")
    base = n_sep(lines[anchor_i])
    for ln in new:
        if n_sep(ln) != base:
            raise SystemExit(
                f"❗ {what}：新行竖线数 {n_sep(ln)} != 锚点 {base} -> {ln[:80]}")
    lines[anchor_i + 1:anchor_i + 1] = new


def has(lines: list[str], needle: str) -> bool:
    """幂等守卫：目标文本是否已在（重跑时跳过，避免重复插入）。"""
    return any(needle in ln for ln in lines)


def replace_once(lines: list[str], old: str, new: str, what: str) -> None:
    hit = 0
    for i, ln in enumerate(lines):
        if old in ln:
            lines[i] = ln.replace(old, new)
            hit += 1
    if hit != 1:
        raise SystemExit(f"❗ {what}：命中 {hit} 次（应为 1）")


# ---------------------------------------------------------------- 主计划
D66_DECISION = (
    "| **D66** | 2026-10-17 | ✅ **把 Stage 8 的输入契约立死：只吃 v4.1 逐被试 txt；"
    "历史汇总 CSV 不可转换（信息不存在，不是解析问题）**。① 缺陷："
    "`stage8_run.py --data <CSV>` 抛**未捕获的** `KeyError: 'matchKey'`"
    "（`RF.validate` 在 `RF.load_file` 的 try 之外）、exit 1 裸 traceback。"
    "② 事实：`2_Data/Real_Data/EXP_data_combined.csv` 是 32 列逗号汇总，"
    "`HEADER25` 缺 **9 列**（`block`、`premature_press`、`timeout`、"
    "`responded_by_deadline`、三个 `*_actual`、`stimulus_dur_actual`、"
    "`stimulus_frames`），且 `2_Data/Real_Data/` 下 **0 个 `*.txt`** ⇒ "
    "历史 87 人件**不能**喂进 Stage 8（补列 = 猜测）。③ 修法：入口点名拒绝"
    "（逐条列出缺列）、空目录点名、`load_file` 空观测用 `rep[\"error\"]` 说明、"
    "`validate` 包 try、无可用被试时打印明细并 **exit 2**。④ 牙齿 E1–E5 ⇒ "
    "`check_stage8_run.py` **18/18 → 23/23**。⑤ 后果：Stage 8 的真实数据输入"
    "**只能**来自 Stage 7 采集产出的逐被试 txt；不写 CSV 适配层。"
    " | `1_Code/DDM_Core/stage8_run.py`（`_no_inputs_message` / `_non_txt_reason`）、"
    "`1_Code/DDM_Core/_scratch/check_stage8_run.py`（E 组）；落纸见 "
    "`1_Code/DDM_Core/README.md` §8.41 与 `Stage8_建模与验证方案.md` §8/§9/§10/§11/§12 "
    " | 判据、推荐点、交付件依据件、`n_fim` **一个都没动**（只加输入契约与入口守卫）；"
    "用户侧 Stage 1/6/7 仍在等 |"
)

D66_PROGRESS = (
    "| 2026-10-17 | **8**（输入契约 → D66） | **把「Stage 8 吃什么样的数据」"
    "从散落在 docstring 里的期望变成入口守卫**。D65 收尾时发现：把历史汇总 CSV "
    "当 `--data` 喂进 `stage8_run.py`，运行器会一路走到 `RF.to_trials(rec)` 才抛"
    "**未捕获的 `KeyError: 'matchKey'`** —— 症状是裸 traceback，根因是那个文件"
    "**缺 `HEADER25` 的 9 列**（`block`/`premature_press`/`timeout`/"
    "`responded_by_deadline`/三个 `*_actual`/`stimulus_dur_actual`/"
    "`stimulus_frames`），而 `2_Data/Real_Data/` 下一个 `*.txt` 都没有。"
    "⇒ 本轮在 `collect()` 入口把契约立死：非 txt 输入点名拒绝并**逐条列出缺列**、"
    "空目录点名、`load_file` 空观测用 `rep[\"error\"]` 说明、`validate` 包 try、"
    "无可用被试时打印被拒明细并 **exit 2**（原为未捕获异常）。"
    "**牙齿 E1–E5**（理由含 v4.1/HEADER25 且点名 9 列 / CSV ⇒ exit 2 / 无 txt 目录 "
    "⇒ exit 2 / 静态三条守卫 / 正路未被误伤）⇒ `check_stage8_run.py` "
    "**18/18 → 23/23**。 | 见 D66 决策行；证据 = 两次拒绝实跑 + "
    "`1_Code/DDM_Core/README.md` §8.41 | 下一步：等 Stage 7 产出的逐被试 txt；"
    "不再考虑 CSV 适配（补列等于造数据） |"
)
D66_CHANGELOG = (
    "| 2026-10-17 | **新增 D66：Stage 8 的输入契约（只吃 v4.1 逐被试 txt；"
    "历史汇总 CSV 缺 9 列、不可转换）+ 入口守卫 + E1–E5 五颗牙齿**。"
    "`stage8_run.py` 新增 `_no_inputs_message()` 与 `_non_txt_reason()`，"
    "`collect()` 改为先分辨输入（目录 / txt / 其它）、再把 `RF.validate` 包进 "
    "try、无可用被试时打印被拒明细并 exit 2；`check_stage8_run.py` 新增 E 组五颗"
    "（18/18 → 23/23）；`Stage8_建模与验证方案.md` §8 自测数、§9 工具链加一行、"
    "§10 加第 5 条回填要求、§11 加第 14 条限制、§12 加 v1.3；"
    "`1_Code/DDM_Core/README.md` 新增 §8.41 + §9 第 50 项 |"
)

D66_EVIDENCE_MP = (
    "| `1_Code/DDM_Core/stage8_run.py`（输入契约，D66）+ "
    "`_scratch/check_stage8_run.py`（E 组） | "
    "`collect()` 入口分辨输入：目录只取 `*.txt`（没有则点名拒绝）、文件非 `*.txt` 用 "
    "`_non_txt_reason()` 拒绝并**逐条列出 `HEADER25` 缺列**、空观测用 "
    "`rep[\"error\"]` 说明、`RF.validate` 包进 try、无可用被试时打印明细并 "
    "**exit 2**。实跑：喂 `2_Data/Real_Data/EXP_data_combined.csv` ⇒ exit 2 且点名 "
    "**9 列**缺列（改前是未捕获 `KeyError: matchKey`、exit 1）；喂 "
    "`2_Data/Real_Data/HDDM_Traces` ⇒ exit 2、点名「没有 *.txt」；"
    "`--synthetic 2 --plan-only` ⇒ exit 0、2 人收下。牙齿 E1–E5 ⇒ 自测 "
    "**18/18 → 23/23** |"
)

D66_EVIDENCE_S8 = (
    "| `1_Code/DDM_Core/stage8_run.py`（输入契约，D66） | "
    "入口分辨输入：目录只取 `*.txt`、非 txt 用 `_non_txt_reason()` 拒绝并逐条列出 "
    "`HEADER25` 缺列、空观测用 `rep[\"error\"]` 说明、`RF.validate` 包进 try、"
    "无可用被试时打印明细并 **exit 2** | 喂 `EXP_data_combined.csv` ⇒ exit 2 并点名 "
    "**9 列**缺列（改前未捕获 `KeyError: matchKey`、exit 1）；喂无 txt 目录 ⇒ "
    "exit 2；`--synthetic 2 --plan-only` ⇒ exit 0 |"
)

D66_EVIDENCE_S8_NOTE = (
    "| `1_Code/DDM_Core/_scratch/check_stage8_run.py`（E 组，D66） | "
    "输入契约的回归守卫：E1 理由含 `v4.1`/`HEADER25` 且点名 9 个缺列；E2 CSV ⇒ "
    "`SystemExit(2)`；E3 无 txt 目录 ⇒ `SystemExit(2)`；E4 静态三条守卫；"
    "E5 正路未被误伤 | 自测 **23/23、未通过 0 项、exit 0** |"
)


def do_master_plan() -> None:
    lines = load(MP)
    if has(lines, "| **D66** | 2026-10-17 |"):
        print("  [跳过] 主计划 §5：D66 决策行已在")
    else:
        i = idx_of(lines, "| **D65** | 2026-10-17 |", "主计划 §5 D65 决策行")
        ins_after(lines, i, [D66_DECISION], "主计划 §5 D66 决策行")
    if has(lines, "**8**（输入契约 → D66）"):
        print("  [跳过] 主计划 §6：D66 进度行已在")
    else:
        i = idx_of(lines, "| 2026-10-17 | **8**（全量运行器合成干跑 → D65） |",
                   "主计划 §6 进度行（D65）")
        ins_after(lines, i, [D66_PROGRESS], "主计划 §6 D66 进度行")
    if has(lines, "**新增 D66："):
        print("  [跳过] 主计划 §7：D66 变更日志已在")
    else:
        i = idx_of(lines, "**新增 D65：", "主计划 §7 变更日志 D65 行")
        ins_after(lines, i, [D66_CHANGELOG], "主计划 §7 D66 变更日志")
    if has(lines, "（输入契约，D66）"):
        print("  [跳过] 主计划 §8：D66 证据行已在")
    else:
        i = idx_of(lines, "stage8_synth3_dryrun/stage8_report.md",
                   "主计划 §8 D65 证据行")
        ins_after(lines, i, [D66_EVIDENCE_MP], "主计划 §8 D66 证据行")
    save(MP, lines)


def do_stage8() -> None:
    lines = load(S8)
    if has(lines, "18/18 → 23/23"):
        print("  [跳过] Stage8 §8 自测数：已改")
    else:
        replace_once(lines, "自测 **18/18**。",
                     "自测 **18/18 → 23/23**（D66 加 E1–E5 五颗输入契约牙齿）。",
                     "Stage8 §8 自测数")
    if has(lines, "（输入契约，D66）"):
        print("  [跳过] Stage8 §9：D66 两行已在")
    else:
        i = idx_of(lines, "`1_Code/DDM_Core/stage8_run.py`（干跑 II）",
                   "Stage8 §9 干跑 II 行")
        ins_after(lines, i, [D66_EVIDENCE_S8, D66_EVIDENCE_S8_NOTE],
                  "Stage8 §9 D66 两行")
    if has(lines, "5. ❗ **输入形态只有一种**"):
        print("  [跳过] Stage8 §10：第 5 条已在")
    else:
        i = idx_of(lines, "4. PPC 的**分单元**统计量", "Stage8 §10 第 4 条")
        ins_after(lines, i, [
            "5. ❗ **输入形态只有一种**：`stage8_run.py` 只吃 `Exp_Design_Formal.m` 写出的"
            " **v4.1 逐被试 txt**（制表符、`HEADER25` 25 列，见 D66）。历史汇总 CSV"
            "（`2_Data/Real_Data/EXP_data_combined.csv`）**缺 9 个必填列**、"
            "`2_Data/Real_Data/` 下也没有任何 `*.txt` ⇒ **不得**把它当 Stage 8 的输入，"
            "也**不写** CSV 适配层（补列等于造数据）。"
        ], "Stage8 §10 第 5 条")
    if has(lines, "14. ❗ **输入契约是硬约束**"):
        print("  [跳过] Stage8 §11：第 14 条已在")
    else:
        i = idx_of(lines, "13. ❗ **报数值健康时必须同时报 `n_degenerate_nonfinite`**",
                   "Stage8 §11 第 13 条")
        ins_after(lines, i, [
            "14. ❗ **输入契约是硬约束**（D66）：Stage 8 只吃 v4.1 逐被试 txt；"
            "历史汇总 CSV 缺 9 列（含 `block`/`premature_press`/`timeout`/三个 "
            "`*_actual`）⇒ 缺的就是**没记下来的信息**，不是解析缺陷。任何人拿历史数据"
            "跑 Stage 8 的结果都必须先过这条闸。"
        ], "Stage8 §11 第 14 条")
    if has(lines, "| v1.3 | 2026-10-17 |"):
        print("  [跳过] Stage8 §12：v1.3 已在")
    else:
        i = idx_of(lines, "| v1.2 | 2026-10-17 |", "Stage8 §12 v1.2 行")
        ins_after(lines, i, [
            "| v1.3 | 2026-10-17 | **§8 自测数 18/18 → 23/23、§9 加两行输入契约证据、"
            "§10 加第 5 条回填要求、§11 加第 14 条限制（D66：只吃 v4.1 逐被试 txt，"
            "历史 CSV 缺 9 列不可转换）** |"
        ], "Stage8 §12 v1.3 行")
    save(S8, lines)


# ---------------------------------------------------------------- DDM README
RM_841 = [
    "## 8.41 Stage 8 的输入契约：只吃 v4.1 逐被试 txt（2026-10-17，D66）",
    "",
    "**动机**：D65 收尾时把 `2_Data/Real_Data/EXP_data_combined.csv` 当 `--data` "
    "喂进 `1_Code/DDM_Core/stage8_run.py`，运行器一路走到 `read_formal_data.py:180` "
    "的 `RF.to_trials(rec)` 才抛**未捕获的** `KeyError: 'matchKey'`"
    "（`RF.validate` 在 `RF.load_file` 的 try 之外）、exit 1、裸 traceback。"
    "症状像是「读坏了」，根因是那个文件**根本没有那些列**。",
    "",
    "**为什么不能转换**：`2_Data/Real_Data/EXP_data_combined.csv` 是 **32 列逗号"
    "汇总**，而 `HEADER25` 要 25 列（制表符）。缺的 **9 列**是：`block`、"
    "`premature_press`、`timeout`、`responded_by_deadline`、"
    "`stimulus_onset_actual`、`stimulus_offset_actual`、`mask_onset_actual`、"
    "`stimulus_dur_actual`、`stimulus_frames` —— 全是**刺激呈现时序对反应时窗"
    "的记录**。它们不是「换个写法」，而是**当初没采**。补列只能靠猜（例如用 "
    "`RT` 倒推「有没有抢按」），而猜出来的列会**伪装成数据**进入模型。"
    "另外 `2_Data/Real_Data/` 下 **0 个 `*.txt`**。",
    "",
    "**改法（入口契约）**：`collect()` 先分辨输入 —— 目录只取 `*.txt`（没有就"
    "点名拒绝）、文件非 `*.txt` 用 `_non_txt_reason()` 拒绝并**逐条列出缺列**、"
    "`load_file` 返回空观测用 `rep[\"error\"]` 说明、`RF.validate` 包进 try、"
    "一个可用被试都没有时打印**被拒明细**并 **exit 2**。",
    "",
    "**牙齿**：`1_Code/DDM_Core/_scratch/check_stage8_run.py` 新增 **E1–E5** "
    "⇒ 自测 **18/18 → 23/23**。",
    "",
    "**后果**：Stage 8 的真实数据输入**只能**来自 Stage 7 采集产出的逐被试 txt；"
    "**不写** CSV 适配层；历史 87 人件与 Stage 8 无关（它服务的是 Stage 2–5 的"
    "恢复/比较，那些不要求 `block`/`premature_press` 等列）。",
    "",
]

RM_ITEM = (
    "| 50 | ✅ **Stage 8 的输入契约立死：只吃 v4.1 逐被试 txt；历史汇总 CSV 缺 9 列、"
    "不可转换（D66，§8.41）** | 改前喂 CSV 抛未捕获 `KeyError: 'matchKey'`、exit 1；"
    "改后 exit 2 并逐条点名 9 列缺列；`check_stage8_run.py` **23/23** |"
)


def do_ddm_readme() -> None:
    lines = load(RDM)
    if has(lines, "## 8.41 Stage 8 的输入契约"):
        print("  [跳过] DDM README §8.41：已在")
    else:
        i = idx_of(lines, "## 9. 尚未做", "DDM README §9 标题")
        lines[i:i] = RM_841
    if has(lines, "| 50 | ✅ **Stage 8 的输入契约立死"):
        print("  [跳过] DDM README §9：第 50 项已在")
    else:
        i = idx_of(lines, "| 49 | ✅ **Stage 8 全量运行器在合成数据上端到端跑通",
                   "DDM README §9 第 49 项")
        ins_after(lines, i, [RM_ITEM], "DDM README §9 第 50 项")
    save(RDM, lines)


def main() -> int:
    print("=" * 88)
    print(f"D66 落纸（{'应用' if APPLY else '干跑'}）")
    print("=" * 88)
    do_master_plan()
    do_stage8()
    do_ddm_readme()
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
