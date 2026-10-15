# -*- coding: utf-8 -*-
"""
stage8.py —— Stage 8 核心：拉普拉斯后验抽样 + 后验预测检验（零依赖路线）
==========================================================================
主计划 §3 Stage 8 的字面要求是：
    层级 DDM 拟合 → PPC → PSIS-LOO（含 Pareto k 诊断）→ 模型比较
    → leave-one-participant-out

⚠️ **环境约束（2026-10-14 实测）**：本机没有 `pymc` / `numpyro` / `jax` /
`arviz` / `cmdstanpy` / `emcee` / `torch` / `hddm`（全部 `ModuleNotFoundError`）。
因此本模块走**零依赖路线**：用 `likelihood.numerical_hessian` 在众数处取
Hessian，做**拉普拉斯近似**得到后验协方差并抽样。PPC 与
leave-one-participant-out 两条路线与抽样器无关，不受影响。

本模块交付的三件东西
--------------------
1. `laplace_draws` —— 通用拉普拉斯抽样器（只要求一个 `log_post_x` 闭包）；
2. `subject_laplace` —— 把逐被试 WFPT 对数似然包成 `log_post_x` 再抽样；
3. `sample_ppc` / `ppc_table` —— 后验预测抽样与检验统计量表。

⚠️ **已知限制（必须随结果一起报）**
* 拉普拉斯近似是**局部**近似：似然面在 `(τ_T, β_T, β_ST)` 与 `(τ_a, δ_a)`
  方向极平（见 `likelihood.fit_mle` 的注释），平方向上正态近似最难成立，
  所以**必须同时报 Hessian 的特征值谱与 `n_flipped`**；
* 本项目目前**没有先验**（`DDM_Core` 全线是 MLE），所以 `log_post` 在
  默认情况下就是对数似然 ⇒ 抽到的是"以 MLE 为中心、按观测信息量宽度"的
  近似后验。它**不等于**真实的贝叶斯后验，报告中必须写清这一点；
* Hessian 在**无约束坐标** `x` 上算，`_from_x` 再映射回有界参数
  ⇒ 边界附近（如 `τ_P` 撞上界）抽样分布会被挤压。
"""
from __future__ import annotations

import sys
from typing import Callable

import numpy as np

from likelihood import _from_x, _to_x, _bounds_for, log_likelihood, numerical_hessian
from mapping import MappingParams
from simulate import simulate_subject

__all__ = ["laplace_draws", "hessian_x", "subject_laplace", "sample_ppc",
           "ppc_table", "format_ppc",
           "PPC_STATS", "PPC_CELL_KEYS", "CELL_STATS"]

#: 拉普拉斯协方差的特征值下限（相对最大特征值）；小于它的方向被"压平"
EIG_FLOOR = 1e-6


# ------------------------------------------------------------------
# 1. 通用拉普拉斯抽样器
# ------------------------------------------------------------------
def hessian_x(f: Callable[[np.ndarray], float], x0: np.ndarray,
              rel_step: float = 1e-4) -> np.ndarray:
    """在 ``x0`` 处对 ``f``（**对数**后验）做中心差分，返回二阶导矩阵。

    与 `likelihood.numerical_hessian` 同法（那里对**负**对数似然），
    但这里接受任意 `log_post_x` 闭包，便于拿解析基准做自测。
    """
    x0 = np.asarray(x0, dtype=float)
    n = x0.size
    h = np.maximum(np.abs(x0) * rel_step, 1e-4)
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            xpp, xpm, xmp, xmm = x0.copy(), x0.copy(), x0.copy(), x0.copy()
            xpp[i] += h[i]; xpp[j] += h[j]
            xpm[i] += h[i]; xpm[j] -= h[j]
            xmp[i] -= h[i]; xmp[j] += h[j]
            xmm[i] -= h[i]; xmm[j] -= h[j]
            H[i, j] = H[j, i] = (f(xpp) - f(xpm) - f(xmp) + f(xmm)) / (4 * h[i] * h[j])
    return H


