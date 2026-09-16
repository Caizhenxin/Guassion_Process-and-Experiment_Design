# -*- coding: utf-8 -*-
"""
crf_overlay.py —— 模拟 CRF 与实测 CRF 的叠加对比（图8-3）2026-09-12
====================================================================
补齐 v3 初稿 §8.3 的待补项：把 Stim-Coding 仿真的 CRF 从"定性一致"升级为"定量叠加对比"。

口径
----
* **实测 CRF**：内部 88 人匹配任务试次（2_Data/Generate_Data/CRF_Analysis/trial_level_combined.csv）。
  对已反应的试次按 RT 分成 5 个等数量分位箱，计算每个箱内"按匹配键（Matching）反应"的比例；
  分别对自我条件、陌生人条件与全部试次计算；置信区间用**被试级 cluster bootstrap**（500 次重抽样）。
* **仿真 CRF**：Stim-Coding 仿真（起始点偏向 z = 0.50/0.55/0.60/0.65），双引擎
  （Wiener = Euler–Maruyama 数值积分；HDDM = 官方生成器），每条件 5 个 RT 分位箱（2_Data/Generate_Data/
  HDDM_Stim-Coding_Simulation/）。

图 8-3 三个面板
    (A) 实测 CRF：自我 vs 陌生人（含 cluster bootstrap 95% CI）
    (B) 仿真 CRF（4 个 z 水平 × 2 引擎）叠加实测的自我/陌生人曲线
    (C) 差异曲线：仿真（large − neutral）vs 实测（自我 − 陌生人）

产物
----
3_Figures/Thesis_v3_20260912/F8-3_crf_overlay.png
2_Data/Generate_Data/TenRules_Revision_20260912/crf/observed_crf.csv
2_Data/Generate_Data/TenRules_Revision_20260912/crf/simulated_crf.csv
2_Data/Generate_Data/TenRules_Revision_20260912/crf/crf_difference.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import OUT_DATA_DIR, OUT_FIG_DIR, setup_cjk_font  # noqa: E402

OBS_FILE = BASE / "2_Data" / "Generate_Data" / "CRF_Analysis" / "trial_level_combined.csv"
HDDM_READY = BASE / "2_Data" / "Real_Data" / "HDDM_Ready"
SIM_DIR = BASE / "2_Data" / "Generate_Data" / "HDDM_Stim-Coding_Simulation"
OUT = OUT_DATA_DIR / "crf"
OUT.mkdir(parents=True, exist_ok=True)
N_BINS = 5
N_BOOT = 500
SEED = 42
# 仿真条件的规范化名称（原始文件用 z_bias_*）
COND_MAP = {"neutral": "neutral", "z_bias_small": "small", "z_bias_medium": "medium", "z_bias_large": "large"}


def load_observed_from_hddm_ready() -> pd.DataFrame:
    """直接从 HDDM_Ready 读取实测试次（该文件的 identity 口径已由 SPE 方向验证：identity=1 为自我）。

    返回列：subj_idx, rt, response(1=匹配键), omission, identity(1=Self,0=Stranger), group_id
    ⚠️ 说明：`CRF_Analysis/trial_level_combined.csv` 中的 Identity 文本标签与 HDDM_Ready 的 identity 编码
    方向相反（经 RT 方向核对），因此本脚本不直接使用该文件的标签列，改由 HDDM_Ready 重建，避免自我/
    陌生人颠倒。
    """
    frames = []
    for f in sorted(HDDM_READY.glob("hddm_data_group*_*.csv")):
        gid = int(f.name.split("group")[1].split("_")[0])
        d = pd.read_csv(f)
        d["group_id"] = gid
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def observed_crf(df: pd.DataFrame, identity: int | None = None) -> pd.DataFrame:
    d = df[df["omission"] == 0].copy()
    if identity is not None:
        d = d[d["identity"] == identity]
    d["rt_ms"] = pd.to_numeric(d["rt"], errors="coerce") * 1000
    d = d.dropna(subset=["rt_ms"])
    # 分位箱（等数量）
    d["bin"] = pd.qcut(d["rt_ms"].rank(method="first"), N_BINS, labels=range(1, N_BINS + 1)).astype(int)
    d["is_match"] = (d["response"] == 1).astype(int)
    grp = d.groupby("bin").agg(n=("is_match", "size"), rt_mean_ms=("rt_ms", "mean"),
                              p_matching=("is_match", "mean")).reset_index()

    # 被试级 cluster bootstrap
    subs = d["subj_idx"].unique()
    rng = np.random.default_rng(SEED)
    boot = np.zeros((N_BOOT, N_BINS))
    for b in range(N_BOOT):
        pick = rng.choice(subs, size=len(subs), replace=True)
        dd = pd.concat([d[d.subj_idx == s] for s in pick])
        dd = dd.assign(bin=pd.qcut(dd["rt_ms"].rank(method="first"), N_BINS,
                                   labels=range(1, N_BINS + 1)).astype(int))
        m = dd.groupby("bin")["is_match"].mean().reindex(range(1, N_BINS + 1))
        boot[b] = m.to_numpy()
    grp["ci_lo"] = np.nanpercentile(boot, 2.5, axis=0)
    grp["ci_hi"] = np.nanpercentile(boot, 97.5, axis=0)
    grp["identity"] = {1: "Self", 0: "Stranger", None: "all"}[identity]
    return grp


def main():
    obs = load_observed_from_hddm_ready()
    print(f"[crf] 实测数据（HDDM_Ready 合并）{len(obs)} 行；组别 {sorted(obs.group_id.unique())}")
    frames = [observed_crf(obs, None), observed_crf(obs, 1), observed_crf(obs, 0)]
    obs_df = pd.concat(frames, ignore_index=True)
    obs_df.to_csv(OUT / "observed_crf.csv", index=False)
    print("[crf] 实测 CRF（identity=1 为自我）：")
    print(obs_df.round(3).to_string(index=False))

    sim_frames = []
    for engine, sub in [("Wiener", "Wiener"), ("HDDM", "HDDM")]:
        f = SIM_DIR / sub / "crf_results_zbias.csv"
        if f.exists():
            d = pd.read_csv(f)
            d["engine"] = engine
            d["condition"] = d["condition"].map(lambda c: COND_MAP.get(c, c))
            sim_frames.append(d)
    sim = pd.concat(sim_frames, ignore_index=True) if sim_frames else pd.DataFrame()
    if not sim.empty:
        sim.to_csv(OUT / "simulated_crf.csv", index=False)
        print(f"[crf] 仿真 CRF：{len(sim)} 行（条件 {sorted(sim.condition.unique())}）")

    # 差异曲线
    diff_rows = []
    if not sim.empty:
        for engine, g in sim.groupby("engine"):
            piv = g.pivot_table(index="bin", columns="condition", values="p_matching")
            if {"large", "neutral"}.issubset(piv.columns):
                for b, v in (piv["large"] - piv["neutral"]).items():
                    diff_rows.append({"source": f"sim_{engine}", "bin": b, "diff": v})
    obs_piv = obs_df[obs_df.identity.isin(["Self", "Stranger"])].pivot_table(
        index="bin", columns="identity", values="p_matching")
    if {"Self", "Stranger"}.issubset(obs_piv.columns):
        for b, v in (obs_piv["Self"] - obs_piv["Stranger"]).items():
            diff_rows.append({"source": "observed(Self-Stranger)", "bin": b, "diff": v})
    diff = pd.DataFrame(diff_rows)
    diff.to_csv(OUT / "crf_difference.csv", index=False)

    # ---- 图 ----
    setup_cjk_font()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    style = {"Self": dict(color="#2a6f97", marker="o"), "Stranger": dict(color="#e76f51", marker="s"),
             "all": dict(color="#555555", marker="^")}
    ax = axes[0]
    for ident, st in style.items():
        s = obs_df[obs_df.identity == ident].sort_values("bin")
        ax.errorbar(s.rt_mean_ms, s.p_matching,
                    yerr=[s.p_matching - s.ci_lo, s.ci_hi - s.p_matching],
                    capsize=3, lw=1.6, label={"Self": "自我", "Stranger": "陌生人", "all": "全部"}[ident], **st)
    ax.set_xlabel("反应时 (ms)"); ax.set_ylabel("按匹配键反应的比例")
    ax.set_title("(A) 实测 CRF（88 人，cluster bootstrap 95% CI）"); ax.legend(fontsize=9)

    ax = axes[1]
    if not sim.empty:
        cmap = {c: col for c, col in zip(["neutral", "small", "medium", "large"],
                                         ["#bbbbbb", "#9ecae1", "#4292c6", "#08519c"])}
        for (engine, cond), g in sim.groupby(["engine", "condition"]):
            g = g.sort_values("bin")
            ax.plot(g.rt_mean_ms, g.p_matching, marker="o" if engine == "HDDM" else None,
                    ls="-" if engine == "HDDM" else "--", color=cmap.get(cond, "k"),
                    alpha=.9, label=f"{engine}·{cond}")
    for ident in ["Self", "Stranger"]:
        s = obs_df[obs_df.identity == ident].sort_values("bin")
        ax.errorbar(s.rt_mean_ms, s.p_matching,
                    yerr=[s.p_matching - s.ci_lo, s.ci_hi - s.p_matching], capsize=3, lw=2.4,
                    label=f"实测·{'自我' if ident=='Self' else '陌生人'}", **style[ident])
    ax.set_xlabel("反应时 (ms)"); ax.set_ylabel("按匹配键反应的比例")
    ax.set_title("(B) 仿真 CRF（4 个起始点偏向 × 双引擎）叠加实测")
    ax.legend(fontsize=7, ncol=2)

    ax = axes[2]
    for src, g in diff.groupby("source"):
        g = g.sort_values("bin")
        sim_x = sim[(sim.engine == src.split("_")[1]) & (sim.condition == "neutral")].sort_values("bin")["rt_mean_ms"] \
            if src.startswith("sim_") else obs_df[obs_df.identity == "Stranger"].sort_values("bin")["rt_mean_ms"]
        ax.plot(sim_x.to_numpy()[:len(g)], g["diff"].to_numpy(), marker="o",
                ls="-" if src.startswith("sim_") else "--", label=src)
    ax.axhline(0, color="k", lw=.8, ls=":")
    ax.set_xlabel("反应时 (ms)"); ax.set_ylabel("正确率差（偏向条件 − 中性）")
    ax.set_title("(C) 差异曲线：仿真(large−neutral) vs 实测(自我−陌生人)")
    ax.legend(fontsize=8)

    fig.suptitle("图8-3 模拟与实测 CRF 的定量叠加对比")
    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "F8-3_crf_overlay.png", dpi=300)
    plt.close(fig)
    print(f"[crf] 产物 → {OUT}")
    print(f"[crf] 图 → {OUT_FIG_DIR / 'F8-3_crf_overlay.png'}")


if __name__ == "__main__":
    main()
