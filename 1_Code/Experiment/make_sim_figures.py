#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""论文级**模拟图**：不需要任何真实被试数据。

出三张图（可直接进论文的方法章 / 识别性与功效章）：

* ``fig_sim_crlb.png``    **CRLB**：组层参数相对精度（SE/真值）随组人数的变化，
  并标出达到 10% / 25% 需要的组人数。数据来自 ``design_fim.design_se``
  （OPG 信息矩阵求逆，576 试次 = 4 T × 3 W × 4 种 × 12 次）。
* ``fig_sim_p_design.png`` **P 水平设计的识别力**（oracle：用被试层真值做组间回归，
  无 DDM 拟合），比较 4 水平 / 7 水平 / 3 水平三套 P 方案在 6–50 人/组下的
  `beta_P` 与 `tau_P` 相对 RMSE。
* ``fig_sim_trials.png``   **试次级生成数据**：按真值参数用 M-T1（含 rho=0.8 的
  掩蔽期漂移）Euler 路径模拟生成一名被试的 576 个试次，展示 RT 分位数、
  RT 分布、以及正确率 / 遗漏率随 T 的变化。

为什么这三张能进论文
--------------------
它们全部是**模型与设计的性质**，与「有没有收数据」无关：
* CRLB 是参数精度的下界 ⇒ 支撑「每组 40 人」的样本量论证；
* oracle 识别力说明「P 取 0/8/32/120」这四档足以估出饱和曲线；
* 试次级模拟图是「模型能生成什么样的数据」的阳性对照，属于方法章的证据。

⚠️ 与真实数据的边界（D104 纪律一）：本脚本一切输出**不得**写进结果章；
它们只能进方法章 / 识别性与功效章，且图注必须写明「模拟」。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent            # 1_Code/Experiment
_CODE = _HERE.parents[0]                           # 1_Code
for _p in (str(_CODE / "DDM_Core"), str(_CODE / "DDM_Core" / "_scratch"), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from make_figures import setup_matplotlib           # noqa: E402  复用中文字体探测

T_LEVELS = [2 / 60, 5 / 60, 9 / 60, 15 / 60]
W_LEVELS = [48 / 60, 72 / 60, 108 / 60]
N_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30, 40, 48]
KEY_PARAMS = ["d_ref", "beta_T", "beta_S", "beta_ST"]

ZH = {
    "d_ref": "漂移幅度 d_ref", "beta_T": "T 效应 beta_T", "beta_S": "自我效应 beta_S",
    "beta_ST": "自我×T beta_ST", "a_ref": "边界 a_ref", "delta_a": "身份边界差 delta_a",
    "tau_a": "边界时间常数 tau_a", "tau_T": "T 饱和常数 tau_T", "t0": "非决策时间 t0",
    "beta_P": "P 效应 beta_P", "tau_P": "P 饱和常数 tau_P",
    "n": "组人数 n（每组）", "rel": "相对精度（SE / 真值，%）",
    "rel_rmse": "相对 RMSE（RMSE / 真值）", "rt": "RT（ms）", "p": "概率",
    "quant": "RT 分位数", "acc": "正确率", "om": "遗漏率（未在期限内响应）",
    "density": "试次密度", "T": "刺激时长 T（帧 / ms）",
}
EN = {
    "d_ref": "drift d_ref", "beta_T": "T effect beta_T", "beta_S": "self effect beta_S",
    "beta_ST": "self x T beta_ST", "a_ref": "boundary a_ref", "delta_a": "identity delta_a",
    "tau_a": "boundary tau_a", "tau_T": "T saturation tau_T", "t0": "non-decision t0",
    "beta_P": "P effect beta_P", "tau_P": "P saturation tau_P",
    "n": "subjects per group", "rel": "relative precision (SE / truth, %)",
    "rel_rmse": "relative RMSE (RMSE / truth)", "rt": "RT (ms)", "p": "probability",
    "quant": "RT quantile", "acc": "accuracy", "om": "timeout rate",
    "density": "trial density", "T": "stimulus duration T (frames / ms)",
}


