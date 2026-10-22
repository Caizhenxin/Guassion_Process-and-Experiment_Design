# -*- coding: utf-8 -*-
"""
simulate.py —— 从设计表 + 真值参数生成被试数据（Stage 3/4 共用）
================================================================
与 `likelihood.py` 共用同一套映射（`mapping.trial_params`），保证
"生成"与"拟合"用的是同一个模型——否则参数恢复没有意义。

⚠️ 生成的工件必须包含**真值文件**（研究计划 §7.3）：
`simulate_subject` 返回的 dict 里含 ``truth`` 字段（逐试次真实的 v/a/z/t0），
**拟合代码不得读取它**，它只用于参数恢复与模型恢复。
"""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr, ndtri

from mapping import PARAM_BOUNDS, MappingParams, trial_params
from wfpt import sample_wfpt

__all__ = ["build_design", "design_arrays", "simulate_subject",
           "SUBJECT_SD", "draw_subject_params"]

_DESIGN_KEYS = ("P", "T", "W", "is_self", "is_match")

#: 被试水平随机效应的标准差（**群体层参数的真值不受影响**）。
#: 为什么必须有：若所有被试共用同一套参数，组间回归就是确定性的，恢复会
#: 不真实地容易，Stage 4 会高估设计的识别力。
#:
#: ``dz_S = 0.06``（2026-10-22 加入）：SPE 的**判据通道**必须有被试间变异，
#: 否则层次模型的组间方差真值为 0、不可估。取值依据：SDT 拆解给群体
#: ``Δc = −0.239 ⇔ Δ(z/a) ≈ 0.12``（`5_Reference/02_方法学审查/生成模型编码约定审查_20260930.md:81-83`），
#: 取个体 SD 为其一半。
#:
#: ⚠️ **加键会改变随机流**（每名被试多抽一个正态），因此本文件与
#: `_scratch/` 里 2026-10-22 之前的历史日志**不再逐位可复现**。要复现旧流，
#: 显式传 ``sd={**SUBJECT_SD, "dz_S": 0.0}``——`draw_subject_params` 会跳过
#: ``s <= 0`` 的键，随机数消耗与加入前完全一致。
SUBJECT_SD = {"d_ref": 0.15, "beta_S": 0.10, "a_ref": 0.25, "t0": 0.030,
              "dz_S": 0.06}

#: `draw_subject_params` 的两种抽样模式（见该函数 docstring）。
SUBJECT_MODE_CLIP = "clip"
SUBJECT_MODE_TRUNCATE = "truncate"


def _truncated_normal(mu: float, sigma: float, lo: float, hi: float,
                      rng: np.random.Generator) -> float:
    """恰在 ``[lo, hi]`` 上的截断正态（逆 CDF 法，抽一次即得，无重抽循环）。

    ``mode="truncate"`` 用的就是它。为什么不用「越界重抽」：重抽的抽数随机，
    会让「同一个种子」在不同平台上可能给出不同的被试参数；逆 CDF 固定只抽 1 个
    均匀数，流是与平台无关的。
    """
    a = float(ndtr((lo - mu) / sigma))
    b = float(ndtr((hi - mu) / sigma))
    if not np.isfinite(a) or not np.isfinite(b) or b <= a:
        # 截断区间落在正态的远尾（概率质量 ≈ 0）⇒ 退化为取最近端点
        return float(min(max(mu, lo), hi))
    u = float(rng.uniform(a, b))
    u = min(max(u, np.finfo(float).tiny), 1.0 - np.finfo(float).eps)
    return float(mu + sigma * float(ndtri(u)))


