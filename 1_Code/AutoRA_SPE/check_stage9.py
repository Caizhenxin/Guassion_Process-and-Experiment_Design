# -*- coding: utf-8 -*-
"""Stage 9 的**汇总自测**：把五个子自测跑一遍，再加上三件只有汇总层才能做的漂移守卫。

**为什么需要一个汇总层**（`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9）：
五个子自测各自验证**自己的**文件，没有任何一个会检查下面三件事：

- **W1 冻结规格没有漂移**：`stage9_objective.SPEC_SHA256` 必须等于 `compute_sha256()`
  （即哈希是**算出来的**、不是手抄的），且 `assert_frozen()` 不抛。这是"事前登记 + 哈希锁定"
  这条处方唯一能被机器检的地方。
- **W2/W3 文件清单没有漂移**：七个 Stage 9 文件必须**同时**出现在
  `1_Code/AutoRA_SPE/README.md` §7 的文件清单与
  `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9 的工具表里
  （新增文件忘了登记是这类项目的常见漂移）。

**它怎么跑子自测**：用 `subprocess` 把每个子自测的 stdout/stderr **重定向到文件**（不走管道），
再读文件解析各自的通过计数；**以子进程退出码为权威**，解析出来的计数只用于报告。

用法：
    python -u 1_Code/AutoRA_SPE/check_stage9.py                 # 全套（约 4–5 min）
    python -u 1_Code/AutoRA_SPE/check_stage9.py --n-fim-inner 4 # 内环用更大的 n_fim
    python -u 1_Code/AutoRA_SPE/check_stage9.py --quick         # 跳过内环/循环两档慢的
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LOGS = HERE  # 与其它自测一致：日志就写在 AutoRA_SPE 下，前缀 _scratch_

STAGE9_FILES = (
    "stage9_inner.py",
    "check_stage9_inner.py",
    "stage9_objective.py",
    "stage9_loop.py",
    "check_stage9_loop.py",
    "stage9_report.py",
    "check_stage9_report.py",
)

RESULTS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((label, bool(ok), detail))
    print(f"{'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""), flush=True)
    return bool(ok)


def run_checker(script: str, args: list[str], log_name: str) -> tuple[int, str, str]:
    """跑一个子自测，stdout/stderr **重定向到文件**（不走管道），返回 (退出码, 日志文本, 路径)。"""
    log = LOGS / log_name
    cmd = [sys.executable, "-u", str(HERE / script), *args]
    print(f"\n▶ {' '.join([script, *args])}  →  {log.name}", flush=True)
    t0 = time.time()
    with open(log, "w", encoding="utf-8", newline="\n") as fh:
        proc = subprocess.run(cmd, cwd=str(HERE), stdout=fh, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, check=False)
    print(f"  退出码 {proc.returncode}、耗时 {time.time() - t0:.1f}s", flush=True)
    return proc.returncode, log.read_text(encoding="utf-8", errors="replace"), str(log)


def parse_counts(text: str) -> str:
    """从子自测日志里抓通过计数（只用于报告；权威是退出码）。

    ⚠️ 三种汇总句式都要认，否则表里会出现 `(未解析到计数)` 这种**看起来像"0 项"**的空洞：

    1. `31/31 通过`（`check_stage9_loop.py`、`check_timing_convention.py` 等）；
    2. `共 42 项判据，未通过 0 项。`（`check_stage9_report.py` 与循环自测的现行句式）——
       中间那个词（"判据"）曾经把旧正则 `共\\s*(\\d+)\\s*项，未通过` 挡在门外，
       于是聚合表的计数列长期显示 `(未解析到计数)`；
    3. `===== 21/21 =====`（早期句式）。
    """
    m = re.search(r"(\d+)/(\d+)\s*通过", text)
    if m:
        return f"{m.group(1)}/{m.group(2)} 通过"
    m = re.search(r"共\s*(\d+)\s*项[^，\n]*，未通过\s*(\d+)\s*项", text)
    if m:
        return f"{int(m.group(1)) - int(m.group(2))}/{m.group(1)} 通过"
    m = re.search(r"=====\s*(\d+)/(\d+)\s*=====", text)
    if m:
        return f"{m.group(1)}/{m.group(2)} 通过"
    return "(未解析到计数)"


def doc_has_file(path: Path, name: str) -> bool:
    """某文档里是否登记了文件 `name`。

    **为什么不只查 `` `name` ``**：`Stage9_...md` §9 的工具表习惯写成
    `` `1_Code/AutoRA_SPE/stage9_inner.py` ``（带目录前缀），只查裸露的反引号名会
    误报"缺登记"。这里同时接受两种写法：裸名 `` `name` `` 或带前缀 `` /name` ``。
    ⚠️ 前缀那一路必须带 `/` —— 否则 `stage9_inner.py` 会被
    `check_stage9_inner.py` 里的子串满足，守卫就白设了。
    """
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return f"`{name}`" in text or f"/{name}`" in text


