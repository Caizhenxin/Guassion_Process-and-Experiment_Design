"""Stage 6 Pilot 的「时间压力操纵检查」：三档 W 到底有没有真的压住被试。

为什么单独写一个而不是塞进 `read_formal_data.py`：
    后者是**数据完整性**检查（25 列、枚举、时间戳自洽、RT 与响应一致），
    回答「这份数据能不能进模型」；本脚本回答的是**设计问题**——
    「W = 800 / 1200 / 1800 ms 是否在行为上真的构成截止约束」。
    两者判据不同、失败含义不同，混在一起会让「读取器报红」变成噪音。

判据（写死在 `--expect-gap`，默认 0.10，来自设计文档 §3.3 ⑤）：
    omission(800) - omission(1800) >= 10 个百分点
    且 800 档 RT 中位数被压到「净可按键窗口」下沿（RT_p50 >= W - T - 0.2 的比例够高）
    ⇒ 操纵成立；否则按 §3.3 ⑤ 的备选处理（报告 W 不可识别 / 加档）。

净可按键时间（设计文档 §3.3 ②）：
    从刺激 onset 到截止 = W；刺激期 T（D5 按键即结束）；掩蔽/空白 200 ms
    ⇒ 掩蔽结束后还能按多久 = W - T - 0.2

用法::

    python 1_Code/Experiment/check_manipulation.py <csv 或目录> [--expect-gap 0.10] [--per-cell]

说明：本项目的无屏幕冒烟产物（`exp_matlab/test/_full_session_out/`）是**桩造的假数据**，
按键剧本按试次号取模，三档 W 的漏答率必然相同 —— 用它跑通只证明脚本能读、能算、能判，
不构成操纵证据。
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MASK = 0.2
LEVELS = (0.8, 1.2, 1.8)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """二项比例的 Wilson 区间（小样本下比正态近似稳，n=8 也能用）。"""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def to_float(s: str) -> float:
    s = (s or "").strip()
    if s in ("", "NA", "NaN", "nan"):
        return float("nan")
    return float(s)


def load(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        if (r.get("stage") or "").strip() != "formal":
            continue  # 练习段的 block=0、W 也写 0.8，混进来会把 800 档的漏答率抬高
        rt = to_float(r.get("RT", ""))
        w = to_float(r.get("W", ""))
        t = to_float(r.get("T", ""))
        resp = (r.get("Response") or "").strip()
        timed_out = to_float(r.get("timeout", "")) == 1.0
        out.append(
            {
                "W_ms": int(round(w * 1000)),  # D87：按整毫秒归组，避免 0.7999 ≠ 0.8
                "T": round(t, 4),
                "RT": rt,
                "omission": timed_out or resp in ("", "NA") or math.isnan(rt),
                "responded_by_deadline": to_float(r.get("responded_by_deadline", "")) == 1.0,
                "file": path.name,
            }
        )
    return out


def summarize(rows: list[dict], per_cell: bool, expect_gap: float = 0.10) -> tuple[bool, list[str]]:
    lines: list[str] = []
    by_w: dict[int, list[dict]] = {}
    for r in rows:
        by_w.setdefault(r["W_ms"], []).append(r)

    lines.append(f"{'W(ms)':>7} {'n':>5} {'漏答':>6} {'漏答率':>8} {'95%CI':>18} "
                 f"{'RT中位':>8} {'RT p10-p90':>18} {'贴边占比':>9}")
    lines.append("-" * 92)
    stat: dict[int, dict] = {}
    for w_ms in sorted(by_w):
        rs = by_w[w_ms]
        w = w_ms / 1000.0
        n = len(rs)
        k = sum(1 for r in rs if r["omission"])
        lo, hi = wilson(k, n)
        rts = sorted(r["RT"] for r in rs if not r["omission"] and not math.isnan(r["RT"]))
        p50 = statistics.median(rts) if rts else float("nan")
        p10 = rts[int(0.10 * (len(rts) - 1))] if rts else float("nan")
        p90 = rts[int(0.90 * (len(rts) - 1))] if rts else float("nan")
        # 贴边：RT 落在截止前 100 ms 之内 ⇒ 被试是被窗口逼到边上的
        edge = sum(1 for x in rts if x >= w - 0.1) / len(rts) if rts else float("nan")
        stat[w_ms] = {"n": n, "k": k, "rate": k / n, "p50": p50, "edge": edge}
        lines.append(
            f"{w*1000:7.0f} {n:5d} {k:6d} {k/n:8.1%} "
            f"[{lo:6.1%}, {hi:6.1%}] {p50*1000:8.1f} "
            f"{p10*1000:7.1f}-{p90*1000:7.1f} {edge:9.1%}"
        )

    if per_cell:
        lines.append("")
        lines.append("逐 (W, T) 单元：n / 漏答率 / 净可按键时间(ms)")
        lines.append(f"{'W(ms)':>7} {'T(ms)':>7} {'n':>5} {'漏答率':>8} {'净窗口':>8}")
        cells: dict[tuple[int, float], list[dict]] = {}
        for r in rows:
            cells.setdefault((r["W_ms"], r["T"]), []).append(r)
        for (w_ms, t) in sorted(cells):
            rs = cells[(w_ms, t)]
            k = sum(1 for r in rs if r["omission"])
            lines.append(f"{w_ms:7d} {t*1000:7.1f} {len(rs):5d} {k/len(rs):8.1%} "
                         f"{(w_ms/1000.0 - t - MASK)*1000:8.0f}")

    lines.append("")
    ok = True
    if 800 in stat and 1800 in stat:
        gap = stat[800]["rate"] - stat[1800]["rate"]
        need = stat[800]["edge"]
        lines.append(f"判据 ①：漏答率差（800 − 1800）= {gap:+.1%}（要求 ≥ +{expect_gap:.0%}）")
        lines.append(f"判据 ②：800 档 RT 贴边占比 = {need:.1%}（要求 > 0，理想 ≥ 20%）")
        monotone = all(
            stat[a]["rate"] >= stat[b]["rate"] - 0.05
            for a, b in ((800, 1200), (1200, 1800))
            if a in stat and b in stat
        )
        lines.append(f"判据 ③：漏答率随 W 单调不升（容差 5 pp）：{'成立' if monotone else '不成立'}")
        ok = gap >= expect_gap and monotone
    else:
        lines.append("⚠️ 缺 800 或 1800 档，无法判定（是否只读了部分 block？）")
        ok = False
    lines.append("")
    lines.append("⇒ 操纵" + ("成立：截止时间在行为上确实是约束" if ok else
                              "未通过：按设计文档 §3.3 ⑤ 处理（报 W 不可识别，或加档重估）"))
    return ok, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 6 操纵检查：三档 W 的漏答率与 RT 贴边")
    ap.add_argument("paths", nargs="+", help="CSV 文件或包含 CSV 的目录")
    ap.add_argument("--expect-gap", type=float, default=0.10, help="800 vs 1800 的最小漏答率差")
    ap.add_argument("--per-cell", action="store_true", help="额外打印 (W, T) 单元表")
    args = ap.parse_args(argv)

    files: list[Path] = []
    for p in map(Path, args.paths):
        if p.is_dir():
            files.extend(sorted(p.glob("*.csv")))
        elif p.is_file():
            files.append(p)
    if not files:
        print("❌ 没有找到 CSV")
        return 1

    rows: list[dict] = []
    for f in files:
        rows.extend(load(f))
    if not rows:
        print("❌ 读到了文件但没有 formal 试次")
        return 1

    print(f"读取 {len(files)} 个文件、{len(rows)} 个正式试次：")
    for f in files:
        print(f"  - {f.name}")
    print()
    ok, lines = summarize(rows, args.per_cell, args.expect_gap)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
