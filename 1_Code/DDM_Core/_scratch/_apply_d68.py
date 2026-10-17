# -*- coding: utf-8 -*-
"""把 D68（超参数 Hessian 非正定 ⇒ σ 不得解读）落纸到四份文档。

设计
----
* 每条插入都有一个稳定的「锚点」（表格行或段落首句），`ins_after` 会断言
  新行与锚点的**竖线数相同**（表格列数），避免插错列。
* `--apply` 才写盘；默认只打印将要做的动作（干跑）。
* 幂等：每条插入前都用 `has()` 找「已存在则跳过」的标记。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

APPLY = "--apply" in sys.argv

#: 本次要写出的全部动作：(文件, 说明, 锚点片段, 新内容, 模式)
#: 模式 `after` = 插在锚点行之后；`before` = 插在锚点行之前；`replace` = 替换
ACTIONS: list[tuple[Path, str, str, str, str]] = []

# ---------------------------------------------------------------- 主计划 §5
D68_DECISION = (
    "| **D68** | 2026-10-17 | ✅ **把「超参数 Hessian 正不正定」从一句提醒变成报告里的判据行，"
    "并量出「不正定」对 σ 的实际破坏：本次收敛 σ 的末轮区间含 2.27e+03**。"
    "① 缺口：D65 的 §11 第 13 条只写「必须同报特征值谱与 `n_flipped`」，"
    "**没说后果**，读者会以为记一笔就行；而 `1_Code/DDM_Core/hier.py::subject_map_laplace` "
    "把非正特征值抬到 `floor = max(1e-8·max abs(λ), 1e-12)` 再取逆 ⇒ 该方向方差 ≈ 1/floor"
    "（可到 1e5 量级），而层级 σ² 的定义就是 `mean[(x − μ)² + Cov_kk]` ⇒ **一个被抬过的方向就能把 σ 撑到没有意义**。"
    "② 代码：`1_Code/DDM_Core/stage8_run.py::render_group` 每个模型多印一行「超参数 Hessian」——"
    "正定 ⇒ 报特征值区间并写「**正定**」；非正定 ⇒ ⛔ 写「**本次的 σ（被试间 SD）不得解读**」"
    "+ `floor` 公式 + `1/floor` 的数 + **本次收敛 σ 的末轮区间**（实测值才是「这次到底有没有被撑大」的证据）。"
    "③ 实测（D65 主配置干跑件 `_scratch/stage8_synth3_dryrun/stage8_results.json`）："
    "M-T1 `n_flipped` = **1/16**、特征值 ∈ [−0.203, 229] ⇒ `floor` = 2.29e-06、`1/floor` ≈ **4.37e+05**、"
    "收敛 σ ∈ [**0.0127, 2.27e+03**]（σ 已无意义）；M-T3 `n_flipped` = 0/14、特征值 ∈ [0.0199, 231]、"
    "σ ∈ [6.65e-06, 2.95]。④ 牙齿：`1_Code/DDM_Core/_scratch/check_stage8_run.py` 加 **A11**（非正定 ⇒ "
    "必须同时出现「1/4」「不得解读」「1/floor」）与 **A12**（正定 ⇒ 只许报「正定」、不得误报「不得解读」），"
    "**23/23 → 25/25、未通过 0 项、exit 0**（日志 `_scratch/_check_stage8_run_console.txt`）。"
    "⑤ 未测：非正定是**不是 N 依赖**（扫描探针 `_scratch/_probe_hess_scaling.py` 在跑 N ∈ {3,6,12,24}，"
    "A 组 N=3 已复现 min eig −2.3725、归一化 −4.2e-03），结果**尚未回填** —— 在它出结果前，"
    "只能写「N=3 实测不正定」，不能写「N 大了就会好」。 |"
)
ACTIONS.append((MP, "§5 决策行 D68", "", D68_DECISION, "after"))

# ---------------------------------------------------------------- 主计划 §6
D68_PROGRESS = (
    "| 2026-10-17 | **8**（报告里的 Hessian 判据 → D68） | **把「σ 到底能不能报」变成报告里的一行判据**。"
    "`stage8_run.py::render_group` 新增「超参数 Hessian」行：正定 ⇒ 报特征值区间 + 「正定」；"
    "非正定 ⇒ ⛔ 「本次 σ 不得解读」+ `floor` + `1/floor` + **本次收敛 σ 的末轮区间**。"
    "干跑件实测 M-T1 `n_flipped` = 1/16、`1/floor` ≈ 4.37e+05、σ 末轮最大 **2.27e+03** ⇒ σ 不可用；"
    "M-T3 正定、σ 最大 2.95。牙齿 A11/A12，自测 **25/25** | "
    "`1_Code/DDM_Core/stage8_run.py`（render_group）+ `_scratch/check_stage8_run.py`（A11/A12）+ "
    "`_scratch/stage8_synth3_dryrun/stage8_results.json` | 等 N 扫描（N ∈ {3,6,12,24}）结果回填「非正定是否 N 依赖」 |"
)
ACTIONS.append((MP, "§6 进度行 D68", "", D68_PROGRESS, "after"))

# ---------------------------------------------------------------- 主计划 §7
D68_CHANGELOG = (
    "| 2026-10-17 | **新增 D68：超参数 Hessian 非正定 ⇒ 报告必须说「σ 不得解读」（含 `1/floor` 与收敛 σ 区间）**。"
    "`stage8_run.py::render_group` 加一行；实测 M-T1 收敛 σ 末轮最大 2.27e+03；牙齿 A11/A12 ⇒ 25/25 |"
)
ACTIONS.append((MP, "§7 变更日志 D68", "", D68_CHANGELOG, "after"))

# ---------------------------------------------------------------- 主计划 §8
D68_EVIDENCE = (
    "| `1_Code/DDM_Core/stage8_run.py::render_group`（D68）+ `_scratch/check_stage8_run.py`（A11/A12） | "
    "每个模型多一行「超参数 Hessian」：正定 ⇒ 「正定」+ 特征值区间；非正定 ⇒ ⛔「本次 σ 不得解读」"
    "+ `floor` + `1/floor` + 收敛 σ 末轮区间。干跑件 M-T1 `n_flipped` = 1/16、eig ∈ [−0.203, 229]、"
    "`1/floor` ≈ 4.37e+05、σ ∈ [0.0127, 2.27e+03]；M-T3 0/14、σ ∈ [6.65e-06, 2.95]。自测 **25/25** |"
)
ACTIONS.append((MP, "§8 附录证据 D68", "", D68_EVIDENCE, "after"))

# ------------------------------------------------------- Stage 8 §9 自测数
S8_ROW_OLD = "自测 **23/23、未通过 0 项、exit 0**"
S8_ROW_NEW = ("自测 **25/25、未通过 0 项、exit 0**（D68 加 **A11/A12**：非正定必须写「σ 不得解读」"
              "+ `floor` + 收敛 σ 区间；正定只报「正定」）")
ACTIONS.append((S8, "§9 check_stage8_run 自测数 23/23 → 25/25", S8_ROW_OLD, S8_ROW_NEW, "replace"))

S8_NEW_ROW = (
    "| `1_Code/DDM_Core/stage8_run.py::render_group`（D68） | 每个模型多一行「超参数 Hessian」：正定 ⇒ 报特征值区间"
    " 并写「正定」；非正定 ⇒ ⛔「本次的 σ（被试间 SD）不得解读」+ `floor = max(1e-8·max abs(λ), 1e-12)` + `1/floor`"
    " + **本次收敛 σ 的末轮区间** | 干跑件实测 M-T1 `n_flipped` = 1/16、eig ∈ [−0.203, 229]、`1/floor` ≈ 4.37e+05、"
    "收敛 σ ∈ [0.0127, 2.27e+03]（σ 已无意义）；M-T3 `n_flipped` = 0/14、eig ∈ [0.0199, 231]、σ ∈ [6.65e-06, 2.95] |"
)
ACTIONS.append((S8, "§9 新增 render_group 行", "", S8_NEW_ROW, "after"))

# ------------------------------------------------------- Stage 8 §11 第 13 条
S8_LIM_OLD = "⇒ §11 第 2 条的「必须同报特征值谱与 `n_flipped`」不是仪式。"
S8_LIM_NEW = ("⇒ §11 第 2 条的「必须同报特征值谱与 `n_flipped`」不是仪式。"
              "**D68 把后果补上**：非正方向被 `floor` 抬起 ⇒ 方差 ≈ 1/floor（实测 `1/floor` ≈ 4.37e+05），"
              "层级 σ² 会被它撑大；干跑件里 M-T1 的收敛 σ 末轮最大 **2.27e+03** ⇒ **本次 σ 不得解读**，"
              "报告已按此打印（`stage8_run.py::render_group` 的「超参数 Hessian」行）。")
ACTIONS.append((S8, "§11 第 13 条追加 D68 后果", S8_LIM_OLD, S8_LIM_NEW, "replace"))

# ------------------------------------------------------- Stage 8 §12
S8_CHANGELOG = (
    "| v1.4 | 2026-10-17 | **§9 加 `render_group` 的「超参数 Hessian」行、`check_stage8_run.py` 自测 23/23 → 25/25"
    "（A11/A12）；§11 第 13 条补「非正定 ⇒ σ 不得解读」的后果与实测值（M-T1 收敛 σ 末轮最大 2.27e+03）。决策 D68 |"
)
ACTIONS.append((S8, "§12 变更日志 v1.4", "", S8_CHANGELOG, "after"))

# ---------------------------------------------------------------- DDM README §8.43
RM_843 = """## 8.43 超参数 Hessian 非正定 ⇒ 「本次的 σ 不得解读」（2026-10-17，D68）

