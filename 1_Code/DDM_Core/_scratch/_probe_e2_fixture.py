"""探针：E2/E3 的真实场次 fixture 该用哪份、剔除练习段后报告怎么说。"""
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
SRC = REPO / "2_Data" / "Real_Data" / "New_Design" / "Condition 2"
STAGE6 = REPO / "1_Code" / "Experiment" / "stage6_report.py"
MAKER = REPO / "1_Code" / "DDM_Core" / "_scratch" / "make_fake_pilot.py"


def run(d, tag):
    p = subprocess.run([sys.executable, "-X", "utf8", str(STAGE6), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(f"\n########## {tag}: exit {p.returncode} ##########")
    lines = out.splitlines()
    for ln in lines[:6]:
        print(" ", ln)
    for ln in lines:
        if "场次" in ln or "练习段" in ln or "N =" in ln or "Stage 7" in ln or "不计入" in ln:
            print(" >", ln)
    return p.returncode, out


with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    d = tmp / "e2"
    d.mkdir()
    shutil.copy2(SRC / "EXP_data_group2_1.csv", d / "EXP_data_group2_1.csv")
    shutil.copy2(SRC / "exp_group2_subject1.txt", d / "exp_group2_subject1.txt")
    csv_path = d / "EXP_data_group2_1.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    print("列：", list(rows[0].keys())[:12])
    stages = {}
    for r in rows:
        stages[r.get("stage", "?")] = stages.get(r.get("stage", "?"), 0) + 1
    print("原始行数", len(rows), "stage 分布", stages)
    run(d, "原样（组 2 真实场次）")

    # 剔掉练习段
    keep = [r for r in rows if r.get("stage") != "practice"]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(keep)
    print(f"\n剔除练习段：{len(rows)} → {len(keep)} 行")
    run(d, "剔练习段（组 2）")

    # 混放：组 2 合成件 + 组 2 真实场次（含练习段，先还原）
    d2 = tmp / "e3"
    subprocess.run([sys.executable, "-X", "utf8", str(MAKER), str(d2),
                    "--n-subjects", "2", "--group", "1", "--seed", "11"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    shutil.copy2(SRC / "EXP_data_group2_1.csv", d2 / "EXP_data_group2_1.csv")
    shutil.copy2(SRC / "exp_group2_subject1.txt", d2 / "exp_group2_subject1.txt")
    run(d2, "混放（合成组1 ×2 + 真实组2）")
