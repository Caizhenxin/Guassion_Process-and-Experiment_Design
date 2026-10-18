"""D101 落纸：按行首前缀重写证据行与 §9 第 84 项（避免长锚点漂移）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MP = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RD = ROOT / "1_Code" / "DDM_Core" / "README.md"

NEW_EV = [
    ("| `1_Code/Experiment/manuscript.py`（**新建**，D101",
     "| `1_Code/Experiment/manuscript.py`（**新建**，D101，154 行）：`load_template` / `table_under` / "
     "`render`（缺块即 `KeyError`）/ `synth_banner` / `load_truth` / `write_draft` / CLI | "
     "**D101 的一手证据（结果章自动填表）**：草稿 130 行、10 处 `【待写】`；`render` 对缺块抛 "
     "`KeyError`（2026-10-18，D101） |"),
    ("| `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，D101",
     "| `5_Reference/03_论文写作/论文_结果章_模板.md`（**新建**，D101，92 行）：第 9 章框架、7 节、"
     "四个花括号占位、三张图相对路径 | 章号待定（插为第 9 章）；含 `synth_truth.json` 时草稿不得进正文"
     "（2026-10-18，D101） |"),
]
NEW_ITEM = (
    "| 84 | ❌ **未做**：`论文_结果章_模板.md` 尚未真正插入 `5_Reference/03_论文写作/_v3_正文.md`"
    "（章号、上下章衔接、表号重编都要人工定）；且模板里的 `【待写】` 10 处没有真实数据可填 | "
    "现在只有模板与自动填表，缺的是「插进正文 + 用真数据填论述」 |"
)


def main() -> int:
    L = MP.read_text(encoding="utf-8").split("\n")
    for prefix, new in NEW_EV:
        idx = [i for i, x in enumerate(L) if x.startswith(prefix)]
        assert len(idx) == 1, f"主计划证据行前缀 {prefix[:30]!r} 命中 {len(idx)} 个"
        L[idx[0]] = new
    MP.write_text("\n".join(L), encoding="utf-8", newline="\n")

    R = RD.read_text(encoding="utf-8").split("\n")
    idx = [i for i, x in enumerate(R) if x.startswith("| 84 | ")]
    assert len(idx) == 1, f"README 84 项命中 {len(idx)} 个"
    R[idx[0]] = NEW_ITEM
    RD.write_text("\n".join(R), encoding="utf-8", newline="\n")

    print(f"[ok] 主计划 {len(L) - 1} 行、README {len(R) - 1} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
