# -*- coding: utf-8 -*-
"""check_flux_smallt.py —— `wfpt.flux` 小 t 分支（镜像级数）的自验证

为什么要这个脚本
----------------
2026-10-14 之前 `1_Code/DDM_Core/wfpt.py` 的 `flux` 只有**一条**正弦级数分支。
t→0 时级数各项幅值 O(k)、而真值指数级小 ⇒ 真值一旦落到相消地板（≈ kmax·eps）
以下，返回值就是**符号随机**的双精度噪声（实测 −7.77e−14 / +6.01e−16 /
−8.23e−15），然后被 `likelihood.per_trial_loglik` 的 `np.any(f <= 0)` 守卫
放大成「**整份**数据判 None」。详见 `1_Code/DDM_Core/README.md` §8.24 ④。

修法是给同一个特征函数展开补**第二条对偶级数**（镜像/反射级数），按 t 选分支。

本脚本的判据设计
----------------
**不是**"两条分支互相对一眼"——那只能证明它们一致，不能证明它们都对。
真正独立的判据是 V3/V4：**对 t 积分必须等于 `wfpt.p_upper` 的闭式吸收概率**，
这条恒等式的推导路径（Fokker–Planck 吸收概率）与密度级数完全不同。

V1 两条级数在交叉窗口内逐点吻合（交叉点取"首项衰减率相等"处，两支都准）
V2 `flux` 在交叉点两侧连续（派发器没把两支接错、没漏掉分组）
V3 镜像级数的**解析积分恒等式** == `wfpt.p_upper`（紧容差，纯代数，独立路径）
V4 **数值积分** `∫ flux dt` == `wfpt.p_upper`（过派发器，容差松一档）
V5 小 t 一侧确实路由到镜像分支，且**旧实现的误差在那里多大**（如实报出）
V6 无回归：在大 t 一侧 `flux` 与原来的正弦级数**逐位相同**

用法：``python _scratch/check_flux_smallt.py``（退出码 0 = 全过）
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from scipy.integrate import quad

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from wfpt import flux, p_upper, _flux_series, _flux_dual, _k_max  # noqa: E402

FAILS = []


def check(name, ok, detail):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n         {detail}")
    if not ok:
        FAILS.append(name)


def note(msg):
    print(f"[NOTE] {msg}")


# 参数网格：a / z 比例 / v。d = a − z 是"到该边界的距离"。
A_LIST = (1.0, 2.0, 3.0)
FRAC_LIST = (0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9)
V_LIST = (-2.0, -0.5, 0.0, 0.5, 2.0)


def cross_point(a, d):
    """正弦级数与镜像级数首项衰减率相等处：π²t/(2a²) = d_min²/(2t)。"""
    d_min = min(d, 2.0 * a - d)
    return a * d_min / np.pi


def dual_integral(d, v, a, n_max=600):
    """e^{vd}·Σ_n sgn(d+2na)·e^{−v|d+2na|}（v > 0 时逐项积分合法）。"""
    s = 0.0
    for n in range(-n_max, n_max + 1):
        img = d + 2.0 * n * a
        s += np.sign(img) * np.exp(-v * abs(img))
    return np.exp(v * d) * s


# ---------------------------------------------------------------- V1
def v1():
    worst, worst_at, n_pts = 0.0, None, 0
    for a in A_LIST:
        for frac in FRAC_LIST:
            z = frac * a
            d = a - z
            cross = cross_point(a, d)
            # 两支都准的窗口：交叉点两侧各一个数量级
            ts = cross * np.exp(np.linspace(np.log(0.3), np.log(3.0), 25))
            for v in V_LIST:
                s = np.asarray(_flux_series(d, v, a, ts), dtype=float)
                du = np.asarray(_flux_dual(d, v, a, ts), dtype=float)
                rel = np.abs(s - du) / np.maximum(np.abs(s), 1e-300)
                n_pts += ts.size
                i = int(np.argmax(rel))
                if rel[i] > worst:
                    worst, worst_at = float(rel[i]), (a, z, v, float(ts[i]))
    check("V1 两条级数在交叉窗口内吻合",
          worst < 1e-9,
          f"最差相对误差 {worst:.3e}（{n_pts} 点，{len(A_LIST)}×{len(FRAC_LIST)}×{len(V_LIST)} 组）；"
          f"最差点 a={worst_at[0]} z={worst_at[1]} v={worst_at[2]} t={worst_at[3]:.6g}")


# ---------------------------------------------------------------- V2
def v2():
    worst, worst_at = 0.0, None
    for a in A_LIST:
        for frac in FRAC_LIST:
            z = frac * a
            d = a - z
            cross = cross_point(a, d)
            lo = float(flux(d, 0.0, a, cross * (1.0 - 1e-9)))
            hi = float(flux(d, 0.0, a, cross * (1.0 + 1e-9)))
            rel = abs(hi - lo) / max(abs(hi), 1e-300)
            if rel > worst:
                worst, worst_at = rel, (a, z, lo, hi)
    check("V2 flux 在交叉点两侧连续",
          worst < 1e-6,
          f"最差相对跳变 {worst:.3e}（a={worst_at[0]} z={worst_at[1]}；"
          f"左 {worst_at[2]:.12g} → 右 {worst_at[3]:.12g}）")


# ---------------------------------------------------------------- V3
def v3():
    worst, worst_at = 0.0, None
    for a in (1.0, 2.0, 3.0):
        for frac in (0.1, 0.25, 0.5, 0.75, 0.9):
            z = frac * a
            d = a - z
            for v in (0.25, 0.5, 1.0, 2.0):
                got = dual_integral(d, v, a)
                want = float(p_upper(v, a, z))
                rel = abs(got - want) / max(abs(want), 1e-300)
                if rel > worst:
                    worst, worst_at = rel, (a, z, v, got, want)
    # v→0 的特殊情形：∫ = 1 − d/a = z/a（与级数形式的 Dirichlet 求和一致）
    a = 2.0
    d = 0.5
    s0 = sum(np.sin(k * np.pi * d / a) / k for k in range(1, 400001))
    limit = 1.0 - (np.pi * d / a) / np.pi    # (π/2)(1 − d/a) 归一化后 = 1 − d/a
    check("V3 镜像级数的解析积分 == p_upper（闭式吸收概率）",
          worst < 1e-12,
          f"最差相对误差 {worst:.3e}（a={worst_at[0]} z={worst_at[1]} v={worst_at[2]}；"
          f"恒等式 {worst_at[3]:.15g} vs p_upper {worst_at[4]:.15g}）；"
          f"另 v→0 的 Dirichlet 求和 Σsin(kπd/a)/k = {s0:.12f} ⇒ 1−d/a = {limit:.12f}")
    note(f"v→0 检验：Σ_{{k≥1}} sin(kπd/a)/k = {s0:.12f}，理论 (π/2)(1−d/a) = "
         f"{(np.pi / 2) * (1 - d / a):.12f}")


# ---------------------------------------------------------------- V4
def v4():
    worst, worst_at = 0.0, None
    for a in (1.0, 2.0):
        for frac in (0.2, 0.5, 0.8):
            z = frac * a
            d = a - z
            for v in (-2.0, -0.5, 0.5, 2.0):
                # t→0 端被 e^{−d²/(2t)} 压得极平坦，从 1e-12 起积分足够；
                # t→∞ 端被 e^{−v²t/2} 压掉（v=0 时由 1/t^{3/2} 压掉）。
                got, err = quad(lambda t: float(flux(d, v, a, t)), 1e-12, 60.0,
                                limit=400, epsabs=1e-13, epsrel=1e-12)
                want = float(p_upper(v, a, z))
                rel = abs(got - want) / max(abs(want), 1e-300)
                if rel > worst:
                    worst, worst_at = rel, (a, z, v, got, want, err)
    check("V4 数值积分 ∫flux dt == p_upper（过派发器）",
          worst < 1e-6,
          f"最差相对误差 {worst:.3e}（a={worst_at[0]} z={worst_at[1]} v={worst_at[2]}；"
          f"∫ = {worst_at[3]:.12g} vs p_upper = {worst_at[4]:.12g}，quad 自报 err {worst_at[5]:.1e}）")


# ---------------------------------------------------------------- V5
def v5():
    """小 t 一侧：确认路由到镜像分支，并如实报出**旧实现**在那里的误差。"""
    route_bad = 0
    old_worst, old_at = 0.0, None
    n_small, n_old_wrong, n_old_nonpos = 0, 0, 0
    for a in (1.0, 2.0, 3.0):
        for frac in (0.25, 0.5, 0.75):
            z = frac * a
            d = a - z
            cross = cross_point(a, d)
            # 小 t 侧：从交叉点往下两个数量级（再小会被 e^{−d²/(2t)} 下溢成 0）
            ts = cross * np.exp(np.linspace(np.log(1e-2), np.log(0.95), 60))
            for v in (0.5, 2.0):
                du = np.asarray(_flux_dual(d, v, a, ts), dtype=float)
                fu = np.asarray(flux(d, v, a, ts), dtype=float)
                se = np.asarray(_flux_series(d, v, a, ts), dtype=float)
                keep = du > 0.0            # 只看双精度还表示得出来的范围
                n_small += int(keep.sum())
                # (a) 派发器必须逐位走镜像分支
                if not np.array_equal(fu[keep], du[keep]):
                    route_bad += 1
                # (b) 旧实现（纯正弦级数）在同一批点上的误差
                rel = np.abs(se[keep] - du[keep]) / du[keep]
                n_old_wrong += int((rel > 1e-3).sum())
                n_old_nonpos += int((se[keep] <= 0.0).sum())
                if rel.size and float(rel.max()) > old_worst:
                    i = int(np.argmax(rel))
                    old_worst = float(rel[i])
                    old_at = (a, z, v, float(ts[keep][i]), float(se[keep][i]), float(du[keep][i]))
    k_at = _k_max(float(0.02), 2.0, 1e-15)
    check("V5 小 t 一侧路由到镜像分支，且旧实现在那里确实错",
          route_bad == 0 and old_worst > 1e-3,
          f"小 t 侧可比点 {n_small} 个：`flux` 与镜像级数逐位相同的组数 = {route_bad} 个不符；"
          f"旧实现相对误差 >1e-3 的点 {n_old_wrong} 个、≤0 的点 {n_old_nonpos} 个。\n"
          f"         旧实现最差：a={old_at[0]} z={old_at[1]} v={old_at[2]} t={old_at[3]:.6g} ⇒ "
          f"正弦级数 {old_at[4]:.6g} vs 镜像 {old_at[5]:.6g}（相对 {old_worst:.2e}）\n"
          f"         参考：t=0.02、a=2 时 k_max = {k_at} ⇒ 相消地板 ≈ {k_at * np.finfo(float).eps:.2e}")


# ---------------------------------------------------------------- V6
def v6():
    bad, n_pts = 0, 0
    for a in A_LIST:
        for frac in FRAC_LIST:
            z = frac * a
            d = a - z
            cross = cross_point(a, d)
            ts = cross * np.exp(np.linspace(np.log(3.0), np.log(1000.0), 40))
            for v in V_LIST:
                want = np.asarray(_flux_series(d, v, a, ts), dtype=float)
                got = np.asarray(flux(d, v, a, ts), dtype=float)
                n_pts += ts.size
                if not np.array_equal(got, want):
                    bad += 1
    check("V6 大 t 一侧与原来的正弦级数逐位相同（无回归）",
          bad == 0,
          f"{n_pts} 点、{len(A_LIST) * len(FRAC_LIST) * len(V_LIST)} 组，"
          f"与旧实现不一致的组数 = {bad}")


def main():
    print("=" * 78)
    print("check_flux_smallt.py —— wfpt.flux 小 t 分支（镜像级数）自验证")
    print("=" * 78)
    v1()
    v2()
    v3()
    v4()
    v5()
    v6()
    print("-" * 78)
    if FAILS:
        print(f"❌ {len(FAILS)} 项未通过：{', '.join(FAILS)}")
        return 1
    print("✅ 全部通过（6 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
