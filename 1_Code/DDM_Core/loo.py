"""零依赖的 PSIS-LOO：Pareto 平滑重要性采样留一交叉验证。

为什么需要这个模块
==================
主计划 §3 Stage 8 要求「层级 DDM 拟合 → PPC → **PSIS-LOO（含 Pareto k 诊断）**
→ 模型比较 → leave-one-participant-out」。但本机的 Python 环境**没有**任何
贝叶斯采样/诊断库（`pymc` / `numpyro` / `jax` / `arviz` / `cmdstanpy` / `emcee` /
`hddm` 全部缺失，只有 `numpy` / `scipy` / `pandas` / `matplotlib` / `sklearn`）。

因此本模块按 **Vehtari, Gelman & Gabry (2017)** 的算法 1 自己实现 PSIS，
配合 `likelihood.numerical_hessian` 给出的**拉普拉斯近似**后验抽样
（见 `stage8.laplace_draws`）即可得到 PSIS-LOO 与 Pareto k 诊断，
**不引入任何新依赖**。若以后获批安装 `pymc` + `arviz`，本模块可作为
交叉验证的第二个实现保留。

算法要点（与参考实现一致）
==========================
对每个观测 i（S 条抽样 = S 行）：
1. 原始重要性比 `r_s = 1 / lik_s`；
2. 取最大的 `M = min(S/5, 3*sqrt(S))` 个比值，对其超出第 `M+1` 大值（阈值 `u`）
   的**超额**拟合广义 Pareto 分布（GPD，形状 `k`、尺度 `sigma`）；
3. 用拟合的 GPD 分位数**替换**这 M 个最大值（Pareto 平滑）；
4. 截断：`w = min(w, S**0.75 * mean(w))`；
5. `elpd_i = logsumexp(log w + log lik) - logsumexp(log w)`。

两个关键不变量（本模块依赖它们做数值稳定化）
--------------------------------------------
* 权重整体乘正常数 `c` **不改变** `elpd_i`（两个 logsumexp 同时平移 `log c`）；
* 因此截断阈值同样尺度不变（`mean` 同步缩放）。
⇒ 可以对 `log r` 减去最大值后再取指数，不影响结果。

Pareto k 的诊断口径（Vehtari 2017, §3.2）
==========================================
`k <= 0.7` 可用；`k > 0.7` 该观测的 LOO 估计不可靠（应改用 `k`-fold CV）；
`k > 1` 估计量方差无穷，必须换法。本模块对每个观测返回自己的 `k`，
`psis_loo` 汇总报告 `k > 0.7` 与 `k > 1` 的**个数**与**最大 k**。

⚠️ **单观测的 `k̂` 噪声很大，不要逐点解读**（本模块实测，见
`_scratch/diag_gpd_bias.py`，2000 次重复、S=4000、M=189）：
* Pareto(α=3.0)（真值 `k = 0.3333`）：`E[k̂] = 0.3248`（偏差 −0.0086），**单观测 SD = 0.103**；
* Pareto(α=1.2)（真值 `k = 0.8333`）：`E[k̂] = 0.8200`（偏差 −0.0134），**单观测 SD = 0.143**。
⇒ 结论：(1) 估计量只有约 1–3% 的负偏差，可用；(2) 但**逐点 `k̂` 的 ±0.1 抖动是正常的**，
所以判断"是否该换 `k`-fold CV"要看 `n_k_gt_bad / N` 这个**比例**与 `k_max`，
而不是某一个观测的 `k̂` 是否刚好越过 0.7；(3) 解析基准见 `_scratch/check_loo.py` A 组
（与一元高斯模型的闭式 LOO 差 0.015）。
"""
from __future__ import annotations

import sys

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp

__all__ = ["gpd_fit", "gpd_ppf", "psis_one", "psis_loo", "waic", "loo_compare"]

