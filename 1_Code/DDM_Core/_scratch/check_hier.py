"""check_hier.py —— `hier.py`（Stage 8 层级耦合 + 以被试为单位的 LOO）的自测。

判据分两组：

**A 组（解析基准，一元高斯）** —— 层级模型有**闭式**边际，用来验"这台机器算得对不对"：
    y_sj ~ N(θ_s, 1)、θ_s ~ N(mu, σ²)。则
    ``log p(y_s | mu, σ) = −½Σ(y−ȳ)² − (n/2)log2π + ½log(2πσ²) − ½log(nσ²+1)
                            − ½·n(ȳ−mu)²/(nσ²+1)``
    且被积函数是**二次型** ⇒ 拉普拉斯近似**精确**（不是近似）⇒ 可以要求 1e-6 级一致。

**B 组（真实 DDM）** —— 只看**行为**：数据由 M-T1（ρ=0.5）生成时，
以被试为单位的 PSIS-LOO 是否把 M-T1 排在 M-T3 之前。

**C 组（D68，机制）** —— 用纯二次 `ll_x` 把 Hessian 造死：非正特征值的方向上
`cov` 必须恰为 `1/floor`，且负曲率方向上众数搜索会**发散**（该点不是众数）。

用法：``python _scratch/check_hier.py [B 的被试数=5]``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hier import (compare_models, ddm_subject, fit_and_loo,   # noqa: E402
                  hier_fit, hyper_draws, loo_bruteforce, loo_matrix,
                  make_subject, subject_map_laplace)
from mapping import MappingParams                              # noqa: E402
from simulate import build_design                              # noqa: E402
from twophase import simulate_euler_subject                    # noqa: E402

WIDE = (-100.0, 100.0)
N_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global N_FAIL
    mark = "✅" if cond else "❌"
    if not cond:
        N_FAIL += 1
    print(f"  {mark} {name}" + (f" —— {detail}" if detail else ""))


# ------------------------------------------------------------------
# A 组
# ------------------------------------------------------------------
def gauss_subject(y: np.ndarray, sd: float = 1.0) -> dict:
    """``ll_x(x)`` 把 ``x`` 当**自然参数** θ 用（自定义被试不做 logistic 变换）。"""
    y = np.asarray(y, float)
    n = y.size
    const = -0.5 * n * np.log(2 * np.pi * sd * sd)

    def ll_x(x):
        th = float(np.asarray(x).ravel()[0])
        return const - 0.5 * float(np.sum((y - th) ** 2)) / (sd * sd)

    return make_subject(ll_x, [WIDE[0]], [WIDE[1]], ["theta"])


def gauss_log_marginal_closed(y: np.ndarray, mu: float, sigma: float,
                              sd: float = 1.0) -> float:
    """``log ∫ Π_j N(y_j; θ, sd²) · N(θ; mu, σ²) dθ`` 的**闭式**。

    ⚠️ 2026-10-14 教训：第一版把最后两项写成 ``+½log(2πσ²)`` 与
    ``−½log(nσ²/sd²+1)``（应为 ``+½log2π − ½log(2πσ²)`` 与 ``−½log(n + sd²/σ²)``），
    差出 ``−½log σ² − ½log(2π)``——**实测 0.226 / 0.696 / 0.467**。
    闭式基准自己也要被验：极点情形（σ→0 退化为逐点似然）与"拉普拉斯精确"这一
    解析事实互相钉死。第二版仍差 ``−½log σ² − ½log2π``，说明当时只改了符号没改结构。
    """
    y = np.asarray(y, float)
    n = y.size
    ybar = float(np.mean(y))
    v = sigma ** 2
    return (-0.5 * float(np.sum((y - ybar) ** 2)) / sd ** 2
            - 0.5 * n * np.log(2 * np.pi * sd * sd)
            + 0.5 * np.log(2 * np.pi)
            - 0.5 * np.log(2 * np.pi * v)
            - 0.5 * np.log(n + sd ** 2 / v)
            - 0.5 * (ybar - mu) ** 2 / (v + sd ** 2 / n))


def draw_gauss_group(rng, n_sub: int, n_obs: int, mu: float, sigma: float,
                     sd: float = 1.0) -> list[dict]:
    """``θ_s ~ N(mu, σ²)``、``y_sj ~ N(θ_s, sd²)`` —— **每名被试一个 θ**。

    ⚠️ 第一版误写成 ``rng.normal(mu, sigma, size=n_obs)``（即每个人的观测
    各自独立、**没有**共同的 θ_s）⇒ 被试间方差为 0，EM 必然把群体 SD 压到 0，
    A2 因此假报失败。**生成器写错时，测的就不是估计量了。**
    """
    out = []
    for _ in range(n_sub):
        theta = float(rng.normal(mu, sigma))
        out.append(gauss_subject(rng.normal(theta, sd, size=n_obs), sd=sd))
    return out


def case_a() -> None:
    print("\n[A] 解析基准（一元高斯，拉普拉斯**精确**）")
    rng = np.random.default_rng(20261014)
    n = 15
    y = rng.normal(0.4, 1.0, size=n)
    sub = gauss_subject(y)
    x0 = np.array([0.0])

    # ---- A1：边际对数似然 vs 闭式 ----
    worst = 0.0
    rows = []
    for mu, sigma in ((0.0, 0.5), (0.4, 0.8), (-0.3, 0.25)):
        r = subject_map_laplace(sub, x0, [mu], [np.log(sigma)])
        exact = gauss_log_marginal_closed(y, mu, sigma)
        d = abs(r["log_marginal"] - exact)
        worst = max(worst, d)
        rows.append(f"mu={mu:+.1f} σ={sigma:.2f}: {r['log_marginal']:.6f} vs "
                    f"{exact:.6f}（差 {d:.2e}）")
        check(f"A1 sigma={sigma} 时众数正确（n_flipped = 0）",
              r["n_flipped"] == 0, f"eigval = {np.round(r['eigval'], 4)}")
    for line in rows:
        print("      " + line)
    check("A1 拉普拉斯边际 = 闭式（最大差 < 1e-6）", worst < 1e-6,
          f"max |Δ| = {worst:.2e}")

    # ---- A2：EM 能不能把 σ 估回来（以及"漏掉 Cov 修正会低估"）----
    n_sub, n_obs, sigma_true = 40, 20, 0.5
    subs = draw_gauss_group(rng, n_sub, n_obs, 0.3, sigma_true)
    fit = hier_fit(subs, n_em=25, tol=1e-6)
    s_hat = float(np.exp(fit["log_sigma"])[0])
    naive = float(np.std(fit["modes"][:, 0], ddof=0))
    cov_mean = float(np.mean([c[0, 0] for c in fit["covs"]]))
    check("A2a EM 把群体 SD 估回到真值附近（|σ̂−0.5| < 0.12）",
          abs(s_hat - sigma_true) < 0.12,
          f"σ̂ = {s_hat:.4f}（真值 {sigma_true}）")
    check("A2b 众数方差的偏差方向正确（众数比真参数更集中）",
          naive < s_hat,
          f"只用众数离散度 = {naive:.4f} < 含 Cov 修正的 σ̂ = {s_hat:.4f}"
          f"（平均后验方差 = {cov_mean:.5f}）")
    check("A2c 群体均值估回真值附近（|mu_hat−0.3| < 0.15）",
          abs(float(fit["mu"][0]) - 0.3) < 0.15, f"mu_hat = {float(fit['mu'][0]):.4f}")
    check("A2d EM 收敛（步长 < 容差）", fit["history"][-1]["step"] < 1e-6,
          f"用 {fit['n_em_used']} 轮、末步长 {fit['history'][-1]['step']:.2e}")

    # ---- A3：以被试为单位的 LOO：PSIS vs 真留一 ----
    n_small = 10
    subs_small = draw_gauss_group(rng, n_small, 12, 0.3, 0.5)
    fit_s = hier_fit(subs_small, n_em=20, tol=1e-7)
    hyper = hyper_draws(subs_small, fit_s, n_draws=300, seed=3)
    L = loo_matrix(subs_small, hyper, mode_warm=fit_s["modes"])
    from loo import psis_loo
    lo = psis_loo(L)
    bf = loo_bruteforce(subs_small, n_em=20, tol=1e-7)
    corr = float(np.corrcoef(lo["elpd_i"], bf)[0, 1])
    tot_psis, tot_bf = float(lo["elpd_loo"]), float(np.sum(bf))
    check("A3a PSIS-LOO 与真留一的逐被试值正相关（r > 0.9）", corr > 0.9,
          f"r = {corr:.4f}")
    check("A3b 两者总量差 < 3（N=10、S=300 下的可接受带）",
          abs(tot_psis - tot_bf) < 3.0,
          f"PSIS = {tot_psis:.3f} vs 真留一 = {tot_bf:.3f}")
    check("A3c Pareto k 全在可用区（max k < 0.7）", lo["k_max"] < 0.7,
          f"max k = {lo['k_max']:.3f}、k>0.7 个数 = {lo['n_k_gt_bad']}")

    # ---- A4：超参数后验 SD 随 N 收缩 ----
    sd_small = float(np.sqrt(hyper["cov"][0, 0]))
    subs_big = draw_gauss_group(rng, 60, 12, 0.3, 0.5)
    fit_b = hier_fit(subs_big, n_em=20, tol=1e-7)
    hyp_b = hyper_draws(subs_big, fit_b, n_draws=100, seed=4)
    sd_big = float(np.sqrt(hyp_b["cov"][0, 0]))
    check("A4 群体均值的后验 SD 随 N 收缩（60 人 < 10 人）", sd_big < sd_small,
          f"10 人 {sd_small:.4f} → 60 人 {sd_big:.4f}")


# ------------------------------------------------------------------
# B 组
# ------------------------------------------------------------------
def case_b(n_sub: int = 3) -> None:
    print(f"\n[B] 真实 DDM：数据由 M-T1（ρ=0.5）生成，LOO 是否把 M-T1 排在前面")
    # ⚠️ 规模是**成本**决定的，不是统计决定的：实测（576 试次、K=4）单人冷启动
    # L-BFGS ≤60 步 9.3 s、Hessian 3.4 s ⇒ 超参数 Hessian（4·K(2K+1)/2 次评估）
    # 会跑到几十分钟。这里用 64 试次、2 个被试内参数、N=3 把整条管线跑通；
    # 真数据的规模由 `stage8_run.py` 在**正式数据**上跑，不在自测里跑。
    names = ["d_ref"]
    truth = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                          shape_model="lin")
    design = build_design(30.0, [0.03333, 0.14999], [0.79998, 1.79990], 4)
    print(f"      设计：{design['T'].size} 试次/人（2 档 T × 2 档 W × 4 类 × 4 次）；"
          f"N = {n_sub}；被试内参数 {names}"
          + ("（M-T1 多一个 ρ）" if True else ""))

    subs_m1, subs_m3 = [], []
    t0 = time.perf_counter()
    for s in range(n_sub):
        rng = np.random.default_rng(4100 + s)
        sim = simulate_euler_subject(design, truth, 0.5, rng, dt=5e-5)
        tr = dict(design)
        tr.update({k: np.asarray(v) for k, v in sim.items()})
        subs_m1.append(ddm_subject(tr, truth, names, rho_free=True))
        subs_m3.append(ddm_subject(tr, truth, names, rho_free=False))
    print(f"      生成 {n_sub} 人耗时 {time.perf_counter() - t0:.1f}s")

    out = {}
    for tag, subs, n_draws in (("M-T1（ρ 自由）", subs_m1, 60),
                               ("M-T3（ρ=1）", subs_m3, 60)):
        t0 = time.perf_counter()
        r = fit_and_loo(subs, n_draws=n_draws, seed=5, n_em=6)
        dt = time.perf_counter() - t0
        out[tag] = r
        f = r["fit"]
        print(f"      {tag}: σ̂ = {np.round(f['sigma'], 3)}、"
              f"mu = {np.round(f['mu'], 3)}、n_flipped = {f['n_flipped']}、"
              f"EM {f['n_em_used']} 轮、{dt:.1f}s、"
              f"ELPD = {r['loo']['elpd_loo']:.2f} ± {r['loo']['se']:.2f}")

    a, b = out["M-T1（ρ 自由）"]["loo"], out["M-T3（ρ=1）"]["loo"]
    check("B1 M-T1 的 ELPD 高于 M-T3（数据确实由 M-T1 生成）",
          a["elpd_loo"] > b["elpd_loo"],
          f"{a['elpd_loo']:.2f} vs {b['elpd_loo']:.2f}"
          f"（差 {a['elpd_loo'] - b['elpd_loo']:+.2f}）")
    # ❗ B2 **不**断言"k 落在可用区"——恰恰相反。实测 N=3 时 max k = 4.33 / 5.00、
    # 3/3 个被试都越界，`p_loo` 28.7 / 516.5 远大于 N。这不是 bug，而是
    # **PSIS 在被试层需要足够多的被试**：N 太小 ⇒ 重要性权重天然重尾。
    # 这条判据检查的是**诊断自己会不会报警**（若在 k=5 处还说"可用"，诊断才失效）。
    check("B2 Pareto k 诊断在 N=3 下如实报警（max k > 1.0 ⇒ 本组不构成模型比较证据）",
          a["k_max"] > 1.0 and b["k_max"] > 1.0,
          f"max k：M-T1 {a['k_max']:.2f}、M-T3 {b['k_max']:.2f}；"
          f"k>0.7 个数 {a['n_k_gt_bad']}/{len(a['pareto_k'])}、"
          f"{b['n_k_gt_bad']}/{len(b['pareto_k'])}；"
          f"p_loo/N：{a['p_loo'] / 3:.1f}、{b['p_loo'] / 3:.1f}")
    check("B3 M-T1 的逐被试众数没有撞到非正定（n_flipped = 0）",
          out["M-T1（ρ 自由）"]["fit"]["n_flipped"] == 0,
          f"n_flipped = {out['M-T1（ρ 自由）']['fit']['n_flipped']}")
    print("\n      ⚠️ 判决：B1 的方向正确，但 B2 说明 **N=3 的逐被试 PSIS-LOO 不可作为证据**"
          "\n         （k 越界 ⇒ 中心值可看、区间与差值不可信）。正式设计的 ~40 人/组"
          "\n         必须在正式数据上重跑本诊断后才能引用。")
    print("\n      " + compare_models(out).replace("\n", "\n      "))


def case_c() -> None:
    """C 组（D68）：`n_flipped > 0` 的**机制** —— 被抬平的方向方差 = 1/floor。

    为什么必须单独测：报告里一句「σ 不得解读」如果没有机制支撑，就只是措辞。
    这里用一个**纯二次**的 `ll_x` 把 Hessian 造死：`g = −½(λ1 x1² + λ2 x2²)`，
    `λ1 = 10`、`λ2 = −5` ⇒ `A = −H = diag(10, −5)` ⇒ 有一个负特征值。
    于是 `floor = max(1e-8·10, 1e-12) = 1e-7`，被抬方向的后验方差应恰为 `1/floor = 1e7`。
    附带事实：负曲率方向上目标函数**无上界** ⇒ L-BFGS 会沿该方向发散（`maxiter=2`
    就已经到 1e9 量级）—— 这说明 `n_flipped > 0` 不只是"数值毛刺"，而是"这个点不是众数"。
    """
    print("\n[C] 非正特征值被抬平的机制（D68：cov 该方向 = 1/floor）")
    lam1, lam2 = 10.0, -5.0

    def ll_x(x):
        x = np.asarray(x, float)
        return -0.5 * (lam1 * x[0] ** 2 + lam2 * x[1] ** 2)

    sub = {"ll_x": ll_x, "lo": np.array([-1.0, -1.0]), "hi": np.array([1.0, 1.0])}
    big = float(np.log(1e9))
    floor = max(1e-8 * lam1, 1e-12)
    r = subject_map_laplace(sub, np.array([0.1, 0.1]), np.array([0.0, 0.0]),
                            np.array([big, big]), maxiter=2)
    check("C1 负特征值被如实计入 n_flipped（= 1）", r["n_flipped"] == 1,
          f"eigval = {np.round(r['eigval'], 4)}")
    ratio = float(r["cov"][1, 1] * floor)
    check("C2 被抬方向的方差 = 1/floor（比值 = 1）", abs(ratio - 1.0) < 1e-4,
          f"cov[1,1]·floor = {ratio:.6f}、floor = {floor:.1e}、cov[1,1] = {r['cov'][1, 1]:.3e}")
    check("C3 边际仍有限（退化被吸收，但 `n_flipped` 记了账）",
          bool(np.isfinite(r["log_marginal"])), f"log_marginal = {r['log_marginal']:.3e}")
    check("C4 负曲率方向上众数搜索会发散（该点不是众数）",
          float(np.max(np.abs(r["mode"]))) > 1e3,
          f"|mode|_max = {float(np.max(np.abs(r['mode']))):.3e}")


def main() -> None:
    t0 = time.perf_counter()
    case_a()
    case_b(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    case_c()
    print(f"\n合计：{N_FAIL} 项未通过；总耗时 {time.perf_counter() - t0:.1f}s")
    sys.exit(1 if N_FAIL else 0)


if __name__ == "__main__":
    main()
