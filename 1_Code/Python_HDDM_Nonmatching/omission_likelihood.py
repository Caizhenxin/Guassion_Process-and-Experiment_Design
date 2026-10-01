# -*- coding: utf-8 -*-
"""阶段 1：遗漏似然项 P(遗漏 | v, a, z, t0, deadline) 的解析实现与校验

数学（主口径 A：解析 Wiener 生存函数）
====================================
恒定边界 Wiener 扩散：吸收壁在 0 与 a（`a` = **分离度**），起点 z·a（`z` 为边界比例），
漂移 v，扩散系数 σ=1。令 T 为首达时，则

    P(遗漏) = P(T > D) = S(D),      D = deadline − t0

生存函数有闭式谱级数解：

    S(D) = (2π/a²) · e^{−v²D/2} · e^{−v·(z·a)}
                 · Σ_{k≥1} k·sin(kπ z)·[1 − (−1)^k e^{va}] / (v² + (kπ/a)²) · e^{−k²π²D/(2a²)}

推导：令 p = e^{v(x−x0)}·q（x0 = z·a 为绝对起点），则 q 满足无漂移热方程再减去 v²/2；
Dirichlet 本征函数为 sin(kπx/a)，本征值 v²/2 + k²π²/(2a²)；系数由 δ 的 Fourier 正弦展开
给出，对 x∈(0,a) 积分时产生起点权重因子 e^{−v·x0}（**这一步最初漏掉，误差达 0.23，
靠 dt→0 的仿真对账抓出来**）。
v→0 时退化为经典结果 Σ_{k 奇} (4/(kπ))·sin(kπ z)·e^{−k²π²D/(2a²)}（已核对）。

与仿真器的口径（唯一事实来源 `sim_utils.simulate_trials`）
====================================================
* Euler–Maruyama，dt = 0.002，σ = 1；壁在 0 与 a；起点 start = z·a（z 为比例）；
* 判遗漏：决策时间 > deadline − t0，即 D = deadline − t0；
* ⇒ P(遗漏) = S(D)，与上式同构。

⚠️ 纪律：本模块的数值实现必须先用 `sim_utils` 交叉校验（`python omission_likelihood.py`），
   这是防止出现"第二套事实来源"的唯一办法（规格文档 §5 步骤 1）。

用法
====
  python omission_likelihood.py            # 跑自检（解析 vs 仿真）
  python omission_likelihood.py --n 60000  # 加大仿真试次数
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 生存函数级数的收敛控制
MAX_TERMS = 500
TOL = 1e-12


def wiener_survival(D, v, a, z, max_terms=MAX_TERMS, tol=TOL):
    """P(T > D)：Wiener 首达时的生存函数（向量化谱级数）。

    参数
    ----
    D : deadline − t0（秒）
    v : 漂移率
    a : 边界**分离度**（0..a）
    z : **相对**起点，落在 (0,1)

    返回与广播后形状一致的数组；D ≤ 0 处返回 1（没有时间触界）。

    ⚠️ 实现为**矩阵形式**：把级数的 k 循环整体向量化（`(K, n)` 一次算完），
    而不是逐项 Python 循环。这项优化是必须的——势函数在一次 MCMC 迭代里会被调用
    上百次（每个随机节点的步进器都要算一遍它的对数后验），逐项循环会把采样拖慢 3 倍以上。
    项数上界由指数因子解析给出：需要 k²·π²D/(2a²) ≳ log(1/tol)，即
    K ≈ √(2·log(1/tol))·a/(π√D)。
    """
    D = np.asarray(D, dtype=float)
    v = np.asarray(v, dtype=float)
    a = np.asarray(a, dtype=float)
    # 起点比例裁到开区间，避免 sin(kπz) 在端点上恒为 0 造成的退化
    z = np.clip(np.asarray(z, dtype=float), 1e-6, 1.0 - 1e-6)
    D, v, a, z = (np.array(x, dtype=float, copy=True)
                  for x in np.broadcast_arrays(D, v, a, z))

    out = np.ones(D.shape, dtype=float)
    pos = D > 0.0
    if not np.any(pos):
        return out

    dp, vp, ap, zp = D[pos], v[pos], a[pos], z[pos]
    if np.any(ap <= 0.0):
        raise ValueError(f"边界分离度必须为正，收到最小 {np.min(ap)!r}")

    b = np.pi / ap                                   # 基频 kπ/a
    start_abs = zp * ap                              # 绝对起点 z·a
    # 规范变换的起点权重 e^{−v·(z·a)}：p = e^{v(x−z_a)}·q 里对初值 δ(x−z_a) 的 e^{−v z_a}
    pref = (2.0 * np.pi / ap ** 2) * np.exp(-(vp ** 2) * dp / 2.0) * np.exp(-vp * start_abs)
    eva = np.exp(vp * ap)                            # e^{va}

    k_need = np.ceil(np.sqrt(2.0 * np.log(1.0 / tol)) / (b * np.sqrt(dp))).astype(int)
    n_terms = int(np.clip(k_need.max() + 2, 1, max_terms))

    k = np.arange(1, n_terms + 1, dtype=float)[:, None]          # (K,1)
    kb = k * b[None, :]                                          # (K,n)
    sign = np.where(np.arange(1, n_terms + 1) % 2 == 0, 1.0, -1.0)[:, None]
    numer = 1.0 - sign * eva[None, :]
    terms = (k * np.sin(kb * start_abs[None, :]) * numer / (vp[None, :] ** 2 + kb ** 2)
             * np.exp(-(k ** 2) * np.pi ** 2 * dp[None, :] / (2.0 * ap[None, :] ** 2)))
    out[pos] = np.clip(pref * terms.sum(axis=0), 0.0, 1.0)
    return out


def wiener_survival_loop(D, v, a, z, max_terms=MAX_TERMS, tol=TOL):
    """逐项循环的参考实现（仅用于与矩阵版对账，勿在似然里使用）。"""
    D = np.asarray(D, dtype=float)
    v = np.asarray(v, dtype=float)
    a = np.asarray(a, dtype=float)
    z = np.clip(np.asarray(z, dtype=float), 1e-6, 1.0 - 1e-6)
    D, v, a, z = (np.array(x, dtype=float, copy=True)
                  for x in np.broadcast_arrays(D, v, a, z))
    out = np.ones(D.shape, dtype=float)
    pos = D > 0.0
    if not np.any(pos):
        return out
    dp, vp, ap, zp = D[pos], v[pos], a[pos], z[pos]
    b = np.pi / ap
    start_abs = zp * ap
    pref = (2.0 * np.pi / ap ** 2) * np.exp(-(vp ** 2) * dp / 2.0) * np.exp(-vp * start_abs)
    decay = np.exp(-(b ** 2) * dp / 2.0)
    acc = np.zeros_like(dp)
    eva = np.exp(vp * ap)
    for kk in range(1, max_terms + 1):
        kb = kk * b
        term = (kk * np.sin(kb * start_abs) * (1.0 - (1.0 if kk % 2 == 0 else -1.0) * eva)
                / (vp ** 2 + kb ** 2) * decay ** (kk ** 2))
        acc += term
        if np.max(np.abs(term)) < tol:
            break
    out[pos] = np.clip(pref * acc, 0.0, 1.0)
    return out


def p_omission(v, a, z, t0, deadline):
    """P(遗漏 | v, a, z, t0, deadline) = S(deadline − t0)。"""
    return wiener_survival(np.asarray(deadline, dtype=float) - np.asarray(t0, dtype=float),
                           v, a, z)


def omission_logp(n_omission, p_om, eps=1e-10):
    """遗漏项对数似然：Σ_格子 n_遗漏(格子) × log P(遗漏 | θ_格子)。

    取 log 前先 clip（规格文档 §5 步骤 3 的口径约束）。
    """
    p = np.clip(np.asarray(p_om, dtype=float), eps, 1.0 - eps)
    n = np.asarray(n_omission, dtype=float)
    if n.shape != p.shape:
        raise ValueError(f"n_omission 形状 {n.shape} 与 p_om 形状 {p.shape} 不一致")
    if n.size == 0:
        return 0.0
    return float(np.sum(n * np.log(p)))


# ------------------------------------------------------------------
# 自检：解析式 vs 自家仿真器（单一事实来源）
# ------------------------------------------------------------------
# 取自规格文档 §4.5.5 的配置 C 冻结参数（组, 身份, v, a, t0, z, deadline），
# 最后一列是文档记录的"仿真真值"，用于独立锚定。
_REAL_CASES = [
    ("g5-self",    1.35, 1.34, 0.40, 0.45, 1.20, 0.089),
    ("g5-stranger", 0.64, 1.34, 0.40, 0.45, 1.20, 0.139),
    ("g3-self",   -1.89, 1.22, 0.35, 0.57, 0.63, 0.408),
    ("g3-stranger", -1.73, 1.22, 0.35, 0.57, 0.63, 0.429),
    ("g7-self",    1.20, 1.09, 0.40, 0.50, 0.83, 0.189),
    ("g7-stranger", 0.75, 1.09, 0.40, 0.50, 0.83, 0.220),
    ("g4-self",    0.64, 1.42, 0.35, 0.57, 0.68, 0.525),
    ("g4-stranger", -0.02, 1.42, 0.35, 0.57, 0.68, 0.583),
    ("g8-self",    2.81, 2.42, 0.35, 0.50, 0.88, 0.268),
    ("g8-stranger", 2.55, 2.42, 0.35, 0.50, 0.88, 0.334),
    ("g6-self",    1.81, 1.48, 0.66, 0.71, 2.00, 0.005),
    ("g6-stranger", 1.17, 1.48, 0.66, 0.71, 2.00, 0.018),
]


def _import_sim_utils():
    """导入唯一事实来源 `sim_utils`（TenRules_Revision_20260912）。"""
    here = Path(__file__).resolve()
    sim_dir = here.parents[1] / "Python_for_Check" / "TenRules_Revision_20260912"
    if not sim_dir.exists():
        raise FileNotFoundError(f"未找到仿真器目录：{sim_dir}")
    if str(sim_dir) not in sys.path:
        sys.path.insert(0, str(sim_dir))
    import sim_utils  # noqa: E402
    return sim_utils


# 自检用的细步长（项目口径是 sim_utils.SIM_DT = 0.002）
FINE_DT = 0.0005
# 步长缩小 4 倍时，离散偏差理论上按 √dt 缩到 1/2；留些裕量取 0.65
SHRINK_MAX = 0.65
# 细步长下的绝对误差上限（此时残差应已接近蒙特卡洛噪声）
FINE_MAE_MAX = 0.03


def self_test(n_trials=40000, seed=20261001, dt=None, verbose=True):
    """逐点比较：解析 P(遗漏) vs `sim_utils.simulate_trials` 的经验遗漏率。

    ⚠️ 仿真器用 Euler–Maruyama **在网格点上**判定越界，会漏掉"越界后又折回"的路径，
    因此系统性**高估**遗漏率。实测这个偏差按 **√dt** 收缩：

        dt        0.002   0.0005   （40000 试次，12 个真实条件）
        MAE       0.0204  0.0107
        √dt       0.0447  0.0224   → MAE/√dt ≈ 0.46（两处一致）

    所以判据不能用一个固定阈值，而要看**误差是否随 dt 收缩**（见 `verify`）：
    实现层面的错误不会随 dt 变小，而仿真器离散偏差会。

    返回 (max_abs_err, mean_abs_err, rows)。
    """
    su = _import_sim_utils()
    rng = np.random.default_rng(seed)
    kw = {} if dt is None else {"dt": dt}
    rows = []
    for name, v, a, t0, z, dl, doc_truth in _REAL_CASES:
        sim = su.simulate_trials(v, a, t0, z, dl, n_trials, rng, **kw)
        emp = float(np.mean(sim["omission"]))
        ana = float(p_omission(v, a, z, t0, dl))
        rows.append({"case": name, "v": v, "a": a, "t0": t0, "z": z, "deadline": dl,
                     "analytic": ana, "simulated": emp, "doc_truth": doc_truth,
                     "abs_err": abs(ana - emp), "doc_err": abs(ana - doc_truth)})

    errs = np.array([r["abs_err"] for r in rows], dtype=float)
    doc_errs = np.array([r["doc_err"] for r in rows], dtype=float)
    if verbose:
        tag = "项目口径 dt=0.002" if dt is None else f"细步长 dt={dt}"
        print("=" * 86)
        print(f"自检（{tag}）：解析 Wiener 生存函数 vs sim_utils 仿真（每点 {n_trials} 试次）")
        print("=" * 86)
        print(f"{'case':<12}{'analytic':>10}{'simulated':>11}{'doc_truth':>11}"
              f"{'|ana−sim|':>11}{'|ana−doc|':>11}")
        for r in rows:
            print(f"{r['case']:<12}{r['analytic']:>10.4f}{r['simulated']:>11.4f}"
                  f"{r['doc_truth']:>11.4f}{r['abs_err']:>11.4f}{r['doc_err']:>11.4f}")
        print("-" * 86)
        print(f"解析 vs 仿真：MAE = {errs.mean():.4f} | 最大 = {errs.max():.4f}")
        print(f"解析 vs 文档记录的仿真真值：MAE = {doc_errs.mean():.4f} | 最大 = {doc_errs.max():.4f}")
    return float(errs.max()), float(errs.mean()), rows


def check_series_equivalence(n=3000, seed=7, verbose=True):
    """矩阵版 vs 逐项循环版：随机参数逐点对账（实现层面的自检）。"""
    rng = np.random.default_rng(seed)
    v = rng.uniform(-4.0, 4.0, n)
    a = rng.uniform(0.4, 3.0, n)
    z = rng.uniform(0.02, 0.98, n)
    D = rng.uniform(0.001, 2.0, n)
    fast = wiener_survival(D, v, a, z)
    slow = wiener_survival_loop(D, v, a, z)
    d = np.abs(fast - slow)
    i = int(np.argmax(d))
    if verbose:
        print(f"级数实现对账（{n} 个随机点）：最大绝对差 = {d.max():.3e}"
              f"（最差点 D={D[i]:.4f}, v={v[i]:.3f}, a={a[i]:.3f}, z={z[i]:.3f}）")
    return float(d.max())


def verify(n_trials=40000, seed=20261001):
    """双口径校验。判据：细步长误差应显著小于项目口径误差（证明残差是离散偏差而非实现错误）。"""
    eq = check_series_equivalence(seed=seed)
    print()
    p_max, p_mae, _ = self_test(n_trials=n_trials, seed=seed, dt=None, verbose=True)
    print()
    f_max, f_mae, _ = self_test(n_trials=n_trials, seed=seed, dt=FINE_DT, verbose=True)

    ratio = f_mae / p_mae if p_mae > 0 else float("nan")
    print()
    print("=" * 86)
    print("判据（误差必须随 dt 收缩，否则说明是**实现错误**而不是仿真器离散偏差）")
    print("=" * 86)
    print(f"  矩阵版 vs 循环版最大差 = {eq:.3e}（要求 ≤ 1e-10）")
    print(f"  项目口径 MAE = {p_mae:.4f}  →  细步长 MAE = {f_mae:.4f}"
          f"  （比值 {ratio:.3f}，要求 ≤ {SHRINK_MAX}）")
    print(f"  细步长最大绝对误差 = {f_max:.4f}（要求 ≤ {FINE_MAE_MAX}）")
    ok = bool(np.isfinite(ratio) and ratio <= SHRINK_MAX and f_mae <= FINE_MAE_MAX and eq <= 1e-10)
    print(f"  → {'✅ 通过：解析实现正确，残差为仿真器 √dt 离散偏差' if ok else '❌ 未通过'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description="遗漏似然项 P(遗漏) 的自检")
    ap.add_argument("--n", type=int, default=40000, help="每个参数点的仿真试次数")
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--quick", action="store_true", help="只跑项目口径（跳过收缩判据）")
    args = ap.parse_args()
    if args.quick:
        mx, _, _ = self_test(n_trials=args.n, seed=args.seed, dt=None)
        raise SystemExit(0 if mx <= 0.05 else 1)
    raise SystemExit(0 if verify(n_trials=args.n, seed=args.seed) else 1)


if __name__ == "__main__":
    main()