K_BAD = 0.7     # 超过它 ⇒ 该观测的 LOO 估计不可靠
K_UNUSABLE = 1.0  # 超过它 ⇒ 重要性权重方差无穷，必须换方法
_MIN_EXCESS = 5   # 超额点太少就不拟合 GPD，退回纯截断


# --------------------------------------------------------------------------- #
# 广义 Pareto 分布
# --------------------------------------------------------------------------- #
def gpd_fit(excess: np.ndarray) -> tuple[float, float]:
    """对正的超额样本拟合 GPD，返回 `(k, sigma)`。

    用**一维剖面似然**（Grimshaw 技巧）：给定形状 `k` 时，尺度 `sigma` 的 MLE
    由一维方程

        给定 a = k / sigma，则  Σ_i 1 / (1 + a y_i) = m / (1 + k)

    唯一确定（左端关于 `a` 单调递减 ⇒ 二分即可），于是只需对 `k` 做一维搜索。
    这比直接跑二维数值优化稳定得多：2 维 BFGS 在 `k` 附近平缓时会提前停，
    得到的 `k̂` 会**系统性偏低**（本模块早期版本实测偏 ~10%）。
    """
    y = np.asarray(excess, dtype=float)
    y = y[y > 0]
    m = y.size
    if m < _MIN_EXCESS:
        return 0.0, float(y.mean()) if m else 1.0

    def neg_ll_profile(k: float) -> float:
        if abs(k) < 1e-6:                      # 指数尾部（k = 0）的闭式解
            sigma0 = float(y.mean())
            return m * np.log(sigma0) + float(np.sum(y)) / sigma0
        target = m / (1.0 + k)
        # 解 Σ 1/(1 + a y) = target：左端关于 a 单调递减，先定上界再二分
        lo, hi = 1e-12, 1.0
        for _ in range(100):
            if float(np.sum(1.0 / (1.0 + hi * y))) < target:
                break
            hi *= 2.0
        else:
            return 1e12
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            g = float(np.sum(1.0 / (1.0 + mid * y))) - target
            if g > 0:
                lo = mid
            else:
                hi = mid
        a = 0.5 * (lo + hi)
        sigma = k / a
        if not np.isfinite(sigma) or sigma <= 0:
            return 1e12
        return m * np.log(sigma) + (1.0 / k + 1.0) * float(np.sum(np.log1p(a * y)))

    try:
        res = minimize_scalar(neg_ll_profile, bounds=(-0.95, 5.0), method="bounded",
                              options={"xatol": 1e-6})
    except Exception:
        return 0.0, float(y.mean())
    if not np.isfinite(res.fun):
        return 0.0, float(y.mean())

    k = float(res.x)
    if abs(k) < 1e-6:
        return 0.0, float(y.mean())
    target = m / (1.0 + k)
    a = _solve_a(y, target)
    sigma = k / a if a > 0 else float(y.mean())
    if not np.isfinite(k) or k <= -1.0 or not np.isfinite(sigma) or sigma <= 0:
        return 0.0, float(y.mean())
    k = float(np.clip(k, -0.9, 5.0))
    return k, sigma


def _solve_a(y: np.ndarray, target: float) -> float:
    """解 `Σ 1/(1 + a y_i) = target`（`a > 0`），二分法。"""
    lo, hi = 1e-12, 1.0
    for _ in range(100):
        if float(np.sum(1.0 / (1.0 + hi * y))) < target:
            break
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        g = float(np.sum(1.0 / (1.0 + mid * y))) - target
        if g > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def gpd_ppf(p, k: float, sigma: float):
    """GPD 的逆 CDF：`F^{-1}(p)`，`p ∈ (0, 1)`。"""
    p = np.asarray(p, dtype=float)
    if abs(k) < 1e-8:
        return -sigma * np.log1p(-p)
    return sigma * (np.power(1.0 - p, -k) - 1.0) / k


