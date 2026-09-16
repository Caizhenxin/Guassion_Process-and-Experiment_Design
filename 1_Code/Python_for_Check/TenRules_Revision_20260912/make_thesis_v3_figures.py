# -*- coding: utf-8 -*-
"""
make_thesis_v3_figures.py —— 生成论文 v3 版图集（2026-09-12）
==============================================================
产物目录：3_Figures/Thesis_v3_20260912/

新绘（源自冻结口径数据）：
    F4-1_design_space.png          实验设计空间 Ω 与 8 组取点（含质量分档）
    F5-1_spe_subjects.png          被试级 SPE_RT / SPE_ACC（行为层）
    F5-2_hddm_params_forest.png    HDDM 群体层参数与 95% CI（含遗漏率标注）
    F5-3_omission_delta.png        遗漏率 vs Censor−Drop 参数差异
汇集（复用已有产物，统一拷入 v3 目录，便于 docx 一次性内嵌）：
    F6-2_opn.png                   OPN 第一版预测表现
    F7-1_insample.png              Sigmoid+GP in-sample 拟合（冻结 6 条件）
    F7-2_locv.png                  LOCV（6 折）
    F7-3_ppc_interval.png          PPC：观测 vs 95% 预测区间
    F7-4_ppc_coverage.png          PPC 覆盖率
    F7-5_ppc_qp.png                QP 图（观测 vs 预测）
    F7-6_model_comparison.png      模型比较 + 模型恢复混淆矩阵
    F7-7_candidates.png            候选设计点（探索性）
    F8-1_sliding_window.png        内部数据滑动窗口 SPE
    F8-3_stimcoding_crf.png        Stim-Coding 双引擎 CRF

说明：颜色约定 —— 灰色=排除（G1/G2）、橙色=谨慎（G3/G4）、蓝色=主口径核心（G5–G8）。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim_utils import setup_cjk_font  # noqa: E402

OUT = BASE / "3_Figures" / "Thesis_v3_20260912"
OUT.mkdir(parents=True, exist_ok=True)

OMISSION_SUMMARY = BASE / "2_Data" / "Generate_Data" / "Omission_Sensitivity" / "data_summary.csv"
SENSITIVITY = BASE / "2_Data" / "Generate_Data" / "Omission_Sensitivity" / "sensitivity_comparison.csv"
HDDM_PARAMS = BASE / "2_Data" / "Real_Data" / "HDDM_Traces" / "all_groups_ddm_params.csv"
HDDM_READY = BASE / "2_Data" / "Real_Data" / "HDDM_Ready"

QUALITY_COLOR = {1: "#9e9e9e", 2: "#9e9e9e", 3: "#f4a261", 4: "#f4a261",
                 5: "#2a6f97", 6: "#2a6f97", 7: "#2a6f97", 8: "#2a6f97"}
QUALITY_LABEL = {1: "排除(高遗漏)", 2: "排除(高遗漏)", 3: "谨慎", 4: "谨慎",
                 5: "主口径核心", 6: "主口径核心", 7: "主口径核心", 8: "主口径核心"}


def fig_design_space(design: pd.DataFrame):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for g, row in design.iterrows():
        c = QUALITY_COLOR[int(row.group_id)]
        for ax, (xcol, xlabel) in zip(axes, [("P", "练习次数 P"), ("T_ms", "刺激呈现时间 T (ms)")]):
            ycol, ylabel = ("W_ms", "反应窗口 W (ms)")
            ax.scatter(row[xcol], row[ycol], s=120, color=c, edgecolor="k", zorder=3)
            ax.annotate(f"G{int(row.group_id)}", (row[xcol], row[ycol]),
                        textcoords="offset points", xytext=(7, 5), fontsize=10)
    axes[0].set_xlabel("练习次数 P"); axes[0].set_ylabel("反应窗口 W (ms)")
    axes[0].set_title("(A) P–W 平面")
    axes[1].set_xlabel("刺激呈现时间 T (ms)"); axes[1].set_ylabel("反应窗口 W (ms)")
    axes[1].set_title("(B) T–W 平面")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=l, markeredgecolor="k")
               for c, l in [(QUALITY_COLOR[1], "排除（遗漏率>50%）"),
                            (QUALITY_COLOR[3], "谨慎（遗漏率≈35–40%）"),
                            (QUALITY_COLOR[5], "主口径核心（遗漏率<16%）")]]
    axes[1].legend(handles=handles, fontsize=8, loc="upper left")
    fig.suptitle("图4-1 实验设计空间 Ω=(P, T, W) 与 8 组取点")
    fig.tight_layout()
    fig.savefig(OUT / "F4-1_design_space.png", dpi=300)
    plt.close(fig)


def subject_level_spe(group_id: int):
    """计算某条件内被试级 SPE_RT 与 SPE_ACC（Matching 试次、omission 计为错误）。"""
    f = list(HDDM_READY.glob(f"hddm_data_group{group_id}_*.csv"))
    if not f:
        return None
    df = pd.read_csv(f[0])
    df["correct"] = ((df["response"] == 1) & (df["omission"] == 0)).astype(int)
    rows = []
    for subj, g in df.groupby("subj_idx"):
        self_g = g[g["identity"] == 1]
        str_g = g[g["identity"] == 0]
        rt_self = self_g.loc[self_g["correct"] == 1, "rt"].mean() * 1000
        rt_str = str_g.loc[str_g["correct"] == 1, "rt"].mean() * 1000
        rows.append({"group_id": group_id, "subj_idx": subj,
                     "SPE_RT_ms": rt_self - rt_str,
                     "SPE_ACC": self_g["correct"].mean() - str_g["correct"].mean()})
    return pd.DataFrame(rows)


def fig_spe_subjects(design: pd.DataFrame):
    import matplotlib.pyplot as plt
    data = pd.concat([d for d in (subject_level_spe(int(g)) for g in design.group_id) if d is not None],
                     ignore_index=True)
    data.to_csv(OUT / "T5-1b_subject_level_spe.csv", index=False)
    labels = [f"G{int(g)}" for g in design.group_id]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, metric, ylabel in [(axes[0], "SPE_RT_ms", "SPE_RT (ms)：自我 − 陌生人（负=自我更快）"),
                               (axes[1], "SPE_ACC", "SPE_ACC：自我 − 陌生人（正=自我更准）")]:
        groups = [data.loc[data.group_id == g, metric].dropna().to_numpy() for g in design.group_id]
        bp = ax.boxplot(groups, tick_labels=labels, widths=.55, patch_artist=True, showfliers=False)
        for patch, g in zip(bp["boxes"], design.group_id):
            patch.set_facecolor(QUALITY_COLOR[int(g)]); patch.set_alpha(.45)
        for i, (g, vals) in enumerate(zip(design.group_id, groups), start=1):
            ax.scatter(np.full(len(vals), i) + np.random.default_rng(42).normal(0, .06, len(vals)),
                       vals, s=16, color=QUALITY_COLOR[int(g)], edgecolor="k", linewidth=.3, zorder=3)
            ax.scatter(i, np.mean(vals), marker="D", color="k", s=26, zorder=4)
        ax.axhline(0, color="k", lw=.8, ls="--")
        ax.set_xticks(range(1, len(labels) + 1)); ax.set_xticklabels(labels)
        ax.set_ylabel(ylabel)
        for i, g in enumerate(design.group_id, start=1):
            om = design.loc[design.group_id == g, "omission_rate"].iloc[0] * 100
            ax.text(i, ax.get_ylim()[0], f"om={om:.0f}%", ha="center", va="bottom", fontsize=7, color="#555")
    axes[0].set_title("(A) 反应时层面的自我优势")
    axes[1].set_title("(B) 正确率层面的自我优势")
    fig.suptitle("图5-1 被试级 SPE 分布（黑菱形=条件均值；颜色=质量分档）")
    fig.tight_layout(); fig.savefig(OUT / "F5-1_spe_subjects.png", dpi=300); plt.close(fig)


def fig_hddm_forest(design: pd.DataFrame):
    import matplotlib.pyplot as plt
    p = pd.read_csv(HDDM_PARAMS).set_index("group_id")
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    specs = [("v_self", "v_self_mean", "v_self_q025", "v_self_q975", "(A) 自我条件漂移率 v_self"),
             ("v_stranger", "v_stranger_mean", "v_stranger_q025", "v_stranger_q975", "(B) 陌生人条件漂移率 v_stranger"),
             ("a", "a_mean", "a_q025", "a_q975", "(C) 决策边界 a")]
    for ax, (_k, mcol, lo, hi, title) in zip(axes, specs):
        for i, g in enumerate(design.group_id, start=1):
            c = QUALITY_COLOR[int(g)]
            est, l, h = p.loc[g, mcol], p.loc[g, lo], p.loc[g, hi]
            ax.errorbar(est, i, xerr=[[est - l], [h - est]], fmt="o", color=c,
                        ecolor=c, elinewidth=1.6, capsize=3, ms=6)
        ax.set_yticks(range(1, len(design) + 1))
        ax.set_yticklabels([f"G{int(g)}" for g in design.group_id])
        ax.axvline(0, color="k", lw=.8, ls="--")
        ax.set_title(title); ax.invert_yaxis()
    fig.suptitle("图5-2 HDDM 群体层参数与 95% 可信区间（灰=排除、橙=谨慎、蓝=主口径核心）")
    fig.tight_layout(); fig.savefig(OUT / "F5-2_hddm_params_forest.png", dpi=300); plt.close(fig)


def fig_omission_delta(design: pd.DataFrame):
    import matplotlib.pyplot as plt
    s = pd.read_csv(SENSITIVITY)
    om = design.set_index("group_id")["omission_rate"] * 100
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    for ax, param, ylabel in [(axes[0], "v_self", "Δv_self（Censor − Drop）"),
                              (axes[1], "a", "Δa（Censor − Drop）"),
                              (axes[2], "SPE_v", "ΔSPE_v（Censor − Drop）")]:
        sub = s[s.parameter == param]
        for _, row in sub.iterrows():
            g = int(row.group_id)
            c = QUALITY_COLOR[g]
            filled = not bool(row.ci_overlap)
            ax.scatter(om.loc[g], row.delta, s=110 if filled else 70, color=c,
                       marker="o" if filled else "s", edgecolor="k", zorder=3)
            ax.annotate(f"G{g}", (om.loc[g], row.delta), textcoords="offset points",
                        xytext=(7, 4), fontsize=9)
        ax.axhline(0, color="k", lw=.8, ls="--")
        ax.axvspan(15, 35, color="#ffd166", alpha=.25, zorder=0)
        ax.set_xlabel("遗漏率 (%)"); ax.set_ylabel(ylabel)
        ax.set_title(param)
    axes[0].text(.98, .95, "● 95%CI 不重叠\n■ 95%CI 重叠\n阴影=无数据组区间(15–35%)",
                 transform=axes[0].transAxes, ha="right", va="top", fontsize=8)
    fig.suptitle("图5-3 Censor 与 Drop 的参数估计差异随遗漏率变化")
    fig.tight_layout(); fig.savefig(OUT / "F6-1_omission_delta.png", dpi=300); plt.close(fig)


def copy_existing():
    """把已有产物统一汇入 v3 图目录。"""
    mapping = [
        (BASE / "3_Figures" / "TenRules_Revision_20260912" / "ppc_interval_by_identity.png", "F7-4_ppc_interval.png"),
        (BASE / "3_Figures" / "TenRules_Revision_20260912" / "ppc_coverage.png", "F7-5_ppc_coverage.png"),
        (BASE / "3_Figures" / "TenRules_Revision_20260912" / "ppc_quantile_probability.png", "F7-6_ppc_qp.png"),
        (BASE / "3_Figures" / "TenRules_Revision_20260912" / "model_comparison.png", "F7-3_model_comparison.png"),
        (BASE / "3_Figures" / "GP_Sigmoid_Frozen6" / "step4_training_fit_cleaned.png", "F7-1_insample.png"),
        (BASE / "3_Figures" / "GP_Sigmoid_Frozen6" / "step4_locv_fit_cleaned.png", "F7-2_locv.png"),
        (BASE / "3_Figures" / "GP_Sigmoid_Frozen6" / "step6_candidate_design_points.png", "F7-7_candidates.png"),
        (BASE / "3_Figures" / "Thesis_20260902" / "figures" / "F6-2_opn_prediction_accuracy.png", "F6-2_opn.png"),
        (BASE / "3_Figures" / "Thesis_20260902" / "figures" / "F8-1_sliding_window.png", "F8-1_sliding_window.png"),
        (BASE / "3_Figures" / "Thesis_20260902" / "figures" / "F8-3_HDDM_figure_01_CRF_zbias_main.png", "F8-2_stimcoding_crf.png"),
    ]
    ok, miss = 0, []
    for src, dst in mapping:
        if src.exists():
            shutil.copy2(src, OUT / dst); ok += 1
        else:
            miss.append(str(src.relative_to(BASE)))
    print(f"[figures] 复用 {ok} 张，缺失 {len(miss)} 张")
    for m in miss:
        print("   缺:", m)


def main():
    setup_cjk_font()
    design = pd.read_csv(OMISSION_SUMMARY).sort_values("group_id").reset_index(drop=True)
    print("[figures] 设计表：", design[["group_id", "P", "T_ms", "W_ms", "n_subjects", "omission_rate"]]
          .round(3).to_string(index=False))
    fig_design_space(design)
    fig_spe_subjects(design)
    fig_hddm_forest(design)
    fig_omission_delta(design)
    copy_existing()
    print(f"[figures] 产物目录 → {OUT}")
    for f in sorted(OUT.glob("*.png")):
        print("   ", f.name)


if __name__ == "__main__":
    main()