def laplace_draws(log_post_x: Callable[[np.ndarray], float], x0,
                  n_draws: int = 4000, seed: int = 0, rel_step: float = 1e-4,
                  eig_floor: float = EIG_FLOOR) -> dict:
    """在 ``x0``（应为**众数**）处做拉普拉斯近似并抽 ``n_draws`` 条后验样本。

    目标协方差 = ``(−∂²log_post/∂x²)^{-1}``。若非正定（似然面在该处不是极大），
    把负/零特征值**抬到** ``eig_floor * max|λ|`` 后再求逆，并如实报告
    ``n_flipped``（被抬起的个数）——**这个数不为 0 就说明该点不是可信的众数**。

    Returns
    -------
    dict: ``x``(n_draws, n) 无约束坐标抽取、``log_post``(n_draws,) 各抽取点的
          对数后验、``log_post_mode``、``cov_x``、``eigval``（**原始**特征值，
          升序）、``n_flipped``、``n_draws``、``x_mode``、``method``。
    """
    x0 = np.asarray(x0, dtype=float).ravel()
    n = x0.size
    H = hessian_x(log_post_x, x0, rel_step=rel_step)
    A = -H                                   # 众数处应为正定
    A = 0.5 * (A + A.T)
    eigval, eigvec = np.linalg.eigh(A)
    mx = float(np.max(np.abs(eigval))) if eigval.size else 1.0
    floor = max(eig_floor * mx, 1e-12)
    n_flipped = int(np.sum(eigval <= 0.0))
    eig_use = np.maximum(eigval, floor)
    cov = (eigvec / eig_use) @ eigvec.T
    cov = 0.5 * (cov + cov.T)

    rng = np.random.default_rng(seed)
    method = "cholesky"
    try:
        x = rng.multivariate_normal(x0, cov, size=n_draws, method="cholesky")
    except np.linalg.LinAlgError:
        # 极端病态时 cholesky 会失败；退回特征分解抽样（数学上等价，只是慢）
        method = "eigh"
        z = rng.standard_normal((n_draws, n))
        x = x0 + (z * np.sqrt(eig_use)) @ eigvec.T
        x = np.atleast_2d(x)

    lp = np.array([log_post_x(xi) for xi in np.atleast_2d(x)], dtype=float)
    return {
        "x": np.atleast_2d(x), "log_post": lp,
        "log_post_mode": float(log_post_x(x0)),
        "cov_x": cov, "eigval": eigval, "n_flipped": n_flipped,
        "n_draws": int(n_draws), "x_mode": x0, "method": method,
        "eig_floor": float(floor),
    }


# ------------------------------------------------------------------
# 2. 逐被试后验（默认无先验 ⇒ 对数后验 = 对数似然）
# ------------------------------------------------------------------
def subject_laplace(tr: dict, names: list[str], p_map: MappingParams,
                    n_draws: int = 4000, seed: int = 0, rel_step: float = 1e-4,
                    bounds_override: dict | None = None,
                    log_prior_x: Callable[[np.ndarray], float] | None = None) -> dict:
    """对一名被试在 MLE（``p_map``）处做拉普拉斯近似并抽样。

    ⚠️ `p_map` 必须真的是该数据的 MLE，否则 `n_flipped > 0`，协方差不可信。
    """
    names = list(names)
    lo, hi = _bounds_for(names, bounds_override)
    x0 = _to_x(p_map.vector(names), lo, hi)

    def log_post_x(x):
        ll = log_likelihood(p_map.with_vector(names, _from_x(x, lo, hi)), tr)
        if not np.isfinite(ll):
            return -np.inf
        return ll if log_prior_x is None else ll + float(log_prior_x(x))

    out = laplace_draws(log_post_x, x0, n_draws=n_draws, seed=seed,
                        rel_step=rel_step)
    out["names"] = names
    out["theta"] = np.array([_from_x(xi, lo, hi) for xi in out["x"]])
    out["lo"], out["hi"] = lo, hi
    out["log_lik"] = np.array([log_likelihood(
        p_map.with_vector(names, th), tr) for th in out["theta"]])
    out["tr"] = tr
    out["p_map"] = p_map
    return out


# ------------------------------------------------------------------
# 3. 后验预测检验（PPC）
# ------------------------------------------------------------------
#: PPC 统计量清单：键 = 名称，(观测 → 标量) 的取法在 `ppc_table` 里
PPC_STATS = ("n_obs", "omission_rate", "acc", "rt_p10", "rt_p25", "rt_p50",
             "rt_p75", "rt_p90", "rt_p50_correct", "rt_p50_error",
             "rt_lt_T_rate", "worst_cell_omission")

