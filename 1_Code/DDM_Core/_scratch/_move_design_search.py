"""把 design_search 的 CSV/MD 从 5_Reference/03_论文写作/figures_sim 迁到 2_Data/Generate_Data/_design_search，
并改 design_search.py 的 OUT 常量（图数据分家，D115 口径）。"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
SRC = ROOT / "5_Reference" / "03_论文写作" / "figures_sim"
DST = ROOT / "2_Data" / "Generate_Data" / "_design_search"
PY = ROOT / "1_Code" / "Experiment" / "design_search.py"

DST.mkdir(parents=True, exist_ok=True)
for p in sorted(SRC.glob("design_search_*")):
    target = DST / p.name
    if target.exists():
        print(f"[skip] 已存在 {target.name}")
        continue
    try:
        subprocess_ok = False
        import subprocess
        subprocess.run(["git", "mv", str(p), str(target)], cwd=ROOT, check=True,
                       capture_output=True)
        print(f"[git mv] {p.name}")
    except Exception:
        shutil.move(str(p), str(target))
        print(f"[move] {p.name}")

s = PY.read_text(encoding="utf-8")
old = 'OUT = _ROOT / "5_Reference" / "03_论文写作" / "figures_sim"'
new = 'OUT = _ROOT / "2_Data" / "Generate_Data" / "_design_search"'
if old in s:
    s = s.replace(old, new)
    s = s.replace("5_Reference/03_论文写作/figures_sim/design_search_<truth>.csv",
                  "2_Data/Generate_Data/_design_search/design_search_<truth>.csv")
    s = s.replace("5_Reference/03_论文写作/figures_sim/design_search_<truth>.md",
                  "2_Data/Generate_Data/_design_search/design_search_<truth>.md")
    PY.write_text(s, encoding="utf-8", newline="\n")
    print("[ok] design_search.py OUT 已改")
else:
    print("[skip] design_search.py 已是新路径" if new in s else "[warn] 未找到 OUT 行")
