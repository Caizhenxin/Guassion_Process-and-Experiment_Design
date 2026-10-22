"""ramp.py —— M-T2（斜坡漂移）的数据生成器。

三条模型的关系
--------------
* **M-T1**（阶跃，`twophase.py`）：刺激期内漂移恒为 ``d_stim``；掩蔽后降为 ``rho·d_stim``。
* **M-T2**（斜坡，本文件）：刺激期内漂移**逐步爬升** ``d(t) = d_stim·(1 − e^{−t/τ_T})``；
  掩蔽后取掩蔽时刻的值并乘 ``rho``：``rho·d_stim·(1 − e^{−T/τ_T})``。
* **M-T3**（单阶段）：``rho = 1`` 的 M-T1（严格嵌套特例）。

于是 ``τ_T → 0`` 时 M-T2 ≡ M-T1 ⇒ 三者是**同一条轴上的三种取值**，而不是三个互不相干
的模型。这条轴解释的是同一个现象：**刺激呈现得越久，证据为什么积累得越多**——
M-T1 说「多了 T 秒的满速积累」，M-T2 说「漂移本身要时间才能升到满」。

⚠️ 与 M-T1 的口径差异（为什么 M-T2 要单独一个生成器）
-----------------------------------------------------
在 M-T1 里，T 的效应来自映射方程 ``β_T·(T − T_ref)``（`mapping.drift_magnitude`）。
在 M-T2 里，T 的效应**主要来自斜坡本身**：T 越长，爬升的时间越长，平均漂移越大。
两者同时打开会重复计数，所以 `gen_model_data.py` 生成 M-T2 时默认
``beta_T_mapping = 0``（`--ramp-beta-t zero`），只让 τ_T 产生 T 效应。

⚠️ 本文件**没有似然**，因此 M-T2 目前只能造数据、不能拟合（D113 记录在案）。
要把它纳入模型比较，需要先加 ``per_trial_loglik_ramp``——斜坡模型的首次通过密度没有
闭式解，只能靠 PDE/级数近似或模拟近似，成本远高于 M-T1/M-T3 的嵌套比较。

接口与 `twophase.simulate_euler_subject` 完全一致（``rt``/``side``/``omission``/``truth``），
以便与 M-T1/M-T3 共用下游的 `trials_from_arrays` 与可视化。
"""
from __future__ import annotations

import numpy as np

from mapping import MappingParams, trial_params

__all__ = ["simulate_ramp_subject", "ramp_profile"]


def ramp_profile(t: np.ndarray, tau: float) -> np.ndarray:
    """斜坡增益 ``1 − e^{−t/τ}``（t 为秒，从刺激开始计）。"""
    t = np.asarray(t, dtype=float)
    return 1.0 - np.exp(-np.maximum(t, 0.0) / max(float(tau), 1e-9))


def simulate_ramp_subject(design: dict, p: MappingParams, rho: float,
                          rng: np.random.Generator, dt: float = 5e-5,
                          t_max: float | None = None,
                          tau_ramp: float | None = None,
                          drift_sd: float = 0.0) -> dict:
    """按 M-T2（斜坡）生成一名被试的试次级数据。

    Parameters
    ----------
    design : dict
        与 `twophase.simulate_euler_subject` 相同：``P``/``T``/``W``/``is_self``/``is_match``。
    p : MappingParams
        **应当已把 ``beta_T`` 置 0**（见模块 docstring），否则 T 效应重复计数。
    rho : float
        掩蔽后保留率；``rho = 1`` 表示掩蔽无影响。
    dt : float
        Euler 步长，默认 5e-5（与 M-T1 同标定，见 `twophase.simulate_euler_subject`）。
    tau_ramp : float | None
        斜坡时标（秒）；默认取 ``p.tau_T``。
    """
    tau = float(p.tau_T if tau_ramp is None else tau_ramp)
    if not (tau > 0):
        raise ValueError(f"tau_ramp 必须为正：{tau}")

    tp = trial_params(design, p)
    v = np.asarray(tp["v"], dtype=float)
    if drift_sd and drift_sd > 0:
        # 与 `twophase.simulate_euler_subject` 同口径：逐试次漂移变异（lognormal，均值 1）
        v = v * np.exp(rng.normal(0.0, float(drift_sd), v.size))
    a = np.asarray(tp["a"], dtype=float)
    z = np.asarray(tp["z"], dtype=float)
    t0 = tp["t0"]
    W = np.asarray(design["W"], dtype=float)
    TT = np.asarray(design["T"], dtype=float)
    n = v.size
    if t_max is None:
        t_max = float(np.max(W))
    n_steps = int(np.ceil(t_max / dt))
    sq = np.sqrt(dt)

    # 掩蔽时刻的斜坡增益（逐试次常量，事先算好）
    g_at_T = ramp_profile(TT, tau)

    x = z.astype(float).copy()
    alive = np.ones(n, dtype=bool)
    tau_hit = np.full(n, np.inf)
    side = np.zeros(n, dtype=int)

    for i in range(n_steps):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        s = i * dt
        g_now = ramp_profile(np.array([s]), tau)[0]
        # 刺激期内：漂移随斜坡爬升；掩蔽后：取掩蔽时刻的漂移并乘 rho
        vv = np.where(s <= TT[idx],
                      v[idx] * g_now,
                      float(rho) * v[idx] * g_at_T[idx])
        x[idx] += vv * dt + sq * rng.standard_normal(idx.size)
        hit_u = idx[x[idx] >= a[idx]]
        hit_l = idx[x[idx] <= 0.0]
        if hit_u.size:
            tau_hit[hit_u] = s + dt
            side[hit_u] = 1
            alive[hit_u] = False
        if hit_l.size:
            tau_hit[hit_l] = s + dt
            side[hit_l] = 0
            alive[hit_l] = False

    rt = tau_hit + float(t0)
    omission = (~np.isfinite(rt)) | (rt > W)
    rt = np.where(omission, np.nan, rt)
    side = np.where(omission, 0, side)
    return {
        "rt": rt, "side": side.astype(int), "omission": omission.astype(int),
        "truth": {"v": v, "a": a, "z": z, "t0": np.full(n, t0),
                  "d_at_T": v * g_at_T, "tau_ramp": np.full(n, tau)},
    }
