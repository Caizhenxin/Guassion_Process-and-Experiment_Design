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

import re
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

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
# D. 外部交叉复核（D63）：本机装了 ArviZ 的那个解释器跑出来的对照记录
# --------------------------------------------------------------------------- #
def case_d() -> None:
    """`loo.py` 是**手写** PSIS，最大的风险是「自己对自己一致」。D63 用本机
    `D:\\Conda\\envs\\hssm\\python.exe`（pymc 5.28.5 + arviz 0.23.4）在同一份逐点
    对数似然矩阵上跑 `arviz.loo` 做独立复核 —— 但那条路线**不能**进本自测（自测跑在
    零依赖解释器上）。所以这里守的是**证据可追溯**：探针记录必须在场、且自报一致。

    ⚠️ 这条判据**不**重算 ArviZ 的结果（没有 arviz 就不可能有），它只保证「文档里那句
    『ArviZ 复核一致』指得到的文件确实存在、且里面确实是那个结论」—— 反过来说，删掉
    探针日志会让文档里的声明失去依据，这正是它要防的。
    """
    print("\n[D] 外部交叉复核记录（ArviZ，D63）")
    log = _HERE / "_probe_bayes_stack_u8.txt"
    if not log.is_file():
        check("D1 交叉复核日志必须存在（文档里的「ArviZ 一致」要指得到它）", False, "缺 %s" % log.name)
        return
    txt = log.read_text(encoding="utf-8")
    check("D1 交叉复核日志必须存在且自报一致", "✓ 两套 PSIS 在同一矩阵上一致" in txt,
          "含一致行" if "✓ 两套 PSIS 在同一矩阵上一致" in txt else "未自报一致")
    m = re.search(r"相对 ([+-][0-9.eE+-]+)", txt)
    rel = abs(float(m.group(1))) if m else float("nan")
    check("D2 相对差必须 < 1e-3（手写 PSIS 与 ArviZ 在同一矩阵上）",
          rel == rel and rel < 1e-3, "相对差 = %.2e" % rel)
    check("D3 日志必须记下 pymc 版本与「采样能否用」这两件事（D63 的结论就建立在这两点上）",
          "pymc" in txt and ("pm.sample 可用" in txt or "pm.sample 失败" in txt),
          "pymc=%s、采样=%s" % ("有" if "pymc" in txt else "缺",
                                "可用" if "pm.sample 可用" in txt else "失败"))


# --------------------------------------------------------------------------- #
# E. 病态抽样的**存活**（D73）：单个 (抽取, 被试) 的 Hessian 非有限
# --------------------------------------------------------------------------- #
def case_e() -> None:
    """长跑里最贵的死法：40 小时的作业在第 39 小时被**一个**病态超参数抽样杀掉。

    `subject_map_laplace` 在众数处 `∂²g` 非有限时会抛 `ValueError`。若 `loo_matrix`
    不接住它，整个 Stage 8 运行就崩在这一格上（实测发生过：`_probe_loo_draws.py`
    用 S=30 的 `analytic` 抽样时就撞到了，报「在众数处 ∂²g 非有限（28/64 个元素）」）。

    判据：(1) 不抛异常；(2) 该格记 −inf；(3) 计入 `n_hessian_fail`；
    (4) 该列被 `psis_loo` 记为失败（`n_failed ≥ 1`），而不是把全表算成 nan 或崩掉。
    """
    print("\n[E] 病态抽样不许中断整轮（D73）")
    import hier

    calls = {"n": 0}

    def fake_smap(sub, x0, mu, ls, maxiter=None, **kw):       # noqa: ANN001
        calls["n"] += 1
        if sub.get("boom"):
            raise ValueError("在众数处 ∂²g 非有限（假）")
        return {"mode": np.asarray(x0, float), "log_marginal": 5.0,
                "fell_back": False, "n_nonfinite_g": 0,
                "cov": np.eye(2), "converged": True}

    subs = [{"id": "ok"}, {"id": "bad", "boom": True}]
    hyper = {"theta": np.zeros((3, 4))}
    real = hier.subject_map_laplace
    stats: dict = {}
    try:
        hier.subject_map_laplace = fake_smap
        L = hier.loo_matrix(subs, hyper, mode_warm=[np.zeros(2), np.zeros(2)],
                            stats=stats)
        err = None
    except Exception as exc:                                   # noqa: BLE001
        L, err = None, f"{type(exc).__name__}: {exc}"
    finally:
        hier.subject_map_laplace = real

    check("E1 Hessian 非有限**不再**中断整轮", err is None, err or "未抛异常")
    if L is None:
        return
    check("E2 病态格记 −inf（而不是 NaN 冒充数值）",
          np.all(np.isneginf(L[:, 1])) and np.all(L[:, 0] == 5.0),
          "第 2 列全 −inf = %s、第 1 列全 5.0 = %s"
          % (bool(np.all(np.isneginf(L[:, 1]))), bool(np.all(L[:, 0] == 5.0))))
    check("E3 退化计数 `n_hessian_fail` 逐格累加", stats.get("n_hessian_fail") == 3,
          "n_hessian_fail = %s（应为 3 = 3 次抽取 × 1 名病态被试）"
          % stats.get("n_hessian_fail"))
    out = psis_loo(L)
    check("E4 该列被 PSIS 记为失败（`n_failed ≥ 1`），不污染其他列",
          out["n_failed"] >= 1 and np.isfinite(out["elpd_loo"]),
          "n_failed = %d、elpd_loo = %.3f" % (out["n_failed"], out["elpd_loo"]))


