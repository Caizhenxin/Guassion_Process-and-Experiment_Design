"""解析超参数 Hessian（Louis 恒等式）的对错与代价 —— 独立判据，不靠"两条分支互相对一眼"。

判据分三层：

* **A 组（闭式高斯层级，内层拉普拉斯精确）**：真边际 = ``y ~ N(mu, diag(sigma²+1))``
  有闭式，于是可以对它做**独立**的中心差分 Hessian ``H_true``。此时
  ``hyper_hessian_analytic`` 必须与 ``H_true`` 吻合到机器精度量级。
  ⇒ 这一组**证明的是推导本身**，与 DDM 无关。
  A 组还包含"测试有牙齿"的检查：扰动 ``covs`` / ``modes`` 必须让解析 Hessian 变化，
  否则说明 ``C`` 根本没被用上，而 A1 会变成一道盲判据。
* **B 组（真实 DDM）**：``hyper_hessian_analytic`` 算的是**真边际**的 Hessian，
  ``hyper_hessian`` 算的是**拉普拉斯边际**的 Hessian ⇒ 两者**允许有差**，
  差值就是内层拉普拉斯误差。这组同时**扫步长**，因为有限差分还额外受步长截断
  误差与差分噪声影响 —— 实测在 ``HYPER_STEP = 0.05`` 处差分版可能**不是正定**的，
  那样它给出的后验 SD 就不可用（判据只在差分版正定的步长上比较）。
* **C 组（接线）**：``hyper_draws(method=...)`` 能出 ``(n_draws, 2K)``，
  ``cov`` 与 ``inv(A)`` 一致，抽样 SD 与解析 SD 在蒙特卡洛误差内一致，
  非法 ``method`` 必须报错。

跑法：``python 1_Code/DDM_Core/_scratch/check_hyper_hess.py``（约 6–8 min）。
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hier import (HYPER_STEP, ddm_subject, hier_fit,   # noqa: E402
                  hyper_draws, hyper_hessian, hyper_hessian_analytic,
                  make_subject, subject_map_laplace)
from mapping import MappingParams                      # noqa: E402
from simulate import build_design                      # noqa: E402
from twophase import simulate_euler_subject            # noqa: E402

WIDE = (-50.0, 50.0)
N_FAIL = 0


def check(name, ok, detail=""):
    global N_FAIL
    mark = "✅" if ok else "❌"
    if not ok:
        N_FAIL += 1
    print(f"  {mark} {name}" + (f"\n       {detail}" if detail else ""))


def note(text):
    print(f"       · {text}")


def fd_hess(f, theta0, step=1e-4):
    """中心差分 Hessian（与 `hier.hyper_hessian` 同一格式，但可作用在闭式函数上）。"""
    theta0 = np.asarray(theta0, float)
    n = theta0.size
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            tp, tm = theta0.copy(), theta0.copy()
            tp[i] += step
            tp[j] += step
            tm[i] -= step
            tm[j] -= step
            a, b = f(tp), f(tm)
            tp2, tm2 = theta0.copy(), theta0.copy()
            tp2[i] += step
            tp2[j] -= step
            tm2[i] -= step
            tm2[j] += step
            c, d = f(tp2), f(tm2)
            H[i, j] = H[j, i] = (a - c - d + b) / (4.0 * step * step)
    return H


def rel_max(X, Y):
    """相对差（按 Y 的最大绝对值归一），并给出最差元素的位置。"""
    s = float(np.max(np.abs(Y)))
    if s == 0.0:
        return float(np.max(np.abs(X - Y))), (0, 0)
    D = np.abs(X - Y)
    ij = np.unravel_index(int(np.argmax(D)), D.shape)
    return float(np.max(D) / s), ij


def pos_def_stats(H):
    """H 是 ∂²log posterior；A = −H。返回 (min eig of A, 非正特征值个数, cov)。"""
    A = -0.5 * (H + H.T)
    ev, Q = np.linalg.eigh(A)
    mx = float(np.max(np.abs(ev))) if ev.size else 1.0
    use = np.maximum(ev, max(1e-6 * mx, 1e-12))
    cov = (Q / use) @ Q.T
    return float(np.min(ev)), int(np.sum(ev <= 0.0)), cov


# ======================================================================
# A 组：闭式高斯层级 —— 内层拉普拉斯精确，真边际有闭式
# ======================================================================
def gauss_setup(Y, mu, ls):
    subs, modes, covs = [], [], []
    for y in Y:
        yy = np.asarray(y, float)
        k = yy.size
        ll = (lambda yv: (lambda x: -0.5 * float(np.sum((x - yv) ** 2))))(yy)
        s = make_subject(ll, [WIDE[0]] * k, [WIDE[1]] * k,
                         [f"g{i}" for i in range(k)])
        r = subject_map_laplace(s, None, mu, ls)
        subs.append(s)
        modes.append(r["mode"])
        covs.append(r["cov"])
    return subs, np.array(modes), covs


def log_marg_true(Y, mu, ls):
    """``Σ_s log N(y_s; mu, diag(sigma²+1)) + log 超参数先验``（完全闭式）。"""
    v = np.exp(2.0 * np.asarray(ls, float)) + 1.0
    from hier import _log_hyper_prior
    tot = _log_hyper_prior(mu, ls)
    for y in Y:
        d = (np.asarray(y, float) - np.asarray(mu, float)) ** 2
        tot += float(-0.5 * np.sum(d / v + np.log(2.0 * np.pi * v)))
    return float(tot)


def case_a():
    print("\nA 组：闭式高斯层级（内层拉普拉斯精确 ⇒ 解析式必须与闭式差分吻合）")
    k, n_sub = 2, 4
    rng = np.random.default_rng(20261014)
    Y = [np.array([0.7, -0.4]) + 0.5 * rng.standard_normal(k) for _ in range(n_sub)]
    mu0 = np.array([0.10, -0.30])
    ls0 = np.array([np.log(0.60), np.log(0.45)])
    theta0 = np.concatenate([mu0, ls0])
    subs, modes, covs = gauss_setup(Y, mu0, ls0)

    exact_mode = np.array([(y[0] + mu0[0] / np.exp(2 * ls0[0])) /
                           (1.0 + 1.0 / np.exp(2 * ls0[0])) for y in Y])
    exact_c = 1.0 / (1.0 + 1.0 / np.exp(2 * ls0[0]))
    err_mode = float(np.max(np.abs(modes[:, 0] - exact_mode)))
    check("A0 闭式基准自洽：subject_map_laplace 的模式 = (y + mu/sigma²)/(1+1/sigma²)",
          err_mode < 1e-6,
          f"max|Δmode| = {err_mode:.3e}；C_00 = {covs[0][0,0]:.8f} vs 闭式 {exact_c:.8f}")

    f_true = lambda th: log_marg_true(Y, th[:k], th[k:])
    H_true = fd_hess(f_true, theta0)
    base = float(np.max(np.abs(H_true)))

    t0 = time.perf_counter()
    ha = hyper_hessian_analytic(modes, covs, mu0, ls0)
    t_a = time.perf_counter() - t0
    Ha = ha["H"]

    t0 = time.perf_counter()
    Hf = hyper_hessian(subs, mu0, ls0, modes)["H"]
    t_fd = time.perf_counter() - t0
    Hf_s = hyper_hessian(subs, mu0, ls0, modes, step=0.005)["H"]

    H_true2 = fd_hess(f_true, theta0, step=2.5e-5)
    fd_self = float(np.max(np.abs(H_true - H_true2)) / base)

    r_a, ij_a = rel_max(Ha, H_true)
    r_f, ij_f = rel_max(Hf, H_true)
    r_fs, _ = rel_max(Hf_s, H_true)
    r_af, ij_af = rel_max(Ha, Hf)

    check("A1 解析 Hessian == 闭式真边际的差分 Hessian（相对化到 max|H|）",
          r_a < 1e-6,
          f"max 相对差 = {r_a:.3e}（最差元素 H[{ij_a[0]},{ij_a[1]}]）；"
          f"max|H_true| = {base:.6f}；闭式差分自身的步长误差 = {fd_self:.3e}")
    expo = (np.log(r_f / r_fs) / np.log(HYPER_STEP / 0.005)
            if r_fs > 0 else float("nan"))
    check("A2 有限差分版（拉普拉斯边际）在此也与闭式真边际一致，残差随步长单调下降"
          "（⇒ 它是**离散/优化残差**，不是定义差异）",
          r_f < 1e-3 and r_fs < r_f / 5.0,
          f"step = HYPER_STEP = {HYPER_STEP}: max 相对差 = {r_f:.3e}"
          f"（最差 H[{ij_f[0]},{ij_f[1]}]）；step = 0.005: {r_fs:.3e}"
          f" ⇒ 步长缩 10× 让残差降 {r_f / max(r_fs, 1e-300):.0f}×，"
          f"实测幂律指数 ≈ {expo:.2f}（不是理想的 2 —— 与优化器收敛噪声同量级）")
    check("A3 解析版 vs 有限差分版（默认步长）：精确情形下应当同量",
          r_af < 1e-3,
          f"max 相对差 = {r_af:.3e}（最差元素 H[{ij_af[0]},{ij_af[1]}]）；"
          f"其中大部分来自上面那条步长截断")

    hf = hyper_hessian(subs, mu0, ls0, modes)
    n = theta0.size
    check("A4 代价：解析版 0 次众数搜索，差分版 4n(n+1)/2·N 次",
          ha["n_evals"] == 0 and hf["n_evals"] == 4 * n * (n + 1) // 2,
          f"解析 n_evals = {ha['n_evals']}（墙钟 {t_a * 1000:.2f} ms）vs "
          f"差分 n_evals = {hf['n_evals']}（墙钟 {t_fd:.3f}s，N = {n_sub}）")

    covs_up = [1.6 * C for C in covs]
    H_c = hyper_hessian_analytic(modes, covs_up, mu0, ls0)["H"]
    H_m = hyper_hessian_analytic(modes + 0.30, covs, mu0, ls0)["H"]
    d_c = float(np.max(np.abs(H_c - Ha)) / base)
    d_m = float(np.max(np.abs(H_m - Ha)) / base)
    check("A5 判据有牙齿：放大 C 与平移 x* 都必须改变解析 Hessian",
          d_c > 1e-3 and d_m > 1e-3,
          f"放大 C ×1.6 ⇒ max|ΔH|/max|H| = {d_c:.3e}；"
          f"x* + 0.30 ⇒ {d_m:.3e}")

    bad = []
    try:
        hyper_hessian_analytic(modes[:, :1], covs, mu0, ls0)
    except ValueError:
        bad.append("modes 维数不符")
    try:
        hyper_hessian_analytic(modes, covs[:2], mu0, ls0)
    except ValueError:
        bad.append("covs 个数不符")
    try:
        hyper_hessian_analytic(modes, [np.eye(3)] * n_sub, mu0, ls0)
    except ValueError:
        bad.append("cov 形状不符")
    check("A6 形状守卫：modes/covs 不合法必须 ValueError（三条各报一次）",
          len(bad) == 3, "触发：" + "、".join(bad))


# ======================================================================
# B 组：真实 DDM —— 两版算的是不同量，只测量并报告
# ======================================================================
NAMES = ["d_ref", "beta_T"]


def ddm_setup(n_sub=2, n_rep=3):
    truth = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                          shape_model="lin")
    design = build_design(30.0, [0.03333, 0.14999], [0.79998, 1.79990], n_rep)
    subs = []
    for s in range(n_sub):
        rng = np.random.default_rng(9200 + s)
        sim = simulate_euler_subject(design, truth, 1.0, rng, dt=5e-5)
        tr = dict(design)
        tr.update({k: np.asarray(v) for k, v in sim.items()})
        subs.append(ddm_subject(tr, truth, NAMES, rho_free=False))
    return subs, truth, design


def case_b():
    print("\nB 组：真实 DDM（解析版算真边际、差分版算拉普拉斯边际 ⇒ 允许有差，只报告）")
    subs, truth, design = ddm_setup(n_sub=2)
    n_tr = int(design["T"].size)
    print(f"      构造：N = 2，{n_tr} 试次/人，被试内参数 {'/'.join(NAMES)}")

    t0 = time.perf_counter()
    fit = hier_fit(subs, n_em=8)
    t_fit = time.perf_counter() - t0
    k = fit["k"]
    labels = [f"mu_{n}" for n in NAMES] + [f"ls_{n}" for n in NAMES]
    note(f"EM 拟合 {fit['n_em_used']} 轮、{t_fit:.1f}s；"
         f"mu = {np.round(fit['mu'], 4)}、sigma = {np.round(fit['sigma'], 4)}、"
         f"n_flipped = {fit['n_flipped']}")

    t0 = time.perf_counter()
    ha = hyper_hessian_analytic(fit["modes"], fit["covs"], fit["mu"],
                                fit["log_sigma"])
    t_a = time.perf_counter() - t0
    mn_a, bad_a, cov_a = pos_def_stats(ha["H"])
    sd_a = np.sqrt(np.diag(cov_a))
    check("B1 解析版的 A = −∂²log post 正定（C 为合法协方差时应当如此）",
          bad_a == 0,
          f"min eig = {mn_a:.3e}、非正 {bad_a} 个；后验 SD = "
          + "、".join(f"{labels[i]} {sd_a[i]:.4f}" for i in range(sd_a.size)))

    rows = []
    for st in (HYPER_STEP, 0.02, 0.005):
        t0 = time.perf_counter()
        hf = hyper_hessian(subs, fit["mu"], fit["log_sigma"], fit["modes"], step=st)
        dt = time.perf_counter() - t0
        mn, bad, cv = pos_def_stats(hf["H"])
        sdf = np.sqrt(np.diag(cv))
        rows.append({"step": st, "min_eig": mn, "n_bad": bad, "sd": sdf,
                     "n_evals": hf["n_evals"], "t": dt, "H": hf["H"]})
        note(f"差分 step = {st:<6}: min eig = {mn:+.4e}、非正 {bad} 个、"
             f"墙钟 {dt:.1f}s；SD = " + "、".join(f"{v:.4g}" for v in sdf))

    pd_rows = [r for r in rows if r["n_bad"] == 0]

    # B2：判据不能是"差分版可用"（实测 3 个步长 0/3 正定 —— 我的原先期望被推翻）。
    #     可为真的要求是：**失真必须被如实报告**，调用方才能据此拒绝该后验。
    dd = hyper_draws(subs, fit, n_draws=2, seed=1, method="fd")
    check("B2 差分版若不正定，其失真必须被**如实报告**"
          "（n_flipped = 该 Hessian 非正特征值个数，不得静默抬地板后照常抽样）",
          int(dd["n_flipped"]) == int(rows[0]["n_bad"]),
          f"`hyper_draws(method='fd', step={rows[0]['step']:g})` 报 "
          f"n_flipped = {dd['n_flipped']}；同一步长 Hessian 的非正特征值 "
          f"{rows[0]['n_bad']} 个"
          + ("（⇒ 失真被暴露，调用方可拒绝该后验）"
             if rows[0]["n_bad"] > 0 else "（⇒ 该点上差分版正好正定）"))

    if pd_rows:
        r0 = max(pd_rows, key=lambda r: r["step"])   # 取最接近默认步长的那个
        ratio = r0["sd"] / sd_a
        worst = int(np.argmax(np.abs(np.log(ratio))))
        check("B3 在差分版正定的步长上，两版后验 SD 同数量级"
              f"（step = {r0['step']:g}）",
              bool(np.all((ratio > 0.3) & (ratio < 3.0))),
              "；".join(f"{labels[i]} {ratio[i]:.3f}" for i in range(ratio.size))
              + f" ⇒ 最差 {labels[worst]} 比值 {ratio[worst]:.3f}"
              f"（最大偏离 {abs(ratio[worst] - 1) * 100:.1f}%）")
        r_h, ij_h = rel_max(ha["H"], r0["H"])
        note(f"同一步长上 Hessian 逐元素差 max|ΔH|/max|H| = {r_h:.3e}"
             f"（最差 H[{ij_h[0]},{ij_h[1]}]）—— 这个数就是**内层拉普拉斯误差**的实测量级")
    else:
        note("B3 跳过：没有任何差分步长给出正定 Hessian ⇒ 两版 SD 在该点"
             "**无法比较**；解析版是唯一可用的后验，SD = "
             + "、".join(f"{labels[i]} {sd_a[i]:.4g}" for i in range(sd_a.size)))

    non_pd = [r for r in rows if r["n_bad"] > 0]
    if non_pd:
        r1 = non_pd[0]
        note(f"❗实测缺陷（记录，不是判据）：差分版在 step = {r1['step']:g} 处"
             f"**不正定** —— min eig = {r1['min_eig']:+.4e}、非正 {r1['n_bad']} 个，"
             f"而 `hyper_draws` 会把负特征值抬到地板后照常抽样 ⇒ "
             f"该配置下差分后验 SD 不可用（见上面 B2：**但它是被如实报告的**）")
        note(f"解析版同点 min eig = {mn_a:+.4e}（正定）⇒ 解析版不只是快："
             f"它**不可能**因为差分噪声丢掉正定性；代价是它算的是真边际的 Hessian，"
             f"内层拉普拉斯误差必须如实报告（见上面那条逐元素差）")

    hf0 = rows[0]
    check("B5 代价：解析版 0 次搜索 vs 差分版 npair·N 次温启动众数搜索",
          ha["n_evals"] == 0 and hf0["n_evals"] == 4 * (2 * k) * (2 * k + 1) // 2,
          f"解析：n_evals = {ha['n_evals']}、墙钟 {t_a * 1000:.1f} ms；"
          f"差分（step = {hf0['step']:g}）：n_evals = {hf0['n_evals']} × 2 人 = "
          f"{hf0['n_evals'] * 2} 次众数搜索、墙钟 {hf0['t']:.1f}s "
          f"⇒ 加速 {hf0['t'] / max(t_a, 1e-9):.0f}×")

    note("正式规模换算：M-T3（K=7, n=14）差分需 420·N 次搜索；"
         "M-T1（K=8, n=16, ρ 自由）需 544·N 次搜索；解析版两项都是 **0**")
    return fit, ha, subs


# ======================================================================
# C 组：接线
# ======================================================================
def case_c(fit, subs):
    print("\nC 组：hyper_draws 的接线")
    k = fit["k"]
    da = hyper_draws(subs, fit, n_draws=200, seed=3, method="analytic")
    check("C1 解析法的 draws 形状正确",
          da["theta"].shape == (200, 2 * k),
          f"theta {da['theta'].shape}、mu {da['mu'].shape}、"
          f"log_sigma {da['log_sigma'].shape}、n_flipped = {da['n_flipped']}、"
          f"n_evals = {da['n_evals']}（不随 n_draws 变）")

    ha = hyper_hessian_analytic(fit["modes"], fit["covs"], fit["mu"],
                                fit["log_sigma"])["H"]
    _, _, cov_direct = pos_def_stats(ha)
    d = float(np.max(np.abs(da["cov"] - cov_direct)) / np.max(np.abs(cov_direct)))
    check("C2 draws 的 cov 与 inv(A) 一致（同一份 Hessian，没有二次近似）",
          d < 1e-12, f"max 相对差 = {d:.3e}")

    sd_mc = np.std(da["theta"], axis=0)
    sd_th = np.sqrt(np.diag(cov_direct))
    rr = sd_mc / sd_th
    worst = int(np.argmax(np.abs(np.log(rr))))
    check("C3 200 次抽取的经验 SD 与解析 SD 在蒙特卡洛误差内一致",
          bool(np.all(np.abs(rr - 1.0) < 0.25)),
          "比值 " + "、".join(f"{v:.3f}" for v in rr)
          + f" ⇒ 最差偏离 {abs(rr[worst] - 1) * 100:.1f}%")

    try:
        hyper_draws(subs, fit, n_draws=2, method="bogus")
        ok, msg = False, "没有报错"
    except ValueError as e:
        ok, msg = True, str(e)
    check("C4 非法 method 必须 ValueError（不得静默退回某一版）", ok, msg)


def main():
    print("=" * 72)
    print("解析超参数 Hessian（Louis 恒等式）的校验")
    print("=" * 72)
    case_a()
    fit, ha, subs = case_b()
    case_c(fit, subs)
    print("\n" + "=" * 72)
    if N_FAIL == 0:
        print("全部通过 ✅")
        return 0
    print(f"未通过 {N_FAIL} 项 ❌")
    return 1


if __name__ == "__main__":
    sys.exit(main())
