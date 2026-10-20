#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""③ 设计空间优化：把「被试内 T/W/重复」与「被试间 P 水平」放进同一个搜索。

要回答的唯一问题：**在给定试次预算内，哪种设计组合需要的组人数最少？**

三个判据同时成立才算达标：
  * 被试内 `beta_T`：CRLB 相对 SE ≤ 10%（在 P = P_ref 水平上评估）；
  * 被试间 `beta_P`：相对 RMSE ≤ 0.30（D105 的 oracle 判据）；
  * 被试间 `tau_P`：相对 RMSE ≤ 0.50。
「总需人数」取三者所需组人数的最大值，再按人数排序。

方法上的两个要点（也是本脚本与 `oracle_power.py` 的区别）：
1. 每个 P 水平各算一次被试层 CRLB ⇒ 各水平的 `d` 精度不同，低 P 水平漂移≈0、
   几乎不提供漂移信息（P=0 组的 CRLB 里漂移簇信息近奇异），这是「P=0 不能当
   基线以外的水平用」的量化版本。
2. 组层回归用带权的三参数 Jacobian（`d_ref`、`beta_P`、`tau_P`），权重同时含
   被试间随机效应 SD 与该水平的试次噪声 ⇒ 「加人」和「加密 P 水平」的收益不会
   被算成同一件事。

用法
----
    python -X utf8 1_Code/Experiment/design_search.py --quick
    python -X utf8 1_Code/Experiment/design_search.py --budget 576

产物
----
    5_Reference/03_论文写作/figures_sim/design_search_<truth>.csv
    5_Reference/03_论文写作/figures_sim/design_search_<truth>.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_CORE = _ROOT / "1_Code" / "DDM_Core"
sys.path.insert(0, str(_CORE))

from design_fim import NAMES, P_SINGLE, TRUTH, check_validity  # noqa: E402
from likelihood import opg_information, trials_from_arrays  # noqa: E402
from mapping import f_P  # noqa: E402
from recover_group import P_COMMON_REF, P_LEVELS  # noqa: E402
from simulate import SUBJECT_SD, build_design, design_arrays, simulate_subject  # noqa: E402

OUT = _ROOT / "5_Reference" / "03_论文写作" / "figures_sim"

#: 两套组层真值（见 `_scratch/_diag_tau_p.py` 的诊断）：
#: * ``design``  —— `design_fim.TRUTH`：P_ref=120、beta_P=1.5 ⇒ 由于
#:   `drift_magnitude` 对幅度取 `max(0, ·)`，P≤32 的漂移被截到 0，
#:   只有 P=120 真正携带信息（P 设计实际只剩 2 个有效水平）；
#: * ``oracle``  —— `oracle_power.TRUTH`：P_ref=30、beta_P=0.35，四个水平都携带信息。
TRUTHS = {
    "design": {"d_ref": 0.70, "beta_P": 1.50, "beta_S": 0.16,
               "beta_SP": 0.06, "tau_P": 30.0, "P_ref": 120.0},
    "oracle": {"d_ref": 0.70, "beta_P": 0.35, "beta_S": 0.16,
               "beta_SP": 0.06, "tau_P": 30.0, "P_ref": 30.0},
}
GROUP_TRUTH = dict(TRUTHS["design"])
GROUP_P_REF = GROUP_TRUTH["P_ref"]


WITHIN_TRUTH = TRUTH


def use_truth(name: str) -> None:
    """切换组层真值，**同时**把被试内仿真的 beta_P / P_ref 换成同一套。

    这是必须的：`design_fim.TRUTH` 的 beta_P=1.5、P_ref=120，而
    `drift_magnitude` 对幅度取 max(0,·)，于是 P≤32 的漂移被截到 0，被试层
    CRLB 在漂移簇上直接奇异（SE 恰为 0）⇒ 低 P 水平会被当成「无信息水平」
    剔除。若只改组层真值而不改这里，两种口径会跑出完全相同的结果。
    """
    global GROUP_TRUTH, GROUP_P_REF, WITHIN_TRUTH
    GROUP_TRUTH = dict(TRUTHS[name])
    GROUP_P_REF = GROUP_TRUTH["P_ref"]
    WITHIN_TRUTH = TRUTH.replace(beta_P=GROUP_TRUTH["beta_P"],
                                 P_ref=GROUP_P_REF)
