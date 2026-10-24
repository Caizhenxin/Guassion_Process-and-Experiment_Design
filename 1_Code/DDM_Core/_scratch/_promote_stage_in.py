"""把转接层从 `_scratch/` 提升到 `1_Code/Experiment/`，同步四处文档引用。幂等。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
FILES = [
    ROOT / "5_Reference/08_工作流/数据快速筛查SOP.md",
    ROOT / "5_Reference/03_论文写作/Stage8_真实数据首轮_20261025.md",
    ROOT / "5_Reference/08_工作流/工作流_主计划.md",
    ROOT / "1_Code/DDM_Core/README.md",
]
PAIRS = [
    ("1_Code/DDM_Core/_scratch/_stage8_stage_in.py", "1_Code/Experiment/stage8_stage_in.py"),
    ("1_Code\\DDM_Core\\_scratch\\_stage8_stage_in.py", "1_Code\\Experiment\\stage8_stage_in.py"),
    ("`_stage8_stage_in.py`（转接层）", "`1_Code/Experiment/stage8_stage_in.py`（转接层）"),
    ("`_stage8_stage_in.py`", "`stage8_stage_in.py`"),
]
for f in FILES:
    s = f.read_text(encoding="utf-8")
    old = s
    for a, b in PAIRS:
        s = s.replace(a, b)
    if s != old:
        f.write_text(s, encoding="utf-8", newline="\n")
        print(f"[fix] {f.name}")
    else:
        print(f"[ok ] {f.name} 无需改")
