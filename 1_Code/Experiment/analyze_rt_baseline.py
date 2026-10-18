# -*- coding: utf-8 -*-
"""analyze_rt_baseline.py —— 把 Stage 6 的行为量级阈值锚在历史真人数据上。

为什么需要它
------------
`analyze_pilot.py` 的 **S6-5** 用的是三条阈值：正确率 0.55–0.98、RT 中位 0.3–2.0 s、
过快（RT < 0.15 s）≤ 10%（口径：只在 `RT ≥ T` 的试次里算）。这三条是**判断**，不是数据推出来的。

第一场真实场次（60 Hz，v4.5，主试自己按键试跑）跑出正确率 0.485、RT 中位 0.069 s、
过快 56.2%、注视期抢按 74.8% ⇒ S6-5 / S6-1 双 FAIL。这就产生一个必须回答的问题：
**是这一场真的不是「人在做任务」，还是判据定得不对？**
唯一能回答它的证据，是这套范式下**真人**的行为分布 —— 本仓库里有 87 份
（`2_Data/Real_Data/UnExtact/emp_data`，旧 16 列口径，D4 之前那套 T/W 取值）。

本脚本做三件事（零依赖、只读）：
  1. 在参照集上算出 S6-5 关心的四个量的分布（min / q05 / 中位 / q95 / max）；
  2. 报告三条阈值各自会把多少份**历史真人文件**判成 FAIL —— 阈值越宽松、判失误报越少；
  3. 给出待评场次在参照分布里的百分位，回答「这场数据像不像人」。

注意（写进报告里，不要忽略）：参照集是**旧设计**（T/W 取值不同、无掩蔽、`RT` 下限由
「掩蔽期不读队列」的物理限制决定，历史最小 RT 中位 = 0.234 s ≈ T + 200 ms）。
因此它只能校准「像不像人在做任务」的量级，不能当作新设计的性能预期。

用法
----
    python analyze_rt_baseline.py [--ref <历史目录>] [--session <新数据文件/目录> ...]

    只给 `--ref`：打印参照分布 + 阈值误报率。
    给 `--session`：额外打印待评场次的四个量及其百分位。
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from pathlib import Path

FAST = 0.15          # S6-5 的「过快」口径（秒）
ACC_LO, ACC_HI = 0.55, 0.98
RT_LO, RT_HI = 0.30, 2.00
FAST_MAX = 0.10


def read_rows(path: Path) -> list[dict]:
    """读一个逐被试 CSV/txt，只要正式段。分隔符按首行嗅探（D83b 的教训）。"""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    head = text.split("\n", 1)[0]
    delim = "\t" if "\t" in head else ","
    rows = list(csv.DictReader(text.splitlines(), delimiter=delim))
    return [r for r in rows if (r.get("stage") or "").strip() == "formal"]


def stats(rows: list[dict]) -> dict | None:
    """四个量：RT 中位（已响应内）、正确率（已响应内）、过快比例（S6-5 口径）、漏答率。"""
    rt, correct, timeout, slow_enough, fast = [], 0, 0, 0, 0
    for r in rows:
        resp = (r.get("Response") or "").strip()
        try:
            v = float(r.get("RT"))
        except (TypeError, ValueError):
            v = float("nan")
        if not resp or v != v or resp.upper() in ("NA", "NAN"):
            timeout += 1
            continue
        try:
            t = float(r.get("T"))
        except (TypeError, ValueError):
            t = float("nan")
        rt.append(v)
        c = (r.get("Correct") or "").strip()
        if c in ("0", "1"):
            correct += int(float(c))
        # S6-5 的「过快」口径见 Stage6 §5.2：分母只算 RT >= T 的试次
        if t == t and v >= t:
            slow_enough += 1
            if v < FAST:
                fast += 1
    if not rt:
        return None
    return {
        "n": len(rows),
        "n_rt": len(rt),
        "rt_med": st.median(rt),
        "acc": correct / len(rt),
        "fast": fast / slow_enough if slow_enough else 0.0,
        "n_fast_denom": slow_enough,
        "timeout": timeout / len(rows),
    }


def quantile(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if not s:
        return float("nan")
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def pct_rank(vals: list[float], x: float) -> float:
    return sum(1 for v in vals if v <= x) / len(vals)


def collect(paths: list[Path]) -> list[dict]:
    out = []
    for p in paths:
        files = [p] if p.is_file() else sorted(p.glob("*.csv")) + sorted(p.glob("*.txt"))
        for f in files:
            try:
                rows = read_rows(f)
            except Exception as exc:                     # noqa: BLE001
                print("  ! 跳过 %s（%s）" % (f.name, exc), file=sys.stderr)
                continue
            s = stats(rows)
            if s:
                s["file"] = f.name
                out.append(s)
    return out


def report(ref: list[dict]) -> None:
    print("## 参照集：%d 份真人逐被试文件" % len(ref))
    print()
    print("| 量 | min | q05 | 中位 | q95 | max |")
    print("|---|---|---|---|---|---|")
    for key, name in [
        ("rt_med", "RT 中位（s）"),
        ("acc", "正确率（已响应内）"),
        ("fast", "过快比例（RT < %.2f s）" % FAST),
        ("timeout", "漏答率（占正式试次）"),
    ]:
        vals = [p[key] for p in ref]
        print("| %s | %.3f | %.3f | %.3f | %.3f | %.3f |" % (
            name, min(vals), quantile(vals, 0.05), st.median(vals), quantile(vals, 0.95), max(vals)))
    print()

    n = len(ref)
    n_acc = sum(1 for p in ref if not (ACC_LO <= p["acc"] <= ACC_HI))
    n_acc_lo = sum(1 for p in ref if p["acc"] < ACC_LO)
    n_rt = sum(1 for p in ref if not (RT_LO <= p["rt_med"] <= RT_HI))
    n_fast = sum(1 for p in ref if p["fast"] > FAST_MAX)
    print("## 三条 S6-5 阈值在参照集上的「误报」")
    print()
    print("| 阈值 | 判 FAIL 的历史文件 | 占比 |")
    print("|---|---|---|")
    print("| 正确率 ∉ [%.2f, %.2f] | %d / %d | %.1f%% |" % (ACC_LO, ACC_HI, n_acc, n, 100 * n_acc / n))
    print("| 　其中正确率 < %.2f | %d / %d | %.1f%% |" % (ACC_LO, n_acc_lo, n, 100 * n_acc_lo / n))
    print("| RT 中位 ∉ [%.2f, %.2f] s | %d / %d | %.1f%% |" % (RT_LO, RT_HI, n_rt, n, 100 * n_rt / n))
    print("| 过快 > %.0f%% | %d / %d | %.1f%% |" % (100 * FAST_MAX, n_fast, n, 100 * n_fast / n))
    print()
    print("读法：正确率那条会判掉 %d/%d 份历史真人数据 ⇒ 它是**保守阈值**（宁可多喊人看），"
          "不是「低于它就是坏数据」。" % (n_acc_lo, n))
    print("      过快那条在历史数据上 **0 份**超标（历史最小 RT 中位 %.3f s）⇒ 它对「乱按」很敏感，"
          "对正常被试几乎不误伤。" % min(p["rt_med"] for p in ref))
    print()


def report_session(ref: list[dict], sess: list[dict]) -> None:
    for s in sess:
        print("## 待评场次：`%s`（正式 %d 试次、已响应 %d）" % (s["file"], s["n"], s["n_rt"]))
        print()
        print("| 量 | 实测 | 参照集百分位 | 判读 |")
        print("|---|---|---|---|")
        for key, name, fmt in [
            ("rt_med", "RT 中位（s）", "%.3f"),
            ("acc", "正确率（已响应内）", "%.3f"),
            ("fast", "过快比例", "%.3f"),
            ("timeout", "漏答率", "%.3f"),
        ]:
            vals = [p[key] for p in ref]
            pr = pct_rank(vals, s[key])
            print("| %s | %s | P%.0f | %s |" % (name, fmt % s[key], 100 * pr,
                                              "低于全部历史" if pr == 0 else
                                              ("高于全部历史" if pr >= 1 - 1e-12 else "参照集内")))
        print()
        below = [p for p in ref if p["rt_med"] <= s["rt_med"]]
        print("- RT 中位 %.3f s 的百分位是 P%.0f ⇒ %d/%d 份历史真人数据比它慢。"
              % (s["rt_med"], 100 * pct_rank([p["rt_med"] for p in ref], s["rt_med"]),
                 len(ref) - len(below), len(ref)))
        inrange = [p for p in ref if abs(p["rt_med"] - s["rt_med"]) <= 0.01]
        print("- 参照集里 RT 中位落在 ±10 ms 内的文件数：%d" % len(inrange))
        print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 6 行为量级阈值的历史锚点")
    ap.add_argument("--ref", default="2_Data/Real_Data/UnExtact/emp_data",
                    help="历史逐被试数据目录（默认 2_Data/Real_Data/UnExtact/emp_data）")
    ap.add_argument("--session", nargs="*", default=[],
                    help="待评的新场次（文件或目录，可多个）")
    a = ap.parse_args(argv)

    refp = Path(a.ref)
    if not refp.exists():
        print("❌ 参照目录不存在：%s" % refp, file=sys.stderr)
        return 2
    ref = collect([refp])
    if not ref:
        print("❌ 参照集为空", file=sys.stderr)
        return 2
    report(ref)
    if a.session:
        sess = collect([Path(s) for s in a.session])
        if not sess:
            print("❌ 待评场次读不出正式段", file=sys.stderr)
            return 2
        report_session(ref, sess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
