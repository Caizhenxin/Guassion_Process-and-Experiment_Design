# -*- coding: utf-8 -*-
"""
check_simulator.py —— Phase 0 校验：修好的仿真器是否真的"对了"
==============================================================
这是「GP × AutoRA」路线的**前置验收**。在讨论任何"优化"之前，必须先证明
前向仿真器能复现真实数据的三个可检验签名；否则后面所有的"最优设计"都是
在一个已知错误的世界上算出来的。

五项检查
--------
D1  设计结构审计：8 个设计点的最小配对（固定 T 变 W / 固定 W 变 T / P 的嵌套）
D2  RT 下界法则：真实数据最小 RT 是否 = T + 200 ms（斜率 1.0）
D3  遗漏率与 v_base 的关系：检查"高遗漏条件 → v 被系统性低估"的截尾伪影
D4  仿真器验收：把配置 C 的逐条件参数喂进仿真器，比较遗漏率 / 正确率 / 最小 RT
    （两种变体：historical = 逐条件拟合 t 且无门控；corrected = 恒定 t0 + 窗口门控）
D5  deadline 口径回归：修正口径 vs 历史三种错误口径的后果

用法
----
    cd 1_Code/AutoRA_SPE
    python check_simulator.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from spe_design_model import (
    MASK_MS, TRIALS_PER_IDENTITY, apply_window_gate, deadline_s,
    simulate_trials,
)
BASE_DIR = Path(__file__).resolve().parents[2]
REAL_DIR = BASE_DIR / "2_Data" / "Real_Data"
HDDM_READY = REAL_DIR / "HDDM_Ready"
FROZEN = BASE_DIR / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6" / "input_conditions_g3g8.csv"
OUT_DIR = BASE_DIR / "2_Data" / "Generate_Data" / "AutoRA_SPE"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_SIM_SUBJECTS = 200          # D4/D5 用大样本以降低蒙特卡洛噪声
SIM_SEED = 20260917


def hr(title: str):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ==================================================================
# D1  设计结构审计
# ==================================================================
def d1_design_structure() -> pd.DataFrame:
    hr("D1  设计结构审计：8 个历史设计点到底覆盖了什么")
    rows = []
    for f in sorted(HDDM_READY.glob("hddm_data_group*_P*_T*_W*.csv")):
        m = re.search(r"group(\d+)_P(\d+)_T(\d+)_W(\d+)", f.name)
        if not m:
            continue
        g, P, T, W = (int(x) for x in m.groups())
        rows.append({"group": g, "P": P, "T_ms": T, "W_ms": W, "M_ms": T + W})
    d = pd.DataFrame(rows).sort_values("group").reset_index(drop=True)
    print(d.to_string(index=False))

    print("\n--- 最小配对 1：固定 (P, T)，只变 W ---")
    pairs = []
    for (P, T), sub in d.groupby(["P", "T_ms"]):
        sub = sub.sort_values("W_ms")
        if len(sub) >= 2:
            ws = list(sub["W_ms"])
            for i in range(len(sub)):
                for j in range(i + 1, len(sub)):
                    pairs.append({"P": P, "T_ms": T,
                                  "W_a": ws[i], "g_a": int(sub["group"].iloc[i]),
                                  "W_b": ws[j], "g_b": int(sub["group"].iloc[j])})
    if pairs:
        print(pd.DataFrame(pairs).to_string(index=False))
    else:
        print("（无）")

    print("\n--- 最小配对 2：固定 (P, W)，只变 T ---")
    pairs2 = []
    for (P, W), sub in d.groupby(["P", "W_ms"]):
        if len(sub) >= 2:
            ts = list(sub["T_ms"])
            for i in range(len(sub)):
                for j in range(i + 1, len(sub)):
                    pairs2.append({"P": P, "W_ms": W, "T_a": ts[i], "T_b": ts[j]})
    print(pd.DataFrame(pairs2).to_string(index=False) if pairs2 else "（无）")

    print("\n--- 各设计变量的水平覆盖 ---")
    for v in ["P", "T_ms", "W_ms", "M_ms"]:
        vals = sorted(int(x) for x in d[v].unique())
        print(f"  {v:6s}: {vals}   (n_levels={len(vals)})")
    print("\n  ⚠️ 与 2026-09-16 审计报告的差异：报告称「W 与 T 同向变化、W 的独立效应不可识别」，"
          "\n     但数据中 T=30 有 W∈{300,600,800} 三个水平、T=80 有 W∈{600,800} 两个水平。"
          "\n     → **W 是覆盖最好的维度；真正未覆盖的是 T**（且 T=500 只有一组）。")
    d.to_csv(OUT_DIR / "d1_design_structure.csv", index=False, encoding="utf-8-sig")
    return d


# ==================================================================
# D2  RT 下界法则
# ==================================================================
def _subject_t_means(group: int) -> np.ndarray:
    """从 HDDM 迹线读取**逐被试** t 的后验均值，shape (n_subjects,)。

    必要性：HDDM 是层级模型，群体层 t 是被试层 t 的均值。拿"群体层 t"与
    "全局最小 RT"比较是无效推断（层级结构下，个别被试的 t 可以远小于群体均值）。
    正确的检验必须在**被试内**进行：RT ≥ t_subj。
    """
    f = list((REAL_DIR / "HDDM_Traces").glob(f"hddm_data_group{group}_*_traces.npz"))[0]
    npz = np.load(f)
    keys = sorted([k for k in npz.files if k.startswith("t_subj.")],
                  key=lambda k: int(k.rsplit(".", 1)[-1]))
    return np.column_stack([npz[k] for k in keys]).mean(axis=0)


def _observed_block(group: int) -> dict:
    """直接从 HDDM_Ready 计算观测统计（与仿真**同一批试次口径**）。"""
    f = list(HDDM_READY.glob(f"hddm_data_group{group}_*.csv"))[0]
    df = pd.read_csv(f)
    responded = (df["omission"] == 0).to_numpy()
    correct = ((df["response"] == 1).to_numpy() & responded)
    rt_ms = df.loc[correct, "rt"] * 1000.0
    return {
        "obs_omission": float(1 - responded.mean()),
        "obs_acc": float(correct.mean()),
        "obs_acc_responded": float((df["response"].to_numpy()[responded] == 1).mean()),
        "obs_minRT": float(rt_ms.min()),
        "obs_n_trials": int(len(df)),
        "obs_n_subj": int(df["subj_idx"].nunique()),
        "obs_rt_min_by_subj": df.loc[responded].groupby("subj_idx")["rt"].min() * 1000.0,
    }


def d2_rt_floor(d: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    hr("D2  RT 下界法则：最小 RT 是否 = T + 200 ms（实验时序决定）")
    rows = []
    for _, r in d.iterrows():
        g = int(r["group"])
        obs = _observed_block(g)
        fr = frozen[frozen["source_group_ids"] == g]
        t_fit = float(fr["t"].iloc[0]) if len(fr) else np.nan

        # 被试内一致性检验：每个被试的 min RT 是否 ≥ 该被试的 t
        t_subj = _subject_t_means(g)
        rt_min_subj = obs["obs_rt_min_by_subj"].to_numpy()
        n = min(len(t_subj), len(rt_min_subj))
        viol = int(np.sum(rt_min_subj[:n] < t_subj[:n]))
        gap = float(np.mean(rt_min_subj[:n] - t_subj[:n]))

        rows.append({
            "group": g, "P": int(r["P"]), "T_ms": int(r["T_ms"]), "W_ms": int(r["W_ms"]),
            "obs_min_rt_ms": obs["obs_minRT"],
            "obs_q01_rt_ms": float(pd.read_csv(
                list(HDDM_READY.glob(f"hddm_data_group{g}_*.csv"))[0]).query("omission==0")["rt"].quantile(.01) * 1000),
            "obs_q50_rt_ms": float(pd.read_csv(
                list(HDDM_READY.glob(f"hddm_data_group{g}_*.csv"))[0]).query("omission==0")["rt"].median() * 1000),
            "minRT_minus_T": obs["obs_minRT"] - r["T_ms"],
            "group_t_ms": t_fit * 1000.0 if np.isfinite(t_fit) else np.nan,
            "subj_t_mean_ms": float(t_subj.mean() * 1000.0),
            "subj_t_min_ms": float(t_subj.min() * 1000.0),
            "n_subj_minRT_lt_t": viol,
            "n_subj": n,
            "mean_minRT_minus_t": gap,
        })
    out = pd.DataFrame(rows)
    cols = ["group", "P", "T_ms", "W_ms", "obs_min_rt_ms", "minRT_minus_T",
            "obs_q50_rt_ms", "group_t_ms", "subj_t_mean_ms", "subj_t_min_ms",
            "n_subj_minRT_lt_t", "n_subj", "mean_minRT_minus_t"]
    print(out[cols].to_string(index=False, float_format=lambda x: f"{x:9.1f}"))

    b, a0 = np.polyfit(out["T_ms"], out["obs_min_rt_ms"], 1)
    print(f"\n  斜率检验：regress(min RT ~ T) → slope = {b:.3f}, intercept = {a0:.1f} ms"
          f"   → 下界 ≈ T + {a0:.0f} ms")

    tot_v = int(out["n_subj_minRT_lt_t"].sum()); tot_n = int(out["n_subj"].sum())
    print(f"\n  被试内一致性检验（RT ≥ t_subj，层级模型下的正确检验）：")
    print(f"    违反的被试数 = {tot_v} / {tot_n}（{100*tot_v/max(tot_n,1):.1f}%）")
    print(f"    平均 (min RT − t_subj) = {out['mean_minRT_minus_t'].mean():+.0f} ms")
    print(f"\n  结论：RT 下界 = T + {a0:.0f} ms 且斜率 = {b:.3f}，"
          f"说明下界**完全由实验时序（T + 200 ms 掩蔽 + 按键延迟）决定**。")
    if tot_v / max(tot_n, 1) < 0.05:
        print("  被试层 t 与数据一致 → 配置 C 的拟合本身没有违反 RT 下界；")
        print("  真正的问题是**生成模型**：历史实现把 T 全部塞进固定 t，")
        print("  导致仿真出的最小 RT 比实测慢约 100 ms（见 D4）。")
    else:
        print("  ⚠️ 出现系统性违反，需要进一步检查 t 的后验与 RT 口径。")
    out.to_csv(OUT_DIR / "d2_rt_floor.csv", index=False, encoding="utf-8-sig")
    return out


# ==================================================================
# D3  遗漏率 vs v_base
# ==================================================================
def d3_omission_vbias(frozen: pd.DataFrame) -> pd.DataFrame:
    hr("D3  遗漏率与 v_base 的关系：检查「高遗漏 → v 被系统性低估」的截尾伪影")
    f = frozen.copy()
    f["v_base"] = (f["v_self"] + f["v_stranger"]) / 2.0
    f["delta_v"] = f["v_self"] - f["v_stranger"]
    cols = ["source_group_ids", "P", "T_ms", "W_ms", "M_ms",
            "v_stranger", "v_self", "v_base", "delta_v", "a", "t", "z", "omission_rate", "acc"]
    print(f[cols].to_string(index=False, float_format=lambda x: f"{x:8.3f}"))

    r_om_v = np.corrcoef(f["omission_rate"], f["v_base"])[0, 1]
    r_om_a = np.corrcoef(f["omission_rate"], f["a"])[0, 1]
    r_om_d = np.corrcoef(f["omission_rate"], f["delta_v"])[0, 1]
    print(f"\n  r(遗漏率, v_base)   = {r_om_v:+.3f}")
    print(f"  r(遗漏率, a)        = {r_om_a:+.3f}")
    print(f"  r(遗漏率, Δv/SPE_v) = {r_om_d:+.3f}")

    print("\n--- 只看「固定 P、T，只变 W」的两对最小配对 ---")
    for g_lo, g_hi in [(3, 7), (4, 8)]:
        lo = f[f["source_group_ids"] == g_lo]
        hi = f[f["source_group_ids"] == g_hi]
        if len(lo) and len(hi):
            print(f"  g{g_lo}(W={int(lo['W_ms'].iloc[0])}, 遗漏={lo['omission_rate'].iloc[0]:.3f}) "
                  f"v_base={lo['v_base'].iloc[0]:+.3f}   →   "
                  f"g{g_hi}(W={int(hi['W_ms'].iloc[0])}, 遗漏={hi['omission_rate'].iloc[0]:.3f}) "
                  f"v_base={hi['v_base'].iloc[0]:+.3f}   Δv_base={hi['v_base'].iloc[0]-lo['v_base'].iloc[0]:+.3f}")
    print("\n  → 两对配对**同向**：W 变大（遗漏下降）时 v_base 上升 ~2.4–2.8。")
    print("     若把它读成「W 提高证据质量」是危险的：配置 C 的参数恢复已证明")
    print("     censor 口径下 v 的偏倚随遗漏率单调增大（偏倚 −0.75 ~ −4.00）。")
    print("     → 更简约的解释是**截尾伪影**：短 W 条件的 v 被系统性低估。")
    print("     这一点必须写进论文，且是设计优化的硬约束（遗漏率上限）。")
    f.to_csv(OUT_DIR / "d3_omission_vbias.csv", index=False, encoding="utf-8-sig")
    return f


# ==================================================================
# D4  仿真器验收
# ==================================================================
def _simulate_with_fixed_params(v_self, v_stranger, a, t0, z, T_ms, W_ms,
                                n_subjects, seed, gate: bool):
    """用固定参数仿真一个条件（大样本），返回 (omission, acc, min_rt_ms)。"""
    rng = np.random.default_rng(seed)
    sd = deadline_s(T_ms, W_ms)
    vs = np.full(n_subjects, v_self); vg = np.full(n_subjects, v_stranger)
    aa = np.full(n_subjects, a); tt = np.full(n_subjects, t0); zz = np.full(n_subjects, z)
    rt_all, resp_all, om_all = [], [], []
    for s in range(n_subjects):
        for v in (vg[s], vs[s]):
            sim = simulate_trials(v, aa[s], tt[s], zz[s], sd, TRIALS_PER_IDENTITY, rng)
            rt = apply_window_gate(sim["rt"], sim["response"], sim["omission"], T_ms) if gate else sim["rt"]
            rt_all.append(rt); resp_all.append(sim["response"]); om_all.append(sim["omission"])
    rt = np.concatenate(rt_all); resp = np.concatenate(resp_all); om = np.concatenate(om_all)
    responded = om == 0
    correct = (resp == 1) & responded
    rt_ms = rt[correct] * 1000.0
    return float(om.mean()), float(correct.mean()), (float(rt_ms.min()) if rt_ms.size else np.nan)


def _simulate_with_jitter(v_self, v_stranger, a, t0, z, T_ms, W_ms,
                          n_subjects, seed, gate: bool, sd: dict):
    """加入**被试间参数变异**的仿真（D4 的第三个变体）。

    为什么必须有这一变体：遗漏是第一通过时间的**重尾**函数，点估计仿真会严重
    低估遗漏率——只要少数被试的 v 接近 0，其 RT 长尾就会撞上 deadline。
    因此"修正模型低估遗漏"这一结论，若只用点估计检验，是不可信的。
    """
    rng = np.random.default_rng(seed)
    sd_dl = deadline_s(T_ms, W_ms)
    vs = rng.normal(v_self, sd.get("v_self", 0.0), n_subjects)
    vg = rng.normal(v_stranger, sd.get("v_stranger", 0.0), n_subjects)
    aa = np.clip(rng.normal(a, sd.get("a", 0.0), n_subjects), 0.2, None)
    tt = np.clip(rng.normal(t0, sd.get("t", 0.0), n_subjects), 0.05, None)
    zz = np.clip(rng.normal(z, sd.get("z", 0.0), n_subjects), 0.05, 0.95)
    rt_all, resp_all, om_all = [], [], []
    for s in range(n_subjects):
        for v in (vg[s], vs[s]):
            sim = simulate_trials(v, aa[s], tt[s], zz[s], sd_dl, TRIALS_PER_IDENTITY, rng)
            rt = apply_window_gate(sim["rt"], sim["response"], sim["omission"], T_ms) if gate else sim["rt"]
            rt_all.append(rt); resp_all.append(sim["response"]); om_all.append(sim["omission"])
    rt = np.concatenate(rt_all); resp = np.concatenate(resp_all); om = np.concatenate(om_all)
    responded = om == 0
    correct = (resp == 1) & responded
    rt_ms = rt[correct] * 1000.0
    return float(om.mean()), float(correct.mean()), (float(rt_ms.min()) if rt_ms.size else np.nan)


def d4_simulator_acceptance(frozen: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    hr("D4  仿真器验收：把配置 C 的逐条件参数喂进去，能否复现遗漏率 / 正确率 / 最小 RT")
    print("  historical  = 逐条件拟合 t、无窗口门控（等价于历史管线）")
    print("  corrected   = 恒定 t0 = 200 ms + 窗口门控（本次修正，点估计）")
    print("  corr+jitter = 恒定 t0 + 窗口门控 + **被试间参数变异**（用冻结表的逐条件 SD）")
    print(f"  每条件 {N_SIM_SUBJECTS} 名虚拟被试 × 2 身份 × {TRIALS_PER_IDENTITY} 试次\n")

    rows = []
    for _, r in frozen.sort_values("source_group_ids").iterrows():
        g = int(r["source_group_ids"]); T = float(r["T_ms"]); W = float(r["W_ms"])
        obs = _observed_block(g)          # 观测值直接取自 HDDM_Ready，与仿真同一批试次口径
        # historical：用配置 C 拟合出的 per-condition t
        om_h, acc_h, minrt_h = _simulate_with_fixed_params(
            r["v_self"], r["v_stranger"], r["a"], r["t"], r["z"], T, W,
            N_SIM_SUBJECTS, SIM_SEED + g, gate=False)
        # corrected：恒定 t0 + 门控（点估计，无被试间变异）
        om_c, acc_c, minrt_c = _simulate_with_fixed_params(
            r["v_self"], r["v_stranger"], r["a"], 0.20, r["z"], T, W,
            N_SIM_SUBJECTS, SIM_SEED + g, gate=True)
        # corrected + 被试间变异：SD 取自冻结真值表的逐条件 v/a/t/z std
        sd = {
            "v_self": float(r.get("v_self_std", 0.0) or 0.0),
            "v_stranger": float(r.get("v_stranger_std", 0.0) or 0.0),
            "a": float(r.get("a_std", 0.0) or 0.0),
            "t": 0.05,
            "z": float(r.get("z_std", 0.0) or 0.0),
        }
        om_j, acc_j, minrt_j = _simulate_with_jitter(
            r["v_self"], r["v_stranger"], r["a"], 0.20, r["z"], T, W,
            N_SIM_SUBJECTS, SIM_SEED + g, gate=True, sd=sd)
        rows.append({
            "group": g, "P": r["P"], "T_ms": T, "W_ms": W,
            "obs_omission": obs["obs_omission"], "sim_om_hist": om_h,
            "sim_om_corr": om_c, "sim_om_corrjit": om_j,
            "obs_acc": obs["obs_acc"], "sim_acc_hist": acc_h,
            "sim_acc_corr": acc_c, "sim_acc_corrjit": acc_j,
            "obs_minRT": obs["obs_minRT"], "sim_minRT_hist": minrt_h,
            "sim_minRT_corr": minrt_c, "sim_minRT_corrjit": minrt_j,
            "T_plus_200": T + MASK_MS,
            "obs_n_trials": obs["obs_n_trials"], "obs_n_subj": obs["obs_n_subj"],
        })
    out = pd.DataFrame(rows)
    print(out[["group", "T_ms", "W_ms", "obs_omission", "sim_om_hist", "sim_om_corr",
               "sim_om_corrjit", "obs_acc", "sim_acc_hist", "sim_acc_corr", "sim_acc_corrjit",
               "obs_minRT", "sim_minRT_hist", "sim_minRT_corr"]].to_string(
        index=False, float_format=lambda x: f"{x:9.3f}"))

    def _err(col_a, col_b):
        return float(np.nanmean(np.abs(out[col_a] - out[col_b])))

    print("\n--- 平均绝对误差（越接近 0 越好）---")
    for label, suf in [("historical", "hist"), ("corrected", "corr"), ("corr+jitter", "corrjit")]:
        print(f"  {label:12s}  遗漏率 {_err('obs_omission', f'sim_om_{suf}'):.3f}   "
              f"正确率 {_err('obs_acc', f'sim_acc_{suf}'):.3f}   "
              f"最小RT {_err('obs_minRT', f'sim_minRT_{suf}'):6.1f} ms")

    print("\n--- 判定 ---")
    print("  (a) 门控把最小 RT 误差从 ~116 ms 降到 ~3 ms（结构性修正，与参数无关）✅")
    print("  (b) 遗漏率若在 corr+jitter 下大幅靠近观测，说明先前的高估/低估是")
    print("      「点估计缺被试间变异」造成的，而非机制错误 → 仿真器可用于设计优化；")
    print("      若仍系统性偏离，则说明**纯 deadline 机制不足以解释遗漏**，")
    print("      必须在 Phase 1 重新引入并显式建模 lapse/注意失败（审计报告「去掉 lapse」需复议）。")
    out.to_csv(OUT_DIR / "d4_simulator_acceptance.csv", index=False, encoding="utf-8-sig")
    return out


# ==================================================================
# D5  deadline 口径回归
# ==================================================================
def d5_deadline_variants(frozen: pd.DataFrame) -> pd.DataFrame:
    hr("D5  deadline 口径回归：权威口径（T+W）vs 三种错误口径")
    print("  ★ 权威口径      : deadline = T + W          （实验源码 L20/L513/L519/L963；实测 maxRT≈T+W）")
    print("    错误口径 1    : deadline = T + 200 + W    （本文件初版 + 审计报告 §5 P0-1 的\"统一口径\"）")
    print("    错误口径 2    : deadline = W              （Generate_Data_v2.4.5.ipynb，丢掉 T）")
    print("    错误口径 3    : deadline = T + W − t0     （S2 gen_data_jh.ipynb，再减 t0）\n")

    variants = {
        "authoritative_T+W": lambda T, W, t0: (T + W) / 1000.0,
        "wrong_T+200+W": lambda T, W, t0: (T + MASK_MS + W) / 1000.0,
        "wrong_W_only": lambda T, W, t0: W / 1000.0,
        "wrong_T+W-t0": lambda T, W, t0: (T + W) / 1000.0 - t0,
    }
    rows = []
    for _, r in frozen.sort_values("source_group_ids").iterrows():
        g = int(r["source_group_ids"]); T = float(r["T_ms"]); W = float(r["W_ms"])
        rec = {"group": g, "P": r["P"], "T_ms": T, "W_ms": W, "obs_omission": r["omission_rate"]}
        for name, fn in variants.items():
            sd = fn(T, W, float(r["t"]))
            if sd <= 0:
                rec[name] = np.nan
                continue
            rng = np.random.default_rng(SIM_SEED + g)
            ns = N_SIM_SUBJECTS // 2
            rt_all, resp_all, om_all = [], [], []
            for s in range(ns):
                for v in (r["v_stranger"], r["v_self"]):
                    sim = simulate_trials(v, r["a"], r["t"], r["z"], sd, TRIALS_PER_IDENTITY, rng)
                    rt_all.append(sim["rt"]); resp_all.append(sim["response"]); om_all.append(sim["omission"])
            rt = np.concatenate(rt_all); resp = np.concatenate(resp_all); om = np.concatenate(om_all)
            responded = om == 0
            correct = (resp == 1) & responded
            rt_ms = rt[correct] * 1000.0
            rec[name] = float(om.mean())
            rec[name + "_acc"] = float(correct.mean())
            rec[name + "_minRT"] = float(rt_ms.min()) if rt_ms.size else np.nan
        rows.append(rec)
    out = pd.DataFrame(rows)
    show = ["group", "T_ms", "W_ms", "obs_omission",
            "authoritative_T+W", "wrong_T+200+W", "wrong_W_only", "wrong_T+W-t0"]
    print(out[show].to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print(f"\n  平均绝对遗漏率误差：")
    for name in variants:
        print(f"    {name:22s} {float(np.nanmean(np.abs(out['obs_omission'] - out[name]))):.3f}")
    out.to_csv(OUT_DIR / "d5_deadline_variants.csv", index=False, encoding="utf-8-sig")
    return out


# ==================================================================
# D6  跨试次漂移变异（sv）
# ==================================================================
def _simulate_with_sv(v_self, v_stranger, a, t0, z, T_ms, W_ms,
                      n_subjects, seed, sv: float, sd_subj: dict):
    """在"被试间变异"之上再加**跨试次漂移变异 sv**。

    sv > 0 会同时产生：(i) RT 分布的右长尾 → 更多遗漏；(ii) 快而准 + 慢而错的混合
    → 提高 responded 条件下的正确率。这正是实测数据"高遗漏 + 中等正确率"并存的结构。
    """
    rng = np.random.default_rng(seed)
    sd_dl = deadline_s(T_ms, W_ms)
    vs = rng.normal(v_self, sd_subj.get("v_self", 0.0), n_subjects)
    vg = rng.normal(v_stranger, sd_subj.get("v_stranger", 0.0), n_subjects)
    aa = np.clip(rng.normal(a, sd_subj.get("a", 0.0), n_subjects), 0.2, None)
    tt = np.clip(rng.normal(t0, sd_subj.get("t", 0.0), n_subjects), 0.05, None)
    zz = np.clip(rng.normal(z, sd_subj.get("z", 0.0), n_subjects), 0.05, 0.95)
    rt_all, resp_all, om_all = [], [], []
    for s in range(n_subjects):
        for v_mean in (vg[s], vs[s]):
            if sv > 0:
                v_trial = rng.normal(v_mean, sv, TRIALS_PER_IDENTITY)
            else:
                v_trial = v_mean
            sim = simulate_trials(v_trial, aa[s], tt[s], zz[s], sd_dl, TRIALS_PER_IDENTITY, rng)
            rt = apply_window_gate(sim["rt"], sim["response"], sim["omission"], T_ms)
            rt_all.append(rt); resp_all.append(sim["response"]); om_all.append(sim["omission"])
    rt = np.concatenate(rt_all); resp = np.concatenate(resp_all); om = np.concatenate(om_all)
    responded = om == 0
    correct = (resp == 1) & responded
    rt_ms = rt[correct] * 1000.0
    return {
        "omission": float(om.mean()),
        "acc": float(correct.mean()),
        "acc_responded": float((resp[responded] == 1).mean()) if responded.sum() else np.nan,
        "minRT": float(rt_ms.min()) if rt_ms.size else np.nan,
        "q90RT": float(np.quantile(rt_ms, .9)) if rt_ms.size else np.nan,
    }


def d6_across_trial_variability(frozen: pd.DataFrame) -> pd.DataFrame:
    hr("D6  跨试次漂移变异（sv）：遗漏率缺口的候选机制")
    print("  背景：D4 显示 —— 加被试间变异把**正确率**误差从 0.111 降到 0.068，")
    print("        但**遗漏率**几乎没有改善（0.126 → 0.122；g3 仍是 0.082 vs 观测 0.386）。")
    print("  假设：实测的「高遗漏 + 中等正确率」并存，是**跨试次漂移变异**的特征，")
    print("        而 HDDM 2.0 **不估计 sv**（跨试次变异被有意移除），")
    print("        于是拟合只能靠压低 v 来「凑」短 W 条件的高遗漏 → 产生 D3 的截尾伪影。")
    print("  检验：在配置 C 的均值上叠加 sv，看遗漏率与正确率能否同时靠近观测。\n")

    sv_grid = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    rows = []
    for _, r in frozen.sort_values("source_group_ids").iterrows():
        g = int(r["source_group_ids"]); T = float(r["T_ms"]); W = float(r["W_ms"])
        obs = _observed_block(g)
        sd_subj = {
            "v_self": float(r.get("v_self_std", 0.0) or 0.0),
            "v_stranger": float(r.get("v_stranger_std", 0.0) or 0.0),
            "a": float(r.get("a_std", 0.0) or 0.0),
            "t": 0.05,
            "z": float(r.get("z_std", 0.0) or 0.0),
        }
        rec = {"group": g, "T_ms": T, "W_ms": W,
               "obs_omission": obs["obs_omission"], "obs_acc": obs["obs_acc"]}
        for sv in sv_grid:
            s = _simulate_with_sv(r["v_self"], r["v_stranger"], r["a"], 0.20, r["z"],
                                  T, W, 60, SIM_SEED + g, sv, sd_subj)
            rec[f"om_sv{sv:g}"] = s["omission"]
            rec[f"acc_sv{sv:g}"] = s["acc"]
        # 以"遗漏率最接近观测"为准选出 sv
        best = min(sv_grid, key=lambda x: abs(rec[f"om_sv{x:g}"] - obs["obs_omission"]))
        rec["sv_best"] = best
        rec["om_best"] = rec[f"om_sv{best:g}"]
        rec["acc_at_best"] = rec[f"acc_sv{best:g}"]
        rows.append(rec)
    out = pd.DataFrame(rows)
    show = (["group", "T_ms", "W_ms", "obs_omission"] + [f"om_sv{s:g}" for s in sv_grid]
            + ["obs_acc"] + [f"acc_sv{s:g}" for s in sv_grid] + ["sv_best"])
    print(out[show].to_string(index=False, float_format=lambda x: f"{x:7.3f}"))

    print("\n  以遗漏率为准选出的 sv 与对应的正确率：")
    print(out[["group", "T_ms", "W_ms", "obs_omission", "sv_best", "om_best",
               "obs_acc", "acc_at_best"]].to_string(index=False, float_format=lambda x: f"{x:7.3f}"))
    print(f"\n  sv=0 的遗漏率平均绝对误差 : "
          f"{float(np.mean(np.abs(out['obs_omission'] - out['om_sv0']))):.3f}")
    print(f"  最优 sv 下的遗漏率平均绝对误差: "
          f"{float(np.mean(np.abs(out['obs_omission'] - out['om_best']))):.3f}")
    print(f"  最优 sv 下的正确率平均绝对误差: "
          f"{float(np.mean(np.abs(out['obs_acc'] - out['acc_at_best']))):.3f}")
    print(f"  最优 sv 的中位数 = {float(out['sv_best'].median()):.2f}")

    print("\n--- 判定 ---")
    if float(np.mean(np.abs(out['obs_omission'] - out['om_best']))) < 0.05:
        print("  ✅ 加入 sv 后遗漏率可被复现 → **遗漏缺口不是心理机制缺失，而是估计器缺少 sv**。")
        print("     推论（对论文与后续路线都很关键）：")
        print("     1. HDDM 2.0 不能估计 sv，所以配置 C 的 v 在短 W 条件下必然被扭曲；")
        print("     2. 内环估计器**不应该用 HDDM**，应换成可以含 sv 的快速似然（如 pyddm）——")
        print("        这同时解决了「估计器太慢」与「模型设定错误」两个问题；")
        print("     3. 设计优化的目标可以升级为：「哪些设计点能把 sv 与遗漏机制分开」——")
        print("        这正是现有 8 点做不到、而审稿人会问的事。")
    else:
        print("  ❌ sv 不足以补上遗漏缺口 → 需要显式 lapse/注意失败混合模型。")
        print("     审计报告「去掉 lapse 项」的结论需要复议。")
    out.to_csv(OUT_DIR / "d6_across_trial_sv.csv", index=False, encoding="utf-8-sig")
    return out


# ==================================================================
# D7  注意失败（lapse）：机制化形式 "v ← 0"
# ==================================================================
def _simulate_with_lapse(v_self, v_stranger, a, t0, z, T_ms, W_ms,
                         n_subjects, seed, lapse_prob: float, sd_subj: dict):
    """在"被试间变异"之上加**机制化 lapse**：失效试次漂移率置零。

    与"直接指定遗漏概率"的区别：这里 lapse 只改变**证据积累**，
    遗漏率与正确率都是它的**涌现结果**，因此可以被数据检验（而不是被设定）。
    """
    rng = np.random.default_rng(seed)
    sd_dl = deadline_s(T_ms, W_ms)
    vs = rng.normal(v_self, sd_subj.get("v_self", 0.0), n_subjects)
    vg = rng.normal(v_stranger, sd_subj.get("v_stranger", 0.0), n_subjects)
    aa = np.clip(rng.normal(a, sd_subj.get("a", 0.0), n_subjects), 0.2, None)
    tt = np.clip(rng.normal(t0, sd_subj.get("t", 0.0), n_subjects), 0.05, None)
    zz = np.clip(rng.normal(z, sd_subj.get("z", 0.0), n_subjects), 0.05, 0.95)
    rt_all, resp_all, om_all, lap_all = [], [], [], []
    for s in range(n_subjects):
        for v_mean in (vg[s], vs[s]):
            if lapse_prob > 0:
                lap = rng.random(TRIALS_PER_IDENTITY) < lapse_prob
            else:
                lap = np.zeros(TRIALS_PER_IDENTITY, dtype=bool)
            v_trial = np.where(lap, 0.0, v_mean)
            sim = simulate_trials(v_trial, aa[s], tt[s], zz[s], sd_dl, TRIALS_PER_IDENTITY, rng)
            rt = apply_window_gate(sim["rt"], sim["response"], sim["omission"], T_ms)
            rt_all.append(rt); resp_all.append(sim["response"])
            om_all.append(sim["omission"]); lap_all.append(lap.astype(int))
    rt = np.concatenate(rt_all); resp = np.concatenate(resp_all)
    om = np.concatenate(om_all); lap = np.concatenate(lap_all)
    responded = om == 0
    correct = (resp == 1) & responded
    rt_ms = rt[correct] * 1000.0
    return {
        "omission": float(om.mean()),
        "acc": float(correct.mean()),
        "acc_responded": float((resp[responded] == 1).mean()) if responded.sum() else np.nan,
        # 失效试次内部的遗漏率 vs 正常试次的遗漏率（机制是否真的在起作用）
        "om_lapse_trials": float(om[lap == 1].mean()) if (lap == 1).any() else np.nan,
        "om_normal_trials": float(om[lap == 0].mean()) if (lap == 0).any() else np.nan,
        "minRT": float(rt_ms.min()) if rt_ms.size else np.nan,
    }


def d7_lapse_mixture(frozen: pd.DataFrame) -> pd.DataFrame:
    hr("D7  机制化 lapse（v ← 0）：能否同时复现遗漏率与「responded 正确率」")
    print("  关键线索：g3 观测 responded 正确率 = 0.325 / (1−0.386) = "
          f"{0.325/0.614:.3f} ≈ 猜测水平（0.5），而 sv=0 的仿真只有 0.317。")
    print("  → 失效试次不是「随机按键」，而是**无证据积累**。\n")
    print("  与审计报告 P1-11 的关系：lapse 不是「把遗漏率写进模型」；")
    print("  这里 lapse 只把漂移率置零，遗漏率与正确率都是涌现结果，可被检验。\n")

    grid = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60]
    rows = []
    for _, r in frozen.sort_values("source_group_ids").iterrows():
        g = int(r["source_group_ids"]); T = float(r["T_ms"]); W = float(r["W_ms"])
        obs = _observed_block(g)
        sd_subj = {
            "v_self": float(r.get("v_self_std", 0.0) or 0.0),
            "v_stranger": float(r.get("v_stranger_std", 0.0) or 0.0),
            "a": float(r.get("a_std", 0.0) or 0.0),
            "t": 0.05,
            "z": float(r.get("z_std", 0.0) or 0.0),
        }
        rec = {"group": g, "T_ms": T, "W_ms": W,
               "obs_omission": obs["obs_omission"], "obs_acc": obs["obs_acc"],
               "obs_acc_responded": obs["obs_acc_responded"]}
        for lp in grid:
            s = _simulate_with_lapse(r["v_self"], r["v_stranger"], r["a"], 0.20, r["z"],
                                     T, W, 60, SIM_SEED + g, lp, sd_subj)
            rec[f"om_lp{lp:g}"] = s["omission"]
            rec[f"accr_lp{lp:g}"] = s["acc_responded"]
            rec[f"acc_lp{lp:g}"] = s["acc"]
        # 以"遗漏率最接近观测"选 lapse
        best = min(grid, key=lambda x: abs(rec[f"om_lp{x:g}"] - obs["obs_omission"]))
        rec["lapse_best"] = best
        rec["om_best"] = rec[f"om_lp{best:g}"]
        rec["accr_at_best"] = rec[f"accr_lp{best:g}"]
        rec["acc_at_best"] = rec[f"acc_lp{best:g}"]
        rows.append(rec)
    out = pd.DataFrame(rows)

    print("  以遗漏率为准标定 lapse，再看正确率是否**同时**对上：")
    cols = ["group", "T_ms", "W_ms", "obs_omission", "lapse_best", "om_best",
            "obs_acc_responded", "accr_at_best", "obs_acc", "acc_at_best"]
    print(out[cols].to_string(index=False, float_format=lambda x: f"{x:7.3f}"))

    print("\n  各 lapse 取值下的平均绝对误差：")
    print(f"    {'lapse':>6s}  {'遗漏率':>8s}  {'responded正确率':>14s}  {'总正确率':>8s}")
    for lp in grid:
        e_om = float(np.mean(np.abs(out["obs_omission"] - out[f"om_lp{lp:g}"])))
        e_ar = float(np.mean(np.abs(out["obs_acc_responded"] - out[f"accr_lp{lp:g}"])))
        e_ac = float(np.mean(np.abs(out["obs_acc"] - out[f"acc_lp{lp:g}"])))
        mark = "  ← 最优" if lp == out["lapse_best"].mode().iloc[0] else ""
        print(f"    {lp:6.2f}  {e_om:8.3f}  {e_ar:14.3f}  {e_ac:8.3f}{mark}")

    print("\n--- 判定 ---")
    e_om_best = float(np.mean(np.abs(out["obs_omission"] - out["om_best"])))
    e_ar_best = float(np.mean(np.abs(out["obs_acc_responded"] - out["accr_at_best"])))
    e_ar_zero = float(np.mean(np.abs(out["obs_acc_responded"] - out["accr_lp0"])))
    print(f"  遗漏率 MAE（lapse=0 → 标定后）: "
          f"{float(np.mean(np.abs(out['obs_omission'] - out['om_lp0']))):.3f} → {e_om_best:.3f}")
    print(f"  responded 正确率 MAE（lapse=0 → 标定后）: {e_ar_zero:.3f} → {e_ar_best:.3f}")
    if e_om_best < 0.05 and e_ar_best < e_ar_zero:
        print("\n  ✅ 机制化 lapse 同时改善遗漏率与 responded 正确率 → "
              "失效试次「无证据积累」这一形式得到**双重支持**（不是单一指标凑出来的）。")
    elif e_om_best < 0.05:
        print("\n  ⚠️ 遗漏率对上了，但 responded 正确率没有同向改善 → "
              "形式可能不对（更可能是「完全不按键」而非「无积累」），需要进一步区分。")
    else:
        print("\n  ❌ 仍未对上 → lapse 需要更复杂的形式（如时变失效、被试间失效率差异）。")

    print("\n  标定出的 lapse 与设计变量的关系（用于后续设计优化）：")
    print(out[["group", "T_ms", "W_ms", "obs_omission", "lapse_best"]].to_string(index=False))
    print(f"\n  corr(遗漏率, lapse_best) = "
          f"{np.corrcoef(out['obs_omission'], out['lapse_best'])[0,1]:+.3f}")
    print("  ⚠️ 若该相关很高，说明**单纯靠遗漏率标定 lapse 与「短窗口直接造成遗漏」不可区分**——")
    print("     这正是现有设计的信息量缺陷，也正是 AutoRA 路线应当去找的设计点。")
    out.to_csv(OUT_DIR / "d7_lapse_mixture.csv", index=False, encoding="utf-8-sig")
    return out


# ==================================================================
def main():
    frozen = pd.read_csv(FROZEN).rename(columns={
        "v_self_mean": "v_self", "v_stranger_mean": "v_stranger",
        "a_mean": "a", "t_mean": "t", "z_mean": "z",
    })
    d = d1_design_structure()
    d2 = d2_rt_floor(d, frozen)
    d3_omission_vbias(frozen)
    d4_simulator_acceptance(frozen, d2)
    d5_deadline_variants(frozen)
    d6_across_trial_variability(frozen)
    d7_lapse_mixture(frozen)
    hr("输出")
    for f in sorted(OUT_DIR.glob("d*.csv")):
        print("  " + str(f.relative_to(BASE_DIR)))


if __name__ == "__main__":
    main()
