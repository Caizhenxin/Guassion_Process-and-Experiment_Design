# -*- coding: utf-8 -*-
"""把 Stage 8 的产物画成论文用的图（零新依赖：numpy + matplotlib）。

用法
====
    python -X utf8 make_figures.py <stage8_out_dir> \
        [--data <数据目录>] [--out <图目录>] [--truth <synth_truth.json>] [--lang zh|en]

产出
====
    fig1_behavior_by_P.png      行为随 P 变化（正确率、RT 中位）
    fig2_param_recovery.png     组层参数估计 vs 真值（仅合成数据有真值）
    fig3_model_comparison.png   M-T1 与 M-T3 的 elpd 对比（Δelpd）
    figures_index.md            图目录 + 每张图的读法 + 数据来源与「可否进论文」标注

设计约束
========
* **不复制判据**：行为量直接由 `read_formal_data.load_file` 读原始文件，与
  `analyze_pilot.py` / `qc_group.py` 用同一套解析口径。
* 图里必须写清数据来源（合成 / 真实）。合成数据的图**不得**进论文结果节，
  函数会在 `figures_index.md` 里逐图标注。
* 参数反变换：`fit.mu` 是**无约束**坐标的组均值，自然尺度 = `lo + (hi-lo)*expit(mu)`
  （与 `likelihood._from_x` 完全一致）；区间用同变换作用在 `mu ± 1.96·se` 上（近似）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import read_formal_data as RF                       # noqa: E402
from likelihood import _from_x                      # noqa: E402
from mapping import PARAM_BOUNDS, WITHIN_FREE_LIN   # noqa: E402
from twophase import MASK_RHO_BOUNDS                # noqa: E402

RHO_NAME = "rho"

#: 图里显示的中文/英文参数字名
LABELS = {
    "d_ref": ("漂移幅度 d_ref", "drift d_ref"),
    "beta_T": ("T 效应 beta_T", "T effect beta_T"),
    "beta_S": ("自我效应 beta_S", "self effect beta_S"),
    "beta_ST": ("自我×T beta_ST", "self×T beta_ST"),
    "a_ref": ("边界 a_ref", "boundary a_ref"),
    "delta_a": ("身份边界差 delta_a", "identity Δa"),
    "t0": ("非决策时间 t0 (s)", "non-decision t0 (s)"),
    "rho": ("掩蔽期漂移比 rho", "masked-phase rho"),
}

CJK_FONTS = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"]


def setup_matplotlib(lang: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    if lang == "zh":
        have = {f.name for f in font_manager.fontManager.ttflist}
        picked = [f for f in CJK_FONTS if f in have]
        if picked:
            plt.rcParams["font.sans-serif"] = picked + ["DejaVu Sans"]
        else:                       # 没有中文字体就退回英文，避免整图豆腐块
            lang = "en"
            print("[warn] 没有中文字体，图内文字改用英文")
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 200
    return plt, lang


def lab(key: str, lang: str) -> str:
    zh, en = LABELS.get(key, (key, key))
    return zh if lang == "zh" else en


# --------------------------------------------------------------------------- #
# 1. 行为层：直接从原始文件算
# --------------------------------------------------------------------------- #
def behavior_by_group(data_dir: Path) -> dict[int, list[dict]]:
    """{组: [{'sid','acc','rt_med','timeout','n_formal'}...]}"""
    out: dict[int, list[dict]] = {}
    for p in sorted(data_dir.rglob("*")):
        if not p.is_file():
            continue
        name = p.name
        if not (name.startswith("exp_group") or name.startswith("EXP_data_group")):
            continue
        try:
            # `load_file` 返回 (逐试次数组 dict, 报告 dict)；默认只保留正式段
            tr, _rep = RF.load_file(p)
        except Exception as exc:                       # noqa: BLE001
            print(f"[warn] 读不了 {p.name}：{exc}")
            continue
        gid = int(tr["groupID"])
        sid = int(tr["subjectID"])
        corr = np.asarray(tr["Correct"], dtype=float)
        to = np.asarray(tr["timeout"], dtype=float)
        rt = np.asarray(tr["RT"], dtype=float)
        rt = rt[np.isfinite(rt)]
        if corr.size == 0:
            continue

        item = {
            "sid": sid,
            "acc": float(np.nanmean(corr)),
            "rt_med": float(np.median(rt)) if rt.size else float("nan"),
            "timeout": float(np.nanmean(to)),
            "n_formal": int(corr.size),
        }
        out.setdefault(gid, []).append(item)
    for gid in out:
        out[gid].sort(key=lambda d: d["sid"])
    return out


def fig_behavior(plt, beh: dict[int, list[dict]], out: Path, lang: str) -> Path:
    ps = sorted(beh)
    x = np.arange(len(ps))
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))

    ax = axes[0]
    for i, g in enumerate(ps):
        accs = [d["acc"] for d in beh[g]]
        ax.scatter(np.full(len(accs), i), accs, s=26, color="0.35", zorder=3,
                   label=("个体" if lang == "zh" else "individual") if i == 0 else None)
        ax.plot([i - 0.18, i + 0.18], [np.mean(accs)] * 2, color="tab:red",
                lw=2.4, zorder=4,
                label=("组均" if lang == "zh" else "group mean") if i == 0 else None)
    ax.set_xticks(x, [f"P={0 if g == 1 else (8 if g == 2 else (32 if g == 3 else 120))}" for g in ps])
    ax.set_xlabel("P（练习试次）" if lang == "zh" else "P (practice trials)")
    ax.set_ylabel("正确率" if lang == "zh" else "accuracy")
    ax.set_ylim(0.0, 1.02)
    ax.axhline(0.5, ls=":", lw=1, color="0.6")
    ax.set_title(("正确率随 P 的变化（虚线 = 机会水平）" if lang == "zh"
                  else "Accuracy vs P (dotted = chance)"), fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.grid(alpha=0.25)

    ax = axes[1]
    for i, g in enumerate(ps):
        rts = [d["rt_med"] for d in beh[g]]
        ax.scatter(np.full(len(rts), i), rts, s=26, color="0.35", zorder=3)
        ax.plot([i - 0.18, i + 0.18], [np.mean(rts)] * 2, color="tab:blue", lw=2.4, zorder=4)
    ax.set_xticks(x, [f"P={0 if g == 1 else (8 if g == 2 else (32 if g == 3 else 120))}" for g in ps])
    ax.set_xlabel("P（练习试次）" if lang == "zh" else "P (practice trials)")
    ax.set_ylabel("RT 中位（s）" if lang == "zh" else "median RT (s)")
    ax.set_title(("RT 中位随 P 的变化" if lang == "zh" else "Median RT vs P"), fontsize=10)
    ax.grid(alpha=0.25)

    fig.suptitle(("行为层（原始数据直算，未拟合）" if lang == "zh"
                  else "Behaviour (computed from raw files)"), fontsize=11)
    fig.tight_layout()
    path = out / "fig1_behavior_by_P.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# 2. 参数恢复 / 3. 模型比较
# --------------------------------------------------------------------------- #
def load_groups(stage8_dir: Path) -> dict[int, dict]:
    out = {}
    for p in sorted(stage8_dir.glob("stage8_group_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[int(d.get("tag", p.stem.split("_")[-1]))] = d
    return out


def natural(mu: float, se: float, lo: float, hi: float) -> tuple[float, float, float]:
    v = float(_from_x(np.array([mu]), np.array([lo]), np.array([hi]))[0])
    v_lo = float(_from_x(np.array([mu - 1.96 * se]), np.array([lo]), np.array([hi]))[0])
    v_hi = float(_from_x(np.array([mu + 1.96 * se]), np.array([lo]), np.array([hi]))[0])
    return v, v_lo, v_hi


def fig_recovery(plt, groups: dict[int, dict], truth: dict | None, out: Path,
                 lang: str) -> Path:
    """组层参数恢复图。

    ⚠️ 区间口径：`fit.covs[s]` 是**单个被试**在其众数处的拉普拉斯协方差，
    不是组均值的标准误；把它当组层区间会低估/高估且语义错误。
    这里改画**被试层估计**（每个被试自己的众数）+ 组均值 ± 被试间 SEM，
    语义明确、也不依赖任何近似。
    """
    names = list(WITHIN_FREE_LIN) + [RHO_NAME]
    bounds = dict(PARAM_BOUNDS)
    bounds[RHO_NAME] = MASK_RHO_BOUNDS

    ps = sorted(groups)
    fig, axes = plt.subplots(2, 4, figsize=(12.0, 5.4), sharex=True)
    for ax, name in zip(axes.ravel(), names):
        lo, hi = bounds[name]
        for i, g in enumerate(ps):
            res = (groups[g].get("results") or {}).get("M-T1") or {}
            fit = res.get("fit") or {}
            modes = np.asarray(fit.get("modes") or [], dtype=float)
            if modes.ndim != 2 or modes.size == 0:
                continue
            j = (WITHIN_FREE_LIN.index(name) if name in WITHIN_FREE_LIN
                 else (len(WITHIN_FREE_LIN) if res.get("rho_free") else None))
            if j is None or j >= modes.shape[1]:
                continue
            vals = np.asarray([natural(float(m[j]), 0.0, lo, hi)[0] for m in modes])
            ax.scatter(np.full(vals.size, i), vals, s=22, color="0.45", zorder=3)
            if vals.size >= 2:
                m = float(np.mean(vals))
                sem = float(np.std(vals, ddof=1) / np.sqrt(vals.size))
                ax.errorbar([i], [m], yerr=[[sem], [sem]], fmt="o", ms=6,
                            color="tab:blue", capsize=4, zorder=4)
            else:
                ax.plot([i], [float(vals.mean())], "o", ms=6, color="tab:blue", zorder=4)
        if truth is not None:
            tv = truth.get(name)
            if tv is not None:
                ax.axhline(float(tv), ls="--", lw=1.2, color="tab:red")
        ax.set_xticks(range(len(ps)), [str(g) for g in ps])
        ax.set_title(lab(name, lang), fontsize=9)
        ax.grid(alpha=0.25)

    axes.ravel()[0].set_ylabel(("估计值（自然尺度）" if lang == "zh" else "estimate"))
    axes.ravel()[4].set_ylabel(("估计值（自然尺度）" if lang == "zh" else "estimate"))
    for ax in axes.ravel()[4:]:
        ax.set_xlabel(("组（1–4）" if lang == "zh" else "group (1–4)"))
    fig.suptitle(("组层参数估计 vs 真值（灰点 = 被试、蓝点 = 组均值 ± 被试间 SEM）" if lang == "zh"
                  else "Group estimates vs truth (grey = subjects, blue = mean ± SEM)"), fontsize=10)
    fig.tight_layout()
    path = out / "fig2_param_recovery.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def paired_se(a: dict, b: dict) -> float:
    """Δelpd 的**配对**标准误（PSIS-LOO 口径）。

    两个模型在同一批观测上算 LOO，`elpd_i` 是逐观测贡献，因此
    Δ 的 SE = sqrt(n) · sd(elpd_i^A − elpd_i^B)（Vehtari 等 2017 的
    `se_diff`），**不能**把两个 SE 平方相加——那样把「同一批数据的
    共同变异」算了两遍，会把区间放大到接近 √2 倍甚至更多。
    """
    ea = a.get("elpd_i")
    eb = b.get("elpd_i")
    if ea is None or eb is None or len(ea) != len(eb) or not ea:
        return float("nan")
    d = np.asarray(ea, dtype=float) - np.asarray(eb, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 2:
        return float("nan")
    return float(np.sqrt(d.size) * np.std(d, ddof=1))


def fig_model_cmp(plt, groups: dict[int, dict], out: Path, lang: str) -> tuple[Path, dict]:
    ps = sorted(groups)
    d_elpd, se, kdiag, se_kind = [], [], [], []
    for g in ps:
        res = groups[g].get("results") or {}
        a = (res.get("M-T1") or {}).get("loo") or {}
        b = (res.get("M-T3") or {}).get("loo") or {}
        ea = float(a.get("elpd_loo", float("nan")))
        eb = float(b.get("elpd_loo", float("nan")))
        d_elpd.append(ea - eb)
        s = paired_se(a, b)
        if np.isfinite(s):
            se_kind.append("paired")
        else:                      # 拿不到逐观测贡献才退回（并显式标注）
            sa = float(a.get("se", float("nan")))
            sb = float(b.get("se", float("nan")))
            s = float(np.sqrt(np.nansum([sa ** 2, sb ** 2])))
            se_kind.append("unpaired")
        se.append(s)
        kdiag.append(bool(a.get("k_diag_ok", False)) and bool(b.get("k_diag_ok", False)))

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = np.arange(len(ps))
    vals = np.array(d_elpd, dtype=float)
    errs = np.array(se, dtype=float)
    colors = ["tab:green" if v > 0 else "tab:red" for v in vals]
    ax.bar(x, vals, color=colors, width=0.55)
    if np.all(np.isfinite(errs)):
        ax.errorbar(x, vals, yerr=errs, fmt="none", ecolor="0.3", capsize=3, lw=1)
    ax.axhline(0, color="0.3", lw=1)
    ax.set_xticks(x, [f"组 {g}" if lang == "zh" else f"group {g}" for g in ps])
    ax.set_ylabel(("Δelpd (M-T1 − M-T3)" if lang == "zh" else "Δelpd (M-T1 − M-T3)"))
    ax.set_title(("模型比较：越大越支持两阶段（M-T1）" if lang == "zh"
                  else "Model comparison: larger ⇒ two-phase (M-T1) preferred"), fontsize=10)
    if not all(kdiag):
        note = ("(!) 抽样数 < 25 -> Pareto k 诊断不可用，本图只作流程验证"
                if lang == "zh" else
                "(!) draws < 25 -> Pareto-k diagnostics unavailable; smoke check only")
        ax.text(0.02, 0.02, note, transform=ax.transAxes, fontsize=7.5, color="tab:red")
    if "unpaired" in se_kind:
        note = ("(!) 分不出逐观测贡献 -> Δ 的 SE 按独立相加，偏大"
                if lang == "zh" else
                "(!) pointwise contributions missing -> SE of Δ summed as independent (too wide)")
        ax.text(0.02, 0.14, note, transform=ax.transAxes, fontsize=7.5, color="tab:orange")
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    path = out / "fig3_model_comparison.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path, {"d_elpd": vals.tolist(), "se": errs.tolist(), "k_diag_ok": kdiag,
                  "se_kind": se_kind}


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 8 产物 → 论文图")
    ap.add_argument("stage8_dir")
    ap.add_argument("--data", default=None, help="原始数据目录（默认 = stage8 目录的上一级）")
    ap.add_argument("--out", default=None, help="图输出目录（默认 = stage8 目录/figures）")
    ap.add_argument("--truth", default=None, help="合成数据真值 JSON（真有数据时不给）")
    ap.add_argument("--lang", choices=("zh", "en"), default="zh")
    args = ap.parse_args()

    s8 = Path(args.stage8_dir)
    if not s8.is_dir():
        print(f"[FAIL] 不是目录：{s8}", file=sys.stderr)
        return 2
    data = Path(args.data) if args.data else s8.parent
    out = Path(args.out) if args.out else (s8 / "figures")
    out.mkdir(parents=True, exist_ok=True)

    truth = None
    if args.truth:
        t = json.loads(Path(args.truth).read_text(encoding="utf-8"))
        gt = t.get("group_truth") or {}
        first = next(iter(gt.values()), None)
        if isinstance(first, dict):
            truth = first
            truth.setdefault("rho", (t.get("params") or {}).get("rho"))
        print(f"[truth] {args.truth}（合成数据）")

    plt, lang = setup_matplotlib(args.lang)
    groups = load_groups(s8)
    if not groups:
        print(f"[FAIL] {s8} 下没有 stage8_group_*.json", file=sys.stderr)
        return 2

    figs = []
    beh = behavior_by_group(data) if data.is_dir() else {}
    if beh:
        figs.append(("fig1_behavior_by_P.png", fig_behavior(plt, beh, out, lang),
                     "行为层：正确率与 RT 中位随 P 的变化（原始文件直算，不经过任何拟合）"))
    else:
        print("[warn] 数据目录里没读到正式文件，跳过 fig1")

    figs.append(("fig2_param_recovery.png", fig_recovery(plt, groups, truth, out, lang),
                 "组层参数估计（自然尺度）；灰点 = 被试层众数、蓝点 = 组均值 ± 被试间 SEM；红虚线 = 合成真值（真数据没有）"))
    p3, cmp_stats = fig_model_cmp(plt, groups, out, lang)
    figs.append(("fig3_model_comparison.png", p3,
                 "模型比较：Δelpd = elpd(M-T1) − elpd(M-T3)；正值支持两阶段"))

    kind = "合成数据（仅流程验证）" if truth is not None else "真实数据"
    lines = ["# 图目录", "", f"- 数据来源：**{kind}**", f"- Stage 8 目录：`{s8}`", ""]
    for name, path, desc in figs:
        lines += [f"## {name}", "", f"![{name}]({name})", "", desc, "",
                  f"- 文件：`{path}`", ""]
    lines += ["## 模型比较数值", "", "| 组 | Δelpd | SE | Pareto k 诊断可用 |", "|---|---|---|---|"]
    for i, g in enumerate(sorted(groups)):
        lines.append(f"| {g} | {cmp_stats['d_elpd'][i]:.1f} | {cmp_stats['se'][i]:.1f} | "
                     f"{'是' if cmp_stats['k_diag_ok'][i] else '否（抽样数 < 25）'} |")
    lines += ["", "> 合成数据的图**不得**进入论文结果节；它们只证明「流水线能跑通」。", ""]
    (out / "figures_index.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    for name, path, _ in figs:
        print(f"[ok] {name}  ← {path}")
    print(f"[ok] figures_index.md ← {out / 'figures_index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
