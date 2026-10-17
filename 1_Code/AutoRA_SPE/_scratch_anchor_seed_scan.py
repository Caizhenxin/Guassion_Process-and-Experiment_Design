"""锚点/单设计 `(A)` 的**种子间分布**：`2·sd_A` 这根带子到底有多可靠？（只读）

调查背景（D58）
---------------
`1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py` 的第一版读数（`n_fim = 1`、锚点 D4）：

* **CRN**（判据实际用的种子，`cell_seed(D4, 0)` = 1820496569）：`A = 0.385802`；
* **noise** 族（标定带宽用的 6 个种子 `cell_seed(D4, 791_900 + 37k)`，
  即**算术邻居**）：均值 `0.354077`、`sd = 0.004779`；
* **无关种子** 24 个：均值 `0.359310`、**`sd = 0.019226`**（约为 noise 族的 **4.02 倍**）。

⇒ 标定用的 `sd_A` 可能小 4 倍，而 `2·sd_A` 正是所有「不可分辨 / 显著更差 / 被支配」
裁决的门槛，也是 `alpha = sd_J²`（BO 的探索尺度）的来源。

两个竞争假设
------------
* **H1「算术邻居」**：`np.random.default_rng(s + 37k)` 的流彼此相关 ⇒ 邻居族天然更紧。
  检验法：另起一族**同样间距 37、但基点不同**的邻居种子（`base + 4_000_000 + 37k`）；
  若它也异常紧 ⇒ 支持 H1。
* **H2「分布本身是多峰的」**：`A` 随种子的分布不是单峰正态，而是两簇
  （第一版 24 个读数里约 14 个落在 0.343–0.356、约 10 个落在 0.367–0.391）；
  6 个邻居种子恰好只抽到低簇 ⇒ 样本 `sd` 系统性偏小。检验法：加大 `n`，
  打印**直方图 + 分位数 + 稳健尺度**（`MAD`、`IQR`），看是否仍是两簇。

本脚本
------
固定锚点设计、`rho = 0.6`、`n_subjects = 40`、`P = None`、`param_set = "exp"`，
在给定 `n_fim` 下扫四族种子并打印逐次读数、族内统计、**直方图**与**稳健尺度**：

* `CRN`：`cell_seed(D4, 0)`；
* `noise`：`cell_seed(D4, 791_900 + 37k), k = 0..5`（现行标定族，算术邻居）；
* `near`：`cell_seed(D4, 4_000_000 + 37k), k = 0..5`（**另一族算术邻居**，检验 H1）；
* `unrel`：`default_rng(20261016).integers(...)` 抽的 `n_unrel` 个无关种子。

用法
----
    python -u 1_Code/AutoRA_SPE/_scratch_anchor_seed_scan.py [n_fim] [n_unrel] [out_txt] [design_name]

`n_fim` 默认 1、`n_unrel` 默认 48、`design_name` 默认锚点 `L.ANCHOR_DESIGN`。
`n_fim = 12` 单次约 25–40 s（`n_unrel = 12` 约 8 min）。第三参数给出时把结果同时
写进该文本文件（默认只打屏）。

❗ **D60 起支持第四个参数（设计名）**：判据带宽要用在**任意两个设计**的差上，
而 `sd_A` 只在锚点处量过 ⇒ 「同方差假设」需要实测。逐设计量 `sd_A`：
`design_name` 指定为候选集里的**完整设计名**（`L.enumerate_designs()` 的 `name`，
形如 `T[...]ms x W[...]ms x r16`）；不给则仍是锚点 D4。
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import stage9_loop as L          # noqa: E402
import stage9_inner as S9I       # noqa: E402
import stage9_objective as S9O   # noqa: E402

SUBJECTS = 40
RHO = 0.6
PARAM_SET = "exp"
NOISE_BASE = 791_900
NEAR_BASE = 4_000_000
STRIDE = 37
N_FAMILY = 6


def _one(design: dict, *, n_fim: int, seed: int) -> dict:
    """与 `Evaluator._raw` + `_objective_record` 完全同路的一次评估。"""
    res = S9I.inner_eval(L.levels_sec(design["T_ms"]), L.levels_sec(design["W_ms"]),
                         design["n_rep"], model=S9I.M_T1, rho=RHO, n_fim=n_fim,
                         seed=int(seed), param_set=PARAM_SET, P=None)
    return {
        "A": float(S9O.component_A(res)),
        "B": float(S9O.component_B(float(res["se_rho"]), SUBJECTS)),
        "omission": float(res["omission"]),
        "cond": float(res.get("cond", float("nan"))),
        "n_bad": int(res.get("n_bad", 0)),
        "rt_ms": float(res.get("rt_ms", float("nan"))),
        "acc": float(res.get("acc", float("nan"))),
    }


def _stats(vals) -> dict:
    a = np.asarray(vals, dtype=float)
    med = float(np.median(a))
    mad = float(np.median(np.abs(a - med))) * 1.4826          # 正态一致尺度
    q1, q3 = (float(v) for v in np.percentile(a, [25, 75]))
    return {"n": int(a.size), "mean": float(a.mean()),
            "sd": float(a.std(ddof=1)) if a.size > 1 else float("nan"),
            "median": med, "mad": mad, "q1": q1, "q3": q3,
            "iqr": q3 - q1, "min": float(a.min()), "max": float(a.max()),
            "2sd": 2.0 * (float(a.std(ddof=1)) if a.size > 1 else float("nan")),
            "2mad": 2.0 * mad, "2iqr_1p349": 2.0 * (q3 - q1) / 1.349}


def _hist(a, *, bins: int = 10) -> str:
    a = np.asarray(a, dtype=float)
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        return f"  [{lo:.4f}, {hi:.4f}] 全部相同"
    edges = np.linspace(lo, hi, bins + 1)
    idx = np.clip(np.digitize(a, edges[1:-1]), 0, bins - 1)
    lines = []
    for b in range(bins):
        cnt = int((idx == b).sum())
        if cnt:
            lines.append(f"  [{edges[b]:.4f}, {edges[b + 1]:.4f})  "
                         f"{'#' * cnt}  {cnt}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    n_fim = int(argv[0]) if len(argv) > 0 else 1
    n_unrel = int(argv[1]) if len(argv) > 1 else 48
    out_path = argv[2] if len(argv) > 2 else None
    dname = argv[3] if len(argv) > 3 else L.ANCHOR_DESIGN

    designs = L.enumerate_designs(verbose=False)
    index = {d["name"]: i for i, d in enumerate(designs)}
    if dname not in index:
        print(f"❌ 设计 {dname!r} 不在候选集里（共 {len(designs)} 个）")
        return 2
    d = designs[index[dname]]
    name = d["name"]

    fams = [
        ("CRN", [L.cell_seed(name, 0)]),
        ("noise", [L.cell_seed(name, NOISE_BASE + STRIDE * k) for k in range(N_FAMILY)]),
        ("near", [L.cell_seed(name, NEAR_BASE + STRIDE * k) for k in range(N_FAMILY)]),
        ("unrel", [int(v) for v in np.random.default_rng(20261016)
                   .integers(1, 2 ** 31 - 1, size=n_unrel)]),
    ]

    ln: list[str] = []

    def say(s: str = "") -> None:
        print(s, flush=True)
        ln.append(s)

    say("# 单设计 `(A)` 的种子间分布（D58 调查，D60 起可指定设计）")
    say(f"# 设计：{name}（{'锚点 D4' if name == L.ANCHOR_DESIGN else '非锚点'}）")
    say(f"#   T={d['T_ms']}  W={d['W_ms']}  n_rep={d['n_rep']}  n_trials={d['n_trials']}")
    say(f"#   rho={RHO}  n_subjects={SUBJECTS}  n_fim={n_fim}  param_set={PARAM_SET}  P=None")
    for tag, seeds in fams:
        say(f"#   [{tag}] {len(seeds)} 个种子：{[] if tag == 'unrel' else [int(s) for s in seeds]}")
    if out_path:
        say(f"# 结果同时写入 {out_path}")
    say()

    rows: dict[str, list[dict]] = {}
    t_all = time.time()
    for tag, seeds in fams:
        say(f"[{tag}] 共 {len(seeds)} 个种子")
        out = []
        for i, s in enumerate(seeds, 1):
            t0 = time.time()
            r = _one(d, n_fim=n_fim, seed=s)
            r["seed"] = int(s)
            r["seconds"] = time.time() - t0
            out.append(r)
            show = tag != "unrel" or i <= 8 or i % 8 == 0
            if show:
                say(f"  #{i:3d} seed={int(s):>11d}  A={r['A']:.6f}  B={r['B']:.6f}  "
                    f"遗漏={r['omission']:.4f}  cond={r['cond']:.3e}  n_bad={r['n_bad']}  "
                    f"rt={r['rt_ms']:.1f}ms  ({r['seconds']:.1f}s)")
        rows[tag] = out
        st = _stats([r["A"] for r in out])
        stb = _stats([r["B"] for r in out]) if len(out) > 1 else None
        say(f"  → A: n={st['n']} 均值 {st['mean']:.6f}  sd {st['sd']:.6f}  "
            f"中位 {st['median']:.6f}  MAD {st['mad']:.6f}  IQR {st['iqr']:.6f}  "
            f"极差 [{st['min']:.6f}, {st['max']:.6f}]")
        say(f"    带宽候选：2·sd = {st['2sd']:.6f}   2·MAD = {st['2mad']:.6f}   "
            f"2·IQR/1.349 = {st['2iqr_1p349']:.6f}")
        if stb:
            say(f"  → B: 均值 {stb['mean']:.6f}  sd {stb['sd']:.6f}  "
                f"中位 {stb['median']:.6f}  MAD {stb['mad']:.6f}  （2·sd = {stb['2sd']:.6f}）")
        if tag == "unrel":
            say("  分布直方图（A）：")
            say(_hist([r["A"] for r in out]))
        say()

    un = np.asarray([r["A"] for r in rows["unrel"]], dtype=float)
    st_un = _stats(un)
    say("=" * 72)
    say(f"无关种子分布（n = {st_un['n']}）：均值 {st_un['mean']:.6f}  sd {st_un['sd']:.6f}  "
        f"中位 {st_un['median']:.6f}  MAD {st_un['mad']:.6f}")
    for tag in ("CRN", "noise", "near"):
        vals = np.asarray([r["A"] for r in rows[tag]], dtype=float)
        z_sd = (vals - st_un["mean"]) / st_un["sd"] if st_un["sd"] else np.full(vals.shape, np.nan)
        z_mad = (vals - st_un["median"]) / st_un["mad"] if st_un["mad"] else np.full(vals.shape, np.nan)
        rank = 1 + int((un < vals.min()).sum())
        say(f"  [{tag}] n={vals.size}  均值 {vals.mean():.6f}  sd {vals.std(ddof=1):.6f}  "
            f"极差 {vals.max() - vals.min():.6f}")
        say(f"        z(sd) = {np.round(z_sd, 2).tolist()}")
        say(f"        z(MAD) = {np.round(z_mad, 2).tolist()}   最小者排第 "
            f"{rank}/{un.size + 1}")
    say()
    for tag in ("noise", "near", "unrel"):
        sd = float(np.asarray([r["A"] for r in rows[tag]], dtype=float).std(ddof=1))
        say(f"  sd_A[{tag}] = {sd:.6f}  （相对无关族 {sd / st_un['sd']:.2f} 倍）")
    say()
    # 两簇结构：以无关族的整体中位数为界
    med = st_un["median"]
    below = int((un < med).sum())
    above = int((un >= med).sum())
    say(f"  无关族以中位数 {med:.6f} 分界：低侧 {below} 个、高侧 {above} 个；"
        f"低侧均值 {un[un < med].mean():.6f}、高侧均值 {un[un >= med].mean():.6f}；"
        f"两簇间距 {un[un >= med].mean() - un[un < med].mean():.6f}")
    say(f"  6 个 noise 种子落在低侧的有 "
        f"{int((np.asarray([r['A'] for r in rows['noise']]) < med).sum())} 个、"
        f"6 个 near 种子落在低侧的有 "
        f"{int((np.asarray([r['A'] for r in rows['near']]) < med).sum())} 个")
    say(f"总耗时 {time.time() - t_all:.1f}s")

    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(ln) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
