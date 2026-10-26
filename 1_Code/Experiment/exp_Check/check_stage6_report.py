# -*- coding: utf-8 -*-
"""`stage6_report.py` 自测：七例，覆盖「能放行」「能拦」「N 不足」「写盘」。

为什么必须自测：报告器的失败模式不是抛异常，而是**给出一个看起来合理的错结论**——
比如把「不计入的场次」也算进判据汇总，或把 WARN 当 FAIL 一票否决。这两种都不会报错。

| 编号 | 场景 | 期望 |
|---|---|---|
| E1 | 2 名干净合成被试（组 1） | exit 0；「可进入 Stage 7」；N=2；S6-1/S6-5 各 PASS 2 |
| E2 | 真实 v4.8 场次，且练习段被剔空（组 2 的 P=8 ⇒ 真缺陷） | exit 1；N=0；出现「练习段 0 行」 |
| E3 | 同上真实场次 + 2 名干净被试混放 | exit 0；N=2、不计入 1（**不计入的不能被算进判据**） |
| E4 | 干净数据但只有 2 档 T（`--defect-missing-t`） | exit 1；§3 出现 `S6-4` 分支 |
| E5 | 空目录 | exit 2 |
| E6 | 干净 2 人 + `--expect-n 8` | exit 1；「目标 N：8 ⇒ **不足**」 |
| E7 | `--out` 写盘 | 文件存在、含标题与「## 3.」段 |

用法：`python -X utf8 1_Code/Experiment/exp_Check/check_stage6_report.py`
"""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
SCRIPT = EXP / "stage6_report.py"
MAKER = EXP.parent / "DDM_Core" / "_scratch" / "make_fake_pilot.py"
# 真实场次必须取**组 2**（P=8）：D120 之后「练习段行数 = P」，组 1 的 P=0 本来就是零练习，
# 拿它当「练习段 0 行」的缺陷 fixture 会与定稿设计自相矛盾。
REAL_DIR = EXP.parent.parent / "2_Data" / "Real_Data" / "New_Design" / "Condition 2"
REAL_CSV = REAL_DIR / "EXP_data_group2_1.csv"
REAL_TXT = REAL_DIR / "exp_group2_subject1.txt"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} [{name}] {detail}")


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def make_clean(dst: Path, n: int = 2, seed: int = 11, extra: list[str] | None = None,
               group: int = 1) -> bool:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    args = [sys.executable, "-X", "utf8", str(MAKER), str(dst),
            "--n-subjects", str(n), "--group", str(group), "--seed", str(seed)]
    if extra:
        args += extra
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0


