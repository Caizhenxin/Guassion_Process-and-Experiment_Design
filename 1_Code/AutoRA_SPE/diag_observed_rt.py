# -*- coding: utf-8 -*-
"""
diag_observed_rt.py —— 观测 RT 分布诊断（D7 失败后的定性诊断）
==============================================================
问题：配置 C 的参数（g3: v≈−1.86, a=1.22）在仿真中只能产生 8.2% 遗漏，
      而实测是 38.6%。加了被试间变异、跨试次变异 sv、机制化 lapse（v←0）
      都补不上（D4/D6/D7）。

本脚本回答一个更基本的问题：**实测的 RT 分布到底长什么样？**
如果它是"单峰 + 长尾"，那 DDM 原理上能装；如果它是"两个模态"或
"在 deadline 处有点质量"，那说明另有机制。

输出：逐条件的 RT 分位数、deadline 位置、以及"还能反应"的存活结构。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
HDDM_READY = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Ready"
OUT_DIR = BASE_DIR / "2_Data" / "Generate_Data" / "AutoRA_SPE"
MASK_MS = 200.0

DESIGNS = {1: (0, 30, 300), 2: (0, 30, 600), 3: (120, 30, 600), 4: (120, 80, 600),
           5: (8, 100, 1100), 6: (120, 500, 1500), 7: (120, 30, 800), 8: (120, 80, 800)}


def main():
    print("=" * 100)
    print("观测 RT 分布诊断（Matching 试次，HDDM_Ready 口径）")
    print("=" * 100)
    rows = []
    for g, (P, T, W) in DESIGNS.items():
        f = list(HDDM_READY.glob(f"hddm_data_group{g}_*.csv"))[0]
        df = pd.read_csv(f)
        # 权威口径：deadline = T + W（见 spe_design_model 对实验源码的引用）
        dl_ms = T + W
        resp = df[df["omission"] == 0]
        rt = resp["rt"] * 1000.0
        q = {f"q{int(x*100)}": float(np.quantile(rt, x)) for x in
             [.01, .05, .10, .25, .50, .75, .90, .95, .99]}
        # 反应试次占该条件全部试次的比例（未归一化）
        uncond = {f"uq{int(x*100)}": float(np.quantile(rt, x) ) for x in [.25, .50, .75]}
        rows.append({
            "g": g, "P": P, "T": T, "W": W, "M": T + W, "deadline_ms": dl_ms,
            "obs_omission": float(1 - (df["omission"] == 0).mean()),
            "acc_all": float(((df["response"] == 1) & (df["omission"] == 0)).mean()),
            "acc_resp": float((resp["response"] == 1).mean()),
            "n_resp": int(len(rt)), "max_rt": float(rt.max()),
            "maxRT_vs_deadline": float(rt.max()) - dl_ms,
            **q,
        })
    out = pd.DataFrame(rows)
    print(out[["g", "P", "T", "W", "deadline_ms", "obs_omission", "acc_all", "acc_resp",
               "q1", "q10", "q25", "q50", "q75", "q90", "q95", "q99", "max_rt",
               "maxRT_vs_deadline"]].to_string(index=False, float_format=lambda x: f"{x:8.1f}"))

    print("\n" + "=" * 100)
    print("关键读数")
    print("=" * 100)
    print("  1) max_rt_vs_deadline：若为负且量级明显，说明反应试次的 RT 从未接近 deadline ")
    print("     → 那 38.6% 的遗漏就不是「反应太慢」，而是**另一种过程**（不按键）。")
    print("  2) q50 与 deadline 的比值：衡量反应试次离上限有多远。")
    print()
    for _, r in out.iterrows():
        ratio = r["q50"] / r["deadline_ms"]
        print(f"  g{int(r['g'])}  deadline={r['deadline_ms']:6.0f} ms   "
              f"maxRT={r['max_rt']:7.1f} ms ({r['maxRT_vs_deadline']:+7.1f})   "
              f"q50/deadline={ratio:.3f}   q95={r['q95']:6.1f}   "
              f"遗漏={r['obs_omission']:.3f}")

    print("\n" + "=" * 100)
    print("判定：反应试次的 RT 是否真的'用满'了窗口？")
    print("=" * 100)
    close = (out["max_rt"] / out["deadline_ms"])
    print(f"  max RT / deadline 之比：min={close.min():.3f}, median={close.median():.3f}, max={close.max():.3f}")
    if close.median() < 0.9:
        print("  ⚠️ 反应试次的 RT 上限**明显低于** deadline（中位比值 < 0.9）→")
        print("     遗漏更可能来自「该试次压根没有产生反应」（注意失败/漏按），")
        print("     而不是「反应太慢被截断」。→ 支持 lapse 用**点质量在遗漏上**的形式，")
        print("     而不是「零漂移扩散」——后者仍会撞边界，产生不了足够多的遗漏。")
    else:
        print("  → 反应试次用满了窗口，遗漏是真正的右截尾。")

    print("\n  补充：反应时的经验存活函数（在各 deadline 比例处的未反应比例）")
    for _, r in out.iterrows():
        f = list(HDDM_READY.glob(f"hddm_data_group{int(r['g'])}_*.csv"))[0]
        df = pd.read_csv(f)
        dl = r["deadline_ms"]
        rt = (df.loc[df["omission"] == 0, "rt"] * 1000.0).to_numpy()
        n = len(df)
        pts = []
        for frac in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            thr = dl * frac
            pts.append(f"{frac:.1f}:{(len(rt) - (rt <= thr).sum()) / n:.3f}")
        print(f"  g{int(r['g'])}  " + "  ".join(pts))
    print("  （数值 = 全部试次中 RT > dl×frac 或遗漏 的比例；最后一个点即观测遗漏率）")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_DIR / "d8_observed_rt_diagnostic.csv", index=False, encoding="utf-8-sig")
    print(f"\n输出：{OUT_DIR / 'd8_observed_rt_diagnostic.csv'}")


if __name__ == "__main__":
    main()
