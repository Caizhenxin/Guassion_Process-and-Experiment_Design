"""修 D121 落纸后的两处表格问题：① 行内字面竖线 `|θ|` ② 证据行前的断表空行。幂等。"""
from pathlib import Path

PLAN = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
lines = PLAN.read_text(encoding="utf-8").split("\n")

# ① 行内字面竖线
n_fix = 0
for i, s in enumerate(lines):
    if "`|θ|` 最大" in s:
        lines[i] = s.replace("`|θ|` 最大", "θ 的最大绝对值")
        n_fix += 1
print(f"[pipes] 修 {n_fix} 行")

# ② 末尾断表空行：把证据行摘出来，剥尾部空串后重新 append
tail_idx = [i for i, s in enumerate(lines) if s.startswith("| `5_Reference/03_论文写作/Stage8_真实数据首轮_20261025.md`")]
assert len(tail_idx) == 1, tail_idx
ev = lines.pop(tail_idx[0])
while lines and not lines[-1].strip():
    lines.pop()
lines.append(ev)
lines.append("")
PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(f"[plan] {len(lines)} 行（末尾保留一个空串）")
