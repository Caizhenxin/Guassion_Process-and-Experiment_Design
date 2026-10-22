"""把 README §9 第 94 行从 4 列压回 3 列（该表是 序号 | 标题 | 内容）。"""
from pathlib import Path

RME = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\README.md")
lines = RME.read_text(encoding="utf-8").splitlines()
idx = next(i for i, s in enumerate(lines) if s.startswith("| 94 |"))
old = lines[idx]
assert old.count("|") == 5, old.count("|")
cells = [c for c in old.strip().strip("|").split("|")]
assert len(cells) == 4, len(cells)
cells[2] = cells[2].rstrip() + " 用户原话：「" + cells[3].strip() + "」"
# cells[3] 里已经带了「用户 2026-10-23：「…」，这里只保留引号内容
new = "| " + " | ".join(c[:0] + c for c in cells[:3]) + " |"
new = f"| {cells[0].strip()} | {cells[1].strip()} | {cells[2].strip()} |"
assert new.count("|") == 4, new.count("|")
lines[idx] = new
RME.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("fixed; 行数", len(lines))
print(new[:100], "...", new[-120:])
