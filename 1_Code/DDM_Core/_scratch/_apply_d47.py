"""_apply_d47.py — 把决策 D47 落进 `5_Reference/08_工作流/工作流_主计划.md` 的四处。

为什么要写脚本而不是手工 edit：决策表行是一条**数千字符的单行**，用 `edit` 追加必须
一字不差地匹配行尾（含可能的尾随空格），而本轮要插 4 处、其中两处是超长行。脚本按
**前缀/子串**定位再插入，不依赖行尾形状。

同时把附录里 `check_stage8_run.py` 的计数由 13/13 更正为 15/15。
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"

DECISION = (
    "| **D47** | 2026-10-14 | "
    "✅ **解析超参数 Hessian（Louis 恒等式）把正式运行从「不可行」变成「可行」**："
    "新增 `hier.hyper_hessian_analytic(modes, covs, mu, log_sigma, with_prior=True)`，"
    "用 E 步已有的众数 `x*` 与拉普拉斯协方差 `Cov` **直接**算超参数 Hessian —— "
    "**0 次众数搜索**、只剩矩阵运算；正式规模（40 人、576 试次/人）投影里超参数 Hessian 一项由 "
    "**8725 min 降为 0**。❗ 并且实测出**差分版在真实 DDM（N=2、48 试次、`names=[\"d_ref\",\"beta_T\"]`）上三个步长全都不正定**"
    "（step 0.05 / 0.02 / 0.005 的 min eig = **−1.382e-01 / −1.347e-01 / −1.223e-01**，各 1 个非正），"
    "后验 SD 因此由 `eig_floor` 而非数据决定（`ls_beta_T` 在 0.9182 / 0.9332 / 1.31 之间随步长摆动 **43%**），"
    "而解析版同点 **+9.013e-02 正定** ⇒ 这不是「更快的近似」，是**去掉了差分噪声这个错误来源**。"
    "❗ 另两条被自测抓到的错报已修：`loo.psis_loo` **没有** `n_bad` / `n` 键（真实是 `n_k_gt_bad` / `n_obs`，"
    "`stage8_run` 曾因此 `KeyError`，而自测 13/13 全绿 —— 因为 **fixture 是手写的、用了与代码相同的错键名**）；"
    "`k_max = nan` 曾被误报成「k > 1.0 不构成证据」（`nan <= 0.7` 与 `nan <= 1.0` 都是 `False`），现报「⛔ 本组 LOO 无效」 | "
    "① **独立参考**：`1_Code/DDM_Core/_scratch/check_hyper_hess.py`（新建，**全绿、exit 0**）。"
    "A 组用**闭式高斯层级**（`y~N(x,1)` ⇒ 真边际 `y~N(mu, diag(σ²+1))`）对**闭式函数**另做中心差分："
    "**A1 解析 vs 闭式差分 max 相对差 = 1.881e-08**（最差 `H[1,3]`、`max\\|H_true\\| = 3.576403`）；"
    "A0 众数 `max\\|Δ\\| = 1.022e-08`、`C_00 = 0.26470588` 与闭式一致；"
    "A2 差分步长 0.05 → **3.132e-04**、0.005 → **3.168e-05**（实测幂律 **≈1.0**，是优化残差不是定义差异）；"
    "A4 解析 `n_evals=0`（**0.26 ms**）vs 差分 40 次（0.238 s）；A5 有牙齿（`C×1.6 ⇒ 2.756e+00`、`x*+0.30 ⇒ 9.248e-01`）；"
    "A6 三条形状守卫全触发。② ❗ **B2 判据被我自己的实测推翻**：原写「至少一个步长必须正定」实测 **0/3** ⇒ "
    "改为「差分版若不正定，其失真必须被**如实报告**」（断言 `n_flipped` == 非正特征值个数，实测 **1 == 1**）。"
    "③ **B1 解析版正定**：min eig **+9.013e-02**、后验 SD `mu_d_ref` **0.9764** / `mu_beta_T` **0.6971** / "
    "`ls_d_ref` **3.1912** / `ls_beta_T` **0.9117**；EM 8 轮 23.7 s、`mu=[−1.1983,−0.2267]`、`sigma=[0.2171,0.2720]`、`n_flipped=0`。"
    "④ **B5 加速 354 647×**（解析 **0.3 ms** vs 差分 **96.4 s**）；B3 无正定步长可比 ⇒ 跳过。"
    "⑤ C 组：`cov` 与 `inv(A)` 一致到 **4.361e-17**、200 次抽取经验 SD/解析 SD = 1.013/1.047/1.004/0.925、"
    "`n_evals=0` 不随 `n_draws` 变、非法 method 抛 `ValueError`。"
    "⑥ **接口守卫 A0**：正则从 `stage8_run` 源码抽 `lk[...]` / `lk.get(...)` 的键，断言都存在于 `psis_loo` 返回中"
    "（抽到 **8 个键、0 缺失**；第一版用字面串匹配、因单双引号混用只抽到 2 个键 ⇒ **守卫本身也要有牙齿**）。"
    "⑦ `1_Code/DDM_Core/_scratch/check_stage8_run.py` **15/15、exit 0**（含新增 A7b）；"
    "`1_Code/DDM_Core/hier.py` 的 `fit_and_loo` 新增 `n_nonfinite_loglik` 让失效**可归因** | "
    "**正式采集前不必再换算法**——超参数 Hessian 已是 0 成本；单组投影中仍占大头的是 **LOO 矩阵（3566 min）** 与 "
    "**PPC（2667 min）**，二者都随 `n_draws` / `n_ppc` 线性、可调。`stage8_run.py` 新增 CLI `--hyper-method {fd,analytic}`"
    "（默认 `fd` 保持历史口径），analytic 时 `project()` 打印「解析法（Louis）⇒ 0 次众数搜索」。"
    "**已端到端跑通**（`--synthetic 2 … --hyper-method analytic`，**532.9 s**，两模型 + 分单元 PPC + "
    "`stage8_report.md` / `stage8_results.json`）；N=2 / 8 条抽取下 LOO 仍无效（`p_loo` −706.37 / −2900.54、`k_max nan`、失败 2/2），"
    "但渲染现在**如实报「⛔ 本组 LOO 无效」**、并把 `n_nonfinite_loglik` 一并印出 |"
)

PROGRESS = (
    "| 2026-10-14 | **8**（超参数 Hessian 解析化 → D47） | "
    "**把 D46 的「待办」做成实测可用的解析式，并顺手抓出两条错报与一个差分版的真缺陷**。"
    "① **解析超参数 Hessian**：`hier.hyper_hessian_analytic` 用 E 步已有的众数与拉普拉斯协方差算 "
    "`∂²log_marg/∂θ²`（Louis 恒等式：`E[∂²logN/∂θ²] + Cov[∂logN/∂θ]`） ⇒ **0 次众数搜索**，"
    "把正式规模预测里的 **8725 min 降为 0**；同点实测 **0.3 ms vs 有限差分 96.4 s = 354 647×**。"
    "② ❗ **实测推翻我的两条期望**：B2「至少一个步长必须正定」实测 **0/3**（差分版在真实 DDM 上三档全不正定，"
    "后验 SD 由地板决定）；A2 我按理想的二阶幂律设容差，实测幂律 **≈1.0**（是优化残差）。"
    "③ ❗ **两条错报**：`loo.psis_loo` 的键是 `n_k_gt_bad` / `n_obs`（`n_bad` / `n` 从不存在）⇒ `stage8_run` 曾 `KeyError`，"
    "而自测 **13/13 全绿**（**手写 fixture 与代码同错** ⇒ 测的是虚构不是接口）；`k_max = nan` 因 "
    "`nan <= 0.7` 与 `nan <= 1.0` 都是 `False` 而被误报成「k > 1.0 不构成证据」⇒ 现单独报「⛔ 本组 LOO 无效」。"
    "④ 端到端 **532.9 s 跑通**（analytic，2 人），产出 `stage8_report.md` + `stage8_results.json` | "
    "`1_Code/DDM_Core/hier.py`（新增 `hyper_hessian_analytic` + `hyper_draws(method=)` + `fit_and_loo(n_nonfinite_loglik)`）、"
    "`1_Code/DDM_Core/_scratch/check_hyper_hess.py`（新建，全绿）、"
    "`1_Code/DDM_Core/_scratch/check_stage8_run.py`（**升为 15/15**，新增 A0 接口守卫 + A7b） | "
    "**Stage 8 已无「必须做但没做」的模型件**：剩下的是**等正式数据**跑全量（`stage8_run.py --data`）；"
    "4 人干跑（作业 pwsh-190）用于看 N=4 时 LOO 是否开始可用 |"
)

CHANGELOG = (
    "| 2026-10-14 | "
    "**新增 D47：解析超参数 Hessian（Louis 恒等式）——把 D46 判为「不可行」的正式运行变成可行，"
    "并实测出差分版在真实 DDM 上不正定**。① `hier.hyper_hessian_analytic(modes, covs, mu, log_sigma, with_prior=True)`："
    "用 E 步已有的众数与拉普拉斯协方差**闭式**给出 `∂²log_marg/∂θ²`，`n_evals = 0`、"
    "**0 次众数搜索**（正式规模投影里 8725 min → 0）；同点实测 **0.3 ms vs 有限差分 96.4 s = 354 647×**。"
    "② **独立验证**（`_scratch/check_hyper_hess.py`，全绿）：A 组用闭式高斯层级另做中心差分作完全独立的参考，"
    "**max 相对差 = 1.881e-08**；❗ 首跑抓到我自己的代数错误 —— `ls` 块漏了 `4 m_k m_l s_kl`（错把 `Cov[B_k,B_l]` 写成 `2 s_kl²`），"
    "相对误差 **23%**；四阶矩交叉项**只在 `m = 0` 时消失**。"
    "③ ❗❗ **实测出的真缺陷**：差分版在真实 DDM 上 step 0.05 / 0.02 / 0.005 **全都不正定**"
    "（min eig −1.382e-01 / −1.347e-01 / −1.223e-01），`hyper_draws` 会**静默把负特征值抬到地板后照常抽样** ⇒ "
    "后验 SD 崩成 58.5/1.67/196/0.92 之类（`ls_beta_T` 摆动 43%）；解析版同点 **+9.013e-02 正定**。"
    "⇒ 记录为 note（**不是**永远为真的 `check(..., True, ...)`：那是无牙守卫），并把 B2 判据改成"
    "「差分版失真必须被如实报告」（`n_flipped` == 非正特征值个数，实测 1 == 1）。"
    "④ ❗ **两条错报**：`loo.psis_loo` 的键是 `n_k_gt_bad` / `n_obs`（**没有** `n_bad` / `n`）⇒ `stage8_run.fit_group` 曾 `KeyError`，"
    "而自测 **13/13 全绿没抓到**（**手写 fixture 用了与代码相同的错键名**）⇒ fixture 改为由真实 `psis_loo` 产生，"
    "并加 **A0** 守卫（**正则**从源码抽 `lk[...]` 键，第一版字面串匹配因单双引号混用只抽到 2 个键）；"
    "`k_max = nan` 因 `nan <= 0.7` 与 `nan <= 1.0` 都是 `False` 而被误报成「k > 1.0 不构成证据」⇒ 现报「⛔ 本组 LOO 无效」，新增 **A7b**。"
    "⑤ `stage8_run.py` 新增 `--hyper-method {fd,analytic}`（默认 `fd` 保持历史口径）与报告头记录；"
    "`project()` 在 analytic 下打印「解析法（Louis）⇒ 0 次众数搜索」。"
    "⑥ **端到端跑通**：`--synthetic 2 … --hyper-method analytic` **532.9 s**，两模型 + 分单元 PPC + `stage8_report.md` + `stage8_results.json`；"
    "N=2 时 LOO 仍无效（`p_loo` −706.37 / −2900.54、`k_max nan`）⇒ 已知小样本性质，渲染如实报「无效」。"
    "⑦ 回写：`1_Code/DDM_Core/README.md` 新增 **§8.26**（八小节）+ §8.25 第 6 节计数 13/13 → 15/15 + **§9 第 30 项**。 |"
)

EVID1 = (
    "| `1_Code/DDM_Core/_scratch/check_hyper_hess.py`（新建，**全绿、exit 0**） | "
    "**D47 的一手证据（解析超参数 Hessian）**。A 组用**闭式高斯层级**"
    "（`y~N(x,1)` ⇒ 真边际 `y~N(mu, diag(σ²+1))`）给三条公式一个完全独立的参考："
    "**解析 vs 闭式差分 max 相对差 = 1.881e-08**（最差 `H[1,3]`）；"
    "A0 众数 `max\\|Δ\\| = 1.022e-08`、`C_00 = 0.26470588` 与闭式一致。"
    "❗ **实测出真缺陷**：差分版在真实 DDM（N=2、48 试次）上三个步长全不正定"
    "（min eig −1.382e-01 / −1.347e-01 / −1.223e-01），后验 SD 由地板决定"
    "（`ls_beta_T` 0.9182 / 0.9332 / 1.31 随步长摆动 **43%**），解析版同点 **+9.013e-02 正定** ⇒ "
    "这不是「更快的近似」，而是**去掉了差分噪声这个错误来源**。另：解析 **0.3 ms** vs 差分 **96.4 s** = **354 647×** |"
)

EVID2 = (
    "| `1_Code/DDM_Core/loo.py`（`psis_loo` 的返回键）+ `1_Code/DDM_Core/_scratch/check_stage8_run.py`（**升为 15/15**） | "
    "**D47 抓到的两条错报**。① `psis_loo` 的键是 `n_k_gt_bad` / `n_obs`"
    "（另有 `n_k_gt_unusable` / `n_failed` / `k_max` / `k_median` / `pareto_k` / `elpd_i` / `n_draws`），"
    "**没有** `n_bad` / `n`；`stage8_run.fit_group` 曾因此 `KeyError: 'n_bad'`，"
    "而自测仍 **13/13 全绿** —— 因为 **fixture 是手写的、用了与代码相同的错键名**"
    "（测的是我的虚构，不是接口）⇒ fixture 改为由**真实的** `psis_loo` 产生，"
    "并加 **A0** 守卫（**正则**从源码抽 `lk[...]` / `lk.get(...)` 的键逐一核对；"
    "第一版用字面串匹配、因单双引号混用只抽到 2 个键）。"
    "② `k_max = nan` 曾掉进最差挡位被报成「k > 1.0 不构成证据」"
    "（`nan <= 0.7` 与 `nan <= 1.0` **都是 `False`**）⇒ 现单独报「⛔ **本组 LOO 无效**」，新增 **A7b** 守卫 |"
)

EVID3 = (
    "| `1_Code/DDM_Core/stage8_run.py`（`--hyper-method` / `project()` / `fit_group` / `render_group`） | "
    "**D47 的端到端证据**。analytic 下 `project()` 打印「解析法（Louis）⇒ 0 次众数搜索」，"
    "同配置投影由 FD 的 **3.42 h** 降为 **0.03 h**；正式规模（40 人、576 试次、`n_em=12`、`n_draws=200`、`n_ppc=4000`）"
    "的超参数 Hessian 一项由 **8725 min** 降为 **0**。"
    "实测端到端跑通：`--synthetic 2 … --hyper-method analytic` **532.9 s**"
    "（两模型 + 分单元 PPC + `stage8_report.md` + `stage8_results.json`）；"
    "N=2 时 LOO 仍无效（M-T1 `p_loo −706.37`、M-T3 `p_loo −2900.54`、`k_max nan`、失败 2/2），"
    "但渲染**如实报「⛔ 本组 LOO 无效」**并把 `n_nonfinite_loglik` 一并印出 |"
)


def main() -> int:
    raw = PLAN.read_text(encoding="utf-8")
    lines = raw.split("\n")
    orig = len(lines)

    def find(pred, what):
        for i, ln in enumerate(lines):
            if pred(ln):
                return i
        raise SystemExit(f"定位失败：{what}")

    # 1) 决策行：插在 D46 之后
    i_dec = find(lambda s: s.startswith("| **D46** |"), "D46 决策行")
    lines.insert(i_dec + 1, DECISION)

    # 2) 进度表行：插在 D46 那行之后
    i_prg = find(lambda s: "**8**（Stage 8 正式运行的可扩展性 → D46）" in s, "D46 进度表行")
    lines.insert(i_prg + 1, PROGRESS)

    # 3) 变更日志行：插在 D46 那行之后
    i_log = find(lambda s: s.startswith("| 2026-10-14 | **新增 D46："), "D46 变更日志行")
    lines.insert(i_log + 1, CHANGELOG)

    # 4) 附录：把 check_stage8_run.py 的计数由 13/13 更正为 15/15（只改附录那一行）
    i_app = find(
        lambda s: s.startswith("| `1_Code/DDM_Core/_scratch/check_stage8_run.py`（新建，**13/13"),
        "附录 check_stage8_run.py 行",
    )
    lines[i_app] = lines[i_app].replace("**13/13、exit 0**", "**15/15、exit 0**")

    # 5) 附录：追加 3 行 D47 证据（接在最后一行表格行之后）
    last_tbl = max(i for i, s in enumerate(lines) if s.startswith("| "))
    for k, row in enumerate((EVID1, EVID2, EVID3)):
        lines.insert(last_tbl + 1 + k, row)

    out = "\n".join(lines)
    PLAN.write_text(out, encoding="utf-8", newline="")

    print(f"文件：{PLAN}")
    print(f"行数：{orig} → {len(lines)}")
    print(f"UTF-8 BOM：{out.startswith(chr(0xFEFF))}")
    for tag, i in (("决策 D47", i_dec + 1), ("进度表", i_prg + 1), ("变更日志", i_log + 1)):
        print(f"  {tag} @ 第 {i + 1} 行，前 60 字符：{lines[i][:60]}")
    print(f"  附录 D47 证据 @ 第 {last_tbl + 2}–{last_tbl + 4} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
