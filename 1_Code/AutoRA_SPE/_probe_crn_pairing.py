# -*- coding: utf-8 -*-
"""「共享流 CRN 配对」在**正式 `n_fim`** 下值不值得升格为判据（D69 候选）。

背景（D60/D61）：`stage9_loop.compare_arms` 现在的判据带是 `2·√2·sd`，
其中 `√2` 来自「两条臂是**不同设计**、各自独立抽样 ⇒ `Var(A1 − A2) = 2·sd²`」。
`stage9_loop.Evaluator._raw` 用 `seed = cell_seed(d["name"], base_seed)` ⇒ 各设计各一条流。

若改成「同一条随机流 + 逐种子配对」，`Var(差)` 会随两设计的正相关而下降：
`Var(Δ) = sd1² + sd2² − 2ρ·sd1·sd2`，判据系数从 `2√2` 收到 `2·sd_pair/sd`。
本探针就是量这个系数：**同种子表**下各设计的 `(A)` 读数、两两 `ρ`、配对 `sd_pair`。

不做的事：**不**改判据、**不**重跑内环落盘件。D60 是事前登记的；
本探针只回答「如果重做一次，配对口径能把带子收窄多少倍」，供下一轮决策引用。

用法：
    python -X utf8 -u _probe_crn_pairing.py <payload.json> [n_seeds=12] [n_fim=12] [out_txt]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import stage9_loop as L                                            # noqa: E402
import _scratch_anchor_seed_scan as SCAN                           # noqa: E402

SEED_TABLE_SEED = 20261016
N_TOP = 3


def _seeds(n: int) -> list[int]:
    return [int(v) for v in np.random.default_rng(SEED_TABLE_SEED).integers(1, 2 ** 31 - 1, size=n)]


def main(argv: list[str]) -> int:
    if not argv:
        print("用法：python -X utf8 -u _probe_crn_pairing.py <payload.json> "
              "[n_seeds=12] [n_fim=12] [out_txt]")
        return 2
    payload_path = argv[0]
    n_seeds = int(argv[1]) if len(argv) > 1 else 12
    n_fim = int(argv[2]) if len(argv) > 2 else 12
    out_path = argv[3] if len(argv) > 3 else ""

    with open(payload_path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    cache = d.get("cache") or {}
    if not cache:
        print(f"❌ {payload_path} 里没有逐设计 `cache` ⇒ 无法选设计")
        return 2
    anchor_name = (d.get("anchor") or {}).get("name")
    feas = sorted(((r["A"], r["name"]) for r in cache.values() if r.get("feasible")),
                  key=lambda t: t[0])
    names = [n for _, n in feas[:N_TOP]] + [anchor_name or ""]
    by_name = {x["name"]: x for x in L.enumerate_designs()}
    designs = [(n, by_name[n]) for n in names if n and n in by_name]
    if not designs:
        print("❌ 选不出设计")
        return 2

    out: list[str] = []

    def say(msg: str = "") -> None:
        print(msg, flush=True)
        out.append(msg)

    seeds = _seeds(n_seeds)
    say(f"# payload：{payload_path}")
    say(f"# n_seeds = {n_seeds}（共用种子表 `default_rng({SEED_TABLE_SEED})`）、n_fim = {n_fim}、"
        f"rho = {SCAN.RHO}、n_subjects = {SCAN.SUBJECTS}")
    say(f"# 设计：{len(designs)} 个（前 {N_TOP} 个可行 `(A)` 最小者 + 锚点 {anchor_name}）")
    say("")

    vals: dict[str, list[float]] = {}
    for name, design in designs:
        t0 = time.time()
        vals[name] = [float(SCAN._one(design, n_fim=n_fim, seed=s)["A"]) for s in seeds]
        say(f"  [完成] {name}  均值 = {np.mean(vals[name]):.6f}  "
            f"sd = {np.std(vals[name], ddof=1):.6f}  {time.time() - t0:.1f}s")

    say("")
    say("## 逐设计 sd 与两两相关（同种子表 ⇒ 配对可行）")
    base = designs[0][0]
    a0 = np.asarray(vals[base], float)
    sd0 = float(np.std(a0, ddof=1))
    say(f"基准设计 `{base}`：sd = {sd0:.6f}")
    say("")
    say("| 设计 | 均值 | sd | 与基准 ρ | 配对 sd | `2·sd_pair/sd` | 相对 `2√2` 收窄 |")
    say("|---|---|---|---|---|---|---|")
    rows = []
    for name, _ in designs[1:]:
        a1 = np.asarray(vals[name], float)
        sd1 = float(np.std(a1, ddof=1))
        diff = a1 - a0
        sd_pair = float(np.std(diff, ddof=1))
        rho = float(np.corrcoef(a0, a1)[0, 1])
        coef = 2.0 * sd_pair / float(np.sqrt(0.5 * (sd0 ** 2 + sd1 ** 2)))
        rows.append({"name": name, "mean": float(np.mean(a1)), "sd": sd1,
                     "rho": rho, "sd_pair": sd_pair, "coef_vs_2sqrt2": coef,
                     "narrow": (2.0 * float(np.sqrt(2.0))) / coef})
        say(f"| `{name}` | {np.mean(a1):.6f} | {sd1:.6f} | {rho:+.3f} | {sd_pair:.6f} | "
            f"**{coef:.3f}** | **{rows[-1]['narrow']:.2f}×** |")

    say("")
    say("## 判定")
    if rows:
        coefs = [r["coef_vs_2sqrt2"] for r in rows]
        say(f"配对口径下系数区间 **{min(coefs):.3f} – {max(coefs):.3f}**（独立性假设是 `2√2 = 2.828`）")
        say(f"⇒ 若改用配对，判据带会收窄 **{min(r['narrow'] for r in rows):.2f}× – "
            f"{max(r['narrow'] for r in rows):.2f}×**")
        say("⚠️ 这只是「同样的种子、不同设计」的**相关性实测**；要真用上，"
            "`stage9_loop.Evaluator._raw` 的种子必须改成**只依赖种子表**（不再掺设计名），"
            "那会改变所有既有落盘件的 `cache` 键 ⇒ 属于**换实验**，不是换分析。")
        say("⇒ 结论分工：`2·√2·sd` 是**现行事前登记**（D60）；配对口径只能写进「下一轮若重做应事前登记」的建议。")

    txt = "\n".join(out) + "\n"
    if out_path:
        Path(out_path).write_text(txt, encoding="utf-8", newline="\n")
        vals_path = str(Path(out_path).with_suffix("")) + ".vals.json"
        Path(vals_path).write_text(json.dumps(
            {"payload": str(payload_path), "n_fim": n_fim, "n_seeds": n_seeds,
             "seed_table_seed": SEED_TABLE_SEED, "seeds": seeds, "vals": vals,
             "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"\n已写 {out_path} 与 {vals_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