### 一、动机：D65 只记了「要报」，没记「报了之后怎样」

D65 的 §11 第 13 条要求「必须同报特征值谱与 `n_flipped`」。但报告里多印一个 `n_flipped = 1/16`
**不改变任何结论的强度** —— 读者看到它只会想「记一笔就行」。真正的机制是：

1. `1_Code/DDM_Core/hier.py::subject_map_laplace` 对每个被试的 Hessian 做特征分解，
   把**非正**特征值抬到 `floor = max(1e-8 · max abs(λ), 1e-12)`，再取逆得到 `cov`；
2. ⇒ 被抬过的那个方向，后验方差 ≈ **1/floor**（实测 `1/floor` ≈ 4.37e+05）；
3. 层级 σ² 的定义（`hier.fit_hier`）是 `mean[(x − μ)² + Cov_kk]`
   ⇒ **一个被抬过的方向就能把 σ 撑到没有意义**。

### 二、代码改动：报告里多一行判据（`stage8_run.py::render_group`）

* 正定（`n_flipped == 0`）⇒ `超参数 Hessian：**正定**（n_flipped = 0/K、特征值 [min, max]）`；
* 非正定 ⇒ 一行写四件事：`n_flipped`、特征值区间、`floor` 公式与 `1/floor` 的数值、
  **本次收敛 σ 的末轮区间**（这一项是关键 —— `1/floor` 是机制上界，实测 σ 才是「这次到底有没有被撑大」）。