def plant_real(dst: Path, strip_practice: bool = False) -> None:
    """搬一份真实场次进临时目录；`strip_practice` 时把练习段从 **csv 与 txt 一起**剔掉。

    只剔 csv 不管用：`n_practice` 是从 txt 读的，两边不一致反而会被记成另一条缺陷。
    """
    rows = list(csv.DictReader(REAL_CSV.open(encoding="utf-8")))
    if strip_practice:
        rows = [r for r in rows if r.get("stage") != "practice"]
    with (dst / REAL_CSV.name).open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = REAL_TXT.read_text(encoding="utf-8", errors="replace").splitlines()
    if strip_practice:
        cols = [c.strip() for c in lines[0].lstrip("#").split("\t")]
        idx = cols.index("stage")
        kept = [lines[0]]
        for ln in lines[1:]:
            parts = ln.split("\t")
            if len(parts) > idx and parts[idx].strip() == "practice":
                continue
            kept.append(ln)
        lines = kept
    (dst / REAL_TXT.name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def e1_clean(tmp: Path) -> None:
    d = tmp / "e1"
    if not make_clean(d):
        check("E1 干净合成", False, "生成器失败")
        return
    code, out = run([str(d), "--expect-n", "2"])
    check("E1 exit 0", code == 0, f"code={code}")
    check("E1 判可进 Stage 7", "可进入 Stage 7" in out, "")
    check("E1 N=2", "计入 N = **2**" in out, "")
    check("E1 S6-1 全 PASS", "| **S6-1** | 2 | 0 | 0 |" in out, "")
    check("E1 S6-5 全 PASS", "| **S6-5** | 2 | 0 | 0 |" in out, "")


def e2_real(tmp: Path) -> None:
    if not (REAL_CSV.exists() and REAL_TXT.exists()):
        check("E2 真实场次", False, f"缺样本 {REAL_CSV}")
        return
    d = tmp / "e2"
    d.mkdir()
    plant_real(d, strip_practice=True)
    code, out = run([str(d)])
    check("E2 exit 1", code == 1, f"code={code}")
    check("E2 N=0", "计入 N = **0**" in out, "")
    check("E2 抓到练习段 0 行", "练习段 0 行" in out, "")
    check("E2 判不可进", "暂不可进入 Stage 7" in out, "")


def e3_mixed(tmp: Path) -> None:
    d = tmp / "e3"
    # 合成件必须放在**别的组**：真实场次是组 2，合成件放组 1，否则 (组,编号) 同名会触发
    # intake 的「同一 (组,编号) 取最浅层」
    if not make_clean(d, group=1):
        check("E3 混放", False, "生成器失败")
        return
    plant_real(d, strip_practice=True)
    code, out = run([str(d)])
    check("E3 exit 0", code == 0, f"code={code}")
    check("E3 场次 3 / N=2", "场次：3（计入 N = **2**，不计入 = 1）" in out, "")
    check("E3 不计入者不进判据", "| **S6-1** | 2 | 0 | 0 |" in out, "")


def e4_defect(tmp: Path) -> None:
    d = tmp / "e4"
    if not make_clean(d, extra=["--defect-missing-t"]):
        check("E4 缺陷数据", False, "生成器失败")
        return
    code, out = run([str(d)])
    check("E4 exit 1", code == 1, f"code={code}")
    # 缺一档 T 会让正式段只有 288 行 ⇒ 先被 intake 判提前退出；S6-4 的裁决仍要显形（§1 与 §3 附注）
    check("E4 裁决 S6-4 FAIL 可见", "S6-4 FAIL" in out, "")


def e5_empty(tmp: Path) -> None:
    d = tmp / "e5"
    d.mkdir()
    code, out = run([str(d)])
    check("E5 空目录 exit 2", code == 2, f"code={code}")
    check("E5 给出原因", "没有找到" in out, "")


def e6_short(tmp: Path) -> None:
    d = tmp / "e6"
    if not make_clean(d):
        check("E6 N 不足", False, "生成器失败")
        return
    code, out = run([str(d), "--expect-n", "8"])
    check("E6 exit 1", code == 1, f"code={code}")
    check("E6 报 N 不足", "目标 N：8 ⇒ **不足**" in out, "")
    check("E6 结论给出原因", "不足 8" in out, "")


def e7_write(tmp: Path) -> None:
    d = tmp / "e7"
    if not make_clean(d):
        check("E7 写盘", False, "生成器失败")
        return
    out_md = tmp / "e7_report.md"
    code, out = run([str(d), "--expect-n", "2", "--out", str(out_md)])
    check("E7 exit 0", code == 0, f"code={code}")
    check("E7 文件已写", out_md.exists(), str(out_md))
    if out_md.exists():
        txt = out_md.read_text(encoding="utf-8")
        check("E7 内容完整", "# Stage 6 ｜Pilot 达标报告" in txt and "## 3." in txt, f"{len(txt)} B")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        e1_clean(tmp)
        e2_real(tmp)
        e3_mixed(tmp)
        e4_defect(tmp)
        e5_empty(tmp)
        e6_short(tmp)
        e7_write(tmp)

    bad = [r for r in results if not r[1]]
    print()
    print(f"== 共 {len(results)} 项：通过 {len(results) - len(bad)} / 未通过 {len(bad)} ==")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
