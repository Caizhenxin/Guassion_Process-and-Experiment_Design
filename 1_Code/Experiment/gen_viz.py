"""gen_viz.py —— 把生成的试次级数据画成「能看出机制」的图。

六张图回答六个问题（每一张都对应论文里的一句话）
------------------------------------------------
1. `fig1_rt_density`     RT 分布像不像人？不同条件（自我/他人 × T）的分布差在哪？
2. `fig2_rt_quantiles`   RT 分位曲线：整条分布的形状差异，而不是只看均值。
3. `fig3_accuracy`       正确率 / 遗漏率 随 T 与 W：设计的两个操作变量**有没有效果**。
4. `fig4_crf`            **CRF（条件正确率函数）**：按 RT 五分位分箱看正确率——
                          慢试次更准（DDM 的 speed–accuracy 权衡），自我优势是否在快试次上更大。
5. `fig5_delta`          delta 图：他人 − 自我 在各 RT 分位上的差（SPE 的效应形状）。
6. `fig6_mechanism`      机制图：三模型的漂移轨迹 d(t)——掩蔽、斜坡、保留率 ρ。

跨模型还有一张 `plot_model_compare`：同一套真值、同一套设计下，三模型的行为差异 ⇒
「为什么需要三条模型」的图证据（它们**可区分**，不是重复描述）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent            # 1_Code/Experiment
for _p in (str(_HERE), str(_HERE.parent / "DDM_Core")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from make_figures import setup_matplotlib          # noqa: E402

plt, _LANG = setup_matplotlib("zh")

QUANTS = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
C_SELF = "#c0392b"
C_OTHER = "#2c6fbb"
T_COLORS = ["#4c72b0", "#dd8452", "#55a868", "#c44e52"]
DPI = 150


def _save(fig, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def _responded(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["omission"] == 0].copy()


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (np.nan, np.nan)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# ----------------------------------------------------------------------
# 1. RT 分布
# ----------------------------------------------------------------------
def plot_rt_density(df: pd.DataFrame, out: Path, title: str = "") -> Path:
    """RT 密度：左 = 自我 vs 他人（合并 T），右 = 各 T 下的自我 vs 他人。"""
    d = _responded(df)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0), sharey=True)
    bins = np.arange(0, 2000, 40)

    for ident, color, lab in ((0, C_OTHER, "他人"), (1, C_SELF, "自我")):
        rt = d.loc[d["is_self"] == ident, "rt_ms"].to_numpy()
        if rt.size:
            axes[0].hist(rt, bins=bins, density=True, histtype="step", lw=2,
                         color=color, label=f"{lab}（n={rt.size}）")
    axes[0].set_xlabel("RT（ms）")
    axes[0].set_ylabel("概率密度")
    axes[0].set_title("RT 分布：自我 vs 他人（合并所有 T/W）")
    axes[0].legend(fontsize=8)

    for i, T in enumerate(sorted(d["T_ms"].unique())):
        for ident, color, lab in ((0, C_OTHER, "他人"), (1, C_SELF, "自我")):
            rt = d.loc[(d["T_ms"] == T) & (d["is_self"] == ident), "rt_ms"].to_numpy()
            if rt.size:
                axes[1].hist(rt, bins=bins, density=True, histtype="step", lw=1.6,
                             color=color, alpha=0.85 if ident == 1 else 0.55,
                             label=f"T={T:.0f} ms {lab}")
    axes[1].set_xlabel("RT（ms）")
    axes[1].set_title("按刺激呈现时长 T 拆开")
    axes[1].legend(fontsize=6.5, ncol=2)
    if title:
        fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 2. RT 分位曲线
# ----------------------------------------------------------------------
def plot_rt_quantiles(df: pd.DataFrame, out: Path, title: str = "") -> Path:
    d = _responded(df)
    Ts = sorted(d["T_ms"].unique())
    fig, axes = plt.subplots(1, len(Ts), figsize=(3.0 * len(Ts) + 0.6, 3.8),
                             sharey=True, squeeze=False)
    axes = axes.ravel()
    for ax, T in zip(axes, Ts):
        for ident, color, lab in ((0, C_OTHER, "他人"), (1, C_SELF, "自我")):
            rt = d.loc[(d["T_ms"] == T) & (d["is_self"] == ident), "rt_ms"].to_numpy()
            if rt.size < 10:
                continue
            q = np.quantile(rt, QUANTS)
            ax.plot(QUANTS, q, "o-", ms=4, lw=1.8, color=color, label=lab)
        ax.set_title(f"T = {T:.0f} ms", fontsize=10)
        ax.set_xlabel("RT 分位数")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("RT（ms）")
    axes[0].legend(fontsize=8)
    if title:
        fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 3. 正确率 / 遗漏率
# ----------------------------------------------------------------------
def plot_accuracy_omission(df: pd.DataFrame, out: Path, title: str = "") -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 3.9))
    for ax, key, xlab in ((axes[0], "T_ms", "刺激呈现时长 T（ms）"),
                          (axes[1], "W_ms", "反应期限 W（ms）")):
        xs = sorted(df[key].unique())
        for ident, color, lab, mk in ((0, C_OTHER, "他人", "s"), (1, C_SELF, "自我", "o")):
            accs, oms = [], []
            for x in xs:
                sub = df[(df[key] == x) & (df["is_self"] == ident)]
                resp = sub[sub["omission"] == 0]
                accs.append(resp["correct"].mean() if len(resp) else np.nan)
                oms.append(sub["omission"].mean() if len(sub) else np.nan)
            ax.plot(xs, accs, mk + "-", color=color, lw=2, ms=6, label=f"{lab} 正确率")
            ax.plot(xs, oms, mk + "--", color=color, lw=1.4, ms=5, alpha=0.8,
                    label=f"{lab} 遗漏率")
        ax.set_xlabel(xlab)
        ax.set_ylabel("概率")
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7.5, ncol=2)
    axes[0].set_title("正确率 / 遗漏率 随刺激时长 T")
    axes[1].set_title("正确率 / 遗漏率 随反应期限 W")
    if title:
        fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 4. CRF（条件正确率函数）
# ----------------------------------------------------------------------
def crf_table(df: pd.DataFrame, n_bins: int = 5,
              within: tuple[str, ...] = ("T_ms", "W_ms")) -> pd.DataFrame:
    """逐被试**在条件内**分 RT 分位箱后汇总（口径同旧项目的 observed_crf）。

    ⚠️ 必须在条件内分箱：若把 T/W 混在一起分箱，长 RT 主要来自「长 W + 低漂移」，
    这些条件本身正确率就低，CRF 会被人为压平（这一版的第一稿就踩了这个坑）。
    控制到 ``T × W`` 之后剩下的 RT 变异才只反映**试次内噪声**。
    """
    d = _responded(df)
    keys = ["subject_id"] + list(within) + ["is_self"]
    rows = []
    for gk, sub in d.groupby(keys):
        if len(sub) < n_bins:
            continue
        edges = np.unique(np.quantile(sub["rt_ms"], np.linspace(0, 1, n_bins + 1)))
        if edges.size < 2:
            continue
        idx = np.clip(np.searchsorted(edges, sub["rt_ms"], side="right") - 1,
                      0, edges.size - 2)
        sid, ident = gk[0], gk[-1]
        for b in range(edges.size - 1):
            m = idx == b
            if m.sum() == 0:
                continue
            rows.append({"subject_id": sid, "is_self": int(ident), "bin": b + 1,
                         "n": int(m.sum()), "rt_mean_ms": float(sub.loc[m, "rt_ms"].mean()),
                         "p_correct": float(sub.loc[m, "correct"].mean())})
    per = pd.DataFrame(rows)
    if per.empty:
        return per
    agg = (per.groupby(["is_self", "bin"])
           .agg(n=("n", "sum"), rt_mean_ms=("rt_mean_ms", "mean"),
                p_correct=("p_correct", "mean"),
                sd=("p_correct", "std"), n_subj=("p_correct", "size"))
           .reset_index())
    agg["se"] = agg["sd"] / np.sqrt(agg["n_subj"].clip(lower=1))
    agg["ci_lo"] = (agg["p_correct"] - 1.96 * agg["se"]).clip(0, 1)
    agg["ci_hi"] = (agg["p_correct"] + 1.96 * agg["se"]).clip(0, 1)
    return agg


def plot_crf(df: pd.DataFrame, out: Path, title: str = "", n_bins: int = 5) -> Path:
    agg = crf_table(df, n_bins=n_bins)
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    if agg.empty:
        ax.text(0.5, 0.5, "样本不足", ha="center", va="center")
        return _save(fig, out)
    for ident, color, lab in ((0, C_OTHER, "他人"), (1, C_SELF, "自我")):
        sub = agg[agg["is_self"] == ident].sort_values("bin")
        if sub.empty:
            continue
        ax.errorbar(sub["rt_mean_ms"], sub["p_correct"],
                    yerr=[sub["p_correct"] - sub["ci_lo"], sub["ci_hi"] - sub["p_correct"]],
                    fmt="o-", color=color, lw=2, ms=6, capsize=3, label=lab)
    ax.set_xlabel("RT 分箱均值（ms）")
    ax.set_ylabel("该箱内的正确率 P(correct)")
    ax.set_title(title or "CRF（条件正确率函数）：按 RT 五分位分箱")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 5. delta 图
# ----------------------------------------------------------------------
def plot_delta(df: pd.DataFrame, out: Path, title: str = "") -> Path:
    """他人 − 自我 在各 RT 分位上的差（逐被试算，再跨被试平均；误差条 = 95% CI）。"""
    d = _responded(df)
    per_sub = {}
    for sid, sub in d.groupby("subject_id"):
        a = sub.loc[sub["is_self"] == 1, "rt_ms"].to_numpy()
        b = sub.loc[sub["is_self"] == 0, "rt_ms"].to_numpy()
        if a.size < 20 or b.size < 20:
            continue
        per_sub[sid] = np.quantile(b, QUANTS) - np.quantile(a, QUANTS)
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    if not per_sub:
        ax.text(0.5, 0.5, "样本不足", ha="center", va="center")
        return _save(fig, out)
    M = np.vstack(list(per_sub.values()))
    mean = M.mean(axis=0)
    sem = M.std(axis=0, ddof=1) / np.sqrt(M.shape[0])
    ax.axhline(0, color="0.5", lw=1, ls=":")
    ax.errorbar(QUANTS, mean, yerr=1.96 * sem, fmt="o-", color="#6a3d9a",
                lw=2, ms=6, capsize=3)
    ax.set_xlabel("RT 分位数")
    ax.set_ylabel("ΔRT = 他人 − 自我（ms）")
    ax.set_title(title or f"delta 图（{M.shape[0]} 名被试；正 = 自我更快）")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 6. 机制图：三模型的漂移轨迹
# ----------------------------------------------------------------------
def plot_mechanism(out: Path, model: str, rho: float = 0.8, tau_ramp: float = 0.08,
                   T_levels=(2 / 60, 5 / 60, 9 / 60, 15 / 60),
                   d_stim: float = 1.0, title: str = "") -> Path:
    """把三条模型的 d(t) 画在同一张图上：掩蔽发生处、斜坡爬升、ρ 打折。"""
    t = np.linspace(0, 0.45, 1200)
    T_ex = 9 / 60                                   # 示例：T = 150 ms
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 3.9),
                             gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    specs = [("M-T1", "#1f77b4", "阶跃 + ρ"), ("M-T2", "#d62728", "斜坡 + ρ"),
             ("M-T3", "#2ca02c", "阶跃，无掩蔽效应")]
    for name, color, lab in specs:
        if name == "M-T2":
            g = 1.0 - np.exp(-t / tau_ramp)
            d = np.where(t <= T_ex, d_stim * g, d_stim * (1 - np.exp(-T_ex / tau_ramp)))
        elif name == "M-T3":
            d = np.full_like(t, d_stim)
        else:
            d = np.where(t <= T_ex, d_stim, d_stim)
            d = np.where(t > T_ex, d_stim * rho, d_stim)
        ax.plot(t * 1000, d, lw=2.2, color=color, label=f"{name}（{lab}）",
                alpha=1.0 if name == model else 0.45)
    ax.axvline(T_ex * 1000, color="0.35", ls="--", lw=1)
    ax.annotate("刺激结束 → 掩蔽", xy=(T_ex * 1000, d_stim * 0.35),
                xytext=(T_ex * 1000 + 55, d_stim * 0.18), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8, color="0.35"))
    ax.set_xlabel("试次内时间 t（ms）")
    ax.set_ylabel("漂移率 d(t)（任意单位）")
    ax.set_title("三条模型的漂移轨迹（示例 T = 150 ms，ρ = 0.8）")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.25)

    ax = axes[1]
    for T in T_levels:
        if model == "M-T2":
            g = 1.0 - np.exp(-t / tau_ramp)
            d = np.where(t <= T, d_stim * g, d_stim * (1 - np.exp(-T / tau_ramp)))
        elif model == "M-T3":
            d = np.full_like(t, d_stim)
        else:
            d = np.where(t > T, d_stim * rho, d_stim)
        ax.plot(t * 1000, d, lw=1.8, color=T_COLORS[list(T_levels).index(T)],
                label=f"T = {T*1000:.0f} ms")
    ax.set_xlabel("试次内时间 t（ms）")
    ax.set_title(f"{model}：4 个 T 水平的漂移轨迹")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    if title:
        fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 跨模型对照
# ----------------------------------------------------------------------
def plot_model_compare(dfs: dict[str, pd.DataFrame], out: Path) -> Path:
    """同一真值/设计下，三模型的行为差异 ⇒ 它们可区分。"""
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 3.9))
    styles = {"M-T1": ("#1f77b4", "o"), "M-T2": ("#d62728", "s"), "M-T3": ("#2ca02c", "^")}

    ax = axes[0]
    for name, df in dfs.items():
        color, mk = styles.get(name, ("0.4", "o"))
        xs = sorted(df["T_ms"].unique())
        acc = []
        for T in xs:
            sub = df[(df["T_ms"] == T) & (df["omission"] == 0)]
            acc.append(sub["correct"].mean())
        ax.plot(xs, acc, mk + "-", color=color, lw=2, ms=6, label=name)
    ax.set_xlabel("刺激呈现时长 T（ms）")
    ax.set_ylabel("正确率（已响应试次）")
    ax.set_title("正确率随 T：模型的 T 效应不同")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    for name, df in dfs.items():
        color, mk = styles.get(name, ("0.4", "o"))
        d = _responded(df)
        per = []
        for sid, sub in d.groupby("subject_id"):
            a = sub.loc[sub["is_self"] == 1, "rt_ms"].to_numpy()
            b = sub.loc[sub["is_self"] == 0, "rt_ms"].to_numpy()
            if a.size > 20 and b.size > 20:
                per.append(np.quantile(b, QUANTS) - np.quantile(a, QUANTS))
        if not per:
            continue
        M = np.vstack(per)
        ax.plot(QUANTS, M.mean(axis=0), mk + "-", color=color, lw=2, ms=5, label=name)
    ax.axhline(0, color="0.5", lw=1, ls=":")
    ax.set_xlabel("RT 分位数")
    ax.set_ylabel("ΔRT（他人 − 自我，ms）")
    ax.set_title("SPE 的效应形状")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2]
    for name, df in dfs.items():
        color, mk = styles.get(name, ("0.4", "o"))
        agg = crf_table(df)
        sub = agg[(agg["is_self"] == 1)].sort_values("bin")
        if sub.empty:
            continue
        ax.plot(sub["rt_mean_ms"], sub["p_correct"], mk + "-", color=color,
                lw=2, ms=5, label=f"{name} 自我")
    ax.set_xlabel("RT 分箱均值（ms）")
    ax.set_ylabel("P(correct)")
    ax.set_title("CRF（自我试次）：慢试次更准")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


# ----------------------------------------------------------------------
# 一键
# ----------------------------------------------------------------------
def make_all(model: str, df: pd.DataFrame, out_dir: Path,
             rho: float = 0.8, tau_ramp: float = 0.08) -> list[Path]:
    """给一个模型出全套图（写到 ``out_dir/figures``），返回文件清单。"""
    figdir = Path(out_dir) / "figures"
    tag = f"{model}（模拟数据，非人类被试）"
    paths = [
        plot_rt_density(df, figdir / "fig1_rt_density.png", title=tag),
        plot_rt_quantiles(df, figdir / "fig2_rt_quantiles.png", title=tag),
        plot_accuracy_omission(df, figdir / "fig3_accuracy_omission.png", title=tag),
        plot_crf(df, figdir / "fig4_crf.png", title=f"{model}：CRF（条件正确率函数）"),
        plot_delta(df, figdir / "fig5_delta.png", title=f"{model}：delta 图（他人 − 自我）"),
        plot_mechanism(figdir / "fig6_mechanism.png", model, rho=rho, tau_ramp=tau_ramp,
                       title=f"{model}：漂移轨迹"),
    ]
    # CRF 的数值表也存一份（论文里要报数）
    agg = crf_table(df)
    if not agg.empty:
        p = figdir.parent / "crf_table.csv"
        agg.to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    return paths


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    import gen_model_data as G

    ap = argparse.ArgumentParser(description="给生成的数据出图")
    ap.add_argument("--model", default="all")
    ap.add_argument("--root", default=str(G.DEFAULT_OUT))
    a = ap.parse_args(argv)

    root = Path(a.root)
    models = list(G.MODELS) if a.model == "all" else [a.model]
    dfs = {}
    for m in models:
        d = root / m
        if not (d / "trials_long.csv").exists():
            print(f"[skip] {m}：{d} 下没有 trials_long.csv")
            continue
        df = G.load_trials(d)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        figs = make_all(m, df, d, rho=meta.get("rho", 0.8),
                        tau_ramp=meta.get("tau_ramp") or 0.08)
        print(f"[{m}] {len(figs)} 个产物 → {d / 'figures'}")
        dfs[m] = df
    if len(dfs) >= 2:
        out = root / "_compare" / "fig7_model_compare.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        p = plot_model_compare(dfs, out)
        print(f"[compare] → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
