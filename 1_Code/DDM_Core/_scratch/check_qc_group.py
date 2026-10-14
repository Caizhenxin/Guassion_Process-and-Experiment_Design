#!/usr/bin/env python3
"""`1_Code/Experiment/qc_group.py`（Stage 7 逐 P 组质量快检）的自测。

纪律：**一个检查器的"全绿"只有在它被负向自测打红过之后才算证据。**
本脚本为 qc_group.py 的每一条 G 判据与每一档处置都造一份最小语料，
断言它确实**红在该红的地方、绿在该绿的地方**。

用法
----
    python _scratch/check_qc_group.py            # 全部用例
    python _scratch/check_qc_group.py -v         # 同时打印子进程输出

退出码：全部通过 0，任一用例不符 1。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GEN = HERE / "make_fake_pilot.py"
QC = REPO / "1_Code" / "Experiment" / "qc_group.py"

VERBOSE = False


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kw)
    if VERBOSE:
        print("    $ " + " ".join(str(c) for c in cmd))
        for ln in (proc.stdout or "").splitlines():
            print("      | " + ln)
    return proc


def gen(outdir: Path, group: int, n: int, *flags: str, seed: int = 11) -> None:
    run([sys.executable, str(GEN), str(outdir), "--group", str(group),
         "--n-subjects", str(n), "--seed", str(seed), *flags])


def qc(datadir: Path, *flags: str) -> tuple[int, dict]:
    js = Path(tempfile.mkdtemp()) / "qc.json"
    proc = run([sys.executable, str(QC), str(datadir), "--json", str(js), *flags])
    payload = json.loads(js.read_text(encoding="utf-8")) if js.exists() else {}
    return proc.returncode, payload


def status_of(payload: dict, gid: int, cid: str) -> str | None:
    for g in payload.get("groups", []):
        if g["group"] == gid:
            for c, st, _ in g["criteria"]:
                if c == cid:
                    return st
    return None


def subject_of(payload: dict, gid: int, sid: int) -> dict | None:
    for s in payload.get("subjects", []):
        if s["group"] == gid and int(s["subject"]) == sid:
            return s
    return None


# --------------------------------------------------------------------------- #
# 用例
# --------------------------------------------------------------------------- #
def case(fn):
    fn._is_case = True
    return fn


@case
def t01_clean_passes(tmp: Path) -> list[str]:
    """干净语料：4 组各 2 人 ⇒ 全绿，exit 0。"""
    d = tmp / "clean"
    for g in (1, 2, 3, 4):
        gen(d, g, 2, seed=10 + g)
    rc, p = qc(d, "--expect-n", "2")
    bad = []
    if rc != 0:
        bad.append(f"exit 应为 0，实际 {rc}")
    for g in (1, 2, 3, 4):
        for c in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"):
            st = status_of(p, g, c)
            if st != "PASS":
                bad.append(f"组{g} {c} 应为 PASS，实际 {st}")
    for s in p.get("subjects", []):
        if s["class"] != "KEEP":
            bad.append(f"组{s['group']}-{s['subject']} 应为 KEEP，实际 {s['class']}")
    return bad


@case
def t02_p_mapping_is_checked(tmp: Path) -> list[str]:
    """把 P=120 的组 4 文件冒充成组 1 ⇒ G8 FAIL，且组 1 被标红。"""
    d = tmp / "mismatch"
    gen(d, 4, 2, seed=20)
    shutil.copy(d / "exp_group4_subject1.txt", d / "exp_group1_subject1.txt")
    rc, p = qc(d, "--expect-n", "1")
    bad = []
    if status_of(p, 1, "G8") != "FAIL":
        bad.append(f"组1 G8 应 FAIL，实际 {status_of(p, 1, 'G8')}")
    if status_of(p, 4, "G8") != "PASS":
        bad.append(f"组4 G8 应 PASS，实际 {status_of(p, 4, 'G8')}")
    if rc == 0:
        bad.append("exit 应为 1")
    return bad


@case
def t03_tw_precision_defect(tmp: Path) -> list[str]:
    """`--defect-1f`（T/W 只打一位小数）⇒ 每格试次数崩掉 ⇒ G4 FAIL。"""
    d = tmp / "def1f"
    gen(d, 1, 2, "--defect-1f", seed=21)
    rc, p = qc(d, "--expect-n", "2")
    bad = []
    if status_of(p, 1, "G4") != "FAIL":
        bad.append(f"G4 应 FAIL，实际 {status_of(p, 1, 'G4')}")
    if rc == 0:
        bad.append("exit 应为 1")
    return bad


@case
def t04_missing_t_level(tmp: Path) -> list[str]:
    """只 2 档 T ⇒ 正式段 288 而非 576 ⇒ G2 WARN + G4 FAIL（**不得假通过**）。"""
    d = tmp / "missingT"
    gen(d, 2, 2, "--defect-missing-t", seed=22)
    rc, p = qc(d, "--expect-n", "2")
    bad = []
    if status_of(p, 2, "G2") != "WARN":
        bad.append(f"G2 应 WARN，实际 {status_of(p, 2, 'G2')}")
    if status_of(p, 2, "G4") != "FAIL":
        bad.append(f"G4 应 FAIL，实际 {status_of(p, 2, 'G4')}")
    # 两名被试都应被剔除（< 90% × 576）
    for sid in (1, 2):
        s = subject_of(p, 2, sid)
        if s and s["class"] != "EXCLUDE":
            bad.append(f"组2-{sid} 应 EXCLUDE，实际 {s['class']}")
    return bad


@case
def t05_s6_3_fail_excludes(tmp: Path) -> list[str]:
    """注入 Response/RT/responded_by_deadline 矛盾行 ⇒ S6-3 FAIL ⇒ 该被试剔除。"""
    d = tmp / "contra"
    gen(d, 3, 2, "--defect-mismatch", seed=23)
    rc, p = qc(d, "--expect-n", "2")
    bad = []
    s = subject_of(p, 3, 1)
    if not s:
        bad.append("找不到组3-1")
    elif s["class"] != "EXCLUDE":
        bad.append(f"组3-1 应 EXCLUDE，实际 {s['class']}")
    elif not any("S6-3" in r for r in s["reasons"]):
        bad.append(f"剔除理由应含 S6-3，实际 {s['reasons']}")
    if rc == 0:
        bad.append("exit 应为 1")
    return bad


@case
def t06_early_exit_excludes(tmp: Path) -> list[str]:
    """把一名被试正式段砍剩一半 ⇒ EXCLUDE（提前退出），且**报出真实计数**。"""
    d = tmp / "earlyexit"
    gen(d, 3, 2, seed=24)
    f = d / "exp_group3_subject2.txt"
    lines = f.read_text(encoding="utf-8").splitlines()
    f.write_text("\n".join(lines[: int(len(lines) * 0.5)]) + "\n", encoding="utf-8")
    rc, p = qc(d, "--expect-n", "2")
    bad = []
    s = subject_of(p, 3, 2)
    if not s:
        bad.append("找不到组3-2")
    else:
        if s["class"] != "EXCLUDE":
            bad.append(f"组3-2 应 EXCLUDE，实际 {s['class']}")
        if s["n_formal"] == 0:
            bad.append("n_formal 不应为 0（说明列名没解析出来，真实值应 ≈271）")
        elif not (200 < s["n_formal"] < 320):
            bad.append(f"n_formal 应 ≈271，实际 {s['n_formal']}")
    return bad


@case
def t07_bom_is_tolerated(tmp: Path) -> list[str]:
    """把文件重存成带 UTF-8 BOM ⇒ 解析结果必须**完全不变**（列名不能退化成 col1..col25）。"""
    d = tmp / "bom"
    gen(d, 1, 2, seed=25)
    f = d / "exp_group1_subject1.txt"
    text = f.read_text(encoding="utf-8")
    f.write_text(text, encoding="utf-8-sig")  # 写回带 BOM
    raw = f.read_bytes()
    bad = []
    if not raw.startswith(b"\xef\xbb\xbf"):
        bad.append("前置条件不成立：文件没有 BOM")
    rc, p = qc(d, "--expect-n", "2")
    s = subject_of(p, 1, 1)
    if not s:
        bad.append("找不到组1-1")
    elif s["n_formal"] != 576:
        bad.append(f"带 BOM 后 n_formal 应仍为 576，实际 {s['n_formal']}")
    elif s["class"] != "KEEP":
        bad.append(f"带 BOM 后应为 KEEP，实际 {s['class']}（{s['reasons']}）")
    return bad


@case
def t08_final_makes_n_a_failure(tmp: Path) -> list[str]:
    """`--final` 且人数不足 ⇒ G1 FAIL；不加 --final 时只报进度（INFO）。"""
    d = tmp / "final"
    gen(d, 1, 1, seed=26)
    bad = []
    _, p1 = qc(d, "--expect-n", "5")
    if status_of(p1, 1, "G1") != "INFO":
        bad.append(f"未 --final 时 G1 应 INFO，实际 {status_of(p1, 1, 'G1')}")
    _, p2 = qc(d, "--expect-n", "5", "--final")
    if status_of(p2, 1, "G1") != "FAIL":
        bad.append(f"--final 时 G1 应 FAIL，实际 {status_of(p2, 1, 'G1')}")
    return bad


@case
def t09_in_stim_triggers_stage8(tmp: Path) -> list[str]:
    """长 T 档 95% 是刺激内完成累计 ⇒ G7 WARN + 结论段提示 Stage 8 扩展。"""
    d = tmp / "instim"
    gen(d, 4, 2, "--rt-lt-t", "0.03", "--in-stim-top", "0.95", seed=27)
    rc, p = qc(d, "--expect-n", "2")
    bad = []
    if status_of(p, 4, "G7") != "WARN":
        bad.append(f"G7 应 WARN，实际 {status_of(p, 4, 'G7')}")
    return bad


@case
def t10_legacy_is_excluded_not_crashed(tmp: Path) -> list[str]:
    """旧 16 列文件 ⇒ 列为 EXCLUDE 并说明原因，脚本不崩。"""
    d = tmp / "legacy"
    gen(d, 1, 1, seed=28)
    src = d / "exp_group1_subject1.txt"
    lines = src.read_text(encoding="utf-8").splitlines()
    old = d / "exp_group1_subject9.txt"
    old.write_text("\n".join("\t".join(ln.split("\t")[:16]) for ln in lines) + "\n",
                   encoding="utf-8")
    rc, p = qc(d, "--expect-n", "1")
    bad = []
    s = subject_of(p, 1, 9)
    if not s:
        bad.append("找不到组1-9")
    else:
        if s["class"] != "EXCLUDE":
            bad.append(f"旧 16 列应 EXCLUDE，实际 {s['class']}")
        if not s["legacy"]:
            bad.append("legacy 标志应为 True")
    return bad


def main() -> int:
    global VERBOSE
    # 本机 `python` 的 stdout 默认走 GBK，打印 ✅/❌ 会 UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="qc_group.py 自测")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    VERBOSE = args.verbose

    cases = [v for k, v in sorted(globals().items())
             if k.startswith("t") and callable(v) and getattr(v, "_is_case", False)]
    cases.sort(key=lambda f: f.__name__)

    root = Path(tempfile.mkdtemp(prefix="qc_selftest_"))
    n_bad = 0
    print(f"qc_group.py 自测：{len(cases)} 个用例（临时目录 {root}）")
    print()
    for f in cases:
        sub = root / f.__name__
        sub.mkdir(parents=True, exist_ok=True)
        name = f.__name__.split("_", 1)[1]
        doc = (f.__doc__ or "").strip().splitlines()[0]
        try:
            bad = f(sub) or []
        except Exception as exc:  # noqa: BLE001
            bad = [f"用例抛异常：{type(exc).__name__}: {exc}"]
        if bad:
            n_bad += 1
            print(f"❌ {name}：{doc}")
            for b in bad:
                print(f"     · {b}")
        else:
            print(f"✅ {name}：{doc}")

    print()
    if n_bad:
        print(f"❌ {n_bad}/{len(cases)} 个用例不符预期")
        return 1
    print(f"✅ {len(cases)}/{len(cases)} 个用例全部符合预期")
    return 0


if __name__ == "__main__":
    sys.exit(main())
