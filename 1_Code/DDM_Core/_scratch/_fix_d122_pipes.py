from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
MEMO = ROOT / "5_Reference" / "03_论文写作" / "定编依据_N精度与N区分_20261025.md"

fixes = [
    (PLAN, "`--mode precision|discriminate`", "`--mode precision / discriminate`"),
    (MEMO, "dt=1e-4（|Δacc| ≈ 0.005", "dt=1e-4（Δacc 绝对偏差 ≈ 0.005"),
]

for path, old, new in fixes:
    text = io.open(path, encoding="utf-8").read()
    n = text.count(old)
    assert n == 1, f"{path.name}: {old!r} 命中 {n} 次"
    io.open(path, "w", encoding="utf-8", newline="\n").write(text.replace(old, new))
    print(f"[ok] {path.name}: {old} -> {new}")