#: 分单元 PPC 的划分维度——主计划 Stage 8 点名要求
#: 「PPC（分位数、正确/错误 RT、timeout、**Self/Other × Match/Nonmatch**）」。
#: 全局 12 项统计量会**把单元间的差异平均掉**：一个在 Self 条件下系统性高估
#: 未响应率、在 Other 条件下低估的模型，全局 `omission_rate` 可能恰好落回带内。
PPC_CELL_KEYS = ("is_self", "is_match")

#: 每个单元报的量（比全局少，避免单元内样本量小导致的抖动）
CELL_STATS = ("n_obs", "omission_rate", "acc", "rt_p50", "rt_lt_T_rate")


def _cell_label(is_self: int, is_match: int) -> str:
    """把 (Self/Other, Match/Nonmatch) 两个布尔量拼成人类可读的单元名。"""
    return f"{'Self' if int(is_self) else 'Other'}-{'Match' if int(is_match) else 'Nonmatch'}"


def _select(tr: dict, mask: np.ndarray) -> dict:
    """按布尔掩码切一份数据集；标量值原样保留，等长数组按掩码取值。"""
    out = {}
    for k, v in tr.items():
        a = np.asarray(v)
        out[k] = a[mask] if a.ndim >= 1 and a.shape[0] == mask.size else v
    return out


def _cell_stats_of(tr: dict) -> dict:
    """按 Self/Other × Match/Nonmatch 切片，逐单元算 `CELL_STATS`。

    Returns
    -------
    dict: ``{单元名: {统计量: 值}}``；缺 `is_self`/`is_match` 时返回空 dict
          （调用方据此退化为"只有全局 PPC"）。
    """
    if not all(k in tr for k in PPC_CELL_KEYS):
        return {}
    n = np.asarray(tr["rt"], dtype=float).size
    if n == 0:
        return {}
    is_self = np.asarray(tr["is_self"], dtype=int)
    is_match = np.asarray(tr["is_match"], dtype=int)
    out = {}
    for s in np.unique(is_self):
        for m in np.unique(is_match):
            mask = (is_self == s) & (is_match == m)
            if not np.any(mask):
                continue
            full = _stats_of(_select(tr, mask))
            out[_cell_label(s, m)] = {k: full.get(k, np.nan) for k in CELL_STATS}
    return out


def _stats_of(tr: dict) -> dict:
    """把一份（观测或模拟的）数据集压成 PPC 统计量表。

    ``tr`` 需要 ``rt``/``side``/``omission``，可含 ``is_match``（正确性用）。
    """
    rt = np.asarray(tr["rt"], dtype=float)
    om = np.asarray(tr["omission"], dtype=float).astype(bool)
    ok = np.isfinite(rt) & (~om)
    rt_ok = rt[ok]
    d = {"n_obs": float(rt.size),
         "omission_rate": float(np.mean(om)) if rt.size else np.nan}
    if rt_ok.size:
        q = np.percentile(rt_ok, [10, 25, 50, 75, 90])
        d.update({"rt_p10": q[0], "rt_p25": q[1], "rt_p50": q[2],
                  "rt_p75": q[3], "rt_p90": q[4]})
    else:
        d.update({k: np.nan for k in ("rt_p10", "rt_p25", "rt_p50",
                                      "rt_p75", "rt_p90")})
    # 正确率：side == is_match（1 = 上边界 = Match）
    if "is_match" in tr and rt.size:
        side = np.asarray(tr["side"], dtype=int)
        m = np.asarray(tr["is_match"], dtype=int)
        d["acc"] = float(np.mean(side[ok] == m[ok])) if np.any(ok) else np.nan
    else:
        d["acc"] = np.nan
    for tag, sel in (("correct", ok & (np.asarray(tr.get("side", np.zeros(rt.size)),
                                                  dtype=int) ==
                                       np.asarray(tr.get("is_match", np.zeros(rt.size)),
                                                  dtype=int))),
                     ("error", ok & (np.asarray(tr.get("side", np.zeros(rt.size)),
                                                dtype=int) !=
                                     np.asarray(tr.get("is_match", np.zeros(rt.size)),
                                                dtype=int)))):
        v = rt[sel]
        d["rt_p50_" + tag] = float(np.median(v)) if v.size else np.nan
    # RT < T 的比例（主计划点名的关键量）
    if "T" in tr and rt_ok.size:
        T = np.asarray(tr["T"], dtype=float)[ok]
        d["rt_lt_T_rate"] = float(np.mean(rt_ok < T))
    else:
        d["rt_lt_T_rate"] = np.nan
    # 最差 (T,W) 单元的未响应率——只看最大未响应率，不依赖单元命名
    if "T" in tr and "W" in tr and rt.size:
        T = np.asarray(tr["T"], dtype=float)
        W = np.asarray(tr["W"], dtype=float)
        key = T * 1000.0 + W                       # 可哈希的单元标识
        worst = 0.0
        for k in np.unique(key):
            sel = key == k
            worst = max(worst, float(np.mean(om[sel])))
        d["worst_cell_omission"] = worst
    else:
        d["worst_cell_omission"] = np.nan
    return d


