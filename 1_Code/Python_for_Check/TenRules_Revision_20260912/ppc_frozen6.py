# -*- coding: utf-8 -*-
"""
ppc_frozen6.py —— 规则7：后验预测检验（Posterior Predictive Check）
==================================================================
对应《计算建模十条规则》规则7："Validate (at least) the winning model"：
用拟合得到的参数仿真，**再用分析真实数据的同一套方法分析仿真数据**，
检查关键行为效应是否被定性与定量地捕获。

本脚本做的是**严格意义的 PPC**（相对已有的 in-sample 聚合相关）：
* 从 HDDM 迹线抽取**被试水平**参数的联合后验（保留参数间相关），
  而非只用群体均值——自检显示群体均值仿真会使 G8 的正确率虚高到 ~1.00（真实 ~0.69）；
* 每次抽样都按该条件的真实被试数、每身份 130 试次、真实 deadline 重新仿真；
* 对每个统计量给出**后验预测中位数与 95% 预测区间**，并报告观测值是否落在区间内（覆盖率）与尾概率。

统计量（观测与仿真使用完全相同的定义，见 sim_utils.behavior_stats）
    acc_all（omission 记为错）、acc_responded、omission_rate、
    correct_rt_mean / q10 / q30 / q50 / q70 / q90、
    条件层：SPE_RT（self−stranger 正确 RT 差）、SPE_ACC

用法
----
    python ppc_frozen6.py --n-draws 200            # 主分析（默认 200 次后验抽样）
    python ppc_frozen6.py --n-draws 500 --seed 7   # 更稳的版本

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/ppc/
    ppc_by_identity.csv        身份层：观测 vs 预测区间（含 inside95 / 尾概率）
    ppc_condition.csv          条件层（含 SPE 指标）
    ppc_quantile_table.csv     QP 图数据（正确/错误 RT 分位数）
    ppc_coverage_summary.csv   覆盖率汇总（论文正文可直接引用）
3_Figures/TenRules_Revision_20260912/ppc_*.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim_utils import (  # noqa: E402
    FROZEN_GROUPS, OUT_DATA_DIR, OUT_FIG_DIR, TRIALS_PER_IDENTITY,
    behavior_stats, build_trial_params, load_frozen_truth,
    load_subject_posterior, observed_condition_stats, simulate_trials,
)

PPC_DIR = OUT_DATA_DIR / "ppc"
IDENTITY_STATS = ["acc_all", "acc_responded", "omission_rate", "correct_rt_mean_ms", "correct_rt_q50_ms"]


def posterior_predictive(truth: pd.DataFrame, n_draws: int, trials_per_identity: int, seed: int):
    """对 6 个条件做后验预测仿真，返回逐抽样统计与 QP 数据。"""
    rng = np.random.default_rng(seed)
    rows, qp_rows = [], []

    for _, row in truth.iterrows():
        gid = int(row.group_id)
        deadline = float((row.T_ms + row.W_ms) / 1000.0)
        try:
            post = load_subject_posterior(gid, n_draws=n_draws, seed=seed + gid)
        except (FileNotFoundError, KeyError) as exc:
            print(f"  ⚠️ G{gid} 迹线不可用：{exc}")
            continue

        n_subj = post["n_subjects"]
        per_condition = {name: [] for name in ["all", "self", "stranger"]}
        for d in range(post["v_self"].shape[0]):
            tp = build_trial_params(post["v_self"][d], post["v_stranger"][d],
                                    post["a"][d], post["t"][d], post["z"][d], trials_per_identity)
            sim = simulate_trials(tp["v"], tp["a"], tp["t"], tp["z"], deadline,
                                  len(tp["v"]), rng)
            df = pd.DataFrame({"rt": sim["rt"], "response": sim["response"],
                               "omission": sim["omission"], "identity": tp["identity"]})
            per_condition["all"].append(behavior_stats(df, rt_unit="sec"))
            for identity, name in [(1, "self"), (0, "stranger")]:
                per_condition[name].append(behavior_stats(df[df["identity"] == identity], rt_unit="sec"))

        rec = {"group_id": gid, "P": row.P, "T_ms": row.T_ms, "W_ms": row.W_ms,
               "n_subjects": n_subj, "n_sim_draws": len(per_condition["all"]),
               "realized_omission_obs": row.omission_rate}
        for name, stats_list in per_condition.items():
            for stat in (IDENTITY_STATS + ["correct_rt_q10_ms", "correct_rt_q30_ms", "correct_rt_q70_ms", "correct_rt_q90_ms"]):
                rec[f"{name}_{stat}"] = np.array([s[stat] for s in stats_list], dtype=float)
        # 条件层 SPE
        rec["SPE_RT_ms"] = rec["self_correct_rt_mean_ms"] - rec["stranger_correct_rt_mean_ms"]
        rec["SPE_ACC"] = rec["self_acc_all"] - rec["stranger_acc_all"]
        rows.append(rec)

    return rows


def summarize(rows: list[dict], truth: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    by_id, cond_rows, cov_rows = [], [], []
    stats_to_report = ["acc_all", "acc_responded", "omission_rate", "correct_rt_mean_ms", "correct_rt_q50_ms"]

    for rec in rows:
        gid = rec["group_id"]
        obs = observed_condition_stats(gid)
        for name in ["all", "self", "stranger"]:
            for stat in stats_to_report:
                pred = rec[f"{name}_{stat}"]
                observed = obs["all" if name == "all" else name][stat]
                lo, hi = np.percentile(pred, [2.5, 97.5])
                inside = int(lo <= observed <= hi)
                p_tail = float(min((pred <= observed).mean(), (pred >= observed).mean()) * 2)
                by_id.append({
                    "group_id": gid, "identity": name, "stat": stat,
                    "observed": observed, "pred_median": float(np.median(pred)),
                    "pred_lo95": float(lo), "pred_hi95": float(hi),
                    "pred_sd": float(np.std(pred, ddof=1)) if len(pred) > 1 else np.nan,
                    "inside95": inside, "p_tail": min(p_tail, 1.0),
                    "deviation_sd": (observed - float(np.median(pred))) / (float(np.std(pred, ddof=1)) or np.nan),
                })
        # 条件层
        for stat, obs_val in [("SPE_RT_ms", obs["SPE_RT_ms"]), ("SPE_ACC", obs["SPE_ACC"])]:
            pred = rec[stat] if stat == "SPE_RT_ms" else rec["SPE_ACC"]
            lo, hi = np.percentile(pred, [2.5, 97.5])
            cond_rows.append({
                "group_id": gid, "T_ms": rec["T_ms"], "W_ms": rec["W_ms"], "stat": stat,
                "observed": obs_val, "pred_median": float(np.median(pred)),
                "pred_lo95": float(lo), "pred_hi95": float(hi),
                "inside95": int(lo <= obs_val <= hi),
                "p_tail": min(float(min((pred <= obs_val).mean(), (pred >= obs_val).mean()) * 2), 1.0),
            })

    by_id_df = pd.DataFrame(by_id)
    cond_df = pd.DataFrame(cond_rows)
    for stat, g in by_id_df.groupby("stat"):
        cov_rows.append({"stat": stat, "n_cells": len(g), "coverage_95": g["inside95"].mean(),
                         "median_p_tail": g["p_tail"].median(),
                         "n_cells_outside": int((1 - g["inside95"]).sum())})
    cov_df = pd.DataFrame(cov_rows)
    return by_id_df, cond_df, cov_df, pd.DataFrame()


def make_figures(by_id: pd.DataFrame, cond: pd.DataFrame, cov: pd.DataFrame, rows: list[dict], truth: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sim_utils import setup_cjk_font
    setup_cjk_font()

    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)

    # 图1：身份层观测 vs 95% 预测区间（选择 4 个关键统计量）
    stats_show = ["acc_all", "omission_rate", "correct_rt_mean_ms", "correct_rt_q50_ms"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax, stat in zip(axes.ravel(), stats_show):
        sub = by_id[by_id["stat"] == stat].sort_values(["identity", "group_id"])
        y = np.arange(len(sub))
        ax.errorbar(sub["pred_median"], y,
                    xerr=[sub["pred_median"] - sub["pred_lo95"], sub["pred_hi95"] - sub["pred_median"]],
                    fmt="o", color="tab:blue", label="预测中位数与95%区间", lw=1)
        ax.plot(sub["observed"], y, "rx", label="观测值")
        ax.set_yticks(y)
        ax.set_yticklabels([f"G{g}-{i}" for g, i in zip(sub["group_id"], sub["identity"])], fontsize=8)
        ax.set_title(stat); ax.legend(fontsize=8)
    fig.suptitle("后验预测检验：观测值 vs 预测区间（冻结 6 条件，被试水平后验）")
    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "ppc_interval_by_identity.png", dpi=200)
    plt.close(fig)

    # 图2：覆盖率
    if not cov.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(cov["stat"], cov["coverage_95"], color="tab:green", alpha=.8)
        ax.axhline(0.95, color="k", ls="--", lw=1, label="名义 95%")
        for i, (n, c) in enumerate(zip(cov["n_cells"], cov["coverage_95"])):
            ax.text(i, c + .01, f"{c:.2f}\n(n={n})", ha="center", fontsize=8)
        ax.set_ylim(0, 1.05); ax.set_ylabel("观测值落入 95% 预测区间的比例")
        ax.set_title("PPC 覆盖率汇总"); ax.legend()
        fig.tight_layout(); fig.savefig(OUT_FIG_DIR / "ppc_coverage.png", dpi=200); plt.close(fig)

    # 图3：QP 图（正确/错误 RT 分位数 × 正确率）
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, identity in zip(axes, ["all", "self"]):
        for rec in rows:
            gid = rec["group_id"]
            acc = float(np.median(rec[f"{identity}_acc_all"]))
            qs = [np.median(rec[f"{identity}_correct_rt_q{p}0_ms"]) for p in [1, 3, 5, 7, 9]]
            ax.plot(qs, [acc] * len(qs), "o-", ms=4, alpha=.7, label=f"G{gid}")
            obs = observed_condition_stats(gid)["all" if identity == "all" else identity]
            if identity == "self":
                obs = observed_condition_stats(gid)["self"]
            ax.plot([obs["correct_rt_q10_ms"], obs["correct_rt_q30_ms"], obs["correct_rt_q50_ms"],
                     obs["correct_rt_q70_ms"], obs["correct_rt_q90_ms"]],
                    [obs["acc_all"]] * 5, "kx", ms=6)
        ax.set_xlabel("正确反应 RT 分位数 (ms)"); ax.set_ylabel("正确率 (acc_all)")
        ax.set_title(f"QP 图（{identity}）：线=预测中位数，× = 观测")
        ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(OUT_FIG_DIR / "ppc_quantile_probability.png", dpi=200); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="冻结版后验预测检验（规则7）")
    ap.add_argument("--n-draws", type=int, default=200, help="后验抽样次数（默认 200）")
    ap.add_argument("--trials-per-identity", type=int, default=TRIALS_PER_IDENTITY)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    PPC_DIR.mkdir(parents=True, exist_ok=True)
    truth = load_frozen_truth()
    truth = truth[truth.group_id.isin(FROZEN_GROUPS)].reset_index(drop=True)
    print(f"[ppc] 条件：G{list(truth.group_id)}；后验抽样 {args.n_draws} 次/条件")

    rows = posterior_predictive(truth, args.n_draws, args.trials_per_identity, args.seed)
    if not rows:
        print("[ppc] 没有可用的迹线，终止")
        return

    by_id, cond, cov, _ = summarize(rows, truth)
    by_id.to_csv(PPC_DIR / "ppc_by_identity.csv", index=False)
    cond.to_csv(PPC_DIR / "ppc_condition.csv", index=False)
    cov.to_csv(PPC_DIR / "ppc_coverage_summary.csv", index=False)

    qp = []
    for rec in rows:
        for identity in ["all", "self", "stranger"]:
            row = {"group_id": rec["group_id"], "identity": identity,
                   "acc_all_median": float(np.median(rec[f"{identity}_acc_all"]))}
            for p in [10, 30, 50, 70, 90]:
                row[f"correct_rt_q{p}_median"] = float(np.median(rec[f"{identity}_correct_rt_q{p}_ms"])) \
                    if f"{identity}_correct_rt_q{p}_ms" in rec else np.nan
            qp.append(row)
    pd.DataFrame(qp).to_csv(PPC_DIR / "ppc_quantile_table.csv", index=False)

    make_figures(by_id, cond, cov, rows, truth)

    print("\n[ppc] 覆盖率汇总：")
    print(cov.round(3).to_string(index=False))
    print("\n[ppc] 落在 95% 区间外的单元格（需在讨论中说明）：")
    out = by_id[by_id["inside95"] == 0][["group_id", "identity", "stat", "observed", "pred_median", "pred_lo95", "pred_hi95"]]
    print(out.round(3).to_string(index=False) if not out.empty else "  （无）")
    print(f"\n[ppc] 产物 → {PPC_DIR}")


if __name__ == "__main__":
    main()
