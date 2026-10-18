# -*- coding: utf-8 -*-
"""D87：修两个「判据本身写错」的缺陷（幂等、逐处断言命中 1 次）。

1) `exp_Check/check_stage1_acceptance.py`
   `estimate_flip()` 用 `median(stimulus_dur_actual / stimulus_frames)` 反推
   FlipIntv。但第 25 列是 `round(dur / FlipIntv)`，而 dur 比名义时长多 0~1 帧
   （vsync 余量）⇒ 比值把余量整份算进一帧里，小 T 档被抬得最狠。
   60.004 Hz 实机实测：中位 17.02 ms ⇒ 读成 58.7 Hz（偏 2.1%），
   进而把正常行判成缺陷（`frames=10 ≠ round(dur/17.02ms)=9`），
   并让环境门（D81c）把这块 60.004 Hz 的屏判成「证据降级」。
   改为解约束：在 5~25 ms 上以 0.01 ms 步长搜索，
   取「满足 `round(dur/flip) == frames` 的行数最多」那段平台的中位数。
   同时给 `--self-test` 加一例：用**真实实机的 (dur, frames) 数对**做回归，
   断言新估计器偏差 < 1%、而旧的 `median(dur/frames)` 偏差 > 1.5%。

2) `check_manipulation.py`
   `load()` 存的是 `round(W, 4)`（如 0.7999），`summarize()` 却用
   `0.8 in stat` 判「有没有 800 档」⇒ 永远 False ⇒ 明明三个 W 档都在，
   却打「⚠️ 缺 800 或 1800 档，无法判定」。改为按整毫秒 `W_ms` 归组。

用法： python -X utf8 _apply_d87_flip_and_wlevels.py
"""
from __future__ import annotations

import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1] / "Experiment"
CHK = EXP / "exp_Check" / "check_stage1_acceptance.py"
MAN = EXP / "check_manipulation.py"

OLD_EST = '''    est = []
    for r in rows:
        dur = num(r.get("stimulus_dur_actual"))
        fr = num(r.get("stimulus_frames"))
        if dur > 0 and fr >= 1 and math.isfinite(fr):
            est.append(dur / fr)
    if not est:
        return float("nan")
    est.sort()
    return est[len(est) // 2]
'''

NEW_EST = '''    pts: list[tuple[float, int]] = []
    for r in rows:
        dur = num(r.get("stimulus_dur_actual"))
        fr = num(r.get("stimulus_frames"))
        if dur > 0 and fr >= 1 and math.isfinite(fr):
            pts.append((dur * 1000.0, int(round(fr))))
    if not pts:
        return float("nan")
    # 网格搜索：真值必须让尽可能多的行满足 round(dur/flip) == frames。
    # 步长 0.01 ms（对 16.67 ms 是 0.06%），搜索区间 5~25 ms 覆盖 40~200 Hz。
    best_n, best: int, list[float] = -1, []
    flip_ms = 5.0
    while flip_ms <= 25.0 + 1e-9:
        n = sum(1 for d, f in pts if round(d / flip_ms) == f)
        if n > best_n:
            best_n, best = n, [flip_ms]
        elif n == best_n:
            best.append(flip_ms)
        flip_ms = round(flip_ms + 0.01, 4)
    return (best[0] + best[-1]) / 2.0 / 1000.0
'''

OLD_DOC_TAIL = '''    （165 Hz 实机：算出 5.83 ms，真值 6.06 ms，低 4%），进而把正常行判成缺陷。
    """
'''

NEW_DOC_TAIL = '''    （165 Hz 实机：算出 5.83 ms，真值 6.06 ms，低 4%），进而把正常行判成缺陷。

    ⚠️ D87：也不能用 `median(dur / frames)`（D81 的写法）。dur 比名义时长多
    0~1 帧，这个余量被整份摊进一帧里，T 越小抬得越狠：60.004 Hz 实机实测
    中位 17.02 ms（真值 16.666 ms，偏 +2.1%）⇒ 读成 58.7 Hz，于是
    ① 6-C 的 `frames == round(dur/flip)` 把 1 行正常数据判成缺陷；
    ② 环境门把这块真·60.004 Hz 的屏判成「证据降级」。
    改为**解约束**（见下），不再依赖任何单一比值。
    """
'''

OLD_SELFTEST_ANCHOR = '''            print(f"  {'✅' if ok else '❌'} {name}：判为未通过、拦住 {key} = "
                  f"{'✅' if hit else '❌'}")
    print()
'''