### 三、实测：一次真实干跑里 σ 被撑到 2.27e+03

来源 `1_Code/DDM_Core/_scratch/stage8_synth3_dryrun/stage8_results.json`（D65 主配置干跑，N=3）：

| 模型 | `n_flipped` | 特征值区间 | `1/floor` | 收敛 σ 末轮区间 |
|---|---|---|---|---|
| M-T1（`rho` 自由，K=8） | **1/16** | [−0.203, 229] | 4.37e+05 | [**0.0127, 2.27e+03**] |
| M-T3（`rho` = 1，K=7） | 0/14 | [0.0199, 231] | — | [6.65e-06, 2.95] |

⇒ M-T1 的 `(A)` 类参数（有界 [0, 1] 量级）出现 σ = 2270，**这在统计上没有意义**：
它正是 `1/floor` 把某个方向的后验方差放大后的产物。报告现在已经会在同一行里把这件事说出来。

### 四、牙齿（`_scratch/check_stage8_run.py`，23/23 → 25/25）

* **A11**：`eigval = [1e-2, 0.5, −2.3725, 3.0]`、`n_flipped = 1` ⇒ 报告必须同时含
  `n_flipped` = **1/4**、`不得解读`、`1/floor`，且**不得**出现单独的「正定」；
* **A12**（反向对照）：`eigval = [1e-2, 0.5, 2.0, 3.0]`、`n_flipped = 0` ⇒ 必须含「**正定**」、
  **不得**出现「不得解读」（防止一刀切把健康情形也污名化）。

### 五、尚未做

1. **非正定是不是 N 依赖**：探针 `_scratch/_probe_hess_scaling.py` 在跑 N ∈ {3, 6, 12, 24}
   （A 组 DDM 数据 / B 组非 DDM 数据，M-T1，`n_x = 21`、`n_em = 5`、144 试次/人）；
   A 组 N=3 已复现 `min eig = −2.3725`（归一化 −4.2e-03）、非正 1/16。**结果未回填** ⇒
   在它出结果前只能写「N=3 实测不正定」，**不能**写「N 大了就会好」。
2. 若 N 大了仍然不正定，则正式数据上「σ」这一列必须整列放弃（或改 `hyper_method="fd"` 重算超参数协方差，
   代价见 D47/D65 的成本表）。
3. σ 的这一行**不改变** LOO/ELPD 的结论：非正定发生在**被试层协方差**，
   而 LOO 的边际是逐被试的 log-lik，不受 `cov` 抬升影响（D65 已实测：eigenvalue shift 不影响组层 LOO 边际）。
