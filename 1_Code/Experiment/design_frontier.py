#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""③ 设计空间优化：把「表格」变成「设计决策图」（成本—精度前沿）。

`design_search.py` 的产出是一张 7 种被试内设计 × 9 种 P 方案的排名表——能查，但不能决策。
本脚本把同一批数字画成三张图：

① **精度 vs 每组人数**：每条线一个被试内设计（同一套 P 方案），横线是 10% 判据；
   现行方案（45 人）与计划方案（30 人）标在线上，读者一眼看出「多一个 W 水平省 6 人」。
② **等预算前沿**：横轴人均试次、纵轴「达到 10% 所需人数」、气泡 = 总试次量；
   淡灰双曲线是等成本线（总试次 = N × 人均试次）⇒ 「加 W 水平」落在左下（免费），「加重复」落在右侧（要付试次）。
③ **判据分解**：现行被试内设计下，同一 N 对 `beta_T` / `beta_P` / `tau_P` 三个判据分别要多少人，
   P 方案取现行 vs 5 水平 ⇒ 说明「卡住人数的是 beta_T，不是 P 方案」。

数据来源：`2_Data/Generate_Data/_design_search/design_search_{oracle,design}.csv`
（`rel_beta_T` 是该设计在 N=1 时的组层相对 SE，精度按 1/√N 缩放）。

产物：
- `2_Data/Generate_Data/_design_search/design_frontier.csv`（前沿表，含成本口径）
- `3_Figures/_design/fig10_design_frontier.png`

跑法：`python 1_Code/Experiment/design_frontier.py`
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from make_figures import setup_matplotlib          # noqa: E402

plt, _LANG = setup_matplotlib("zh")

DATA = ROOT / "2_Data" / "Generate_Data" / "_design_search"
FIG = ROOT / "3_Figures" / "_design"

CURRENT = "4T×3W r12（现行）"
CURRENT_P = "现行 0/8/32/120"
JUDGE = {"beta_T": 0.10, "beta_P": 0.30, "tau_P": 0.50}
TARGET_SE = 0.10          # beta_T 判据：相对 SE ≤ 10%
PLANNED_N = 30            # D109 的落地人数（30 人/组），用于在图上标注实际处境
COLORS = {
    CURRENT: "#c0392b",
    "4T×4W r9（加 W=1400）": "#2c6fbb",
    "4T×2W r18（省 W）": "#27ae60",
    "3T×3W r16（省一个 T）": "#8e44ad",
    "5T×3W r9（加 T=200）": "#e67e22",
}


def load(truth: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"design_search_{truth}.csv")
    df["truth"] = truth
    return df


def se_at(rel_at_n1: float, n: float) -> float:
    """组层相对 SE 随 N 的 1/√N 缩放（`design_search` 的 rel_* 就是 N=1 的值）。"""
    return rel_at_n1 / math.sqrt(max(n, 1))


def frontier_table(df: pd.DataFrame) -> pd.DataFrame:
    """把每个（被试内设计 × P 方案）补上成本与「达标所需人数」口径。"""
    out = df.copy()
    out["trials_per_subject"] = out["trials_per_subject"] * 4      # ×(自我/他人) ×(匹配/不匹配)
    out["n_needed"] = out["n_total"]
    out["total_trials"] = out["n_needed"] * out["trials_per_subject"]
    out["se_beta_T_at_30"] = [se_at(r, PLANNED_N) for r in out["rel_beta_T"]]
    return out