# --------------------------------------------------------------------------- #
# 单个观测的 PSIS
# --------------------------------------------------------------------------- #
def psis_one(log_lik_row: np.ndarray) -> tuple[float, float]:
    """单个观测的 PSIS-LOO。

    参数
    ----
    log_lik_row : (S,) 该观测在 S 条后验抽样下的**逐点对数似然**。

    返回
    ----
    `(elpd_i, k_hat)`：该观测的 LOO 对数预测密度，以及拟合出的 Pareto 形状参数。
    """
    ll = np.asarray(log_lik_row, dtype=float)
    S = ll.size
    if S < 10 or not np.all(np.isfinite(ll)):
        return float("nan"), float("nan")

    # 比值 r = 1/lik ⇒ log r = -log lik；按似然**升序**排即比值降序
    # （似然最小者比值最大，最危险，排在最前）
    order = np.argsort(ll)
    log_r_sorted = -ll[order]
    shift = log_r_sorted[0]
    z = np.exp(log_r_sorted - shift)            # z[0] == 1，降序

    M = int(min(S / 5.0, 3.0 * np.sqrt(S)))
    M = max(M, 2)
    if M >= S:
        M = S - 1
    u = float(z[M])                             # 阈值 = 第 M+1 大的比值
    excess = z[:M] - u
    excess = excess[excess > 0]

    if excess.size >= _MIN_EXCESS:
        k_hat, sigma = gpd_fit(excess)
        # 平滑：把最大的 M 个比值替换成拟合 GPD 的分位数（降序）
        p = (np.arange(M, 0, -1) - 0.5) / M
        smoothed = u + gpd_ppf(p, k_hat, sigma)
        z = z.copy()
        z[:M] = smoothed
        if not np.all(np.isfinite(z)):
            # GPD 分位数溢出：整体退回未平滑的比值（此时 k 不可信，记为 nan）
            z = np.exp(log_r_sorted - shift)
            k_hat = float("nan")
    else:
        k_hat = 0.0                             # 数据太少，不做平滑

    # 截断（尺度不变）
    z = np.minimum(z, S ** 0.75 * float(np.mean(z)))
    z = np.maximum(z, np.finfo(float).tiny)
    log_w = np.log(z)
    elpd_i = float(logsumexp(log_w + ll[order]) - logsumexp(log_w))
    return elpd_i, k_hat


# --------------------------------------------------------------------------- #
# 汇总
# --------------------------------------------------------------------------- #
def psis_loo(log_lik: np.ndarray) -> dict:
    """PSIS-LOO。`log_lik` 形状 `(S, N)`（S 条抽样 × N 个观测）。"""
    L = np.asarray(log_lik, dtype=float)
    if L.ndim != 2:
        raise ValueError("log_lik 必须是 (S, N) 二维数组")
    S, N = L.shape
    elpd = np.empty(N)
    k_hat = np.empty(N)
    for i in range(N):
        elpd[i], k_hat[i] = psis_one(L[:, i])

    ok = np.isfinite(elpd)
    elpd_loo = float(np.sum(elpd[ok]))
    se = float(np.sqrt(N * np.var(elpd[ok], ddof=1))) if ok.sum() > 1 else float("nan")

    # lppd 与有效参数个数：p_loo = lppd - elpd_loo（Vehtari 2017 式 12/13）
    with np.errstate(invalid="ignore"):
        lppd = float(np.sum(logsumexp(L, axis=0) - np.log(S)))
    p_loo = lppd - elpd_loo

    k_finite = k_hat[np.isfinite(k_hat)]
    return {
        "elpd_loo": elpd_loo,
        "se": se,
        "p_loo": p_loo,
        "n_obs": int(N),
        "n_draws": int(S),
        "elpd_i": elpd,
        "pareto_k": k_hat,
        "k_max": float(k_finite.max()) if k_finite.size else float("nan"),
        "k_median": float(np.median(k_finite)) if k_finite.size else float("nan"),
        "n_k_gt_bad": int(np.sum(k_finite > K_BAD)),
        "n_k_gt_unusable": int(np.sum(k_finite > K_UNUSABLE)),
        "n_failed": int(np.sum(~ok)),
        # S < 25 时 M = min(S/5, 3√S) < 5，GPD 永不拟合 ⇒ k̂ 恒 0，
        # `n_k_gt_bad = 0` 不代表「诊断通过」，只代表「没有诊断能力」。
        "k_diag_ok": bool(S >= 25),
    }


