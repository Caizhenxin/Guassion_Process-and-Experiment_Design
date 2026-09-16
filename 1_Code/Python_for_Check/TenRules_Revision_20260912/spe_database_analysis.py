# -*- coding: utf-8 -*-
"""
spe_database_analysis.py —— SPE 数据库可获得子集分析（表8-1~8-3 + 图）2026-09-12
================================================================================
目的：把 v3 初稿 §8 的"外部验证"从笼统表述改为**可复现、可核对**的分析：
      报告实际纳入的数据集/被试/试次规模（而非全库自述数字），并给出跨研究 SPE 分布
      与设计变量（P/T/W）关系的探索性结果。

数据
----
2_Data/Real_Data/SPE_Database/*_SP.csv（63 个数据集文件，标准列：
    Subject, RT_ms, RT_sec, ACC, P_trials, T_ms, W_ms, Matching,
    Label_Standardized_Identity, Shape_Standardized_Identity）

清洗规则（写论文时须照此报告）
------------------------------
1. 仅保留 Matching 试次（若有 Matching 列）；
2. 身份仅保留 Self 与 Stranger（优先 Label_Standardized_Identity，缺则用 Shape_Standardized_Identity）；
3. ACC 仅保留 0/1（数据库说明：-1 表示无反应、2 表示其他按键，属无效编码）；
4. RT 限定 150–3000 ms；
5. 每名被试需在 Self 与 Stranger 各有 ≥5 个正确试次才能计算 SPE；
6. 数据集层面需 ≥10 名有效被试才纳入。

指标
----
SPE_RT = mean(RT | Self, 正确) − mean(RT | Stranger, 正确)    （负值=自我更快）
SPE_ACC = mean(ACC | Self) − mean(ACC | Stranger)             （匹配试次）

统计
----
* 数据集层面：均值、95% CI（被试级 t 分布）
* 汇总：**按数据集做 cluster bootstrap**（1,000 次）得到 SPE 均值的 95% CI
* 调节变量：数据集层面 Spearman ρ（SPE ~ P/T/W），同样用数据集 bootstrap 给 CI
  ⚠️ 探索性分析：P/T/W 由数据库元数据解析而来（部分为区间近似），且各研究范式异质。

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/spe_database/
    T8-1_dataset_level.csv      表8-1：逐数据集（含清洗后规模、SPE、P/T/W）
    T8-2_pooled.csv             表8-2：汇总分布（cluster bootstrap）
    T8-3_moderators.csv         表8-3：设计变量调节效应（Spearman + CI）
    excluded_datasets.csv       被排除的数据集及原因
3_Figures/Thesis_v3_20260912/F8-4_spe_database.png
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import OUT_DATA_DIR, OUT_FIG_DIR, setup_cjk_font  # noqa: E402

warnings.filterwarnings("ignore")
DB = BASE / "2_Data" / "Real_Data" / "SPE_Database"
OUT = OUT_DATA_DIR / "spe_database"
OUT.mkdir(parents=True, exist_ok=True)

RT_LO, RT_HI = 150.0, 3000.0
MIN_TRIALS_PER_CELL, MIN_SUBJECTS = 5, 10
N_BOOT = 1000
SEED = 42


def analyse_dataset(path: Path) -> tuple[dict | None, str]:
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return None, f"读取失败: {exc}"

    cols = set(df.columns)
    if "Subject" not in cols:
        return None, "缺少 Subject 列"
    id_col = "Label_Standardized_Identity" if "Label_Standardized_Identity" in cols else \
             ("Shape_Standardized_Identity" if "Shape_Standardized_Identity" in cols else None)
    if id_col is None:
        return None, "缺少标准化身份列"

    d = df.copy()
    n_raw = len(d)
    if "Matching" in cols:
        m = d["Matching"].astype(str).str.lower()
        d = d[m.str.contains("match") & ~m.str.contains("non")] if m.str.contains("non").any() else d[m.str.contains("match")]
    d = d[d[id_col].isin(["Self", "Stranger"])]
    d["ACC"] = pd.to_numeric(d["ACC"], errors="coerce")
    d = d[d["ACC"].isin([0, 1])]
    rt = pd.to_numeric(d["RT_ms"], errors="coerce") if "RT_ms" in cols else pd.to_numeric(d.get("RT_sec"), errors="coerce") * 1000
    d["rt_ms"] = rt
    d = d[d["rt_ms"].between(RT_LO, RT_HI)]
    if d.empty:
        return None, "清洗后无有效试次"

    rows = []
    for subj, g in d.groupby("Subject"):
        s = g[(g[id_col] == "Self")]
        t = g[(g[id_col] == "Stranger")]
        sc, tc = s[s.ACC == 1], t[t.ACC == 1]
        if len(sc) < MIN_TRIALS_PER_CELL or len(tc) < MIN_TRIALS_PER_CELL:
            continue
        rows.append({"Subject": subj,
                     "SPE_RT": sc.rt_ms.mean() - tc.rt_ms.mean(),
                     "SPE_ACC": s.ACC.mean() - t.ACC.mean(),
                     "n_self": len(s), "n_stranger": len(t)})
    sub = pd.DataFrame(rows)
    if len(sub) < MIN_SUBJECTS:
        return None, f"有效被试不足（{len(sub)} < {MIN_SUBJECTS}）"

    def mode_val(c):
        if c not in cols:
            return np.nan
        v = pd.to_numeric(d[c], errors="coerce").dropna()
        return float(v.mode().iloc[0]) if len(v) else np.nan

    se = sub.SPE_RT.std(ddof=1) / np.sqrt(len(sub))
    crit = stats.t.ppf(0.975, len(sub) - 1)
    return {
        "dataset": path.stem.replace("_SP", ""), "file": path.name,
        "n_subjects": len(sub), "n_trials_raw": n_raw, "n_trials_used": int(len(d)),
        "self_trials": int(sub.n_self.sum()), "stranger_trials": int(sub.n_stranger.sum()),
        "P_trials": mode_val("P_trials"), "T_ms": mode_val("T_ms"), "W_ms": mode_val("W_ms"),
        "SPE_RT_mean": sub.SPE_RT.mean(), "SPE_RT_se": se,
        "SPE_RT_lo": sub.SPE_RT.mean() - crit * se, "SPE_RT_hi": sub.SPE_RT.mean() + crit * se,
        "SPE_RT_median": sub.SPE_RT.median(),
        "SPE_ACC_mean": sub.SPE_ACC.mean(),
        "SPE_RT_pct_negative": float((sub.SPE_RT < 0).mean()),
        "identity_source": id_col,
    }, ""


def main():
    files = sorted(DB.glob("*_SP.csv"))
    print(f"[spe-db] 发现 {len(files)} 个数据集文件")
    rows, excluded = [], []
    for f in files:
        rec, why = analyse_dataset(f)
        if rec:
            rows.append(rec)
        else:
            excluded.append({"file": f.name, "reason": why})
    ds = pd.DataFrame(rows).sort_values("SPE_RT_mean")
    ds.to_csv(OUT / "T8-1_dataset_level.csv", index=False)
    pd.DataFrame(excluded).to_csv(OUT / "excluded_datasets.csv", index=False)

    print(f"[spe-db] 纳入 {len(ds)} 个数据集；排除 {len(excluded)} 个")
    print(f"[spe-db] 实际分析样本：{len(ds)} 数据集 / {int(ds.n_subjects.sum())} 名被试 / "
          f"{int(ds.n_trials_used.sum()):,} 试次（清洗后）")

    # cluster bootstrap（按数据集）
    rng = np.random.default_rng(SEED)
    idx = np.arange(len(ds))
    boot_mean, boot_med = np.zeros(N_BOOT), np.zeros(N_BOOT)
    boot_rho = {k: np.zeros(N_BOOT) for k in ["P_trials", "T_ms", "W_ms"]}
    for b in range(N_BOOT):
        pick = rng.choice(idx, size=len(idx), replace=True)
        s = ds.iloc[pick]
        boot_mean[b] = s.SPE_RT_mean.mean()
        boot_med[b] = s.SPE_RT_mean.median()
        for k in boot_rho:
            v = s[[k, "SPE_RT_mean"]].dropna()
            boot_rho[k][b] = stats.spearmanr(v[k], v.SPE_RT_mean).correlation if len(v) >= 5 else np.nan

    pooled = pd.DataFrame([{
        "n_datasets": len(ds), "n_subjects": int(ds.n_subjects.sum()),
        "n_trials_used": int(ds.n_trials_used.sum()),
        "SPE_RT_mean": ds.SPE_RT_mean.mean(),
        "SPE_RT_mean_ci_lo": np.nanpercentile(boot_mean, 2.5),
        "SPE_RT_mean_ci_hi": np.nanpercentile(boot_mean, 97.5),
        "SPE_RT_median": ds.SPE_RT_mean.median(),
        "SPE_RT_median_ci_lo": np.nanpercentile(boot_med, 2.5),
        "SPE_RT_median_ci_hi": np.nanpercentile(boot_med, 97.5),
        "SPE_RT_sd_between_datasets": ds.SPE_RT_mean.std(ddof=1),
        "pct_datasets_self_faster": float((ds.SPE_RT_mean < 0).mean()),
        "SPE_ACC_mean": ds.SPE_ACC_mean.mean(),
        "mean_within_dataset_pct_self_faster": ds.SPE_RT_pct_negative.mean(),
    }])
    pooled.to_csv(OUT / "T8-2_pooled.csv", index=False)

    mods = []
    for k, label in [("P_trials", "练习试次数 P"), ("T_ms", "刺激呈现时间 T (ms)"), ("W_ms", "反应窗口 W (ms)")]:
        v = ds[[k, "SPE_RT_mean"]].dropna()
        rho = stats.spearmanr(v[k], v.SPE_RT_mean) if len(v) >= 5 else (np.nan, np.nan)
        mods.append({
            "moderator": k, "label": label, "k_datasets": len(v),
            "spearman_rho": rho[0], "p_value": rho[1],
            "boot_ci_lo": np.nanpercentile(boot_rho[k], 2.5),
            "boot_ci_hi": np.nanpercentile(boot_rho[k], 97.5),
            "median_value": v[k].median() if len(v) else np.nan,
        })
    mod_df = pd.DataFrame(mods)
    mod_df.to_csv(OUT / "T8-3_moderators.csv", index=False)

    print("\n[spe-db] 汇总（表8-2）：")
    print(pooled.round(3).to_string(index=False))
    print("\n[spe-db] 调节效应（表8-3，探索性）：")
    print(mod_df.round(3).to_string(index=False))
    if len(excluded):
        print("\n[spe-db] 排除示例：", excluded[:3])

    # ---- 图 8-4 ----
    setup_cjk_font()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.2))
    order = ds.sort_values("SPE_RT_mean").reset_index(drop=True)
    y = np.arange(len(order))
    axes[0].errorbar(order.SPE_RT_mean, y,
                     xerr=[order.SPE_RT_mean - order.SPE_RT_lo, order.SPE_RT_hi - order.SPE_RT_mean],
                     fmt="o", ms=4, lw=1, color="#2a6f97")
    axes[0].axvline(0, color="k", ls="--", lw=.8)
    axes[0].axvline(pooled.SPE_RT_mean[0], color="r", ls=":", lw=1.2,
                    label=f"合并均值 {pooled.SPE_RT_mean[0]:.1f} ms")
    axes[0].set_yticks(y[::2]); axes[0].set_yticklabels(order.dataset[::2], fontsize=6)
    axes[0].set_xlabel("数据集层面 SPE_RT (ms)"); axes[0].set_ylabel("数据集（按效应排序）")
    axes[0].set_title(f"(A) 逐数据集 SPE_RT 森林图（k={len(ds)}）"); axes[0].legend(fontsize=8)

    for ax, xcol, xlabel in [(axes[1], "T_ms", "刺激呈现时间 T (ms)"), (axes[2], "P_trials", "练习试次数 P")]:
        v = ds[[xcol, "SPE_RT_mean", "n_subjects"]].dropna()
        ax.scatter(v[xcol], v.SPE_RT_mean, s=np.clip(v.n_subjects, 5, 400) * .8,
                   color="#e76f51", alpha=.7, edgecolor="k", linewidth=.4)
        ax.axhline(0, color="k", ls="--", lw=.8)
        m = mod_df[mod_df.moderator == xcol].iloc[0]
        ax.set_xlabel(xlabel); ax.set_ylabel("数据集层面 SPE_RT (ms)")
        ax.set_title(f"(B) SPE ~ {xlabel.split(' ')[0]}：ρ = {m.spearman_rho:.2f}\n(95% CI "
                     f"{m.boot_ci_lo:.2f} ~ {m.boot_ci_hi:.2f}, k={int(m.k_datasets)})" if xcol == "T_ms"
                     else f"(C) SPE ~ {xlabel.split(' ')[0]}：ρ = {m.spearman_rho:.2f}\n(95% CI "
                          f"{m.boot_ci_lo:.2f} ~ {m.boot_ci_hi:.2f}, k={int(m.k_datasets)})")
        if xcol == "T_ms":
            ax.set_xscale("log")
    axes[1].text(.02, .03, "点大小 ∝ 被试数", transform=axes[1].transAxes, fontsize=8)

    fig.suptitle("图8-4 SPE 数据库可获得子集的跨研究分布与设计变量关系（探索性）")
    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "F8-4_spe_database.png", dpi=300)
    plt.close(fig)
    print(f"\n[spe-db] 产物 → {OUT}\n[spe-db] 图 → {OUT_FIG_DIR / 'F8-4_spe_database.png'}")


if __name__ == "__main__":
    main()
