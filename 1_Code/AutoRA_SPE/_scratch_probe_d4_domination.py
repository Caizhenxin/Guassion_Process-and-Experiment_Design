# -*- coding: utf-8 -*-
"""D4 在 (A,B) 平面上到底被谁支配？—— 两种模式，同一个问题。

背景：`Stage9_...md` §11 第 15 条曾写「锚点 D4 被
`T[33.33/83.33/249.98]ms × W[799.98/1199.90/2399.80]ms × r16` 在 (A,B) 两维上同时支配
⇒ 与遗漏率罚分无关」。D54 把遗漏率带从**罚分**改成**可行域约束**之后，"支配"必须限定在
**可行集**内说，否则会用一个人为不可行的设计去否定一个可执行的设计。

两种模式：

1. **离线模式**（推荐）：`python -u _scratch_probe_d4_domination.py <某次运行的 JSON>`
   直接读 `stage9_loop.main()` 落盘的 `cache`（D55 起 payload 已含逐设计记录）⇒ 不必重跑内环。
2. **即时模式**：`python -u _scratch_probe_d4_domination.py <n_fim> [rho]`
   只对锚点与那位"旧支配者"各做**一次** `inner_eval` —— 够用，因为
   `stage9_objective.component_A(res)` 与锚点无关、(B) 只依赖 `res["se_rho"]` 与 `N`。
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# D54 之前那次冒烟（`_scratch_stage9_loop_smoke12.json`）里报出的"支配者"
OLD_DOMINATOR = "T[33.33/83.33/249.98]ms x W[799.98/1199.90/2399.80]ms x r16"


def _dominates(r: dict, ref: dict, tol: float = 1e-12) -> bool:
    """(A,B) 两维都不差、且至少一维严格更好。"""
    return (r["A"] <= ref["A"] + tol and r["B"] >= ref["B"] - tol)


def offline(path: pathlib.Path) -> int:
    d = json.loads(path.read_text(encoding="utf-8"))
    if "cache" not in d:
        print(f"⚠️ {path.name} 里没有 `cache` —— 这是 D55 之前落的盘")
        print("   keys =", sorted(d.keys()))
        print("   只能报锚点 / 推荐点 / 前沿：")
        print("   [anchor]", d.get("anchor"))
        print("   [best]  ", d.get("best"))
        for p in d.get("pareto", []):
            print("   [pareto]", p)
        return 0

    cache = d["cache"]
    a_name = d["anchor"]["name"]
    r4 = cache[a_name]
    feas = {n: r for n, r in cache.items() if r.get("feasible")}
    infeas = {n: r for n, r in cache.items() if not r.get("feasible")}

    print("=" * 78)
    print(f"离线核对（{path.name}）：缓存 {len(cache)} 个设计，可行 {len(feas)}、不可行 {len(infeas)}")
    print("=" * 78)
    print(f"锚点 D4：A = {r4['A']:.6f}  B = {r4['B']:.6f}  C = {r4['C']:.6f}  J = {r4['J']:.6f}")
    print(f"          遗漏 = {r4['omission']:.4f}  可行 = {r4['feasible']}")
    print(f"          闸门 = {r4.get('gates')}")

    dom_all = sorted((n for n, r in cache.items() if n != a_name and _dominates(r, r4)),
                     key=lambda n: cache[n]["A"])
    dom_feas = [n for n in dom_all if cache[n].get("feasible")]
    print(f"\n在**全部**已评估设计里支配 D4 的：{len(dom_all)} 个")
    for n in dom_all[:6]:
        r = cache[n]
        print(f"   A={r['A']:.4f} B={r['B']:.4f} 遗漏={r['omission']:.4f} "
              f"可行={r['feasible']}  {n}")
    print(f"\n在**可行集**内支配 D4 的：{len(dom_feas)} 个")
    for n in dom_feas[:6]:
        r = cache[n]
        print(f"   A={r['A']:.4f} B={r['B']:.4f} 遗漏={r['omission']:.4f}  {n}")

    print("\n" + "=" * 78)
    print("D54 之前那次报出的『支配者』现在是什么状态")
    print("=" * 78)
    if OLD_DOMINATOR in cache:
        r = cache[OLD_DOMINATOR]
        print(f"  A = {r['A']:.6f}  B = {r['B']:.6f}  遗漏 = {r['omission']:.4f}  "
              f"可行 = {r['feasible']}")
        print(f"  闸门 = {r.get('gates')}")
    else:
        print(f"  —— 本次缓存里没有这个设计（预算小 ⇒ 没抽样到）")

    if feas:
        best = min(feas.values(), key=lambda r: r["A"])
        print("\n" + "=" * 78)
        print("可行集里 (A) 最小的那一个")
        print("=" * 78)
        print(f"  A = {best['A']:.6f}  B = {best['B']:.6f}  遗漏 = {best['omission']:.4f}")
        print(f"  {best['name']}")
        print(f"\n  D4 的 A = {r4['A']:.6f} ⇒ ΔA = {r4['A'] - best['A']:+.6f}"
              f"（{'D4 反而更好' if r4['A'] < best['A'] else '推荐点更好'}）")
    print(f"\n⇒ D4 {'被' if dom_feas else '**不被**'}任何**可行**设计在 (A,B) 上支配")
    return 0


def online(n_fim: int, rho: float) -> int:
    import stage9_inner as S9I
    import stage9_objective as S9O

    cases = [
        ("D4（锚点）", [33.33, 83.33, 149.99, 249.98], [799.98, 1199.9, 1799.9], 12),
        (f"旧『支配者』{OLD_DOMINATOR}", [33.33, 83.33, 249.98], [799.98, 1199.9, 2399.8], 16),
    ]
    print("=" * 78)
    print(f"D54 遗漏率带 = {S9O.FROZEN['omission_band']}；n_fim = {n_fim}；rho = {rho}")
    print("=" * 78)
    out = []
    for label, T, W, n_rep in cases:
        res = S9I.inner_eval([t / 1000.0 for t in T], [w / 1000.0 for w in W], n_rep,
                             model=S9I.M_T1, rho=rho, n_fim=n_fim, seed=0)
        om = float(res["omission"])
        lo, hi = S9O.FROZEN["omission_band"]
        rec = {"label": label, "A": S9O.component_A(res),
               "B": S9O.component_B(float(res["se_rho"]), 40), "omission": om,
               "feasible": bool(lo <= om <= hi), "cond": float(res["cond"]),
               "n_bad": int(res["n_bad"]), "n_trials": int(res["n_trials"])}
        out.append(rec)
        print(f"{label}")
        print(f"   A = {rec['A']:.6f}  B = {rec['B']:.6f}  遗漏 = {om:.4f}  "
              f"可行 = {rec['feasible']}")
        print(f"   cond = {rec['cond']:.3g}  n_bad = {rec['n_bad']}  "
              f"n_trials = {rec['n_trials']}")
    a, b = out
    print("-" * 78)
    print(f"ΔA（后者 − 锚点）= {b['A'] - a['A']:+.6f}")
    print(f"ΔB（后者 − 锚点）= {b['B'] - a['B']:+.6f}")
    print(f"在 (A,B) 上支配锚点？ {'是' if _dominates(b, a) else '否'}")
    print(f"该设计在 D54 的带下可行？ {'是' if b['feasible'] else '否'}"
          f"（遗漏 {b['omission']:.4f} vs 带 {S9O.FROZEN['omission_band']}）")
    if _dominates(b, a) and not b["feasible"]:
        print("⇒ **支配关系只在不设可行域时成立**：那位『支配者』自己就落在遗漏率带外，"
              "不能用来否定一个可执行的设计。")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    arg = sys.argv[1]
    if arg.lower().endswith(".json"):
        return offline(pathlib.Path(arg))
    n_fim = int(arg)
    rho = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    return online(n_fim, rho)


if __name__ == "__main__":
    raise SystemExit(main())
