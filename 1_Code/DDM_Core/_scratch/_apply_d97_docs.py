# -*- coding: utf-8 -*-
"""D97 落纸：Stage 5 定稿（签批已填）+ 效应量三层方案。

改动清单（每处断言「命中恰 1 次」，命中数不对整批不写）：

`5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md`
  1. 头部状态行 🟡 待签批 → ✅ 定稿（2026-10-18 蔡振辛 / hcp）
  2. 头部「阶段状态」行：Stage 5 → ✅、Stage 1 → 🟢、Stage 6 → 🟡、Stage 7 → ⚪
  3. 新增 **§5.7 效应量与证据强度：三层分工**（插在 `## 6. 报告纪律清单` 之前）
  4. §6 末加两条报告纪律（G*Power 只作行为层；LOO ≠ BF）
  5. §7 表末加 **⑩**（顺序 BF 停收的裁定）
  6. §9 变更日志加 **v2.7**

`5_Reference/08_工作流/工作流_主计划.md`
  7. 决策表：D96 之后加 **D97**
  8. §2 阶段总览 Stage 5 行：🟡 进行中 → ✅ 定稿
  9. §3 Stage 5 详述标题加状态
 10. 进度表末行后加一行
 11. 变更日志末行后加一行
 12. 一手证据表末行后加一行

`1_Code/DDM_Core/README.md`
 13. 新 §8.68（插在 `## 9. 尚未做` 之前）
 14. §9 第 **81** 项（接在第 80 项之后）
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
FINAL = ROOT / "5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md"
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
README = ROOT / "1_Code/DDM_Core/README.md"


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def write(p: Path, lines: list[str]) -> None:
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def one(lines: list[str], needle: str) -> int:
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, f"锚点命中 {len(hits)} 次（应为 1）：{needle[:70]}"
    return hits[0]


def startswith_one(lines: list[str], prefix: str) -> int:
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(hits) == 1, f"前缀命中 {len(hits)} 次（应为 1）：{prefix[:70]}"
    return hits[0]


STATUS_NEW = (
    "> 状态：**✅ 定稿（2026-10-18 签批：研究者 蔡振辛、导师 hcp）**。"
    "签批后设计冻结；任何改动须在 §9 新增变更行并重签。"
)
PHASE_NEW = (
    "> 阶段状态：Stage 0 ✅、Stage 1 🟢（六张表已齐，程序 v4.9）、Stage 2 ✅、Stage 3 ✅、Stage 4 ✅、"
    "**Stage 5 ✅ 定稿（2026-10-18 签批）**、Stage 6 🟡（工具链就绪，只等 v4.9 真被试）、"
    "Stage 7 ⚪（待正式采集）、Stage 8/9 ✅（分析线已建好，待真数据）。"
)

S57 = [
    "### ⑦ 效应量与证据强度：三层分工（2026-10-18 新增）",
    "",
    "用户问「效应量怎么验证：G\\*Power 还是 BF，还是边收数据边算 BF」。**三者不是备选关系，各自负责一层**；",
    "混用（例如用 ANOVA 的 `f` 定样本量、再用 BF 宣称参数假设成立）会在论文里留下能被一句话指出来的口径错配。",
    "",
    "| 层 | 问题 | 工具 | 本设计的落点 | 不能做的 |",
    "|---|---|---|---|---|",
    "| **事前（行为层）** | 要多少人才能以 80% 把握检出**人层汇总指标**（SPE 分数 / 正确率 / RT 中位）的组间差异？ | G\\*Power（非中心 F 敏感性分析） | **4 组 × 40 = 160 人 ⇒ `f_min = 0.264`（η² = 6.5%）**；192 人 ⇒ 0.241（5.5%） | 不能替代参数层效力；它不认识 DDM |",
    "| **事前（参数层）** | 组层参数能不能估、估多准？ | **CRLB / FIM + 模拟恢复**（§5 ①–⑥） | `beta_P` ~40 人/组；ρ 组层效力 **95.3% / 99.9%**；`beta_ST` 在 n=40/组 下 `z = 1.38 < 1.96` ⇒ 降级（§7 ②） | 不能用于「行为上显著」这类人层命题 |",
    "| **终局（参数层）** | 数据支持 `H₁`（`beta_P ≠ 0`）还是 `H₀`？多强？ | **Savage–Dickey 密度比**（用已有后验抽样 + 先验密度；**不做桥采样**） | 核心假设报「SD-BF + 先验敏感性」 | 不能把 PSIS-LOO 的权重写成精确 BF |",
    "| **终局（模型层）** | M-T1 与其他备选的预测优劣 | **PSIS-LOO**（已建，§4） | 模型比较按 LOO 报 | LOO → BF 只能走 pseudo-BMA，属近似 |",
    "| **采集期** | 要不要现在停？ | 固定节点 futility（预注册） | **不做**顺序 BF 停收（§7 ⑩） | 不允许未预注册的「BF > 10 就停」 |",
    "",
    "**G\\*Power 读数的来历（可复算）**：单因素 ANOVA、α = 0.05、power = 0.80，解非中心 F 得 `f_min`：",
    "`k = 4, n = 40 ⇒ f = 0.264`（η² = `f²/(1+f²)` = 0.065）；`k = 4, n = 48 ⇒ 0.241`；`k = 4, n = 30 ⇒ 0.307`。",
    "交叉核对：`k = 6, n = 11`（总 66，≈ 旧报告 65 人）⇒ `f = 0.461`，旧报告 G\\*Power 给 **0.465**（差 0.9%）。",
    "",
    "⚠️ **为什么不用 G\\*Power 决定 N**：现成反例就是 §7 ② 的 `beta_ST` —— 它在行为层可以「显著」，",
    "但 CRLB 与 MLE 两个口径一致地说它在 D4 里**没有信息**（SE/真值 11.7× 与 5.1×）。行为层的 `f` 大",
    "并不蕴含参数可估；**样本量的主依据只能是参数层**。",
    "",
]

DISCIPLINE = [
    "- [ ] G\\*Power 只作**行为层**敏感性分析报告（`f_min = 0.264`，η² = 6.5%，N = 160），并注明它**不驱动**样本量。",
    "- [ ] 参数层证据报 **Savage–Dickey BF + 先验敏感性**；**不得**把 PSIS-LOO 的 pseudo-BMA 权重写成「贝叶斯因子」。",
]

ITEM10 = (
    "| **⑩** | **要不要「边收数据边算 BF」来决定停收？** | 顺序监控会改变**决策**的错误率特性（BF 作为似然比有一定容忍性，但「BF>10 就停」是一个决策过程）；"
    "层级 DDM 每次重拟合是 D72 记载的「N=160 数十小时批处理」量级；本设计的信息主要来自被试内 576 试次，"
    "多收 1 人只加 1/40 的组层信息 | **不做**未预注册的顺序 BF 停收。若导师坚持：先跑 **BFDA 模拟**"
    "（用现成生成器模拟「固定 N + BF 阈值 10/3」的错误率与预期样本量，Schönbrodt & Wagenmakers 2018），"
    "并在预注册里写明只做**固定节点 futility**（每 10 人/组看一次，只许以「明显达不到」停，不许提前宣称成功） |"
)

V27 = (
    "| **v2.7（定稿 + 效应量三层方案 → D97）** | 2026-10-18 | 研究者 **蔡振辛**、导师 **hcp** 签署 §8 签批表 ⇒ 状态由 🟡 待签批改为 **✅ 定稿并冻结**；"
    "新增 **§5.7 效应量与证据强度三层分工**（行为层 G\\*Power `f_min = 0.264` / 参数层 CRLB+模拟 / 终局 SD-BF + PSIS-LOO / 采集期只做 futility），"
    "并在 §6 加两条报告纪律；§7 新增第 **⑩** 项：裁定**不做**未预注册的顺序 BF 停收。 |"
)

D97 = (
    "| **D97** | 2026-10-18 | ✅ **Stage 5 定稿：签批完成，并补上「效应量怎么验证」的三层方案**。"
    "① 用户已填 §8 签批表（研究者 蔡振辛、导师 hcp、2026.10.18）⇒ `正式采集_候选设计_v2_定稿.md` 由 🟡 待签批改为 **✅ 定稿并冻结**；"
    "② 用户在签批后补问「效应量用 G\\*Power 还是 BF、要不要边收边算 BF」，答案不是二选一而是**分层**："
    "行为层用 G\\*Power（**新算：4 组 × 40 ⇒ `f_min = 0.264`、η² = 6.5%；192 人 ⇒ 0.241**；"
    "并用旧报告 6 组 × 66 人的 `f_min = 0.461` 对上其 G\\*Power 的 0.465，差 0.9% 证明方法一致）、"
    "参数层用已建的 CRLB/模拟效力（ρ 95.3%/99.9%）、终局参数证据用 **Savage–Dickey 密度比**（不用桥采样，因为它对层级 DDM 又贵又脆）、"
    "模型层仍用 PSIS-LOO（**LOO→BF 只能走 pseudo-BMA，属近似，不得写成精确 BF**）；"
    "③ **裁定不做未预注册的顺序 BF 停收**：顺序监控改变的是**决策**的错误率特性，而 BF 的容忍性说的是「证据」不是「停止规则」；"
    "且层级 DDM 每次重拟合是 D72 的「数十小时」量级、多收 1 人只加 1/40 组层信息。替代方案 = 预注册的**固定节点 futility**，"
    "若导师坚持顺序方案则先跑 **BFDA 模拟**（Schönbrodt & Wagenmakers 2018）定错误率与预期样本量；"
    "④ 为什么 G\\*Power 不能定 N：`beta_ST` 就是现成反例——行为层可以「显著」，但 CRLB 与 MLE 一致指向它在 D4 里没有信息（SE/真值 11.7× 与 5.1×）；"
    "⑤ 落地件：`正式采集_候选设计_v2_定稿.md`（§5.7 + §6 两条纪律 + §7 ⑩ + §9 v2.7，**354 → 366 行**）+ 主计划 D97 行 + README §8.68。"
    " | `5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md`（**v2.7 定稿**）+ `1_Code/DDM_Core/_scratch/_apply_d97_docs.py` + README §8.68 "
    "| **(1)** 定稿已冻结，正式采集按此执行；**(2)** 不再有需要你拍板的设计问题；"
    "**(3)** 若导师要保留顺序 BF，回来只需一句话，我补 BFDA 模拟脚本 |"
)

D97_PROGRESS = (
    "| 2026-10-18 | **5（定稿签批 + 效应量三层方案 → D97）** | 用户签批（蔡振辛 / 导师 hcp）；补问「效应量怎么验证」⇒ 落成**分层方案**："
    "行为层 G\\*Power（4×40 ⇒ `f_min = 0.264`、η² = 6.5%）、参数层 CRLB/模拟（ρ 95.3%/99.9%）、终局参数证据用 Savage–Dickey BF、"
    "模型层用 PSIS-LOO；并**裁定不做未预注册的顺序 BF 停收**（改固定节点 futility，必要时先跑 BFDA 模拟）。"
    "定稿文档 354 → 366 行。 | `5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md`（v2.7 定稿）+ `_scratch/_apply_d97_docs.py` | 定稿冻结；下一件是 Stage 6 真被试 |"
)

D97_CHANGELOG = (
    "| 2026-10-18 | **新增 D97（Stage 5 定稿 + 效应量三层方案）**：`正式采集_候选设计_v2_定稿.md` 升 **v2.7 定稿**（签批：蔡振辛 / hcp），"
    "新增 §5.7（G\\*Power `f_min = 0.264` / CRLB+模拟 / SD-BF / PSIS-LOO / futility 五层分工）、§6 两条报告纪律、§7 ⑩（不做顺序 BF 停收） |"
)

D97_EVIDENCE = (
    "| `5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md`（**v2.7 定稿**，366 行，含 §5.7 + §7 ⑩） + "
    "`1_Code/Python_for_Check/Basic_Hypothesis/SPE_BF_Analysis_Report.md`（G\\*Power 0.465 的复算对照） | "
    "**D97**：签批完成 + 效应量验证的分层方案（行为层 G\\*Power / 参数层 CRLB / 终局 SD-BF / 模型层 LOO） |"
)

README_868 = [
    "### 8.68 效应量验证的分层：G*Power 只管行为层，参数层靠 CRLB，终局靠 Savage–Dickey（D97，2026-10-18）",
    "",
    "- **触发**：Stage 5 定稿签批后，用户问「这个效应量要怎么验证，用 G*Power 还是 BF，还是边收数据边算 BF」。",
    "- **结论**：三者不是备选，各管一层。行为层（人层汇总指标）用 G*Power 敏感性分析；参数层用 CRLB/FIM + 模拟恢复；",
    "  终局参数证据用 **Savage–Dickey 密度比**（从已有后验抽样算，不做桥采样）；模型层仍用 PSIS-LOO（`LOO → BF` 只能 pseudo-BMA）。",
    "- **新算的数**：4 组 × 40（N=160）单因素 ANOVA、80% power ⇒ `f_min = 0.264`（η² = 6.5%）；192 人 ⇒ 0.241。",
    "  方法自检：6 组 × 66 人 ⇒ 0.461，对上旧报告 G*Power 的 0.465（差 0.9%）。",
    "- **为什么 G*Power 不能定 N**：`beta_ST` 就是反例——行为层可以「显著」，CRLB 与 MLE 却一致说它在 D4 里没有信息（SE/真值 11.7× 与 5.1×）。",
    "- **裁定**：不做未预注册的顺序 BF 停收（改变的是决策的错误率，而 BF 的容忍性说的是证据；且层级重拟合是数十小时量级）；",
    "  替代 = 预注册的固定节点 futility；必要时先跑 BFDA 模拟。落点：定稿文档 §5.7 / §6 两条纪律 / §7 ⑩。",
    "",
]

README_81 = (
    "| 81 | ✅ **效应量验证分三层：G\\*Power 只管行为层，参数层靠 CRLB，终局靠 Savage–Dickey（D97，§8.68）** | "
    "4 组 × 40 ⇒ `f_min = 0.264`（η² = 6.5%）；`beta_ST` 是「行为显著但参数不可估」的反例。"
    "**尚未做**：Savage–Dickey BF 与 BFDA 模拟脚本**都还没写**（当前只有后验抽样与 PSIS-LOO）；"
    "定稿文档里的 `f_min` 是本次用非中心 F 复算，未用 G*Power 软件本体 |"
)


def main() -> None:
    # ---------- 定稿文档 ----------
    a = read(FINAL)
    assert "✅ 定稿" not in "\n".join(a[:8]), "头部已是定稿"

    i = one(a, "> 状态：**🟡 待签批（阻塞已解除）**")
    a[i] = STATUS_NEW
    i = one(a, "> 阶段状态：Stage 0 ✅")
    a[i] = PHASE_NEW

    i = startswith_one(a, "## 6. 报告纪律清单")
    a[i:i] = S57

    i = one(a, "引用 9 设计的 Fisher 信息/名次数值时**必须注明参数集")
    a[i + 1:i + 1] = DISCIPLINE

    i = one(a, "| **⑨** | ✅ **是否新增「无掩蔽」对照？已裁定：不加（D91")
    a.insert(i + 1, ITEM10)

    i = one(a, "| **v2.6（掩蔽因子取舍 → D91）**")
    a.insert(i + 1, V27)
    write(FINAL, a)
    print(f"[ok] 定稿：{len(a)} 行")

    # ---------- 主计划 ----------
    p = read(PLAN)
    i = startswith_one(p, "| **D96** |")
    p.insert(i + 1, D97)

    i = one(p, "🟡 进行中（**分析线已收口，只待签批**）")
    p[i] = p[i].replace("🟡 进行中（**分析线已收口，只待签批**）",
                        "✅ 定稿（2026-10-18 签批：蔡振辛 / hcp）")

    i = one(p, "### Stage 5 ｜模型恢复 + 最优设计定稿（我 → 一起）")
    assert p[i].endswith("（我 → 一起）")
    p[i] = p[i] + "✅ 2026-10-18 定稿"

    i = startswith_one(p, "| 2026-10-18 | **6（Pilot 达标报告器 → D96）** |")
    p.insert(i + 1, D97_PROGRESS)

    i = one(p, "**新增 D96（Pilot 达标报告器）**")
    p.insert(i + 1, D97_CHANGELOG)

    i = one(p, "`1_Code/Experiment/stage6_report.py`（**新建**，D96，221 行）")
    p.insert(i + 1, D97_EVIDENCE)

    write(PLAN, p)
    print(f"[ok] 主计划：{len(p)} 行")

    # ---------- README ----------
    r = read(README)
    i = startswith_one(r, "## 9. 尚未做")
    r[i:i] = README_868
    i = startswith_one(r, "| 80 | ✅ **Pilot 达标报告器")
    r.insert(i + 1, README_81)
    write(README, r)
    print(f"[ok] README：{len(r)} 行")


if __name__ == "__main__":
    main()