def pareto(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """(人均试次, 需要人数) 的帕累托前沿：两项都越小越好。"""
    pts = sorted(set(pts))
    best, front = float("inf"), []
    for x, y in pts:
        if y < best:
            front.append((x, y))
            best = y
    return front


def fig_frontier(tab: pd.DataFrame, out: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.2))

    # ① 精度 vs N：同一 P 方案下比较被试内设计
    ax = axes[0]
    cur = tab[(tab["p_scheme"] == CURRENT_P) & (tab["truth"] == "oracle")]
    for _, row in cur.iterrows():
        name = row["within"]
        rel = row["rel_beta_T"]
        ns = np.arange(6, 81)
        short = name.replace("（现行）", "")
        ax.plot(ns, [se_at(rel, n) * 100 for n in ns], lw=2.2 if name == CURRENT else 1.2,
                color=COLORS.get(name, "0.6"),
                ls="-" if name == CURRENT else "--",
                label=f"{short}：需 {int(row['n_needed'])} 人")
        ax.plot([row["n_needed"]], [se_at(rel, row["n_needed"]) * 100], "o", ms=6,
                color=COLORS.get(name, "0.6"), zorder=4)
    ax.axhline(TARGET_SE * 100, color="0.3", lw=0.9, ls=":")
    ax.annotate(f"判据 {TARGET_SE*100:.0f}%", xy=(79, TARGET_SE * 100 + 0.8), fontsize=8,
                color="0.3", ha="right")
    ax.axvline(PLANNED_N, color="#c0392b", lw=0.8, ls="--", alpha=0.6)
    ax.annotate(f"计划 {PLANNED_N} 人/组", xy=(PLANNED_N - 1.5, 26), fontsize=8,
                color="#c0392b", ha="right", rotation=90, va="top")
    ax.set_xlim(6, 80)
    ax.set_ylim(6, 30)
    ax.set_xlabel("每组人数 N")
    ax.set_ylabel("beta_T 的相对 SE（%）")
    ax.set_title("① 同一预算下，被试内设计决定「要多少人」")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6.8, loc="upper right", framealpha=0.95)

    # ② 等预算前沿
    ax = axes[1]
    best = tab[(tab["p_scheme"] == CURRENT_P) & (tab["truth"] == "oracle")]
    for _, row in best.iterrows():
        ax.scatter(row["trials_per_subject"], row["n_needed"],
                   s=row["total_trials"] / 120, color=COLORS.get(row["within"], "#7f8c8d"),
                   alpha=0.85, edgecolor="white", zorder=3,
                   label=f"{row['within'].replace('（', ' (').replace('）', ')')}")
    fr = pareto(list(zip(best["trials_per_subject"], best["n_needed"])))
    if len(fr) > 1:
        ax.step([p[0] for p in fr], [p[1] for p in fr], where="post", color="0.45",
                lw=1.1, ls="--", zorder=1, label="帕累托前沿（两项都越小越好）")
    xs = np.linspace(520, 800)
    for budget in (18000, 22000, 26000):
        ax.plot(xs, budget / xs, color="0.85", lw=0.8, zorder=0)
        x_lab = budget / 31.2           # 在 y ≈ 31 处标预算
        if 525 < x_lab < 795:
            ax.annotate(f"{budget // 1000}k 总试次", xy=(x_lab, 31.2), fontsize=6,
                        color="0.5", ha="center", va="bottom", rotation=-32)
    ax.set_xlabel("每名被试的试次数（气泡大小 = 总试次量）")
    ax.set_ylabel("达到 beta_T≤10% 所需人数")
    ax.set_title("② 等预算前沿：加一个 W 水平免费，加重复要付试次")
    ax.set_xlim(520, 800)
    ax.set_ylim(30, 56)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6.2, loc="center right", framealpha=0.95)

    # ③ 判据分解：现行设计 × 两种 P 方案
    ax = axes[2]
    w = 0.36
    for k, (pname, color) in enumerate({CURRENT_P: "#7f8c8d", "5 水平 0/8/24/64/120": "#2c6fbb"}.items()):
        sub = tab[(tab["within"] == CURRENT) & (tab["p_scheme"] == pname) & (tab["truth"] == "design")]
        if sub.empty:
            continue
        row = sub.iloc[0]
        vals = [row["n_beta_T"], row["n_beta_P"], row["n_tau_P"]]
        xs = np.arange(3) + (k - 0.5) * w
        heights = [0.0 if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)
                   for v in vals]
        ax.bar(xs, heights, width=w, color=color, alpha=0.9, label=pname)
        for x, v, h in zip(xs, vals, heights):
            if h == 0.0:
                ax.annotate("不可识别", xy=(x, 1.5), xytext=(0, 0), textcoords="offset points",
                            ha="center", va="bottom", fontsize=6.5, color=color)
            else:
                ax.annotate(f"{int(h)}", xy=(x, h), xytext=(0, 2), textcoords="offset points",
                            ha="center", fontsize=7.5)
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(["beta_T（呈现时长）", "beta_P（练习）", "tau_P（练习饱和）"], fontsize=8)
    ax.set_ylabel("达到判据所需人数（组层真值 = design）")
    ax.set_title("③ 卡住人数的是 beta_T；现行 P 方案下 beta_P/tau_P 不可识别")
    ax.grid(alpha=0.25, axis="y")
    ax.legend(fontsize=7)

    fig.suptitle("设计空间优化：7 种被试内设计 × P 方案的成本—精度前沿（③，D116）", fontsize=12)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    frames = [frontier_table(load(t)) for t in ("oracle", "design")]
    tab = pd.concat(frames, ignore_index=True)
    tab.to_csv(DATA / "design_frontier.csv", index=False, encoding="utf-8-sig")
    p = fig_frontier(tab, FIG / "fig10_design_frontier.png")

    cur = tab[(tab["within"] == CURRENT) & (tab["p_scheme"] == CURRENT_P)]
    print("现行方案（两种组层真值）：")
    print(cur[["truth", "trials_per_subject", "n_beta_T", "n_beta_P", "n_tau_P",
               "n_needed", "total_trials"]].to_string(index=False))
    print(f"\n[ok] {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
