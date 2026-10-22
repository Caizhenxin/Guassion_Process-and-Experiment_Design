from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\工作流_主计划.md")
lines = P.read_text(encoding="utf-8").split("\n")
for i, ln in enumerate(lines):
    if "14（③ 设计空间优化 → D116）" in ln:
        print(i, "pipes=", ln.count("|"))
        print(repr(ln[-160:]))
        # 打印表头
        j = i
        while j > 0 and lines[j].startswith("|"):
            j -= 1
        print("header:", repr(lines[j + 1][:160]), lines[j + 1].count("|"))
