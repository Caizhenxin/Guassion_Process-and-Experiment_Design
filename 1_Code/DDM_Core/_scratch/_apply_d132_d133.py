# -*- coding: utf-8 -*-
"""在主计划里登记 D132（真值校准）与 D133（形状族预登记 + L1）。四处：决策表/进度/变更日志/证据表。"""
from __future__ import annotations

import sys
from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
text = P.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
n0 = len(lines)

D133_ROW = ("| **D133** | 2026-10-26 | **形状族（exp/lin/sigmoid/power）在本设计下不可裁定：L1 最大族间差 8.8 ms < 2 SE**。"
            "① 预登记写入 `5_Reference/08_工作流/形状族恢复_预登记_20261026.md`（主判据 LOCV、辅判据 ΔBIC 罚 `k·ln576` 与组层 `ΣLRT~χ²(n)`、逐被试 LRT 不作主判据、必报撞界率与假阳性格）。"
            "② L1（`_scratch/_l1_shape_curvature.py`）：四族归一到同过 d(100)/d(250)，插值 d(150) 与线性的最大差 **8.8 ms**"
            "（`sigmoid(n=8,K=0.12)`；exp τ=0.08 仅 3.8 ms、power 全档 ≤1.3 ms），换算灵敏度实测「d +10% ⇒ RT −46 ms」；"
            "1 SE≈8 ms、2 SE≈16 ms ⇒ 落 1–2 SE「边缘可分辨」。③ 外推到 T=400 ms 也只有 **17.7 ms**（≈2.2 SE）⇒ 补一档 T 的投入产出比不支持。"
            "④ 决策：**不改程序、不追加采集、不跑 L3**；限制写成「形状分辨率由 T 的**跨度**决定，不是档数也不是人数」，"
            "与 Stage 4「low6 最差」不矛盾（那是参数 SE 视角）。 | 用户 2026-10-26「形状函数的行为层恢复…先给思路后再补方案」+「请继续」 | "
            "`5_Reference/08_工作流/形状族恢复_预登记_20261026.md` §一–§六 + `_scratch/_l1_shape_curvature.py` |\n")

D132_ROW = ("| **D132** | 2026-10-26 | **「把 SPE 做大」不能靠调 `beta_S`：两通道不可解耦 + 分位形状结构失配**。"
            "① `_scratch/_truth_calibrate.py` 扫 `beta_S ∈ [−0.30, 0.45]` × `dz_S ∈ [0, 0.08]`（6 格 × 2500 抽样，885 s）："
            "`beta_S` 与 `dz_S` **同向**推高（RT 更负、acc 更大），(ΔRT −33 ms, Δacc +0.067) **在模型内无解**——RT 差对上时 Δacc 必然 1.5–1.8 倍（+0.105…0.119）。"
            "② 更要紧的是分位形状：实测 ΔRT 随分位**变大**（p25 −18 → p75 −47），模型任何参数下都平坦或反向收窄（−39 → −26）⇒ **结构失配**，不是调参。"
            "③ 模型漏答恒 32–33% vs 实测 14.5%（W=800 格 55–58% vs 45.5%），与 §七 PPC 过散同源（`t0`/`a` 偏慢）。"
            "④ 决定：生成图只改真值口径时须明写「Δacc 会跟着涨」，**不改 Stage 8 八个拟合**；结构修正（让 SPE 只作用慢尾，如与 `P`/`W` 交互）留到 55 人批评估。 | "
            "用户 2026-10-26「我认同你的 1+3（真值校准 + 换图），暂时不需要 2」 | "
            "`5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md` §十 + `_scratch/_truth_calibrate.py` + `2_Data/Real_Data/New_Design/_pipeline/truth_calibrated_20261026.json` |\n")

# 1) 决策表：插在 D131 行之前（D133 在上，D132 次之）
idx = next(i for i, ln in enumerate(lines) if ln.startswith("| **D131** |"))
lines[idx:idx] = [D133_ROW, D132_ROW]