def waic(log_lik: np.ndarray) -> dict:
    """WAIC：与 PSIS-LOO 用同一个逐点对数似然矩阵，作为交叉核对。

    `lppd = Σ log mean_s lik`、`p_waic = Σ var_s(log lik)`、`elpd = lppd - p_waic`。
    ⚠️ WAIC 与 PSIS-LOO 在小 `k` 时应接近；两者**不一致**本身就是诊断信号
    （通常意味着重要性权重尾部很重，这时以 PSIS-LOO 的 `k` 为准）。
    """
    L = np.asarray(log_lik, dtype=float)
    if L.ndim != 2:
        raise ValueError("log_lik 必须是 (S, N) 二维数组")
    S, N = L.shape
    lppd_i = logsumexp(L, axis=0) - np.log(S)
    p_waic_i = np.var(L, axis=0, ddof=1)
    elpd_i = lppd_i - p_waic_i
    return {
        "elpd_waic": float(np.sum(elpd_i)),
        "se": float(np.sqrt(N * np.var(elpd_i, ddof=1))),
        "p_waic": float(np.sum(p_waic_i)),
        "n_obs": int(N),
        "n_draws": int(S),
    }


def loo_compare(models: dict[str, np.ndarray]) -> str:
    """比较多个模型的逐点对数似然矩阵，返回 Markdown 表格文本。

    差值口径：以 ELPD 最高者为基准，给出 `ΔELPD` 与配对差的 `SE`
    （`SE = sqrt(N) * sd(elpd_a - elpd_b)`，**不能**用两个 SE 各自相加）。
    """
    res = {name: psis_loo(L) for name, L in models.items()}
    order = sorted(res, key=lambda n: -res[n]["elpd_loo"])
    best = order[0]
    lines = [
        "| 模型 | ELPD-LOO | SE | p_loo | ΔELPD | Δ 的 SE | max k | k>0.7 个数 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in order:
        r = res[name]
        if name == best:
            d_elpd, d_se = 0.0, 0.0
        else:
            diff = r["elpd_i"] - res[best]["elpd_i"]
            ok = np.isfinite(diff)
            d_elpd = float(np.sum(diff[ok]))
            d_se = float(np.sqrt(ok.sum() * np.var(diff[ok], ddof=1)))
        lines.append("| %s | %.1f | %.1f | %.1f | %+.1f | %.1f | %.2f | %d |" % (
            name, r["elpd_loo"], r["se"], r["p_loo"], d_elpd, d_se,
            r["k_max"], r["n_k_gt_bad"]))
    lines.append("")
    lines.append("基准模型 = `%s`（ELPD 最高）；`ΔELPD` 为负表示比基准差。" % best)
    return "\n".join(lines)


if __name__ == "__main__":  # 极小自检：无需外部数据
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = np.random.default_rng(0)
    n, S = 20, 4000
    y = rng.normal(0.3, 1.0, size=n)
    prec = 1.0 + n
    mu = rng.normal(y.sum() / prec, 1.0 / np.sqrt(prec), size=S)
    L = -0.5 * (y[None, :] - mu[:, None]) ** 2 - 0.5 * np.log(2 * np.pi)
    out = psis_loo(L)
    print("PSIS-LOO ELPD = %.3f ± %.3f  (p_loo = %.2f, max k = %.2f)"
          % (out["elpd_loo"], out["se"], out["p_loo"], out["k_max"]))
    print("WAIC   ELPD = %.3f" % waic(L)["elpd_waic"])
