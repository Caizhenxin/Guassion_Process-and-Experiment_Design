"""真实数据（New_Design，20 人 = 4 组 × 5 人）的质检 + 描述统计 + SPE 效应量 + 成图。

只用 numpy / pandas / matplotlib。产物：
  数据  -> 2_Data/Generate_Data/_real_check/{trial_clean.csv, qc_session.csv,
            qc_cell.csv, spe_per_subject.csv, spe_summary.csv, spe_by_p.csv,
            desc_cell.csv, tradeoff_point.csv, meta.json}
  图    -> 3_Figures/_real_check/fig_r1..fig_r6

用法：
  python -X utf8 1_Code/Experiment/real_data_check.py
  python -X utf8 1_Code/Experiment/real_data_check.py --data <dir> --out <dir> --figout <dir>
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
DATA_DEFAULT = ROOT / "2_Data" / "Real_Data" / "New_Design"
OUT_DEFAULT = ROOT / "2_Data" / "Generate_Data" / "_real_check"
FIG_DEFAULT = ROOT / "3_Figures" / "_real_check"
FAMILIES = ROOT / "2_Data" / "Generate_Data" / "_families" / "families.csv"

QUANT = (0.1, 0.3, 0.5, 0.7, 0.9)
C_SELF, C_OTHER = "#c0392b", "#2c6fbb"


# ---------------------------------------------------------------- 读入与清洗
def load_trials(data: Path) -> pd.DataFrame:
    frames = []
    for c in sorted(data.glob("Condition *")):
        for f in sorted(c.glob("*.csv")):
            d = pd.read_csv(f, encoding="utf-8-sig")
            d["cond_dir"] = c.name
            frames.append(d)
    if not frames:
        raise SystemExit(f"没找到 CSV：{data}")
    df = pd.concat(frames, ignore_index=True)
    num = lambda col: pd.to_numeric(df[col], errors="coerce")
    df["is_self"] = df["Label"].astype(str).str.lower().str.strip().eq("self").astype(int)
    df["responded"] = num("responded_by_deadline").fillna(0).astype(int)
    df["correct"] = num("Correct").fillna(0).astype(int)
    df["premature"] = num("premature_press").fillna(0).astype(int)
    df["rt_ms"] = num("RT") * 1000.0
    df["T_ms"] = num("T") * 1000.0
    df["W_ms"] = num("W") * 1000.0
    df["P"] = num("P")
    df["dur_dev_ms"] = (num("stimulus_dur_actual") - num("T")) * 1000.0
    df["subject_id"] = df["groupID"].astype(str) + "-" + df["subjectID"].astype(str)
    # T / W 两列存的是「本试次实际值」（每场浮点抖动），统计前归到设计档位
    df["T_lvl"] = _nearest(df["T_ms"], (33.3, 83.3, 150.0, 250.0))
    df["W_lvl"] = _nearest(df["W_ms"], (800.0, 1200.0, 1800.0))
    return df


def _nearest(x: pd.Series, levels: tuple[float, ...]) -> pd.Series:
    arr = np.asarray(levels, dtype=float)
    idx = np.abs(x.to_numpy(float)[:, None] - arr[None, :]).argmin(axis=1)
    return pd.Series(arr[idx], index=x.index)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """试次级清洗：按期响应 + RT 在 (120 ms, W+50 ms]。"""
    d = df[(df.responded == 1) & df.rt_ms.notna()].copy()
    return d[(d.rt_ms > 120) & (d.rt_ms <= d.W_ms + 50)].reset_index(drop=True)


# ---------------------------------------------------------------- 质检
def qc_session(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, sub in df.groupby("subject_id"):
        dev = sub.dur_dev_ms.abs()
        rows.append({
            "subject_id": sid, "P": float(sub.P.iloc[0]), "n_trials": len(sub),
            "dev_mean_ms": float(dev.mean()), "dev_p99_ms": float(dev.quantile(0.99)),
            "dev_max_ms": float(dev.max()), "n_dev_gt20": int((dev > 20).sum()),
            "timeout_rate": float((sub.responded == 0).mean()),
            "premature_rate": float(sub.premature.mean()),
            "acc_responded": float(sub.loc[sub.responded == 1, "correct"].mean()),
            "rt_med_ms": float(sub.loc[sub.rt_ms.notna(), "rt_ms"].median()),
        })
    return pd.DataFrame(rows).sort_values("dev_max_ms", ascending=False)


def qc_cell(df: pd.DataFrame) -> pd.DataFrame:
    d = clean(df)
    g = (d.groupby(["P", "T_lvl", "W_lvl", "is_self"])
           .agg(n=("rt_ms", "size"), acc=("correct", "mean"),
                rt_med=("rt_ms", "median"), rt_mean=("rt_ms", "mean"))
           .reset_index())
    return g


# ---------------------------------------------------------------- 描述统计
def desc_cell(df: pd.DataFrame) -> pd.DataFrame:
    d = clean(df)
    return (d.groupby(["P", "T_lvl", "W_lvl", "is_self"])
              .agg(n=("rt_ms", "size"), acc=("correct", "mean"),
                   timeout=("responded", lambda s: 1 - s.mean()),
                   rt_med=("rt_ms", "median"), rt_sd=("rt_ms", "std"))
              .reset_index())


def spe_per_subject(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sid, P), sub in d.groupby(["subject_id", "P"]):
        s, o = sub[sub.is_self == 1], sub[sub.is_self == 0]
        if len(s) < 20 or len(o) < 20:
            continue
        rec = {"subject_id": sid, "P": float(P), "n_self": len(s), "n_other": len(o),
               "acc_self": float(s.correct.mean()), "acc_other": float(o.correct.mean()),
               "rt_self_med": float(s.rt_ms.median()), "rt_other_med": float(o.rt_ms.median())}
        rec["d_acc"] = rec["acc_self"] - rec["acc_other"]
        rec["d_timeout"] = float((1 - o.responded.mean()) - (1 - s.responded.mean())) \
            if False else float(0.0)  # 占位：d 只在响应试次内算
        for q in QUANT:
            rec[f"drt_q{int(q*100)}"] = float(np.quantile(o.rt_ms, q) - np.quantile(s.rt_ms, q))
        rec["drt_med"] = float(o.rt_ms.median() - s.rt_ms.median())
        rec["slope"] = rec["drt_q90"] - rec["drt_q10"]
        rows.append(rec)
    return pd.DataFrame(rows)


def t_ci(x: np.ndarray) -> tuple[float, float]:
    n = len(x)
    se = float(x.std(ddof=1) / math.sqrt(n))
    return float(x.mean() - 1.96 * se), float(x.mean() + 1.96 * se)


def boot_ci(x: np.ndarray, n: int = 20000, seed: int = 20261024) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def spe_summary(per: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key in ("d_acc", "drt_q10", "drt_q30", "drt_q50", "drt_q70", "drt_q90", "slope"):
        x = per[key].to_numpy(float)
        lo, hi = t_ci(x)
        rows.append({"metric": key, "n": len(x), "mean": float(x.mean()),
                     "sd": float(x.std(ddof=1)), "se": float(x.std(ddof=1) / math.sqrt(len(x))),
                     "ci_lo": lo, "ci_hi": hi,
                     "ci_lo_boot": boot_ci(x)[0], "ci_hi_boot": boot_ci(x)[1],
                     "t": float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 图
def _style() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.dpi"] = 150
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def fig_qc(df: pd.DataFrame, qs: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    ax = axes[0]
    s = qs.sort_values("dev_max_ms")
    ax.bar(range(len(s)), s.dev_max_ms, color="#7f8c8d", label="单场最大偏差")
    ax.plot(range(len(s)), s.dev_p99_ms, "o", ms=3.2, color="#c0392b", label="99 分位")
    ax.axhline(20, ls="--", lw=1, color="#c0392b")
    ax.text(0.5, 26, "20 ms 判据", fontsize=8, color="#c0392b")
    ax.set_xlabel("场次（按最大偏差排序）"); ax.set_ylabel("|实际时长 − T| (ms)")
    ax.set_xticks(list(range(0, len(s) + 1, 5)))
    ax.set_title("① 刺激时长偏差：每场都有 1–2 个掉帧试次，均值 <3 ms")
    ax.legend(fontsize=8)

    ax = axes[1]
    by_p = df.groupby("P").agg(timeout=("responded", lambda s: 1 - s.mean()),
                              prem=("premature", "mean"), n=("responded", "size")).reset_index()
    ax.bar(by_p.P.astype(str), by_p.timeout * 100, color="#e67e22")
    for i, r in by_p.iterrows():
        ax.text(i, r.timeout * 100 + 1, f"{r.timeout*100:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, max(45, by_p.timeout.max() * 120))
    ax.set_xlabel("练习量 P（组间）"); ax.set_ylabel("超时率 (%)")
    ax.set_title("② 超时率 24–29%：W=800 ms 对这批被试偏紧")

    ax = axes[2]
    ax.bar(by_p.P.astype(str), by_p.prem * 100, color="#8e44ad")
    for i, r in by_p.iterrows():
        ax.text(i, r.prem * 100 + 0.4, f"{r.prem*100:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, max(20, by_p.prem.max() * 130))
    ax.set_xlabel("练习量 P（组间）"); ax.set_ylabel("提前按键率 (%)")
    ax.set_title("③ 提前按键 7–12%：需按期剔除")
    fig.suptitle("真实数据质检（New_Design，20 人 / 12,320 试次；模拟与统计，非人造数据）", y=1.02)
    fig.tight_layout(); fig.savefig(out / "fig_r1_qc.png", bbox_inches="tight"); plt.close(fig)


def fig_rt(df: pd.DataFrame, out: Path) -> None:
    d = clean(df)
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.4))
    ax = axes[0]
    bins = np.arange(100, 1900, 40)
    for ident, lab, col in ((0, "他人", C_OTHER), (1, "自我", C_SELF)):
        x = d.loc[d.is_self == ident, "rt_ms"].to_numpy()
        ax.hist(x, bins=bins, density=True, histtype="step", lw=1.8, color=col,
                label=f"{lab}（n={len(x)}，中位 {np.median(x):.0f} ms）")
        ax.axvline(np.median(x), color=col, ls=":", lw=1.2)
    ax.set_xlabel("RT (ms)"); ax.set_ylabel("概率密度")
    ax.set_title("① RT 分布：自我 vs 他人（合并 T/W）")
    ax.legend(fontsize=8)

    ax = axes[1]
    for T in sorted(d.T_lvl.unique()):
        for ident, ls in ((0, "--"), (1, "-")):
            x = d.loc[(d.T_lvl == T) & (d.is_self == ident), "rt_ms"]
            if len(x) < 30:
                continue
            ax.hist(x, bins=bins, density=True, histtype="step", ls=ls, lw=1.2,
                    color=C_SELF if ident else C_OTHER, alpha=0.9,
                    label=f"T={T:.0f} ms {'自我' if ident else '他人'}")
    ax.set_xlabel("RT (ms)"); ax.set_ylabel("概率密度")
    ax.set_title("② 按刺激呈现时长 T 拆开（实线自我 / 虚线他人）")
    ax.legend(fontsize=6.5, ncol=2)
    fig.tight_layout(); fig.savefig(out / "fig_r2_rt_density.png", bbox_inches="tight"); plt.close(fig)


def fig_spe_delta(per: pd.DataFrame, sm: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    qs = [10, 30, 50, 70, 90]
    mean = np.array([sm.loc[sm.metric == f"drt_q{q}", "mean"].iloc[0] for q in qs])
    lo = np.array([sm.loc[sm.metric == f"drt_q{q}", "ci_lo"].iloc[0] for q in qs])
    hi = np.array([sm.loc[sm.metric == f"drt_q{q}", "ci_hi"].iloc[0] for q in qs])
    ax.axhline(0, color="0.3", lw=1)
    ax.fill_between(qs, lo, hi, color="#8e44ad", alpha=0.16, label="95% CI（t 近似）")
    ax.plot(qs, mean, "-o", color="#8e44ad", ms=6, label="ΔRT = 他人 − 自我")
    for q, m in zip(qs, mean):
        ax.annotate(f"{m:+.0f}", (q, m), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9, color="#8e44ad")
    ax.set_xlabel("RT 分位（%）"); ax.set_ylabel("ΔRT (ms)")
    ax.set_title("SPE 的分位形状：分位越高差越大，即漂移型签名（非 t0 型平移）")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out / "fig_r3_spe_delta.png", bbox_inches="tight"); plt.close(fig)


def fig_acc(df: pd.DataFrame, out: Path) -> None:
    d = clean(df)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.3))
    for ax, key, lab in ((axes[0], "T_lvl", "刺激呈现时长 T (ms)"), (axes[1], "W_lvl", "反应期限 W (ms)")):
        for ident, col, name in ((0, C_OTHER, "他人"), (1, C_SELF, "自我")):
            g = (d[d.is_self == ident].groupby(key)
                 .agg(acc=("correct", "mean"), n=("correct", "size")).reset_index())
            se = np.sqrt(g.acc * (1 - g.acc) / g.n)
            ax.errorbar(g[key], g.acc, yerr=1.96 * se, fmt="-o", ms=5, capsize=3,
                        color=col, label=name)
        ax.set_xlabel(lab); ax.set_ylabel("正确率（响应试次内）")
        ax.legend(fontsize=8)
    axes[0].set_title("① 正确率随 T：越长越准（模型与数据同向）")
    axes[1].set_title("② 正确率随 W：期限越宽越准（被试愿意更慢更准，长 RT 尾巴也被收进来）")
    fig.tight_layout(); fig.savefig(out / "fig_r4_acc.png", bbox_inches="tight"); plt.close(fig)


def fig_spe_by_p(per: pd.DataFrame, out: Path) -> None:
    by = per.groupby("P").agg(n=("d_acc", "size"), d_acc=("d_acc", "mean"),
                              d_acc_sd=("d_acc", "std"), drt=("drt_med", "mean"),
                              drt_sd=("drt_med", "std")).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
    for ax, col_m, col_sd, lab, ttl in (
            (axes[0], "d_acc", "d_acc_sd", "Δ正确率（自我 − 他人）", "① 正确率侧 SPE 随练习量削弱（P=0 最强）"),
            (axes[1], "drt", "drt_sd", "ΔRT 中位（他人 − 自我, ms)", "② RT 侧 SPE 随练习量削弱（P=120 组回抬，非单调）")):
        se = by[col_sd] / np.sqrt(by.n)
        ax.errorbar(by.P, by[col_m], yerr=1.96 * se, fmt="-o", ms=6, capsize=3, color="#2c3e50")
        ax.axhline(0, color="0.4", lw=1, ls=":")
        ax.set_xlabel("练习量 P（组间剂量，每组 5 人）"); ax.set_ylabel(lab)
        ax.set_title(ttl + "（n=5/组，只作趋势）")
        for _, r in by.iterrows():
            ax.annotate(f"n={int(r.n)}", (r.P, r[col_m]), textcoords="offset points",
                        xytext=(0, 10), ha="center", fontsize=8, color="0.35")
    fig.tight_layout(); fig.savefig(out / "fig_r5_spe_by_p.png", bbox_inches="tight"); plt.close(fig)


def fig_tradeoff(per: pd.DataFrame, d: pd.DataFrame, out: Path, data_out: Path) -> None:
    sd_rt = float(d.rt_ms.std())
    drt = float(per.drt_med.mean())
    dacc = float(per.d_acc.mean())
    point = pd.DataFrame([{"source": "real_20p", "d_rt_med": drt, "d_acc": dacc,
                           "sd_rt": sd_rt, "vis_rt": drt / sd_rt, "n": len(per)}])
    point.to_csv(data_out / "tradeoff_point.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    if FAMILIES.exists():
        fam = pd.read_csv(FAMILIES, encoding="utf-8-sig")
        fam = fam[fam.P == 0]
        names = {"const": "只改漂移（现行）", "gate": "只改速率 r_S", "gate_drift": "速率+漂移",
                 "noise": "只改噪声", "boundary": "只改边界", "ratio": "乘性比例",
                 "ceiling": "λ 天花板", "selfsat": "自我单独饱和", "power": "幂律衰减"}
        seen: dict[tuple, list] = {}
        for _, r in fam.iterrows():
            key = (round(float(r.vis_rt), 3), round(float(r.d_acc), 3))
            seen.setdefault(key, []).append(names.get(r.family, r.family))
        offs = [(-6, -16), (10, 6), (10, -14), (-64, 8)]
        for i, ((x, y), labs) in enumerate(sorted(seen.items())):
            lab = " / ".join(labs) if len(labs) < 4 else "只改漂移族（4 支 P=0 完全同值）"
            ax.scatter(x, y, s=90, alpha=.85, zorder=3, marker="o", color="#7f8c8d")
            ax.annotate(lab, (x, y), textcoords="offset points", xytext=offs[i % len(offs)],
                        fontsize=8, color="0.25")
    ax.axhline(0, color="0.4", lw=1, ls=":")
    ax.axvline(0, color="0.4", lw=1, ls=":")
    ax.scatter(drt / sd_rt, dacc, s=260, marker="*", color="#c0392b", zorder=5,
               edgecolor="white", linewidth=1.2, label="真实数据（20 人，n=20 配对）")
    ax.annotate(f"ΔRT {drt:+.0f} ms（{drt/sd_rt:.2f} SD，SD={sd_rt:.0f} ms）\nΔacc {dacc*100:+.1f} pp",
                (drt / sd_rt, dacc), textcoords="offset points", xytext=(-158, 6),
                fontsize=9, color="#c0392b", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.4))
    ax.set_xlabel("RT 可见度 = |ΔRT 中位| / SD(RT)")
    ax.set_ylabel("Δ正确率（自我 − 他人）")
    ax.set_title("取舍平面：真实点靠「速率+漂移 / 只改噪声」，远离「只改速率」（后者 Δacc≈0）", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.95)
    fig.tight_layout(); fig.savefig(out / "fig_r6_tradeoff.png", bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_DEFAULT))
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--figout", default=str(FIG_DEFAULT))
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--drop", default="3-1",
                    help="敏感性分析里剔除的被试（逗号分隔，默认 3-1 疑似无效场次）")
    args = ap.parse_args()

    data, out, figout = Path(args.data), Path(args.out), Path(args.figout)
    out.mkdir(parents=True, exist_ok=True)
    figout.mkdir(parents=True, exist_ok=True)
    _style()

    df = load_trials(data)
    d = clean(df)
    d.to_csv(out / "trial_clean.csv", index=False, encoding="utf-8-sig")
    qs = qc_session(df); qs.to_csv(out / "qc_session.csv", index=False, encoding="utf-8-sig")
    qc_cell(df).to_csv(out / "qc_cell.csv", index=False, encoding="utf-8-sig")
    desc_cell(df).to_csv(out / "desc_cell.csv", index=False, encoding="utf-8-sig")
    per = spe_per_subject(d); per.to_csv(out / "spe_per_subject.csv", index=False, encoding="utf-8-sig")
    sm = spe_summary(per); sm.to_csv(out / "spe_summary.csv", index=False, encoding="utf-8-sig")
    by_p = (per.groupby("P").agg(n=("subject_id", "size"), d_acc=("d_acc", "mean"),
                                 drt_med=("drt_med", "mean"), slope=("slope", "mean"))
            .reset_index())
    by_p.to_csv(out / "spe_by_p.csv", index=False, encoding="utf-8-sig")

    print("=== SPE 汇总（n=20 被试，配对） ===")
    print(sm[["metric", "mean", "se", "ci_lo", "ci_hi", "t"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("\n=== 按 P ===")
    print(by_p.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("\n=== 质检（最差 5 场） ===")
    print(qs.head(5)[["subject_id", "n_trials", "dev_mean_ms", "dev_max_ms", "n_dev_gt20",
                      "timeout_rate", "premature_rate", "acc_responded", "rt_med_ms"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    # 敏感性：剔除疑似无效场次后重算（默认 3-1）
    drop = [s.strip() for s in str(args.drop).split(",") if s.strip()]
    if drop:
        per_d = per[~per.subject_id.isin(drop)]
        sm_d = spe_summary(per_d)
        sm_d.to_csv(out / "spe_summary_drop.csv", index=False, encoding="utf-8-sig")
        cmp = sm[["metric", "mean", "t"]].merge(sm_d[["metric", "mean", "t"]], on="metric",
                                               suffixes=("_全部", "_剔除"))
        print(f"\n=== 敏感性：剔除 {','.join(drop)}（n={len(per_d)}） ===")
        print(cmp.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    if not args.no_fig:
        fig_qc(df, qs, figout)
        fig_rt(df, figout)
        fig_spe_delta(per, sm, figout)
        fig_acc(df, figout)
        fig_spe_by_p(per, figout)
        fig_tradeoff(per, d, figout, out)
        print(f"\n[fig] {figout}")

    meta = {"data": str(data), "n_trials_raw": int(len(df)), "n_trials_clean": int(len(d)),
            "n_subjects": int(per.subject_id.nunique()), "n_groups": int(per.P.nunique()),
            "P_levels": sorted(per.P.unique().tolist()),
            "rt_sd_ms": float(d.rt_ms.std()), "quantiles": list(QUANT),
            "filter": "responded_by_deadline==1 且 120 < RT <= W+50 ms"}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n->", out)


if __name__ == "__main__":
    main()
