# -*- coding: utf-8 -*-
"""
spe_runner.py —— AutoRA-SPE 的合成 Experiment Runner
=====================================================
职责：给定一个设计点 (P, T, W)，产生**试次级**数据（虚拟被试）。

在 AutoRA 架构中的位置
----------------------
    Experimentalist（采集函数）── 提出 (P,T,W) ──▶ **Runner（本模块）**
                                                      │
                                                      ▼
                                            Theorist（估计/模型比较）
                                                      │
                                                      ▼
                                            冻结 Objective ──▶ 下一轮

本模块**只做前向仿真**，不含任何"模型拟合"或"打分"逻辑——那是 Theorist 与
冻结 Objective 的职责（分离是为了防止奖励劫持：Runner 与 Objective 必须能被
独立审计）。

设计要点
--------
* 仿真统一调用 `sim_utils.simulate_trials`（与论文配置 C 的验证管线**同一个**仿真器，
  避免出现第二个"事实来源"）。
* 时序与门控统一来自 `spe_design_model`（deadline = T+200+W；窗口门控）。
* 被试水平变异由 `DesignParams` 的 `sd_*` 控制，逐被试抽样后**跨条件固定**
  （同一虚拟被试在不同条件下 v_base 相对群体的偏移是同一份抽样），
  这样"被试内对比"与"被试间对比"的统计结构才正确。
* 输出保留 `omission` 原始列（未做 Censor/Drop 处理），由下游决定口径。

⚠️ 本 runner 是"已知真值的模拟世界"，**不是**"对真实数据的拟合"。
   任何以它为基础的结论都受 truth ensemble 的设定约束（见 README）。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from spe_design_model import (
    DEFAULT_PARAMS,
    DesignParams,
    apply_window_gate,
    design_to_params,
    simulate_trials,
    TRIALS_PER_IDENTITY,
)

__all__ = ["draw_subject_params", "run_design", "run_design_set", "summarize_design_set"]


# ------------------------------------------------------------------
# 虚拟被试抽样
# ------------------------------------------------------------------
def draw_subject_params(design: dict, n_subjects: int, params: DesignParams,
                        rng: np.random.Generator) -> dict:
    """为一个设计点抽 n_subjects 名虚拟被试的 DDM 参数（正态抖动，带边界截断）。

    Returns
    -------
    dict: v_self / v_stranger / a / t0 / z，各为 shape (n_subjects,) 的数组
    """
    def _jitter(mean, sd, lo=None, hi=None):
        x = rng.normal(mean, sd, size=n_subjects) if sd > 0 else np.full(n_subjects, mean)
        if lo is not None or hi is not None:
            x = np.clip(x, lo, hi)
        return x

    v_base = _jitter(design["v_base"], params.sd_v_base)
    # 身份效应为加性：ΔI 与被试的 v_base 独立抽样
    delta = _jitter(design["delta_identity"], params.sd_delta_identity)
    return {
        "v_base": v_base,
        "delta_identity": delta,
        "v_self": v_base + 0.5 * delta,
        "v_stranger": v_base - 0.5 * delta,
        "a": _jitter(design["a"], params.sd_a, lo=0.2),
        "t0": _jitter(design["t0"], params.sd_t0, lo=0.05),
        "z": _jitter(design["z"], params.sd_z_ratio, lo=0.05, hi=0.95),
    }


# ------------------------------------------------------------------
# 单设计点仿真
# ------------------------------------------------------------------
def run_design(P, T_ms, W_ms, n_subjects: int = 20,
               params: DesignParams | None = None,
               seed: int | None = None,
               trials_per_identity: int = TRIALS_PER_IDENTITY,
               rng: np.random.Generator | None = None,
               subject_params: dict | None = None,
               design_id: str | None = None) -> pd.DataFrame:
    """仿真一个设计点（一个条件）下的全部试次。

    Args
    ----
    P, T_ms, W_ms : 设计点
    n_subjects    : 虚拟被试数
    params        : 机制参数（默认 DEFAULT_PARAMS）
    seed          : 若给定且 rng 为 None，则用该种子建 rng（保证可复现）
    subject_params: 直接给定逐被试参数（用于"同一批被试跑多个条件"的配对设计）；
                    给定后忽略 n_subjects 与抖动抽样
    design_id     : 附加到输出行的标签

    Returns
    -------
    DataFrame，列：subj_idx, rt, response, identity, omission,
                    P, T_ms, W_ms, M_ms, deadline_s, window_open_s, design_id
    其中 rt 为**秒**（自刺激起点计，已过窗口门控；omission 行 rt 为 NaN）。
    """
    p = params or DEFAULT_PARAMS
    if rng is None:
        rng = np.random.default_rng(seed)

    des = design_to_params(P, T_ms, W_ms, p)
    sp = subject_params if subject_params is not None else draw_subject_params(des, n_subjects, p, rng)
    n_subjects = len(sp["a"])

    frames = []
    for s in range(n_subjects):
        for identity, v_key in [(0, "v_stranger"), (1, "v_self")]:
            v_mean = sp[v_key][s]
            # 注意失败（lapse）：该试次漂移率置零（无证据积累）。
            # 机制化处理，而非直接指定遗漏概率——见 DesignParams.lapse_prob 的说明。
            if p.lapse_prob > 0:
                lapse_mask = rng.random(trials_per_identity) < p.lapse_prob
                v_trial = np.where(lapse_mask, 0.0, v_mean)
            else:
                lapse_mask = np.zeros(trials_per_identity, dtype=bool)
                v_trial = v_mean
            sim = simulate_trials(
                v=v_trial, a=sp["a"][s], t0=sp["t0"][s], z=sp["z"][s],
                deadline=des["deadline_s"], n_trials=trials_per_identity, rng=rng,
            )
            rt = apply_window_gate(sim["rt"], sim["response"], sim["omission"], T_ms)
            frames.append(pd.DataFrame({
                "subj_idx": s,
                "rt": rt,
                "response": sim["response"],
                "identity": identity,
                "omission": sim["omission"],
                "lapse": lapse_mask.astype(int),
            }))

    df = pd.concat(frames, ignore_index=True)
    df["P"] = float(P)
    df["T_ms"] = float(T_ms)
    df["W_ms"] = float(W_ms)
    df["M_ms"] = des["M_ms"]
    df["deadline_s"] = des["deadline_s"]
    df["window_open_s"] = des["window_open_s"]
    df["design_id"] = design_id if design_id is not None else f"P{P:g}_T{T_ms:g}_W{W_ms:g}"
    return df


# ------------------------------------------------------------------
# 多设计点仿真
# ------------------------------------------------------------------
def run_design_set(designs: pd.DataFrame | list[dict], n_subjects: int = 20,
                   params: DesignParams | None = None,
                   seed: int = 20260917,
                   trials_per_identity: int = TRIALS_PER_IDENTITY,
                   paired_subjects: bool = False) -> pd.DataFrame:
    """仿真一组设计点。

    Args
    ----
    designs : DataFrame（需含 P / T_ms / W_ms）或 list[dict]
    paired_subjects : True 时**同一批虚拟被试**依次完成所有设计点
        （被试内设计，用于检验"P 由被试间因子改为被试内因子"能否解除
          P 与条件的嵌套混淆——这是审计报告 §2.1 的核心建议）。
        ⚠️ 注意：配对只配对 v_base / a / t0 / z 的**个体偏移**，
        ΔI 在每个条件下独立抽（当前世界假设：身份效应不随设计点系统变化）。

    Returns
    -------
    DataFrame（试次级），含 run_design 的全部列。
    """
    p = params or DEFAULT_PARAMS
    if isinstance(designs, pd.DataFrame):
        rows = designs.to_dict("records")
    else:
        rows = list(designs)

    rng = np.random.default_rng(seed)
    shared = None
    if paired_subjects:
        # 用第一个设计点抽出个体偏移，之后所有条件复用同一批偏移
        d0 = design_to_params(rows[0]["P"], rows[0]["T_ms"], rows[0]["W_ms"], p)
        shared = draw_subject_params(d0, n_subjects, p, rng)

    frames = []
    for row in rows:
        if paired_subjects:
            d = design_to_params(row["P"], row["T_ms"], row["W_ms"], p)
            # 复用个体偏移量（相对群体均值的偏离），但只复用与设计无关的部分
            des_sp = {
                "v_self": d["v_self"] + (shared["v_base"] - shared["v_base"].mean()),
                "v_stranger": d["v_stranger"] + (shared["v_base"] - shared["v_base"].mean()),
                "a": shared["a"] - shared["a"].mean() + d["a"],
                "t0": shared["t0"] - shared["t0"].mean() + d["t0"],
                "z": np.clip(shared["z"] - shared["z"].mean() + d["z"], 0.05, 0.95),
            }
            df = run_design(row["P"], row["T_ms"], row["W_ms"], p=p, rng=rng,
                            subject_params=des_sp, trials_per_identity=trials_per_identity,
                            design_id=row.get("design_id"))
        else:
            df = run_design(row["P"], row["T_ms"], row["W_ms"], n_subjects=n_subjects, p=p,
                            rng=rng, trials_per_identity=trials_per_identity,
                            design_id=row.get("design_id"))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ------------------------------------------------------------------
# 汇总
# ------------------------------------------------------------------
def summarize_design_set(df: pd.DataFrame) -> pd.DataFrame:
    """把试次级输出汇总为条件 × 身份的观测统计（与 `sim_utils.behavior_stats` 同口径）。"""
    out = []
    for (did, identity), sub in df.groupby(["design_id", "identity"], sort=False):
        responded = sub["omission"] == 0
        correct = (sub["response"] == 1) & responded
        rt_ms = sub.loc[correct, "rt"] * 1000.0
        out.append({
            "design_id": did,
            "identity": "self" if identity == 1 else "stranger",
            "P": sub["P"].iloc[0], "T_ms": sub["T_ms"].iloc[0], "W_ms": sub["W_ms"].iloc[0],
            "n_trials": len(sub),
            "omission_rate": float(1 - responded.mean()),
            "acc_all": float(correct.mean()),
            "correct_rt_mean_ms": float(rt_ms.mean()) if len(rt_ms) else np.nan,
            "correct_rt_min_ms": float(rt_ms.min()) if len(rt_ms) else np.nan,
            "correct_rt_q50_ms": float(rt_ms.quantile(.5)) if len(rt_ms) else np.nan,
        })
    return pd.DataFrame(out)
