# -*- coding: utf-8 -*-
"""把 D70 落纸脚本里的 PC_* 占位符替换成实测数字（一次性）。"""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = Path(__file__).resolve().parent / "_apply_d70.py"
t = p.read_text(encoding="utf-8")

N_SR = len((Path(__file__).resolve().parents[1] / "stage8_run.py").read_text(encoding="utf-8").split("\n"))
N_CHK = len((Path(__file__).resolve().parent / "check_stage8_run.py").read_text(encoding="utf-8").split("\n"))
print(f"stage8_run.py = {N_SR} 行、check_stage8_run.py = {N_CHK} 行")

RESULT = (
    "3 人 × 96 试次、`n_x = 25`、`analytic`：**PPC 认得出自己生成的数据** —— 6 个（被试 × 模型）块的"
    "全局统计量 **69/72 = 95.8% 在带内**、分单元 **120/120 = 100%**；而 D65 的非 DDM 数据只有 "
    "**37/72 = 51.4%** 与 **95/120 = 79.2%** ⇒ 分辨力是实打实的。但**被试层 LOO 在 N=3 上仍无效**"
    "（M-T1 `p_loo/n_obs` = 496、M-T3 = 3.68）⇒ 不得引用 ELPD/ΔELPD，正向对照能支持的**只有 PPC**。"
)
RUN = (
    "3 人 × 96 试次、`n_x = 25`：M-T1 ELPD −1642.940 ± 588.064（`p_loo` 1489.10 ⇒ 无效）、"
    "M-T3 ELPD −153.004 ± 43.343（`p_loo` 11.03、`p_loo/n_obs` 3.68 ⇒ 无效）；"
    "**PPC：M-T1 全局 34/36、分单元 60/60；M-T3 全局 35/36、分单元 60/60**（合计 **69/72** 与 **120/120**），"
    "阴性对照只有 **37/72** 与 **95/120**；总耗时 **6229.7 s**（M-T1 3966.0 s + M-T3 2236.9 s）；"
    "另 M-T1 的 Hessian 又一次 `n_flipped` = 1/16（特征值 [−0.539, 338]）⇒ 与 D68 的「最平方向随时翻负」一致"
)
DETAIL = (
    "**DDM 生成的数据被自己的 PPC 认了出来**（`_scratch/ddm_pilot_posctrl`，3 人 × 96 试次、`n_x = 25`、"
    "`--hyper-method analytic`；报告在 `_scratch/stage8_posctrl_rho08/`）：\n\n"
    "| 数据来源 | （被试 × 模型）块数 | 全局 12 项在带内 | 分单元 20 项在带内 |\n"
    "|---|---|---|---|\n"
    "| **正向对照**（`_make_ddm_pilot.py`，M-T1 为生成模型） | 6 | **69/72 = 95.8%** | **120/120 = 100%** |\n"
    "| 阴性对照（D65 的 `make_fake_pilot.py`，非 DDM） | 6 | **37/72 = 51.4%** | **95/120 = 79.2%** |\n\n"
    "逐块：M-T1 12/12、12/12、10/12；M-T3 12/12、12/12、11/12 ⇒ 连**错的模型**（M-T3，`rho` 固定 1）"
    "也能把「由 M-T1 生成」的数据描述到带内 —— 这符合预期（M-T3 是 M-T1 的约束特例，`rho = 0.8` 与 1 "
    "在 96 试次上分辨力有限），也说明**PPC 不是模型选择工具**（§11 第 7 条）。\n\n"
    "**LOO 这边没有变好**：3 人 × 96 试次下 `p_loo/n_obs` = **496**（M-T1）与 **3.68**（M-T3）⇒ 两个模型都被"
    "判「⛔ 本组 LOO 无效」，`compare_models` 的 ΔELPD 不得引用。这不是数据来源的问题，是 §11 第 3 条的 "
    "N 依赖 ⇒ 「正向对照能做」与「LOO 能用」是两件事。\n\n"
    "附带一条观测：M-T1 的超参数 Hessian 又是 `n_flipped` = **1/16**（特征值 [−0.539, 338]），M-T3 正定"
    "（0/14、[0.229, 343]）—— 与 D68 的「最平方向随时可能翻负、与 N 无单调关系」完全一致。\n\n"
    "顺带修掉一个显示缺陷：报告表头的「来源」原先硬编码成「正式数据」，对照运行里是错的标签；"
    "现在写成 `--data <路径>`（`check_stage8_run.py` 的 **E6** 静态守卫，自测 **26/26**）。"
)

repl = {
    "PC_RESULT_RUN": RUN,
    "PC_RESULT_DETAIL": DETAIL,
    "PC_PLOO_RATIO": "496（M-T1）/ 3.68（M-T3）",
    "PC_RESULT_SHORT": "PPC 全局 **69/72 = 95.8%** 在带内、分单元 **120/120**"
                       "（阴性对照 37/72 = 51.4%、95/120）",
    "PC_EVIDENCE": "正向对照：全局在带内 **69/72 = 95.8%**、分单元 **120/120**"
                   "（阴性对照 37/72 = 51.4%、95/120）；`p_loo/n_obs` = 496 / 3.68（N=3 下 LOO 无效）；"
                   "总耗时 6229.7 s",
    "PC_NEXT": "Stage 8 的对照两半齐了（正向 95.8% vs 阴性 51.4%）；LOO 仍卡在 N=3（§11 第 3 条）；"
               "下一步仍是用户侧 Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / 定稿签批",
    # PC_RESULT（决策行里的那一句）最后替换，避免短字符串被它吞掉
}
for k, v in repl.items():
    n = t.count(k)
    if n == 0:
        print(f"[跳过] {k}（已替换）")
        continue
    t = t.replace(k, v)
    print(f"[替换] {k} ×{n}")

n = t.count("PC_RESULT")
t = t.replace("PC_RESULT", RESULT)
print(f"[替换] PC_RESULT ×{n}")

t = t.replace(
    "`_scratch/check_make_ddm_pilot.py`（**138 行**）",
    f"`_scratch/check_make_ddm_pilot.py`（**138 行**）")
p.write_text(t, encoding="utf-8", newline="\n")
assert "PC_" not in t, "还有未替换的占位符：" + str([ln for ln in t.split("\n") if "PC_" in ln][:3])
print("✅ 占位符全部替换")
