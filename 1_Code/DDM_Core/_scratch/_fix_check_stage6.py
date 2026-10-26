"""一次性改写 check_stage6_report.py：真实场次 fixture 换成组 2 + 可剔练习段。"""
from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\exp_Check\check_stage6_report.py")

s = P.read_text(encoding="utf-8")
orig = s

s = s.replace(
    "| E2 | 真实 v4.8 场次（练习段 0 行 + 整场跑两遍） | exit 1；N=0；出现「练习段 0 行」 |\n"
    "| E3 | 真实场次 + 2 名干净被试混放 | exit 0；N=2、不计入 1（**不计入的不能被算进判据**） |",
    "| E2 | 真实 v4.8 场次，且练习段被剔空（组 2 的 P=8 ⇒ 真缺陷） | exit 1；N=0；出现「练习段 0 行」 |\n"
    "| E3 | 同上真实场次 + 2 名干净被试混放 | exit 0；N=2、不计入 1（**不计入的不能被算进判据**） |")

s = s.replace("import shutil\nimport subprocess", "import csv\nimport subprocess")

s = s.replace(
    'REAL_DIR = EXP.parent.parent / "2_Data" / "Real_Data" / "New_Design" / "Condition 1"\n'
    'REAL_CSV = REAL_DIR / "EXP_data_group1_1.csv"\n'
    'REAL_TXT = REAL_DIR / "exp_group1_subject1.txt"',
    "# 真实场次必须取**组 2**（P=8）：D120 之后「练习段行数 = P」，组 1 的 P=0 本来就是零练习，\n"
    "# 拿它当「练习段 0 行」的缺陷 fixture 会与定稿设计自相矛盾。\n"
    'REAL_DIR = EXP.parent.parent / "2_Data" / "Real_Data" / "New_Design" / "Condition 2"\n'
    'REAL_CSV = REAL_DIR / "EXP_data_group2_1.csv"\n'
    'REAL_TXT = REAL_DIR / "exp_group2_subject1.txt"')

s = s.replace(
    "def plant_real(dst: Path) -> None:\n"
    "    shutil.copy2(REAL_CSV, dst / REAL_CSV.name)\n"
    "    shutil.copy2(REAL_TXT, dst / REAL_TXT.name)",
    "def plant_real(dst: Path, strip_practice: bool = False) -> None:\n"
    '    """搬一份真实场次进临时目录；`strip_practice` 时把练习段从 **csv 与 txt 一起**剔掉。\n\n'
    "    只剔 csv 不管用：`n_practice` 是从 txt 读的，两边不一致反而会被记成另一条缺陷。\n"
    '    """\n'
    "    rows = list(csv.DictReader(REAL_CSV.open(encoding=\"utf-8\")))\n"
    "    if strip_practice:\n"
    "        rows = [r for r in rows if r.get(\"stage\") != \"practice\"]\n"
    "    with (dst / REAL_CSV.name).open(\"w\", encoding=\"utf-8\", newline=\"\") as fh:\n"
    "        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator=\"\\n\")\n"
    "        writer.writeheader()\n"
    "        writer.writerows(rows)\n"
    "\n"
    "    lines = REAL_TXT.read_text(encoding=\"utf-8\", errors=\"replace\").splitlines()\n"
    "    if strip_practice:\n"
    "        cols = [c.strip() for c in lines[0].lstrip(\"#\").split(\"\\t\")]\n"
    "        idx = cols.index(\"stage\")\n"
    "        kept = [lines[0]]\n"
    "        for ln in lines[1:]:\n"
    "            parts = ln.split(\"\\t\")\n"
    "            if len(parts) > idx and parts[idx].strip() == \"practice\":\n"
    "                continue\n"
    "            kept.append(ln)\n"
    "        lines = kept\n"
    "    (dst / REAL_TXT.name).write_text(\"\\n\".join(lines) + \"\\n\", encoding=\"utf-8\")")

s = s.replace(
    "    plant_real(d)\n"
    '    code, out = run([str(d)])\n'
    '    check("E2 exit 1", code == 1, f"code={code}")',
    "    plant_real(d, strip_practice=True)\n"
    '    code, out = run([str(d)])\n'
    '    check("E2 exit 1", code == 1, f"code={code}")')

s = s.replace(
    "    # 合成件必须放在**别的组**：组 1 的 (1,1) 会与真实场次同名，触发 intake 的「同一 (组,编号) 取最浅层」\n"
    "    if not make_clean(d, group=2):",
    "    # 合成件必须放在**别的组**：真实场次是组 2，合成件放组 1，否则 (组,编号) 同名会触发\n"
    "    # intake 的「同一 (组,编号) 取最浅层」\n"
    "    if not make_clean(d, group=1):")

s = s.replace(
    "    plant_real(d)\n"
    '    code, out = run([str(d)])\n'
    '    check("E3 exit 0", code == 0, f"code={code}")',
    "    plant_real(d, strip_practice=True)\n"
    '    code, out = run([str(d)])\n'
    '    check("E3 exit 0", code == 0, f"code={code}")')

if s == orig:
    raise SystemExit("没有任何替换生效")
P.write_text(s, encoding="utf-8", newline="\n")
print("已改写；shutil 仍被引用:", "shutil." in s)
