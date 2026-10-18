"""D101 落纸：论文结果章模板 + 自动填表（manuscript.py + build_blocks 抽取）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RD = ROOT / "1_Code" / "DDM_Core" / "README.md"
US = ROOT / "5_Reference" / "08_工作流" / "全流程一键跑通_使用说明.md"
RG = ROOT / "5_Reference" / "03_论文写作" / "结果节_生成流程_20261018.md"

D101_ROW = (
    "| **D101** | 2026-10-18 | **结果是跑通了，但「结果怎么进论文」还没有出口** ⇒ 新增论文结果章模板 + "
    "自动填表：`5_Reference/03_论文写作/论文_结果章_模板.md`（新第 9 章框架，7 节）由 "
    "`1_Code/Experiment/manuscript.py` 填表生成 `_pipeline/manuscript_draft.md`。"
    "**关键设计**：① 表与横幅只有一处渲染（把 `write_results_skeleton` 里的渲染抽成 "
    "`run_pipeline.build_blocks`，返回 `intake_table` / `model_block` / `param_block` 三块），"
    "骨架与草稿共用——D98 配对 SE、D99 闸门都是「两处各自渲染」漏的；② `s6_table` 从已有 "
    "`stage6_report.md` 的 `## 2.` 抽，不重算判据；③ `render()` 对模板里每个 `{{name}}` "
    "强制要求有块，缺一个即 `KeyError`（宁可炸，不许静默留空）；④ 含 `synth_truth.json` 时草稿"
    "顶部插合成数据警示条；⑤ 论述一律留 `【待写】`（首个草稿 130 行、10 处）。"
    "**章号待定**：插为第 9 章，原总讨论/结论后移为 10/11 章。"
    "自测 `check_run_pipeline.py` 9 → **11/11**（P7 四块表 + ⛔ 横幅 + 合成警示 + 无 `{{` 残留；"
    "P8 缺块必报错）。 | `1_Code/Experiment/manuscript.py`（**新建**，188 行）+ "
    "`1_Code/Experiment/run_pipeline.py`（367 → **420 行**：抽 `build_blocks`、加第 5 步、"
    "步号 `1/4…4/4` → `1/5…5/5`）+ `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，84 行）"
    "+ `1_Code/Experiment/exp_Check/check_run_pipeline.py`（191 → **223 行**） | 复核模板章节顺序与"
    "「本章不得进论文」的边界；真数据到位后按模板 `【待写】` 补论述 |"
)

PROGRESS_ROW = (
    "| 2026-10-18 | **6.5（结果进论文）** | 论文结果章模板 + `manuscript.py` 自动填表接进流水线第 5 步；"
    "`build_blocks` 抽出后骨架与草稿共用同一渲染；`check_run_pipeline.py` 11/11 | "
    "`1_Code/Experiment/manuscript.py`、`论文_结果章_模板.md`、`run_pipeline.py`（420 行） | "
    "读 `_pipeline/manuscript_draft.md` 的 10 处 `【待写】`，决定哪些要补实测数字 |"
)

CHANGELOG_ROW = (
    "| 2026-10-18 | **新增 D101（结果章模板 + 自动填表）**：`manuscript.py`（188 行）把 "
    "`build_blocks` 的三块表填进 `论文_结果章_模板.md`；流水线多一步 `[5/5] 论文草稿`；"
    "自测 9 → 11/11 |"
)

EVIDENCE_ROWS = [
    "| `1_Code/Experiment/manuscript.py`（**新建**，D101，188 行）：`load_template` / `table_under` / "
    "`render`（缺块即 `KeyError`）/ `synth_banner` / `load_truth` / `write_draft` / CLI |",
    "| `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，D101，84 行）：第 9 章框架 + 四个"
    "花括号占位 + 三张图的相对路径 |",
]

README_SECTION = """### 8.72 论文结果章模板与自动填表（D101）

`5_Reference/03_论文写作/论文_结果章_模板.md`（第 9 章框架、7 节）由 `1_Code/Experiment/manuscript.py` 填成 `_pipeline/manuscript_draft.md`，作为 `run_pipeline.py` 的第 5 步。

| 要点 | 做法 | 为什么 |
|---|---|---|
| 表格单一来源 | 把 `write_results_skeleton` 的渲染抽成 `run_pipeline.build_blocks`，返回 `intake_table` / `model_block` / `param_block` 三块，骨架与草稿共用 | D98 配对 SE、D99 闸门都是「两处各自渲染」漏的 |
| 判据不重算 | `s6_table` 从已有 `stage6_report.md` 的 `## 2.` 小节抽 | 判据只写在 `stage6_report.py` 一处（D94 教训） |
| 占位缺失即炸 | `render()` 对模板里每个 `{{name}}` 要求有块，缺一个抛 `KeyError` | 静默留空会让论文里出现空表 |
| 合成数据警示 | 数据目录含 `synth_truth.json` 时正文顶部插警示条 | 合成数字进正文是本项目最容易犯的错（D98） |
| 论述留槽 | 表与统计量自动填，论述一律 `【待写】`（首稿 10 处） | 数字可自动、解释不可自动 |
| DB 口径写进正文 | 9.5 明说区间是**被试间 SEM**；9.4 明说 SE 必须配对 | 读者不复现就等于没报 |

