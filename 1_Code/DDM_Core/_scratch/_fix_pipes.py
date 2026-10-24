from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")

plan = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
s = plan.read_text(encoding="utf-8")

fixes = [
    # D119 里的字面竖线（markdown 表格会把它们当成列分隔）
    ("真实点（可见度 |ΔRT|/SD = 0.16、Δacc 5.9 pp）",
     "真实点（可见度取 ΔRT 绝对值 / SD = 0.16、Δacc 5.9 pp）"),
    ("`|dur−T|` 均值 2.71 ms", "刺激时长偏差均值 2.71 ms"),
    # D118 行多出一个单元（历史遗留）：把最后一格并进前一格
    ("`假设_模型_参数_对照_v1.md` | 关闭「SPE 只在漂移上」的结构缺口",
     "`假设_模型_参数_对照_v1.md`；关闭「SPE 只在漂移上」的结构缺口"),
]
for a, b in fixes:
    n = s.count(a)
    print(f"{n}x  {a[:36]}")
    assert n == 1, a
    s = s.replace(a, b)
plan.write_text(s, encoding="utf-8", newline="\n")

readme = ROOT / "2_Data/Real_Data/New_Design/README.md"
r = readme.read_text(encoding="utf-8")
for a, b in [("| `|dur − T|` 均值 |", "| 刺激时长偏差（均值） |"),
             ("| `|dur − T|` 最大 |", "| 刺激时长偏差（最大） |")]:
    n = r.count(a)
    print(f"{n}x  {a}")
    assert n == 1, a
    r = r.replace(a, b)
readme.write_text(r, encoding="utf-8", newline="\n")
print("done")
