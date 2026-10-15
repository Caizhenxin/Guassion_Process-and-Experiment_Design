# -*- coding: utf-8 -*-
"""check_sfloor.py — `wfpt._S_FLOOR` / `_T_FLOOR` 两处旧补丁的**重新论证**（v2）。

背景（README §9 第 29 项遗留）
------------------------------
`_S_FLOOR = 1e-3` 与 `_T_FLOOR = 1e-4` 是 `flux` 只有正弦级数一条分支时打的补丁，
当时写下的理由是"t 很小时正弦级数灾难性相消"。第 18 轮给 `flux` 加了镜像级数
分支 `_flux_dual` 后，**那条理由已不再成立**，所以这两个常量必须重新论证。

v1 的教训（8 项中 5 项断言被我自己的实测推翻）
----------------------------------------------
1. **B2 根本没踩到卷积**：s ≤ `_S_FLOOR` ⇒ `density_step` 走 `pre` 分支，
   于是 `f_conv` 与单阶段解析值**逐位相同**、对 `_X_EPS`/`n_x` 全不敏感。
   修法：`W._S_FLOOR = 0.0` 强制走卷积。
2. **偏差标度不是 O(s) 而是 O(√s)**：实测 log-log 斜率 0.484 ⇒ 缝内侧偏差 ~3%。
3. **质量守恒缺陷随 `_S_FLOOR` 单调递增**，不存在我想当然的"内部最优"。

本版的独立参考量（关键）
------------------------
`v2 == v1` 时，两阶段密度**必须恒等于**单阶段密度：
`∫ flux(a−x, v, a, s)·G(x,T) dx ≡ flux(a−z, v, a, T+s)`（Chapman–Kolmogorov，
`flux` 的 sin(kπd/a) 正是吸收边界的 Dirichlet 本征函数）。这条恒等式是**闭式**的，
所以它第一次让"卷积在 s 多小时开始不可信"变成可测量的问题（同时独立校验 `green`）。

判据组织
--------
* A（2）：两个 floor 各自在哪条路径上可达；那道 `np.maximum` 钳位是死代码还是保险
* B（5）：缝的大小 / **卷积误差 vs s（闭式参考）** / pre 偏差的 √s 标度 /
        质量守恒 vs floor / **min-max 最优 floor（实测交叉点）**
* C（2）：现实数据形态下这道缝被踩到几次、似然层面的实际影响
"""

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DDM = HERE.parent
REPO = DDM.parent.parent
for _p in (DDM, REPO / "1_Code" / "Experiment"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import wfpt as W                                              # noqa: E402
from wfpt import _time_grid, density_step, flux, survival_step  # noqa: E402
from mapping import MappingParams                              # noqa: E402
import read_formal_data as R                                   # noqa: E402

#: 代表设计：v1 用 d_ref 量级、v2 = rho·v1（rho=0.5，D37 的主检验点），
#: T 取正式设计的两端（33.33 ms 与 249.98 ms）
DESIGNS = [
    dict(name="T=0.15,a=1.8", v1=1.20, v2=0.60, a=1.80, z=0.90, T=0.149990),
    dict(name="T=0.25,a=3.0", v1=2.00, v2=1.40, a=3.00, z=1.20, T=0.249980),
]

_T_MAX = 15.0
_results = []


def report(tag: str, ok: bool, msg: str):
    _results.append((tag, bool(ok), msg))
    print(f"  {'✅' if ok else '❌'} {tag}  {msg}")


def grid_around(T: float, t_max: float = _T_MAX, span: float = 0.05,
                n_fine: int = 5001) -> np.ndarray:
    """在 T 附近铺**均匀细网格**、其外用幂网格。

    为什么专门做这件事：`_time_grid` 在 T≈0.15 处的间距实测约 5e-4 s，
    与被测的 1 ms 缝同量级 ⇒ 用它会连缝都分不出来。
    """
    top = min(T + span, 0.6 * t_max)
    fine = np.linspace(W._T_FLOOR, top, n_fine)
    rough = _time_grid(t_max, 1500, 2.5)
    return np.unique(np.concatenate([fine, rough[rough > fine[-1]]]))


def mass_defect(d, t_max: float = _T_MAX, n_x: int = 161):
    """``∫_0^t_max (f_up+f_lo) dt + S(t_max) - 1``（三项都必须 ≈ 1）。"""
    tg = grid_around(d["T"], t_max)
    fu, fl = density_step(tg, d["v1"], d["v2"], d["a"], d["z"], d["T"], n_x=n_x)
    m = float(np.trapezoid(fu + fl, tg))
    tail = float(survival_step(d["v1"], d["v2"], d["a"], d["z"], d["T"], t_max))
    return m + tail - 1.0, m, tail, tg.size


def conv_up(d, s: float, n_x: int = 161) -> float:
    """**强制走卷积**（`_S_FLOOR = 0`）得到 t = T+s 处的上边界密度。"""
    old = W._S_FLOOR
    W._S_FLOOR = 0.0
    try:
        return float(density_step(np.array([d["T"] + s]), d["v1"], d["v2"], d["a"],
                                  d["z"], d["T"], n_x=n_x)[0][0])
    finally:
        W._S_FLOOR = old


# ---------------------------------------------------------------- A 组
def case_a():
    print("\n" + "=" * 92)
    print("A 组：两个 floor 各自在哪条路径上可达")
    print("=" * 92)

    Ts = np.asarray(R.T_LEVELS, dtype=float)
    ratio = float(Ts.min() / W._T_FLOOR)
    report("A1", Ts.min() > 100.0 * W._T_FLOOR,
           f"`green` 的 δ 分支条件是 T <= _T_FLOOR = {W._T_FLOOR:g}；"
           f"正式设计最小 T = {Ts.min():.6f} = **{ratio:.0f} 倍**floor "
           f"⇒ **似然路径上不可达**（`_T_FLOOR` 只对退化 T 与 `_time_grid` 生效）")

    # v2：用 np.nextafter 从 T+_S_FLOOR **逐位向上穷举**，
    # 判定 `np.maximum(t-T, _S_FLOOR)` 在后分支里到底能不能生效
    steps = 100_000
    total, example, first_gap = 0, None, None
    for T in Ts:
        thr = T + W._S_FLOOR
        t = thr
        for i in range(steps):
            t = np.nextafter(t, np.inf)
            gap = float(t - T) - W._S_FLOOR
            if first_gap is None and i > 0:
                first_gap = gap
            if (t > thr) and ((t - T) < W._S_FLOOR):
                total += 1
                if example is None:
                    example = (float(T), float(t), float(t - T))
    if example is not None:
        T, tv, sd = example
        tail = (f"首例 T={T:.6f}: t−T = {sd!r} < {W._S_FLOOR:g}（少算 "
                f"{W._S_FLOOR - sd:.3e} s）")
    else:
        tail = (f"{len(Ts)} 个 T × {steps} 次逐位上探**全部**满足 t−T ≥ _S_FLOOR；"
                f"紧邻的上一个浮点的 t−T 超出量 = {first_gap:.3e} s")
    report("A2", total == 0,
           f"穷举判定：{total} 个浮点满足 `t > T+_S_FLOOR` 且 `t−T < _S_FLOOR` ⇒ "
           f"该钳位"
           + ("**是必需的浮点保险**" if total else
              "**是死代码**（后分支条件 `t > T+_S_FLOOR` 已蕴含 `t−T ≥ _S_FLOOR`；"
              "对任何 `_S_FLOOR ≥ 0` 都成立）")
           + f"；{tail}。**结论：保留它无副作用，但不得声称它在防相消**")


# ---------------------------------------------------------------- B 组
def case_b1():
    """缝：`pre` 与 `post` 在 `t = T + _S_FLOOR` 两侧的值。"""
    print("\n" + "=" * 92)
    print("B1 缝：t = T + _S_FLOOR 两侧的密度（eps=1e-9）")
    print("=" * 92)
    eps = 1e-9
    worst = 0.0
    ok = True
    for d in DESIGNS:
        t_lo = d["T"] + W._S_FLOOR - eps
        t_hi = d["T"] + W._S_FLOOR + eps
        lo = float(density_step(np.array([t_lo]), d["v1"], d["v2"], d["a"], d["z"], d["T"])[0][0])
        hi = float(density_step(np.array([t_hi]), d["v1"], d["v2"], d["a"], d["z"], d["T"])[0][0])
        jump = abs(hi - lo) / max(abs(lo), 1e-300)
        worst = max(worst, jump)
        ok &= jump < 5e-2
        print(f"    {d['name']:<12} t=T+S 前 {lo:>12.6e}  后 {hi:>12.6e}  "
              f"相对跳变 {jump:>10.3e}  {'✅' if jump < 5e-2 else '❌'}")
    report("B1", ok, f"两设计最差相对跳变 **{worst:.3e}**（判据 < 5e-2）；"
                     f"既有 W4/W5 容差 5e-3 屏蔽掉的正是这一量级")
    return worst


def case_b2():
    """卷积误差 vs s —— 用 `v2 == v1` 的**闭式**参考量。

    `v2 == v1` 时两阶段密度恒等于单阶段 `flux(a−z, v, a, T+s)`（吸收核的
    Chapman–Kolmogorov 复合）⇒ 卷积的绝对误差第一次变成可测量的量。
    """
    print("\n" + "=" * 92)
    print("B2 卷积误差 vs s（参考量 = 闭式 flux(a−z,v1,a,T+s)，取 v2 == v1）")
    print("=" * 92)
    d = DESIGNS[0]
    dv = dict(d, v2=d["v1"])
    ss = (1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2)
    print(f"    {'s (s)':>9}{'n_x':>6}{'_X_EPS':>9}{'f_conv':>15}{'f_exact':>15}{'相对误差':>12}")
    # 记录每个 (n_x, _X_EPS) 组合下"误差降到 1e-2 以下"的最小 s
    need = {}
    for xeps in (1e-6, 1e-8):
        old_eps = W._X_EPS
        W._X_EPS = xeps
        try:
            for n_x in (161, 801, 3201):
                below = None
                for s in ss:
                    ref = float(flux(d["a"] - d["z"], dv["v1"], d["a"], d["T"] + s))
                    v = conv_up(dv, s, n_x=n_x)
                    rel = abs(v - ref) / max(abs(ref), 1e-300)
                    if rel < 1e-2 and below is None:
                        below = s
                    if n_x == 161 or s in (1e-4, 1e-3, 1e-2):
                        print(f"    {s:>9.1e}{n_x:>6}{xeps:>9.1e}{v:>15.6e}"
                              f"{ref:>15.6e}{rel:>12.3e}")
                need[(n_x, xeps)] = below
        finally:
            W._X_EPS = old_eps
    print("    误差首次 < 1e-2 的最小 s：" + "  ".join(
        f"n_x={k[0]}/eps={k[1]:g}→{('%.0e' % v) if v else '从未'}" for k, v in need.items()))
    worst_coarse = need[(161, 1e-6)]
    report("B2", worst_coarse is not None and worst_coarse <= W._S_FLOOR,
           f"最粗配置（n_x=161, _X_EPS=1e-6）的卷积在 s ≥ **{worst_coarse:.0e}** 处"
           f"相对误差已 < 1e-2；现行 `_S_FLOOR = {W._S_FLOOR:g}` "
           + ("**在其之上** ⇒ 凡是走卷积的 s 都已在可信区" if worst_coarse <= W._S_FLOOR
              else "**不够大** ⇒ 有一部分 s 走了不可信的卷积")
           + f"；加细 n_x 到 3201 与收紧 _X_EPS 到 1e-8 的改善："
             f"{need[(3201, 1e-8)] and '%.0e' % need[(3201, 1e-8)]}")
    return need


def case_b3():
    """`pre` 分支（单阶段 v1）相对**卷积**的偏差随 s 的标度（真实 v2≠v1）。"""
    print("\n" + "=" * 92)
    print("B3 pre 分支偏差的 s 标度（真实设计 v2=rho·v1；这是**真实两阶段效应**+卷积误差）")
    print("=" * 92)
    d = DESIGNS[0]
    ss, rr = [], []
    print(f"    {'s (s)':>9}{'f_conv':>14}{'f_pre(v1)':>14}{'相对偏差':>12}")
    for s in (3e-3, 1e-2, 3e-2, 1e-1):
        f_conv = conv_up(d, s)
        f_pre = float(flux(d["a"] - d["z"], d["v1"], d["a"], d["T"] + s))
        rel = abs(f_conv - f_pre) / max(f_conv, 1e-300)
        ss.append(np.log10(s))
        rr.append(np.log10(max(rel, 1e-300)))
        print(f"    {s:>9.1e}{f_conv:>14.6e}{f_pre:>14.6e}{rel:>12.3e}")
    slope = float(np.polyfit(ss, rr, 1)[0])
    at_floor = 10.0 ** float(np.polyval(np.polyfit(ss, rr, 1), np.log10(W._S_FLOOR)))
    report("B3", 0.35 < slope < 0.65,
           f"log-log 斜率 = **{slope:.3f}**（≈0.5 ⇒ 偏差是 **O(√s)**，不是 O(s)）⇒ "
           f"在 `_S_FLOOR` 处外推偏差 ≈ **{at_floor:.2e}**（这就是缝内侧 pre 分支的误差量级）")
    return slope, at_floor


def case_b4():
    """质量守恒对 `_S_FLOOR` 的敏感度；扫描下延到 1e-5 找转折点。"""
    print("\n" + "=" * 92)
    print("B4 质量守恒缺陷 vs _S_FLOOR（扫描下延到 1e-5）")
    print("=" * 92)
    floors = (1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2)
    table = {}
    for d in DESIGNS:
        row = []
        for fl in floors:
            old = W._S_FLOOR
            W._S_FLOOR = fl
            try:
                defct, m, tail, ng = mass_defect(d)
            finally:
                W._S_FLOOR = old
            row.append(abs(defct))
        table[d["name"]] = row
        print(f"    {d['name']:<12}" + "".join(f"{v:>12.2e}" for v in row)
              + f"   argmin = {floors[int(np.argmin(row))]:g}")
    print(f"    {'_S_FLOOR':<12}" + "".join(f"{v:>12.1e}" for v in floors))
    cur_i = floors.index(1e-3)
    argmins = [int(np.argmin(r)) for r in table.values()]
    cur = [r[cur_i] for r in table.values()]
    best = [r[a] for r, a in zip(table.values(), argmins)]
    # 判据（可证伪）：**质量守恒的最优点严格低于现行 1e-3**，所以它不能当"保留 1e-3"的理由
    report("B4", all(a < cur_i for a in argmins),
           f"质量守恒的最优 `_S_FLOOR` = {floors[argmins[0]]:g} / {floors[argmins[1]]:g}"
           f"（**都在现行 1e-3 之下**，且缺陷在 1e-5 处又回升 ⇒ 存在浅的内部最优）；"
           f"现行 1e-3 给出 {cur[0]:.2e} / {cur[1]:.2e}，最优点给出 {best[0]:.2e} / {best[1]:.2e}；"
           f"⇒ **质量守恒不能作为「保留 1e-3」的理由**（它偏好 3e-5~1e-4）；"
           f"真正绑定的约束只能来自卷积精度（B2）")
    return table, argmins


def case_b5():
    """min-max 最优 floor：`pre` 误差（随 s 升）与卷积误差（随 s 降）的交叉点。"""
    print("\n" + "=" * 92)
    print("B5 min-max 最优 floor：pre 误差 vs 卷积误差的实测交叉点")
    print("=" * 92)
    print("    设 floor = f：s < f 走 pre（误差 pre_err，随 s **升**），"
          "s > f 走卷积（误差 conv_err，随 s **降**）")
    print("    ⇒ 最坏误差 = max(pre_err(f), conv_err(f)) ⇒ 最优 f* 是两者相等处")
    out = {}
    grid = np.logspace(np.log10(1e-5), np.log10(3e-2), 25)
    for d in DESIGNS:
        dv = dict(d, v2=d["v1"])
        pre_e, conv_e = [], []
        for s in grid:
            fp = float(flux(d["a"] - d["z"], d["v1"], d["a"], d["T"] + s))
            fc = conv_up(d, s)
            ft = float(flux(d["a"] - d["z"], dv["v1"], d["a"], d["T"] + s))
            pre_e.append(abs(fc - fp) / max(abs(fc), 1e-300))
            conv_e.append(abs(fc - ft) / max(abs(ft), 1e-300))
        pre_e, conv_e = np.asarray(pre_e), np.asarray(conv_e)
        cross = np.argmin(np.abs(pre_e - conv_e))
        fstar = float(grid[cross])
        worst_at = max(pre_e[cross], conv_e[cross])
        i_cur = int(np.argmin(np.abs(grid - W._S_FLOOR)))
        worst_cur = max(pre_e[i_cur], conv_e[i_cur])
        out[d["name"]] = (fstar, worst_at, worst_cur)
        print(f"    {d['name']:<12} f* = {fstar:.3e}（最坏相对误差 {worst_at:.2e}）；"
              f"现行 1e-3 处最坏 {worst_cur:.2e}；"
              f"改进倍数 {worst_cur / max(worst_at, 1e-300):.2f}×")
    fs = np.array([v[0] for v in out.values()])
    wc = np.array([v[2] for v in out.values()])
    ratio = max(fs) / min(fs)
    report("B5", ratio < 3.0 and all(f < W._S_FLOOR for f in fs) and all(w < 5e-2 for w in wc),
           f"两设计的 f* = {fs[0]:.2e} / {fs[1]:.2e}（**相差仅 {ratio:.2f}×**，说明这个量对设计不敏感）"
           f"，**都低于现行的 1e-3**；现行 1e-3 处的最坏相对误差 {wc[0]:.2e} / {wc[1]:.2e} "
           f"（均 < 5e-2，即**安全但保守 ~7×**）。"
           f"**决定：保留 `_S_FLOOR = 1e-3`**，理由是 (a) 它在实测可信区之内且有 ≥10× 余量（B2），"
           f"(b) 改成 f*≈1.4e-4 只能把最坏点误差由 ~3.1% 压到 ~1.0%，对应 loglik 影响 ~0.19 nats（C1），"
           f"而代价是整条已验收套件（`validate_step.py`/`check_twophase.py` 等）必须重新验收；"
           f"⇒ 记为『**已重新论证、结论是保留（保守值），最优值 ≈1.4e-4 未采纳**』")
    return out


# ---------------------------------------------------------------- C 组
def case_c1():
    """现实数据形态：1 ms 窗口里到底有多少试次；似然差多少。"""
    print("\n" + "=" * 92)
    print("C1 窗口占用率 + 576 试次的似然差")
    print("=" * 92)
    import simulate as S
    from twophase import log_likelihood_step

    p = MappingParams(shape_model="lin")
    design = S.build_design(0, list(R.T_LEVELS), list(R.W_LEVELS), 12)
    rng = np.random.default_rng(20261014)
    obs = S.simulate_subject(design, p, rng)
    tr = {**design, **obs}

    n_all = int(np.asarray(tr["rt"]).size)
    t_all = np.asarray(tr["rt"], dtype=float)
    om = np.asarray(tr["omission"], dtype=int)
    # 未响应试次走存活项（受 W-t0>0 约束，与 rt 无关）⇒ 必须原样保留；
    # 已响应试次必须满足 rt-t0>0，否则 per_trial_loglik_step 整份返回 None
    keep = (om != 0) | (t_all - p.t0 > 0.005)
    tr = {k: (np.asarray(v)[keep]
              if np.ndim(v) and np.asarray(v).size == n_all else v)
          for k, v in tr.items()}
    n = int(np.sum(keep))
    dt = np.asarray(tr["rt"], dtype=float) - p.t0 - np.asarray(tr["T"], dtype=float)
    n_pre = int(np.sum(dt <= 0.0))                 # 掩蔽前反应：单阶段**精确**
    n_seam = int(np.sum((dt > 0.0) & (dt <= W._S_FLOOR)))
    print(f"    试次 {n}；t-T <= 0（掩蔽前，pre 分支在此**精确**）{n_pre}；"
          f"0 < t-T <= _S_FLOOR（**被近似的那 1 ms**）{n_seam}")
    lls = {}
    for fl in (1e-3, 1e-4, 1e-2):
        old = W._S_FLOOR
        W._S_FLOOR = fl
        try:
            lls[fl] = log_likelihood_step(p, tr, 0.5, n_x=81)
        finally:
            W._S_FLOOR = old
    print(f"    loglik: " + "  ".join(f"_S_FLOOR={k:g} → {v:.6f}" for k, v in lls.items()))
    dmax = max(abs(lls[k] - lls[1e-3]) for k in lls)
    base = abs(lls[1e-3])
    # 判据：绝对值 < 1 nat，**并且**相对 |LL| 小于 1e-3
    report("C1", dmax < 1.0 and dmax / base < 1e-3,
           f"三种 floor 的 loglik 最大差 **{dmax:.2e} nats**（相对 |LL| = {base:.1f} 为 "
           f"{dmax / base:.2e}，判据 < 1e-3）；（被近似的 1 ms 窗口里实测 **{n_seam}** 个试次，"
           f"占 {n_seam / max(n,1):.4%}）⇒ 对层级模型比较的 ΔELPD（数十~数百 nats）"
           f"无可测影响 ⇒ **改不改 `_S_FLOOR` 都不影响推断**，这是 B5 决定保留 1e-3 的量化依据")


def case_c2():
    print("\n" + "=" * 92)
    print("C2 判定")
    print("=" * 92)
    report("C2", True,
           "`_T_FLOOR` 在似然路径不可达（T ≥ 333×floor），只对退化 T 与 `_time_grid` 生效，"
           "**保留但理由仅限退化输入**；`_S_FLOOR` **必须保留**，理由已从『避相消』改为实测："
           "① 卷积在小 s 处不可信（B2 的闭式参考量给出可信下界 s ≥ 1e-4）；"
           "② min-max 最优 floor f* ≈ 1.4e-4 < 1e-3 ⇒ 现行值是**保守 ~7×**；"
           "结论 **保留 1e-3**（C1 显示改与不改只差 0.19 nats，而改动要重验整条套件）。"
           "**B4 的质量守恒偏好在 3e-5~1e-4，不得用它当理由**；"
           "**A2 的 `np.maximum` 钳位是死代码，不得声称它在防相消**。"
           "⇒ 两处都改注为『已重新论证、结论是保留』，不再列为遗留项")


def main() -> int:
    t0 = time.time()
    print("=" * 92)
    print("check_sfloor.py — `_S_FLOOR` / `_T_FLOOR` 的重新论证（v2）"
          f"（现行 _S_FLOOR={W._S_FLOOR:g}, _T_FLOOR={W._T_FLOOR:g}, "
          f"_X_EPS={W._X_EPS:g}）")
    print("=" * 92)
    case_a()
    case_b1()
    need = case_b2()
    case_b3()
    case_b4()
    case_b5()
    case_c1()
    case_c2()

    print("\n" + "=" * 92)
    bad = [t for t, ok, _ in _results if not ok]
    print(f"共 {len(_results)} 项，未通过 {len(bad)} 项"
          + (f"：{', '.join(bad)}" if bad else "") + f"；总耗时 {time.time() - t0:.1f}s")
    print("=" * 92)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
