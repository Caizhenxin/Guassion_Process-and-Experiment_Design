"""可行设计的**种子平均** `(A)`：（只读 + 重算）推荐点真的最好吗？

起因（D60 同族的第五处读数）
---------------------------
`(A)` 是一个 **MC 估计量**：同一个设计换个种子，`n_fim = 1` 下实测 `sd_A ≈ 0.018`
（32 个无关种子：锚点 `0.017976`、推荐点 `0.018638`、病态样例 `0.021285`）。

而 `1_Code/AutoRA_SPE/stage9_loop.py` 报出的「推荐点」是
**174 个候选 / 27 个可行里 `(A)` 最小的那个**（`Evaluator.best(key="A")`）⇒ 它是
**极值统计量**，天然带 *winner's curse*（选择偏差）。逐设计实测（`n_fim = 1`，32 个无关种子）：

===========  ==========  ==========  =========
设计          CRN 读数     种子均值     CRN 的 z
===========  ==========  ==========  =========
锚点 D4      0.385802    0.357344    **+1.58**
推荐点       0.344643    0.386742    **−2.26**
病态样例     0.289613    0.318175    **−1.34**
===========  ==========  ==========  =========

⇒ 两个直接后果：

1. **单种子 CRN 下的「谁更好」可能是抽签结果**：推荐点的 CRN 读数比它自己的种子均值
   低 2.26σ（抽到了一个好种子），锚点则高 1.58σ。
2. **在期望意义上锚点反而更好**：两设计的种子均值差 `0.386742 − 0.357344 = 0.0294`，
   而均值标准误 `≈ 0.0186/√32 = 0.0033` ⇒ 约 **8.9 个标准误**（不是噪声）。
   （这不改 D54 的结论：D4 因遗漏率 0.3611 > 0.20 仍不可行；但「推荐点比锚点好」
   这句话在 `n_fim = 1` 下**站不住**。）

本脚本
------
对 payload 里**按 CRN 读数排在最前的 `--top` 个可行设计**（外加锚点）逐个做种子平均：

    python -u 1_Code/AutoRA_SPE/_scratch_mean_A_rank.py <payload.json> [n_seeds] [n_fim] [out_txt]

默认 `n_seeds = 32`、`n_fim = 1`。所有设计**共用同一份种子表**
（`default_rng(20261016).integers(1, 2**31-1, size=n_seeds)`）⇒ 既可比、又便于日后
改成配对比较。逐次评估走 `_scratch_anchor_seed_scan._one()`（与 `Evaluator._raw` +
`_objective_record` 同路），所以数字与 `stage9_loop.py` 直接可比。

输出：按**种子均值**排序的排名表 + 每个设计「CRN 读数 − 种子均值」的偏差 +
按均值选出的赢家与它在 CRN 口径下的名次（选择偏差的幅度）。
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import stage9_loop as L                      # noqa: E402
import _scratch_anchor_seed_scan as SCAN     # noqa: E402  （复用 _one/_stats，保证同路）

SEED_TABLE_SEED = 20261016
DEFAULT_N_SEEDS = 32
DEFAULT_TOP = 6


def _seeds(n: int) -> list[int]:
    return [int(v) for v in np.random.default_rng(SEED_TABLE_SEED).integers(1, 2 ** 31 - 1, size=n)]


def main(argv: list[str]) -> int:
    if not argv:
        print("用法：python -u _scratch_mean_A_rank.py <payload.json> [n_seeds] [n_fim] [out_txt]")
        return 2
    payload_path = argv[0]
    n_seeds = int(argv[1]) if len(argv) > 1 else DEFAULT_N_SEEDS
    n_fim = int(argv[2]) if len(argv) > 2 else 1
    out_path = argv[3] if len(argv) > 3 else ""
    with open(payload_path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    cache = d.get("cache") or {}
    if not cache:
        print(f"❌ {payload_path} 里没有逐设计 `cache`（D55 之前的落盘件）⇒ 无法排名")
        return 2
    anchor_name = (d.get("anchor") or {}).get("name")
    feas = [(r["A"], r["name"], r) for r in cache.values() if r.get("feasible")]
    feas.sort(key=lambda t: t[0])
    keep = [r for _, _, r in feas[:DEFAULT_TOP]]
    if anchor_name and all(r["name"] != anchor_name for r in keep):
        keep.append(cache[anchor_name])
    by_name = {x["name"]: x for x in L.enumerate_designs()}

    out: list[str] = []

    def say(msg: str = "") -> None:
        print(msg, flush=True)
        out.append(msg)

    say(f"# payload：{payload_path}")
    say(f"# n_seeds = {n_seeds}（共用种子表 `default_rng({SEED_TABLE_SEED})`）、n_fim = {n_fim}、"
        f"rho = {SCAN.RHO}、n_subjects = {SCAN.SUBJECTS}、P = None")
    say(f"# 可行设计 {len(feas)} 个；本脚本对 CRN 读数列前 {len(keep)} 名逐个做种子平均")
    seeds = _seeds(n_seeds)
    t_all = time.time()
    rows: list[dict] = []
    for rec in keep:
        name = rec["name"]
        design = by_name.get(name)
        if design is None:
            say(f"❌ 设计 {name!r} 不在 `enumerate_designs()` 里 ⇒ 跳过")
            continue
        t0 = time.time()
        vals = [SCAN._one(design, n_fim=n_fim, seed=s)["A"] for s in seeds]
        st = SCAN._stats(vals)
        se = st["sd"] / float(np.sqrt(st["n"]))
        rows.append({"name": name, "crn": float(rec["A"]), "mean": st["mean"], "se": se,
                     "sd": st["sd"], "n": st["n"], "omission": float(rec.get("omission", float("nan"))),
                     "feasible": bool(rec.get("feasible")), "vals": [float(v) for v in vals],
                     "seconds": time.time() - t0})
        say(f"  [完成] {name}  CRN = {rec['A']:.6f}  均值 = {st['mean']:.6f} ± {se:.6f}"
            f"  sd = {st['sd']:.6f}  {time.time() - t0:.1f}s")

    say()
    say("=" * 78)
    say("按**种子均值** `(A)` 升序（越小越好）")
    say("=" * 78)
    say(f"{'排名':<4} {'设计':<58} {'均值(A)':>9} {'±se':>8} {'CRN(A)':>9} {'偏差σ':>7}")
    means = sorted(rows, key=lambda r: r["mean"])
    for i, r in enumerate(means, 1):
        z = (r["crn"] - r["mean"]) / r["sd"] if r["sd"] > 0 else float("nan")
        say(f"{i:<4} {r['name']:<58} {r['mean']:9.6f} {r['se']:8.6f} {r['crn']:9.6f} {z:+7.2f}")

    say()
    crn_sorted = sorted(rows, key=lambda r: r["crn"])
    say("按 **CRN 读数**排序（`stage9_loop.py` 实际报出的口径）：")
    for i, r in enumerate(crn_sorted, 1):
        say(f"  {i}. {r['name']}  CRN = {r['crn']:.6f}  均值 = {r['mean']:.6f}")

    if means:
        w_mean, w_crn = means[0], crn_sorted[0]
        rank_of_mean_winner = next(i for i, r in enumerate(crn_sorted, 1) if r is w_mean)
        say()
        say(f"按均值选出的赢家：{w_mean['name']}")
        say(f"  ⇒ 它在 **CRN 口径**下排第 {rank_of_mean_winner}/{len(crn_sorted)}"
            f"、CRN 读数 {w_mean['crn']:.6f}（比自己的均值 {w_mean['mean']:.6f} "
            f"低 {(w_mean['mean'] - w_mean['crn']) / w_mean['sd']:.2f}σ）")
        say(f"按 CRN 选出的赢家：{w_crn['name']}")
        say(f"  ⇒ 它的 CRN 读数比自己的均值低 {(w_crn['mean'] - w_crn['crn']) / w_crn['sd']:.2f}σ"
            f"（这就是 *winner's curse* 的幅度：单种子选最小 ⇒ 系统性抽到好种子）")
        if anchor_name and anchor_name in {r["name"] for r in rows}:
            a = next(r for r in rows if r["name"] == anchor_name)
            say(f"锚点 {anchor_name}：均值 {a['mean']:.6f}、CRN {a['crn']:.6f}"
                f"（比自己的均值高 {(a['crn'] - a['mean']) / a['sd']:.2f}σ）")
            for r in means:
                if r is a:
                    continue
                dm = r["mean"] - a["mean"]
                se_d = float(np.sqrt(r["se"] ** 2 + a["se"] ** 2))
                say(f"  vs {r['name'][:52]:<52} 均值差 {dm:+.6f}（{dm / se_d:+.1f} 个标准误）")
            # ❗ 配对比较：所有设计共用**同一份种子表** ⇒ 逐种子配对，能消掉「同一种子下的共同噪声」。
            #    上面那组 `sqrt(se_r² + se_a²)` 是**非配对**口径，在这里是**保守**的（偏大）。
            say()
            say("**配对比较**（同一份种子表 ⇒ 逐种子配对；判据 = |配对均值差| ≥ 2 个配对标准误）")
            av = np.asarray(a["vals"], dtype=float)
            for r in means:
                if r is a:
                    continue
                d = np.asarray(r["vals"], dtype=float) - av
                md = float(np.mean(d))
                sd_d = float(np.std(d, ddof=1))
                se_d = sd_d / float(np.sqrt(d.size)) if d.size > 1 else float("nan")
                t = md / se_d if se_d and se_d > 0 else float("nan")
                if md >= 2.0 * se_d:
                    verdict = "**比锚点差**（`(A)` 更大）"
                elif md <= -2.0 * se_d:
                    verdict = "**比锚点好**（`(A)` 更小）"
                else:
                    verdict = "与锚点**不可分辨**"
                say(f"  {r['name']:<58} 配对均值差 {md:+.6f} ± {se_d:.6f}"
                    f"（t = {t:+.2f}，sd_pair = {sd_d:.6f}）⇒ {verdict}")
            say("  ⚠️ 判据是**配对**标准误；若两设计在不同种子上的波动不完全同步，"
                "这里的灵敏度会高于非配对口径 —— 用哪个口径都在本文件里写明。")
            say("  ❗ **本段的口径 ≠ `stage9_loop.compare_arms` 的判据带**：这里走 "
                "`_scratch_anchor_seed_scan._one()`，它把种子**直接**交给 `inner_eval`，"
                "同一份种子表下**所有设计共用同一条随机流**（共享 CRN）⇒ 逐设计读数正相关"
                f"（实测 ρ ≈ +0.49…+0.85，`_scratch_pair_corr.py`），配对 `sd_pair` 因此"
                "小于独立性假设的 `√2·sd`。而循环里 `Evaluator._raw` 用的是 "
                "`seed=cell_seed(d[\"name\"], base_seed)` ⇒ **每个设计各自一条流** ⇒ 两条臂"
                "相互独立 ⇒ 带宽必须是 `2·√2·sd`（D60）。**两处口径都能用，但不可混用**："
                "本段的 t 值偏灵敏（方差缩减的 CRN 配对），不能拿去替代循环的判词。")
    say()
    say(f"总耗时 {time.time() - t_all:.1f}s")
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out) + "\n")
        # 逐种子读数落盘：种子平均每次都要重跑 7 × n_seeds 次内环（n_fim = 1 下约 13 min）⇒
        # 把原始读数留下，日后改判据/改配对口径时**不必重新模拟**（只读 + 重算）。
        side = os.path.splitext(out_path)[0] + ".vals.json"
        with open(side, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"payload": str(payload_path), "n_fim": n_fim,
                       "seed_table_seed": SEED_TABLE_SEED, "seeds": [int(s) for s in seeds],
                       "rows": rows}, fh, ensure_ascii=False, indent=1)
        print(f"[逐种子读数] 已写 {side}（{len(rows)} 个设计 × "
              f"{rows[0]['n'] if rows else 0} 个种子）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
