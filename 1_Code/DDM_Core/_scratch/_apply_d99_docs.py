"""D99 落纸：Stage 8 quick 配置下四组 LOO 全不可引用 ⇒ 闸门接进流水线。

幂等：D99 已存在则不重复插入。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
GUIDE = ROOT / "5_Reference" / "08_工作流" / "全流程一键跑通_使用说明.md"

D_DATE = "2026-10-18"


def one(lines: list[str], needle: str, what: str) -> int:
    hits = [i for i, x in enumerate(lines) if needle in x]
    if len(hits) != 1:
        raise AssertionError(f"{what}：命中 {len(hits)} 次（期望 1）—— 锚点 `{needle}`")
    return hits[0]


def patch_main() -> str:
    L = MAIN.read_text(encoding="utf-8").split("\n")
    if any("| **D99** |" in x for x in L):
        return "主计划：D99 已存在，跳过"

    # 1) 决策表：D98 行之后
    i = one(L, "| **D98** |", "决策表 D98")
    row = (
        f"| **D99** | {D_DATE} | ⛔ **Stage 8 四组 LOO 全部不可引用：闸门必须进流水线，不许靠人记**。"
        "① 触发：`stage8_run.py` 在 quick 配置（`n_em=3`、`n_draws=12`、`n_x=21`）上跑完 8 人 4 组、"
        "耗时 **11594.3 s（3.2 h）**；逐组 M-T1/M-T3 的 ELPD 分别为 组1 **−536.7/−537.4**、"
        "组2 **−3359.6/−2904.8**、组3 **−3899.6/−3402.0**、组4 **−2886.1/−2668.1**。"
        "② 复核：`stage8_health.py --strict` 判 **4/4 组「不可引用」** —— `n_flipped` = 1/16、2/16、3/16、3/16"
        "（D74 超参数 Hessian 非正定），`p_loo÷n_obs` = 0.009、2.16、3.22、2.33（后三组把拟合样本量全算成了有效参数）。"
        "组 1 的 `p_loo` 看着健康也被 D74 判死 ⇒ **`k_max = 0` 与 `p_loo` 都不是充分判据**。"
        "③ 缺陷：`run_pipeline.py` 的结果节骨架只印 elpd/Δelpd/SE/**k 诊断**，不读 `stage8_health` ⇒ "
        "把不可引用的 Δelpd 摆在「模型比较」标题下，正是 D52 警告的「只报 k 会误判可报」。"
        "④ 修法：新增 `assess_health()`（复用 `H8.assess_group`，不重写判据）+ 流水线新增 **3.5 LOO 健康** 步骤"
        "（任一组 BAD ⇒ 该步 `ok=False`、整体退出码 1）+ 骨架 §2 增 `p_loo÷n_obs`/`n_flipped`/判定/原因四列"
        "与段首横幅 + `fig3` 对不可引用组加斜线并标注「N/M 组未过闸门」。"
        "⑤ 结论：quick 配置**只能证明流水线可跑通**，Δelpd 一律不进论文；正式数据必须 `--profile formal`"
        "（`n_draws=50` ≥ 25 才有 k 诊断）且先过 `stage8_health.py --strict`。"
        "⑥ 代价：这次 3.2 h 的拟合**一个可引用数字都没换来**，但换到了「闸门必须自动跑」这条硬约束。 |"
        " `1_Code/Experiment/run_pipeline.py`（+`assess_health`、「3.5 LOO 健康」步骤、骨架 §2 四列）"
        " + `1_Code/Experiment/make_figures.py`（`fig3` 斜线标记）"
        " + `2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_pipeline/results_skeleton.md`（实测 0/4 可引用） |"
        " 看论文结果时先看「判定」列：`⛔ 不可引用` 的组一律只写进流程验证记录 |"
    )
    L.insert(i + 1, row)

    # 2) 进度表：末行之后
    last = max(k for k, x in enumerate(L) if x.startswith("| 2026-10-18 | **全流程跑通"))
    L.insert(last + 1,
             f"| {D_DATE} | **D98 复核（→ D99）** | 等 3.2 h 的拟合跑完才发现四组 LOO 全不可引用，"
             "而流水线骨架照样把 Δelpd 印在「模型比较」标题下 ⇒ 把 `stage8_health` 的判据接进流水线"
             "（3.5 步 + 骨架四列 + 图注斜线），并明确「quick 只验证机制、formal 才出结论」 |")
    # 3) 变更日志：末行之后
    tail = max(k for k, x in enumerate(L) if x.startswith("| 2026-10-18 | **新增 D98"))
    L.insert(tail + 1,
             f"| {D_DATE} | **新增 D99（LOO 闸门进流水线）**：`run_pipeline.py` 加 `assess_health()` 与 "
             "「3.5 LOO 健康」步骤（复用 `stage8_health.assess_group`）、骨架 §2 增 `p_loo÷n_obs`/"
             "`n_flipped`/判定/原因四列 + 段首「不可引用」横幅、`make_figures.fig3` 对不可引用组加斜线；"
             "实测四组 0/4 可引用（`n_flipped` 1–3/16、`p_loo÷n_obs` 0.009–3.22） |")
    # 4) 证据表：末行之后
    ev = max(k for k, x in enumerate(L) if x.startswith("| `1_Code/Experiment/run_pipeline.py`"))
    L.insert(ev + 1,
             "| `1_Code/Experiment/run_pipeline.py`（D99 增 `assess_health` + 3.5 步 + 骨架四列）、"
             "`1_Code/Experiment/make_figures.py`（`fig3` 斜线）、"
             "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_stage8_out/`（4 组 JSON）| "
             "**D99**：实测 `n_flipped` 1/16–3/16、`p_loo÷n_obs` 0.009–3.22 ⇒ 4/4 组不可引用 |")
    MAIN.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return f"主计划：已插入 D99（{len(L)} 行）"


def patch_readme() -> str:
    L = README.read_text(encoding="utf-8").split("\n")
    if any(x.startswith("## 8.70") for x in L):
        return "README：§8.70 已存在，跳过"
    h = one(L, "## 9. 尚未做", "README §9 标题")
    block = [
        "## 8.70 LOO 闸门必须自动跑：quick 配置下四组全不可引用（D99）",
        "",
        "- 事实：`stage8_run.py` 在 quick 配置上跑完 8 人 4 组（3.2 h），"
        "`stage8_health.py --strict` 判 **4/4 组「不可引用」** ——"
        "`n_flipped` = 1/16、2/16、3/16、3/16（D74），`p_loo÷n_obs` = 0.009、2.16、3.22、2.33。",
        "- **`k_max = 0` 与 `p_loo` 都不是充分判据**：组 1 的 `p_loo` = 10.07（÷`n_obs` = 0.009）看着很健康，"
        "仍因超参数 Hessian 非正定被判死。判据只有一处：`stage8_health.assess_mode/assess_group`。",
        "- 已犯的错：`run_pipeline.py` 的结果节骨架只印 elpd/Δelpd/SE/「k 诊断可用」，不读健康判词 ⇒ "
        "把不可引用的 Δelpd 摆在「模型比较」标题下（D52 的老毛病换了个外壳）。",
        "- 现在的行为：① 新增 `assess_health()`（复用 `H8.assess_group`，**不重写判据**）；"
        "② 流水线多一个「3.5 LOO 健康」步骤，任一组 BAD ⇒ `ok=False` 且整体退出码 1；"
        "③ 骨架 §2 增 `p_loo÷n_obs`、`n_flipped`、判定、原因四列 + 段首横幅；"
        "④ `fig3` 对不可引用组加斜线并标注「N/M 组未过闸门」。",
        "- 口径：quick（`n_draws=12`）**只验证机制**；要出结论必须 `--profile formal`（`n_draws=50` ≥ 25 才有 Pareto-k 诊断）"
        "并先过 `stage8_health.py --strict`。",
        "",
    ]
    L[h:h] = block
    README.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return f"README：已插入 §8.70（{len(L)} 行）"


def patch_guide() -> str:
    if not GUIDE.exists():
        return "使用说明：不存在，跳过"
    L = GUIDE.read_text(encoding="utf-8").split("\n")
    if any("3.5 LOO 健康" in x for x in L):
        return "使用说明：已含 3.5 步，跳过"
    anchors = [k for k, x in enumerate(L) if "退出码" in x]
    i = anchors[0] if anchors else len(L) - 1
    insert = [
        "",
        "### 步骤 3.5「LOO 健康」是硬闸门",
        "",
        "`stage8_run.py` 打印的 ELPD 是否可引用，**不看 `k_max`**：`k_max = 0` 在抽样数不足时是恒定值，",
        "`p_loo` 健康也不够（超参数 Hessian 非正定同样判死）。判据只有 `1_Code/DDM_Core/stage8_health.py` 一处。",
        "流水线会在拟合后自动跑这一步：任一组 `BAD` ⇒ 该步 ❌、整体**退出码 1**，",
        "`results_skeleton.md` §2 会打「本段数值不可引用」横幅，`fig3` 给这些组加斜线。",
        "此时图与表仍可看，但**只能写进流程验证记录**，不得作为模型比较证据。",
    ]
    L[i:i] = insert
    GUIDE.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return f"使用说明：已插入「3.5 步」小节（{len(L)} 行）"


if __name__ == "__main__":
    for fn in (patch_main, patch_readme, patch_guide):
        print(fn())
    sys.exit(0)