def L(key: str, lang: str) -> str:
    return (ZH if lang == "zh" else EN).get(key, key)


# --------------------------------------------------------------------------- #
# 1. CRLB
# --------------------------------------------------------------------------- #
def crlb(n_fim: int) -> dict:
    import design_fim as DF

    res = DF.design_se(T_LEVELS, W_LEVELS, 12, n_fim=n_fim)
    truth = DF.TRUTH.as_dict()
    se = {n: float(res["se"][i]) for i, n in enumerate(DF.NAMES)}
    return {"se": se, "truth": truth, "n_trials": int(res["n_trials"]),
            "acc": float(res["acc"]), "omission": float(res["omission"]),
            "rt_ms": float(res["rt_ms"]), "names": list(DF.NAMES)}


def n_for_target(c: dict, name: str, target: float) -> int | None:
    """组层相对 SE 达到 target 所需的最小组人数。"""
    se = c["se"][name]
    tv = abs(c["truth"][name])
    if tv <= 0 or se <= 0:
        return None
    n = (se / target / tv) ** 2
    return int(np.ceil(n))


def fig_crlb(plt, c: dict, out: Path, lang: str) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    n_arr = np.array(N_GRID, float)
    for ax, names, title in (
        (axes[0], c["names"], "全部 9 个被试层参数" if lang == "zh" else "all 9 within-subject parameters"),
        (axes[1], KEY_PARAMS, "四个关键参数（10% 与 25% 参考线）" if lang == "zh"
         else "four key parameters (10% / 25% reference lines)"),
    ):
        for name in names:
            rel = [100.0 * c["se"][name] / np.sqrt(n) / abs(c["truth"][name]) for n in n_arr]
            lw = 2.0 if name in KEY_PARAMS else 1.1
            ax.plot(n_arr, rel, marker="o", ms=3.2, lw=lw, label=L(name, lang))
        ax.set_yscale("log")
        ax.set_xlabel(L("n", lang))
        ax.set_ylabel(L("rel", lang))
        ax.set_title(title)
        ax.grid(alpha=0.3, which="both")
        ax.set_xlim(0.5, max(n_arr) + 2)
    ax = axes[1]
    ax.axhline(10, color="tab:red", ls="--", lw=1.0,
               label="10%（设计目标）" if lang == "zh" else "10% target")
    ax.axhline(25, color="tab:orange", ls=":", lw=1.0,
               label="25%（仅能粗解释）" if lang == "zh" else "25% coarse")
    for name, target, dx, dy in (("d_ref", 10, 1.0, 1.9), ("beta_T", 10, -4.0, 1.9),
                                 ("beta_S", 10, 2.0, 0.50)):
        need = n_for_target(c, name, target / 100.0)
        if need and need <= max(N_GRID):
            ax.annotate((f"{L(name, lang).split()[0]}：{need} 人" if lang == "zh"
                         else f"{name}: n={need}"),
                        xy=(need, target), xytext=(need + dx, target * dy),
                        fontsize=7.5, color="0.2", ha="center",
                        arrowprops=dict(arrowstyle="-", color="0.65", lw=0.7))
    axes[0].legend(fontsize=7, ncol=2, loc="upper right")
    axes[1].legend(fontsize=8, loc="upper right")
    fig.suptitle("参数精度的 Cramér–Rao 下界：每组多少人才能把参数压到 10%"
                 if lang == "zh"
                 else "Cramer-Rao bound on parameter precision (simulated, 576 trials/subject)",
                 fontsize=12)
    fig.tight_layout()
    p = out / "fig_sim_crlb.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# --------------------------------------------------------------------------- #
# 2. P 水平设计的识别力（oracle）
# --------------------------------------------------------------------------- #
SCENARIOS = [
    ("当前推荐：P = 0/8/32/120（4 水平）", "current: P = 0/8/32/120 (4 levels)", [0, 8, 32, 120]),
    ("加密：7 个 P 水平", "denser: 7 P levels", [0, 4, 8, 16, 32, 64, 120]),
    ("文献常见：3 个 P 水平", "common: 3 P levels", [0, 32, 120]),
]
ORACLE_NS = [6, 12, 20, 30, 40, 50]