def sample_ppc(design: dict, p: MappingParams, rng: np.random.Generator,
               sampler: Callable | None = None) -> dict:
    """从 ``p`` 生成一份后验预测数据集（默认用 `simulate.simulate_subject`）。

    返回值把**设计列**（`T`/`W`/`is_self`/`is_match`/`P`）与观测列
    （`rt`/`side`/`omission`）合并在一起，这样 `_stats_of` 才能算
    `RT<T` 与分单元未响应率——`simulate_subject` 自己不回填设计列。
    """
    sampler = sampler or simulate_subject
    s = dict(sampler(design, p, rng))
    out = {k: np.asarray(v) for k, v in design.items()}
    out.update({k: np.asarray(v) for k, v in s.items()})
    return out


def _aggregate_rows(obs: dict, sims: list[dict], stats, alpha: float,
                    key: str | None = None) -> list[dict]:
    """把「观测一份 + 模拟 B 份」的统计量表聚合成 PPC 行。

    ``key`` 为 None 时对 ``stats`` 里每个统计量聚合成一行；给定时
    （如 ``"cell"``）则先按键展开，每 (键, 统计量) 一行。
    """
    def mk(label_kv: dict, stat: str, pool: list[dict], o) -> dict:
        # ⚠️ 必须显式传 pool 与 o：分单元时它们分别是"该单元的模拟统计量"与
        # "该单元的观测统计量"，闭包里的 sims/obs 是整张表（键为单元名），
        # 直接取 r.get(stat) 会全部落成 NaN ⇒ 每一行的 ok 都是 None（静默通过）。
        vals = np.array([r.get(stat, np.nan) for r in pool], dtype=float)
        vals = vals[np.isfinite(vals)]
        base = {**label_kv, "stat": stat, "obs": o}
        if vals.size == 0 or not np.isfinite(o):
            return {**base, "mean": np.nan, "sd": np.nan, "lo": np.nan,
                    "hi": np.nan, "p_ppc": np.nan, "ok": None}
        lo, hi = np.percentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        p_two = 2.0 * min(float(np.mean(vals <= o)), float(np.mean(vals >= o)))
        return {**base, "mean": float(np.mean(vals)),
                "sd": float(np.std(vals, ddof=1)), "lo": float(lo),
                "hi": float(hi), "p_ppc": float(min(p_two, 1.0)),
                "ok": bool(lo <= o <= hi)}

    rows = []
    if key is None:
        return [mk({}, s, sims, obs.get(s, np.nan)) for s in stats]
    for label in sorted(obs):
        sub = [r[label] for r in sims if label in r]
        if not sub:
            continue
        o_cell = obs[label]
        rows.extend(mk({key: label}, s, sub, o_cell.get(s, np.nan)) for s in stats)
    return rows