def draw_subject_params(p_group: MappingParams, rng: np.random.Generator,
                        sd: dict | None = None,
                        mode: str = SUBJECT_MODE_CLIP) -> MappingParams:
    """从群体参数抽一名被试的参数（正态随机效应，截断到物理边界内）。

    两种模式（`mode`）：

    ``"clip"``（**默认，与历史日志逐位一致**）
        先抽正态、越界者用 `np.clip` **压到界值本身**。这是 **clipping 而非
        truncation**：边界上因此有一个概率堆（`SUBJECT_SD["d_ref"] = 0.15`、
        P=0 组真值均值 0.4902 距下界 0.20 仅 1.97 SD ⇒ 约 2.4% 的 P=0 被试真值
        被压在下界上）。好处是真值**保证落在拟合箱体内**，故界不会让真值不可达。
        ⚠️ 这是**默认值**，不要改——改了就无法复现 `_scratch/` 里的历史日志。

    ``"truncate"``（**新工作的推荐模式**）
        恰在界内的截断正态（逆 CDF，`_truncated_normal`）。概率堆消失，代价是
        真值的**边际 SD 略被压缩**（例如 `mu=0.4902, sigma=0.15, lo=0.20` 时
        0.15 → 0.1449）。

    两种模式的差别量化见 `_scratch/check_bounds_trunc.py`。
    """
    if mode not in (SUBJECT_MODE_CLIP, SUBJECT_MODE_TRUNCATE):
        raise ValueError(f"mode 只能是 'clip' 或 'truncate'，收到 {mode!r}")
    sd = SUBJECT_SD if sd is None else sd
    kw = {}
    for k, s in sd.items():
        if s <= 0:
            continue
        lo, hi = PARAM_BOUNDS[k]
        mu = float(getattr(p_group, k))
        if mode == SUBJECT_MODE_CLIP:
            kw[k] = float(np.clip(mu + rng.normal(0.0, s), lo, hi))
        else:
            kw[k] = _truncated_normal(mu, s, lo, hi, rng)
    return p_group.replace(**kw) if kw else p_group


def build_design(P, T_list, W_list, n_rep: int,
                 self_levels=(0, 1), match_levels=(0, 1)) -> dict:
    """构造完整因子设计表（每单元 ``n_rep`` 次重复）。

    返回 dict of ndarray，字段与 `likelihood.trials_from_arrays` 兼容
    （不含观测列 rt/side/omission）。
    """
    rows = []
    for T in np.atleast_1d(T_list):
        for W in np.atleast_1d(W_list):
            for s in self_levels:
                for m in match_levels:
                    for _ in range(n_rep):
                        rows.append((P, float(T), float(W), int(s), int(m)))
    arr = np.array(rows, dtype=float)
    out = {k: arr[:, i] for i, k in enumerate(_DESIGN_KEYS)}
    out["is_self"] = out["is_self"].astype(float)
    out["is_match"] = out["is_match"].astype(int)
    return out


def design_arrays(design: dict):
    """把设计 dict 拆成 `trials_from_arrays` 需要的参数序列。"""
    return (design["P"], design["T"], design["W"],
            design["is_self"], design["is_match"])


def simulate_subject(design: dict, p: MappingParams, rng: np.random.Generator,
                     t_max: float | None = None) -> dict:
    """生成一名被试的观测数据。

    Returns
    -------
    dict: ``rt``（秒，未响应为 NaN）、``side``（1 上 / 0 下）、``omission``、
          ``truth``（逐试次真实 v/a/z/t0，**仅供恢复检验使用**）
    """
    tp = trial_params(design, p)
    v, a, z, t0 = tp["v"], tp["a"], tp["z"], tp["t0"]
    W = np.asarray(design["W"], dtype=float)
    n = v.size

    rt = np.full(n, np.nan)
    side = np.zeros(n, dtype=int)
    omission = np.zeros(n, dtype=int)

    # 同一设计单元内 (v, a, z) 相同 → 按唯一参数组批量抽样
    key = np.column_stack([v, a, z])
    uniq, inv = np.unique(np.round(key, 10), axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()

    for gi in range(uniq.shape[0]):
        idx = np.flatnonzero(inv == gi)
        if idx.size == 0:
            continue
        vv, aa, zz = (float(x) for x in uniq[gi])
        tau, b = sample_wfpt(vv, aa, zz, idx.size, rng, t_max=t_max)
        rt_g = tau + t0
        om = (~np.isfinite(rt_g)) | (rt_g > W[idx])
        rt[idx] = np.where(om, np.nan, rt_g)
        side[idx] = np.where(om, 0, b)
        omission[idx] = om.astype(int)

    return {
        "rt": rt, "side": side, "omission": omission,
        "truth": {"v": v, "a": a, "z": z, "t0": np.full(n, t0)},
    }
