# -*- coding: utf-8 -*-
"""
stage9_inner.py —— Stage 9 内环评估器（M-T3 / M-T1 双分支 + CRN 预计算表）
=========================================================================
**为什么需要它**（`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §5）
-------------------------------------------------------------------------------
Stage 8 的完整层级拟合单次评估要 420·N（M-T3）/ 544·N（M-T1）次众数搜索
（决策 D46/D47 实测），**不能进优化循环**。Stage 9 改用**期望信息量的
Cramér–Rao 下界**当内环：`1_Code/DDM_Core/design_fim.py` 实测 **0.08 s/评估**。

但 `design_fim.py` 的生成器是**恒定漂移（M-T3）**。决策 **D5**（刺激期内按键即
结束试次）把数据生成机制改成了 **M-T1**：漂移在 `t = T` 处从 `d_stim` 阶跃到
`rho · d_stim`。本模块把两条分支放进同一个入口，于是 Objective 的两项都能在
**正确的生成模型**下算。

**本模块的来源与地位（重要）**
------------------------------
M-T1 的内环仪器最早写在 `1_Code/DDM_Core/_scratch/check_mt1_fim.py`（434 行，
自检 A/B 全过）。本文件把它**提升为生产文件**，并做三件事：
1. 把 M-T3 / M-T1 **合成一个入口** `inner_eval(...)`，两条分支共享同一份
   行为诊断与同一套 CRN 种子规则 ⇒ 设计与设计之间可比；
2. Euler 抽样**按 `n_fim` 批次向量化**（`batch=True`，见 `_simulate_euler_batch`
   的实测加速比）；
3. 提供 **CRN 预计算表**（`build_table` / `save_table` / `load_table`），让优化
   内环退化为查表。

⚠️ 因此本文件对 `check_mt1_fim.py` 的数值有**可复现义务**：`batch=False` 时它与
后者逐位一致（`check_stage9_inner.py` 的 B2 组钉住这一点）。

三个限定（与 `design_fim.py` 完全相同的三条）
--------------------------------------------
1. 这是 **Cramér–Rao 下界**；真实 MLE 只会更差，`se` 不是"将会得到的 SE"。
2. 用**聚合被试**（不含被试层随机效应）；固定 n_subj 下比较单人 SE 与比较
   被试量等价。⚠️ 这与 Stage 8 的层级模型**不是同一个量**。
3. 信息量用 **OPG**（逐试次得分外积）而非 Hessian：小曲率参数（`delta_a` 的
   a 跨度只有 0.13）在二阶差分下会被浮点噪声淹没。

用法
----
    from stage9_inner import inner_eval, build_table, M_T3, M_T1

    r3 = inner_eval(T4, W3, 12, model=M_T3)                       # 恒定漂移
    r1 = inner_eval(T4, W3, 12, model=M_T1, rho=0.75)             # 两阶段漂移
    tbl = build_table(DESIGNS, model=M_T1, rho=0.75, n_fim=4)     # CRN 预计算表

命令行（冒烟 + 加速比实测）::

    python 1_Code\\AutoRA_SPE\\stage9_inner.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent            # .../1_Code/AutoRA_SPE
_DDM_DIR = _HERE.parent / "DDM_Core"
if str(_DDM_DIR) not in sys.path:
    sys.path.insert(0, str(_DDM_DIR))

from design_fim import (DESIGNS, NAMES as NAMES_EXP,  # noqa: E402
                        P_SINGLE, PRIMARY, TRUTH, check_validity)
from likelihood import (_bounds_for, fim_diagnostics, opg_information,  # noqa: E402
                        trials_from_arrays)
from mapping import WITHIN_FREE_LIN  # noqa: E402
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402
from twophase import (MASK_RHO_BOUNDS, per_trial_loglik_step,  # noqa: E402
                      simulate_euler_subject)

__all__ = [
    "M_T3", "M_T1", "RHO_NAME", "CRN_STRIDE", "DT_GEN", "SELFCHECK_TOLS",
    "param_names_for", "crn_seeds", "opg_information_step", "se_from_information",
    "inner_eval", "build_table", "save_table", "load_table", "table_key",
    "geomean_relative_se",
]

#: 两个生成模型（名字与 `stage8_run.MODELS` 一致）
M_T3 = "M-T3"     # 恒定漂移：rho == 1 的严格特例
M_T1 = "M-T1"     # 两阶段时变漂移：漂移在 t = T 处阶跃

#: M-T1 多出来的那个参数名（与 `twophase.RHO_NAME` 保持一致）
RHO_NAME = "rho"

#: CRN（共同随机数）步长。**这是本项目 CRN 的唯一规则**，取自 `design_fim.design_se`
#: 的 `np.random.default_rng(seed + 1000 * r)`。所有设计、所有臂共用同一组种子
#: ⇒ 设计之间的比较是**配对**的（差值里的生成噪声被抵消）。
CRN_STRIDE = 1000

#: Euler-Maruyama 步长。**必须标定过**：`_scratch/check_euler_dt.py` 实测以解析
#: 单阶段生成器为基准，dt=2e-4 → |Δacc| 0.0174、1e-4 → 0.0046、5e-5 → 0.0022、
#: 2.5e-5 → 0.0003；默认 5e-5 在 0.002 的精度与 6 s/被试之间取平衡。
DT_GEN = 5e-5

#: OPG 有限差分相对步长（边界宽度的比例）。
REL_STEP_FD = 1e-3

#: 自检判据（**来自实测的抽样分布，不是"应该相等"**）
SELFCHECK_TOLS = {
    "mt3_vs_design_fim": 1e-12,   # M-T3 分支 vs design_fim.design_se（应逐位一致）
    "mt1_vs_mt3_rho1": 0.02,      # rho=1 同数据上 M-T1(rho 固定) vs M-T3（相对差）
    "mt1_vs_scratch": 1e-12,      # M-T1 batch=False vs _scratch/check_mt1_fim.py
}


# ------------------------------------------------------------------
# 参数集与 CRN 种子
# ------------------------------------------------------------------
def param_names_for(param_set: str = "exp") -> list[str]:
    """把参数集名字翻成参数名列表。

    ``"exp"`` = `design_fim.NAMES`，**9 个**被试内参数（与 `design_fim.py` 排出的
    9 设计名次可比）；``"lin"`` = `mapping.WITHIN_FREE_LIN`，**8 个**（2026-10 加
    `dz_S` 前为 7 个；= 定稿文档
    声明要用的分析模型 `shape_model="lin"`，把 `tau_T`/`tau_a` 当已知固定值）。

    ⚠️ Stage 9 的 Objective (A) 项用的是 **D24 确证集 `C6`**（6 个，决策 D49），
    它是这里的 `param_set` 的一个子集，不是第三套参数集。
    """
    if param_set == "exp":
        return list(NAMES_EXP)
    if param_set == "lin":
        return list(WITHIN_FREE_LIN)
    raise ValueError(f"param_set 只能是 'exp' 或 'lin'，收到 {param_set!r}")


def crn_seeds(seed: int = 0, n_fim: int = 4) -> list[int]:
    """CRN 种子组：``seed + CRN_STRIDE * k``，k = 0..n_fim-1。"""
    return [int(seed) + CRN_STRIDE * k for k in range(int(n_fim))]


# ------------------------------------------------------------------
# 似然 / 信息量
# ------------------------------------------------------------------
def _per_trial_loglik(p, tr: dict, names: list[str], model: str, rho):
    """按生成模型选逐试次对数似然。**这是两条分支唯一的真正分岔点。**"""
    if model == M_T3:
        return per_trial_loglik(p, tr)
    return per_trial_loglik_step(p, tr, float(rho))


def opg_information_step(tr: dict, p, rho: float, names: list[str],
                         rel_step: float = REL_STEP_FD,
                         include_rho: bool = True):
    """M-T1 的 OPG 期望信息量（把 ``rho`` 当成第 K+1 个参数一起做有限差分）。

    ``include_rho=True``（默认）参数向量 = (K 个被试内参数, rho)。
    ``include_rho=False`` 只对 K 个被试内参数求差分、``rho`` **固定在给定值** ——
    这是与 M-T3 做自检时必须用的形式：把 rho 一起放进去会改变其余参数的**边际**
    SE（ρ 与 `d_ref` 强相关），那不是实现错误而是**真实代价**。

    差分在**自然参数尺度**上做（步长 = 边界宽度 × `rel_step`），于是返回的协方差
    可直接开方得到参数自身单位的 SE。返回 ``(I, G)``。

    ⚠️ 本函数是从 `1_Code/DDM_Core/_scratch/check_mt1_fim.py::opg_step_information`
    提升而来，多了一个显式的 ``names`` 参数（原版读模块全局）。
    """
    names = list(names)
    lo, hi = _bounds_for(names, None)
    theta0 = p.vector(names)
    h = rel_step * (hi - lo)
    n = len(names)
    nt = int(tr["rt"].size)
    ncol = n + (1 if include_rho else 0)
    G = np.zeros((nt, ncol))

    for i in range(n):
        d = np.zeros(n)
        d[i] = h[i]
        pt_p = per_trial_loglik_step(p.with_vector(names, theta0 + d), tr, rho)
        pt_m = per_trial_loglik_step(p.with_vector(names, theta0 - d), tr, rho)
        if pt_p is None or pt_m is None:
            raise ValueError(
                f"opg_information_step: 参数 {names[i]} 在步长 {h[i]:g} 处越界；"
                f"请调小 rel_step 或检查真值是否贴近边界")
        G[:, i] = (pt_p - pt_m) / (2.0 * h[i])

    if include_rho:
        lo_r, hi_r = MASK_RHO_BOUNDS
        hr = rel_step * (hi_r - lo_r)
        # ⚠️ **两侧都要查**。`per_trial_loglik_step` 只在 `rho < 0` 时返回 None，
        # **不查上界**（实测 rho=5.0 仍返回有限值）⇒ 只靠它兜底的话，
        # rho 接近或超过 3.0 时 `rho ± hr` 会静默用到范围外的 rho，
        # 给出一个"看起来正常"的信息矩阵。生产版本必须比原型更严。
        if not (lo_r <= rho - hr and rho + hr <= hi_r):
            raise ValueError(
                f"opg_information_step: rho 在 {rho:g} ± {hr:g} 处越界"
                f"（边界 {MASK_RHO_BOUNDS}）——上界同样会被检查"
                f"（`per_trial_loglik_step` 本身不查上界）")
        pt_p = per_trial_loglik_step(p, tr, rho + hr)
        pt_m = per_trial_loglik_step(p, tr, rho - hr)
        if pt_p is None or pt_m is None:
            raise ValueError(
                f"opg_information_step: rho 在 {rho:g} ± {hr:g} 处越界"
                f"（边界 {MASK_RHO_BOUNDS}）")
        G[:, n] = (pt_p - pt_m) / (2.0 * hr)

    return G.T @ G, G


def se_from_information(I: np.ndarray) -> np.ndarray:
    """SE = sqrt(max(diag(pinv(I)), 0))。`pinv` 是**故意的**：病态设计要给大 SE，
    不是抛错；`design_fim` 用 `cond` 与 `n_bad` 另行拒收。"""
    return np.sqrt(np.maximum(np.diag(np.linalg.pinv(I)), 0.0))


# ------------------------------------------------------------------
# 数据生成
# ------------------------------------------------------------------
def _simulate_euler_batch(design: dict, truth, rho: float, seed: int,
                          n_fim: int, dt: float):
    """把 ``n_fim`` 份重复**叠进试次维**，一次 Euler 跑完。

    为什么可行：`simulate_euler_subject` 的步进循环每一步只做 O(n) 的向量运算，
    而**步数只由 t_max/dt 决定、与试次无关**；把 n 放大 n_fim 倍几乎不增加
    Python 层的循环次数，只增加每次迭代的向量长度 ⇒ 摊薄了固定开销。

    ⚠️ 代价：RNG 的消耗顺序变了，所以 `batch=True` 与 `batch=False` **不是**
    同一个 Monte Carlo 样本（两者都有效，但不是逐位同分布）。做**可复现性自检**
    时必须用 `batch=False`（见 `check_stage9_inner.py` 的 B2 组）。
    """
    big = {k: (np.tile(np.asarray(v), n_fim) if np.ndim(v) else v)
           for k, v in design.items()}
    rng = np.random.default_rng(int(seed))
    sim = simulate_euler_subject(big, truth, rho, rng, dt=dt)
    return sim, big


def _split(rng_dict: dict, n_fim: int) -> list[dict]:
    """把批次结果切回 ``n_fim`` 份。**切法必须与 `_simulate_euler_batch` 的
    `np.tile` 一致**：tile 是「整块重复」，所以切法是等长分块（不是交错）。"""
    n = np.asarray(rng_dict["rt"]).size
    m = n // n_fim
    return [{k: (np.asarray(v)[i * m:(i + 1) * m] if np.ndim(v) else v)
             for k, v in rng_dict.items() if k in ("rt", "side", "omission")}
            for i in range(n_fim)]


def _simulate_mt3(design: dict, truth, seed: int):
    """M-T3 的单份生成（与 `design_fim.design_se` 内部逐字一致）。"""
    rng = np.random.default_rng(int(seed))
    sim = simulate_subject(design, truth, rng)
    return sim, design


def _simulate_mt1_one(design: dict, truth, rho: float, seed: int, dt: float):
    """M-T1 的单份生成（与 `check_mt1_fim.py::_gen` 逐字一致）。"""
    rng = np.random.default_rng(int(seed))
    sim = simulate_euler_subject(design, truth, rho, rng, dt=dt)
    return sim, design


# ------------------------------------------------------------------
# 行为诊断（两条分支共用，保证可比）
# ------------------------------------------------------------------
def _behaviour(sim: dict, design: dict) -> tuple[float, float, float]:
    """(遗漏率, 正确率, RT 均值 ms)。**两条分支共用同一个函数**，避免
    「M-T1 与 M-T3 的遗漏率定义悄悄不同」这种不可见的不可比。"""
    om = float(np.mean(sim["omission"]))
    resp = np.asarray(sim["omission"]) == 0
    is_match = np.asarray(design["is_match"]) == 1
    side = np.asarray(sim["side"])
    ok = np.where(is_match, side == 1, side == 0)
    acc = float(np.mean(ok[resp])) if np.any(resp) else float("nan")
    rt_ms = float(np.nanmean(sim["rt"])) * 1000.0
    return om, acc, rt_ms


# ------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------
def inner_eval(T_levels, W_levels, n_rep: int, *, model: str = M_T3,
               rho: float | None = None, n_fim: int = 4, seed: int = 0,
               truth=TRUTH, param_set: str = "exp",
               param_names: list[str] | None = None, P=None,
               dt: float = DT_GEN, batch: bool = True) -> dict:
    """算一个设计点的充分统计量：预测 SE、MC 噪声带、行为诊断、相关结构。

    Parameters
    ----------
    T_levels, W_levels, n_rep :
        设计点，语义与 `simulate.build_design` 一致。⚠️ **时序口径按 D48**：
        提交前应已通过 `spe_timing_convention.assert_current_design`（本函数
        另用 `design_fim.check_validity` 复算 `W > T + 200 ms`）。
    model : ``M_T3`` / ``M_T1``
    rho : M-T1 **必须**给；M-T3 必须不给（传了会报错，避免"以为改了模型"）。
    n_fim : 独立模拟份数。CRN 种子 = ``seed + 1000 * k``。
    param_set / param_names : 参数集；给了 `param_names` 就以它为准。
    batch : M-T1 是否走批次向量化。**做可复现性自检时必须 False。**

    Returns
    -------
    dict: ``se``（K 个被试内参数的 SE）、``se_rho``（M-T3 为 nan）、``se_sd``
    （MC 噪声带）、``info_mean``、``corr``、``cond``、行为诊断与元信息。
    """
    if model not in (M_T3, M_T1):
        raise ValueError(f"model 只能是 {M_T3!r} 或 {M_T1!r}，收到 {model!r}")
    if model == M_T1 and rho is None:
        raise ValueError("model=M-T1 必须给 rho")
    if model == M_T3 and rho is not None:
        raise ValueError(f"model={M_T3} 不接受 rho（它是 rho==1 的严格特例）；"
                         f"要扫 rho 请用 model={M_T1!r}")

    names = list(param_names) if param_names is not None else param_names_for(param_set)
    P = P_SINGLE if P is None else P

    bad = check_validity(T_levels, W_levels)
    if bad:
        raise ValueError(f"设计违反 W > T + 200 ms（Exp_Design_Formal.m L22）：{bad}")

    design = build_design(P, T_levels, W_levels, n_rep)
    n_trials = int(np.asarray(design["T"]).size)
    seeds = crn_seeds(seed, n_fim)

    # ---------------- 生成 ----------------
    sims: list[dict] = []
    if model == M_T1 and batch:
        big_sim, _ = _simulate_euler_batch(design, truth, float(rho),
                                           seeds[0], n_fim, dt)
        # ⚠️ 行为诊断必须用**未平铺**的 design：批次是把同一份设计整块重复
        # n_fim 次，所以每一块的 `is_match` 与原始 design 逐位相同。
        for part in _split(big_sim, n_fim):
            sims.append((part, design))
    else:
        for sd in seeds:
            if model == M_T3:
                sims.append(_simulate_mt3(design, truth, sd))
            else:
                sims.append(_simulate_mt1_one(design, truth, float(rho), sd, dt))

    # ---------------- 信息量 ----------------
    Is, ses_i, om, acc, rt_ms = [], [], [], [], []
    K = len(names)
    for sim, des in sims:
        tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                *design_arrays(des))
        if model == M_T3:
            I, _ = opg_information(tr, names, truth)
            se_full = se_from_information(I)          # 长度 K
            se_i, se_rho_i = se_full[:K], float("nan")
        else:
            I, _ = opg_information_step(tr, truth, float(rho), names,
                                        include_rho=True)
            se_full = se_from_information(I)          # 长度 K+1（末位是 rho）
            se_i, se_rho_i = se_full[:K], float(se_full[K])
        Is.append(I)
        ses_i.append(np.concatenate([se_i, [se_rho_i]]))
        o, a, r = _behaviour(sim, des)
        om.append(o); acc.append(a); rt_ms.append(r)

    I_mean = np.mean(Is, axis=0)
    cov = np.linalg.pinv(I_mean)
    d = np.sqrt(np.maximum(np.diag(cov), 1e-300))
    se_all = np.sqrt(np.maximum(np.diag(cov), 0.0))
    ses_arr = np.asarray(ses_i)                     # (n_fim, K+1)
    # ⚠️ `cond` 与 `n_bad` **必须**与 `design_fim` 同源：Stage 9 的 Objective (D) 闸门
    #    （`cond > 1e10` / `n_bad > 0`）是照着 `design_fim` 的量写的，换成
    #    `np.linalg.cond` 会在存在负特征值时给出不同的数（SVD 用 |λ|，这里只数 λ>0）。
    fdiag = fim_diagnostics(I_mean, names)

    out = {
        "model": model, "rho": (None if model == M_T3 else float(rho)),
        "n_trials": n_trials, "n_fim": int(n_fim), "seed": int(seed), "batch": bool(batch),
        "param_names": names, "K": len(names),
        "se": se_all[:len(names)],
        "se_rho": (float("nan") if model == M_T3 else float(se_all[len(names)])),
        "se_sd": np.std(ses_arr, axis=0)[:len(names)],
        "se_rho_sd": (float("nan") if model == M_T3 else float(np.std(ses_arr[:, -1]))),
        "info_mean": I_mean,
        "corr": cov / np.outer(d, d),
        "cond": float(fdiag["cond"]),
        "n_bad": int(fdiag["n_bad"]),
        "omission": float(np.mean(om)),
        "acc": float(np.mean(acc)),
        "rt_ms": float(np.mean(rt_ms)),
        "T": T_levels, "W": W_levels, "rep": n_rep,
    }
    # 相对 SE 只对"真值"参数算（rho 的真值不是 TRUTH 的键）
    tv = np.array([truth.as_dict()[n] for n in names], dtype=float)
    out["truth_vec"] = tv
    out["relative_se"] = out["se"] / np.abs(tv)
    return out


def geomean_relative_se(res: dict, focus: list[str] | None = None) -> float:
    """相对 SE 在 ``focus`` 上的几何平均 —— Objective (A) 的原始形式。

    ⚠️ **`focus` 必须显式给**（Stage 9 用 D24 确证集 `C6`，决策 D49）：
    `design_fim.PRIMARY`（含 `beta_ST`，相对 SE 4.1–5.8）会把几何平均整个抬起来，
    使 8 个设计的可用性判定从 ✅ 翻成 ❌。不给 `focus` 时退回 `PRIMARY ∩ 参数集`
    并**在返回里没有提示**，所以调用点必须自己写清口径。
    """
    names = list(res["param_names"])
    if focus is None:
        focus = [k for k in PRIMARY if k in names]
    vals = [float(res["relative_se"][names.index(k)]) for k in focus]
    return float(np.exp(np.mean(np.log(vals))))


# ------------------------------------------------------------------
# CRN 预计算表（Stage 9 方案 §5.4）
# ------------------------------------------------------------------
def table_key(name: str, model: str, rho: float | None) -> str:
    """表键。⚠️ 结果解析用的是 ``rsplit("|", 1)``，所以**设计名里不能有 `|`**。"""
    r = "-" if rho is None else f"{float(rho):.4f}"
    return f"{name}|{model}|rho={r}"


def build_table(designs: dict | None = None, *, model: str = M_T3,
                rho: float | None = None, n_fim: int = 4, seed: int = 0,
                param_set: str = "exp", param_names: list[str] | None = None,
                rho_list: list[float] | None = None, batch: bool = True,
                verbose: bool = True) -> dict:
    """预计算 ``design × rho`` 的充分统计量表。

    ``rho_list`` 非 None 时对每个 rho 各算一遍（M-T1）；否则只算 ``rho``。
    表里的每个格子都是**同一个 seed 组**（CRN），所以格子之间的差是配对的。
    """
    designs = DESIGNS if designs is None else designs
    if model == M_T3:
        rhos = [None]
    else:
        rhos = list(rho_list) if rho_list is not None else [rho]
        if any(r is None for r in rhos):
            raise ValueError("model=M-T1 的 rho_list 不能含 None")

    names = list(param_names) if param_names is not None else param_names_for(param_set)
    cells: dict[str, dict] = {}
    t_start = time.time()
    for name, (T, W, r) in designs.items():
        if check_validity(T, W):
            if verbose:
                print(f"  ⚠️ {name} 违反 W > T+200ms（跳过）", flush=True)
            continue
        for rr in rhos:
            t0 = time.time()
            res = inner_eval(T, W, r, model=model, rho=rr, n_fim=n_fim,
                             seed=seed, param_names=names, batch=batch)
            cells[table_key(name, model, rr)] = res
            if verbose:
                print(f"  已算 {name:34s} rho={('-' if rr is None else f'{rr:.2f}'):>4s}  "
                      f"试次={res['n_trials']:4d}  遗漏={res['omission']:.3f}  "
                      f"RT={res['rt_ms']:.0f}ms  "
                      f"g6={geomean_relative_se(res):.3f}  ({time.time()-t0:.1f}s)",
                      flush=True)

    meta = {
        "model": model, "n_fim": int(n_fim), "seed": int(seed),
        "batch": bool(batch), "param_names": names, "rho_list": rhos,
        "crn_stride": CRN_STRIDE, "dt_gen": DT_GEN,
        "truth": {k: float(v) for k, v in TRUTH.as_dict().items()
                  if isinstance(v, (int, float))},
        "n_cells": len(cells), "seconds": time.time() - t_start,
    }
    return {"meta": meta, "cells": cells}


def save_table(table: dict, path: str | Path) -> Path:
    """存成 ``.npz``（数组）+ 同名 ``.json``（meta + 键清单）。"""
    path = Path(path)
    if path.suffix != ".npz":
        path = path.with_suffix(".npz")
    arrays: dict[str, np.ndarray] = {}
    keys: list[str] = []
    for key, res in table["cells"].items():
        keys.append(key)
        flat = {}
        for k, v in res.items():
            if isinstance(v, np.ndarray):
                arrays[f"{key}::{k}"] = v
            elif isinstance(v, (int, float, str, bool)) or v is None:
                flat[k] = v
            elif isinstance(v, (list, tuple)):
                flat[k] = list(v)
        arrays[f"{key}::__scalars__"] = np.array([json.dumps(
            _jsonable(flat), ensure_ascii=False)])
    np.savez_compressed(path, **arrays)
    meta_path = path.with_suffix(".json")
    meta_path.write_text(json.dumps(
        {"meta": _jsonable(table["meta"]), "keys": keys},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    return x


def load_table(path: str | Path) -> dict:
    """读回 `save_table` 写的表，并把 JSON 里的列表还原成 ndarray。"""
    path = Path(path)
    if path.suffix != ".npz":
        path = path.with_suffix(".npz")
    meta_all = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    z = np.load(path, allow_pickle=False)
    cells: dict[str, dict] = {}
    for key in meta_all["keys"]:
        scal = json.loads(str(z[f"{key}::__scalars__"][0]))
        res: dict = {}
        for k, v in scal.items():
            res[k] = v
        for arr_key in z.files:
            if arr_key.startswith(f"{key}::") and not arr_key.endswith("::__scalars__"):
                k = arr_key.split("::", 1)[1]
                res[k] = z[arr_key]
        cells[key] = res
    return {"meta": meta_all["meta"], "cells": cells}


# ------------------------------------------------------------------
# 冒烟 + 加速比实测
# ------------------------------------------------------------------
if __name__ == "__main__":
    T4 = (0.03333, 0.08333, 0.14999, 0.24998)
    W3 = (0.79998, 1.1999, 1.7999)
    print("=" * 100)
    print("stage9_inner.py 冒烟测试（n_fim=1，只为跑通与报加速比；完整自检见 check_stage9_inner.py）")
    print("=" * 100)

    r3 = inner_eval(T4, W3, 12, model=M_T3, n_fim=1)
    print(f"  M-T3        试次={r3['n_trials']:4d}  遗漏={r3['omission']:.3f}  "
          f"正确率={r3['acc']:.3f}  RT={r3['rt_ms']:.0f}ms  "
          f"g6={geomean_relative_se(r3, ['d_ref','beta_T','beta_S','a_ref','delta_a','t0']):.3f}")

    t0 = time.time()
    r1 = inner_eval(T4, W3, 12, model=M_T1, rho=0.75, n_fim=1)
    t_one = time.time() - t0
    print(f"  M-T1(逐份)  试次={r1['n_trials']:4d}  遗漏={r1['omission']:.3f}  "
          f"正确率={r1['acc']:.3f}  RT={r1['rt_ms']:.0f}ms  "
          f"se(rho)={r1['se_rho']:.4f}  逐份耗时={t_one:.1f}s")

    t0 = time.time()
    rb = inner_eval(T4, W3, 12, model=M_T1, rho=0.75, n_fim=4, batch=True)
    t_batch4 = time.time() - t0
    t0 = time.time()
    rn = inner_eval(T4, W3, 12, model=M_T1, rho=0.75, n_fim=4, batch=False)
    t_seq4 = time.time() - t0
    print(f"\n  批次向量化加速比（n_fim=4）：逐份 {t_seq4:.1f}s → 批次 {t_batch4:.1f}s "
          f"= **{t_seq4 / max(t_batch4, 1e-9):.2f}×**")
    print(f"  （逐份 n_fim=4 与批次 n_fim=4 的 se 相对差 = "
          f"{np.max(np.abs(rb['se'] - rn['se']) / np.maximum(rn['se'], 1e-300)):.3%}"
          f"；两者不是同一个 MC 样本，见 `_simulate_euler_batch` 的说明）")
    print("\n  ✅ 冒烟通过（完整自检请跑 check_stage9_inner.py）")
