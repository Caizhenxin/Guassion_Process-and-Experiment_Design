# -*- coding: utf-8 -*-
"""
premask_prediction.py —— 「刺激呈现期按键」会漏掉多少决策？
==========================================================
背景：学姐认为"按键只在反应窗口内采集"是有理论意义的设定（T 与 W 在时间轴上分离，
T 保持外生）；导师偏向"刺激呈现期内也可以按键"。

两者表面冲突，其实争的不是**是否记录**，而是**哪些反应算数**。
本脚本把这场争论转化为一个可算的量：

    决策在"反应窗口开启"（刺激 onset + T + 200 ms）之前就完成的比例。

- 若这个比例在高 T 条件下很大 → 当前设定会**系统性地把已完成决策的试次记为遗漏**
  （学姐担心的正是这个），说明导师的直觉有据；
- 若这个比例在几乎所有条件下都接近 0 → 当前设定没有实际损失，学姐的简化可接受。

用配置 C 的逐条件参数 + 被试间变异，分别计算"门控前完成"的比例。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "1_Code" / "AutoRA_SPE"))

from spe_design_model import MASK_MS, TRIALS_PER_IDENTITY, deadline_s, simulate_trials  # noqa: E402

BASE_DIR = _HERE.parent
FROZEN = BASE_DIR / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6" / "input_conditions_g3g8.csv"
DESIGNS = {1: (0, 30, 300), 2: (0, 30, 600), 3: (120, 30, 600), 4: (120, 80, 600),
           5: (8, 100, 1100), 6: (120, 500, 1500), 7: (120, 30, 800), 8: (120, 80, 800)}

N_SUBJ = 200
SEED = 20260921


def run(v_self, v_stranger, a, t0, z, T_ms, W_ms, sd, n_subj, seed):
    """返回：响应比例、门控前完成比例、门控前完成占响应的比例。"""
    rng = np.random.default_rng(seed)
    dl = deadline_s(T_ms, W_ms)
    win_open = (T_ms + MASK_MS) / 1000.0
    vs = rng.normal(v_self, sd.get("v_self", 0.0), n_subj)
    vg = rng.normal(v_stranger, sd.get("v_stranger", 0.0), n_subj)
    aa = np.clip(rng.normal(a, sd.get("a", 0.0), n_subj), 0.2, None)
    tt = np.clip(rng.normal(t0, sd.get("t", 0.0), n_subj), 0.05, None)
    zz = np.clip(rng.normal(z, sd.get("z", 0.0), n_subj), 0.05, 0.95)

    rt_all, om_all = [], []
    for s in range(n_subj):
        for v in (vg[s], vs[s]):
            # 不加门控：拿到"决策真正完成"的时刻（t0 + 首达时）
            sim = simulate_trials(v, aa[s], tt[s], zz[s], dl, TRIALS_PER_IDENTITY, rng)
            rt_all.append(sim["rt"]); om_all.append(sim["omission"])
    rt = np.concatenate(rt_all); om = np.concatenate(om_all)
    responded = om == 0
    early = responded & (rt < win_open)
    return {
        "respond_rate": float(responded.mean()),
        "premask_rate": float(early.mean()),
        "premask_given_respond": float(early.sum() / max(responded.sum(), 1)),
        "win_open_ms": win_open * 1000.0,
    }


def main():
    frozen = pd.read_csv(FROZEN).rename(columns={
        "v_self_mean": "v_self", "v_stranger_mean": "v_stranger",
        "a_mean": "a", "t_mean": "t", "z_mean": "z"})
    by_group = {int(r["source_group_ids"]): r for _, r in frozen.iterrows()}

    print("=" * 108)
    print("预测：决策在「反应窗口开启」之前就完成的比例（= 当前设定下会丢失的决策）")
    print("=" * 108)
    print(f"  每条件 {N_SUBJ} 名虚拟被试 × 2 身份 × {TRIALS_PER_IDENTITY} 试次；"
          f"参数取配置 C；t0 = 200 ms；含被试间变异\n")

    rows = []
    for g, (P, T, W) in DESIGNS.items():
        if g in by_group:
            r = by_group[g]
            v_s, v_g = r["v_self"], r["v_stranger"]
        else:
            # G1/G2 不在冻结表（不在主口径内）：取相邻条件的参数近似
            r = by_group[3]
            v_s, v_g = r["v_self"], r["v_stranger"]
        a, t0, z = r["a"], 0.20, r["z"]
        sd = {"v_self": float(r.get("v_self_std", 0.0) or 0.0),
              "v_stranger": float(r.get("v_stranger_std", 0.0) or 0.0),
              "a": float(r.get("a_std", 0.0) or 0.0),
              "t": 0.05, "z": float(r.get("z_std", 0.0) or 0.0)}
        out = run(v_s, v_g, a, t0, z, T, W, sd, N_SUBJ, SEED + g)
        obs_om = float(r["omission_rate"]) if g in by_group else np.nan
        rows.append({
            "group": g, "P": P, "T_ms": T, "W_ms": W,
            "窗口开启_ms": T + MASK_MS, "deadline_ms": T + W,
            "响应比例": out["respond_rate"], "观测遗漏率": obs_om,
            "预测_窗前完成": out["premask_rate"],
            "窗前完成/响应": out["premask_given_respond"],
        })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: f"{x:8.3f}"))

    print("\n" + "=" * 108)
    print("关键读数")
    print("=" * 108)
    for _, r in df.iterrows():
        print(f"  g{int(r['group'])}  T={int(r['T_ms']):3d}  窗口开启 {int(r['窗口开启_ms']):4.0f} ms  "
              f"→ 预测窗前完成 **{r['预测_窗前完成']*100:5.1f}%** 的试次"
              f"（占全部响应的 {r['窗前完成/响应']*100:5.1f}%）")

    print("\n  判定：")
    hi = df[df["T_ms"] >= 500]["预测_窗前完成"].max()
    lo = df[df["T_ms"] <= 100]["预测_窗前完成"].max()
    print(f"    T ≤ 100 ms 的条件，窗前完成比例最高 {lo*100:.1f}%")
    print(f"    T = 500 ms 的条件，窗前完成比例 {hi*100:.1f}%")
    if hi > 0.10:
        print("\n    → **导师的直觉有据**：在大 T 条件下，有相当比例的试次其决策其实已经完成，")
        print("      但当前设定把它们记为遗漏（或记为「在窗口开启瞬间才反应」）。")
        print("      这意味着：① 大 T 的遗漏率被系统性高估；② 大 T 的 t 被系统性抬高。")
        print("      而且——**这个效应恰好随 T 单调增长，与 T→v 的估计完全混淆**。")
    if lo < 0.05:
        print(f"\n    → 同时，**学姐的直觉也有据**：T ≤ 100 ms 时窗前完成比例 {lo*100:.1f}%，")
        print("      可以忽略。这些条件下 omission 确实主要来自 deadline，机制干净。")

    out_dir = BASE_DIR / "2_Data" / "Generate_Data" / "AutoRA_SPE"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "premask_prediction.csv", index=False, encoding="utf-8-sig")
    print(f"\n输出：{out_dir / 'premask_prediction.csv'}")


if __name__ == "__main__":
    main()
