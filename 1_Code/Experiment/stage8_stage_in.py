"""把 Condition */ 下的 18 个 KEEP 场次 txt 硬链接到一个扁平目录，喂给 stage8_run.py。

stage8_run.py 只吃「同一目录下 N 个 exp_group<g>_subject<s>.txt」的 v4.1 布局，
而 New_Design 是 Condition 1..4 的分层布局；这里做一个不改数据的转接层。
"""
import json
import os
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
DATA = ROOT / "2_Data" / "Real_Data" / "New_Design"
OUT = DATA / "_stage8_in"
SNAP = ROOT / "4_Reports" / "筛查_New_Design_20261024.json"

rep = json.loads(SNAP.read_text(encoding="utf-8"))
rows = rep["sessions"] if isinstance(rep.get("sessions"), list) else rep.get("rows")
assert rows, list(rep)[:8]
keep = {(r["group"], r["subject"]) for r in rows if r["verdict"] == "KEEP"}
print(f"KEEP 场次：{len(keep)}")
for r in rows:
    if r["verdict"] != "KEEP":
        print(f"  排除 {r['group']}-{r['subject']}：{r['verdict']}")

OUT.mkdir(exist_ok=True)
for f in OUT.iterdir():
    if f.is_file():
        f.unlink()

n = 0
for src in sorted(DATA.glob("Condition */*.txt")):
    stem = src.stem  # exp_group1_subject1
    try:
        gid = int(stem.split("group")[1].split("_")[0])
        sid = int(stem.split("subject")[1])
    except (IndexError, ValueError):
        print(f"  跳过（名字不合规）：{src.name}")
        continue
    if (gid, sid) not in keep:
        continue
    dst = OUT / src.name
    if dst.exists():
        dst.unlink()
    os.link(src, dst)
    n += 1
print(f"硬链接 {n} 个 txt -> {OUT}")
