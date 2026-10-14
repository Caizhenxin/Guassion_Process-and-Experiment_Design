"""检查：被试层真值的**边界概率堆**有多大，以及 `mode="truncate"` 能不能消掉它。

动机（README §9 第 10 项）
--------------------------
`simulate.draw_subject_params` 的默认实现是 `np.clip` —— 这是 **clipping 而不是
truncation**：抽到 `PARAM_BOUNDS` 之外的被试真值被**压到界值本身**，于是边界上
有一个概率堆。后果有二：

1. 真值恰好等于下界的被试（P=0 组的 `d_ref`），**拟合落在界上是答对了**，却会被
   「贴界」判据误报为可疑（§8.12 就是这个坑）。
2. 被试层真值的**边际 SD 被压缩**，于是 `SUBJECT_SD` 不再是实际的被试间 SD ——
   而组间回归的抽样 SD 正是拿它当参照的。

本脚本做四件事（全部秒级，不跑似然、不模拟反应）：
  A. 解析式地给出每个 (参数化, P 水平) 下每个随机效应参数**被压到界上**的概率；
  B. 大样本蒙特卡洛（默认 N=50000/水平）把两种模式的**堆占率 / 均值 / 边际 SD** 并排；
  C. 用**与 `recover_group.py` 完全相同的种子**重放被试层真值，列出贴界个体，
     并给出「组层 `d_ref` 均值」两种模式的差（这是真正会进 `fit_between` 的量）；
  D. 自检：`mode="clip"` 必须与手写的 `np.clip` 老实现**逐位相同**（保证历史日志可复现）；
     `mode="truncate"` 必须**堆占率为 0**、越界数为 0，且边际 SD 与解析截断公式吻合。

用法：``python _scratch/check_bounds_trunc.py [n_big] [n_replay]``
输出：``_scratch/check_bounds_trunc_u8.txt``
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

_HERE = Path(__file__).resolve().parent
_DDM = _HERE.parent
sys.path.insert(0, str(_DDM))

from mapping import PARAM_BOUNDS, WITHIN_FREE, WITHIN_FREE_LIN  # noqa: E402
from recover_group import (BASE_SEED, GROUP_TRUTHS, N_REP, P_COMMON_REF,  # noqa: E402
                           P_LEVELS, T_LEVELS, W_LEVELS, make_subject_truth)
from simulate import (SUBJECT_MODE_CLIP, SUBJECT_MODE_TRUNCATE, SUBJECT_SD,  # noqa: E402
                      draw_subject_params)


def _clip_prob(mu: float, sigma: float, lo: float, hi: float) -> float:
    """`np.clip(N(mu, sigma), lo, hi)` 实际被压到界上的概率。"""
    return float(norm.cdf((lo - mu) / sigma) + 1.0 - norm.cdf((hi - mu) / sigma))


def _trunc_sd(mu: float, sigma: float, lo: float, hi: float) -> float:
    """N(mu, sigma) 截断在 [lo, hi] 上的解析 SD。"""
    a, b = (lo - mu) / sigma, (hi - mu) / sigma
    z = float(norm.cdf(b) - norm.cdf(a))
    if z <= 0:
        return 0.0
    pa, pb = float(norm.pdf(a)), float(norm.pdf(b))
    mean = mu + sigma * (pa - pb) / z
    var = sigma ** 2 * (1.0 + (a * pa - b * pb) / z - ((pa - pb) / z) ** 2)
    _ = mean
    return float(np.sqrt(max(var, 0.0)))


def _group_base(group_truth, P: float):
    """`make_subject_truth` 里构造的**组层**参数（还没抽被试噪声）。"""
    import mapping
    reg = float(mapping.f_P(P, group_truth.tau_P)
                - mapping.f_P(P_COMMON_REF, group_truth.tau_P))
    return group_truth.replace(
        P_ref=float(P),
        d_ref=group_truth.d_ref + group_truth.beta_P * reg,
        beta_S=group_truth.beta_S + group_truth.beta_SP * reg,
    )


def part_a(shape: str, names: list[str]) -> None:
    group_truth = GROUP_TRUTHS[shape]
    varying = [n for n in names if n in SUBJECT_SD and SUBJECT_SD[n] > 0]
    print("=" * 104)
    print(f"A. 解析式：clipping 概率与边际 SD 压缩（参数化 {shape!r}，随机效应参数 {varying}）")
    print("=" * 104)
    print(f"  {'P':>6s} {'参数':>9s} {'组层真值':>10s} {'SD设定':>8s} {'下界':>7s} {'上界':>7s} "
          f"{'clipping%':>10s} {'截断SD':>9s} {'压缩比':>7s}")
    worst = (0.0, None)
    for P in P_LEVELS:
        base = _group_base(group_truth, P)
        for n in varying:
            lo, hi = PARAM_BOUNDS[n]
            mu, s = float(getattr(base, n)), SUBJECT_SD[n]
            pc = _clip_prob(mu, s, lo, hi)
            st = _trunc_sd(mu, s, lo, hi)
            ratio = st / s
            if pc > worst[0]:
                worst = (pc, (P, n))
            mark = "  ⚠️" if pc > 0.005 else ""
            print(f"  {P:6.0f} {n:>9s} {mu:10.4f} {s:8.4f} {lo:7.2f} {hi:7.2f} "
                  f"{100.0 * pc:9.2f}% {st:9.4f} {ratio:7.4f}{mark}")
    if worst[1] is not None:
        P, n = worst[1]
        print(f"\n  ⇒ 堆占率最高的是 P={P:g} 的 {n!r}（{100.0 * worst[0]:.2f}%）。")
    print("\n  ⚠️ clipping 不改变「SD设定」，它把界外的质量**搬到端点**；"
          "截断正态则把质量**重铺在界内**，\n     代价是边际 SD 被压缩（「压缩比」列 < 1，即 `SUBJECT_SD` 不再是实际的被试间 SD）。\n")


def part_b(shape: str, names: list[str], n_big: int, seed: int) -> None:
    group_truth = GROUP_TRUTHS[shape]
    varying = [n for n in names if n in SUBJECT_SD and SUBJECT_SD[n] > 0]
    print("=" * 104)
    print(f"B. 大样本蒙特卡洛（每水平 N={n_big}）：「压到界上的比例」与边际 SD")
    print("=" * 104)
    print(f"  {'P':>6s} {'参数':>9s} {'模式':>9s} {'堆占率':>9s} {'均值':>10s} {'SD':>10s} "
          f"{'最小':>10s} {'越界':>7s}")
    for P in P_LEVELS:
        base = _group_base(group_truth, P)
        for n in varying:
            lo, hi = PARAM_BOUNDS[n]
            for mode in (SUBJECT_MODE_CLIP, SUBJECT_MODE_TRUNCATE):
                rng = np.random.default_rng(seed + int(P) * 17 + varying.index(n) * 101)
                vals = np.array([
                    float(getattr(draw_subject_params(base, rng, mode=mode), n))
                    for _ in range(n_big)], dtype=float)
                pile = float(np.mean((vals <= lo) | (vals >= hi)))
                n_out = int(np.sum((vals < lo) | (vals > hi)))
                print(f"  {P:6.0f} {n:>9s} {mode:>9s} {100.0 * pile:8.2f}% {vals.mean():10.4f} "
                      f"{vals.std(ddof=1):10.4f} {vals.min():10.4f} {n_out:7d}")
    print()


def part_c(shape: str, names: list[str], n_sub: int) -> dict:
    """用真实种子重放被试层真值；给出组层 d_ref 均值与贴界个体。"""
    group_truth = GROUP_TRUTHS[shape]
    print("=" * 104)
    print(f"C. 用 `recover_group.py` 的真实种子重放（每组 {n_sub} 人 = {len(P_LEVELS) * n_sub} 人）")
    print("=" * 104)
    out: dict[str, dict] = {}
    for mode in (SUBJECT_MODE_CLIP, SUBJECT_MODE_TRUNCATE):
        per_P_d: dict[float, list[float]] = {p: [] for p in P_LEVELS}
        on_bound = []
        for P in P_LEVELS:
            for s in range(n_sub):
                rng = np.random.default_rng(BASE_SEED + int(P) * 1000 + s)
                subj, _reg = make_subject_truth(group_truth, P, P_COMMON_REF, rng, mode=mode)
                per_P_d[P].append(float(subj.d_ref))
                for n in names:
                    lo, hi = PARAM_BOUNDS[n]
                    v = float(getattr(subj, n))
                    if v <= lo or v >= hi:
                        on_bound.append((P, s, n, v, lo if v <= lo else hi))
        out[mode] = {"per_P_d": per_P_d, "on_bound": on_bound}
        print(f"\n  模式 {mode!r}")
        print(f"    {'P':>6s} {'组层d_ref':>10s} {'被试层均值':>11s} {'被试层SD':>9s} {'最小':>10s}")
        for P in P_LEVELS:
            v = np.array(per_P_d[P], float)
            print(f"    {P:6.0f} {float(_group_base(group_truth, P).d_ref):10.4f} "
                  f"{v.mean():11.4f} {v.std(ddof=1):9.4f} {v.min():10.4f}")
        print(f"    真值贴界（≤下界或≥上界）的个体数：{len(on_bound)}")
        for P, s, n, v, b in on_bound:
            print(f"      P={P:6.0f} subj={s:3d} {n:>9s} 真值={v:9.4f} 界={b:7.2f}")
    print()
    return out


def part_d(names: list[str], res: dict) -> None:
    print("=" * 104)
    print("D. 自检")
    print("=" * 104)
    # D1: mode="clip" 与手写老实现逐位相同
    shape = "exp"
    group_truth = GROUP_TRUTHS[shape]
    base = _group_base(group_truth, 0.0)
    ok = True
    for trial in range(50):
        seed = 12345 + trial
        r1 = np.random.default_rng(seed)
        new = draw_subject_params(base, r1, mode=SUBJECT_MODE_CLIP)
        r2 = np.random.default_rng(seed)
        kw = {}
        for k, s in SUBJECT_SD.items():
            if s <= 0:
                continue
            lo, hi = PARAM_BOUNDS[k]
            kw[k] = float(np.clip(getattr(base, k) + r2.normal(0.0, s), lo, hi))
        old = base.replace(**kw)
        for n in SUBJECT_SD:
            if float(getattr(new, n)) != float(getattr(old, n)):
                ok = False
    print(f"  D1 `mode='clip'` 与手写 np.clip 老实现逐位相同（50 个种子）："
          f"{'✅ 通过' if ok else '❌ 不一致'}")
    print("     ⇒ 默认模式改回 clip 时，`_scratch/` 里的历史日志仍可逐位复现。")

    # D2: truncate 无堆、无越界
    bad = []
    for mode in (SUBJECT_MODE_TRUNCATE,):
        for P in P_LEVELS:
            b = _group_base(group_truth, P)
            rng = np.random.default_rng(777)
            for _ in range(20000):
                p = draw_subject_params(b, rng, mode=mode)
                for n in names:
                    lo, hi = PARAM_BOUNDS[n]
                    v = float(getattr(p, n))
                    if v <= lo or v >= hi:
                        bad.append((P, n, v))
    print(f"  D2 `mode='truncate'` 在 4 个 P 水平 × 20000 次抽样的堆占数：{len(bad)}"
          f"  {'✅ 通过' if not bad else '❌ 仍有堆'}")
    if bad:
        for P, n, v in bad[:8]:
            print(f"      P={P:6.0f} {n:>9s} {v:.6f}")

    # D3: truncate 的边际 SD 与解析公式吻合
    print("  D3 `mode='truncate'` 的边际 SD vs 解析截断公式（P=0，N=20000）：")
    b = _group_base(group_truth, 0.0)
    for n in ("d_ref", "beta_S", "a_ref", "t0"):
        if n not in SUBJECT_SD:
            continue
        lo, hi = PARAM_BOUNDS[n]
        mu, s = float(getattr(b, n)), SUBJECT_SD[n]
        rng = np.random.default_rng(4242)
        v = np.array([float(getattr(draw_subject_params(b, rng, mode=SUBJECT_MODE_TRUNCATE), n))
                      for _ in range(20000)], dtype=float)
        emp, ana = float(v.std(ddof=1)), _trunc_sd(mu, s, lo, hi)
        flag = "✅" if abs(emp - ana) < 0.01 * max(ana, 1e-9) else "⚠️"
        print(f"      {n:>9s} 实测 {emp:.4f} / 解析 {ana:.4f} / 设定 {s:.4f}  {flag}")

    # D4: 组层 d_ref 均值两种模式的差
    cl = res[SUBJECT_MODE_CLIP]["per_P_d"]
    tr = res[SUBJECT_MODE_TRUNCATE]["per_P_d"]
    print("  D4 组层 `d_ref` 均值（进 `fit_between` 的量）两模式之差：")
    for P in P_LEVELS:
        a, b_ = float(np.mean(cl[P])), float(np.mean(tr[P]))
        print(f"      P={P:6.0f}  clip {a:.4f}  truncate {b_:.4f}  Δ={b_ - a:+.4f}")
    print()


def main() -> None:
    n_big = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    n_sub = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    print(f"\n设计层次：T={T_LEVELS}  W={W_LEVELS}  N_REP={N_REP}")
    print(f"P 水平={P_LEVELS}  P_COMMON_REF={P_COMMON_REF}  BASE_SEED={BASE_SEED}")
    print(f"SUBJECT_SD={SUBJECT_SD}\n")
    for shape in ("exp", "lin"):
        names = list(WITHIN_FREE) if shape == "exp" else list(WITHIN_FREE_LIN)
        part_a(shape, names)
        part_b(shape, names, n_big, seed=90210)
        res = part_c(shape, names, n_sub)
        part_d(names, res)


if __name__ == "__main__":
    main()