def oracle_table(n_rep: int) -> list[dict]:
    import oracle_power as OP

    rows = []
    for zh, _en, levels in SCENARIOS:
        for n in ORACLE_NS:
            r = OP.evaluate(levels, n, n_rep=n_rep)
            rows.append({
                "scenario": zh, "levels": len(levels), "n": n,
                "bp_rel": r["beta_P"]["rmse"] / abs(r["beta_P"]["truth"]),
                "tp_rel": r["tau_P"]["rmse"] / abs(r["tau_P"]["truth"]),
                "bp_rmse": r["beta_P"]["rmse"], "tp_rmse": r["tau_P"]["rmse"],
            })
            print(f"  [oracle] {zh} n={n:2d}  beta_P relRMSE={rows[-1]['bp_rel']:.3f}"
                  f"  tau_P relRMSE={rows[-1]['tp_rel']:.3f}")
    return rows


def fig_oracle(plt, rows: list[dict], out: Path, lang: str) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))
    for ax, key, ref, title in (
        (axes[0], "bp_rel", 0.30, "P 效应 beta_P 的可辨识性" if lang == "zh" else "identifiability of beta_P"),
        (axes[1], "tp_rel", 0.50, "饱和常数 tau_P 的可辨识性" if lang == "zh" else "identifiability of tau_P"),
    ):
        for zh, en, _lv in SCENARIOS:
            sub = [r for r in rows if r["scenario"] == zh]
            ax.plot([r["n"] for r in sub], [r[key] for r in sub],
                    marker="o", lw=1.8, label=zh.split("：")[0] if lang == "zh" else en.split(":")[0])
        ax.axhline(ref, color="tab:red", ls="--", lw=1.0,
                   label=("判据 %.2f" % ref) if lang == "zh" else ("criterion %.2f" % ref))
        ax.set_xlabel(L("n", lang))
        ax.set_ylabel(L("rel_rmse", lang))
        ax.set_title(title)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("P 水平设计的纯识别力（oracle：用被试层真值做组间回归，不含 DDM 拟合噪声）"
                 if lang == "zh"
                 else "oracle identifiability of the P-level design (no DDM fitting noise)",
                 fontsize=11.5)
    fig.tight_layout()
    p = out / "fig_sim_p_design.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# --------------------------------------------------------------------------- #
# 3. 试次级生成数据
# --------------------------------------------------------------------------- #
def pick_truth(choice: str):
    """试次图用哪套真值。

    * ``design``（默认）：``design_grid.TRUTH_LIN`` —— 与 CRLB 图同一设计前提的线性近似
      （``mapping.match_lin_to_exp`` 的残差 0.045），口径可与 Stage 4 对齐。
    * ``qc``：``_make_ddm_pilot.QC_TRUTH`` —— 合成数据集实际用的那套（更接近 Pilot 行为量级，
      但 ``beta_T = 0.45`` 使 T 的漂移跨度只有 0.098，比设计前提弱 3-4 倍）。
    """
    import design_grid as DGRID
    import _make_ddm_pilot as GEN
    if choice == "qc":
        return GEN.QC_TRUTH, "qc（_make_ddm_pilot.QC_TRUTH）"
    return DGRID.TRUTH_LIN, "design（design_grid.TRUTH_LIN）"


