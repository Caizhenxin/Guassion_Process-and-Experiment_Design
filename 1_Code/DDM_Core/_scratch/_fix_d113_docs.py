"""修 _apply_d113_docs.py 重复插入：每条 D113 行只保留一条；README 补第 94 行。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
MAIN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
RME = ROOT / "1_Code" / "DDM_Core" / "README.md"

ANCHORS = ("| **D113** |", "| 2026-10-23 | **11（三模型生成器",
           "| 2026-10-23 | **新增 D113", "| `1_Code/DDM_Core/ramp.py` +")

lines = MAIN.read_text(encoding="utf-8").splitlines()
out: list[str] = []
seen: set[str] = set()
dropped = 0
for s in lines:
    key = next((a for a in ANCHORS if s.startswith(a)), None)
    if key is not None:
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
    out.append(s)
MAIN.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print(f"主计划 {len(lines)} → {len(out)} 行（删重复 {dropped} 行，去重键 {sorted(seen)}）")

README_ROW = (
    "| 94 | ✅ **三模型生成器与图（D113）** | `1_Code/DDM_Core/ramp.py`（M-T2 斜坡，**无似然**）、"
    "`1_Code/Experiment/gen_model_data.py`（`GEN_TRUTH` 独立口径，4 组 × 4 人 × 576 试次 = 9216 行/模型，产物 "
    "`trials_long.csv` / `subjects.csv` / `cells.csv` / `meta.json`）、`1_Code/Experiment/gen_viz.py`"
    "（图 1–6 + 跨模型 `fig7_model_compare`）；数据落 `2_Data/Generate_Data/` 下的 `M-T1`/`M-T2`/`M-T3` 三个目录，"
    "notebook 落 `1_Code/Python_for_Generate/`（由 `_scratch/_build_model_notebooks.py` 生成，实跑 23 单元 0 错误、"
    "自检 5/5）。CRF 在 T×W×身份**内部**分箱；本模拟 CRF 下降（快试次更准）是模型边界，不硬凑真实形状。 | "
    "用户 2026-10-23：「我有 3 个 Model，是不是应该有 3 个数据生成器 + 3 个 `.ipynb`」+「生成的 CSV 放到对应文件夹」+"
    "「把生成数据可视化（RT distribution、按自我/他人分条件、CRF）」 |"
)
print("README 新行竖线数 =", README_ROW.count("|"))

rl = RME.read_text(encoding="utf-8").splitlines()
if any(s.startswith("| 94 |") for s in rl):
    print("README 已有第 94 行，跳过")
else:
    idx = next(i for i, s in enumerate(rl) if s.startswith("| 93 |"))
    rl.insert(idx + 1, README_ROW)
    RME.write_text("\n".join(rl) + "\n", encoding="utf-8", newline="\n")
    print(f"README {idx + 2} 行处插入；总 {len(rl)} 行")
