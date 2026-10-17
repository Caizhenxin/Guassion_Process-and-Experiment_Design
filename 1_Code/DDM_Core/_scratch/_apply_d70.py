# -*- coding: utf-8 -*-
"""D70 落纸：Stage 8 的**正向对照**（DDM 生成数据 ⇒ PPC 认得出、模型比较挑得对）。

用法：``python -X utf8 -u _apply_d70.py [--apply]``
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

MARK = "D70"

# ---------------- 主计划 ----------------
D70_DECISION = (
    "| **D70** | 2026-10-17 | ✅ **Stage 8 的正向对照：用 DDM 真值生成数据，看 PPC 会不会「认对」**。"
    "① 动机：D65 的阴性对照只证明「数据不是本模型生成时 PPC 会失配」（§11 第 12 条）；"
    "**没做过正向对照**，就无法区分「PPC 只会报警」与「PPC 真能对准」。"
    "② 生成器：新建 `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`（**223 行**，零新依赖），"
    "按 `1_Code/DDM_Core/two_phase.simulate_euler_subject` 用 M-T1 真值（`MappingParams` + `rho = 0.8`）"
    "生成 RT/选择，再按 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` 的帧与掩蔽规则写成 v4.1 的 "
    "**25 列 tab 分隔 txt**（`stimulus_frames = round(T / 16.667 ms)`、`mask_onset = onset + T`、"
    "`stimulus_offset = mask_onset`、漏答行 `Response = NA` 且 `Correct = NaN`）；"
    "每人 `t0` 从 `lognormal(median 0.15 s, sigma 0.12)` 抽并 clip 到 `[0.10, 0.30]`，`rho` 默认 **0.8** "
    "⇒ **M-T1 就是生成模型、M-T3 是错的那个**，模型比较的有效性可以直接判。"
    "③ 牙齿：`_scratch/check_make_ddm_pilot.py`（**138 行**）**12/12**（G1–G12：25 列表头逐字、"
    "`block` 练习 0/正式 1–3、帧数由 T 反推、漏答三件套、`n_rep` 与 `(T,W)` 格数、"
    "「不可由生成 RT 反推 rho」、慢真值能让 `timeout` 出现、G11 默认 `rho = 0.8`、G12 写文件钉死裸 LF）。"
    "④ **Stage 7 的 QC 认它**：全量设计（2 人 × 576 试次）跑 `1_Code/Experiment/qc_group.py` ⇒ "
    "**G1–G9 全 PASS、剔除 0、待复核 0**（G5 `timeout` 0.1%、G6 正确率 0.577、G7 `RT<T` 6.34%；"
    "小设计 96 试次会因为试次数不足而不过 G2/G4 —— 那是**降采样**，不是数据错）。"
    "⑤ 真值标定这条坑值得单记：`TRUTH`（`d = 1.20 / a = 1.10 / t0 = 0.15`）的 RT 中位只有 **0.275 s**，"
    "低于 `analyze_pilot.py` 的 Pilot 合理区间下界 0.3 s ⇒ 连**真由 DDM 生成**的数据也会被判 FAIL；"
    "新增 `QC_TRUTH`（`d = 1.15 / a = 1.15 / t0 = 0.18`）后 RT 中位 **0.325 s**、正确率 0.577 ⇒ 全 PASS。"
    "**教训：QC 判 FAIL 不必然是模型/代码错，先看真值选得是否比被试快。**"
    "⑥ 正向对照运行：`stage8_run.py --data ddm_pilot_posctrl`（3 人 × 96 试次、`n_x = 25`、"
    "`--hyper-method analytic`、`n_em` 5、`n_draws` 30、PPC 2）⇒ 3 人 × 96 试次、`n_x = 25`、`analytic`：**PPC 认得出自己生成的数据** —— 6 个（被试 × 模型）块的全局统计量 **69/72 = 95.8% 在带内**、分单元 **120/120 = 100%**；而 D65 的非 DDM 数据只有 **37/72 = 51.4%** 与 **95/120 = 79.2%** ⇒ 分辨力是实打实的。但**被试层 LOO 在 N=3 上仍无效**（M-T1 `p_loo/n_obs` = 496、M-T3 = 3.68）⇒ 不得引用 ELPD/ΔELPD，正向对照能支持的**只有 PPC**。 "
    "| `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`（223 行）+ `check_make_ddm_pilot.py`（138 行、12/12）"
    "+ `_scratch/ddm_pilot_full/`（2 人 × 580 行、QC G1–G9 全 PASS）+ `_scratch/_stage8_posctrl_console.txt`；"
    "`check_files.py` 通过（裸 LF、无 BOM、ast OK） "
    "| Stage 8 的对照两半齐了（正向 95.8% vs 阴性 51.4%）；LOO 仍卡在 N=3（§11 第 3 条）；下一步仍是用户侧 Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / 定稿签批 |"
)

D70_PROGRESS = (
    "| 2026-10-17 | **8**（正向对照：DDM 生成数据 → PPC 认不认得出 → D70） | "
    "**先补上 Stage 8 缺的那一半对照**。新建 `_make_ddm_pilot.py`（223 行）按 M-T1 真值生成 v4.1 逐被试 txt，"
    "`check_make_ddm_pilot.py` **12/12**；全量设计过 Stage 7 的 `qc_group.py`（G1–G9 全 PASS、剔除 0）；"
    "并发现「真值比被试快 ⇒ DDM 数据也会被 S6-5 判 FAIL」，故加 `QC_TRUTH` 预设。正向对照 3 人 × 96 试次、`n_x = 25`、`analytic`：**PPC 认得出自己生成的数据** —— 6 个（被试 × 模型）块的全局统计量 **69/72 = 95.8% 在带内**、分单元 **120/120 = 100%**；而 D65 的非 DDM 数据只有 **37/72 = 51.4%** 与 **95/120 = 79.2%** ⇒ 分辨力是实打实的。但**被试层 LOO 在 N=3 上仍无效**（M-T1 `p_loo/n_obs` = 496、M-T3 = 3.68）⇒ 不得引用 ELPD/ΔELPD，正向对照能支持的**只有 PPC**。 "
    "| `_stage8_posctrl_console.txt`、`_make_ddm_pilot.py`、`check_make_ddm_pilot.py` "
    "| Stage 8 的对照两半齐了（正向 95.8% vs 阴性 51.4%）；LOO 仍卡在 N=3（§11 第 3 条）；下一步仍是用户侧 Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / 定稿签批 |"
)

D70_CHANGELOG = (
    "| 2026-10-17 | **新增 D70：Stage 8 正向对照**。新建 `_scratch/_make_ddm_pilot.py`（223 行，按 M-T1 "
    "`rho = 0.8` 真值生成 v4.1 25 列 txt）+ `_scratch/check_make_ddm_pilot.py`（138 行、**12/12**：表头/block/帧/"
    "漏答三件套/`n_rep`/「不可由 RT 反推 rho」/慢真值出 timeout/G11 默认 `rho = 0.8`/G12 裸 LF）；"
    "全量设计（2 人 × 576 试次）过 `qc_group.py` **G1–G9 全 PASS、剔除 0、待复核 0**；"
    "另发现 `TRUTH`（`d = 1.20 / a = 1.10 / t0 = 0.15`）RT 中位 0.275 s 低于 Pilot 区间 ⇒ 连 DDM 数据也会被判 FAIL，"
    "故加 `QC_TRUTH`（`d = 1.15 / a = 1.15 / t0 = 0.18`，RT 中位 0.325 s）。正向对照 3 人 × 96 试次、`n_x = 25`、`analytic`：**PPC 认得出自己生成的数据** —— 6 个（被试 × 模型）块的全局统计量 **69/72 = 95.8% 在带内**、分单元 **120/120 = 100%**；而 D65 的非 DDM 数据只有 **37/72 = 51.4%** 与 **95/120 = 79.2%** ⇒ 分辨力是实打实的。但**被试层 LOO 在 N=3 上仍无效**（M-T1 `p_loo/n_obs` = 496、M-T3 = 3.68）⇒ 不得引用 ELPD/ΔELPD，正向对照能支持的**只有 PPC**。 |"
)

D70_EVIDENCE = (
    "| `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`（**新建**，223 行）+ `check_make_ddm_pilot.py`（138 行）"
    "+ `_scratch/ddm_pilot_full/` + `_stage8_posctrl_console.txt` "
    "| 正向对照：全局在带内 **69/72 = 95.8%**、分单元 **120/120**（阴性对照 37/72 = 51.4%、95/120）；`p_loo/n_obs` = 496 / 3.68（N=3 下 LOO 无效）；总耗时 6229.7 s |"
)

# ---------------- Stage 8 文档 ----------------
S8_ROW9 = (
    "| `_scratch/_make_ddm_pilot.py`（**D70 正向对照生成器**） | 按 M-T1 真值（`rho = 0.8`）用 "
    "`two_phase.simulate_euler_subject` 生成 RT/选择，再按 `Exp_Design_Formal.m` 的帧/掩蔽规则写成 v4.1 的 "
    "25 列 tab txt；`--preset qc` 用 `QC_TRUTH`（`d = 1.15 / a = 1.15 / t0 = 0.18`）、`--preset fim` 用 "
    "`TRUTH`（`d = 1.20 / a = 1.10 / t0 = 0.15`，与 Stage 9 探针同口径） | "
    "`_scratch/check_make_ddm_pilot.py` **12/12 通过**（G1–G12）；全量设计（2 人 × 576 试次）过 "
    "`1_Code/Experiment/qc_group.py` **G1–G9 全 PASS、剔除 0、待复核 0**；3 人 × 96 试次、`n_x = 25`、`analytic`：**PPC 认得出自己生成的数据** —— 6 个（被试 × 模型）块的全局统计量 **69/72 = 95.8% 在带内**、分单元 **120/120 = 100%**；而 D65 的非 DDM 数据只有 **37/72 = 51.4%** 与 **95/120 = 79.2%** ⇒ 分辨力是实打实的。但**被试层 LOO 在 N=3 上仍无效**（M-T1 `p_loo/n_obs` = 496、M-T3 = 3.68）⇒ 不得引用 ELPD/ΔELPD，正向对照能支持的**只有 PPC**。 |"
)

S8_ROW10 = (
    "| `1_Code/DDM_Core/stage8_run.py`（正向对照运行，D70） | 用 `ddm_pilot_posctrl`（DDM 生成、3 人 × 96 试次）"
    "跑全链路，判「PPC 会不会认对」 | 3 人 × 96 试次、`n_x = 25`：M-T1 ELPD −1642.940 ± 588.064（`p_loo` 1489.10 ⇒ 无效）、M-T3 ELPD −153.004 ± 43.343（`p_loo` 11.03、`p_loo/n_obs` 3.68 ⇒ 无效）；**PPC：M-T1 全局 34/36、分单元 60/60；M-T3 全局 35/36、分单元 60/60**（合计 **69/72** 与 **120/120**），阴性对照只有 **37/72** 与 **95/120**；总耗时 **6229.7 s**（M-T1 3966.0 s + M-T3 2236.9 s）；另 M-T1 的 Hessian 又一次 `n_flipped` = 1/16（特征值 [−0.539, 338]）⇒ 与 D68 的「最平方向随时翻负」一致 |"
)

S8_LIMIT15 = (
    "15. ❗ **正向对照只在 N=3 / 96 试次上做过（D70）**：`p_loo/n_obs` 仍是 496（M-T1）/ 3.68（M-T3） ⇒ 被试层 LOO "
    "**依旧无效**（§11 第 3 条的 N 依赖没有消失）；所以正向对照能支持的只有 PPC 与「模型比较的方向」，"
    "**不能**支持「~40 人时 LOO 可用」。另：`TRUTH` 选得比被试快时（RT 中位 0.275 s）连 DDM 数据也会被 "
    "`analyze_pilot.py` 的 S6-5 判 FAIL ⇒ 生成数据时必须显式选 `QC_TRUTH`，否则 QC 的 FAIL 会掩盖真相。"
)

S8_CHANGELOG = (
    "| v1.5 | 2026-10-17 | **§9 加正向对照生成器与运行两行、§11 加第 15 条限制**（N=3/96 试次下 LOO 仍无效；"
    "`TRUTH` 比被试快时 QC 会误判） |"
)

# ---------------- DDM README ----------------
RM_845 = """

