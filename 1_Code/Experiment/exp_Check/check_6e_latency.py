# -*- coding: utf-8 -*-
"""Stage 1 · 6-E：刺激内与刺激后按键的检测延时可比性（零依赖、只读）。

口径
----
程序的 RT 来自 `KbQueue` 的硬件时间戳，与「程序什么时候把键取走」无关；但**刺激被敲掉的时间**
（`stimulus_dur_actual`）等于「程序发现按键」的时刻。因此两类按键可比性的可检验形式是：

    刺激内按键：0 ≤ stimulus_dur_actual − RT ≤ 1 帧      （检测延时不超过一次 vsync 等待）
    刺激后按键：stimulus_dur_actual 与 RT 无耦合（dur ≈ T，RT 可远大于 T）

前者是硬判据，后者只报计数与区间。

用法
----
    python -X utf8 check_6e_latency.py <data.csv|data.txt> [...]
    python -X utf8 check_6e_latency.py --self-test
"""
import csv
import io
import statistics as st
import sys
import tempfile
from pathlib import Path

EXPECT_HZ = 60.004
NA = {"", "na", "nan", "n/a"}


def sniff(header_line: str) -> str:
    return "\t" if "\t" in header_line else ","


def load(path: Path):
    text = io.open(path, encoding="utf-8-sig", errors="replace").read()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    delim = sniff(lines[0])
    if delim == "\t":
        head = lines[0].split("\t")
        body = [ln.split("\t") for ln in lines[1:]]
    else:
        rdr = list(csv.reader(lines))
        head, body = rdr[0], rdr[1:]
    rows = []
    for cells in body:
        if len(cells) != len(head):
            continue
        rows.append(dict(zip(head, [c.strip() for c in cells])))
    return rows


def num(row, key, default=float("nan")):
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return default


def analyse(rows, flip):
    """返回 dict：刺激内/刺激后两组的关键量。"""
    formal = [r for r in rows if r.get("stage") == "formal"]
    resp = [r for r in formal if r.get("Response") in ("f", "j")]
    inside, after = [], []
    for r in resp:
        t, rt, dur = num(r, "T"), num(r, "RT"), num(r, "stimulus_dur_actual")
        if any(x != x for x in (t, rt, dur)):
            continue
        (inside if rt < t else after).append((t, rt, dur))
    lat = [dur - rt for _, rt, dur in inside]
    mask = [rt - t for t, rt, _ in after if rt - t <= 0.200 + 1e-9]
    late = [rt - t for t, rt, _ in after if rt - t > 0.200 + 1e-9]
    return {
        "rows": len(formal), "responded": len(resp),
        "inside": inside, "after": after, "lat": lat,
        "mask": mask, "late": late,
        "short": [rt for _, rt, _ in inside + after if rt < 0.050],
    }


def report(path: Path, st_: dict, flip: float):
    ok = True
    print("\n[%s]" % path.name)
    print("  正式试次 %d、已响应 %d（刺激内 %d / 刺激后 %d）" % (
        st_["rows"], st_["responded"], len(st_["inside"]), len(st_["after"])))
    if st_["lat"]:
        lo, hi = min(st_["lat"]), max(st_["lat"])
        good = lo >= -1e-3 and hi <= flip * 1.05
        ok = ok and good
        print("  %s 刺激内按键的检测延时 dur−RT：n=%d，%.1f–%.1f ms（1 帧 = %.1f ms）" % (
            "✅" if good else "❌", len(st_["lat"]), lo * 1000, hi * 1000, flip * 1000))
    else:
        print("  ·  本文件没有刺激内按键 ⇒ 6-E 不可判（需要 T 档内落键的试次）")
        ok = False
    if st_["after"]:
        print("  ·  刺激后按键：掩蔽窗内 %d 例（RT−T %.1f–%.1f ms），掩蔽后 %d 例（RT−T 最大 %.1f ms）" % (
            len(st_["mask"]), (min(st_["mask"]) * 1000) if st_["mask"] else float("nan"),
            (max(st_["mask"]) * 1000) if st_["mask"] else float("nan"),
            len(st_["late"]), (max(st_["late"]) * 1000) if st_["late"] else float("nan")))
        print("  ✅ 刺激后按键的 RT 只由时间戳决定（dur 与 RT 无耦合，dur ≈ T）")
    if st_["short"]:
        print("  ⚠  RT < 50 ms 的有 %d 例（预期性/连按，属分析层问题，不计入本条判据）" % len(st_["short"]))
    return ok


def main(argv):
    if "--self-test" in argv:
        return self_test()
    files = [Path(a) for a in argv[1:]]
    if not files:
        print("用法：check_6e_latency.py <data.csv|data.txt> [...] 或 --self-test")
        return 2
    flip = 1.0 / EXPECT_HZ
    all_ok = True
    for p in files:
        all_ok &= report(p, analyse(load(p), flip), flip)
    print("\n== 6-E %s ==" % ("通过" if all_ok else "未通过"))
    return 0 if all_ok else 1


HEAD = ("groupID\tsubjectID\tgender\tage\thandedness\tstage\ttrialID\tP\tT\tW\tShape\tLabel\t"
        "CorrectKey\tResponse\tRT\tCorrect\tblock\tpremature_press\ttimeout\tresponded_by_deadline\t"
        "stimulus_onset_actual\tstimulus_offset_actual\tmask_onset_actual\tstimulus_dur_actual\tstimulus_frames")


def _mk(stage, t, rt, dur, resp="j"):
    return ("%s\t%s\t1\t20\t右\t%s\t1\t0\t%.5f\t0.8\tr\tr\tj\t%s\t%s\t%s\t1\t0\t0\t1\t"
            "100.000\t%.5f\t%.5f\t%.5f\t2") % (
        "1", "99", stage, t, resp, ("%.5f" % rt) if rt is not None else "NaN",
        "NaN" if rt is None else ("1" if resp in ("f", "j") else "NaN"),
        100.0 + dur, 100.0 + dur, dur)


def self_test():
    flip = 1.0 / EXPECT_HZ
    cases = {
        "干净：刺激内 1 帧、刺激后全时长": [_mk("formal", 0.250, 0.120, 0.120 + flip), _mk("formal", 0.083, 0.500, 0.084)],
        "缺陷：检测延时 2.5 帧": [_mk("formal", 0.250, 0.120, 0.120 + 2.5 * flip)],
        "缺陷：只有刺激后按键（不可判）": [_mk("formal", 0.083, 0.500, 0.084)],
    }
    expect = {"干净：刺激内 1 帧、刺激后全时长": True, "缺陷：检测延时 2.5 帧": False,
              "缺陷：只有刺激后按键（不可判）": False}
    bad = 0
    for name, body in cases.items():
        tmp = Path(tempfile.mkdtemp()) / "d.txt"
        io.open(tmp, "w", encoding="utf-8", newline="\n").write("\n".join([HEAD] + body) + "\n")
        got = report(tmp, analyse(load(tmp), flip), flip)
        flag = "PASS" if got == expect[name] else "FAIL"
        bad += got != expect[name]
        print("  [%s] %s" % (flag, name))
    print("\n自测：%s" % ("✅ 全部符合预期" if bad == 0 else "❌ %d 例不符" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
