# -*- coding: utf-8 -*-
"""
check_pure.py —— 单参数"纯切片"：分辨是**设计**问题还是**模型参数化**问题
============================================================================
为什么必须做这一步
------------------
剖面（其余参数自由）显示 τ_T/β_T/β_ST 的 2 单位区间都**不含真值**。但那只能说明
"联合估不出来"，不能说明原因。两种可能、两种完全不同的对策：

  (A) **设计问题**：给定其余参数，数据本身对 τ_T 就几乎没有信息
      ⇒ 对策：改 T 水平的位置/数量（加在 τ_T 陡峭区）、加试次。
  (B) **模型参数化问题**：单独动 τ_T 时信息很强（切片陡），但 β_T 能**线性补偿**
      ⇒ 对策：先验固定 τ_T，或换参数化（报可识别组合），**改设计无用**。

本脚本直接测**纯切片**：只动一个参数、其余钉在真值，Δll 随该参数的变化。
再与剖面对照，得到"补偿代价"。

同时修正一个数值问题
--------------------
`design_ident.py` 用 h_rel=1e-4 求条件 SE，对 τ_T 得到 **inf**（curvature ≥ 0），
那是**步长太小被数值噪声淹没**，不是真的没有曲率。本脚本对每个参数扫多个步长，
**先验证二阶差分收敛，再取 SE**——步长不收敛的一律标为不可用。

用法
----
    python check_pure.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from check_tpath import make_trials  # noqa: E402
from design_fim import TRUTH  # noqa: E402
from likelihood import _bounds_for, log_likelihood  # noqa: E402
from mapping import WITHIN_FREE  # noqa: E402

NAMES = list(WITHIN_FREE)
LO, HI = _bounds_for(NAMES)
TRU = TRUTH.vector(NAMES)

#: 每个参数的扫描半宽（相对真值或绝对量）
SPAN = {
    "d_ref":   ("abs", 0.25), "beta_T":  ("abs", 1.5),  "tau_T":   ("rel", 0.60),
    "beta_S":  ("abs", 0.30), "beta_ST": ("abs", 0.60), "a_ref":   ("abs", 0.25),
    "delta_a": ("abs", 1.0),  "tau_a":  ("rel", 0.80),  "t0":      ("abs", 0.06),
}


def curve(tr, nm, npts=25, span=None):
    """纯切片：只动 nm，其余钉在真值。返回 (参数值, Δll)。"""
    k = NAMES.index(nm)
    t = float(TRU[k])
    kind, s = span or SPAN[nm]
    delta = s * (abs(t) if kind == "rel" else 1.0)
    lo = max(LO[k], t - delta)
    hi = min(HI[k], t + delta)
    xs = np.linspace(lo, hi, npts)
    ll0 = log_likelihood(TRUTH, tr)
    ys = np.array([log_likelihood(TRUTH.replace(**{nm: float(x)}), tr) - ll0
                   for x in xs])
    return xs, ys


def curvature_scan(tr, nm, rel_steps=(1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5)):
    """对每个参数扫步长，检查二阶差分是否收敛；返回 (h 列表, d²ll 列表)。"""
    k = NAMES.index(nm)
    t = float(TRU[k])
    f0 = log_likelihood(TRUTH, tr)
    hs, d2s = [], []
    for r in rel_steps:
        h = r * max(HI[k] - LO[k], 1e-9)
        lp = log_likelihood(TRUTH.replace(**{nm: t + h}), tr)
        lm = log_likelihood(TRUTH.replace(**{nm: t - h}), tr)
        hs.append(h); d2s.append((lp - 2 * f0 + lm) / h ** 2)
    return hs, d2s


def main():
    t_start = time.time()
    _, sim, tr = make_trials(seed=7)
    ll0 = log_likelihood(TRUTH, tr)
    print("=" * 104)
    print("单参数纯切片（其余 8 参数钉死在真值）—— D4，576 试次")
    print(f"  ll(真值) = {ll0:.4f}")
    print("=" * 104)
    print("  读法：切片陡 ⇒ 该参数**单独**可估；切片平 ⇒ 设计对它没信息（设计问题）")
    print("        切片陡但剖面平 ⇒ 被其它参数**补偿**了（模型参数化问题）\n")

    print(f"  {'参数':10s} {'真值':>9s} {'2单位区间（纯切片）':>22s} {'宽度':>9s} "
          f"{'单点曲率SE':>11s} {'形状':>10s}")
    pure = {}
    for nm in NAMES:
        xs, ys = curve(tr, nm)
        m = ys.max()
        ins = xs[ys >= m - 2.0]
        iv = (float(ins.min()), float(ins.max())) if ins.size else (np.nan, np.nan)
        w = iv[1] - iv[0] if ins.size else np.nan
        # 以真值为中心 ±1 单位内的点做二次拟合，取曲率
        sel = np.abs(ys) <= 1.0
        se = np.nan
        if sel.sum() >= 3:
            c = np.polyfit(xs[sel] - float(TRU[NAMES.index(nm)]), ys[sel], 2)
            if c[0] < 0:
                se = 1.0 / np.sqrt(-c[0])
        # 形状判读
        if not np.isfinite(w):
            shape = "无2单位域"
        elif w > 0.6 * (xs[-1] - xs[0]):
            shape = "★平坦"
        elif abs(float(TRU[NAMES.index(nm)]) - iv[0]) > 0.55 * w or \
             abs(iv[1] - float(TRU[NAMES.index(nm)])) > 0.55 * w:
            shape = "偏斜/真值在边缘"
        else:
            shape = "良好"
        pure[nm] = {"xs": xs, "ys": ys, "iv": iv, "w": w, "se": se, "shape": shape}
        print(f"  {nm:10s} {TRU[NAMES.index(nm)]:9.4f} "
              f"[{iv[0]:7.4f},{iv[1]:7.4f}]".rjust(0), end="")
        print(f" {w:9.4f} {se:11.4f} {shape:>10s}")

    # ---------------- 逐个打印形状可疑的切片 ----------------
    print("\n" + "=" * 104)
    print("形状可疑或关键的切片明细")
    print("=" * 104)
    for nm in ("tau_T", "beta_T", "beta_ST", "delta_a", "tau_a", "d_ref"):
        d = pure[nm]
        print(f"\n  ── {nm}（真值 {TRU[NAMES.index(nm)]}）── {d['shape']}")
        for x, y in zip(d["xs"], d["ys"]):
            bar = "█" * int(max(0, min(44, round(y + 6))))
            mark = " ←真值" if abs(x - float(TRU[NAMES.index(nm)])) < \
                (d["xs"][1] - d["xs"][0]) * 0.6 else ""
            print(f"     {x:8.4f} {y:+7.3f} {bar}{mark}")

    # ---------------- 步长收敛性（修正 inf 问题）----------------
    print("\n" + "=" * 104)
    print("步长收敛性自检：d²ll/dθ² 随 h 的变化（只在收敛区读 SE）")
    print("=" * 104)
    print(f"  {'参数':10s} " + " ".join(f"{'h=%.0e' % h:>12s}" for h in
                                        (1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5)))
    for nm in NAMES:
        hs, d2s = curvature_scan(tr, nm)
        print(f"  {nm:10s} " + " ".join(f"{v:12.3f}" for v in d2s))
    print("\n  注：h 是**参数单位**的步长（= rel × 边界宽度）。若某一 h 之下数值开始乱跳，")
    print("      说明该步长已被数值噪声淹没——`design_ident.py` 对 τ_T/τ_a 报 inf 即此原因。")

    # ---------------- 设计 vs 模型 ----------------
    print("\n" + "=" * 104)
    print("★ 判读：设计问题还是模型参数化问题")
    print("=" * 104)
    prof_w = {"tau_T": 0.045, "beta_T": 3.0, "beta_ST": 1.0, "delta_a": 3.0}
    for nm in ("tau_T", "beta_T", "beta_ST", "delta_a"):
        pw = prof_w[nm]
        cw = pure[nm]["w"]
        if not np.isfinite(cw):
            verdict = "切片无法界定（数值）"
        elif cw / max(pw, 1e-9) < 0.2:
            verdict = "**设计问题**：纯切片已窄，剖面却宽 → 是补偿放大"
        else:
            verdict = "模型参数化为主"
        print(f"  {nm:10s} 纯切片宽 {cw:8.4f}   剖面宽 {pw:8.4f}   比 {cw/max(pw,1e-9):6.2f}   {verdict}")
    print(f"\n  总耗时 {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
