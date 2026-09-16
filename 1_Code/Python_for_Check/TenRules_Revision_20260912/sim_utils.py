# -*- coding: utf-8 -*-
"""
sim_utils.py —— 十条规则修订包的共享工具（2026-09-12）
========================================================
供三个脚本共用：
  1) param_recovery_frozen6.py  —— 规则5：参数恢复（Censor vs Drop 的 ground-truth 检验）
  2) ppc_frozen6.py             —— 规则7：后验预测检验（PPC）
  3) model_comparison_frozen6.py—— 规则2/6：模型比较与模型恢复

设计原则
--------
* **与冻结口径完全一致**：仿真器的行为（Euler–Maruyama、dt=0.002、deadline 判 omission、
  z 以边界比例解释）逐行对齐 `1_Code/Python_HDDM/GP+Sigmoid/run_cleaned_validation_pipeline.py`
  中的 `simulate_ddm_trials()`，仅在实现上做了向量化（结果等价，速度提升 ~100x）。
* **HDDM 输入列**与真实数据一致：`subj_idx, rt, response, identity, omission`
  （见 `2_Data/Real_Data/HDDM_Ready/hddm_data_group*.csv`）。
* **参数命名**与 HDDM 迹线一致：群体节点 `v(0)`=stranger、`v(1)`=self、`a`、`t`；
  `z` 在迹线中以 `z_trans`（probit 变换）存储，需用 Φ 还原为边界比例。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

# ------------------------------------------------------------------
# 路径
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[3]
FROZEN6_TABLE = BASE_DIR / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6" / "input_conditions_g3g8.csv"
HDDM_READY_DIR = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Ready"
HDDM_TRACES_DIR = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Traces"
OUT_DATA_DIR = BASE_DIR / "2_Data" / "Generate_Data" / "TenRules_Revision_20260912"
OUT_FIG_DIR = BASE_DIR / "3_Figures" / "TenRules_Revision_20260912"

# 主口径六条件（G3–G8）
FROZEN_GROUPS = [3, 4, 5, 6, 7, 8]
# 每被试每身份的 Matching 试次数（88 人数据为每被试 260 Matching = self 130 + stranger 130）
TRIALS_PER_IDENTITY = 130
SIM_DT = 0.002


def ensure_dirs():
    for p in [OUT_DATA_DIR, OUT_FIG_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def setup_cjk_font():
    """让 matplotlib 正确显示中文（Windows 常见字体）。

    在**导入 matplotlib.pyplot 之前**调用；或在 pyplot 导入后调用再绘图亦可。
    """
    import matplotlib
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


# ------------------------------------------------------------------
# 冻结设计表
# ------------------------------------------------------------------
def load_frozen_truth(path: Path | None = None) -> pd.DataFrame:
    """读取冻结 6 条件表，输出统一的真值表。

    返回列：group_id, P, T_ms, W_ms, M_ms, n_subjects, v_self, v_stranger, a, t, z,
            omission_rate, acc, SPE_RT_ms
    """
    df = pd.read_csv(path or FROZEN6_TABLE)
    out = pd.DataFrame({
        "group_id": df["source_group_ids"].astype(int),
        "P": df["P"].astype(float),
        "T_ms": df["T_ms"].astype(float),
        "W_ms": df["W_ms"].astype(float),
        "M_ms": df["M_ms"].astype(float),
        "n_subjects": df["n_subjects"].astype(int),
        "v_self": df["v_self_mean"].astype(float),
        "v_stranger": df["v_stranger_mean"].astype(float),
        "a": df["a_mean"].astype(float),
        "t": df["t_mean"].astype(float),
        "z": df["z_mean"].astype(float),
        "omission_rate": df["omission_rate"].astype(float),
        "acc": df["acc"].astype(float),
        "SPE_RT_ms": df["SPE_RT_ms"].astype(float),
    }).sort_values("group_id").reset_index(drop=True)
    return out


# ------------------------------------------------------------------
# 向量化 DDM 仿真器（与 simulate_ddm_trials 行为一致）
# ------------------------------------------------------------------
def simulate_trials(v, a, t0, z, deadline: float,
                    n_trials: int, rng: np.random.Generator, dt: float = SIM_DT):
    """向量化仿真一批试次（支持逐试次/逐被试参数）。

    Args
    ----
    v : float or array-like, shape (n_trials,) —— 漂移率
    a, t0, z : float or array-like —— 边界、非决策时间(秒)、起始点(边界比例/绝对值)
    deadline : float —— 截止时间(秒)，超过即判 omission
    n_trials : int
    rng : np.random.Generator

    Returns
    -------
    dict: rt(秒, omission 为 NaN), response(1=上边界/记为正确, 0=下边界), omission(0/1)

    说明：当 a/t0/z 为数组（逐被试）时，循环上界取 max(deadline - t0)/dt，超过 deadline 的
    越界反应一律记为 omission（与逐试次实现等价，仅多迭代若干步，不影响判定）。
    """
    v = np.broadcast_to(np.asarray(v, dtype=float), (n_trials,)).astype(float).copy()
    a_arr = np.broadcast_to(np.asarray(a, dtype=float), (n_trials,)).astype(float)
    t0_arr = np.broadcast_to(np.asarray(t0, dtype=float), (n_trials,)).astype(float)
    z_arr = np.broadcast_to(np.asarray(z, dtype=float), (n_trials,)).astype(float)

    # z 的口径与项目一致：0<z<=1 视为边界比例，否则视为绝对起点
    start = np.where((z_arr > 0) & (z_arr <= 1), z_arr * a_arr, z_arr)
    start = np.clip(start, 0.01, a_arr - 0.01)

    max_steps = max(1, int(np.ceil(max(deadline - float(np.min(t0_arr)), dt) / dt)))
    noise_scale = np.sqrt(dt)

    x = start.copy()
    alive = np.ones(n_trials, dtype=bool)
    response = np.zeros(n_trials, dtype=int)
    rt = np.full(n_trials, np.nan, dtype=float)

    for step in range(1, max_steps + 1):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        x[idx] += v[idx] * dt + rng.normal(0.0, noise_scale, size=idx.size)
        t_candidate = t0_arr[idx] + step * dt

        up = idx[x[idx] >= a_arr[idx]]
        if up.size:
            ok = t_candidate[np.isin(idx, up)] <= deadline
            rt[up[ok]] = t_candidate[np.isin(idx, up)][ok]
            response[up] = 1
            alive[up] = False

        lo = idx[x[idx] <= 0.0]
        if lo.size:
            mask = np.isin(idx, lo)
            ok = t_candidate[mask] <= deadline
            rt[lo[ok]] = t_candidate[mask][ok]
            response[lo] = 0
            alive[lo] = False

    omission = np.isnan(rt).astype(int)
    response = np.where(omission == 1, 0, response)
    return {"rt": rt, "response": response, "omission": omission}


def simulate_condition_block(v_self: float, v_stranger: float, a: float, t0: float, z: float,
                             deadline: float, n_subjects: int, rng: np.random.Generator,
                             trials_per_identity: int = TRIALS_PER_IDENTITY,
                             jitter_sd: dict | None = None):
    """仿真一个条件（n_subjects 名被试 × 两种身份 × trials_per_identity 试次）。

    jitter_sd : dict or None
        被试水平参数抖动的标准差，例如 {"v_self":0.3,"v_stranger":0.3,"a":0.2,"t":0.02,"z":0.02}；
        为 None 时所有被试共享群体真值（population-level recovery，最干净的口径）。
    """
    frames = []
    for subj in range(n_subjects):
        if jitter_sd:
            vs = v_self + (rng.normal(0, jitter_sd["v_self"]) if jitter_sd.get("v_self") else 0.0)
            vg = v_stranger + (rng.normal(0, jitter_sd["v_stranger"]) if jitter_sd.get("v_stranger") else 0.0)
            aa = a + (rng.normal(0, jitter_sd["a"]) if jitter_sd.get("a") else 0.0)
            tt = t0 + (rng.normal(0, jitter_sd["t"]) if jitter_sd.get("t") else 0.0)
            zz = z + (rng.normal(0, jitter_sd["z"]) if jitter_sd.get("z") else 0.0)
            aa = float(max(aa, 0.2)); tt = float(max(tt, 0.05)); zz = float(np.clip(zz, 0.05, 0.95))
        else:
            vs, vg, aa, tt, zz = v_self, v_stranger, a, t0, z

        for identity, v_id in [(0, vg), (1, vs)]:   # 0=stranger, 1=self
            sim = simulate_trials(v_id, aa, tt, zz, deadline, trials_per_identity, rng)
            frames.append(pd.DataFrame({
                "subj_idx": subj,
                "rt": sim["rt"],
                "response": sim["response"],
                "identity": identity,
                "omission": sim["omission"],
            }))
    df = pd.concat(frames, ignore_index=True)
    # Censor 口径：omission 行 rt=deadline、response=0（与项目 prepare_data.py 一致）
    df.loc[df["omission"] == 1, "rt"] = deadline
    return df


def to_drop(df: pd.DataFrame) -> pd.DataFrame:
    """Drop 口径：删除 omission 行，并去掉 omission 列。"""
    out = df[df["omission"] == 0].drop(columns=["omission"]).reset_index(drop=True)
    return out


# ------------------------------------------------------------------
# HDDM 结果解析
# ------------------------------------------------------------------
def z_from_trans(z_trans):
    """z_trans（probit）→ z（边界比例）。"""
    return norm.cdf(np.asarray(z_trans, dtype=float))


def extract_params_from_stats(stats: pd.DataFrame) -> dict:
    """从 HDDM 的 gen_stats() 输出中提取群体层参数（均值与 95% CI）。

    stats 的 index 为参数名（如 'v(0)'、'v(1)'、'a'、't'、'z' 或 'z_trans'）。
    """
    idx = {str(i) for i in stats.index}
    out: dict = {}

    def _row(name):
        r = stats.loc[name]
        return {"mean": float(r["mean"]), "std": float(r["std"]),
                "lo": float(r["2.5q"]), "hi": float(r["97.5q"])}

    for out_name, key in [("v_stranger", "v(0)"), ("v_self", "v(1)"), ("a", "a"), ("t", "t")]:
        if key in idx:
            out[out_name] = _row(key)

    if "z" in idx:
        out["z"] = _row("z")
    elif "z_trans" in idx:
        r = stats.loc["z_trans"]
        out["z"] = {"mean": float(norm.cdf(r["mean"])), "std": float(r["std"]),
                    "lo": float(norm.cdf(r["2.5q"])), "hi": float(norm.cdf(r["97.5q"]))}

    if "v_self" in out and "v_stranger" in out:
        out["SPE_v"] = {
            "mean": out["v_self"]["mean"] - out["v_stranger"]["mean"],
            "std": np.nan,
            "lo": out["v_self"]["lo"] - out["v_stranger"]["hi"],
            "hi": out["v_self"]["hi"] - out["v_stranger"]["lo"],
        }
    return out


# ------------------------------------------------------------------
# 行为统计（观测与仿真共用同一套定义，保证 PPC 可比）
# ------------------------------------------------------------------
def behavior_stats(df: pd.DataFrame, rt_unit: str = "sec") -> dict:
    """计算一组试次的行为统计量。

    参数
    ----
    df : DataFrame，需含 rt / response / omission（可选 identity）
    rt_unit : 'sec' 或 'ms'（输入单位）

    返回：acc_all（omission 记为错）、acc_responded、omission_rate、
          correct_rt_mean/q10/q30/q50/q70/q90（毫秒，仅 response==1）
    """
    rt = pd.to_numeric(df["rt"], errors="coerce")
    if rt_unit == "sec":
        rt_ms = rt * 1000.0
    else:
        rt_ms = rt
    responded = (df["omission"] == 0).to_numpy()
    correct = ((df["response"] == 1) & responded)
    correct_rt = rt_ms[correct].dropna()

    q = {}
    for name, qq in [("q10", .10), ("q30", .30), ("q50", .50), ("q70", .70), ("q90", .90)]:
        q[name] = float(np.quantile(correct_rt, qq)) if len(correct_rt) else np.nan

    return {
        "n_trials": int(len(df)),
        "omission_rate": float(1 - responded.mean()) if len(df) else np.nan,
        "acc_all": float(correct.mean()) if len(df) else np.nan,
        "acc_responded": float((df["response"].to_numpy()[responded] == 1).mean()) if responded.sum() else np.nan,
        "correct_rt_mean_ms": float(correct_rt.mean()) if len(correct_rt) else np.nan,
        "correct_rt_q10_ms": q["q10"],
        "correct_rt_q30_ms": q["q30"],
        "correct_rt_q50_ms": q["q50"],
        "correct_rt_q70_ms": q["q70"],
        "correct_rt_q90_ms": q["q90"],
    }


def observed_condition_stats(group_id: int) -> dict:
    """从 HDDM_Ready 文件计算某条件的观测统计（Matching 试次、身份分列与合并）。"""
    files = list(HDDM_READY_DIR.glob(f"hddm_data_group{group_id}_*.csv"))
    if not files:
        raise FileNotFoundError(f"未找到 group{group_id} 的 HDDM_Ready 数据")
    df = pd.read_csv(files[0])
    out = {"group_id": group_id, "n_subjects": int(df["subj_idx"].nunique())}
    out["all"] = behavior_stats(df, rt_unit="sec")
    for identity, name in [(1, "self"), (0, "stranger")]:
        sub = df[df["identity"] == identity]
        out[name] = behavior_stats(sub, rt_unit="sec")
    out["SPE_RT_ms"] = out["self"]["correct_rt_mean_ms"] - out["stranger"]["correct_rt_mean_ms"]
    out["SPE_ACC"] = out["self"]["acc_all"] - out["stranger"]["acc_all"]
    return out


# ------------------------------------------------------------------
# 被试水平后验（PPC 用）
# ------------------------------------------------------------------
def load_subject_posterior(group_id: int, n_draws: int = 200, seed: int = 42):
    """读取某条件的 HDDM 迹线，抽样被试水平参数的联合后验。

    Returns
    -------
    dict:
        v_stranger, v_self, a, t, z : ndarray, shape (n_draws, n_subjects)
        n_subjects, n_posterior_draws, source
    说明：同一 draw 索引在各参数间对齐，因此保留参数间后验相关（PPC 需要）。
    """
    files = list(HDDM_TRACES_DIR.glob(f"hddm_data_group{group_id}_*_traces.npz"))
    if not files:
        raise FileNotFoundError(f"未找到 group{group_id} 的 HDDM 迹线 npz")
    npz = np.load(files[0])

    def _collect(prefix: str, transform=None):
        keys = [k for k in npz.files if k.startswith(prefix)]
        if not keys:
            raise KeyError(f"迹线中缺少 {prefix}*（现有键示例：{npz.files[:6]}）")
        keys = sorted(keys, key=lambda k: int(k.rsplit(".", 1)[-1]))
        arr = np.column_stack([npz[k] for k in keys]).astype(float)
        return transform(arr) if transform else arr

    v_str = _collect("v_subj(0).")
    v_self = _collect("v_subj(1).")
    a = _collect("a_subj.")
    t = _collect("t_subj.")
    z = _collect("z_subj_trans.", transform=z_from_trans)

    n_total = v_self.shape[0]
    rng = np.random.default_rng(seed)
    if n_draws is None or n_draws >= n_total:
        idx = np.arange(n_total)
    else:
        idx = np.sort(rng.choice(n_total, size=n_draws, replace=False))

    return {
        "v_stranger": v_str[idx], "v_self": v_self[idx], "a": a[idx], "t": t[idx], "z": z[idx],
        "n_subjects": int(v_self.shape[1]), "n_posterior_draws": int(n_total),
        "source": str(files[0].name),
    }


def build_trial_params(v_self_row, v_stranger_row, a_row, t_row, z_row, trials_per_identity: int):
    """把一次后验抽样（每被试一个参数值）展开为逐试次参数向量。

    试次顺序：被试 0 的 stranger 块 → 被试 0 的 self 块 → 被试 1 …（与 simulate_condition_block 一致）
    """
    n_subjects = len(a_row)
    per_subject = 2 * trials_per_identity
    v_parts, a_parts, t_parts, z_parts, id_parts, subj_parts = [], [], [], [], [], []
    for s in range(n_subjects):
        v_parts.append(np.concatenate([np.full(trials_per_identity, v_stranger_row[s]),
                                       np.full(trials_per_identity, v_self_row[s])]))
        a_parts.append(np.full(per_subject, a_row[s]))
        t_parts.append(np.full(per_subject, t_row[s]))
        z_parts.append(np.full(per_subject, z_row[s]))
        id_parts.append(np.concatenate([np.zeros(trials_per_identity, dtype=int),
                                        np.ones(trials_per_identity, dtype=int)]))
        subj_parts.append(np.full(per_subject, s, dtype=int))
    return {
        "v": np.concatenate(v_parts), "a": np.concatenate(a_parts),
        "t": np.concatenate(t_parts), "z": np.concatenate(z_parts),
        "identity": np.concatenate(id_parts), "subj_idx": np.concatenate(subj_parts),
    }
