# -*- coding: utf-8 -*-
"""D75 落纸：超参数 Hessian 的正定性**不是**样本量的函数（扫描 + 加试次两路实测）。

用法：python -X utf8 -u _apply_d75.py [--apply]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

DECISION = (
    "| **D75** | 2026-10-17 | ❗ **超参数 Hessian 的正定性不是样本量的函数 —— 不能承诺「人够了 LOO 就可用」**。"
    "① 扫描（`_scratch/_probe_hyper_pd.py`，`n_em=2`、`n_x=21`、S=2、seed 7、≈46 试次/人、逐档只改 N）："
    "N=2 **正定**（min eig 0.0388、负 0/16、max\\|θ\\| 7.0）、N=3 **正定**（0.0265、0/16、7.3）、"
    "N=4 **非正定**（−0.0875、1/16、62.8）、N=5 **正定**（0.1019、0/16、4.5）、N=6 **非正定**"
    "（−0.0051、1/16、33.6）⇒ **不随 N 单调**。② 加试次也救不了：N=4 把每人试次从 ≈46 提到 187–191"
    "（`n_rep=4`）后仍 1/16 非正定（min eig −0.357、max eig 469.7、max\\|θ\\| **97.9**、拟合 256.4 s）。"
    "③ 与 D74 的 2 人 S=15 那次（2/14 负、max\\|θ\\| 303）合看 ⇒ **`λ_min` 的符号本身不说明程度**"
    "（失败拟合的 `λ_min` 常常只到 −0.005，相对 `λ_max` 约 1e-5），与之同步恶化的是**抽样跑了多远**："
    "正定的四个拟合 max\\|θ\\| ≤ 7.3，非正定的三个 33.6 / 62.8 / 97.9 ⇒ 分离 5–40 倍。"
    "④ 代码：`hier.hyper_draws` 新增 `max_abs_theta` 并随结果落盘；`render_group` 的「超参数 Hessian」行"
    "把 `n_flipped` 与「本次抽样 `\\|θ\\|` 最大」并列印（字段缺失时写「未记录」，**不得静默省略**）；"
    "`check_stage8_run.py` **34 → 36/36**（A13/A13b）。⑤ 正式数据口径：**LOO 可用性只能逐组事后判定**——"
    "每组先看 `n_flipped`、特征值谱与 `max_abs_theta`，再决定该组的 `p_loo`/`ELPD` 是否可引用；"
    "论文不得写「~40 人/组时 LOO 可用」。 | 扫描 `_scratch/_probe_hyper_pd.py`（N=2…6）+ "
    "`_scratch/_probe_hyper_pd_n4r4.txt`（加试次）+ `_scratch/_probe_hyper_pd_nscan.txt`；"
    "自测 `check_stage8_run.py` 36/36（A13/A13b） | D74 的「先查 Hessian」保留不变，但**判据内容补上"
    "「跑多远」这一栏**；Stage 8 §10 的回填要求新增「逐组先看 n_flipped 与 max_abs_theta」；"
    "任何「人数够了就好」的说法作废 |"
)

PROGRESS = (
    "| 2026-10-17 | **8**（Hessian 正定性 vs 样本量 → D75） | **证伪「人够了 LOO 就会好」**：N=2…6 扫描里"
    "正定/非正定交替（2、3、5 正定；4、6 非正定），N=4 把试次 ×4 后仍非正定（max\\|θ\\| 97.9）⇒ 正定性是"
    "逐次拟合的性质，不是样本量的函数；报告的 Hessian 行改为并列印 `n_flipped` 与 max\\|θ\\|。 | "
    "`1_Code/DDM_Core/hier.py`（`max_abs_theta`）、`stage8_run.py`（Hessian 行）、"
    "`_scratch/check_stage8_run.py`（36/36，A13/A13b）、`_scratch/_probe_hyper_pd.py`（扫描） | "
    "正式数据到手后逐组判定 LOO 可用性；仍等用户侧 Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / "
    "定稿签批 |"
)

CHANGELOG = (
    "| 2026-10-17 | **新增 D75：超参数 Hessian 的正定性不是样本量的函数**。① N=2…6 扫描（n_em=2、n_x=21、"
    "S=2、≈46 试次/人）：2/3/5 正定、4/6 非正定 ⇒ 非单调；② N=4 加试次到 187–191 后仍 1/16 非正定"
    "（max\\|θ\\| 97.9）；③ 失败拟合的 λ_min 可只到 −0.005，故判据补「max\\|θ\\|」一栏（正定 ≤ 7.3 vs 非正定 "
    "33.6–97.9，分离 5–40 倍）；④ `hyper_draws` 增 `max_abs_theta`、报告并列印、"
    "`check_stage8_run.py` 34 → 36/36。 |"
)

FILE_ROW = (
    "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（N=2…6 扫描 + N=4 加试次，D75） + "
    "`1_Code/DDM_Core/hier.py`（`max_abs_theta`） + `1_Code/DDM_Core/stage8_run.py`（Hessian 行并列印） + "
    "`_scratch/check_stage8_run.py`（**36/36**，A13/A13b） | 2026-10-17（D75） |"
)

S9_ROW = (
    "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（D75 扫描） | 同一份代码、只改 N（`n_em=2`、`n_x=21`、"
    "S=2、seed 7、≈46 试次/人），读 `hyper.eigval` 与 `max_abs_theta` | N=2 正定（0.0388、0/16、7.0）、"
    "N=3 正定（0.0265、0/16、7.3）、N=4 **非正定**（−0.0875、1/16、62.8）、N=5 正定（0.1019、0/16、4.5）、"
    "N=6 **非正定**（−0.0051、1/16、33.6）；N=4 加试次到 187–191 仍 1/16 非正定（−0.357、max\\|θ\\| 97.9、"
    "256.4 s）⇒ **正定性逐次拟合而定，非样本量函数** |"
)

S11_19 = (
    "19. ❗ **不得写「人够了 LOO 就可用」（D75）**：超参数 Hessian 的正定性在 N=2…6 上**非单调**"
    "（2/3/5 正定、4/6 非正定），调大每人试次也不消除（N=4：≈46 → 187–191 试次后仍 1/16 非正定、"
    "`max|θ|` 从 62.8 升到 97.9）。且失败拟合的 `λ_min` 可只到 −0.005（相对 `λ_max` 约 1e-5）⇒ "
    "**符号不说明程度**，必须与 `max_abs_theta` 并列报告。"
)

VERSION = (
    "| v1.8 | 2026-10-17 | **新增 D75**：超参数 Hessian 正定性非样本量函数（N=2…6 扫描 + N=4 加试次两路实测）；"
    "`hier.hyper_draws` 增 `max_abs_theta`、§9 的 Hessian 行并列入报告、`check_stage8_run.py` 34 → **36/36**"
    "（A13/A13b）；§10 回填要求新增「逐组先看 `n_flipped` 与 `max_abs_theta`，再决定 LOO 是否可引用」；"
    "§11 加第 19 条 |"
)

S10_ITEM = (
    "1. ❗ **先判 LOO 可用性、再谈 ΔELPD（D74/D75）**：每组拟合完，报告里「超参数 Hessian」行若非正定"
    "（`n_flipped` > 0）或本次抽样 `\\|θ\\|` 最大值远大于其余组（实测分离：正定 ≤ 7.3 vs 非正定 33.6–303），"
    "则该组的 `p_loo`/`ELPD` **一律不解读**；同时记录特征值谱与 `max_abs_theta`，并在该组报告口径行标注 "
    "`--loo-level`。⚠️ 不得因为「每组 ~40 人」就预先承诺 LOO 可用（D75：正定性在 N=2…6 上非单调）。"
)

RD_SECTION = (
    "### 8.49 超参数 Hessian 的正定性不是样本量的函数（2026-10-17，D75）\n"
    "\n"
    "1. **问题**：D74 把「超参数 Hessian 非正定」立成了 LOO 可用的前置条件，但当时只有两个点（2 人非正定、"
    "3 人正定），很容易被读成「人太少，人多了就好」。\n"
    "2. **扫描（N=2…6，只改 N）**：`_scratch/_probe_hyper_pd.py`，`n_em=2`、`n_x=21`、S=2、seed 7、"
    "≈46 试次/人：N=2 正定（min eig 0.0388、0/16、max\\|θ\\| 7.0）、N=3 正定（0.0265、0/16、7.3）、"
    "N=4 **非正定**（−0.0875、1/16、62.8）、N=5 正定（0.1019、0/16、4.5）、N=6 **非正定**（−0.0051、1/16、33.6）"
    " ⇒ **非单调**。\n"
    "3. **加试次也不救**：N=4 把每人试次从 ≈46 提到 187–191（`n_rep=4`）后仍是 1/16 非正定"
    "（min eig −0.357、max eig 469.7、max\\|θ\\| **97.9**、拟合 256.4 s）。\n"
    "4. **判据要补一栏**：失败拟合的 `λ_min` 可以只到 −0.005（相对 `λ_max` 约 1e-5）⇒ 符号不说明程度；"
    "与之同步恶化的是**抽样跑了多远**（`max_abs_theta`）。实测分离：正定 ≤ 7.3，非正定 33.6 / 62.8 / 97.9 / 303"
    "（2 人 S=15 那次）。\n"
    "5. **代码**：`hier.hyper_draws` 增 `max_abs_theta`（随结果落盘）；`render_group` 的 Hessian 行并列印"
    "「`n_flipped`」与「本次抽样 `\\|θ\\|` 最大」（字段缺失写「未记录」）。牙齿 `check_stage8_run.py` "
    "**34 → 36/36**（A13 必须印、A13b 不得静默省略）。\n"
    "6. **口径**：正式数据里 LOO 可用性**只能逐组事后判定**；论文不得写「~40 人/组时 LOO 可用」。"
)

RD_ITEM = (
    "| 59 | ✅ **超参数 Hessian 正定性不是样本量的函数（D75，§8.49）** | N=2…6 扫描（`n_em=2`、`n_x=21`、S=2、"
    "≈46 试次/人）：2/3/5 正定、4/6 非正定 ⇒ 非单调；N=4 把试次 ×4（187–191）后仍 1/16 非正定、max\\|θ\\| 97.9 "
    "⇒ 加试次也不消除。失败拟合的 `λ_min` 可只到 −0.005（相对 `λ_max` 1e-5）⇒ 符号不说明程度，须与 "
    "`max_abs_theta` 并列报（正定 ≤ 7.3 vs 非正定 33.6–303，分离 5–40 倍）。`hier.hyper_draws` 增 "
    "`max_abs_theta`、报告 Hessian 行并列印；`check_stage8_run.py` **34 → 36/36**（A13/A13b）。"
    "⚠️ 论文不得写「~40 人/组时 LOO 可用」 |"
)


def insert_after(text: str, prefix: str, new: str) -> str:
    lines = text.split("\n")
    hit = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hit) == 1, f"{prefix[:40]}… 命中 {len(hit)} 行"
    lines.insert(hit[0] + 1, new)
    return "\n".join(lines)


def renumber_s10(t: str) -> str:
    """§10 插入新第 1 条后，把原 1..5 重排成 2..6。"""
    lines = t.split("\n")
    i0 = lines.index("## 10. 正式数据到手后的动作（回填要求）")
    i1 = i0 + 1
    while not lines[i1].startswith("---"):
        i1 += 1
    n = 0
    for i in range(i0 + 2, i1):
        m = re.match(r"^(\d+)\. (.*)$", lines[i])
        if m:
            n += 1
            lines[i] = f"{n}. {m.group(2)}"
    return "\n".join(lines)


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}")

    t = MP.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D75" in t:
        print("  [跳过] 工作流_主计划.md（已落）")
    else:
        t = insert_after(t, "| **D74** | 2026-10-17 |", DECISION)
        t = insert_after(t, "| 2026-10-17 | **8**（试次层 LOO 落地 → D73⑧/D74） |", PROGRESS)
        t = insert_after(t, "| 2026-10-17 | **新增 D74：超参数 Hessian 正定是 LOO 可用的前置条件", CHANGELOG)
        t = insert_after(t, "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（正定侧：", FILE_ROW)
        if APPLY:
            MP.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] 工作流_主计划.md")

    t = S8.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D75" in t:
        print("  [跳过] Stage8_建模与验证方案.md（已落）")
    else:
        t = insert_after(t, "| `1_Code/DDM_Core/_scratch/_probe_hyper_pd.py`（D74） |", S9_ROW)
        t = insert_after(t, "18. ❗ **「试次层」不是 LOO 可用的充分条件（D74）**", S11_19)
        t = insert_after(t, "| v1.7 | 2026-10-17 |", VERSION)
        # §10：新第 1 条 + 重排
        lines = t.split("\n")
        i0 = lines.index("## 10. 正式数据到手后的动作（回填要求）")
        assert lines[i0 + 2].startswith("1. 用 `stage8_run.py`")
        lines.insert(i0 + 2, S10_ITEM)
        t = "\n".join(lines)
        t = renumber_s10(t)
        if APPLY:
            S8.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] Stage8_建模与验证方案.md")

    t = RD.read_text(encoding="utf-8")
    assert "\r" not in t
    if "### 8.49" in t:
        print("  [跳过] README.md（已落）")
    else:
        lines = t.split("\n")
        hits = [i for i, ln in enumerate(lines) if ln.startswith("## 9. 尚未做")]
        assert len(hits) == 1
        lines[hits[0]:hits[0]] = RD_SECTION.split("\n") + [""]
        i59 = [i for i, ln in enumerate(lines) if ln.startswith("| 58 | ✅")]
        assert len(i59) == 1
        lines.insert(i59[0] + 1, RD_ITEM)
        if APPLY:
            RD.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
