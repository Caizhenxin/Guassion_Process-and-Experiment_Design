"""解析超参数 Hessian 的正定性 vs 人数 N —— D65 遗留问题的直接检验。

**问题**：D65 的合成干跑（M-T1、N=3、`make_fake_pilot.py` 造的数据）报
analytic 超参数 Hessian 最小特征值 **−0.2031**（`hyper_draws` 抬地板后照常抽样）。
正式数据将是 ~40 人/组。若非正定只是**小 N** 或**数据不像 DDM** 的产物，正式规模
不受影响；若随 N 不改善，则 D65 报出的超参数 SE 不可信，必须换做法。

**本探针做三组**（同一套 `hier.hyper_hessian_analytic`，只换数据与 N）：

* **A 组（DDM 数据、M-T1、真值 `rho = 0.8`）**：N ∈ {3, 6, 12, 24}，逐点报
  analytic Hessian 的最小/最大特征值、非正个数、归一化最小特征值，以及
  `hier_fit` 的退化计数（`n_fallback` / `n_nonfinite_g`）。
  ⇒ 若最小特征值随 N 变正，说明非正定是**小样本**现象。
* **B 组（非 DDM 数据、M-T1、N=3、两个种子）**：按 `make_fake_pilot.py` 的规则造
  「`rt = T + lognormal(−0.5, 0.45)`、超时按 `rt > W`、side 随机」的数据，
  检验 D65 的负特征值是不是**数据不像 DDM** 的产物。
* **A' 组（DDM、M-T3、N=3）**：同数据下 rho 固定为 1 的对照（K=7，维度少一）。

**判读**：
* A 组最小值随 N 上升并过 0 ⇒ 正式规模（N≈40）安全，D65 的负值是小样本。
* A 组 N=24 仍显著为负 ⇒ 不是小样本问题，正式规模也会踩到。
* B 组显著为负而 A 组同 N 为正 ⇒ D65 那条是**数据误导**，不是模型的缺陷。

跑法：``python -X utf8 1_Code/DDM_Core/_scratch/_probe_hess_scaling.py``
成本：144 试次/人；A 组 4 次 + A' 1 次 + B 2 次拟合 ⇒ 本机约 20–40 min。
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hier import (ddm_subject, hier_fit, hyper_draws,          # noqa: E402
                  hyper_hessian_analytic)
from mapping import MappingParams, WITHIN_FREE_LIN              # noqa: E402
from simulate import build_design                               # noqa: E402
from twophase import simulate_euler_subject                     # noqa: E402

T_L = [0.03333, 0.14999, 0.44998]
W_L = [0.79998, 1.79990]
N_REP = 6
P_FIXED = 32.0
N_X = 21
N_EM = 5

TRUTH = MappingParams(shape_model="lin", d_ref=1.20, beta_T=0.45,
                      beta_S=0.25, beta_ST=0.05, a_ref=1.10,
                      delta_a=0.30, t0=0.15)
RHO_TRUE = 0.8


def eig_report(fit: dict) -> dict:
    """在给定拟合上算 analytic Hessian 的谱，返回字典。"""
    hh = hyper_hessian_analytic(fit["modes"], fit["covs"],
                                fit["mu"], fit["log_sigma"])
    H = np.asarray(hh["H"], float)
    A = -0.5 * (H + H.T)
    eig = np.linalg.eigvalsh(A)
    mx = float(np.max(np.abs(eig))) if eig.size else 1.0
    mn = float(np.min(eig)) if eig.size else 0.0
    return {"min_eig": mn, "max_abs_eig": mx, "ratio": mn / mx,
            "n_nonpos": int(np.sum(eig <= 0.0)), "n_dim": int(eig.size)}


def _make_subjects(n_sub: int, *, ddm: bool, rho_free: bool, seed: int):
    """造 ``n_sub`` 名被试对象；``ddm=False`` 时用 make_fake_pilot 的规则。"""
    design = build_design(P_FIXED, T_L, W_L, N_REP)
    n_tr = int(np.asarray(design["T"]).size)
    master = np.random.default_rng(seed)
    subs = []
    for _ in range(n_sub):
        rng = np.random.default_rng(int(master.integers(1, 2 ** 31 - 1)))
        if ddm:
            sim = simulate_euler_subject(design, TRUTH, RHO_TRUE, rng, dt=5e-5)
            tr = dict(design)
            tr.update({k: np.asarray(v, float) for k, v in sim.items()
                       if k != "truth"})
        else:
            T = np.asarray(design["T"], float)
            W = np.asarray(design["W"], float)
            # make_fake_pilot：rt = T + lognormal(mu=-0.5, sigma=0.45)
            rt = T + rng.lognormal(mean=-0.5, sigma=0.45, size=n_tr)
            om = (rt > W).astype(int)
            side = rng.integers(0, 2, size=n_tr).astype(int)
            tr = dict(design)
            tr.update({"rt": np.where(om == 1, np.nan, rt),
                       "side": side, "omission": om})
        tr["omission"] = np.asarray(tr.get("omission"), int)
        # `t0` 上界 = 最小已响应 RT − 余量（与 `read_formal_data.t0_bounds` 同口径）。
        # 不做这一步的话 `_x0_of` 取区间中点（0.325 s）⇒ 多数试次 `rt − t0 < 0`
        # ⇒ `ll_x` 全为 −inf、拟合直接抛「∂²g 非有限」（本次第一版就踩到了）。
        resp = tr["omission"] == 0
        t0_hi = float(np.nanmin(np.asarray(tr["rt"], float)[resp])) - 0.01
        t0_hi = max(t0_hi, 0.06)
        subs.append(ddm_subject(tr, TRUTH, WITHIN_FREE_LIN,
                                rho_free=rho_free,
                                bounds_override={"t0": (0.05, t0_hi)},
                                n_x=N_X))
    return subs


def fit_group(n_sub: int, *, ddm: bool, rho_free: bool, seed: int = 7) -> dict:
    subs = _make_subjects(n_sub, ddm=ddm, rho_free=rho_free, seed=seed)
    t0 = time.perf_counter()
    fit = hier_fit(subs, n_em=N_EM)
    return {"fit": fit, "subs": subs, "n": n_sub, "ddm": ddm,
            "rho_free": rho_free, "seed": seed,
            "t_fit": time.perf_counter() - t0}


def line(tag: str, r: dict) -> str:
    fit = r["fit"]
    rep = eig_report(fit)
    model = "M-T1" if r["rho_free"] else "M-T3"
    return (f"{tag}: N={r['n']:>2}、{'DDM' if r['ddm'] else '非DDM'}、{model}"
            f" ⇒ min eig = {rep['min_eig']:+.4e}"
            f"（归一化 {rep['ratio']:+.3e}）、非正 {rep['n_nonpos']}/{rep['n_dim']}、"
            f"EM {fit['n_em_used']} 轮、{r['t_fit']:.0f}s、"
            f"n_fallback={fit['n_fallback']}、n_nonfinite_g={fit['n_nonfinite_g']}")


def main() -> int:
    design = build_design(P_FIXED, T_L, W_L, N_REP)
    print("=" * 78)
    print("解析超参数 Hessian 正定性 vs N（D65 遗留：N=3 报 min eig −0.2031）")
    print(f"设计：T {T_L} × W {W_L}、n_rep {N_REP} ⇒ "
          f"{np.asarray(design['T']).size} 试次/人；n_x {N_X}、n_em {N_EM}")
    print("=" * 78)

    print("\n[A 组] DDM 数据、M-T1、真值 rho = 0.8 —— 随 N 的变化")
    a_rows = []
    for n in (3, 6, 12, 24):
        r = fit_group(n, ddm=True, rho_free=True)
        a_rows.append(r)
        print("  " + line("A", r), flush=True)

    print("\n[B 组] 非 DDM 数据（make_fake_pilot 规则）、M-T1、N=3、两个种子")
    b_rows = []
    for seed in (7, 11):
        r = fit_group(3, ddm=False, rho_free=True, seed=seed)
        b_rows.append(r)
        print("  " + line(f"B(seed={seed})", r), flush=True)

    print("\n[A' 组] DDM 数据、M-T3（rho 固定 1）、N=3")
    ap = fit_group(3, ddm=True, rho_free=False)
    print("  " + line("A'", ap), flush=True)

    print("\n" + "=" * 78)
    signs = []
    for r in a_rows:
        rep = eig_report(r["fit"])
        signs.append("正" if rep["n_nonpos"] == 0 else f"非正{rep['n_nonpos']}")
    print("A 组符号序列：" + " → ".join(
        f"N={r['n']} {s}" for r, s in zip(a_rows, signs)))
    if all(s == "正" for s in signs):
        print("⇒ A 组全部正定：非正定未在 DDM 数据上复现（D65 的负值来自数据/小样本）")
    elif signs[-1] != "正":
        print("⇒ N=24 仍非正定：**不是小样本现象**，正式规模也会踩到（须换做法）")
    else:
        # 2026-10-17（D68 回填）：「N 大了就正定」这句话**不能**这么写。
        # 归一化最小特征值在四档都是 1e-3 量级（−4.202e-03 / −1.362e-03 / +1.394e-03 / +1.184e-03）
        # ⇒ 变的只是**符号**、不是量级；且 `_probe_hess_seedcheck.py` 实测 N=3 换 seed=99
        # 就变成 0/16。所以正确说法是「最平的那个方向一直在 1e-3 量级、随时可能翻负」。
        print("⇒ 符号虽转正，但**归一化最小特征值四档都在 1e-3 量级**"
              "（−4.202e-03 / −1.362e-03 / +1.394e-03 / +1.184e-03）")
        print("   ⇒ 变的只是符号、不是量级；`_probe_hess_seedcheck.py` 实测 N=3 换 seed=99 即为 0/16")
        print("   ⇒ **不得**写成「小样本现象、N≈40 安全」；只能说「最平方向随时可能翻负，"
              "正式数据上必须逐模型按 `n_flipped` 判」")

    nb = [eig_report(r["fit"])["n_nonpos"] for r in b_rows]
    print(f"B 组（非 DDM）非正个数：{nb}"
          + ("  ⇒ 与 D65 同向（数据不像 DDM ⇒ 众数贴边 ⇒ 曲率变负）"
             if all(x > 0 for x in nb) else "  ⇒ 未复现 D65 的负值"))

    # 接线一致性：n_flipped 必须等于此处的非正个数
    for r in [a_rows[0], a_rows[-1]]:
        dd = hyper_draws(r["subs"], r["fit"], n_draws=3, seed=1,
                         method="analytic")
        rep = eig_report(r["fit"])
        ok = int(dd["n_flipped"]) == rep["n_nonpos"]
        print(f"  接线核查 N={r['n']}：hyper_draws.n_flipped = {dd['n_flipped']}、"
              f"谱非正 = {rep['n_nonpos']} {'✅ 一致' if ok else '❌ 不一致'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