# 2) 进度行：插在 28（D131）之后
idx = next(i for i, ln in enumerate(lines) if "**28（SPE 量级三方对照 → D131）**" in ln)
lines[idx + 1:idx + 1] = [
    "| 2026-10-26 | **29（真值校准：两通道不可解耦 → D132）** | beta_S×dz_S 30 组扫描：两通道同向，"
    "(ΔRT −33, Δacc +0.067) 无解；实测 ΔRT 随分位变大而模型平坦/反向 ⇒ 结构失配；模型漏答 32–33% vs 实测 14.5%。不改 Stage 8 拟合。 | "
    "用户认可「真值校准 + 换图」 | `_truth_calibrate.py`、`truth_calibrated_20261026.json` |\n",
    "| 2026-10-26 | **30（形状族 L1：不可裁定 → D133）** | 四族插值 d(150) 与线性最大差 8.8 ms（exp τ=0.08 仅 3.8 ms），"
    "灵敏度 d+10%⇒RT −46 ms；1 SE≈8、2 SE≈16 ⇒ 边缘可分辨 ⇒ 不改程序、不跑 L3；补 T=400 仅 17.7 ms。 | "
    "用户「请继续」（批准 L1 先行） | `形状族恢复_预登记_20261026.md`、`_l1_shape_curvature.py` |\n",
]

# 3) 变更日志：插在 D131 行之后
idx = next(i for i, ln in enumerate(lines) if "**新增 D131（SPE 量级三方对照）**" in ln)
lines[idx + 1:idx + 1] = [
    "| 2026-10-26 | **新增 D132（真值校准：两通道不可解耦 + 分位形状失配）**：`beta_S`/`dz_S` 同向，"
    "(ΔRT −33, Δacc +0.067) 无解，实测 SPE 集中在慢尾而模型平坦/反向；漏答 32–33% vs 14.5%。 |\n",
    "| 2026-10-26 | **新增 D133（形状族预登记 + L1）**：LOCV 主判据、ΔBIC/组层 ΣLRT 辅；L1 最大族间差 8.8 ms < 2 SE ⇒ 不可裁定；"
    "补 T=400 仅 17.7 ms ⇒ 不改程序、不跑 L3。 |\n",
]

# 4) 证据表：追加两行到表末
idx = next(i for i, ln in enumerate(lines) if "D131 证据：" in ln)
lines.insert(idx + 1,
             "| `5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md` §十 + `_scratch/_truth_calibrate.py` | D132 证据：① 30 组 (beta_S,dz_S) 扫描表（885 s、6 格 × 2500 抽样）；"
             "② 最优 (0.30,0.02) ⇒ ΔRT −24/−33/−32、Δacc +0.119、漏答 32%；(0.00,0.04) ⇒ −21/−21/−17、+0.063；(−0.15,0.08) ⇒ −39/−37/−26、+0.063；"
             "③ 实测目标 −18/−33/−47、+0.067、14.5%、692 ms。 |\n")
lines.insert(idx + 2,
             "| `5_Reference/08_工作流/形状族恢复_预登记_20261026.md` §六 + `_scratch/_l1_shape_curvature.py` | D133 证据：① 灵敏度 d+10% ⇒ RT −46 ms（基线 689 ms, T=150）；"
             "② LOCV 最大族间差 8.8 ms（sigmoid n=8,K=0.12），exp(τ=0.08) 3.8 ms，power 全档 ≤1.3 ms；③ 外推 T=400 最大 17.7 ms。 |\n")

P.write_text("".join(lines), encoding="utf-8")
print(f"行数 {n0} → {len(lines)}")
for k in ("**D133**", "**D132**", "29（真值校准", "30（形状族", "新增 D132", "新增 D133", "D132 证据", "D133 证据"):
    print(k, sum(1 for ln in lines if k in ln))
