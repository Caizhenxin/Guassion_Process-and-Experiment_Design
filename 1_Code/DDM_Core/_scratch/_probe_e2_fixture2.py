"""探针二：把组 2 真实场次的练习段从 csv 与 txt 一起剔掉，看报告是否判「练习段 0 行 ⇒ 不计入」。"""
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
SRC = REPO / "2_Data" / "Real_Data" / "New_Design" / "Condition 2"
STAGE6 = REPO / "1_Code" / "Experiment" / "stage6_report.py"

with tempfile.TemporaryDirectory() as td:
    d = Path(td) / "e2"
    d.mkdir()
    csv_src, txt_src = SRC / "EXP_data_group2_1.csv", SRC / "exp_group2_subject1.txt"
    raw = txt_src.read_text(encoding="utf-8", errors="replace").splitlines()
    print("txt 行数", len(raw), "首行:", raw[0][:200])
    print("示例数据行:", raw[1][:200] if len(raw) > 1 else "")

    rows = list(csv.DictReader(csv_src.open(encoding="utf-8")))
    keep = [r for r in rows if r.get("stage") != "practice"]
    with (d / csv_src.name).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(keep)
    print("csv 行数", len(rows), "→", len(keep))

    # txt 的 stage 列在第几个位置？先猜是第 6 列（与 csv 同列）
    cols = raw[0].lstrip("#").split("\t")
    print("txt 列数", len(cols), "列名", [c.strip() for c in cols][:10])
    name = "stage" if "stage" in [c.strip() for c in cols] else None
    if name:
        idx = [c.strip() for c in cols].index("stage")
        out = [raw[0]]
        dropped = 0
        for ln in raw[1:]:
            parts = ln.split("\t")
            if len(parts) > idx and parts[idx].strip() == "practice":
                dropped += 1
                continue
            out.append(ln)
        (d / txt_src.name).write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"txt 剔除练习段 {dropped} 行 → {len(out)} 行")
    else:
        shutil.copy2(txt_src, d / txt_src.name)

    p = subprocess.run([sys.executable, "-X", "utf8", str(STAGE6), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(f"\n########## exit {p.returncode} ##########")
    for ln in out.splitlines():
        if any(k in ln for k in ("场次", "练习段", "N =", "Stage 7", "不计入", "判定", "组 | 编号")):
            print(ln[:220])
