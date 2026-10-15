# -*- coding: utf-8 -*-
"""测「一次温启动众数搜索」的耗时 —— `stage8_run.project()` 里超参数 Hessian 项的计价单位。

为什么需要这个探针：`hier.hyper_hessian` 调用 `hier.subject_map_laplace` 的次数是
``4·n(n+1)/2 · N``（``n = 2K``；K = `WITHIN_FREE_LIN` 的长度，rho 自由时 +1），
在 N=3 时就是几千次。`project()` 原先直接用 ``lbfgs_s + hess_s = 12.75 s``
（**冷启动** L-BFGS + Hessian）当计价单位，需要换成实测值。

❗ 早期两版探针都给出了 **0.004 s** 的结论，比 `_probe_s8run_profile.py`
实测的单项（`log_likelihood_step` ≈ 34 ms）小两个数量级，**而且耗时完全不随试次数增长**
（16 / 48 / 144 试次都是 0.004 s）。根因不是退化似然，而是**初值**：
探针传了 `x_init=None`，`np.asarray(None, float)` 得到长度为 1 的 `[nan]`，
L-BFGS 与 `hessian_x` 于是在 NaN 上原地打转（`n_evals=44`、`n_flipped=0`，
看起来"收敛"了）。`hier.subject_map_laplace` 现已对 `None` 回退到区间中点、
对非有限值显式报错；本探针也因此**自带标度自检**：若耗时随试次数不增长，
就直接判该测量无效。

跑法：``python 1_Code/DDM_Core/_scratch/_probe_warm_mode.py``
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

N_X = 41


def build(n_rep: int, rho_free: bool, seed: int = 0):
    """造一名被试的似然对象：2 T × 2 W × 2 with × 2 match × n_rep 试次。"""
    rng = np.random.default_rng(seed)
    design = simulate.build_design(0, [0.03333, 0.24998], [0.79998, 1.7999], n_rep)
    truth = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                          shape_model="lin", t0=0.25)
    tr = simulate.simulate_subject(design, truth, rng)
    tr = {**design, **tr}
    tr, _ = RF.fit_ready(tr)
    tb = RF.t0_bounds(tr)
    sub = hier.ddm_subject(tr, MappingParams(shape_model="lin"), WITHIN_FREE_LIN,
                           rho_free=rho_free, bounds_override=tb, n_x=N_X)
    return sub, len(tr["rt"])


def med(fn, reps: int):
    ts = []
    out = None
    for _ in range(reps):
        t = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t)
    return float(np.median(ts)), out


def measure(n_rep: int, rho_free: bool):
    sub, n_t = build(n_rep, rho_free)
    lo = np.asarray(sub["lo"], float)
    mu = np.zeros(len(lo))
    ls = np.full(len(lo), np.log(0.4))
    # ❗ 必须给**真正的**初值：早期版本的探针传 `x_init=None`，而
    #    `np.asarray(None, float)` 是长度为 1 的 `[nan]` ⇒ L-BFGS 与 `hessian_x`
    #    在 NaN 上原地打转，测出「4 ms 就收敛」的**退化结果**（现已加守卫）。
    x0 = hier._x0_of(sub)
    t_cold, r_cold = med(lambda: hier.subject_map_laplace(sub, x0, mu, ls), 1)
    t_warm, r_warm = med(
        lambda: hier.subject_map_laplace(sub, r_cold["mode"], mu, ls), 3)
    return {"n_t": n_t, "k": len(lo), "cold": t_cold, "warm": t_warm,
            "nfev_cold": r_cold.get("n_evals", 0),
            "nfev_warm": r_warm.get("n_evals", 0),
            "n_flipped": r_warm.get("n_flipped", 0)}


def main() -> int:
    print("=" * 88)
    print("温启动众数搜索的耗时（project() 超参数 Hessian 项的计价单位）")
    print(f"构造与 `_probe_s8run_profile.py` 完全一致：n_x={N_X}、"
          f"MappingParams(shape_model='lin')")
    print("=" * 88)
    out = {}
    for label, rho_free in (("M-T3（rho 固定，K=7）", False),
                            ("M-T1（rho 自由，K=8）", True)):
        print(f"\n{label}")
        rows = []
        for n_rep in (1, 3, 9):
            m = measure(n_rep, rho_free)
            rows.append(m)
            print(f"    试次 {m['n_t']:>4}：冷启动 {m['cold']:8.3f} s"
                  f"（{m['nfev_cold']:>4} 次 L-BFGS 评估）、"
                  f"温启动 {m['warm']:8.3f} s（{m['nfev_warm']} 次）"
                  f"、n_flipped {m['n_flipped']}")
        out[label] = rows
        # ❗ 标度自检：真测量必须随试次数**单调**增长。
        #    判据**不能**要求「与试次数同倍增长」：一次众数搜索的评估次数里，
        #    `hessian_x` 的 2K + 4·K(K−1)/2 次是**固定**的（98/128 次），只有
        #    单次评估耗时随试次数次线性增长（实测幂律 ≈ 0.42）⇒ 总耗时本就
        #    远低于试次倍数。退化路径（`x_init=[nan]`）的特征是 grow ≈ 1.00。
        grow = rows[-1]["warm"] / max(rows[0]["warm"], 1e-12)
        need = rows[-1]["n_t"] / max(rows[0]["n_t"], 1)
        print(f"    ⚠️ 标度自检：试次 ×{need:.0f} ⇒ 温启动耗时 ×{grow:.2f}"
              f"（次线性是预期：评估次数含固定的 {m['nfev_warm']}+2K+4K(K−1)/2 次，"
              f"仅单次评估耗时随试次增长）"
              + ("  ⇒ **无效测量**：完全不随规模增长，似然多半在退化路径上"
                 if grow < 1.15 else "  ⇒ 通过"))

    cal = out["M-T3（rho 固定，K=7）"][1]      # 48 试次
    print("\n" + "=" * 88)
    print(f"**计价单位（校准点：{cal['n_t']} 试次、n_x={N_X}、M-T3）**")
    print(f"    一次温启动众数搜索 = {cal['warm']:.3f} s"
          f"（其中 `hessian_x` 约 2K + 4·K(K−1)/2 = 98 次似然评估）")
    t1 = out["M-T1（rho 自由，K=8）"][1]["warm"]
    print(f"    M-T1 同规模 = {t1:.3f} s ⇒ 两阶段/单阶段比 ≈ {t1 / cal['warm']:.2f}×")
    for label, rho_free in (("M-T3", False), ("M-T1", True)):
        k = len(WITHIN_FREE_LIN) + (1 if rho_free else 0)
        nh = 2 * k
        print(f"    {label}：K={k} ⇒ n=2K={nh} ⇒ 4·n(n+1)/2 = "
              f"{4.0 * nh * (nh + 1) / 2.0:.0f} 次众数搜索/人")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