def main() -> int:
    t_start = time.time()
    quick = "--quick" in sys.argv
    n_fim_inner = 2
    if "--n-fim-inner" in sys.argv:
        n_fim_inner = int(sys.argv[sys.argv.index("--n-fim-inner") + 1])

    print("=" * 78)
    print("Stage 9 汇总自测")
    print(f"仓库根：{ROOT}")
    print(f"模式：{'quick（跳过内环/循环两档慢的）' if quick else '全套'}"
          f"、内环 n_fim = {n_fim_inner}")
    print("=" * 78)

    # ---------------- W 组：只有汇总层能做的漂移守卫（先做，快且与子自测无关）
    print("\n[W 组] 哈希与文件清单的漂移守卫")
    sys.path.insert(0, str(HERE))
    import stage9_objective as S9O  # noqa: E402

    recomputed = S9O.compute_sha256()
    check("W1 冻结规格的哈希是**算出来的**（`SPEC_SHA256` == `compute_sha256()`）"
          "且 `assert_frozen()` 不抛",
          S9O.SPEC_SHA256 == recomputed,
          f"SPEC_SHA256 = {S9O.SPEC_SHA256[:16]}…、重算 = {recomputed[:16]}…")
    try:
        S9O.assert_frozen()
        frozen_ok, frozen_msg = True, "无异常"
    except Exception as e:                                    # noqa: BLE001
        frozen_ok, frozen_msg = False, f"{type(e).__name__}: {e}"
    check("W1b `assert_frozen()` 通过（事前登记未被事后篡改）", frozen_ok, frozen_msg)

    readme_autora = HERE / "README.md"
    doc_stage9 = ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md"
    missing_autora = [f for f in STAGE9_FILES if not doc_has_file(readme_autora, f)]
    check(f"W2 {len(STAGE9_FILES)} 个 Stage 9 文件都登记在 `1_Code/AutoRA_SPE/README.md` §7 的文件清单里",
          not missing_autora,
          f"缺 {missing_autora}" if missing_autora else f"{len(STAGE9_FILES)} 个都在")
    missing_doc = [f for f in STAGE9_FILES if not doc_has_file(doc_stage9, f)]
    check(f"W3 {len(STAGE9_FILES)} 个 Stage 9 文件都登记在 `Stage9_设计空间优化与论文整合方案.md` 的 §9 工具表里",
          not missing_doc,
          f"缺 {missing_doc}" if missing_doc else f"{len(STAGE9_FILES)} 个都在")
    on_disk = [f for f in STAGE9_FILES if not (HERE / f).exists()]
    check(f"W4 {len(STAGE9_FILES)} 个文件都真的在磁盘上", not on_disk,
          f"缺 {on_disk}" if on_disk else f"{len(STAGE9_FILES)}/{len(STAGE9_FILES)}")

    # ---------------- 子自测
    print("\n[子自测] 逐个跑（输出重定向到文件）")
    subs: list[tuple[str, int, str]] = []

    code, text, _ = run_checker("check_timing_convention.py", [], "_scratch_agg_timing_u8.txt")
    subs.append(("check_timing_convention.py", code, parse_counts(text)))
    check("S1 时序口径桥自测通过", code == 0, subs[-1][2])

    code, text, _ = run_checker("stage9_objective.py", [], "_scratch_agg_objective_u8.txt")
    subs.append(("stage9_objective.py", code, parse_counts(text)))
    check("S2 冻结 Objective 的冒烟通过", code == 0, subs[-1][2])

    # S5 很便宜（几秒，不跑内环）⇒ 放在 quick 与全套都跑：它是**交付件**（报告）的唯一守卫。
    code, text, _ = run_checker("check_stage9_report.py", [], "_scratch_agg_report_u8.txt")
    subs.append(("check_stage9_report.py", code, parse_counts(text)))
    check("S5 落盘报告生成器自测通过", code == 0, subs[-1][2])

    if quick:
        print("\n（quick 模式：跳过 check_stage9_inner.py 与 check_stage9_loop.py）")
    else:
        code, text, _ = run_checker(
            "check_stage9_inner.py", [str(n_fim_inner), "_scratch_agg_inner_results_u8.txt"],
            "_scratch_agg_inner_u8.txt")
        subs.append((f"check_stage9_inner.py (n_fim={n_fim_inner})", code, parse_counts(text)))
        check("S3 内环自测通过", code == 0, subs[-1][2])

        code, text, _ = run_checker(
            "check_stage9_loop.py", ["1", "_scratch_agg_loop_results_u8.txt"],
            "_scratch_agg_loop_u8.txt")
        subs.append(("check_stage9_loop.py (n_fim=1)", code, parse_counts(text)))
        check("S4 优化循环自测通过", code == 0, subs[-1][2])

    # ---------------- 汇总
    n_bad = sum(1 for _, ok, _ in RESULTS if not ok)
    print("\n" + "=" * 78)
    print("| 子自测 | 退出码 | 通过计数 |")
    print("|---|---|---|")
    for name, c, cnt in subs:
        print(f"| `{name}` | {c} | {cnt} |")
    print(f"\n共 {len(RESULTS)} 项，未通过 {n_bad} 项；总耗时 {time.time() - t_start:.1f}s")
    if n_bad:
        for lab, ok, det in RESULTS:
            if not ok:
                print(f"  ❌ {lab} —— {det}")
        return 1
    print("✅ Stage 9 汇总自测全部通过")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