def trial_data(seed: int = 2026, n_subjects: int = 3, truth_choice: str = "design") -> dict:
    """同一真值下模拟若干名被试并合并（提高分单元的试次数，压住抽样噪声）。"""
    import twophase as TP
    import _make_ddm_pilot as GEN

    truth, truth_name = pick_truth(truth_choice)
    design, _meta, _mk = GEN.rows_for_subject(1, 12, 1, 0)
    rt_all, om_all, side_all = [], [], []
    for s in range(n_subjects):
        sim = TP.simulate_euler_subject(design, truth, 0.8,
                                        np.random.default_rng(seed + s), dt=5e-5)
        rt_all.append(np.asarray(sim["rt"], float))
        om_all.append(np.asarray(sim["omission"], int))
        side_all.append(np.asarray(sim["side"], int))
    rt = np.concatenate(rt_all)
    om = np.concatenate(om_all)
    side = np.concatenate(side_all)
    T0 = np.asarray(design["T"], float)
    W0 = np.asarray(design["W"], float)
    T = np.tile(T0, n_subjects)
    W = np.tile(W0, n_subjects)
    match = np.tile(np.asarray(design["is_match"], int), n_subjects)
    resp = om == 0
    correct = np.where(match == 1, side == 1, side == 0)

    per = []
    for t in sorted(set(np.round(T, 6))):
        for w in sorted(set(np.round(W, 6))):
            sel = (np.round(T, 6) == t) & (np.round(W, 6) == w)
            r = sel & resp
            per.append({
                "T_ms": round(t * 1000, 1), "W_ms": round(w * 1000, 1),
                "n": int(sel.sum()), "acc": float(correct[r].mean()) if r.any() else float("nan"),
                "omission": float(om[sel].mean()),
                "rt_med_ms": float(np.median(rt[r]) * 1000) if r.any() else float("nan"),
                "n_in_stim": int(((rt < T) & r).sum()),
            })
    return {"rt": rt, "om": om, "T": T, "W": W, "side": side, "correct": correct,
            "per": per, "truth": truth.as_dict(), "truth_name": truth_name, "rho": 0.8,
            "n_subjects": n_subjects}


