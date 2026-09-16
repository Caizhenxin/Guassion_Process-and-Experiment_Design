# -*- coding: utf-8 -*-
"""临时：把重跑（配置 C）结果写入 v3 正文并重建。"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BODY = DOC / "_v3_正文.md"
BUILDER = DOC / "_build_docx_v3.py"
FIGV3 = ROOT / "3_Figures" / "Thesis_v3_20260912"
FIGSRC = ROOT / "3_Figures" / "TenRules_Revision_20260912"

# ① 图6-7 入图集
src = FIGSRC / "F6-7_refit_comparison.png"
if src.exists():
    shutil.copy2(src, FIGV3 / "F6-7_refit_comparison.png")
    print("[fig] F6-7")

s = BODY.read_text(encoding="utf-8")
report = []

# ② §5.3.2：SPE_v 检验改为报告两种配置（诚实修订）
new_532 = '''主口径（G3–G8）下 SPE_v 的组间差异依赖于参数估计配置。在**历史配置**（p_outlier = 0.05、单链 3,000 draws/500 burn-in，即早期主拟合）下：F(5, 59) = 2.948, p = .019, η² = .200，JZS BF₁₀ = 2.83（r = 0.5）/ 3.29（r = 1.0），G*Power 显示可检测最小效应 f = .465 而观察效应 f = .500，安全边际很窄。然而收敛诊断（§6.3.4）显示该配置下 G3 的起始点参数 ESS 仅 8.6、且 p_outlier = 0.05 与 Censor 编码（遗漏试次 rt = deadline、response = 0）相冲突——项目自身的敏感性分析已建议 Censor 方案必须使用 p_outlier = 0。改用**修正配置**（p_outlier = 0、4 条链 × 8,000 draws、2,000 burn-in；6 个条件的核心参数全部达标，R̂ ≤ 1.000、ESS ≥ 9,400）后，组间差异**不再显著**：F(5, 59) = 1.717, p = .145, η² = .127，JZS BF₁₀ = 1.03（r = 0.5）/ 0.82（r = 1.0），观察效应 f = 1.31（可检测最小效应仍为 .465，但被试间 SPE_v 标准差由 1.28 降至 0.62）。

据此，本研究的诚实结论是：**行为层面的设计空间效应稳健（SPE_RT 显著），但漂移率层面的组间差异在参数估计配置被修正后不再显著**；早期"显著"结果部分来自未收敛与配置冲突导致的估计噪声。这一修订也改变了研究三的校准输入（见 §7.3.1）与全文结论的表述。

新旧参数对照见图 6-7（同图亦给出历史单链拟合的 95% CI，可见其区间宽度约为修正配置的两倍）。'''

s, n = re.subn(r"主口径（G3–G8）下 SPE_v 的组间差异显著：.*?(?=\n\n各条件的 HDDM 群体层参数)", new_532 + "\n\n", s, flags=re.S)
report.append(("§5.3.2", n))

# ③ §6.3.4：补三方配置对照
add_634 = '''
为厘清参数变化来源，本研究对同一批数据比较了三种配置：**A** = p_outlier = 0.05、单链 3,000/500（历史主拟合）；**B** = p_outlier = 0、单链 3,000/500（敏感性分析中的 Censor 拟合）；**C** = p_outlier = 0、4 链 × 8,000/2,000（本次重跑）。

表 6-5 三种参数估计配置的对照（群体层 v_self 与 a；CI 宽度为 95% 区间宽度）

| 条件 | A: v_self（CI 宽） | B: v_self（CI 宽） | C: v_self（CI 宽） | A: a | B: a | C: a | A: SPE_v | B: SPE_v | C: SPE_v |
|---|---|---|---|---|---|---|---|---|---|
| G3 | −1.89 (11.0) | −0.79 (0.95) | −1.13 (1.12) | 1.22 | 1.19 | 1.24 | −0.16 | +0.39 | +0.00 |
| G4 | +0.64 (3.44) | +0.23 (1.71) | +0.02 (1.67) | 1.42 | 1.26 | 1.24 | +0.66 | +1.03 | +0.61 |
| G5 | +1.35 (1.10) | +1.49 (0.99) | +1.24 (1.02) | 1.34 | 1.48 | 1.48 | +0.71 | +0.89 | +0.62 |
| G6 | +1.81 (1.46) | +0.92 (0.82) | +1.14 (0.76) | 1.48 | 1.37 | 1.39 | +0.65 | +0.23 | +0.19 |
| G7 | +1.21 (1.40) | +1.51 (1.33) | +1.31 (1.28) | 1.09 | 1.29 | 1.27 | +0.45 | +0.81 | +0.37 |
| G8 | +2.82 (3.46) | +1.56 (1.40) | +1.31 (1.39) | 2.42 | 1.32 | 1.30 | +0.26 | +0.82 | +0.31 |

对照显示两条结论。第一，**配置差异（p_outlier）比抽样长度更关键**：由 A 改为 B 时，v_self 的 CI 宽度中位数从 2.45 降至 1.16，极端取值（G3 的 −1.89、G8 的 +2.82）明显向中心回缩；这正是"Censor 编码必须搭配 p_outlier = 0"的直接体现，而历史主拟合违背了该建议。第二，在同样使用 p_outlier = 0 的前提下，单链（B）与 4 链（C）的参数接近，但**只有 C 具备可验证的收敛**（B 的 Censor 拟合在早先诊断中亦达标，但其抽样量仅为 C 的 1/10）。因此本研究以配置 C 作为参数的最终口径，并在附录 A 中同时登记 A、B、C 三套数值以备核查。
'''
anchor = "各拟合来源的收敛诊断分布见图 6-6（图 6-3 至 6-5 为参数恢复相关图，待 Docker 运行后补入）。"
if anchor in s:
    s = s.replace(anchor, anchor + "\n" + add_634)
    report.append(("§6.3.4 补三方对照", 1))
else:
    # 兼容此前更新过的措辞
    m = re.search(r"各拟合来源的收敛诊断分布见图 6-6[^\n]*\n", s)
    if m:
        s = s[:m.end()] + add_634 + s[m.end():]
        report.append(("§6.3.4 补三方对照（正则）", 1))
    else:
        report.append(("§6.3.4 补三方对照", 0))

# ④ §7.3.1：Sigmoid 校准改为修正配置结果
s, n = re.subn(r"冻结版（6 条件）最优参数：.*?(?=\n\n叙述要点)",
               '''**修正配置**（配置 C，见 §6.3.4）下的最优参数为：α₁ = 0.153、α₂ = −0.335、β₁ = −0.631、β₂ = −0.245、γ = 0.939、base_scale_v = 1.112、base_scale_a = 4.086；拟合 RMSE = 0.704，差分进化收敛。与历史单链配置（α₁ = 0.862、β₁ = +0.328、RMSE = 1.090）相比，拟合优度显著改善（RMSE 下降 35%），但**参数含义发生实质变化**。''',
               s, flags=re.S)
report.append(("§7.3.1 校准参数", n))

s, n = re.subn(r"叙述要点：早期基于含 G1/G2 的 8 条件版本曾报告.*?(?=\n\n表 7-1)",
               '''据此更新解读：① α₁ = 0.153 意味着自我条件的漂移率增益仅约 **+15%**（远低于初始假设的 +150%，也低于历史配置给出的 +86%）；② **β₁ 为负（−0.631）**，即高总可用时间条件下边界反而更低，方向与"时间压力—决策边界"假设相反；这一"符号反转"在早期 8 条件版本中曾被观察到，后被判定为低质量数据伪影，但**在收敛良好的修正配置下再次出现**，因此应被视为该数据对该假设的真实偏离，而非伪影；③ base_scale_a = 4.086 不再触界。以上变化说明：当参数估计本身更可靠时，Sigmoid 理论映射与数据的偏离更为清晰，理论假设需要修正而非归因于数据质量问题。''',
               s, flags=re.S)
report.append(("§7.3.1 解读", n))

# ⑤ §7.3.2：LOCV 更新
s, n = re.subn(r"in-sample：v_self/v_stranger/z 的 r ≈ 1\.00.*?(?=\n\nin-sample 拟合结果见图)",
               '''in-sample：v_self/v_stranger/z 的 r ≈ 1.00（插值拟合，仅说明 GP 能吸收残差），a 的 r = 0.36。修正配置下的 LOCV（6 折）：v_self r = −0.10（RMSE 1.02）、v_stranger r = +0.80（0.72）、a r = +0.77（0.18）、t r = +0.09（0.16）、z r = −0.23（0.10）、SPE_v r = −0.36（0.48）。与历史配置相比，v_stranger 与 a 的外推相关显著改善（分别由 +0.19、−0.29 变为 +0.80、+0.77），整体 RMSE 明显下降；但 v_self 与 SPE_v 仍为负相关，说明**设计点数量不足仍是外推的主要限制**，而参数估计质量改善能部分缓解这一问题。''',
               s, flags=re.S)
report.append(("§7.3.2 LOCV", n))

# ⑥ §7.3.5：PPC 覆盖率更新
s = s.replace("| acc_all（omission 计错） | 18 | .167 | 15 |", "| acc_all（omission 计错） | 18 | .111 | 16 |")
s = s.replace("| acc_responded | 18 | .167 | 15 |", "| acc_responded | 18 | .111 | 16 |")
s = s.replace("| 正确 RT 均值 | 18 | .278 | 13 |", "| 正确 RT 均值 | 18 | .056 | 17 |")
s = s.replace("| 正确 RT 中位数 | 18 | .333 | 12 |", "| 正确 RT 中位数 | 18 | .000 | 18 |")
s = s.replace("| 遗漏率 | 18 | .333 | 12 |", "| 遗漏率 | 18 | .389 | 11 |")
s = s.replace("五个统计量的 95% 预测区间覆盖率见表 7-4：acc_all 与 acc_responded 均为 .167，正确 RT 均值 .278，RT 中位数 .333，遗漏率 .333，均远低于名义水平 .95。",
              "在修正配置（配置 C）下，五个统计量的 95% 预测区间覆盖率见表 7-4：acc_all 与 acc_responded 均为 .111，正确 RT 均值 .056，RT 中位数 .000，遗漏率 .389——仍远低于名义水平 .95，且反应时类指标的失配更明显。")
report.append(("§7.3.5 PPC", 1))

BODY.write_text(s, encoding="utf-8")
print("[body] 替换结果：", report)

# ⑦ 图6-7 登记
entries = '''    ("新旧参数对照见图 6-7。", "F6-7_refit_comparison.png",
     "图6-7 主口径重跑：新旧群体层参数对照",
     "灰点为历史配置（p_outlier = 0.05、单链 3,000 draws）的估计，蓝点为修正配置（p_outlier = 0、4 链 × 8,000 draws）"
     "并含 95% CI。可见历史配置的区间宽度约为修正配置的两倍，且 G3、G6、G8 的中心值发生实质移动——"
     "说明早期参数结论受到配置冲突与收敛不足的共同影响。"),
'''
s3 = BUILDER.read_text(encoding="utf-8")
if "F6-7_refit_comparison.png" not in s3:
    marker = "]\n\n\ndef build()"
    assert s3.count(marker) == 1
    s3 = s3.replace(marker, entries + marker)
    BUILDER.write_text(s3, encoding="utf-8")
    print("[builder] 已登记图6-7")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log13.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "(no stdout)")
