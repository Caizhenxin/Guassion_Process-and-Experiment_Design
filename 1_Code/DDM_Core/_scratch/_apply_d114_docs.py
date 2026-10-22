"""D114 落纸：SPE 位点敏感性分析（诊断 + fig8 + 判别规则）。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MAIN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RME = ROOT / "1_Code" / "DDM_Core" / "README.md"

DECISION = (
    "| **D114** | 2026-10-24 | **SPE 该建模在哪一层：三种位点的敏感性分析（并回答「模型是否失效」）**。"
    "用户质疑「自我/他人的 RT 密度区分不开，SPE 机制是不是没起作用」。诊断结论：机制**在起作用**——"
    "真值漂移差 Δ`d_stim` = **0.320**、正确率差 **+8.0 pp**（16 人配对 95%CI [+0.06, +0.09]）、"
    "RT 中位差 **+13.6 ms**（CI [+0.5, +26.7]），与解析预期（+7.7 pp / +50 ms）方向一致；"
    "密度图看不出是**表达问题**：位移只占 RT 分布宽度（SD≈289 ms）的 **4–5%**，肉眼不可分辨。"
    "但暴露出一个真问题：`ρ` 把掩蔽后的自我/他人漂移差同样乘掉 20% ⇒ **两阶段模型里 RT 侧的 SPE 被二次衰减**"
    "（M-T1 按 W 为 +20.5/+24.7/+9.3 ms，非单调；M-T3 无掩蔽则 +18.6/+32.1/+43.3 ms，单调放大）。"
    "新增 `1_Code/Experiment/spe_locus.py`：同一群人、同一真值，只改 SPE 的落点（共同随机数配对），"
    "得到**四组可区分签名**（ΔRT 分位斜率 = p90−p10，Δ正确率）：漂移 23 ms / +0.073；"
    "边界 73 ms / **−0.011**（更快但更易错）；非决策时间 **0 ms** / 0.000（整体平移 20 ms，正确率不变）；"
    "漂移+非决策时间 21 ms / +0.043。据此写进方法章的**判别规则**：① 正 Δacc + 陡斜率 ⇒ 漂移型；"
    "② Δacc ≈ 0 + 斜率 ≈ 0 + RT 整体平移 ⇒ t0 型；③ Δacc < 0 ⇒ 边界型。"
    "**处置**：主模型保留漂移型（四种里唯一能同时给出「更快 + 更准」），但结果章必须同时报"
    "「ΔRT 的分位斜率」而不只报中位差；若真实数据呈「均匀平移 + 无正确率差」，则改 t0 型并重跑。 | "
    "用户 2026-10-24：「我们的模型是否有问题，自我他人的 RT 密度分布好像区分不开，"
    "SPE 的计算机制不就没发生作用吗」 | "
    "`1_Code/Experiment/spe_locus.py`（**新建**）+ `gen_viz.plot_rt_density`（加中位虚线与「位移占宽度」标注）+ "
    "`2_Data/Generate_Data/_compare/fig8_spe_locus.png` + `spe_locus.csv` + `spe_locus_meta.json` |"
)

PROGRESS = (
    "| 2026-10-24 | **12（SPE 位点诊断 → D114）** | **查清了**：SPE 机制没有失效（Δ漂移 0.32 / Δ正确率 +8 pp / "
    "ΔRT 中位 +13.6 ms，三者都显著且与解析预期同向），密度图看不出是「位移仅占分布宽度 4–5%」的表达问题；"
    "同时暴露 `ρ` 会把 RT 侧 SPE 二次衰减。新增三+一种位点对照图（fig8）与判别规则，写入方法章。"
    "未做：真实数据到手后按判别规则定模型归属。 | `1_Code/Experiment/spe_locus.py`；"
    "`2_Data/Generate_Data/_compare/fig8_spe_locus.png` | — |"
)

CHANGELOG = (
    "| 2026-10-24 | **新增 D114（SPE 位点敏感性分析）**：`spe_locus.py`（drift / boundary / t0 / 混合四组，"
    "共同随机数配对）；`fig1` 加中位虚线与位移占比标注；判别规则（Δacc × ΔRT 分位斜率）写入方法章。 |"
)

EVIDENCE = (
    "| `1_Code/Experiment/spe_locus.py` + `2_Data/Generate_Data/_compare/fig8_spe_locus.png`（四组签名）+ "
    "`_compare/spe_locus.csv` + `spe_locus_meta.json` | D114 证据：同一真值下四种 SPE 落点给出四组可区分签名；"
    "「更快 + 更准」只有漂移型能同时满足，边界型必然牺牲正确率、t0 型不改变正确率 |"
)

README_ROW = (
    "| 95 | ✅ **SPE 位点敏感性分析（D114）** | 用户质疑「自我 vs 他人 RT 密度区分不开 ⇒ SPE 机制失效」。诊断："
    "Δ`d_stim` 0.320、Δacc +8.0 pp（CI [+0.06,+0.09]）、ΔRT 中位 +13.6 ms（CI [+0.5,+26.7]）——机制在起作用；"
    "密度图看不出是因为位移仅占分布宽度 4–5%。真问题：`ρ` 把掩蔽后的漂移差同样乘掉 20%，M-T1 的 RT 侧 SPE 按 W 为 "
    "+20.5/+24.7/+9.3 ms（非单调），而 M-T3 无掩蔽为 +18.6/+32.1/+43.3 ms（单调放大）。新增 "
    "`1_Code/Experiment/spe_locus.py`（drift / boundary / t0 / 混合，共同随机数配对）：ΔRT 分位斜率 23 / 73 / 0 / 21 ms，"
    "Δacc +0.073 / −0.011 / 0.000 / +0.043 ⇒ 判别规则「正 Δacc + 陡斜率 = 漂移型」「均匀平移 + Δacc≈0 = t0 型」"
    "「Δacc<0 = 边界型」，图见 `2_Data/Generate_Data/_compare/fig8_spe_locus.png` |"
)


def insert_after(lines: list[str], anchor: str, new: str, expect_pipes: int) -> int:
    hits = [i for i, s in enumerate(lines) if s.startswith(anchor)]
    assert len(hits) == 1, f"锚点 {anchor[:26]} 命中 {len(hits)} 次"
    i = hits[0]
    assert lines[i].count("|") == expect_pipes, (
        f"锚点列数 {lines[i].count('|')} vs 期望 {expect_pipes} @ {i+1}")
    assert new.count("|") == expect_pipes, f"新行列数 {new.count('|')} vs {expect_pipes}"
    lines.insert(i + 1, new)
    return i + 1


def main() -> int:
    lines = MAIN.read_text(encoding="utf-8").splitlines()
    n0 = len(lines)
    assert not any(s.startswith("| **D114** |") for s in lines), "D114 已存在，先人工检查"
    insert_after(lines, "| **D113** |", DECISION, 6)
    insert_after(lines, "| 2026-10-23 | **11（三模型生成器", PROGRESS, 6)
    insert_after(lines, "| 2026-10-23 | **新增 D113", CHANGELOG, 3)
    insert_after(lines, "| `1_Code/DDM_Core/ramp.py` + `1_Code/Experiment/gen_model_data.py`",
                 EVIDENCE, 3)
    MAIN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"主计划 {n0} → {len(lines)} 行")

    rl = RME.read_text(encoding="utf-8").splitlines()
    r0 = len(rl)
    assert not any(s.startswith("| 95 |") for s in rl), "README 已有 95"
    insert_after(rl, "| 94 |", README_ROW, 4)
    RME.write_text("\n".join(rl) + "\n", encoding="utf-8", newline="\n")
    print(f"README {r0} → {len(rl)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