JUDGE = {"beta_T": 0.10, "beta_P": 0.30, "tau_P": 0.50}
SE_D_UNUSABLE = 1.0          # 被试层漂移 SE 超过它，视为该水平不可用

# 每个设定只算一次的缓存：(within 名, P) -> d_ref 的 SE
_SE_CACHE: dict = {}


# ---------------------------------------------------------------- 被试内 CRLB


def subject_se(P: float, T_levels, W_levels, n_rep: int, n_fim: int,
               seed: int = 0) -> dict:
    """给定 P 与 T/W 设计，返回被试层各参数 CRLB 的 SE（自然单位）。"""
    design = build_design(P, T_levels, W_levels, n_rep)
    Is = []
    for r in range(n_fim):
        rng = np.random.default_rng(seed + 1000 * r + int(P))
        sim = simulate_subject(design, WITHIN_TRUTH, rng)
        tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"],
                                *design_arrays(design))
        I, _ = opg_information(tr, NAMES, WITHIN_TRUTH)
        Is.append(I)
    cov = np.linalg.pinv(np.mean(Is, axis=0))
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    return {n: float(v) for n, v in zip(NAMES, se)}


def rel_se(se: dict) -> dict:
    t = WITHIN_TRUTH.as_dict()
    return {k: (v / abs(t[k]) if t[k] else float("inf")) for k, v in se.items()}


def se_full(name: str, P: float, T, W, r: int, n_fim: int) -> dict:
    key = (name, round(float(P), 3))
    if key not in _SE_CACHE:
        _SE_CACHE[key] = subject_se(P, T, W, r, n_fim=max(1, n_fim))
    return _SE_CACHE[key]


# ------------------------------------------- 被试间 WLS（三参数 Jacobian）


def between_cov(se_d_by_level, n: int, P_levels) -> dict:
    """组层回归 (d_ref, beta_P, tau_P) 的解析协方差（含试次噪声）。"""
    P_arr = np.array(P_levels, float)
    tau = GROUP_TRUTH["tau_P"]
    base = f_P(P_arr, tau) - f_P(GROUP_P_REF, tau)
    h = max(1e-3, 1e-4 * tau)
    dreg = (f_P(P_arr, tau + h) - f_P(P_arr, tau - h)) / (2 * h)
    J = np.column_stack([np.ones_like(base), base, GROUP_TRUTH["beta_P"] * dreg])
    se_d = np.asarray(se_d_by_level, float)
    var_i = (SUBJECT_SD["d_ref"] ** 2 + se_d ** 2) / n
    w = 1.0 / var_i
    cov = np.linalg.pinv(J.T @ (w[:, None] * J))
    return {"cov": cov, "sd": np.sqrt(np.maximum(np.diag(cov), 0.0))}


def rel_group(n: int, se_d_by_level, P_levels) -> dict:
    sd = between_cov(se_d_by_level, n, P_levels)["sd"]
    return {"d_ref": float(sd[0] / abs(GROUP_TRUTH["d_ref"])),
            "beta_P": float(sd[1] / abs(GROUP_TRUTH["beta_P"])),
            "tau_P": float(sd[2] / abs(GROUP_TRUTH["tau_P"]))}


def needed_n(se_d_by_level, P_levels, judge: float, which: str,
             n_max: int = 400) -> dict:
    """二分找满足判据所需的最少组人数（各水平等 n）。"""
    hi_rel = rel_group(n_max, se_d_by_level, P_levels)[which]
    if not np.isfinite(hi_rel) or hi_rel > judge:
        return {"n": None, "rel_at_max": float(hi_rel)}
    lo, hi = 2, n_max
    while lo < hi:
        mid = (lo + hi) // 2
        if rel_group(mid, se_d_by_level, P_levels)[which] <= judge:
            hi = mid
        else:
            lo = mid + 1
    return {"n": int(lo), "rel_at_n": float(rel_group(lo, se_d_by_level, P_levels)[which])}


# ------------------------------------------------------------------ 搜索空间


