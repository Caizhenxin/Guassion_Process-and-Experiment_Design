# -*- coding: utf-8 -*-
"""L1：形状族的「曲率信号」有多大——先用解析法，不拟合。

思路
----
设计里的 T 只有三档（100 / 150 / 250 ms）。任何形状族只要有两个自由参数，就能被
拉成穿过这三个点的同一条曲线；所以「族与族在**设计点上**是否等价」这件事没有信息量。
真正有信息量的是 LOCV：用两端（100、250）去预测中间（150）。此时形状族各自的
**插值曲率**不同，残差就是设计能提供的最大的形状信号。

本脚本：
  1. 以 `TRUTH_LIN` 在 (P=120, T=150, W=1200) 的灵敏度把「漂移差」换算成毫秒
     （ΔRT ≈ k · Δd/d，k 由抽样测出）；
  2. 对四族各取若干合理形状参数，锚定 d(100)、d(250) 与 TRUTH_LIN 一致，
     算它们插值出来的 d(150) 与线性的差，再换算成 ms；
  3. 用「加一档 T=400 ms」的外推残差作对照，看补档能买到多少分离度。

判据闸门（预登记 `5_Reference/08_工作流/形状族恢复_预登记_20261026.md`）：
单格 n=48、σ≈196 ms ⇒ 单格 SE≈35 ms；20 人合并 SE≈8 ms ⇒ **2 SE ≈ 16 ms**。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core")]

import design_grid as DG                   # noqa: E402
import twophase as TP                     # noqa: E402

T_REF, T_MID, T_HI, T_EXTRA = 0.100, 0.150, 0.250, 0.400


def sensitivity() -> tuple[float, float]:
    """在 (P=120, T=150, W=1200) 上把 d 抬高 10%，量 RT 中位变化，返回 (k_ms_per_rel, rt0)。"""
    p = DG.TRUTH_LIN
    d0 = float(TP.trial_params({"P": np.array([120.0]), "T": np.array([T_MID]),
                                "W": np.array([1.2]), "is_self": np.array([1.0]),
                                "is_match": np.array([1.0])}, p)["d"][0])

    def med(d_target: float) -> float:
        # 用 d_target 反推等价参数：临时把 d_ref 平移，其它不动
        q = type(p)(**{**p.__dict__, "d_ref": p.d_ref + (d_target - d0)})
        tp = TP.trial_params({"P": np.array([120.0]), "T": np.array([T_MID]),
                              "W": np.array([1.2]), "is_self": np.array([1.0]),
                              "is_match": np.array([1.0])}, q)
        v, a, z = float(tp["v"][0]), float(tp["a"][0]), float(tp["z"][0])
        tau, b = TP.sample_step(v, 0.8 * v, a, z, T_MID, 4000,
                                np.random.default_rng(3), n_grid=3000)
        rt = tau + float(tp["t0"])
        ok = np.isfinite(rt) & (rt <= 1.2)
        return float(np.median(rt[ok]) * 1000)

    rt0 = med(d0)
    rt1 = med(d0 * 1.10)
    return (rt1 - rt0) / 0.10, rt0


def families(p_dmid: float) -> dict[str, float]:
    """各族在 T_MID 处相对「线性插值」的漂移残差（已归一到 d(100)、d(250) 相同）。"""
    p = DG.TRUTH_LIN
    d_lo = p.d_ref
    d_hi = p.d_ref + p.beta_T * (T_HI - T_REF)          # lin 在 T_HI 的漂移
    span = d_hi - d_lo
    # 线性插值在 T_MID 的值
    lin_mid = d_lo + span * (T_MID - T_REF) / (T_HI - T_REF)

    def shape_pred(g) -> float:
        """把 g(T) 归一成穿过 (T_REF, d_lo) 与 (T_HI, d_hi)，返回 T_MID 的值。"""
        g0, g1, gm = g(T_REF), g(T_HI), g(T_MID)
        return d_lo + span * (gm - g0) / (g1 - g0)

    out = {}
    for tau in (0.05, 0.08, 0.12, 0.20):
        out[f"exp(τ={tau:.2f})"] = shape_pred(lambda T, tau=tau: 1 - np.exp(-T / tau)) - lin_mid
    for n in (2.0, 4.0, 8.0):
        for K in (0.12, 0.18, 0.25):
            out[f"sigmoid(n={n:g},K={K:.2f})"] = shape_pred(
                lambda T, n=n, K=K: T ** n / (K ** n + T ** n)) - lin_mid
    for gam in (0.3, 0.6, 1.0, 1.5):
        out[f"power(γ={gam:.1f})"] = shape_pred(lambda T, gam=gam: (T / T_REF) ** gam) - lin_mid
    out["lin（基线）"] = 0.0
    return out, lin_mid


def extrapolation(p_dmid: float) -> dict[str, float]:
    """用 (100, 250) 这条弦外推到 T=400 ms，各族偏离该直线的量（同样换算到 d 残差）。"""
    p = DG.TRUTH_LIN
    d_lo = p.d_ref
    d_hi = p.d_ref + p.beta_T * (T_HI - T_REF)
    span = d_hi - d_lo
    lin_ext = d_lo + span * (T_EXTRA - T_REF) / (T_HI - T_REF)

    def pred(g) -> float:
        g0, g1, ge = g(T_REF), g(T_HI), g(T_EXTRA)
        return d_lo + span * (ge - g0) / (g1 - g0)

    out = {}
    for tau in (0.05, 0.08, 0.12, 0.20):
        out[f"exp(τ={tau:.2f})"] = pred(lambda T, tau=tau: 1 - np.exp(-T / tau)) - lin_ext
    for n in (2.0, 4.0, 8.0):
        for K in (0.12, 0.18, 0.25):
            out[f"sigmoid(n={n:g},K={K:.2f})"] = pred(
                lambda T, n=n, K=K: T ** n / (K ** n + T ** n)) - lin_ext
    for gam in (0.3, 0.6, 1.0, 1.5):
        out[f"power(γ={gam:.1f})"] = pred(lambda T, gam=gam: (T / T_REF) ** gam) - lin_ext
    out["lin（基线）"] = 0.0
    return out, lin_ext


if __name__ == "__main__":
    k, rt0 = sensitivity()          # k = 每 100% 相对漂移变化的 RT 变化（ms），本设计约 −460
    print(f"灵敏度：d 抬高 10% ⇒ RT 中位变化 {k:+.0f} ms"
          f"（基线 RT 中位 {rt0:.0f} ms, T={T_MID*1000:.0f} ms）")
    print(f"换算：ΔRT(ms) = (Δd / d_mid) × {k:.0f}，d_mid ≈ 0.73（P=120、T=150 ms）\n")

    D_MID = 0.731
    for label, fn in (("LOCV：用 100/250 推 150 ms", families),
                      ("外推：用 100/250 弦推 400 ms", extrapolation)):
        res, anchor = fn(0.0)
        print(f"=== {label} ===")
        print("  族 / 形状参数            漂移残差(d)   换算 RT(ms)   相对 16 ms 闸门")
        for name, dd in sorted(res.items(), key=lambda kv: abs(kv[1]), reverse=True):
            ms = (dd / D_MID) * k
            flag = "**超过**" if abs(ms) > 16 else "低于"
            print(f"  {name:24s} {dd:+.4f}      {ms:+6.1f}      {flag}")
        mx = max(abs((v / D_MID) * k) for v in res.values())
        print(f"  最大族间差：{mx:.1f} ms\n")
