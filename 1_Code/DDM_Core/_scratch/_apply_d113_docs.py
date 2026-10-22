"""D113 落纸：三模型生成器 + 六张图 + 三个 notebook。

严格按锚点行的竖线数断言（历史上踩过：主计划进度表 5 列、变更日志 2 列、证据表 2 列、
README §9 3 列）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MAIN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RME = ROOT / "1_Code" / "DDM_Core" / "README.md"

DECISION = (
    "| **D113** | 2026-10-23 | **三条模型各自一套数据生成器 + 六张图 + 可执行 notebook**。"
    "新建 `1_Code/DDM_Core/ramp.py`（M-T2 斜坡：`d(t)=d_stim(1−e^{−t/τ_T})`，掩蔽后 `ρ·d_stim·(1−e^{−T/τ_T})`，"
    "Euler 实现、与 `twophase.simulate_euler_subject` 同接口、**无似然**）与 "
    "`1_Code/Experiment/gen_model_data.py`（`GEN_TRUTH` 独立标定口径，与 `mapping.TRUTH_EXP` 分开；"
    "4 组 × 4 人 × 576 试次 = 9216 行/模型；产物 `trials_long.csv`/`subjects.csv`/`cells.csv`/`meta.json`，"
    "逐试次含真值潜变量）、`1_Code/Experiment/gen_viz.py`（图 1 RT 分布 / 图 2 分位曲线 / 图 3 正确率-遗漏率 / "
    "图 4 CRF / 图 5 delta 图 / 图 6 机制图 + 跨模型 `fig7_model_compare`）。数据与图落 "
    "`2_Data/Generate_Data/{M-T1,M-T2,M-T3}/`，三个 notebook 落 `1_Code/Python_for_Generate/`。"
    "口径要点：① `drift_sd=0.25` 对数正态逐试次漂移变异（与真实数据的 RT 尾部对齐）；"
    "② CRF 默认**在 T×W×身份内部**分 RT 五分位箱（不在条件内分箱会把长 RT 与低漂移条件混在一起，"
    "第一版就踩了这个坑）；③ 本模拟的 CRF 是**下降**的（快试次更准），真实数据上升来自边界波动/注意失效，"
    "**不用模拟图硬凑真实形状**，差异写进方法章。三模型自检各 5/5 全过（M-T1 acc 0.765 / M-T2 0.666 / M-T3 0.777），"
    "notebook 实跑 23 单元 0 错误。 | 用户 2026-10-23：「我记得我有 3 个 Model，那我是不是应该有三个数据生成器，"
    "对应有 3 个 `.ipynb` 文件」+「希望将生成的 csv 放到对应文件夹里」+「把生成数据可视化，RT distribution、"
    "按自我/他人分条件、CRF」；此前 M-T2 在全仓库只有 `twophase.py:13` 一行注释，属于「论文写了三条模型、代码只有两条」。 | "
    "`1_Code/DDM_Core/ramp.py`（**新建**）+ `1_Code/Experiment/gen_model_data.py`（**新建**）+ "
    "`1_Code/Experiment/gen_viz.py`（**新建**）+ `1_Code/Python_for_Generate/M-T{1,2,3}_*.ipynb`（**新建 3 个**，"
    "`_scratch/_build_model_notebooks.py` 生成）+ `2_Data/Generate_Data/README.md`（**新建**，数据字典 + 读图指引） |"
)

PROGRESS = (
    "| 2026-10-23 | **11（三模型生成器 → D113）** | **补齐了**：M-T2 有生成器（`ramp.py`），三条模型各一套 "
    "576 试次/人的模拟数据（`2_Data/Generate_Data/`）与六张论文级图，三个 notebook 实跑通过、自检 5/5。"
    "未做：M-T2 无似然 ⇒ 不能进模型比较（只能作机制对照），已写进 `2_Data/Generate_Data/README.md` 与局限性。 | "
    "`1_Code/Experiment/gen_model_data.py`；`gen_viz.py`；`2_Data/Generate_Data/` | — |"
)

CHANGELOG = (
    "| 2026-10-23 | **新增 D113（三模型生成器 + 六图 + 三 notebook）**：`ramp.py`（M-T2）、`gen_model_data.py`"
    "（`GEN_TRUTH` 口径、9216 行/模型）、`gen_viz.py`（图 1–7）、`2_Data/Generate_Data/README.md`；"
    "CRF 改在 T×W 内分箱；三 notebook 实跑 0 错误、自检各 5/5。 |"
)

EVIDENCE = (
    "| `1_Code/DDM_Core/ramp.py` + `1_Code/Experiment/gen_model_data.py` + `gen_viz.py` + "
    "`1_Code/Python_for_Generate/M-T{1,2,3}_*.ipynb` + `2_Data/Generate_Data/`（3 模型 × 9216 行） | "
    "D113 证据：三条模型都能生成结构合理的逐试次数据；六张图各自带「什么算不对」的判读阈值；"
    "M-T2 的「无似然」状态被显式记录而非假装能比较 |"
)

README_ROW = (
    "| 94 | ✅ **三模型生成器与图（D113）** | `1_Code/DDM_Core/ramp.py`（M-T2 斜坡，**无似然**）、"
    "`1_Code/Experiment/gen_model_data.py`（`GEN_TRUTH` 独立口径，4 组×4 人×576 试次=9216 行/模型，产物 "
    "`trials_long.csv`/`subjects.csv`/`cells.csv`/`meta.json`）、`1_Code/Experiment/gen_viz.py`"
    "（图 1–6 + 跨模型 `fig7_model_compare`）；数据落 `2_Data/Generate_Data/{M-T1,M-T2,M-T3}/`，"
    "notebook 落 `1_Code/Python_for_Generate/`（`_scratch/_build_model_notebooks.py` 生成，实跑 23 单元 0 错误、"
    "自检 5/5）。CRF 在 T×W×身份**内部**分箱；本模拟 CRF 下降（快试次更准）是模型边界，不硬凑真实形状。 | "
    "用户 2026-10-23：「我有 3 个 Model，是不是应该有 3 个数据生成器 + 3 个 `.ipynb`」+「生成的 CSV 放到对应文件夹」+"
    "「把生成数据可视化（RT distribution、按自我/他人分条件、CRF）」 |"
)


def insert_after(lines: list[str], anchor: str, new: str, expect_pipes: int) -> int:
    hits = [i for i, s in enumerate(lines) if s.startswith(anchor)]
    assert len(hits) == 1, f"锚点 {anchor[:30]} 命中 {len(hits)} 次"
    i = hits[0]
    assert lines[i].count("|") == expect_pipes, (
        f"锚点行列数不符：{lines[i].count('|')} vs 期望 {expect_pipes} @line {i + 1}")
    assert new.count("|") == expect_pipes, f"新行列数不符：{new.count('|')} vs {expect_pipes}"
    lines.insert(i + 1, new)
    return i + 1


def main() -> int:
    lines = MAIN.read_text(encoding="utf-8").splitlines()
    before = len(lines)
    # 决策表：D112 行之后
    insert_after(lines, "| **D112** |", DECISION, expect_pipes=6)
    # 变更日志（2 列）：插在 D112 的变更日志行之后
    i_log = insert_after(lines, "| 2026-10-21 | **新增 D112", CHANGELOG, expect_pipes=3)
    # 进度表（5 列）
    insert_after(lines, "| 2026-10-21 | **10（模型章自动化", PROGRESS, expect_pipes=6)
    # 证据表（2 列）：追加在证据区末尾（D112 证据行之后）
    insert_after(lines, "| `1_Code/Experiment/manuscript.py`（D112 扩写",
                 EVIDENCE, expect_pipes=3)
    MAIN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"主计划 {before} → {len(lines)} 行；变更日志插入行 {i_log + 1}")

    rl = RME.read_text(encoding="utf-8").splitlines()
    rb = len(rl)
    insert_after(rl, "| 93 |", README_ROW, expect_pipes=4)
    RME.write_text("\n".join(rl) + "\n", encoding="utf-8", newline="\n")
    print(f"README {rb} → {len(rl)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
