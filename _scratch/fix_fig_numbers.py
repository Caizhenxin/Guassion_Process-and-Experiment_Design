# -*- coding: utf-8 -*-
"""临时：统一四份文档中的图号（按出现顺序编号）。"""
from pathlib import Path

D = Path(__file__).resolve().parent          # _scratch
ROOT = D.parent                              # 项目根
DOC = ROOT / "5_Reference" / "终版论文格式及要求"

def apply(path: Path, pairs, label):
    s = path.read_text(encoding="utf-8")
    for a, b in pairs:
        n = s.count(a)
        if n != 1:
            print(f"  [{label}] WARN count={n} :: {a[:36]}")
        s = s.replace(a, b)
    path.write_text(s, encoding="utf-8")
    print(f"[{label}] 已处理 {path.name}")

# ---------- 说明书 ----------
apply(DOC / "图表与指标说明书_面向同门_20260912.md", [
    ("图5-3 Censor 与 Drop", "图6-1 Censor 与 Drop"),
    ("`F5-3_omission_delta.png`", "`F6-1_omission_delta.png`"),
    ("图7-3 / 图7-4 / 图7-5 后验预测检验", "图7-4 / 图7-5 / 图7-6 后验预测检验"),
    ("`F7-3_ppc_interval.png` / `F7-4_ppc_coverage.png` / `F7-5_ppc_qp.png`",
     "`F7-4_ppc_interval.png` / `F7-5_ppc_coverage.png` / `F7-6_ppc_qp.png`"),
    ("图7-6 模型比较与模型恢复", "图7-3 模型比较与模型恢复"),
    ("`F7-6_model_comparison.png`", "`F7-3_model_comparison.png`"),
    ("`F7-7_candidates.png`", "`F7-7_candidates.png`"),
    ("图8-3 Stim-Coding 仿真的 CRF 曲线", "图8-2 Stim-Coding 仿真的 CRF 曲线"),
    ("`F8-3_stimcoding_crf.png`", "`F8-2_stimcoding_crf.png`"),
    ("（图5-3）", "（图6-1）"),
    ("| ③ 遗漏处理方式实质影响参数估计 | 图5-3、表6-1、表6-2 |",
     "| ③ 遗漏处理方式实质影响参数估计 | 图6-1、表6-1、表6-2 |"),
    ("| ② 线性模型无法解释该调控 | 表5-5、图7-6（左） |",
     "| ② 线性模型无法解释该调控 | 表5-5、图7-3（左） |"),
    ("| ④ 遗漏率可分档（>35% 不可用 / <15% 可靠） | 图5-3、图6-3（曲线，待运行）、表6-5 |",
     "| ④ 遗漏率可分档（>35% 不可用 / <15% 可靠） | 图6-1、图6-4（曲线，待运行）、表6-5 |"),
    ("| ⑦ GP 层的价值在不确定性而非精度 | 图7-6（左）、表7-5、表7-6 |",
     "| ⑦ GP 层的价值在不确定性而非精度 | 图7-3（左）、表7-5、表7-6 |"),
    ("| ⑧ 恒定边界 DDM 在截止时间任务中存在误配 | 图7-3~7-5、表7-7、表7-8 |",
     "| ⑧ 恒定边界 DDM 在截止时间任务中存在误配 | 图7-4~7-6、表7-7、表7-8 |"),
    ("| ⑨ 机制链：起始点偏向→早期优势 | 图8-3、图8-1 |",
     "| ⑨ 机制链：起始点偏向→早期优势 | 图8-2、图8-1 |"),
], "说明书")

# ---------- 必须补的表清单 ----------
apply(DOC / "必须补的表清单_20260912.md", [
    ("| 图 6-2 | OPN 第一版预测精度与边际效应 | 已有 |",
     "| 图 6-2 | OPN 第一版预测精度与边际效应 | 已有（`F6-2_opn.png`） |"),
    ("| 🆕 图 7-2 | 模型比较条形图 + 混淆矩阵热图 | `model_comparison.png` |",
     "| 🆕 图 7-3 | 模型比较条形图 + 混淆矩阵热图 | `F7-3_model_comparison.png` |"),
    ("| 🆕 图 7-3 | PPC：观测 vs 预测区间（身份层） | `ppc_interval_by_identity.png` |",
     "| 🆕 图 7-4 | PPC：观测 vs 预测区间（身份层） | `F7-4_ppc_interval.png` |"),
    ("| 🆕 图 7-4 | PPC 覆盖率 | `ppc_coverage.png` |",
     "| 🆕 图 7-5 | PPC 覆盖率 | `F7-5_ppc_coverage.png` |"),
    ("| 🆕 图 7-5 | QP 图（观测 vs 预测） | `ppc_quantile_probability.png` |",
     "| 🆕 图 7-6 | QP 图（观测 vs 预测） | `F7-6_ppc_qp.png` |"),
    ("| 图 7-6 | 候选设计点不确定性 | 已有 |",
     "| 图 7-7 | 候选设计点不确定性 | 已有（`F7-7_candidates.png`） |"),
    ("| 图 8-2 | 模拟 CRF vs 实测 CRF（待补叠加） | ⏳ 待补 |",
     "| 图 8-3 | 模拟 CRF vs 实测 CRF（待补叠加） | ⏳ 待补 |"),
    ("| 图 8-3 | Stim-Coding 双引擎 CRF | 已有 |",
     "| 图 8-2 | Stim-Coding 双引擎 CRF | 已有（`F8-2_stimcoding_crf.png`） |"),
    ("| 🆕 图 6-4 | 遗漏率–偏倚曲线（含 15%/35% 参考线） | `param_recovery_omission_bias.png` |",
     "| 🆕 图 6-4 | 遗漏率–偏倚曲线（含 15%/35% 参考线） | `param_recovery_omission_bias.png`（⏳待运行） |"),
    ("| 🆕 图 6-5 | 95% CI 覆盖率 | `param_recovery_coverage.png` |",
     "| 🆕 图 6-5 | 95% CI 覆盖率 | `param_recovery_coverage.png`（⏳待运行） |"),
    ("| 🆕 图 6-3 | 参数恢复：真值 vs 恢复值（两方案） | `param_recovery_scatter.png` |",
     "| 🆕 图 6-3 | 参数恢复：真值 vs 恢复值（两方案） | `param_recovery_scatter.png`（⏳待运行） |"),
], "表清单")

# ---------- 规则5与7段落 ----------
apply(DOC / "规则5与规则7_Methods与Results段落_20260912.md", [
    ("表 7-7、表 7-8、图 7-3~7-5", "表 7-7、表 7-8、图 7-4~7-6"),
    ("图 6-3（真值 vs 恢复值散点，Censor 与 Drop 分列）、图 6-5（95% CI 覆盖率）",
     "图 6-3（真值 vs 恢复值散点，Censor 与 Drop 分列）、图 6-5（95% CI 覆盖率）"),
], "规则5/7段落")

print("完成")
