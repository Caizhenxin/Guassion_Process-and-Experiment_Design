"""离线复核四臂裁决：把落盘件里的 `(A,B)` 用**另一根噪声带**重新判一次（只读）。

为什么需要它
------------
`1_Code/AutoRA_SPE/stage9_loop.py::compare_arms` 的每一条裁决都是一次**带门槛**的比较
（`ΔA` 对 `2·sd_A`、`ΔB` 对 `2·sd_B`），而这两根带子来自 `measure_noise()` 的
`n_repeats` 次重抽。D59 的实测（`_scratch_anchor_seed_scan.py`）表明：

* `n_fim = 1` 下旧标定族（同族**算术邻居**）给 `sd_A = 0.004779`，
  而 48 个**无关**种子给 `0.018933`（**4.0 倍**）；
* `n_fim = 12` 下两者相当（旧族 `0.008586` vs 12 个无关种子 `0.006897`）。

⇒ **同一份 `(A,B)` 读数、换一根带子，裁决会变**。哪些结论是"设计差异"、哪些只是
"带子太窄"，必须能离线分开看。本脚本不做任何新模拟，只重跑判据。

做法
----
读 payload 的 `histories`，把 `noise` 段复制一份并替换 `sd_A` / `sd_B`，
调 `stage9_loop.compare_arms()` 两次（旧带 / 新带），逐臂并列打印，
并给出「锚点 D4 与最优可行设计的 `ΔA` 各等于几倍带子」。

用法
----
    python -u 1_Code/AutoRA_SPE/_scratch_reverdict.py <payload.json> [sd_a] [sd_b]
    python -u 1_Code/AutoRA_SPE/_scratch_reverdict.py <payload.json> --sd-a 0.0189 --sd-b 0.1881

第二个/第三个位置参数给出时按 `sd` 覆盖；不给则只打印原有裁决。
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import stage9_loop as L   # noqa: E402


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _norm_histories(hist: dict) -> dict:
    """兼容 D57 之前的键名 `B_at_best_A`（`compare_arms` 只认 `B_at_A_best`）。"""
    out = {}
    for arm, h in hist.items():
        h2 = dict(h)
        if "B_at_A_best" not in h2 and "B_at_best_A" in h2:
            h2["B_at_A_best"] = h2["B_at_best_A"]
        h2.setdefault("A_best_name", "")
        h2.setdefault("B_max", float("nan"))
        h2.setdefault("seconds", 0.0)
        out[arm] = h2
    return out


def _show(title: str, rows: list[dict], band_a: float, band_b: float) -> None:
    print(f"\n=== {title} ===")
    print(f"门槛：2·sd_A = {band_a:.4f}、2·sd_B = {band_b:.4f}")
    for r in rows:
        a_s = "—" if not np.isfinite(r["A_best"]) else f"{r['A_best']:.4f}"
        b_s = "—" if not np.isfinite(r["B_at_A_best"]) else f"{r['B_at_A_best']:.4f}"
        print(f"  [{r['arm']:>7}] A_best = {a_s}  B@A_best = {b_s}  "
              f"可行 {r['n_feasible']}  ΔA = {r['dA_vs_best']:+.4f}")
        print(f"      → {r['verdict']}")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    if not os.path.isfile(path):
        print(f"❌ 找不到 {path}")
        return 2
    d = _load(path)

    sd_a_new = sd_b_new = None
    rest = argv[1:]
    if "--sd-a" in rest:
        sd_a_new = float(rest[rest.index("--sd-a") + 1])
    if "--sd-b" in rest:
        sd_b_new = float(rest[rest.index("--sd-b") + 1])
    if "--sd-a" not in rest and rest:
        sd_a_new = float(rest[0])
    if "--sd-b" not in rest and len(rest) >= 2:
        sd_b_new = float(rest[1])

    st = d.get("settings", {})
    noise = dict(d.get("noise", {}))
    hist = _norm_histories(d.get("histories", {}))
    print(f"# 落盘件：{path}")
    print(f"#   settings = {st}")
    print(f"#   n_repeats = {noise.get('n_repeats')}、"
          f"标定种子 = {noise.get('seeds', '（未记录 —— D59 之前）')}")
    print(f"#   sd_A = {noise.get('sd_A')}、sd_B = {noise.get('sd_B')}、"
          f"sd_J = {noise.get('sd_J')}、alpha = {noise.get('alpha')}")
    print(f"#   front_scope = {d.get('front_scope')}")

    rows_old = L.compare_arms(hist, noise)
    _show("原判决（落盘件自己的带子）", rows_old,
          2.0 * float(noise.get("sd_A", 0.0)), 2.0 * float(noise.get("sd_B", 0.0)))

    if sd_a_new is not None or sd_b_new is not None:
        n2 = dict(noise)
        if sd_a_new is not None:
            n2["sd_A"] = float(sd_a_new)
        if sd_b_new is not None:
            n2["sd_B"] = float(sd_b_new)
        rows_new = L.compare_arms(hist, n2)
        _show(f"换带重判（sd_A = {n2['sd_A']}、sd_B = {n2['sd_B']}）", rows_new,
              2.0 * float(n2.get("sd_A", 0.0)), 2.0 * float(n2.get("sd_B", 0.0)))

        # 逐臂对照
        old = {r["arm"]: r["verdict"] for r in rows_old}
        new = {r["arm"]: r["verdict"] for r in rows_new}
        print("\n=== 变了的臂 ===")
        n_same = 0
        for arm in old:
            if old[arm] == new.get(arm):
                n_same += 1
                continue
            print(f"  [{arm}]")
            print(f"    旧：{old[arm]}")
            print(f"    新：{new.get(arm)}")
        print(f"  （{len(old) - n_same}/{len(old)} 条变了）")

    # 锚点 vs 最优可行设计的 ΔA，两种带子下各是几倍
    anc = d.get("anchor") or {}
    best = d.get("best") or {}
    if anc.get("A") is not None and best.get("A") is not None:
        da = float(anc["A"]) - float(best["A"])
        print("\n=== 锚点 D4 离最优可行设计多远 ===")
        print(f"  锚点 A = {float(anc['A']):.6f}、最优可行 A = {float(best['A']):.6f}、"
              f"ΔA = {da:+.6f}")
        for lab, sd in (("落盘件带子", float(noise.get("sd_A", 0.0))),
                        ("新带子", float(sd_a_new) if sd_a_new is not None else None)):
            if sd:
                print(f"  {lab}：2·sd_A = {2 * sd:.6f} ⇒ ΔA = **{da / (2 * sd):.2f} 倍**带子")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
