# -*- coding: utf-8 -*-
"""D95 落纸：单场入库判定器 `intake.py`。

四处锚点各断言「命中恰 1 次」，改完打印行数变化。
"""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../Guassion-Process-Experiment-Design
WS = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RM = ROOT / "1_Code" / "DDM_Core" / "README.md"
S7 = ROOT / "5_Reference" / "08_工作流" / "Stage7_数据采集执行与质控方案.md"


def load(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def save(p: Path, lines: list[str]) -> None:
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def anchor_idx(lines: list[str], prefix: str, count: int = 1) -> int:
    hit = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(hit) == count, f"锚点 `{prefix[:60]}` 命中 {len(hit)} 次（期望 {count}）"
    return hit[0]


# --------------------------------------------------------------------------- #
# 1. 主计划：决策行 / 进度行 / 变更日志 / 一手证据
# --------------------------------------------------------------------------- #
D95_ROW = (
    "| **D95** | 2026-10-18 | ✅ **单场入库判定器 `intake.py`：把「这场能不能计入 N」收成一条命令**。"
    "① 触发：D93/D94 那场要手工跑三个工具（`check_stage1_acceptance.py` 技术层、`qc_group.py` 结构层、"
    "`read_formal_data.py` 一致层）再心算合并，而最容易漏判的恰是**合并那一步**——「练习段 0 试次」与"
    "「跑了两遍」都是单层看不清、合并时才显形；"
    "② 落地件：`1_Code/Experiment/intake.py`（**252 行**，零依赖）**不重写任何判据**，只 import 那三个模块的"
    "既有函数（避免 D94 的教训：把「读行」抄进新工具、把「去重」留在旧工具里）；"
    "`1_Code/Experiment/exp_Check/check_intake.py`（**14/14**）；"
    "③ 判定口径：三层任一硬失败 ⇒ **EXCLUDE**（不计入 N）、只有软失败 ⇒ **REVIEW**（进得去分析但要看一眼）、"
    "全过 ⇒ **KEEP**；退出码 0 = 无 EXCLUDE、1 = 至少一场 EXCLUDE、2 = 输入不可用；"
    "④ 当场抓到并修掉自己的三个缺陷：`rec[\"rows\"]` 空键、numpy 数组做真值判断（`ValueError: truth value … "
    "ambiguous`）、以及最严重的**静默挑错文件**——`test/_full_session_out/` 的自测产物与用户交付同名，"
    "字典后写覆盖 ⇒ 报告出的「正确率 0.485 / timeout 23.4%」其实属于自测件，修法 = **层级最浅优先 + `shadowed` 显式点名**；"
    "⑤ 合规 txt 单独也能判（三层退用 txt 并警告），CSV 仍是权威快照；"
    "⑥ 已知限制：启动回显（6-A）与现场纸质记录仍需人看，组层 G1/G9 仍归 `qc_group.py`。"
    " | `1_Code/Experiment/intake.py`（**新建**，252 行）+ `1_Code/Experiment/exp_Check/check_intake.py`"
    "（**新建**，184 行，**14/14**）+ `1_Code/DDM_Core/_scratch/_apply_d95_docs.py`"
    " | **(1)** 每场交回前跑一次 `python -X utf8 1_Code/Experiment/intake.py <本场目录>`，"
    "判 KEEP 才计入 N；**(2)** 四个用户侧 Stage 不变"
    " |"
)

PROG_ROW = (
    "| 2026-10-18 | **6/7（单场入库判定器 → D95）** | 把「一场数据能不能计入 N」从「跑三个工具再心算合并」"
    "收成**一条命令给结论**：技术层（Stage 1 六项）+ 结构层（`qc_group` 的 G2–G9 与被试处置）+ 一致层"
    "（`read_formal_data` 的 25 列/`matchKey`/P）三层合并，硬失败判 EXCLUDE、软失败判 REVIEW、全过判 KEEP。"
    "真实 v4.8 那场判 EXCLUDE（练习段 0 行 + 整场跑两遍），`make_fake_pilot.py` 的干净场次判 KEEP。"
    "自测 **14/14**；顺手修掉自己「同名快照静默覆盖」的缺陷（层级最浅优先 + 点名）。"
    " | `1_Code/Experiment/intake.py`（**新建**，252 行）+ `1_Code/Experiment/exp_Check/check_intake.py`"
    "（**新建**，14/14） | 每场交回前跑一次；判 KEEP 才计入 N |"
)

CHG_ROW = (
    "| 2026-10-18 | **新增 D95（单场入库判定器）**：`1_Code/Experiment/intake.py`（252 行，三层合并判 "
    "EXCLUDE/REVIEW/KEEP，退出码 0/1/2，只 import 既有判据）+ `exp_Check/check_intake.py`（**14/14**）；"
    "同时把「同名快照静默覆盖」修成「层级最浅优先 + `shadowed` 点名」 |"
)

EV_ROW = ("| `1_Code/Experiment/intake.py`（**新建**，D95，252 行）+ "
          "`1_Code/Experiment/exp_Check/check_intake.py`（**新建**，14/14） |")


def patch_main_plan() -> tuple[int, int]:
    L = load(WS)
    before = len(L)

    # 决策行：紧随 D94 行
    i94 = anchor_idx(L, "| **D94** | 2026-10-18 |")
    L.insert(i94 + 1, D95_ROW)

    # 进度行：紧随最后一条进度行（2026-10-18 文档结构修缮）
    ip = anchor_idx(L, "| 2026-10-18 | **6（文档结构修缮）** |")
    L.insert(ip + 1, PROG_ROW)

    # 变更日志：紧随最后一条变更日志行
    ic = anchor_idx(L, "| 2026-10-18 | §3 详述：Stage 3 重名标题去重")
    L.insert(ic + 1, CHG_ROW)

    # 一手证据：紧随 v4.9 那行
    ie = anchor_idx(L, "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.8 → **v4.9**，1494 行）")
    L.insert(ie + 1, EV_ROW)

    save(WS, L)
    return before, len(L)


# --------------------------------------------------------------------------- #
# 2. README：§8.66 + §9 第 79 项
# --------------------------------------------------------------------------- #
SEC_866 = """### 8.66 一场数据能不能计入 N：三层合成一条命令（2026-10-18，D95）

**问题**：一个场次要判三件事，原先要手工跑三个工具再心算合并——技术层
（`exp_Check/check_stage1_acceptance.py`，Stage 1 六项）、结构层（`qc_group.py` 的 G2–G9 + 被试处置）、
一致层（`read_formal_data.py` 的 25 列 / `matchKey` / `P`）。而最容易出事的地方**恰好是合并那一步**：
D93 的「组 1 练习段 0 试次」和 D94 的「整场跑了两遍」都是单层都看不清、合并时才显形的问题。

**做法**：`1_Code/Experiment/intake.py`（252 行，零依赖）**不重写任何判据**，只 import 那三个模块的既有
函数。理由写在文件头：D94 的根因就是「把『读行』抄进新工具、却把『去重』留在旧工具里」，所以新工具
的第一条纪律是**不复制判据**。

| 层 | 硬失败（⇒ EXCLUDE，不计入 N） | 软失败（⇒ REVIEW，进得去分析但要人看） |
|---|---|---|
| 技术 | 六项强制项任一 FAIL | 信息项 FAIL |
| 结构 | `classify` = EXCLUDE；练习段行数 ≠ `max(4, P)`；正式段 < 0.9 × 576 | `classify` = REVIEW |
| 结构补充 | — | txt 按 `(stage, trialID)` 去重丢弃 > 0 行（整场跑了两遍） |
| 一致 | `validate()` 报错 | — |

「待复核」不是淘汰（与 `qc_group.py` 同口径）；「不计入」才是淘汰。退出码：0 = 无 EXCLUDE、
1 = 至少一场 EXCLUDE、2 = 输入不可用（没有可识别的场次）。

**两个自己踩过的坑（都在同一轮修掉）**：

1. **静默挑错文件**。`test/_full_session_out/` 里有一份自测产物 `EXP_data_group1_1.csv`，与用户交付
   的真实场次**同名**；`find_sessions` 用字典按 `(组, 编号)` 聚合，后写覆盖 ⇒ 报告里那行
   「正确率 0.485 / timeout 23.4%」其实属于自测件，真实场次被顶掉。修法：同一 `(组, 编号)` 多处快照
   时**取层级最浅的**，其余进 `shadowed` 并在报告里逐条点名。教训是通用的：**判定器不许静默选数据**。
2. **拿特征当标量**。`rec.get("P") or []` 触发
   `ValueError: The truth value of an array with more than one element is ambiguous` —— `load_file`
   返回的是「列名 → 数组」，`or` 会去求数组真值。改成 `is not None` 判断。

**只有 txt 的场次也判**：合规命名（`exp_group<组>_subject<编号>.txt`）单独存在时，三层都退用 txt 并
警告一声（CSV 是权威快照，缺少它就没法核「CSV 与 txt 是否一致」）。文件名不合规的一律**不猜**（退出码 2）。

**自测**：`exp_Check/check_intake.py`（184 行，**14/14**）六个用例——真实 v4.8 场次必须判 EXCLUDE 且
抓到「练习段 0 行」+「去重丢弃 576 行」；v4.9 冒烟产物读到 576 + 4；同名快照选浅层；文件名不合规退出码 2；
空目录退出码 2；`make_fake_pilot.py` 生成的干净场次必须判 **KEEP**（只会拦的判定器等于没有判定器）。

**实测**：

```
$ python -X utf8 1_Code/Experiment/intake.py 1_Code/Experiment/exp_matlab
[1] 组 1 · 被试 1 · EXP_data_group1_1.csv
    ⚠ 同名快照被忽略（层级更深）：1_Code\\Experiment\\exp_matlab\\test\\_full_session_out\\EXP_data_group1_1.csv
    结构：正式 576/576 试次 · 练习 0/4 行 · 去重丢弃 576 行 · 正确率 0.440 · timeout 18.8%
    ⇒ ❌ **EXCLUDE**
```

**已知限制**：启动回显（6-A）与现场纸质记录不在数据里，仍需人看；组层 G1/G9 仍要等齐人后跑
`qc_group.py`（本工具不替代组层报告）。

"""

ITEM_79 = ("| 79 | ✅ **一场数据能不能计入 N：三层合成一条命令（D95，§8.66）** | "
           "`1_Code/Experiment/intake.py`（252 行，零依赖、只 import 既有判据）把技术层 / 结构层 / 一致层"
           "合并判 EXCLUDE·REVIEW·KEEP，退出码 0/1/2；`check_intake.py` **14/14**（含「干净场次必须判 KEEP」）；"
           "修掉自己两个坑：**同名快照静默覆盖**（改层级最浅优先 + `shadowed` 点名）、拿 numpy 数组当标量判真值 |")


def patch_readme() -> tuple[int, int]:
    L = load(RM)
    before = len(L)

    i9 = anchor_idx(L, "## 9. 尚未做")
    L[i9:i9] = SEC_866.split("\n")          # 已在末尾带空行分段

    i78 = anchor_idx(L, "| 78 | ✅ **`qc_group.py` 把「跑了两遍」判成「试次数不符」（D94")
    L.insert(i78 + 1, ITEM_79)

    save(RM, L)
    return before, len(L)


# --------------------------------------------------------------------------- #
# 3. Stage 7：工具链一行 + 现场清单一条
# --------------------------------------------------------------------------- #
S7_TOOL = ("| `1_Code/Experiment/intake.py` | **单场入库判定**（D95）：把技术层 + 结构层 + 一致层合成一条命令，"
           "判 KEEP / REVIEW / EXCLUDE；**不重写判据**，只调用上面三个工具的函数。自测 `exp_Check/check_intake.py` "
           "**14/14** |")

S7_STEP = ("9. **每场交回前先跑一次入库判定**：`python -X utf8 1_Code/Experiment/intake.py <本场目录>`。"
           "判 **EXCLUDE** ⇒ 这场不计入 N，先查是程序口径（如 D93 的练习段）还是被试本人，别把不合格场次带到下一轮；"
           "判 **REVIEW** ⇒ 逐条看 ❌/🟠 说明后再并入 N；判 **KEEP** 才计样本量。")


def patch_stage7() -> tuple[int, int]:
    L = load(S7)
    before = len(L)

    i6 = anchor_idx(L, "| `1_Code/DDM_Core/_scratch/check_qc_group.py` |")
    L.insert(i6 + 1, S7_TOOL)

    i7 = anchor_idx(L, "8. 把每组的 `qc_g<N>.md` **归档**")
    L.insert(i7 + 1, S7_STEP)

    save(S7, L)
    return before, len(L)


if __name__ == "__main__":
    for name, fn in (("主计划", patch_main_plan), ("README", patch_readme), ("Stage7", patch_stage7)):
        a, b = fn()
        print(f"{name}: {a} → {b} 行（+{b - a}）")
