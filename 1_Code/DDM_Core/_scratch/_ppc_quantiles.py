"""M-T3 的 PPC 分位对照：是「整体平移」还是「尾巴太瘦」。"""
import re
import pathlib

P = pathlib.Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
                 r"\2_Data\Real_Data\New_Design\_pipeline\stage8_d123\stage8_report.md")
lines = P.read_text(encoding="utf-8").splitlines()
cur_model = cur_sub = None
rows = []
i = 0
while i < len(lines):
    m = re.match(r"#### (M-T\d) / 被试 (\d+)", lines[i])
    if m:
        cur_model, cur_sub = m.group(1), int(m.group(2))
    if lines[i].strip() == "### 全局统计量" and cur_model == "M-T3":
        j = i + 3
        got = {}
        while j < len(lines) and lines[j].startswith("|`"):
            cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
            nm = cells[0].strip("`")
            if nm in ("rt_p10", "rt_p25", "rt_p50", "rt_p75", "rt_p90"):
                got[nm] = (float(cells[1]), float(cells[2]))
            j += 1
        if len(got) == 5:
            rows.append((cur_sub, got))
        i = j
        continue
    i += 1

print(f"{'被试':>4s}" + "".join(f"{q:>12s}" for q in ("p10", "p25", "p50", "p75", "p90")))
sums = {k: [] for k in ("p10", "p25", "p50", "p75", "p90")}
for sub, g in rows:
    line = f"{sub:>4d}"
    for q, (o, p) in g.items():
        d = (p - o) * 1000
        sums[q.replace("rt_", "")].append(d)
        line += f"{d:>+12.0f}"
    print(line)
print("\n平均偏差（ms，负=预测偏快）：")
for q, v in sums.items():
    print(f"  {q}: {sum(v) / len(v):+7.1f}   （n={len(v)}）")