# --------------------------------------------------------------------------- #
# F. 试次层矩阵（D73）：`loo_matrix_trials` 的形状 / 摊薄 / 失败语义
# --------------------------------------------------------------------------- #
def case_f() -> None:
    """D73 的落地口径：**PSIS 放试次层**。这里只量「矩阵怎么构造」这一层语义。

    真值证据在 `_scratch/_probe_loo_level.txt`（同一批抽取下被试层 `p_loo/n_obs = 496`
    vs 试次层 `0.138`）与 `_probe_trials_sum.txt`（逐试次之和 == 整人似然，误差 0）。
    本 case 保证：形状 = ``(S, Σ n_s)``、缺 `ll_trials_x` 的对象**报错不降级**、
    逐试次似然非有限的被试块记 −inf 并计数 —— 三条都属于「静默错位就会毁掉一篇论文」
    的那种错。
    """
    print("\n[F] 试次层 LOO 矩阵（D73）")
    import hier

    def fake_smap(sub, x0, mu, ls, maxiter=None, **kw):       # noqa: ANN001
        return {"mode": np.asarray(x0, float), "log_marginal": 5.0,
                "fell_back": False, "n_nonfinite_g": 0,
                "cov": np.eye(2), "converged": True}

    def mk(n, offset, fail=False):                            # noqa: ANN001
        def ll(mode, n=n, offset=offset, fail=fail):          # noqa: ANN001
            if fail:
                return None
            return np.full(n, -1.0) + offset
        return {"kind": "ddm", "ll_trials_x": ll,
                "tr": {"rt": np.zeros(n)}, "lo": np.zeros(2), "hi": np.ones(2),
                "names": ["a", "b"]}

    subs = [mk(4, 0.0), mk(3, 10.0)]
    hyper = {"theta": np.zeros((2, 4))}
    stats: dict = {}
    real = hier.subject_map_laplace
    try:
        hier.subject_map_laplace = fake_smap
        L = hier.loo_matrix_trials(subs, hyper, mode_warm=[np.zeros(2)] * 2,
                                   stats=stats)
    finally:
        hier.subject_map_laplace = real
    check("F1 形状 = (抽取数, 总试次)", L.shape == (2, 7), "shape = %s" % (L.shape,))
    check("F2 每个被试的贡献落在自己的列块里（块内常数 = 该被试的值）",
          np.all(L[:, :4] == -1.0) and np.all(L[:, 4:] == 9.0),
          "前 4 列全 −1.0 = %s、后 3 列全 9.0 = %s"
          % (bool(np.all(L[:, :4] == -1.0)), bool(np.all(L[:, 4:] == 9.0))))
    check("F3 `n_trial_ll_fail` / `n_hessian_fail` 在健康输入上为 0",
          stats.get("n_trial_ll_fail") == 0 and stats.get("n_hessian_fail") == 0,
          "stats = %s" % (stats,))

    # F4：逐试次似然非有限 ⇒ 该块 −inf，计数 +1/抽取，不中断
    st2: dict = {}
    try:
        hier.subject_map_laplace = fake_smap
        L2 = hier.loo_matrix_trials([mk(4, 0.0), mk(3, 0.0, fail=True)], hyper,
                                    mode_warm=[np.zeros(2)] * 2, stats=st2)
        err = None
    except Exception as exc:                                   # noqa: BLE001
        L2, err = None, f"{type(exc).__name__}: {exc}"
    finally:
        hier.subject_map_laplace = real
    check("F4 逐试次似然非有限 ⇒ 该块记 −inf 并计数（不中断整轮）",
          err is None and L2 is not None and np.all(np.isneginf(L2[:, 4:]))
          and st2.get("n_trial_ll_fail") == 2,
          err or "第 2 块全 −inf = %s、n_trial_ll_fail = %s"
          % (bool(L2 is not None and np.all(np.isneginf(L2[:, 4:]))),
             st2.get("n_trial_ll_fail")))

    # F5：解析基准对象（无 ll_trials_x）必须报错，不许静默降级到被试层
    sub0 = hier.make_subject(lambda x: -0.5 * float(np.sum(np.asarray(x) ** 2)),
                             np.zeros(2), np.ones(2), ["a", "b"])
    try:
        hier.loo_matrix_trials([sub0, sub0], hyper)
    except ValueError as exc:
        check("F5 不支持逐试次似然的对象**报错**（不静默降级）",
              "ll_trials_x" in str(exc), "报错信息：%s" % str(exc)[:60])
    else:
        check("F5 不支持逐试次似然的对象**报错**（不静默降级）", False,
              "竟然接受了 make_subject 构造的对象")


# --------------------------------------------------------------------------- #
def main() -> int:
    print("=" * 72)
    print("loo.py 自测（PSIS-LOO / Pareto k / WAIC / loo_compare）")
    print("=" * 72)
    case_a()
    case_b()
    case_c()
    case_d()
    case_e()
    case_f()
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