def ppc_table(obs_tr: dict, design: dict, draws: dict,
              n_rep_draw: int = 0, seed: int = 0, sampler: Callable | None = None,
              n_rep_sim: int = 1, alpha: float = 0.05,
              with_cells: bool = True) -> dict:
    """对每条后验抽样生成一份预测数据，算统计量，再看观测值落在何处。

    ``p_ppc`` = 预测分布中**落在观测值两侧**的尾部概率（双侧）：
    值接近 0 或 1 说明模型系统性地偏离观测；0.025–0.975 是常用接受带。

    ``with_cells=True``（默认）时**用同一批预测数据**额外给出
    Self/Other × Match/Nonmatch 的分单元 PPC（``res["cell_rows"]``），
    不额外增加模拟成本。全局统计量会把单元间差异平均掉，必须两者都看。

    Returns
    -------
    dict: ``rows``（每个统计量一行：obs / 均值 / SD / 2.5% / 97.5% / p_ppc /
          是否落在接受带）、``cell_rows``（同上，多一列 ``cell``）、
          ``n_sim``、``theta_used``、``alpha``。
    """
    names = draws["names"]
    base = draws["p_map"]
    theta = np.atleast_2d(draws["theta"])
    n_sim = theta.shape[0] if n_rep_draw <= 0 else int(n_rep_draw)
    idx = np.arange(theta.shape[0])
    if n_sim < theta.shape[0]:
        idx = np.random.default_rng(seed).choice(theta.shape[0], size=n_sim,
                                                 replace=False)
    obs = _stats_of(obs_tr)
    sim_rows = []
    cell_sim_rows: list[dict] = []
    rng = np.random.default_rng(seed)
    for k, i in enumerate(idx):
        p_i = base.with_vector(names, theta[i])
        for _ in range(max(1, n_rep_sim)):
            s = sample_ppc(design, p_i, rng, sampler=sampler)
            sim_rows.append(_stats_of(s))
            if with_cells:
                cell_sim_rows.append(_cell_stats_of(s))
    out = {"rows": _aggregate_rows(obs, sim_rows, PPC_STATS, alpha),
           "n_sim": len(sim_rows), "theta_used": idx, "alpha": alpha}
    if with_cells:
        out["cell_rows"] = _aggregate_rows(_cell_stats_of(obs_tr), cell_sim_rows,
                                           CELL_STATS, alpha, key="cell")
    return out


def _format_rows(rows: list[dict], head: str, extra: str | None = None) -> list[str]:
    """PPC 行的公用 Markdown 排版（`format_ppc` 与 `format_ppc_cells` 共用）。"""
    if extra:
        sep = f"| {extra} | 统计量 | 观测 | 预测均值 | 预测 SD | 2.5% | 97.5% | p_ppc | 落在带内 |"
        dashes = "|---|---|---|---|---|---|---|---|---|"
        cell = lambda r: f" {r.get(extra, '')} "
    else:
        sep = "| 统计量 | 观测 | 预测均值 | 预测 SD | 2.5% | 97.5% | p_ppc | 落在带内 |"
        dashes = "|---|---|---|---|---|---|---|---|"
        cell = lambda r: ""
    out = [head, sep, dashes]
    for r in rows:
        f = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.4g}"
        ok = "—" if r["ok"] is None else ("✅" if r["ok"] else "❌")
        out.append(f"|{cell(r)}`{r['stat']}` | {f(r['obs'])} | {f(r['mean'])} "
                   f"| {f(r['sd'])} | {f(r['lo'])} | {f(r['hi'])} "
                   f"| {f(r['p_ppc'])} | {ok} |")
    return out


def format_ppc(res: dict) -> str:
    """把 `ppc_table` 的结果排成 Markdown 表。"""
    out = _format_rows(res["rows"], "### 全局统计量")
    out.append("")
    out.append(f"（B = {res['n_sim']} 份后验预测数据；接受带 = "
               f"{100 * res['alpha']:.0f}% 双侧分位）")
    if res.get("cell_rows"):
        n_bad = sum(1 for r in res["cell_rows"] if r["ok"] is False)
        n_tot = sum(1 for r in res["cell_rows"] if r["ok"] is not None)
        out.append("")
        out.extend(_format_rows(res["cell_rows"],
                                "### 分单元统计量（Self/Other × Match/Nonmatch）",
                                extra="cell"))
        out.append("")
        out.append(f"（{n_bad}/{n_tot} 项落在接受带**外**；全局与分单元必须分别判读）")
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # 解析基准自检：一元高斯后验 N(1.5, 0.5²) ⇒ 拉普拉斯应当精确还原
    mu, sd = 1.5, 0.5
    f = lambda x: -0.5 * ((x[0] - mu) / sd) ** 2
    out = laplace_draws(f, np.array([mu]), n_draws=20000, seed=1)
    print(f"高斯基准：x 均值 = {out['x'][:, 0].mean():.4f}（真值 {mu}）"
          f"、SD = {out['x'][:, 0].std(ddof=1):.4f}（真值 {sd}）"
          f"、n_flipped = {out['n_flipped']}")
