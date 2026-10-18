# -*- coding: utf-8 -*-
"""`intake.py` 自测：五条用例，覆盖「能拦」「能放」「不静默挑文件」。

为什么必须自测：一个只会放行的判定器等于没有判定器（D85 的教训）；而一个**静默挑错文件**
的判定器比没有更糟——本轮真的踩到了：`test/_full_session_out/` 的自测产物与用户交付的
真实场次同名，`find_sessions` 按目录遍历顺序覆盖，真实场次被顶掉，报告出来的“正确率
0.485 / timeout 23.4%”其实属于自测产物。

用例：

| 编号 | 场景 | 期望 |
|---|---|---|
| C1 | 用户交回的 v4.8 真实场次 | 判 **EXCLUDE**；理由含「练习段 0 行」与「去重丢弃 576 行」 |
| C2 | v4.9 冒烟产物（组 1，练习 4 行） | 结构层读成 576 正式 + 4 练习 + 去重 0 |
| C3 | 同一 (组, 编号) 两处快照 | 选**层级最浅**、另一份进 `shadowed` |
| C4 | 目录里只有 txt | 退出码 2（不猜） |
| C5 | 空目录 | 退出码 2 |
| C6 | `make_fake_pilot.py` 生成的干净场次（只有 txt） | 判 **KEEP**，且 txt-only 路径能走通（`csv is None`） |

C6 是「能放」的证据：只会拦的判定器等于没有判定器（D85），而只会放的判定器是摆设。
C4 现在只覆盖「txt 名不规范」的情形——合规 txt 名已经能判（C6）。

用法：`python -X utf8 1_Code/Experiment/exp_Check/check_intake.py`
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent.parent
sys.path.insert(0, str(EXP))

import intake                                                  # noqa: E402

REAL_CSV = EXP / "exp_matlab" / "EXP_data_group1_1.csv"
SMOKE = EXP / "exp_matlab" / "test" / "_full_session_out"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} [{name}] {detail}")


def _run_cli(path: Path) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, "-X", "utf8", str(EXP / "intake.py"), str(path)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def c1_real_session(tmp: Path) -> None:
    if not REAL_CSV.exists():
        check("C1 真实场次", False, f"缺样本 {REAL_CSV}")
        return
    d = tmp / "c1"
    d.mkdir()
    shutil.copy2(REAL_CSV, d / REAL_CSV.name)
    txt = REAL_CSV.with_name("exp_group1_subject1.txt")
    shutil.copy2(txt, d / txt.name)

    r = intake.audit_one(1, 1, d / REAL_CSV.name, d / txt.name)
    hard = " ".join(r["hard"])
    soft = " ".join(r["soft"])
    check("C1 真实场次判 EXCLUDE", r["verdict"] == "EXCLUDE",
          f"verdict={r['verdict']}")
    check("C1 抓到练习段 0 行", "练习段 0 行" in hard, hard[:80])
    check("C1 抓到整场跑两遍", "去重丢弃 576 行" in soft, soft[:80])
    rec = r["rec"]
    check("C1 结构与既有工具一致",
          rec["n_formal"] == 576 and rec["n_practice"] == 0
          and abs(rec["acc_mean"] - 0.4402) < 1e-3
          and abs(rec["timeout_prop"] - 0.1875) < 1e-6,
          f"formal={rec['n_formal']} practice={rec['n_practice']} "
          f"acc={rec['acc_mean']:.4f} timeout={rec['timeout_prop']:.4f}")


def c2_smoke(tmp: Path) -> None:
    csv = SMOKE / "EXP_data_group1_99.csv"
    txt = SMOKE / "exp_group1_subject99.txt"
    if not (csv.exists() and txt.exists()):
        check("C2 v4.9 冒烟产物", False, f"缺样本 {csv}")
        return
    r = intake.audit_one(1, 99, csv, txt)
    rec = r["rec"]
    check("C2 结构层读到 576 + 4",
          rec["n_formal"] == 576 and rec["n_practice"] == 4 and rec["n_dropped"] == 0,
          f"formal={rec['n_formal']} practice={rec['n_practice']} dropped={rec['n_dropped']}")


def c3_shadow(tmp: Path) -> None:
    if not REAL_CSV.exists():
        check("C3 同名快照", False, "缺样本")
        return
    d = tmp / "c3"
    deep = d / "test" / "_full_session_out"
    deep.mkdir(parents=True)
    shutil.copy2(REAL_CSV, d / REAL_CSV.name)
    shutil.copy2(REAL_CSV, deep / REAL_CSV.name)
    got = intake.find_sessions([d])
    one = [x for x in got if x["gid"] == 1 and x["sid"] == 1]
    check("C3 只有一个 (组, 编号)", len(one) == 1, f"n={len(one)}")
    if one:
        x = one[0]
        check("C3 选层级最浅的", x["csv"].parent == d, f"选中 {x['csv']}")
        check("C3 另一份进 shadowed", len(x["shadowed"]) == 1,
              f"shadowed={[p.name for p in x['shadowed']]}")


def c4_txt_only(tmp: Path) -> None:
    """文件名不合规的 txt 不许猜（合规 txt 现在能判，见 C6）。"""
    d = tmp / "c4"
    d.mkdir()
    src = REAL_CSV.with_name("exp_group1_subject1.txt")
    if src.exists():
        shutil.copy2(src, d / "group1_1.txt")
    code, out = _run_cli(d)
    check("C4 文件名不合规 ⇒ 退出码 2", code == 2, f"code={code}")
    check("C4 不被误当场次", "没有找到场次" in out, out.strip().splitlines()[:1])


def c5_empty(tmp: Path) -> None:
    d = tmp / "c5"
    d.mkdir()
    code, _ = _run_cli(d)
    check("C5 空目录 ⇒ 退出码 2", code == 2, f"code={code}")


def c6_keep(tmp: Path) -> None:
    """干净场次必须放行 —— 只会拦的判定器等于没有判定器。"""
    d = tmp / "c6"
    d.mkdir()
    gen = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "make_fake_pilot.py"
    if not gen.exists():
        check("C6 干净场次判 KEEP", False, f"缺生成器 {gen}")
        return
    proc = subprocess.run([sys.executable, "-X", "utf8", str(gen), str(d),
                           "--n-subjects", "1", "--group", "1", "--seed", "7"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        check("C6 干净场次判 KEEP", False, (proc.stdout or "")[-200:])
        return

    got = intake.find_sessions([d])
    check("C6 只有 txt 也被收进场次", len(got) == 1 and got[0]["csv"] is None,
          f"n={len(got)} csv={got[0]['csv'] if got else '—'}")
    if not got:
        return
    x = got[0]
    r = intake.audit_one(x["gid"], x["sid"], x["csv"], x["txt"])
    rec = r["rec"]
    check("C6 干净场次判 KEEP", r["verdict"] == "KEEP",
          f"verdict={r['verdict']} hard={r['hard'][:2]} soft={r['soft'][:2]}")
    check("C6 txt-only 结构读到 576 + 4",
          rec["n_formal"] == 576 and rec["n_practice"] == 4,
          f"formal={rec['n_formal']} practice={rec['n_practice']}")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        c1_real_session(tmp)
        c2_smoke(tmp)
        c3_shadow(tmp)
        c4_txt_only(tmp)
        c5_empty(tmp)
        c6_keep(tmp)

    bad = [r for r in results if not r[1]]
    print()
    print(f"== 共 {len(results)} 项：通过 {len(results) - len(bad)} / 未通过 {len(bad)} ==")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
