# -*- coding: utf-8 -*-
"""
check_stage8.py —— 验 `stage8.py` 的拉普拉斯抽样器与 PPC（15 项判据）
======================================================================
判据分三组：

* **A 组：解析基准**。拉普拉斯抽样器的输入只是一个 `log_post_x` 闭包，
  所以可以拿**已知协方差的高斯后验**直接校验——它必须精确还原均值与协方差。
  这是"抽样器对不对"的唯一硬证据。
* **B 组：真实 DDM 路径**。用 `simulate` 造 576 试次、`fit_mle` 取 MLE，
  再比 **拉普拉斯后验 SD** 与**独立的 OPG 期望信息量 SE**（两条完全不同的
  渐近路线）。二者接近只能说明"两条路自洽"，**不等于**后验正确——报告里
  必须这么写。
* **C 组：PPC 的校准**。① 用生成数据的同一套参数当"后验"⇒ 预测区间必须
  基本覆盖观测（否则判据过严）；② 用**错得离谱**的参数当后验 ⇒ 必须有统计量
  掉出区间（否则判据没有检验力）。**两边都要过**才算 PPC 可用。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from likelihood import fit_mle, opg_information, per_trial_loglik      # noqa: E402
from mapping import WITHIN_FREE_LIN, MappingParams                  # noqa: E402
from simulate import build_design, simulate_subject                  # noqa: E402
from stage8 import (laplace_draws, ppc_table, subject_laplace,   # noqa: E402
                    _cell_stats_of, _stats_of)

_N = {"ok": 0, "bad": 0}


def check(name: str, cond: bool, detail: str = "") -> None:
    tag = "✅" if cond else "❌"
    _N["ok" if cond else "bad"] += 1
    print(f"  {tag} {name}" + (f"：{detail}" if detail else ""))


# ------------------------------------------------------------------
# A 组：解析基准
# ------------------------------------------------------------------
def case_a() -> None:
    print("\n[A] 解析基准（高斯后验，已知协方差）")
    # A1 一维：N(1.5, 0.5²) ⇒ 20 000 条抽样的 SD 的 SE ≈ 0.5/√40000 = 0.0025
    mu, sd = 1.5, 0.5
    f1 = lambda x: -0.5 * ((x[0] - mu) / sd) ** 2
    o1 = laplace_draws(f1, np.array([mu]), n_draws=20000, seed=1)
    x1 = o1["x"][:, 0]
    check("A1 一维：均值还原（真值 %.2f）" % mu, abs(x1.mean() - mu) < 0.015,
          "抽样均值 = %.4f（SE ≈ 0.0035）" % x1.mean())
    check("A2 一维：SD 还原（真值 %.2f）" % sd, abs(x1.std(ddof=1) - sd) < 0.010,
          "抽样 SD = %.4f（SE ≈ 0.0025）" % x1.std(ddof=1))
    check("A3 一维：众数处正定 ⇒ 无特征值被抬起", o1["n_flipped"] == 0,
          "n_flipped = %d、λ = %s" % (o1["n_flipped"],
                                      np.round(o1["eigval"], 4).tolist()))

    # A4 二维相关高斯：精度 Λ ⇒ 协方差 = Λ⁻¹
    Lam = np.array([[4.0, 1.5], [1.5, 2.0]])
    cov_true = np.linalg.inv(Lam)          # [[0.3478, -0.2609], [-0.2609, 0.6957]]
    mu2 = np.array([0.3, -0.7])
    f2 = lambda x: -0.5 * float((x - mu2) @ Lam @ (x - mu2))
    o2 = laplace_draws(f2, mu2, n_draws=20000, seed=2)
    cov_emp = np.cov(o2["x"].T)
    err = float(np.max(np.abs(cov_emp - cov_true)))
    check("A4 二维：协方差矩阵还原（最大元素误差 < 0.03）", err < 0.03,
          "最大误差 = %.4f；实测 = %s" % (err, np.round(cov_emp, 4).tolist()))
    check("A5 二维：非对角为负且量级正确",
          cov_emp[0, 1] < 0 and abs(cov_emp[0, 1] - cov_true[0, 1]) < 0.03,
          "实测 cov[0,1] = %.4f（真值 %.4f）" % (cov_emp[0, 1], cov_true[0, 1]))
    check("A6 二维：均值还原", float(np.max(np.abs(o2["x"].mean(axis=0) - mu2))) < 0.02,
          "抽样均值 = %s" % np.round(o2["x"].mean(axis=0), 4).tolist())

    # A7 鞍点：log_post = x0² − x1²/2 ⇒ ∂²/∂x0² = +2 ⇒ 抬到负号后 A = diag(−2, 1)
    # ⇒ 有一个负特征值 ⇒ 必须报告 n_flipped = 1（**不是**"这是极大点"）
    f3 = lambda x: x[0] ** 2 - 0.5 * (x[1] ** 2)
    o3 = laplace_draws(f3, np.array([0.0, 0.0]), n_draws=500, seed=3)
    check("A7 鞍点：负特征值被检出并抬起", o3["n_flipped"] == 1,
          "n_flipped = %d、原始 λ = %s" % (o3["n_flipped"],
                                           np.round(o3["eigval"], 4).tolist()))
    check("A8 鞍点：修复后的协方差仍正定（可抽样）",
          bool(np.all(np.linalg.eigvalsh(o3["cov_x"]) > 0)),
          "cov 特征值 = %s" % np.round(np.linalg.eigvalsh(o3["cov_x"]), 6).tolist())


# ------------------------------------------------------------------
# B 组：真实 DDM 路径（拉普拉斯 SD vs OPG SE）
# ------------------------------------------------------------------
def _ddm_setup(names, n_rep=12, seed=11):
    design = build_design(30.0, [0.03333, 0.08333, 0.14999, 0.24998],
                          [0.79998, 1.19990, 1.79990], n_rep)
    truth = MappingParams(shape_model="lin")
    sim = simulate_subject(design, truth, np.random.default_rng(seed))
    tr = dict(design)
    tr.update({k: np.asarray(v) for k, v in sim.items()})
    return design, truth, tr


def case_b() -> None:
    print("\n[B] 真实 DDM 路径：拉普拉斯后验 SD vs OPG 期望信息量 SE")
    names = ["d_ref", "beta_T", "beta_S", "beta_ST"]
    design, truth, tr = _ddm_setup(names)
    fit = fit_mle(tr, names, truth, n_restart=3, seed=5)
    print(f"    MLE: ll = {fit['loglik']:.3f}、n_starts_ok = {fit['n_starts_ok']}")
    p_hat = fit["params"]
    # ⚠️ B1 **不**检查"MLE ≈ 真值"：本项目已实测（README §9 第 23 项）`beta_ST` 与
    # `beta_T` 互相补偿，逐被试恢复本来就差。优化器是否可信要用**它自己的性质**验：
    # ① MLE 的对数似然不能低于真值（MLE 的定义）；② 换个起点要落回同一个 ll。
    ll_truth = float(np.sum(per_trial_loglik(truth, tr)))
    check("B1a MLE 的似然不劣于真值（优化器真的在最大化）",
          fit["loglik"] >= ll_truth - 1e-6,
          f"ll(MLE) = {fit['loglik']:.4f} vs ll(真值) = {ll_truth:.4f}"
          f"（提升 {fit['loglik'] - ll_truth:+.4f}）")
    fit2 = fit_mle(tr, names, truth.replace(d_ref=0.6, beta_T=4.0, beta_S=0.05,
                                           beta_ST=-2.0), n_restart=3, seed=99)
    check("B1b 换起点落回同一最优（ll 相差 < 0.5）",
          abs(fit2["loglik"] - fit["loglik"]) < 0.5,
          f"ll = {fit2['loglik']:.4f} vs {fit['loglik']:.4f}")
    dev = p_hat.vector(names) / truth.vector(names) - 1.0
    print("    （信息性）逐参数相对偏差 MLE/真值 − 1 = %s"
          % np.round(dev, 3).tolist())

    lap = subject_laplace(tr, names, p_hat, n_draws=2000, seed=7)
    check("B2 在 MLE 处 Hessian 正定（n_flipped = 0）", lap["n_flipped"] == 0,
          "n_flipped = %d、λ = %s" % (lap["n_flipped"],
                                      np.round(lap["eigval"], 2).tolist()))
    sd_lap = lap["theta"].std(axis=0, ddof=1)
    I, _G = opg_information(tr, names, p_hat)
    sd_opg = np.sqrt(np.diag(np.linalg.inv(I)))
    ratio = sd_lap / sd_opg
    check("B3 两条渐近路线的 SE 同量级（比值 ∈ [0.6, 1.7]）",
          bool(np.all((ratio > 0.6) & (ratio < 1.7))),
          "拉普拉斯/OPG = %s" % np.round(ratio, 3).tolist())
    # 后验均值应当靠近 MLE（拉普拉斯是对称近似 ⇒ 均值 ≈ 众数）
    dev = np.abs(lap["theta"].mean(axis=0) - p_hat.vector(names)) / sd_lap
    check("B4 后验均值 ≈ MLE（最大偏差 < 0.3 个后验 SD）", float(np.max(dev)) < 0.3,
          "最大 = %.3f 个 SD" % float(np.max(dev)))
    check("B5 逐条抽样的对数似然都有限", bool(np.all(np.isfinite(lap["log_lik"]))),
          "有限 %d / %d" % (int(np.sum(np.isfinite(lap["log_lik"]))), lap["n_draws"]))
    print("    SE 对照（自然参数单位）：")
    for i, nm in enumerate(names):
        print(f"      {nm:<8} 拉普拉斯 {sd_lap[i]:.4f}   OPG {sd_opg[i]:.4f}"
              f"   比值 {ratio[i]:.3f}")
    # B6：后验相关矩阵应当直接显示 `beta_T` ↔ `beta_ST` 的补偿
    C = np.corrcoef(lap["theta"].T)
    i_t, i_st = names.index("beta_T"), names.index("beta_ST")
    print("    后验相关矩阵：")
    for i, nm in enumerate(names):
        print(f"      {nm:<8} " + "  ".join(f"{C[i, j]:+.3f}" for j in range(len(names))))
    check("B6 后验里 `beta_T` ↔ `beta_ST` 强负相关（补偿方向可见，< −0.5）",
          C[i_t, i_st] < -0.5, "corr = %+.3f" % C[i_t, i_st])
    return names, design, truth, tr, lap


# ------------------------------------------------------------------
# C 组：PPC 校准（双向）
# ------------------------------------------------------------------
def case_c(names, design, truth, tr, lap) -> None:
    print("\n[C] PPC 校准：对的数据要通过，错的数据要被抓")
    # C1 用生成数据的真值当"后验" ⇒ 观测应当落在预测带内
    draws_ok = {"names": names, "p_map": MappingParams(shape_model="lin"),
                "theta": np.tile(truth.vector(names), (40, 1))}
    res_ok = ppc_table(tr, design, draws_ok, seed=21)
    n_ok = sum(1 for r in res_ok["rows"] if r["ok"])
    check("C1 参数正确时，观测基本落在 95% 预测带内（≥ 10/12）",
          n_ok >= 10, f"{n_ok}/{len(res_ok['rows'])} 项在带内")

    # C2 把 d_ref 砍半 + beta_T 翻倍 ⇒ 必须有统计量掉出带
    bad = truth.replace(d_ref=truth.d_ref * 0.5, beta_T=truth.beta_T * 2.0,
                        beta_S=truth.beta_S * 3.0)
    draws_bad = {"names": names, "p_map": MappingParams(shape_model="lin"),
                 "theta": np.tile(bad.vector(names), (40, 1))}
    res_bad = ppc_table(tr, design, draws_bad, seed=21)
    n_bad = sum(1 for r in res_bad["rows"] if r["ok"])
    check("C2 参数错得离谱时，≥ 3 项掉出预测带",
          (len(res_bad["rows"]) - n_bad) >= 3,
          f"{len(res_bad['rows']) - n_bad}/{len(res_bad['rows'])} 项在带外")


# ------------------------------------------------------------------
# D 组：分单元 PPC（Self/Other × Match/Nonmatch）
# ------------------------------------------------------------------
def case_d(names, design, truth, tr, _lap=None) -> None:
    print("\n[D] 分单元 PPC：单元切分正确、且能给出全局看不见的信息")

    # D1/D2 先用**手造数据**把单元切分本身测死（确定性判据，不靠模拟）
    n = 40
    syn = {"rt": np.full(n, 0.5), "side": np.zeros(n, dtype=int),
           "omission": np.zeros(n), "T": np.full(n, 0.25), "W": np.full(n, 1.2),
           "is_self": np.array([1] * 10 + [1] * 10 + [0] * 10 + [0] * 10),
           "is_match": np.array([1] * 10 + [0] * 10 + [1] * 10 + [0] * 10)}
    syn["omission"][:10] = 1.0            # 只有 Self-Match 这 10 个试次全未响应
    syn["side"] = syn["is_match"].copy()  # 全部答对
    cells = _cell_stats_of(syn)
    check("D1 单元标签 = 四个（Self/Other × Match/Nonmatch）",
          sorted(cells) == ["Other-Match", "Other-Nonmatch",
                            "Self-Match", "Self-Nonmatch"],
          f"{sorted(cells)}")
    check("D2 每个单元都拿到 4 个以上统计量",
          all(len(v) >= 4 for v in cells.values()),
          f"单元统计量个数 = {sorted({len(v) for v in cells.values()})}")
    check("D3 未响应率被正确切到单一单元（Self-Match = 1.0，其余 = 0.0）",
          abs(cells["Self-Match"]["omission_rate"] - 1.0) < 1e-12
          and all(abs(cells[c]["omission_rate"]) < 1e-12
                  for c in ("Self-Nonmatch", "Other-Match", "Other-Nonmatch")),
          f"Self-Match = {cells['Self-Match']['omission_rate']:.4g}、"
          f"其余 = {[round(cells[c]['omission_rate'], 6) for c in ('Self-Nonmatch', 'Other-Match', 'Other-Nonmatch')]}")
    check("D4 全局 `omission_rate` 只看到 0.25（单元信息被平均掉了）",
          abs(_stats_of(syn)["omission_rate"] - 0.25) < 1e-12,
          f"全局 = {_stats_of(syn)['omission_rate']:.4g}，而单元内是 1.0 与 0.0")

    # D5/D6 再看真实 DDM 路径上的双向校准
    draws_ok = {"names": names, "p_map": MappingParams(shape_model="lin"),
                "theta": np.tile(truth.vector(names), (40, 1))}
    res_ok = ppc_table(tr, design, draws_ok, seed=21)
    rows = res_ok.get("cell_rows") or []
    check("D5 分单元表覆盖 4 单元 × 5 统计量 = 20 行",
          len(rows) == 20, f"{len(rows)} 行")
    n_ok = sum(1 for r in rows if r["ok"])
    check("D6 参数正确时分单元观测基本落在带内（≥ 15/20）",
          n_ok >= 15, f"{n_ok}/{len(rows)} 项在带内")

    bad = truth.replace(d_ref=truth.d_ref * 0.5, beta_T=truth.beta_T * 2.0,
                        beta_S=truth.beta_S * 3.0)
    draws_bad = {"names": names, "p_map": MappingParams(shape_model="lin"),
                 "theta": np.tile(bad.vector(names), (40, 1))}
    rows_bad = (ppc_table(tr, design, draws_bad, seed=21).get("cell_rows") or [])
    n_out = sum(1 for r in rows_bad if r["ok"] is False)
    check("D7 参数错得离谱时，分单元表也有 ≥ 5 项掉出预测带",
          n_out >= 5, f"{n_out}/{len(rows_bad)} 项在带外")


def main() -> int:
    print("=" * 72)
    print("stage8.py 自测（拉普拉斯抽样 / 后验预测检验）")
    print("=" * 72)
    case_a()
    ctx = case_b()
    case_c(*ctx)
    case_d(*ctx)
    print("\n" + "=" * 72)
    total = _N["ok"] + _N["bad"]
    if _N["bad"]:
        print(f"❌ {_N['bad']} / {total} 项判据未通过")
        return 1
    print(f"✅ 全部 {total} 项判据通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