"""

ACTIONS.append((RD, "§8.43 新节", "", RM_843, "before_section9"))

RM_ITEM = (
    "| 52 | ✅ **超参数 Hessian 非正定 ⇒ 报告必须写「本次的 σ 不得解读」（D68，§8.43）** | "
    "`stage8_run.py::render_group` 新增「超参数 Hessian」行（`floor` + `1/floor` + 收敛 σ 末轮区间）；"
    "实测 M-T1 收敛 σ 末轮最大 **2.27e+03**（`1/floor` ≈ 4.37e+05）、M-T3 正定；牙齿 A11/A12 ⇒ **25/25** |"
)
ACTIONS.append((RD, "§9 第 52 项", "", RM_ITEM, "after"))


# ------------------------------------------------------------------ 工具函数
def n_sep(s: str) -> int:
    """表格**结构**分隔符计数：跳过反引号内的 `|` 与转义的 `\\|`。

    ❗ 不能直接 `s.count("|")`：主计划里已有行把 `|` 写进行内代码
    （如 `|stimulus_dur_actual − …|`），那种竖线不是列分隔符，
    直接数会把「列数相同」的两行判成不同。
    """
    n, in_code, i = 0, False, 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        elif ch == "|" and not in_code:
            n += 1
        i += 1
    return n


def load(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def save(p: Path, lines: list[str]) -> None:
    if not APPLY:
        print(f"  [干跑] 不写 {p.name}")
        return
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def idx_of(lines: list[str], needle: str, what: str) -> int:
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    assert len(hits) == 1, f"{what}：锚点命中 {len(hits)} 次（needle={needle!r}）"
    return hits[0]


def do_actions() -> None:
    for path, what, needle, text, mode in ACTIONS:
        lines = load(path)
        if mode == "before_section9":
            key = "## 9. 尚未做"
            i = idx_of(lines, key, f"{path.name} §9 标题")
            if any(text.split("\n")[0] in ln for ln in lines):
                print(f"[跳过] {path.name}：{what}（已有）")
                continue
            lines[i:i] = text.rstrip("\n").split("\n") + [""]
            print(f"[插入] {path.name}：{what}（在 §9 之前）")
            save(path, lines)
            continue
        if mode == "replace":
            hits = [i for i, ln in enumerate(lines) if needle in ln]
            if not hits:
                # 幂等：替换过一次之后旧文本就不在了 ⇒ 只要新文本在就算已完成
                if any(text in ln for ln in lines):
                    print(f"[跳过] {path.name}：{what}（已是新文本）")
                    continue
                raise AssertionError(f"{path.name}：{what} 的替换锚点命中 0 次，且新文本也不在")
            assert len(hits) == 1, f"{path.name}：{what} 的替换锚点命中 {len(hits)} 次"
            if text in lines[hits[0]]:
                print(f"[跳过] {path.name}：{what}（已是新文本）")
                continue
            lines[hits[0]] = lines[hits[0]].replace(needle, text)
            print(f"[替换] {path.name}：{what}")
            save(path, lines)
            continue
        assert mode == "after", mode
        # 「插在哪一行之后」：靠一个**稳定的末行锚点**逐条指定
        anchor = ANCHORS[(path.name, what)]
        i = idx_of(lines, anchor, f"{path.name}：{what} 的锚点")
        first = next(ln for ln in text.rstrip("\n").split("\n") if ln.strip())
        if any(first in ln for ln in lines):
            print(f"[跳过] {path.name}：{what}（已有）")
            continue
        new = text.rstrip("\n").split("\n")
        assert all(not ln.strip() or n_sep(ln) == n_sep(lines[i]) for ln in new), (
            f"{path.name}：{what} 的新行竖线数 {[n_sep(x) for x in new]} != 锚点 {n_sep(lines[i])}")
        lines[i + 1:i + 1] = new
        print(f"[插入] {path.name}：{what}（在锚点之后）")
        save(path, lines)


#: 每条 `after` 动作的锚点行（必须唯一命中）
ANCHORS: dict[tuple[str, str], str] = {
    (MP.name, "§5 决策行 D68"): "| **D67** | 2026-10-17 |",
    (MP.name, "§6 进度行 D68"): "| 2026-10-17 | **1**（验收的机器判据 → D67） |",
    (MP.name, "§7 变更日志 D68"): "| 2026-10-17 | **新增 D67：Stage 1 验收的机器判据",
    (MP.name, "§8 附录证据 D68"): "| `1_Code/Experiment/exp_Check/check_stage1_acceptance.py`（**新建**",
    (S8.name, "§9 新增 render_group 行"): "| `1_Code/DDM_Core/_scratch/check_stage8_run.py`（E 组，D66） |",
    (S8.name, "§12 变更日志 v1.4"): "| v1.3 | 2026-10-17 |",
    (RD.name, "§9 第 52 项"): "| 51 | ✅ **Stage 1 验收的机器判据",
}

if __name__ == "__main__":
    print(f"{'应用' if APPLY else '干跑'}：{len(ACTIONS)} 条动作")
    do_actions()
    if APPLY:
        print("完成。请复跑一次确认幂等，并跑 check_table_integrity.py / check_files.py。")
