"""λ 污染项·窄窗版剖面（D126 失败记录 §五 的补救试验）。

上一版把污染分量写成 Uniform(0, W)，它抢走的是主峰 600–800 ms 的质量，
于是每个 λ 都把整条曲线的模式（而不是只补快带）改掉 ⇒ 处处 Δℓ<0。

这一版按「快带是独立猜测通道」来写：

* 污染只在**窄窗** ``[LO, min(HI, W)]`` 内出反应（LO=0.20, HI=0.45 s，
  即实测机会水平带 150–400 ms 的外沿）；
* 污染试次**不产生漏答**（猜测者一定按了键）；
* 窗内密度 ``1/(hi−lo) × 1/2``，窗外为 0。

判据：若窄窗版仍处处 Δℓ<0，则快带不是独立猜测通道，PPC 过散属于模型族
局限（漂移扩散+线性证据映射无法同时产生快而准的慢带与慢而不准的快带），
不再继续加成分；若 Δℓ>0 且稳定，则值得把 λ 通道正式写进 likelihood。

实现方式：monkey-patch ``L.per_trial_loglik``（`fit_mle` → `log_likelihood`
→ 模块全局查找，故打补丁对拟合生效）。λ=0 时先自检与原件逐位相等。
"""
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(REPO / "1_Code" / "Experiment"))

import stage8_run as S            # noqa: E402
from mapping import MappingParams  # noqa: E402
import likelihood as L             # noqa: E402
from recover_group import GROUP_INIT_LIN, WITHIN_FREE_LIN  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
WANT = {(1, 2), (3, 3), (4, 5)}
LO, HI = 0.20, 0.45
LAMS = (0.0, 0.05, 0.10, 0.15)

_ORIG = L.per_trial_loglik


def per_trial_loglik_window(p: MappingParams, tr: dict):
    """窄窗污染混合：窗内 ``(1−λ)f + λ·1/(hi−lo)·1/2``，窗外 ``(1−λ)f``。"""
    tp = L.trial_params(tr, p)
    v, a, z, t0 = tp["v"], tp["a"], tp["z"], tp["t0"]
    lam = float(tr.get("lambda_guess", 0.0) or 0.0)
    if not (0.0 <= lam < 1.0):
        return None
    if not (np.all(np.isfinite(v)) and np.all(a > 0) and np.all(z > 0)
            and np.all(z < a) and t0 > 0):
        return None

    omission = tr["omission"]
    responded = omission == 0
    out = np.empty(tr["rt"].size, dtype=float)
    log_1ml = np.log1p(-lam)

    if np.any(responded):
        t = tr["rt"][responded] - t0
        if np.any(t <= 0):
            return None
        side = tr["side"][responded]
        a_r, z_r, v_r = a[responded], z[responded], v[responded]
        d = np.where(side == 1, a_r - z_r, z_r)
        vv = np.where(side == 1, v_r, -v_r)
        f = L.flux(d, vv, a_r, t)
        if not np.all(np.isfinite(f)) or np.any(f <= 0):
            return None
        log_f = np.log(f)
        rt_r = tr["rt"][responded]
        hi = np.minimum(HI, tr["W"][responded])
        inside = (rt_r >= LO) & (rt_r <= hi) & (hi > LO)
        val = np.where(inside, np.log(lam) - np.log(np.maximum(hi - LO, 1e-9))
                       - np.log(2.0), -np.inf)
        out[responded] = np.logaddexp(log_1ml + log_f, val)

    if np.any(~responded):
        t_max = tr["W"][~responded] - t0
        if np.any(t_max <= 0):
            return None
        s = L.survival_series(v[~responded], a[~responded], z[~responded], t_max)
        if not np.all(np.isfinite(s)) or np.any(s <= 0):
            return None
        out[~responded] = log_1ml + np.log(s)
    return out


people, rejected = S.collect([DATA], None, MappingParams(shape_model="lin"))
print(f"可用 {len(people)} 人、被拒 {len(rejected)}；窗口 [{LO}, {HI}] s")
pick = [p for p in people if (p["group"], p["subject"]) in WANT]

# --- 自检：λ=0 时补丁版与原件逐位相等 ---
tr0 = pick[0]["tr"]
tr0 = dict(tr0, lambda_guess=0.0)
o = _ORIG(GROUP_INIT_LIN, tr0)
w = per_trial_loglik_window(GROUP_INIT_LIN, tr0)
same = o is not None and w is not None and np.array_equal(o, w)
print(f"自检 λ=0 逐位等价：{same}"
      f"（ℓ_orig={np.sum(o):.6f}  ℓ_win={np.sum(w):.6f}）")
if not same:
    raise SystemExit("λ=0 不等价，先修再跑")

L.per_trial_loglik = per_trial_loglik_window
print("已打补丁：L.per_trial_loglik = per_trial_loglik_window\n")

for p in pick:
    tr_base = p["tr"]
    om = tr_base["omission"] == 0
    rt_min = float(tr_base["rt"][om].min())
    init = replace(GROUP_INIT_LIN, t0=min(GROUP_INIT_LIN.t0, rt_min - 0.02))
    n_fast = int(np.sum((tr_base["rt"] <= 0.40) & om))
    print(f"=== 组 {p['group']} 被试 {p['subject']}：{tr_base['rt'].size} 试次"
          f"（漏答 {int(tr_base['omission'].sum())}，≤400 ms {n_fast} 个，"
          f"最小 RT {rt_min:.3f}）===")
    print(f"{'λ':>5s}{'ℓ_max':>11s}{'Δℓ':>8s}{'t0':>7s}{'a':>7s}{'v':>7s}{'秒':>6s}")
    base = None
    for lam in LAMS:
        tr = dict(tr_base)
        tr["lambda_guess"] = lam
        t0s = time.time()
        r = L.fit_mle(tr, list(WITHIN_FREE_LIN), init,
                      n_restart=1, maxiter=250, maxfun=6000)
        ll = r["loglik"]
        if base is None:
            base = ll
        par = r["params"]
        print(f"{lam:>5.2f}{ll:>11.2f}{ll - base:>8.2f}{par.t0:>7.3f}"
              f"{par.a_ref:>7.3f}{par.d_ref:>7.3f}{time.time() - t0s:>6.1f}")
    print()
