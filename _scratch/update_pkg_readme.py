# -*- coding: utf-8 -*-
"""临时：更新分析包 README（补充本轮新增脚本）。"""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "1_Code" / "Python_for_Check" / \
    "TenRules_Revision_20260912" / "README.md"
s = p.read_text(encoding="utf-8")

add = """
---

## 六、2026-09-12 新增脚本（收敛诊断 / CRF 叠加 / SPE 库 / 留出验证 / 图集）

| 脚本 | 作用 | 产物 |
|---|---|---|
| `hddm_convergence.py` | 24 次拟合的收敛诊断（单链 Split-R̂ + 自相关 ESS） | `convergence/`；图6-6 |
| `crf_overlay.py` | 模拟 CRF 与实测 CRF 的定量叠加（实测试次直接取自 HDDM_Ready，避免标签方向混淆） | `crf/`；图8-3 |
| `spe_database_analysis.py` | SPE 数据库可获得子集分析（实际样本量、跨研究分布、设计变量调节效应） | `spe_database/T8-1~T8-3`；图8-4 |
| `holdout_subject_validation.py` | 留出被试验证（预测新被试）：prepare / fit-docker / collect | `holdout/`；图9-1 |
| `make_thesis_v3_figures.py` | 生成 v3 论文图集（新绘 4 张 + 汇总 12 张） | `3_Figures/Thesis_v3_20260912/` |

### 运行顺序建议

```powershell
$py = "...\\.venv\\Scripts\\python.exe"

# 收敛诊断（秒级）
& $py -u hddm_convergence.py

# CRF 叠加（约 2 分钟，含被试级 bootstrap）
& $py -u crf_overlay.py

# SPE 数据库子集（约 3–5 分钟，含 1000 次数据集 bootstrap）
& $py -u spe_database_analysis.py

# 参数恢复（需 Docker；并行 4 容器时约 30–60 分钟）
& $py -u param_recovery_frozen6.py --mode fit-docker --parallel 4
& $py -u param_recovery_frozen6.py --mode collect

# 留出被试验证（建议每条件 ≥20 人后再运行）
& $py -u holdout_subject_validation.py --mode prepare
& $py -u holdout_subject_validation.py --mode fit-docker
& $py -u holdout_subject_validation.py --mode collect
```

### 本轮关键结果（供论文引用）

* **收敛**：Censor 敏感性拟合 100% 达标（R̂ ≤ 1.024、ESS ≥ 173）；主拟合 G5–G7 全达标，**G3 严重不收敛（z 的 ESS = 8.6）**、G8 的 z 不达标（ESS = 22）。
* **CRF 叠加**：实测自我优势在 **RT ≈ 480 ms** 最大（+0.14）；起始点偏向只能解释其一部分。
* **SPE 数据库**：实际分析 **44 个数据集 / 2,480 名被试 / 296,240 试次**；SPE_RT = **−98.0 ms [−116.0, −82.1]**；设计变量调节效应均不显著（T: ρ = −0.19；P: ρ = +0.21）。
* **留出验证**：脚本已跑通 prepare；当前样本下只能拆出 3–4 名验证被试（功效不足），待扩样本。
"""

if "## 六、2026-09-12 新增脚本" not in s:
    p.write_text(s.rstrip() + "\n" + add, encoding="utf-8")
    print("[README] 已追加第六节")
else:
    print("[README] 已存在，跳过")
