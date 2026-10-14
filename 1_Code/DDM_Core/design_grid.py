# -*- coding: utf-8 -*-
"""
design_grid.py —— Stage 4 交付物：设计 × 分配 网格比较
================================================================================
目的
----
回答 Stage 4 验收标准所需的「设计 × 指标」表：**在每人固定 576 试次的前提下**，
把试次分配到不同的 (T 水平数 × W 水平数 × 每格重复数) 上，哪个分配最省人、
且行为负担可接受。

⚠️ 方法论更正（第一版错了，记录以免重犯）
----------------------------------------
第一版用**条件曲率**（其余参数钉在真值）作为设计比较指标。实测结果是
**9 个设计的条件 SE 几乎完全相同**（`d_ref` 全是 0.0056、`a_ref` 全是 0.0038）——
因为条件 SE 只由**该参数自己的逐试次信息 × 总试次**决定，与怎么分配无关。
而设计之所以重要，恰恰在于**联合估计时的补偿**（`beta_T ↔ tau_T`、`delta_a ↔ tau_a`）。
把其余参数钉死，等于把设计要解决的问题删掉了。

**正确指标：联合（边缘）信息矩阵的逆** `SE = √diag((−H)^{-1})`，
其中 `H` 是**参数单位**下的数值 Hessian。前提是 `−H` 必须**正定**；
每次计算都检查特征值并报告最大参数相关系数。不通过就拒绝出 SE。

⚠️ 边界约束澄清
----------------
`build_design(P, T_list, W_list, n_rep)` 的试次数是
``len(T)×len(W)×n_rep×len(self_levels)×len(match_levels)`` = `cells × rep × 4`。
因此 ``rep = TRIALS_TARGET / (cells × 4)``。第一版漏了 ×4，实际每人 2304 试次
（预计时长 67 min，不现实）。

用法
----
    python design_grid.py                 # 默认 n=24/组
    python design_grid.py 32              # 指定每组人数
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from likelihood import _bounds_for, log_likelihood, trials_from_arrays  # noqa: E402
from mapping import (WITHIN_FREE, WITHIN_FREE_LIN, MappingParams,  # noqa: E402
                     drift_magnitude, boundary_a, match_lin_to_exp)
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402

TRIALS_TARGET = 576          # 每人**总**试次数（含 4 种刺激类型）
N_STIM_TYPES = 4             # build_design 默认 (self 0/1) × (match 0/1)
SEED = 11
P_SINGLE = 120.0
ITI = 1.0                    # 试次间隔估计（秒，用于时长估算）

#: exp 形状真值（与 design_fim.TRUTH 一致）
TRUTH_EXP = MappingParams(
    P_ref=P_SINGLE, T_ref=0.10, W_ref=1.20, shape_model="exp",
    d_ref=0.70, beta_P=0.35, tau_P=30.0,
    beta_T=0.55, tau_T=0.080,
    beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)

#: lin 形状真值：由 `mapping.match_lin_to_exp` **统一换算**，不再手写。
#: （2026-10-14 修正：旧手写值 beta_T=1.279 / delta_a=0.226 换算规则自相矛盾，
#:  T 斜率乘了 exp 幅度而 W 斜率没乘，边界效应被夸大 1.69 倍。见函数 docstring。）
TRUTH_LIN = None        # 见下方 ``TRUTH_LIN, _LIN_REPORT = ...``（依赖层次定义）

FRAME = 16.6656 / 1000.0     # 帧长（D8：60.004 Hz）
MASK = 0.200                 # 掩蔽时长（硬约束 W > T + MASK）

D4T = [0.0333, 0.0833, 0.14999, 0.24998]
D4W = [0.79998, 1.19990, 1.79990]
LOW6_T = [0.0100, 0.0200, 0.0333, 0.0600, 0.1000, 0.2000]
LOW4_T = [0.0100, 0.0333, 0.1000, 0.2000]
MID4_T = [0.0500, 0.1000, 0.1500, 0.24998]
W4 = [0.69996, 0.99990, 1.39986, 1.89984]
W2 = [0.89988, 1.69986]

DESIGNS: dict[str, tuple[list[float], list[float], str]] = {
    "D4（基线）":  (D4T, D4W, "原推荐：T 33/83/150/250，W 800/1200/1800"),
    "A-screen":    ([0.0500, 0.2000], [0.79998, 1.59984], "2×2 筛查设计，每格试次最多"),
    "low6":        (LOW6_T, D4W, "T 移进 10–200 ms，6 水平（§8.6 推荐方向）"),
    "low4":        (LOW4_T, D4W, "T 只有 4 水平但都低"),
    "mid4":        (MID4_T, D4W, "T 50/100/150/250，间距均匀"),
    "W2（少W）":   (D4T, W2, "W 只留 2 水平，换取每格试次翻倍"),
    "W4（多W）":   (D4T, W4, "W 加到 4 水平，挤掉每格试次"),
    "low4×W4":     (LOW4_T, W4, "T 低 + W 多"),
    "low6×W2":     (LOW6_T, W2, "T 多 + W 少"),
}

# --- lin 真值：在设计**实际用到的层次并集**上做行为匹配 ---
# 用并集（而非某一个设计的层次）是为了让网格里每个设计都被同一把尺子衡量。
_T_UNION = sorted({t for _ts, _ws, _ in DESIGNS.values() for t in _ts})
_W_UNION = sorted({w for _ts, _ws, _ in DESIGNS.values() for w in _ws})
TRUTH_LIN, LIN_REPORT = match_lin_to_exp(TRUTH_EXP, _T_UNION, _W_UNION)

assert TRUTH_LIN is not None  # 供静态检查：上面已赋值


def print_lin_conversion() -> None:
    """打印 exp→lin 的行为匹配对照（可复核换算是否合理）。"""
    r = LIN_REPORT
    print("=" * 100)
    print("exp → lin 真值换算（mapping.match_lin_to_exp：设计层行为最小二乘匹配）")
    print("=" * 100)
    print(f"  T 层次并集（{len(_T_UNION)} 个）："
          f"{[round(x*1000, 1) for x in _T_UNION]} ms")
    print(f"  W 层次并集（{len(_W_UNION)} 个）："
          f"{[round(x*1000, 1) for x in _W_UNION]} ms")
    print(f"  lin 真值：d_ref={TRUTH_LIN.d_ref:.4f} beta_T={TRUTH_LIN.beta_T:.4f} "
          f"beta_S={TRUTH_LIN.beta_S:.4f} beta_ST={TRUTH_LIN.beta_ST:.4f} "
          f"a_ref={TRUTH_LIN.a_ref:.4f} delta_a={TRUTH_LIN.delta_a:.4f} "
          f"t0={TRUTH_LIN.t0:.4f}")
    print(f"  漂移跨度：exp {r['d_span_exp']:.4f} vs lin {r['d_span_lin']:.4f}"
          f" → 恢复 {100*r['d_span_lin']/r['d_span_exp']:.1f}%；"
          f"max|残差| {np.abs(r['d_resid']).max():.4f}")
    print(f"  边界跨度：exp {r['a_span_exp']:.4f} vs lin {r['a_span_lin']:.4f}"
          f" → 恢复 {100*r['a_span_lin']/r['a_span_exp']:.1f}%；"
          f"max|残差| {np.abs(r['a_resid']).max():.4f}")
    print("  ⚠️ 旧手写 TRUTH_LIN 在 W 通路上少乘了 exp 幅度 0.55（夸大 1.69 倍），")
    print("     本版已改由该函数统一换算 —— 旧网格结果需重新生成。")


# ----------------------------------------------------------------------
def joint_se(tr, names, p, rel_list=(1e-3, 3e-3)):
    """联合（边缘）SE：``√diag((−H)^{-1})``，H 为参数单位下的数值 Hessian。

    返回 ``(se_dict | None, diag)``。``−H`` 不正定则 ``se_dict=None``。
    对两个步长各算一次：都给结果且相对差 < 5% 才视为稳定。
    """
    lo, hi = _bounds_for(names)
    x0 = p.vector(names)
    k = len(names)
    base = log_likelihood(p, tr)
    if not np.isfinite(base):
        return None, {"reason": "似然非有限"}

    out = {}
    for rel in rel_list:
        h = np.maximum(rel * (hi - lo), 1e-6)
        H = np.zeros((k, k))
        for i in range(k):
            xp, xm = x0.copy(), x0.copy()
            xp[i] += h[i]
            xm[i] -= h[i]
            H[i, i] = (log_likelihood(p.with_vector(names, xp), tr)
                       - 2.0 * base
                       + log_likelihood(p.with_vector(names, xm), tr)) / h[i] ** 2
        for i in range(k):
            for j in range(i + 1, k):
                xpp, xpm, xmp, xmm = (x0.copy() for _ in range(4))
                xpp[i] += h[i]; xpp[j] += h[j]
                xpm[i] += h[i]; xpm[j] -= h[j]
                xmp[i] -= h[i]; xmp[j] += h[j]
                xmm[i] -= h[i]; xmm[j] -= h[j]
                v = (log_likelihood(p.with_vector(names, xpp), tr)
                     - log_likelihood(p.with_vector(names, xpm), tr)
                     - log_likelihood(p.with_vector(names, xmp), tr)
                     + log_likelihood(p.with_vector(names, xmm), tr)) / (4.0 * h[i] * h[j])
                H[i, j] = H[j, i] = v
        I = (H + H.T) / -2.0                 # I = −H
        ev = np.linalg.eigvalsh(I)
        if ev.min() <= 0:
            out[rel] = None
            continue
        C = np.linalg.inv(I)
        d = np.sqrt(np.diag(C))
        R = C / np.outer(d, d)
        out[rel] = (dict(zip(names, d.tolist())),
                    float(ev.min()), float(ev.max()),
                    float(np.max(np.abs(R - np.eye(k)))), R)
    keys = [k_ for k_, v in out.items() if v is not None]
    if len(keys) != len(rel_list):
        bad = [k_ for k_, v in out.items() if v is None]
        return None, {"reason": f"−H 非正定（步长 {bad}）"}
    a, b = (out[k_] for k_ in rel_list)
    agree = max(abs(a[0][n] - b[0][n]) / max(a[0][n], 1e-12) for n in names)
    if agree > 0.05:
        return None, {"reason": f"两步长结果不一致（最大相对差 {agree:.1%}）"}
    return a[0], {"ev_min": a[1], "ev_max": a[2], "cond": a[2] / a[1],
                  "max_abs_corr": a[3], "R": a[4], "step_agree": agree}


def evaluate(name, t_levels, w_levels, desc, n_subj):
    cells = len(t_levels) * len(w_levels)
    rep = max(1, int(round(TRIALS_TARGET / (cells * N_STIM_TYPES))))
    bad = [t for t in t_levels if any(w <= t + MASK for w in w_levels)]
    if bad:
        raise ValueError(f"{name}: T={bad} 违反 W > T + 200 ms 约束")

    design = build_design(P_SINGLE, t_levels, w_levels, rep)
    sim = simulate_subject(design, TRUTH_EXP, np.random.default_rng(SEED))
    arr = design_arrays(design)
    tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *arr)
    is_match, T_arr = arr[4], arr[1]

    keep = sim["omission"] == 0               # ⚠️ omission 是 int：绝不能写 ~om
    n = len(tr["rt"])
    row = dict(name=name, desc=desc, cells=cells, rep=rep, trials=n, n_subj=n_subj,
               om=float(sim["omission"].mean()),
               acc=float(np.mean(sim["side"][keep] == is_match[keep])),
               rt=float(sim["rt"][keep].mean() * 1000.0),
               frac_rt_lt_T=float(np.mean(sim["rt"][keep] < T_arr[keep])),
               minutes=n * (float(sim["rt"][keep].mean()) + ITI) / 60.0)

    for lab, names, truth, key in (("lin", WITHIN_FREE_LIN, TRUTH_LIN, "lin"),
                                   ("exp", WITHIN_FREE, TRUTH_EXP, "exp")):
        se, diag = joint_se(tr, names, truth)
        row[key] = se
        row[key + "_diag"] = diag
    return row


def main():
    n_subj = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    t_start = time.time()
    print("=" * 122)
    print(f"Stage 4 设计 × 分配 网格   （每人固定 {TRIALS_TARGET} 试次；每组 n={n_subj}；P={P_SINGLE}；seed={SEED}）")
    print("=" * 122)
    print("  组层 SE = 联合SE/√n，其中 联合SE = √diag((−H)⁻¹)（**不是**条件SE）。")
    print("  条件SE 与分配无关（第一版教训），联合SE 才能反映补偿结构。")
    print(f"  帧长 {FRAME*1000:.4f} ms；掩蔽 {MASK*1000:.0f} ms（硬约束 W > T + 200 ms）\n")

    print_lin_conversion()

    rows = []
    for name, (tl, wl, desc) in DESIGNS.items():
        r = evaluate(name, tl, wl, desc, n_subj)
        rows.append(r)
        print(f"  [{name}] {len(tl)}T×{len(wl)}W×{r['rep']}rep×4类 = {r['trials']} 试次"
              f"   遗漏 {r['om']:.3f}  正确率 {r['acc']:.3f}  平均RT {r['rt']:.0f} ms"
              f"   RT<T {r['frac_rt_lt_T']:.1%}   预计 {r['minutes']:.1f} min")
    print()

    for key, title in (("lin", "lin（7 自由，无时标）——**拟采用的参数化**"),
                       ("exp", "exp（9 自由，含时标）——对照")):
        names = WITHIN_FREE_LIN if key == "lin" else WITHIN_FREE
        truth = TRUTH_LIN if key == "lin" else TRUTH_EXP
        print("=" * 122)
        print(f"【{title}】联合 SE（每格 = 组层 SE = 联合SE/√{n_subj}）")
        print("=" * 122)
        hdr = f"  {'设计':13s}" + "".join(f"{nm:>10s}" for nm in names) + f"{'cond':>9s}{'maxCorr':>9s}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))
        for r in rows:
            if r[key] is None:
                print(f"  {r['name']:13s}{'—  拒绝出 SE：' + r[key+'_diag'].get('reason',''):>{len(hdr)-16}s}")
                continue
            line = f"  {r['name']:13s}"
            for nm in names:
                line += f"{r[key][nm]/np.sqrt(n_subj):10.4f}"
            line += f"{r[key+'_diag']['cond']:9.1e}{r[key+'_diag']['max_abs_corr']:9.3f}"
            print(line)
        print(f"  {'真值':13s}" + "".join(f"{float(getattr(truth, nm)):10.4f}" for nm in names))
        print()

    print("=" * 122)
    print("【推荐打分】只用确证性可估集合 {d_ref, beta_T, a_ref, delta_a, t0}（lin 参数化）")
    print("=" * 122)
    key_params = ["d_ref", "beta_T", "a_ref", "delta_a", "t0"]
    print(f"  {'设计':13s}" + "".join(f"{nm:>9s}" for nm in key_params)
          + f"{'相对SE和':>10s}{'时长min':>9s}{'RT<T':>8s}")
    print("  " + "-" * 84)
    scored = []
    for r in rows:
        if r["lin"] is None:
            print(f"  {r['name']:13s}  （拒绝出 SE：{r['lin_diag'].get('reason','')}）")
            continue
        rel, line = [], f"  {r['name']:13s}"
        for nm in key_params:
            se = r["lin"][nm] / np.sqrt(n_subj)
            tv = abs(float(getattr(TRUTH_LIN, nm)))
            rel.append(se / tv)
            line += f"{se/tv:9.1%}"
        score = float(np.sum(rel))
        scored.append((score, r))
        line += f"{score:10.3f}{r['minutes']:9.1f}{r['frac_rt_lt_T']:8.1%}"
        print(line)

    if scored:
        scored.sort(key=lambda x: x[0])
        best = scored[0][1]
        print(f"\n  → 相对精度最优：**{best['name']}**（{best['desc']}），相对 SE 和 {scored[0][0]:.3f}")
        print("     注：等权相加；某参数若科学上更重要，应加权重算。")
    print(f"\n  总耗时 {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
