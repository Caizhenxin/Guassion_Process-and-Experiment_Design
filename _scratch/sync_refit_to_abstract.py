# -*- coding: utf-8 -*-
"""临时：修图6-7锚点 + 把重跑结论同步进摘要与结论，重建。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BUILDER = DOC / "_build_docx_v3.py"
FRONT = DOC / "_v3_front_摘要.md"
BODY = DOC / "_v3_正文.md"

# ① 构建脚本锚点
s = BUILDER.read_text(encoding="utf-8")
s = s.replace('("新旧参数对照见图 6-7。"', '("新旧参数对照见图 6-7"')
BUILDER.write_text(s, encoding="utf-8")
print("[builder] 锚点已放宽")

# ② 摘要（中/英）
f = FRONT.read_text(encoding="utf-8")
old_cn = "参数层面（主口径 6 个条件），漂移率层面的自我优势 SPE_v 差异显著，F(5, 59) = 2.95, p = .019, η² = .200，但贝叶斯因子仅为轶事级（BF₁₀ = 2.83–3.29），功效分析显示安全边际极窄（可检测最小效应 f = .465，观察 f = .500）。"
new_cn = ("参数层面（主口径 6 个条件），漂移率层面的自我优势 SPE_v 差异在历史参数配置下显著（F(5, 59) = 2.95, p = .019, BF₁₀ = 2.83–3.29），"
          "但该配置存在收敛不足（G3 的 ESS 仅 8.6）与 p_outlier 设置冲突；改用修正配置（p_outlier = 0、4 条链 × 8,000 draws、2,000 burn-in，核心参数 ESS ≥ 9,400、R̂ ≤ 1.000）后，"
          "该差异不再显著（F(5, 59) = 1.72, p = .145, BF₁₀ = 1.03）。")
n1 = f.count(old_cn); f = f.replace(old_cn, new_cn)

old_cn2 = "差分进化校准显示，边界调制参数方向与\"时间压力—决策边界\"假设一致（β₁ = +0.328），自我条件的漂移率增益约为 +86%（低于初始假设的 +150%），且早期含低质量组时出现的边界参数饱和现象消失。"
new_cn2 = ("差分进化校准（修正参数配置）给出 α₁ = 0.153（自我条件的漂移率增益仅约 +15%）、β₁ = −0.631（高总可用时间条件下边界反而更低，方向与假设相反）与 RMSE = 0.704；"
           "该结果表明：当参数估计更可靠时，理论与数据的偏离更为清晰，Sigmoid 假设需要修正。")
n2 = f.count(old_cn2); f = f.replace(old_cn2, new_cn2)

old_en = "At the parameter level (six high-quality conditions), SPE in drift rate differed significantly, F(5, 59) = 2.95, p = .019, η² = .200, with anecdotal Bayes factors (BF₁₀ = 2.83–3.29) and a narrow power margin (minimum detectable f = .465 vs. observed f = .500)."
new_en = ("At the parameter level (six high-quality conditions), SPE in drift rate differed significantly under the historical estimation configuration "
          "(F(5, 59) = 2.95, p = .019, BF₁₀ = 2.83–3.29), but that configuration suffered from inadequate convergence (ESS = 8.6 for one parameter in G3) "
          "and a p_outlier setting incompatible with censored omissions; with the corrected configuration (p_outlier = 0; 4 chains × 8,000 draws; ESS ≥ 9,400; R̂ ≤ 1.000) "
          "the difference was no longer significant (F(5, 59) = 1.72, p = .145, BF₁₀ = 1.03).")
n3 = f.count(old_en); f = f.replace(old_en, new_en)

old_en2 = "Differential-evolution calibration yielded boundary-modulation parameters consistent with the time-pressure hypothesis (β₁ = +0.328) and a self-advantage gain in drift rate of about +86% (below the initial +150% assumption)."
new_en2 = ("Differential-evolution calibration under the corrected configuration yielded α₁ = 0.153 (a self-advantage gain in drift rate of only about +15%) and "
           "β₁ = −0.631 (a lower boundary under generous time budgets, opposite to the time-pressure hypothesis), with RMSE = 0.704, indicating that the Sigmoid assumption needs revision.")
n4 = f.count(old_en2); f = f.replace(old_en2, new_en2)
FRONT.write_text(f, encoding="utf-8")
print(f"[摘要] 替换计数：CN1={n1} CN2={n2} EN1={n3} EN2={n4}")

# ③ 正文 §9.1 与 §10
b = BODY.read_text(encoding="utf-8")
b, m1 = re.subn(r"第一，设计空间系统调控 SPE，且作用是非线性的。.*?(?=\n\n第二，遗漏试次的处理方式)",
                "第一，设计空间对 SPE 的调控在**行为层面稳健**：SPE_RT 在 8 个设计单元间差异显著（F(7, 80) = 2.79, p = .012）而 SPE_ACC 不显著；"
                "P/T/W 的线性模型几乎无解释力（R² = .051），模型比较进一步显示线性模型的预测误差比均值基线高一个数量级。"
                "但**参数层面的组间差异不稳健**：在修正参数估计配置后，SPE_v 的组间差异不再显著（F(5, 59) = 1.72, p = .145, BF₁₀ = 1.03），"
                "早期显著结果（p = .019）主要来自收敛不足与 p_outlier 配置冲突。", b, flags=re.S)
b, m2 = re.subn(r"第三，Sigmoid\+GP 混合生成模型实现了.*?(?=\n\n第四，)",
                "第三，Sigmoid+GP 混合生成模型的贡献需按修正配置重新界定：理论先验（Sigmoid）承担主要预测功能（纯 Sigmoid 的 LOCV 误差 1.135，线性模型 8.535），"
                "GP 残差层在 6 个设计点下未提升外推预测；在校正参数估计后，校准得到 α₁ = 0.153（自我增益约 +15%）与 β₁ = −0.631（方向与时间压力假设相反），"
                "拟合优度改善（RMSE 由 1.090 降至 0.704）但 v_self 与 SPE_v 的留一条件交叉验证仍不成立（r = −0.10、−0.36）；"
                "后验预测检验显示行为分布层面仍存在系统失配（95% 预测区间覆盖率 .00–.39）。", b, flags=re.S)
b, m3 = re.subn(r"第二，遗漏试次的处理方法会实质影响 DDM 参数估计：在高遗漏条件下.*?(?=\n\n第三，)",
                "第二，遗漏试次的处理方法会实质影响 DDM 参数估计：绝对漂移率在 Censor 方案下被系统性低估、在 Drop 方案下被系统性高估"
                "（参数恢复：偏倚 −1.34 与 +0.73，95% CI 覆盖率 17% 与 0%），而「自我 vs 陌生人」的**相对效应几乎完美恢复**（SPE_v 覆盖率 100%，r = .97/.91）；"
                "遗漏率–偏倚曲线进一步显示绝对偏倚随遗漏率单调增大（>50% 时达 1.6–3.2），而相对方向在所有水平下保持稳定。", b, flags=re.S)
BODY.write_text(b, encoding="utf-8")
print(f"[正文] §9/§10 替换计数：{m1}/{m2}/{m3}")

r = subprocess.run([sys.executable, "-u", str(BUILDER)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
(ROOT / "_scratch" / "build_log14.txt").write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
print("[build] exit:", r.returncode)
print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "(no stdout)")
