"""`loo.py` 的自测：三部分，各有可判定的判据。

为什么要写这个
==============
PSIS-LOO 是 Stage 8 的模型比较入口（主计划 §3 Stage 8 要求「PSIS-LOO（含
Pareto k 诊断）」）。自己实现的估计量若没有**解析基准**或**已知形状**做对照，
"跑出个数"完全不能证明它对。本脚本给出两个独立基准：

* **A 解析基准**：一元高斯模型 `y_i ~ N(mu, 1)`、先验 `mu ~ N(0, 1)`，
  其**解析 LOO 预测密度**可闭式写出（下面推导），于是 PSIS-LOO 有真值可比。
* **B 已知尾部**：直接令重要性比 `r` 服从 Pareto(α)，由 GPD 的定义性质
  （超过任意阈值的超额仍为同形状 Pareto），拟合出的 `k` 应等于 `1/α`。
  取 α = 3 与 α = 1.2 两支，后者 `k ≈ 0.83 > 0.7` ⇒ **必须被诊断器报警**。

推导（A 的解析 LOO）
--------------------
`n` 个观测、已知 `sigma = 1`、先验精度 1：
* 全数据后验精度 `1 + n`，均值 `Σy / (1 + n)`；
* 去掉第 `i` 个观测后，后验精度 `n`，均值 `Σ_{j≠i} y_j / n`；
* 对 `y_i` 的预测分布是 `N(mean_loo_i, 1 + 1/n)`（观测噪声 1 + 后验方差 1/n）。
⇒ `elpd_loo_i` 可闭式算出，与 PSIS-LOO 的差应落在蒙特卡洛误差内。

运行
----
    python _scratch/check_loo.py
退出码 0 = 全部判据通过；1 = 有判据不过。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loo import K_BAD, loo_compare, psis_loo, waic  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, bool(ok), detail))
    print(("  ✅ " if ok else "  ❌ ") + name + "：" + detail)


# --------------------------------------------------------------------------- #
# A. 解析基准：一元高斯模型
# --------------------------------------------------------------------------- #
def case_a() -> None:
    print("\n[A] 解析基准（一元高斯，n=20，S=4000 条后验抽样）")
    rng = np.random.default_rng(20261014)
    n, S = 20, 4000
    y = rng.normal(0.35, 1.0, size=n)

    # 全数据后验：精度 1+n
    prec = 1.0 + n
    mu = rng.normal(y.sum() / prec, 1.0 / np.sqrt(prec), size=S)
    log_norm = -0.5 * np.log(2 * np.pi)
    L = log_norm - 0.5 * (y[None, :] - mu[:, None]) ** 2

    # 解析 LOO：去掉第 i 个后 精度 n、均值 (Σy - y_i)/n，预测方差 1 + 1/n
    mean_loo = (y.sum() - y) / n
    var_pred = 1.0 + 1.0 / n
    elpd_i_true = log_norm - 0.5 * np.log(var_pred) - 0.5 * (y - mean_loo) ** 2 / var_pred
    elpd_true = float(np.sum(elpd_i_true))

    out = psis_loo(L)
    diff = abs(out["elpd_loo"] - elpd_true)
    check("A1 PSIS-LOO ≈ 解析 LOO",
          diff < 0.15,
          "PSIS = %.3f，解析 = %.3f，|差| = %.3f（判据 < 0.15）"
          % (out["elpd_loo"], elpd_true, diff))
    check("A2 逐点 LOO 也吻合（最大逐点偏差 < 0.25）",
          float(np.max(np.abs(out["elpd_i"] - elpd_i_true))) < 0.25,
          "最大逐点偏差 = %.3f" % float(np.max(np.abs(out["elpd_i"] - elpd_i_true))))
    check("A3 p_loo ≈ 1（真值：1 个自由参数 mu）",
          abs(out["p_loo"] - 1.0) < 0.35,
          "p_loo = %.3f（判据 |p_loo − 1| < 0.35）" % out["p_loo"])
    check("A4 轻尾部 ⇒ 无 k 报警",
          out["n_k_gt_bad"] == 0 and out["k_max"] < 0.5,
          "max k = %.3f，k>0.7 个数 = %d" % (out["k_max"], out["n_k_gt_bad"]))
    w = waic(L)
    check("A5 WAIC ≈ PSIS-LOO（小 k 时两者应接近）",
          abs(w["elpd_waic"] - out["elpd_loo"]) < 0.3,
          "WAIC = %.3f，PSIS = %.3f" % (w["elpd_waic"], out["elpd_loo"]))
    check("A6 无失败观测", out["n_failed"] == 0, "n_failed = %d" % out["n_failed"])


# --------------------------------------------------------------------------- #
# B. 已知尾部：直接构造 Pareto 重要性比
# --------------------------------------------------------------------------- #
def _pareto_loglik(alpha: float, S: int, N: int, rng) -> np.ndarray:
    """构造逐点对数似然，使其重要性比 `r = 1/lik` 恰为 Pareto(α)。

    `F(r) = 1 − r^{-α}` ⇒ `r = (1 − U)^{-1/α}`，GPD 形状参数 `k = 1/α`。
    于是 `log lik = -log r`（差一个常数，而常数在 PSIS 的两个 logsumexp 里抵消）。
    """
    u = rng.random((S, N))
    r = np.power(1.0 - u, -1.0 / alpha)
    return -np.log(r)


def case_b() -> None:
    print("\n[B] 已知尾部：Pareto 重要性比，验证 k̂ 与报警（S=4000，N=200）")
    S, N = 4000, 200
    # ⚠️ 期望值与容差不是拍脑袋定的，来自 `_scratch/diag_gpd_bias.py` 的 2000 次重复实测：
    #   α=3.0 ⇒ E[k̂] = 0.3248（真值 0.3333，偏差 −0.0086），**单观测 SD = 0.103**
    #   α=1.2 ⇒ E[k̂] = 0.8200（真值 0.8333，偏差 −0.0134），**单观测 SD = 0.143**
    # 单观测的 `k̂` 噪声很大（这正是 Vehtari 建议看"个数/分布"而不是逐点值的原因），
    # 所以判据只对 **N 个观测的均值** 设绝对容差（约 4 个均值的 SE），
    # 对报警则只要求**压倒性多数**，不要求 100%。
    for alpha, sd in ((3.0, 0.103), (1.2, 0.143)):
        rng = np.random.default_rng(7)
        L = _pareto_loglik(alpha, S, N, rng)
        out = psis_loo(L)
        expect = 1.0 / alpha
        k = out["pareto_k"]
        tol = max(0.035, 4.0 * sd / np.sqrt(N))
        check("B α=%.1f ⇒ k̂ 均值 ≈ 1/α = %.3f" % (alpha, expect),
              abs(float(np.mean(k)) - expect) < tol,
              "k̂ 均值 = %.4f、中位 = %.4f、偏差 = %+.4f（容差 ±%.3f）"
              % (float(np.mean(k)), out["k_median"], float(np.mean(k)) - expect, tol))
        frac = out["n_k_gt_bad"] / N
        if expect > K_BAD:
            check("B α=%.1f ⇒ 压倒性多数被 k>0.7 报警（理论 80%%）" % alpha,
                  frac >= 0.6,
                  "k>0.7 个数 = %d / %d = %.0f%%" % (out["n_k_gt_bad"], N, 100 * frac))
        else:
            check("B α=%.1f ⇒ 几乎不报警（k ≈ %.2f < 0.7）" % (alpha, expect),
                  frac <= 0.02,
                  "k>0.7 个数 = %d / %d" % (out["n_k_gt_bad"], N))
        check("B α=%.1f ⇒ 单观测 k̂ 的 SD ≈ 实测 %.3f" % (alpha, sd),
              abs(float(np.std(k, ddof=1)) - sd) < 0.05,
              "实测 SD = %.3f" % float(np.std(k, ddof=1)))


# --------------------------------------------------------------------------- #
# C. loo_compare 的差值口径
# --------------------------------------------------------------------------- #
def case_c() -> None:
    print("\n[C] loo_compare：模型比较表的配对差")
    rng = np.random.default_rng(99)
    n, S = 30, 2000
    y = rng.normal(0.3, 1.0, size=n)
    mu = rng.normal(y.mean(), 0.3, size=S)
    ln = -0.5 * np.log(2 * np.pi)
    L_good = ln - 0.5 * (y[None, :] - mu[:, None]) ** 2
    L_bad = ln - 0.5 * np.log(2.0) - 0.5 * (y[None, :] - mu[:, None]) ** 2 / 2.0
    table = loo_compare({"M_good": L_good, "M_bad": L_bad})
    print("\n".join("     " + ln_ for ln_ in table.splitlines()))
    ok = ("M_good" in table) and ("M_bad" in table) and ("基准模型" in table)
    check("C1 表格含两个模型与基准说明", ok, "长度 %d 字符" % len(table))
    # M_good 应胜出（方差正确）
    r_good = psis_loo(L_good)["elpd_loo"]
    r_bad = psis_loo(L_bad)["elpd_loo"]
    check("C2 正确方差模型胜出", r_good > r_bad,
          "M_good = %.2f > M_bad = %.2f" % (r_good, r_bad))


# --------------------------------------------------------------------------- #
def main() -> int:
    print("=" * 72)
    print("loo.py 自测（PSIS-LOO / Pareto k / WAIC / loo_compare）")
    print("=" * 72)
    case_a()
    case_b()
    case_c()
    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    n_all = len(RESULTS)
    print("\n" + "=" * 72)
    if n_ok == n_all:
        print("✅ 全部 %d 项判据通过" % n_all)
        return 0
    print("❌ %d / %d 项通过，失败项：" % (n_ok, n_all))
    for name, ok, detail in RESULTS:
        if not ok:
            print("   - " + name + "：" + detail)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
