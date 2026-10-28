"""把 D134（SPE 真实分布基准）登记进主计划四处：决策表 / 进度行 / 变更日志 / 证据表。"""
from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")

DEC = (
    "| **D134** | 2026-10-27 | **SPE 真实分布基准：文献 ΔRT 中位 +75.9 ms（95% 为正），我们生成模型只到 +8 ms（P7）**。"
    "① 三源统一读数层（`_scratch/_spe_baseline_load.py`）：文献库 92 个逻辑数据集 → 87 个可用（8,634 个 被试×身份 单元），"
    "来源 `SPE_Database/1_Data/**/*_Clean*.csv`，口径沿用 `11_Practice-Effect/practice_effect_workflow.py`"
    "（matching 试次、ACC==1、RT 150–3000 ms、MAD 3.5 修剪、每单元 ≥5 试次、身份取 `Shape_Standardized_Identity`）。"
    "② 文献 Stranger 对比 71 个可算数据集：ΔRT 均值 **79.0**、中位 **75.9**、IQR **45.8–103.2**、5–95% **0.4–192.1**、"
    "**95.8% 为正**；ΔACC 中位 **0.072**、IQR 0.029–0.124。"
    "③ 身份梯度（数据集级中位）：Celebrity 77.7(3) / Stranger 75.9(72) / NonPerson 60.0(9) / **Close 42.8(50)** / Acquaintance 15.3(2) ⇒ "
    "**本库 Close 的 SPE 反而小于 Stranger**，四层梯度只在 self↔stranger、self↔close 两格有足够基准。"
    "④ 本项目位置：新设计 17 人 ΔRT **+33（P18）**、ΔACC **+0.067（P46）**；`TRUTH_LIN` ΔRT **+8（P7）**、ΔACC +0.054（P39）；"
    "旧 v2.4 +221（P99）/ +0.258（P100）⇒ **实测偏小但正常，原版生成模型几乎在分布外，旧版在另一极端**。"
    "⑤ 旧 87 人（仅展示）：ΔRT 随反应窗 W 单调上升（W=300 → −3.3 ms、1500 → **+62.6 ms**），超时率 86%→13% ⇒ "
    "**短 W 会把 SPE 压掉**，旧数据负值应读作「该 W 下测不出」而非「无 SPE」。"
    "⑥ 练习轴（13 个数据集 / 17 个 数据集×水平）：5 个双水平里 4 个 practice > main（Hu_YQ Exp1 35.1→68.3），样本太薄只作描述。"
    "⑦ 结论：**缺的是 RT 通道幅度，不是正确率通道**（文献 ΔRT 比 ΔACC 高一档，模型 `beta_S` 提 ACC 快、提 RT 慢，D132 已证两通道不可解耦）。"
    "可选补法按代价排序：给 `t0` 加自我项（`dt0_S`）> 主张收窄到 ΔACC 与分位形状 > 加身份距离项。"
    "**未做**：`Hu_YQ_2026_ChinaSciData` 的 Exp3 多天轨迹（`1_Data` 里该文件已缺失，历史产物在 `11_Practice-Effect/Output/01_HuYQ_Exp3/`）。"
    "产物：`5_Reference/03_论文写作/SPE_真实分布_基准_20261027.md`、`3_Figures/_real_check/fig_spe_baseline.png`、"
    "`2_Data/Real_Data/_spe_baseline/*.csv`。 |"
)

PROG = (
    "| 2026-10-27 | **31（SPE 真实分布基准 → D134）** | 文献 87 数据集统一读数：Stranger ΔRT 中位 75.9 ms（IQR 45.8–103.2，95.8% 为正）、"
    "ΔACC 0.072；我们 17 人 +33 ms（P18）/+0.067（P46）；`TRUTH_LIN` +8 ms（P7）⇒ 差的是 RT 通道幅度。"
    "身份梯度 Close 42.8 < Stranger 75.9，四层里只有两格有足够基准。旧 87 人 ΔRT 随 W 单调（−3.3 → +62.6 ms，超时 86% → 13%）。 |"
)

CHG = (
    "| 2026-10-27 | **新增 D134（SPE 真实分布基准：文献 87 数据集 vs 本项目）**："
    "ΔRT 中位 75.9 ms（95.8% 为正）、ΔACC 0.072；我们 17 人在 P18/P46，`TRUTH_LIN` RT 侧 P7、ACC 侧 P39；"
    "旧 87 人证明 ΔRT 随 W 单调（短 W 压掉 SPE）。 |"
)

EVI = (
    "| `5_Reference/03_论文写作/SPE_真实分布_基准_20261027.md` + `_scratch/_spe_baseline_{load,merge,fig}.py` | "
    "D134 证据：① 文献 71 个数据集 ΔRT 分位表（均值 79.0 / 中位 75.9 / IQR 45.8–103.2 / 5–95% 0.4–192.1 / 正号率 95.8%）；"
    "② 身份梯度表（Celebrity 77.7、Stranger 75.9、NonPerson 60.0、Close 42.8、Acquaintance 15.3）；"
    "③ 本项目位置表（17 人 P18/P46、TRUTH_LIN P7/P39、旧 v2.4 P99/P100）；"
    "④ 旧 87 人 8 组设计表（ΔRT −3.3…+62.6 ms、超时 85.8%…12.9%）；"
    "⑤ `2_Data/Real_Data/_spe_baseline/{spe_subject_level_all,spe_level_summary_all,spe_position}.csv` + "
    "`3_Figures/_real_check/fig_spe_baseline.png`。 |"
)


def main() -> None:
    lines = P.read_text(encoding="utf-8").splitlines()
    n0 = len(lines)

    def find(pred, what):
        idx = [i for i, l in enumerate(lines) if pred(l)]
        assert len(idx) == 1, f"{what} 匹配 {len(idx)} 处"
        return idx[0]

    # 1 决策表：插在 D133 之前（表格按时间倒序）
    i = find(lambda l: l.startswith("| **D133** |"), "决策表 D133")
    lines.insert(i, DEC)
    # 2 进度行：插在「30（形状族 L1…）」之后
    j = find(lambda l: "**30（形状族 L1：不可裁定 → D133）**" in l, "进度行 30")
    lines.insert(j + 1, PROG)
    # 3 变更日志：插在 D133 那行之后
    k = find(lambda l: l.startswith("| 2026-10-26 | **新增 D133（形状族预登记 + L1）**"), "变更日志 D133")
    lines.insert(k + 1, CHG)
    # 4 证据表：追加在末尾（D133 证据是最后一行）
    m = find(lambda l: "| D133 证据：" in l, "证据表 D133")
    assert m == len(lines) - 1, f"D133 证据行不是最后一行（{m} vs {len(lines) - 1}）"
    lines.append(EVI)

    P.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"主计划 {n0} → {len(lines)} 行")


if __name__ == "__main__":
    main()
