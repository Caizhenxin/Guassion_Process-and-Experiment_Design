from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
lines = p.read_text(encoding="utf-8").split("\n")
row = [s for s in lines if s.startswith("| `1_Code/Experiment/intake.py` + `5_Reference/08_工作流/数据快速筛查SOP.md`")]
assert len(row) == 1, len(row)
lines = [s for s in lines if s != row[0]]
while lines and lines[-1].strip() == "":
    lines.pop()
lines.append(row[0])
p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"[ok] {len(lines)} 行")
