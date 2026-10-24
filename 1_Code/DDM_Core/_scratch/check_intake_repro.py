"""复现性自检：连跑两次 intake.py，比 JSON（去掉时间戳）是否逐字节一致。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
DATA = "2_Data\\Real_Data\\New_Design"
OUT = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "_repro"


def run(tag: str) -> dict:
    p = OUT / f"intake_{tag}.json"
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "1_Code/Experiment/intake.py"), DATA,
           "--out", str(OUT / f"intake_{tag}.md"), "--json", str(p)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1, (r.returncode, r.stderr[-500:])
    d = json.loads(p.read_text(encoding="utf-8"))
    return d


OUT.mkdir(parents=True, exist_ok=True)
a = run("a")
b = run("b")


def strip(d: dict) -> dict:
    d = json.loads(json.dumps(d))
    for k in ("generated_at", "cmd", "data"):
        d.pop(k, None)
    return d


sa, sb = strip(a), strip(b)
if sa == sb:
    print("[ok] 两次运行完全一致")
else:
    print("[!!] 两次运行不一致")
    for k in sa:
        if sa[k] != sb.get(k):
            print(f"  差异键: {k}")

# 与已提交快照对比
snap = ROOT / "4_Reports" / "筛查_New_Design_20261024.json"
cur = json.loads(snap.read_text(encoding="utf-8"))
s0 = strip(cur)
print("[ok] 与提交快照一致" if s0 == sa else "[!!] 与提交快照不同")
if s0 != sa:
    for k in sa:
        if sa[k] != s0.get(k):
            print(f"  差异键: {k}")