def within_designs() -> dict:
    T4 = [0.0333, 0.0833, 0.14999, 0.24998]
    W3 = [0.79998, 1.19990, 1.79990]
    return {
        "4T×3W r12（现行）": (T4, W3, 12),
        "3T×3W r16（省一个 T）": ([0.0333, 0.0833, 0.14999], W3, 16),
        "5T×3W r9（加 T=200）": ([0.0333, 0.0833, 0.14999, 0.19999, 0.24998], W3, 9),
        "4T×3W r12 W-wide": (T4, [0.50000, 1.19990, 2.00000], 12),
        "4T×2W r18（省 W）": (T4, [0.79998, 1.79990], 18),
        "4T×4W r9（加 W=1400）": (T4, [0.79998, 1.09995, 1.39992, 1.79990], 9),
        "5T×2W r14（窄 W 换 T）": ([0.0333, 0.0833, 0.14999, 0.19999, 0.24998],
                                   [0.79998, 1.79990], 14),
    }


def p_schemes() -> dict:
    return {
        "现行 0/8/32/120": [+0, 8, 32, 120],
        "3 水平 0/32/120": [0, 32, 120],
        "5 水平 0/8/24/64/120": [0, 8, 24, 64, 120],
        "6 水平 0/4/8/16/32/64/120": [0, 4, 8, 16, 32, 64, 120],
        "加宽 0/8/32/120/240": [0, 8, 32, 120, 240],
        "两级 0/120": [0, 120],
    }


