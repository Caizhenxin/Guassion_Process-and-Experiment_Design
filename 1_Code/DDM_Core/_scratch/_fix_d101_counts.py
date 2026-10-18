"""修 D101 落纸的三处口径：行数（188→154、420→416、84→92）与两处表格列数。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RD = ROOT / "1_Code" / "DDM_Core" / "README.md"
US = ROOT / "5_Reference" / "08_工作流" / "全流程一键跑通_使用说明.md"

EV_OLD = [
    "| `1_Code/Experiment/manuscript.py`（**新建**，D101，188 行）：`load_template` / `table_under` / "
    "`render`（缺块即 `KeyError`）/ `synth_banner` / `load_truth` / `write_draft` / CLI |",
    "| `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，D101，84 行）：第 9 章框架 + "
    "四个花括号占位 + 三张图的相对路径 |",
]
EV_NEW = [
    "| `1_Code/Experiment/manuscript.py`（**新建**，D101，154 行）：`load_template` / `table_under` / "
    "`render`（缺块即 `KeyError`）/ `synth_banner` / `load_truth` / `write_draft` / CLI | "
    "**D101 的一手证据（结果章自动填表）**：`render` 缺块即抛 `KeyError`；草稿 130 行、10 处 `【待写】`"
    "（2026-10-18，D101） |",
    "| `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，D101，92 行）：第 9 章框架、7 节、"
    "四个花括号占位、三张图相对路径 | 章号待定（插为第 9 章）；含 `synth_truth.json` 时草稿不得进正文"
    "（2026-10-18，D101） |",
]


def main() -> int:
    for p, subs in (
        (MP, [("，188 行）", "，154 行）"), ("（367 → **420 行**", "（367 → **416 行**"),
              ("（**新建**，84 行）", "（**新建**，92 行）")]),
        (RD, [("（188 行）", "（154 行）")]),
        (US, [("（420 行）", "（416 行）")]),
    ):
        t = p.read_text(encoding="utf-8")
        for old, new in subs:
            c = t.count(old)
            if c == 0:
                print(f"  {p.name}: {old!r} 不在（跳过）")
                continue
            t = t.replace(old, new)
            print(f"  {p.name}: {old!r} -> {new!r} × {c}")
        p.write_text(t, encoding="utf-8", newline="\n")

    tm = MP.read_text(encoding="utf-8")
    for old, new in zip(EV_OLD, EV_NEW):
        assert tm.count(old) == 1, f"证据行锚点未命中：{old[:40]!r}"
        tm = tm.replace(old, new, 1)
    MP.write_text(tm, encoding="utf-8", newline="\n")

    tr = RD.read_text(encoding="utf-8")
    item = [x for x in tr.split("\n") if x.startswith("| 84 | ")]
    assert len(item) == 1, f"README 84 项锚点 {len(item)} 个"
    assert item[0].count("|") == 3, "README 84 项列数不对"
    fixed = item[0].rstrip()[:-1] + " | 现在只有模板与自动填表，缺的是「插进正文 + 用真数据填论述」 |"
    tr = tr.replace(item[0], fixed, 1)
    RD.write_text(tr, encoding="utf-8", newline="\n")

    print(f"[ok] 主计划 {len(MP.read_text(encoding='utf-8').splitlines())} 行、"
          f"README {len(RD.read_text(encoding='utf-8').splitlines())} 行、"
          f"使用说明 {len(US.read_text(encoding='utf-8').splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
