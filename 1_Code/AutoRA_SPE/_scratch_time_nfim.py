"""一次性探针：量 `inner_eval` 的耗时与病态率随 `n_fim` 的变化。

用途：为「在正式 `n_fim` 下重测可行域构成」（主计划 L529 仍开放第 (2) 件）定预算 ——
先知道单次评估要多久，再决定整个 174 个候选的扫描要不要跑、跑哪个 `n_fim`。

用法：
    python -u _scratch_time_nfim.py [n_fim ...]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage9_inner as S9I  # noqa: E402
import stage9_loop as L  # noqa: E402


def one(d: dict, n_fim: int, rho: float = float(L.S9O.FROZEN["rho_mu"])) -> dict:
    t0 = time.time()
    res = S9I.inner_eval(L.levels_sec(d["T_ms"]), L.levels_sec(d["W_ms"]), d["n_rep"],
                         model=S9I.M_T1, rho=rho, n_fim=n_fim,
                         seed=L.cell_seed(d["name"], 0))
    dt = time.time() - t0
    return {"n_fim": n_fim, "seconds": dt, "cond": float(res["cond"]),
            "n_bad": int(res["n_bad"]), "se_rho": float(res["se_rho"]),
            "omission": float(res["omission"])}


def main(argv: list[str]) -> int:
    ns = [int(x) for x in argv[1:]] or [1, 4, 12]
    designs = L.enumerate_designs(verbose=False)
    # 取两个点：网格第一个（档位最少的那类）与锚点 D4 的形状（离它最近的候选）
    picks = [designs[0], designs[len(designs) // 2]]
    print(f"候选空间 {len(designs)} 个；抽样测 {len(picks)} 个设计 × {len(ns)} 个 n_fim")
    rows = []
    for n in ns:
        for d in picks:
            r = one(d, n)
            rows.append(r)
            print(f"  n_fim={r['n_fim']:3d}  r{d['n_rep']:2d} T={len(d['T_ms'])}档 "
                  f"W={len(d['W_ms'])}档  {r['seconds']:7.1f}s  "
                  f"cond={r['cond']:.3e}  n_bad={r['n_bad']}  "
                  f"se_rho={r['se_rho']:.4f}  遗漏={r['omission']:.4f}", flush=True)
    base = [r for r in rows if r["n_fim"] == ns[0]]
    t_base = max(r["seconds"] for r in base) if base else 1.0
    print("\n按单点耗时外推整个 {0} 个候选：".format(len(designs)))
    for n in ns:
        rs = [r["seconds"] for r in rows if r["n_fim"] == n]
        if not rs:
            continue
        t = max(rs)
        print(f"  n_fim={n:3d}  {t:7.1f}s/点  ⇒  {t * len(designs) / 60.0:6.1f} min "
              f"(×{t / t_base:.2f} 于 n_fim={ns[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
