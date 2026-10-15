# -*- coding: utf-8 -*-
"""诊断：为什么 `subject_map_laplace` 在**冷启动中点**上会退化（似然恒 −inf）。

`_probe_warm_mode.py` 实测单次众数搜索只要 4 ms 且**不随试次数增长**，而
`_probe_s8run_profile.py` 里同样的构造却给出 34 ms/次似然评估 ⇒ 前者走进了退化路径。
本探针把 `ll_x` 在中点与若干邻点上的取值直接打出来，定位原因。
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
import mapping                                       # noqa: E402
import read_formal_data as RF                        # noqa: E402
import simulate                                      # noqa: E402
from mapping import MappingParams, WITHIN_FREE_LIN   # noqa: E402


def build(n_rep: int, rho_free: bool, seed: int = 0):
    rng = np.random.default_rng(seed)
    design = simulate.build_design(0, [0.03333, 0.24998], [0.79998, 1.7999], n_rep)
    truth = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                          shape_model="lin", t0=0.25)
    tr = simulate.simulate_subject(design, truth, rng)
    tr = {**design, **tr}
    tr, _ = RF.fit_ready(tr)
    tb = RF.t0_bounds(tr)
    return tr, tb


def main() -> int:
    for label, rho_free in (("M-T3 (rho=1)", False), ("M-T1 (rho free)", True)):
        tr, tb = build(3, rho_free)
        sub = hier.ddm_subject(tr, MappingParams(shape_model="lin"), WITHIN_FREE_LIN,
                               rho_free=rho_free, bounds_override=tb, n_x=41)
        lo = np.asarray(sub["lo"], float)
        hi = np.asarray(sub["hi"], float)
        x_mid = 0.5 * (lo + hi)
        print("\n" + "=" * 84)
        print(f"{label}：试次 {len(tr['rt'])}、bounds_override={tb}")
        print(f"    names = {sub['names']}")
        print(f"    中点自然坐标（_from_x）= "
              f"{np.round(hier._from_x(x_mid, lo, hi), 6)}")
        for tag, x in (("中点 0.5(lo+hi)", x_mid),
                       ("低端 0.05", lo + 0.05 * (hi - lo)),
                       ("高端 0.95", lo + 0.95 * (hi - lo))):
            t = time.perf_counter()
            v = sub["ll_x"](x)
            dt = time.perf_counter() - t
            print(f"    ll_x({tag:<16}) = {v!r:<24} 用时 {dt * 1e3:8.2f} ms")

        # ---- 在 subject_map_laplace 内部数 ll_x 的次数与总耗时 ----
        cnt = {"n": 0, "s": 0.0, "tot": 0.0}
        raw = sub["ll_x"]

        def counting(x):
            t = time.perf_counter()
            v = raw(x)
            dt = time.perf_counter() - t
            cnt["n"] += 1
            cnt["s"] += dt
            cnt["tot"] = max(cnt["tot"], dt)
            if cnt["n"] <= 3:
                print(f"      · 第 {cnt['n']} 次调用：x={np.round(np.asarray(x, float), 4)}"
                      f" ⇒ {v!r}，用时 {dt * 1e3:.2f} ms")
            return v

        sub["ll_x"] = counting
        mu = np.zeros(len(lo))
        ls = np.full(len(lo), np.log(0.4))
        for tag, x0 in (("冷启动中点", None), ("温启动", None)):
            n0, s0 = cnt["n"], cnt["s"]
            t = time.perf_counter()
            r = hier.subject_map_laplace(sub, None if x0 is None else r["mode"], mu, ls)
            dt = time.perf_counter() - t
            print(f"    subject_map_laplace({tag})：总 {dt:7.3f} s；"
                  f"ll_x 调用 {cnt['n'] - n0} 次、累计 {cnt['s'] - s0:7.3f} s"
                  f"（单次 {1e3 * (cnt['s'] - s0) / max(cnt['n'] - n0, 1):6.2f} ms）；"
                  f"n_evals {r['n_evals']}、n_flipped {r['n_flipped']}")
        sub["ll_x"] = raw
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