NEW_SELFTEST_ANCHOR = '''            print(f"  {'✅' if ok else '❌'} {name}：判为未通过、拦住 {key} = "
                  f"{'✅' if hit else '❌'}")

        # 用例（D87）：帧量化反推的稳健性。用**真实实机**的 (dur, frames) 数对
        # （60.004 Hz 那场，含 0~1 帧 vsync 余量与截断行）。旧的 `median(dur/frames)`
        # 会给出 17.02 ms（+2.1%）并连带判错 6-C 与环境门；新估计器必须 < 1%。
        REAL_PAIRS = [(8.336, 1), (25.491, 2), (33.331, 2), (41.664, 3), (42.164, 3),
                      (58.759, 4), (75.491, 5), (91.241, 5), (149.990, 9),
                      (158.633, 10), (249.168, 15), (254.879, 15)]
        flip_true = 1.0 / 60.004
        pairs_rows = [{"stimulus_dur_actual": str(d / 1000.0),
                       "stimulus_frames": str(f)} for d, f in REAL_PAIRS]
        ratios = sorted(d / f for d, f in REAL_PAIRS)
        naive = ratios[len(ratios) // 2] / 1000.0
        est = estimate_flip(pairs_rows)
        rel_new = abs(est - flip_true) / flip_true
        rel_old = abs(naive - flip_true) / flip_true
        ok = rel_new < 0.01 and rel_old > 0.015
        print(f"  {'✅' if ok else '❌'} 帧量化反推稳健性：新估计器 {est * 1000:.3f} ms"
              f"（偏 {rel_new:+.2%}）｜旧 `median(dur/frames)` {naive * 1000:.3f} ms"
              f"（偏 {rel_old:+.2%}，需 > 1.5% 才算本用例有牙）")
        if not ok:
            fails += 1
    print()
'''

MAN_EDITS = [
    ('                "W": round(w, 4),',
     '                "W_ms": int(round(w * 1000)),  # D87：按整毫秒归组，避免 0.7999 ≠ 0.8'),
    ('''    by_w: dict[float, list[dict]] = {}
    for r in rows:
        by_w.setdefault(r["W"], []).append(r)''',
     '''    by_w: dict[int, list[dict]] = {}
    for r in rows:
        by_w.setdefault(r["W_ms"], []).append(r)'''),
    ('''    stat: dict[float, dict] = {}
    for w in sorted(by_w):
        rs = by_w[w]''',
     '''    stat: dict[int, dict] = {}
    for w_ms in sorted(by_w):
        rs = by_w[w_ms]
        w = w_ms / 1000.0'''),
    ('        stat[w] = {"n": n, "k": k, "rate": k / n, "p50": p50, "edge": edge}',
     '        stat[w_ms] = {"n": n, "k": k, "rate": k / n, "p50": p50, "edge": edge}'),
    ('''        cells: dict[tuple[float, float], list[dict]] = {}
        for r in rows:
            cells.setdefault((r["W"], r["T"]), []).append(r)
        for (w, t) in sorted(cells):
            rs = cells[(w, t)]
            k = sum(1 for r in rs if r["omission"])
            lines.append(f"{w*1000:7.0f} {t*1000:7.1f} {len(rs):5d} {k/len(rs):8.1%} "
                         f"{(w - t - MASK)*1000:8.0f}")''',
     '''        cells: dict[tuple[int, float], list[dict]] = {}
        for r in rows:
            cells.setdefault((r["W_ms"], r["T"]), []).append(r)
        for (w_ms, t) in sorted(cells):
            rs = cells[(w_ms, t)]
            k = sum(1 for r in rs if r["omission"])
            lines.append(f"{w_ms:7d} {t*1000:7.1f} {len(rs):5d} {k/len(rs):8.1%} "
                         f"{(w_ms/1000.0 - t - MASK)*1000:8.0f}")'''),
    ('    if 0.8 in stat and 1.8 in stat:', '    if 800 in stat and 1800 in stat:'),
    ('        gap = stat[0.8]["rate"] - stat[1.8]["rate"]',
     '        gap = stat[800]["rate"] - stat[1800]["rate"]'),
    ('        need = stat[0.8]["edge"]', '        need = stat[800]["edge"]'),
    ('            for a, b in ((0.8, 1.2), (1.2, 1.8))',
     '            for a, b in ((800, 1200), (1200, 1800))'),
]


def patch(path: Path, edits: list[tuple[str, str]], marker: str) -> int:
    text = io.open(path, encoding="utf-8").read()
    if marker in text:
        print(f"  = {path.name}：已打过补丁，跳过")
        return 0
    n = 0
    for old, new in edits:
        cnt = text.count(old)
        if cnt != 1:
            raise SystemExit(f"❌ {path.name}：命中 {cnt} 次（应为 1）\n---\n{old[:200]}")
        text = text.replace(old, new, 1)
        n += 1
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    print(f"  ✅ {path.name}：{n} 处")
    return n


def main() -> int:
    print("D87 补丁：")
    patch(CHK, [(OLD_DOC_TAIL, NEW_DOC_TAIL), (OLD_EST, NEW_EST),
                (OLD_SELFTEST_ANCHOR, NEW_SELFTEST_ANCHOR)], "D87：也不能用")
    patch(MAN, MAN_EDITS, '"W_ms": int(round(w * 1000))')
    print("完成。下一步：两个 --self-test + 对实机 CSV 复跑。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