def fig_trials(plt, td: dict, out: Path, lang: str) -> Path:
    rt, om, T, W = td["rt"], td["om"], td["T"], td["W"]
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.5))
    Ts = sorted(set(np.round(T, 6)))
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
    qs = np.array([0.1, 0.3, 0.5, 0.7, 0.9])

    ax = axes[0]
    for c, t in zip(colors, Ts):
        sel = (np.round(T, 6) == t) & (om == 0)
        if sel.sum() < 5:
            continue
        ax.plot(qs, np.quantile(rt[sel], qs) * 1000, marker="o", color=c, lw=1.6,
                label=f"T={int(round(t * 1000))} ms")
    ax.set_xlabel(L("quant", lang))
    ax.set_ylabel(L("rt", lang))
    ax.set_title("RT 分位数（只看已响应试次）" if lang == "zh" else "RT quantiles (responded trials)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[1]
    bins = np.arange(0, 1400, 50)
    for c, t in zip(colors, Ts):
        sel = (np.round(T, 6) == t) & (om == 0)
        if sel.sum() < 5:
            continue
        ax.hist(rt[sel] * 1000, bins=bins, alpha=0.45, color=c, density=True,
                label=f"T={int(round(t * 1000))} ms")
    ax.set_xlabel(L("rt", lang))
    ax.set_ylabel(L("density", lang))
    ax.set_title(f"RT 分布（{td['n_subjects']} 名被试合并、同一真值）" if lang == "zh"
                 else f"RT distributions ({td['n_subjects']} subjects pooled, same truth)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[2]
    Ws = sorted(set(np.round(W, 6)))
    for c, w in zip(["tab:blue", "tab:green", "tab:red"], Ws):
        ts, acc, omr = [], [], []
        for t in Ts:
            row = next(x for x in td["per"]
                       if abs(x["T_ms"] - round(t * 1000, 1)) < 1e-6
                       and abs(x["W_ms"] - round(w * 1000, 1)) < 1e-6)
            ts.append(t * 1000)
            acc.append(row["acc"])
            omr.append(row["omission"])
        ax.plot(ts, acc, marker="o", color=c, lw=1.6,
                label=(f"W={int(round(w * 1000))} ms 正确率" if lang == "zh"
                       else f"W={int(round(w * 1000))} ms acc"))
        ax.plot(ts, omr, marker="s", ls="--", color=c, lw=1.2,
                label=(f"W={int(round(w * 1000))} ms 遗漏率" if lang == "zh"
                       else f"W={int(round(w * 1000))} ms timeout"))
    ax.set_xlabel(L("T", lang))
    ax.set_ylabel(L("p", lang))
    ax.set_title("正确率 / 遗漏率随 T" if lang == "zh" else "accuracy / timeout vs T")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=6.5, ncol=1)

    fig.suptitle(f"模型假设下生成的试次级数据（{td['n_subjects']} 名被试 × 576 试次、rho = 0.8；模拟，非人类被试）"
                 if lang == "zh"
                 else f"trial-level data generated by the model ({td['n_subjects']} subjects x 576 trials, rho = 0.8)",
                 fontsize=11.5)
    fig.tight_layout()
    p = out / "fig_sim_trials.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


# --------------------------------------------------------------------------- #
def write_index(out: Path, c: dict, orows: list[dict], td: dict, figs: list[Path]) -> Path:
    need10 = {n: n_for_target(c, n, 0.10) for n in c["names"]}
    need25 = {n: n_for_target(c, n, 0.25) for n in c["names"]}
    lines = [
        "# 模拟图（论文用，模拟数据）",
        "",
        "> 本目录的每张图都由 `1_Code/Experiment/make_sim_figures.py` 生成，**不含任何真实被试数据**。",
        "> 按 D104 纪律一：它们只能进论文的**方法章 / 识别性与功效章**，不得进结果章。",
        "",
        "## 图与读法",
        "",
        "| 文件 | 内容 | 怎么读 | 能进论文哪一章 |",
        "|---|---|---|---|",
        "| `fig_sim_crlb.png` | CRLB：组层参数精度 | 纵轴是 SE/真值（对数）；红线 10% 是「设计目标」，橙点线 25% 是「能估但只能粗解释」 | 方法章（样本量论证）|",
        "| `fig_sim_p_design.png` | P 水平设计的识别力（oracle） | 左图 `beta_P` 相对 RMSE，红虚线 0.30 是判据；右图 `tau_P`，0.50 是判据。曲线越早跌破红线，说明该 P 方案越省人 | 方法章（设计选择）|",
        "| `fig_sim_trials.png` | 试次级生成数据 | 左：RT 分位数（T 越短越快而准越低）；中：RT 密度；右：正确率（实线）与遗漏率（虚线）随 T | 方法章（模型能生成什么）|",
        "",
        "## 关键数字（本脚本实算）",
        "",
        f"* CRLB 用的是 **{c['n_trials']} 试次/人**（4 T × 3 W × 4 种 × 12 次）；该设计在真值下的行为："
        f"正确率 **{c['acc']:.3f}**、遗漏 **{c['omission']:.3f}**、RT 均值 **{c['rt_ms']:.0f} ms**。",
        "* 组层相对 SE 达到 10% 所需组人数：",
        "",
        "| 参数 | 10% 需要 N | 25% 需要 N |",
        "|---|---|---|",
    ]
    for n in c["names"]:
        lines.append(f"| `{n}` | {need10[n] if need10[n] else '—'} | {need25[n] if need25[n] else '—'} |")
    lines += ["", "* P 方案 oracle 识别力（`beta_P` 判据 0.30、`tau_P` 判据 0.50）：", "",
              "| P 方案 | n=6 | n=12 | n=20 | n=30 | n=40 | n=50 |",
              "|---|---|---|---|---|---|---|"]
    for zh, _en, _lv in SCENARIOS:
        cells = []
        for n in ORACLE_NS:
            r = next(x for x in orows if x["scenario"] == zh and x["n"] == n)
            cells.append(f"{r['bp_rel']:.2f} / {r['tp_rel']:.2f}")
        lines.append(f"| {zh} | " + " | ".join(cells) + " |")
    lines += [
        "",
        f"* 试次级模拟（{td['n_subjects']} 名被试 × 576 试次、rho = 0.8）的真值为 "
        f"**{td['truth_name']}**；分单元结果见 `sim_trials_conditions.csv`，真值参数见 "
        "`sim_trials_truth.json`。",
        "",
        "## 三处口径落差（读本目录三张图前必须知道）",
        "",
        "| 对象 | 用的真值 | 影响 |",
        "|---|---|---|",
        "| `fig_sim_crlb.png` | `design_fim.TRUTH`（exp 形式，`beta_P = 1.5`、`P_ref = 120`） | 组层 SE 与所需人数 |",
        "| `fig_sim_trials.png` | `design_grid.TRUTH_LIN`（同一设计前提的线性近似，换算残差 0.045） | 图的形态与量级 |",
        "| `2_Data/Real_Data/_SYNTHETIC_DEMO_v1/` | `_make_ddm_pilot.QC_TRUTH`（lin，`beta_T = 0.45`） | T 的漂移跨度只有 0.098，比设计前提弱 3–4 倍 ⇒ **恢复验证偏保守** |",
        "",
        "* 设计真值在 **P = 0** 组的漂移约 0.0005（`exp` 形式在 `P=0` 处几乎归零）⇒ 期望正确率 0.50，"
        "而 S6-5 的下限是 0.45；两者不相容（首场真实数据 0.440 正落在这一位置）。",
        "* 设计真值的遗漏率约 0.32（`design_fim.TRUTH`）/ 0.35（`TRUTH_LIN`）⇒ 高于 S6-1 的 20% 阈值，"
        "说明设计真值偏悲观，须与 S6-5/S6-1 一起复核。",
        "",
        "## 复现",
        "",
        "```",
        "python -X utf8 1_Code/Experiment/make_sim_figures.py",
        "```",
        "",
        "产物：" + "、".join(f"`{p.name}`" for p in figs) + "、`sim_crlb.csv`、`sim_oracle.csv`、"
        "`sim_trials_conditions.csv`、`sim_trials_truth.json`、本文件。",
    ]
    p = out / "figures_index.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="论文级模拟图（无需真实数据）")
    ap.add_argument("--out", default=None, help="输出目录，默认 5_Reference/03_论文写作/figures_sim")
    ap.add_argument("--lang", default="zh", choices=["zh", "en"])
    ap.add_argument("--crlb-nfim", type=int, default=12, help="CRLB 的独立模拟份数（默认 12）")
    ap.add_argument("--oracle-rep", type=int, default=400, help="oracle 每次的重复数（默认 400）")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--truth", default="design", choices=["design", "qc"],
                    help="试次图的真值：design=design_grid.TRUTH_LIN（与 CRLB 同口径，默认）；"
                         "qc=_make_ddm_pilot.QC_TRUTH（合成数据集实际用的那套）")
    a = ap.parse_args()

    out = Path(a.out) if a.out else (_CODE.parent / "5_Reference" / "03_论文写作" / "figures_sim")
    out.mkdir(parents=True, exist_ok=True)

    plt, lang = setup_matplotlib(a.lang)
    figs: list[Path] = []

    print("[1/3] CRLB …")
    c = crlb(a.crlb_nfim)
    for n in c["names"]:
        print(f"  {n:8s} 单人 SE={c['se'][n]:.4f}  10% 需 N={n_for_target(c, n, 0.10)}")
    figs.append(fig_crlb(plt, c, out, lang))
    with (out / "sim_crlb.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["param", "truth", "se_per_subject", "n_for_10pct", "n_for_25pct"])
        for n in c["names"]:
            w.writerow([n, c["truth"][n], c["se"][n], n_for_target(c, n, 0.10), n_for_target(c, n, 0.25)])

    print("[2/3] P 方案识别力（oracle）…")
    orows = oracle_table(a.oracle_rep)
    figs.append(fig_oracle(plt, orows, out, lang))
    with (out / "sim_oracle.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(orows[0].keys()))
        w.writeheader()
        w.writerows(orows)

    print("[3/3] 试次级生成数据 …")
    td = trial_data(a.seed)
    figs.append(fig_trials(plt, td, out, lang))
    with (out / "sim_trials_conditions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(td["per"][0].keys()))
        w.writeheader()
        w.writerows(td["per"])
    truth = dict(td["truth"])
    truth.update({"rho": td["rho"], "kind": "SYNTHETIC", "n_trials": int(len(td["rt"]))})
    (out / "sim_trials_truth.json").write_text(
        __import__("json").dumps(truth, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    idx = write_index(out, c, orows, td, figs)
    for p in figs:
        print(f"  ✅ {p}")
    print(f"  ✅ {idx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