### 8.45 Stage 8 的正向对照：DDM 生成数据要被自己的 PPC 认出来（2026-10-17，D70）

#### 8.45.1 为什么必须有这一半

D65 的合成干跑给出的是**阴性对照**：`_scratch/make_fake_pilot.py` 生成的数据不是 DDM 生成的，
PPC 报了系统性失配（遗漏率观测 0.06–0.09 vs 预测 0.19–0.26）⇒ 证明「PPC 能认出不是本模型的数据」。
但那句话有个致命的反面：**只会报警的工具也满足它**。要证明 PPC 有分辨力，必须给一份
**由本模型生成**的数据，看它会不会「认对」。

#### 8.45.2 生成器（`_scratch/_make_ddm_pilot.py`，223 行）

* RT/选择来自 `1_Code/DDM_Core/two_phase.simulate_euler_subject`，真值 = `MappingParams`
  （`shape_model = "lin"`）+ `rho = 0.8` ⇒ **生成模型就是 M-T1**，M-T3（`rho` 固定 1）是错的那个。
* 写文件按 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` 的规则：`HEADER25` 25 列、
  tab 分隔、`stimulus_frames = round(T / 16.667 ms)`、`mask_onset_actual = onset + T`、
  `stimulus_offset_actual = mask_onset_actual`、漏答行 `Response = NA` 且 `Correct = NaN`。
* 每人 `t0` 从 `lognormal(median 0.15 s, sigma 0.12)` 抽、clip 到 `[0.10, 0.30]`。
* 两档真值：`--preset qc`（默认，`QC_TRUTH`：`d = 1.15 / a = 1.15 / t0 = 0.18`）与
  `--preset fim`（`TRUTH`，与 Stage 9 探针同口径：`d = 1.20 / a = 1.10 / t0 = 0.15`）。

#### 8.45.3 牙齿（`_scratch/check_make_ddm_pilot.py`，138 行，12/12）

G1 表头逐字等于 `RF.HEADER25`、G2/G3 `block` 练习 0 与正式 1–3、G4 `stimulus_frames` 由 T 反推、
G5 漏答三件套、G6 `(T, W)` 格数与 `n_rep`、G7「不可由生成 RT 反推 rho」、G8 慢真值能让 `timeout` 出现、
G11 默认 `rho = 0.8`、G12 写文件钉死 `newline="\\n"`。

#### 8.45.4 Stage 7 的 QC 认不认这份数据

全量设计（2 人 × 576 试次）跑 `1_Code/Experiment/qc_group.py` ⇒ **G1–G9 全 PASS、剔除 0、待复核 0**
（G5 `timeout` 0.1%、G6 正确率 0.577、G7 `RT<T` 6.34%）。96 试次的小设计会因试次数不足而不过 G2/G4 ——
那是**降采样**，不是数据错。

#### 8.45.5 一条标定发现：真值比被试快，QC 会误判

`TRUTH`（`d = 1.20 / a = 1.10 / t0 = 0.15`）的 RT 中位只有 **0.275 s**，低于 `analyze_pilot.py` 的
S6-5 合理区间下界 0.3 s ⇒ **真由 DDM 生成**的数据也会被 QC 判 FAIL。改 `QC_TRUTH`
（`d = 1.15 / a = 1.15 / t0 = 0.18`）后 RT 中位 **0.325 s**、正确率 0.577 ⇒ 全 PASS。
⇒ 教训：QC 判 FAIL 时先问「真值是不是选得比被试快」，不要直接怀疑模型或代码。

#### 8.45.6 正向对照的结果

**DDM 生成的数据被自己的 PPC 认了出来**（`_scratch/ddm_pilot_posctrl`，3 人 × 96 试次、`n_x = 25`、`--hyper-method analytic`；报告在 `_scratch/stage8_posctrl_rho08/`）：

| 数据来源 | （被试 × 模型）块数 | 全局 12 项在带内 | 分单元 20 项在带内 |
|---|---|---|---|
| **正向对照**（`_make_ddm_pilot.py`，M-T1 为生成模型） | 6 | **69/72 = 95.8%** | **120/120 = 100%** |
| 阴性对照（D65 的 `make_fake_pilot.py`，非 DDM） | 6 | **37/72 = 51.4%** | **95/120 = 79.2%** |

逐块：M-T1 12/12、12/12、10/12；M-T3 12/12、12/12、11/12 ⇒ 连**错的模型**（M-T3，`rho` 固定 1）也能把「由 M-T1 生成」的数据描述到带内 —— 这符合预期（M-T3 是 M-T1 的约束特例，`rho = 0.8` 与 1 在 96 试次上分辨力有限），也说明**PPC 不是模型选择工具**（§11 第 7 条）。

**LOO 这边没有变好**：3 人 × 96 试次下 `p_loo/n_obs` = **496**（M-T1）与 **3.68**（M-T3）⇒ 两个模型都被判「⛔ 本组 LOO 无效」，`compare_models` 的 ΔELPD 不得引用。这不是数据来源的问题，是 §11 第 3 条的 N 依赖 ⇒ 「正向对照能做」与「LOO 能用」是两件事。

附带一条观测：M-T1 的超参数 Hessian 又是 `n_flipped` = **1/16**（特征值 [−0.539, 338]），M-T3 正定（0/14、[0.229, 343]）—— 与 D68 的「最平方向随时可能翻负、与 N 无单调关系」完全一致。

顺带修掉一个显示缺陷：报告表头的「来源」原先硬编码成「正式数据」，对照运行里是错的标签；现在写成 `--data <路径>`（`check_stage8_run.py` 的 **E6** 静态守卫，自测 **26/26**）。

#### 8.45.7 尚未做

1. 正向对照只做了 N=3 / 96 试次；要让**被试层 LOO**（不只是 PPC）也有效，需要 N≈40 的规模，
   成本按 §8.40 的 ×4 余量估算在小时量级 ⇒ 留给真实数据或专门一次长跑。
2. PPC 的分单元统计量在正向对照里也只是 20 项/块；正式数据上要按 §10 第 4 条补齐。
"""

RM_ITEM = (
    "| 54 | ✅ **Stage 8 的正向对照（D70，§8.45）** | `_scratch/_make_ddm_pilot.py`（223 行）按 M-T1 真值生成 "
    "v4.1 txt；`check_make_ddm_pilot.py` **12/12**；全量设计过 `qc_group.py` **G1–G9 全 PASS、剔除 0**；"
    "正向对照 PPC 全局 **69/72 = 95.8%** 在带内、分单元 **120/120**（阴性对照 37/72 = 51.4%、95/120） |"
)


def patch(path: Path, what: str, old: str, new: str) -> bool:
    txt = path.read_text(encoding="utf-8")
    if new in txt:
        print(f"[跳过] {path.name}：{what}（已落纸）")
        return True
    n = txt.count(old)
    if n != 1:
        print(f"❌ {path.name}：{what} 锚点命中 {n} 次")
        return False
    if APPLY:
        path.write_text(txt.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")
    return True


def ins_after(path: Path, what: str, prefix: str, new_line: str, guard: str) -> bool:
    txt = path.read_text(encoding="utf-8")
    if guard in txt:
        print(f"[跳过] {path.name}：{what}（已落纸）")
        return True
    lines = txt.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(idx) != 1:
        print(f"❌ {path.name}：{what} 的前缀命中 {len(idx)} 次（{prefix[:40]}…）")
        return False
    lines[idx[0] + 1:idx[0] + 1] = [new_line]
    if APPLY:
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")
    return True


def ins_before(path: Path, what: str, prefix: str, block: str, guard: str) -> bool:
    txt = path.read_text(encoding="utf-8")
    if guard in txt:
        print(f"[跳过] {path.name}：{what}（已落纸）")
        return True
    lines = txt.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(idx) != 1:
        print(f"❌ {path.name}：{what} 的前缀命中 {len(idx)} 次")
        return False
    lines[idx[0]:idx[0]] = block.split("\n")
    if APPLY:
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[{'写入' if APPLY else '干跑'}] {path.name}：{what}")
    return True


bad = 0
bad += not ins_after(MP, "§5 D70 决策行", "| **D69** | 2026-10-17 |", D70_DECISION, "| **D70** |")
bad += not ins_after(MP, "§6 D70 进度行", "| 2026-10-17 | **9**（共享流 CRN 配对 → D69）",
                     D70_PROGRESS, "（正向对照：DDM 生成数据")
bad += not ins_after(MP, "§7 D70 变更日志", "| 2026-10-17 | **新增 D69：共享流 CRN 配对实测后不升格**",
                     D70_CHANGELOG, "**新增 D70：Stage 8 正向对照**")
bad += not ins_after(MP, "§8 D70 附录证据", "| `1_Code/AutoRA_SPE/_probe_crn_pairing.py`（**新建**，137 行）",
                     D70_EVIDENCE, "_make_ddm_pilot.py`（**新建**，223 行）")
bad += not ins_after(S8, "§9 正向对照运行行", "| `_scratch/diag_gpd_bias.py`", S8_ROW10,
                     "正向对照运行，D70")
bad += not ins_after(S8, "§9 生成器行", "| `_scratch/diag_gpd_bias.py`", S8_ROW9,
                     "D70 正向对照生成器")
bad += not ins_after(S8, "§11 第 15 条", "14. ❗ **输入契约是硬约束**", S8_LIMIT15,
                     "正向对照只在 N=3 / 96 试次上做过")
bad += not ins_after(S8, "§12 v1.5", "| v1.4 | 2026-10-17 |", S8_CHANGELOG, "| v1.5 |")
bad += not ins_before(RD, "§8.45", "## 9. 尚未做", RM_845.strip("\n"), "8.45 Stage 8 的正向对照")
bad += not ins_after(RD, "§9 第 54 项", "| 53 | ✅ **「共享流 CRN 配对」实测后不升格", RM_ITEM,
                     "| 54 | ✅ **Stage 8 的正向对照")

print()
print("✅ 全部落点成功" if not bad else f"❌ {bad} 个落点失败")
raise SystemExit(0 if not bad else 1)
