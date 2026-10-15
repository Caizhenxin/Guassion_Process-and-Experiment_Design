# -*- coding: utf-8 -*-
"""定位 `hier.fit_and_loo` 在**干跑规模**下的真实成本构成。

背景：`stage8_run.project()` 曾断言「超参数 Hessian 是主导项」（§8.25 已写），
但 `_probe_warm_mode.py` 实测单次众数搜索只要 ~4 ms ⇒ 1632 次也只有 ~7 s。
两个结论不可能同时成立，必须实测谁对。本探针把每个阶段包一层计时器，
在真实干跑数据上跑一次最小配置。

跑法：``python 1_Code/DDM_Core/_scratch/_probe_s8run_profile.py [n_rep]``
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
REPO = CORE.parent.parent
EXP_DIR = REPO / "1_Code" / "Experiment"
for _p in (CORE, EXP_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hier                                          # noqa: E402
import read_formal_data as RF                        # noqa: E402
import simulate                                      # noqa: E402
from mapping import MappingParams, WITHIN_FREE_LIN   # noqa: E402

N_REP = int(sys.argv[1]) if len(sys.argv) > 1 else 3
N_X = 41
STATS: dict[str, list] = {}


def wrap(mod, name: str, every: int = 1):
    orig = getattr(mod, name)

    def f(*a, **k):
        t = time.perf_counter()
        try:
            return orig(*a, **k)
        finally:
            d = time.perf_counter() - t
            s = STATS.setdefault(name, [0, 0.0, 0.0])
            s[0] += 1
            s[1] += d
            s[2] = max(s[2], d)
            if every and s[0] % every == 0:
                print(f"      [{name}] #{s[0]:>6} 本次 {d * 1e3:8.2f} ms "
                      f"累计 {s[1]:8.1f} s 最大 {s[2] * 1e3:8.1f} ms", flush=True)

    setattr(mod, name, f)


def build_subjects(n: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    design = simulate.build_design(0, [0.03333, 0.24998], [0.79998, 1.7999], N_REP)
    truth = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                          shape_model="lin", t0=0.25)
    subs = []
    for _ in range(n):
        tr = simulate.simulate_subject(design, truth, rng)
        tr = {**design, **tr}
        tr, _ = RF.fit_ready(tr)
        tb = RF.t0_bounds(tr)
        subs.append(hier.ddm_subject(tr, MappingParams(shape_model="lin"),
                                     WITHIN_FREE_LIN, rho_free=False,
                                     bounds_override=tb, n_x=N_X))
    return subs, len(tr["rt"])


def main() -> int:
    n_sub = 3
    subs, n_t = build_subjects(n_sub)
    print("=" * 88)
    print(f"干跑规模的成本拆解：N={n_sub}、试次/人={n_t}、n_x={N_X}、n_rep={N_REP}")
    print("=" * 88, flush=True)

    for name, every in (("log_likelihood_step", 200), ("hessian_x", 200),
                        ("subject_map_laplace", 200), ("hyper_hessian", 1),
                        ("hyper_draws", 1), ("loo_matrix", 1), ("hier_fit", 1)):
        try:
            wrap(hier, name, every)
        except AttributeError:
            print(f"  （hier 里没有 {name}，跳过）")

    t0 = time.perf_counter()
    try:
        out = hier.fit_and_loo(subs, n_draws=5, seed=0, n_em=2, do_bruteforce=False)
        print(f"\n完成。ELPD {out['loo']['elpd_loo']:.3f}", flush=True)
    except Exception as exc:                                   # noqa: BLE001
        print(f"\n❗ 中断于 {type(exc).__name__}: {exc}", flush=True)
    total = time.perf_counter() - t0

    print("\n" + "=" * 88)
    print(f"总耗时 {total:.1f} s")
    print(f"{'函数':<24}{'次数':>9}{'累计 s':>11}{'占比':>8}{'均值 ms':>11}{'最大 ms':>10}")
    for k, (c, s, mx) in sorted(STATS.items(), key=lambda kv: -kv[1][1]):
        print(f"{k:<24}{c:>9}{s:>11.1f}{100 * s / max(total, 1e-9):>7.1f}%"
              f"{1e3 * s / max(c, 1):>11.2f}{1e3 * mx:>10.1f}")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