自测：`check_run_pipeline.py` **11/11**（P7 四块表 + ⛔ 横幅 + 合成警示 + 无 `{{` 残留；P8 缺块必报错）。
章号：模板写明「章号待定：插为第 9 章，原总讨论/结论后移为 10/11 章」——插入 `_v3_正文.md` 前需人工确认编号。

"""

README_ITEM = (
    "| 84 | ❌ **未做**：`论文_结果章_模板.md` 尚未真正插入 `5_Reference/03_论文写作/_v3_正文.md`"
    "（章号、上下章衔接、表号重编都要人工定）；且模板里的 `【待写】` 10 处没有真实数据可填 |\n"
)

US_TABLE_ROW = (
    "| 7 | `_pipeline/manuscript_draft.md` | 论文结果章的成品骨架（表已填、论述留 `【待写】`） | "
    "别把表号直接当定稿：按 `结果节_生成流程_20261018.md` §4 重编；合成数据的草稿不得进正文 |\n"
)
US_TOOL_ROW = (
    "| 5 | `1_Code/Experiment/manuscript.py` | 把 `build_blocks` 的三块表填进结果章模板（D101） |\n"
)
US_CMD_NOTE = (
    "第 5 步会额外产出 `manuscript_draft.md`（论文结果章草稿，表已填、论述留 `【待写】`）；"
    "若不想生成，用 `--skip-stage8` 跳过整个拟合段即可连带跳过它。\n"
)

RG_TABLE_ROW = (
    "| `_pipeline/manuscript_draft.md` | **结果章成品骨架**（第 9 章模板已填好表） | "
    "按本文 §4 重编表号；`【待写】` 处补论述；确认章号后再粘进 `_v3_正文.md` |\n"
)


def patch(path: Path, edits: list[tuple[str, str, int]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new, want in edits:
        c = text.count(old)
        assert c == want, f"{path.name}: 锚点命中 {c} 次（期望 {want}）：{old[:40]!r}"
        text = text.replace(old, new, 1) if want == 1 else text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def insert_after_line(path: Path, needle: str, lines: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    L = text.split("\n")
    idx = [i for i, x in enumerate(L) if x.startswith(needle)]
    assert len(idx) == 1, f"{path.name}: 行首锚点命中 {len(idx)} 个：{needle!r}"
    L[idx[0] + 1:idx[0] + 1] = lines
    path.write_text("\n".join(L), encoding="utf-8", newline="\n")


def main() -> int:
    # 主计划：决策行 / 进度行 / 变更日志 / 产出文件
    insert_after_line(MP, "| **D100** | 2026-10-18 |", [D101_ROW])
    insert_after_line(MP, "| 2026-10-18 | **D100（LOO 不可引用是样本量问题）** |", [PROGRESS_ROW])
    insert_after_line(MP, "| 2026-10-18 | **新增 D100（Pilot 规模的 LOO 不可引用）**", [CHANGELOG_ROW])

    tm = MP.read_text(encoding="utf-8")
    assert tm.endswith("\n")
    MP.write_text(tm + "\n".join(EVIDENCE_ROWS) + "\n", encoding="utf-8", newline="\n")

    # README：§8.72 + §9 第 84 项
    patch(RD, [("## 9. 尚未做", README_SECTION + "## 9. 尚未做", 1)])
    tr = RD.read_text(encoding="utf-8")
    assert tr.endswith("\n")
    RD.write_text(tr + README_ITEM, encoding="utf-8", newline="\n")

    # 使用说明：产物表 + 工具表 + 命令说明
    patch(US, [
        ("| 6 | `_pipeline/results_skeleton.md` |", "| 6 | `_pipeline/results_skeleton.md` |", 1),
        ("\n## 4. 每步调用的既有工具（不复制判据）", "\n" + US_TABLE_ROW + "\n## 4. 每步调用的既有工具（不复制判据）", 1),
        ("| 5 | `1_Code/Experiment/run_pipeline.py` | 编排、汇总、生成结果节骨架 |",
         "| 5 | `1_Code/Experiment/run_pipeline.py` | 编排、汇总、生成结果节骨架 |", 1),
        ("## 5. 换成真数据时唯一要改的东西", US_CMD_NOTE + "\n## 5. 换成真数据时唯一要改的东西", 1),
    ])
    tus = US.read_text(encoding="utf-8")
    assert "| 5 | `1_Code/Experiment/run_pipeline.py` |" in tus
    US.write_text(tus.replace(
        "| 5 | `1_Code/Experiment/run_pipeline.py` | 编排、汇总、生成结果节骨架 |",
        "| 5 | `1_Code/Experiment/run_pipeline.py` | 编排、汇总、生成结果节骨架（420 行） |\n"
        + US_TOOL_ROW.rstrip("\n"), 1), encoding="utf-8", newline="\n")

    # 结果章生成流程：产物表加一行
    patch(RG, [("| `_pipeline/results_skeleton.md` |",
                RG_TABLE_ROW + "| `_pipeline/results_skeleton.md` |", 1)])

    for p in (MP, RD, US, RG):
        print(f"[ok] {p.relative_to(ROOT)} : {len(p.read_text(encoding='utf-8').splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