def assemble(n_fim: int) -> list[dict]:
    rows = []
    for dname, (T, W, r) in within_designs().items():
        bad = check_validity(T, W)
        if bad:
            print(f"  ⚠️ 跳过 {dname}：违反 W > T+200 ms，{bad}")
            continue
        trials = len(T) * len(W) * r
        # 被试内：在 P_ref 上评估 beta_T 的精度（P=0 处漂移≈0，漂移簇不可识别）
        se_ref = se_full(dname, P_SINGLE, T, W, r, n_fim)
        rel_bT = rel_se(se_ref)["beta_T"]
        n_bT = int(np.ceil((rel_bT / JUDGE["beta_T"]) ** 2)) if np.isfinite(rel_bT) else None

        for pname, levels in p_schemes().items():
            se_ds = []
            for p in levels:
                se_ds.append(se_full(dname, p, T, W, r, max(1, n_fim // 2))["d_ref"])
            se_ds = np.array(se_ds)
            n_bp = n_tp = None
            # P=0 组的漂移≈0 ⇒ 漂移簇信息矩阵近奇异 ⇒ pinv 给出的 SE 恰好为 0，
            # 这是「无信息」而不是「完美精度」；SE 过大（>1.0）同样是不可用水平。
            keep = np.isfinite(se_ds) & (se_ds > 1e-9) & (se_ds < SE_D_UNUSABLE)
            if keep.sum() < 3:
                unusable = True
            else:
                if True:
                    nb = needed_n(se_ds[keep], np.array(levels)[keep],
                                  JUDGE["beta_P"], "beta_P")
                    nt = needed_n(se_ds[keep], np.array(levels)[keep],
                                  JUDGE["tau_P"], "tau_P")
                    n_bp, n_tp = nb["n"], nt["n"]
                    unusable = False
            if unusable or n_bT is None:
                n_total, why = None, "被试层漂移不可识别"
            elif None in (n_bp, n_tp):
                n_total = None
                why = "400 人/组内未达标"
            else:
                n_total = max(n_bT, n_bp, n_tp)
                why = ""
            rows.append({
                "within": dname, "p_scheme": pname, "n_P_levels": int(keep.sum()) if not unusable else 0,
                "trials_per_subject": trials,
                "rel_beta_T": round(rel_bT, 4), "n_beta_T": n_bT,
                "n_beta_P": n_bp, "n_tau_P": n_tp, "n_total": n_total,
                "note": why,
            })
            print(f"  {dname:24s} × {pname:22s} 试次={trials:3d} "
                  f"βT {str(n_bT):>4s} | βP {str(n_bp):>4s} | τP {str(n_tp):>4s} "
                  f"⇒ 总 {str(n_total):>4s}{('  (' + why + ')') if why else ''}",
                  flush=True)
    return rows


def write_reports(rows: list[dict], budget: int) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    tag = GROUP_TRUTH["name_label"]
    csv = OUT / f"design_search_{tag}.csv"
    heads = list(rows[0].keys())
    with csv.open("w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(heads) + "\n")
        for r in rows:
            fh.write(",".join("" if r[h] is None else str(r[h]) for h in heads) + "\n")

    ok = sorted([r for r in rows if r["n_total"]],
                key=lambda r: (r["n_total"], r["trials_per_subject"]))
    md = OUT / f"design_search_{tag}.md"
    L = [
        "# 设计空间搜索结果（③ 第一轮）",
        "",
        f"> 组层真值 = **{GROUP_TRUTH['name_label']}**（P_ref={GROUP_P_REF}、beta_P={GROUP_TRUTH['beta_P']}）；预算 {budget} 试次/人；判据：`beta_T` 相对 SE ≤ {JUDGE['beta_T']:.2f}、"
        f"`beta_P` 相对 RMSE ≤ {JUDGE['beta_P']:.2f}、`tau_P` ≤ {JUDGE['tau_P']:.2f}。",
        "> 被试内用 OPG CRLB（`design_fim.TRUTH`，在 P=P_ref 上评估）；被试间用三参数 "
        "Jacobian 加权回归（含被试间 SD 与该水平试次噪声）。",
        "> 总需人数 = 三者最大值。**这张表是「设计可能性」的边界，不是执行承诺**。",
        "",
        "## 排名（前 15）",
        "",
        "| 排名 | 被试内设计 | P 方案 | P 水平数 | 试次/人 | βT 需 N | βP 需 N | τP 需 N | **总需 N** |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(ok[:15], 1):
        L.append(f"| {i} | {r['within']} | {r['p_scheme']} | {r['n_P_levels']} | "
                 f"{r['trials_per_subject']} | {r['n_beta_T']} | {r['n_beta_P']} | "
                 f"{r['n_tau_P']} | **{r['n_total']}** |")
    bad = [r for r in rows if not r["n_total"]]
    if bad:
        L += ["", "## 未达标组合", "", "| 被试内设计 | P 方案 | 原因 |", "|---|---|---|"]
        for r in bad:
            L.append(f"| {r['within']} | {r['p_scheme']} | {r['note']} |")
    L += ["", "## 读法与边界", "",
          "* 「总需 N」是三条同时成立所需的最大值；单看某一条都会高估设计的可行性。",
          "* 被试内 CRLB 假设 T/W 水平等重复、无疲劳与顺序效应；实际执行还要加遗漏率与时长约束。",
          "* 被试间是解析近似（不含 `fit_between` 的非线性拟合误差），方向与 "
          "`oracle_power.py` 的蒙特卡洛一致（40 人/组稳、20 人/组下限）。",
          "* **P=0 组的漂移在 `exp` 映射下≈0**，其漂移簇 CRLB 近奇异 ⇒ 它只能当基线，"
          "不能作为「低 P 水平」提供斜率信息；表里已把 SE>1.0 的水平剔除。"]
    md.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    return md


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="n_fim 减半的粗略版")
    ap.add_argument("--n-fim", type=int, default=4)
    ap.add_argument("--budget", type=int, default=576, help="试次/人 预算（记录用）")
    ap.add_argument("--group-truth", choices=list(TRUTHS), default="design")
    args = ap.parse_args()
    n_fim = max(1, (2 if args.quick else args.n_fim))
    use_truth(args.group_truth)
    GROUP_TRUTH["name_label"] = args.group_truth
    print("=" * 104)
    print("③ 设计空间优化：被试内 (T/W/重复) × 被试间 (P 方案)")
    print("=" * 104)
    print(f"  判据：{JUDGE}；CRLB 每设定 {n_fim} 份模拟平均；"
          f"被试间 SD_d={SUBJECT_SD['d_ref']}")
    print(f"  真值：P_ref={P_SINGLE}、d_ref={TRUTH.d_ref}、beta_T={TRUTH.beta_T}\n")
    rows = assemble(n_fim)
    md = write_reports(rows, args.budget)
    ok = sorted([r for r in rows if r["n_total"]],
                key=lambda r: (r["n_total"], r["trials_per_subject"]))
    print("\n" + "=" * 104)
    print(f"  达标 {len(ok)}/{len(rows)}；最省 = {ok[0]['n_total'] if ok else '—'} 人/组")
    for r in ok[:6]:
        print(f"    {r['n_total']:3d} 人/组 ← {r['within']} × {r['p_scheme']}"
              f"（试次 {r['trials_per_subject']}）")
    print(f"\n  报告：{md.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
