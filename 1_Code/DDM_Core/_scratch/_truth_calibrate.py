# -*- coding: utf-8 -*-
"""真值校准：把 TRUTH_LIN 的 SPE 通道调到与实测 (ΔRT, Δacc, 漏答率, RT 中位) 一致。

背景
----
实测（17 人 / 7,144 响应试次）：ΔRT 中位 **−33 ms**、Δacc **+0.067**、漏答 ≈ 27%、
RT 中位 692 ms。而 `design_grid.TRUTH_LIN` 的 SPE 只有 `beta_S = 0.148`（加性漂移偏移），
在 12 个设计格上格均 ΔRT 仅 **−12 ms**、Δacc +0.052；单靠漂移放大 `beta_S` 又会把
正确率差一起放大（β = 0.59 时 Δacc 到 +0.158）。

因此校准要**两个通道一起动**：
  * `beta_S`（漂移通道）—— 对正确率敏感；
  * `dz_S`（起点/判据通道）—— 对 RT 更敏感。
两个参数的组合能把 (ΔRT, Δacc) 从一条一维曲线上「解耦」出来。

用法：`python _scratch/_truth_calibrate.py`
输出：最优 (beta_S, dz_S)、对应四目标读数、以及可直接喂给 `MappingParams` 的 kwargs。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"), str(REPO / "1_Code" / "Experiment")]

import design_grid as DG                   # noqa: E402
import twophase as TP                     # noqa: E402
import stage8_run as S                    # noqa: E402
from mapping import MappingParams         # noqa: E402

OUT = REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "truth_calibrated_20261026.json"
NS = 2500
CELLS = [(p, t, w) for p in (0.0, 120.0)
         for t, w in ((0.100, 0.800), (0.150, 1.200), (0.250, 1.800))]
Q = (0.25, 0.50, 0.75)


def draw(p: MappingParams, P, T, W, is_self, n: int = NS):
    d = {"P": np.array([P]), "T": np.array([T]), "W": np.array([W]),
         "is_self": np.array([is_self]), "is_match": np.array([1.0])}
    tp = TP.trial_params(d, p)
    v, a, z = float(tp["v"][0]), float(tp["a"][0]), float(tp["z"][0])
    t0 = float(tp["t0"])
    tau, b = TP.sample_step(v, 0.8 * v, a, z, T, n,
                            np.random.default_rng(7), n_grid=2500)
    rt = tau + t0
    ok = np.isfinite(rt) & (rt <= W)
    return rt[ok], (b[ok] == 1)


def predict(p: MappingParams) -> dict:
    """返回格均 ΔRT(p25/p50/p75)、Δacc、漏答率、RT 中位。"""
    drt, dacc, oms, meds = [], [], [], []
    for P, T, W in CELLS:
        rt_s, ok_s = draw(p, P, T, W, 1.0)
        rt_o, ok_o = draw(p, P, T, W, 0.0)
        drt.append((np.quantile(rt_s, Q) - np.quantile(rt_o, Q)) * 1000)
        dacc.append(ok_s.mean() - ok_o.mean())
        oms.append(0.5 * (1 - len(rt_s) / NS) + 0.5 * (1 - len(rt_o) / NS))
        meds.append(0.5 * (np.median(rt_s) + np.median(rt_o)) * 1000)
    drt = np.mean(np.array(drt), axis=0)
    return {"drt_p25": float(drt[0]), "drt_p50": float(drt[1]), "drt_p75": float(drt[2]),
            "dacc": float(np.mean(dacc)), "omission": float(np.mean(oms)),
            "rt_med": float(np.mean(meds))}


def loss(g: dict, tgt: dict) -> float:
    """相对误差平方和；ΔRT 用 p50 与 p25→p75 的形状各占一半。"""
    r = ((g["drt_p50"] - tgt["drt_p50"]) / 33.0) ** 2
    r += 0.5 * (((g["drt_p25"] - tgt["drt_p25"]) / 15.0) ** 2
                + ((g["drt_p75"] - tgt["drt_p75"]) / 20.0) ** 2)
    r += ((g["dacc"] - tgt["dacc"]) / 0.067) ** 2
    r += 0.5 * ((g["omission"] - tgt["omission"]) / 0.10) ** 2
    r += 0.3 * ((g["rt_med"] - tgt["rt_med"]) / 150.0) ** 2
    return float(r)


def measured_targets() -> dict:
    people, _ = S.collect([REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"],
                          None, DG.TRUTH_LIN)
    rt, sm, co = [], [], []
    for one in people:
        tr = one["tr"]
        o = np.asarray(tr["omission"]) == 0
        rt.append(np.asarray(tr["rt"])[o])
        sm.append(np.asarray(tr["is_self"])[o] == 1)
        co.append((np.asarray(tr["side"])[o] == 1) == (np.asarray(tr["is_match"])[o] == 1))
    rt, sm, co = (np.concatenate(x) for x in (rt, sm, co))
    dq = (np.quantile(rt[sm], Q) - np.quantile(rt[~sm], Q)) * 1000
    return {"drt_p25": float(dq[0]), "drt_p50": float(dq[1]), "drt_p75": float(dq[2]),
            "dacc": float(co[sm].mean() - co[~sm].mean()),
            "omission": float(1 - rt.size / 8355), "rt_med": float(np.median(rt) * 1000)}


if __name__ == "__main__":
    t0 = time.time()
    tgt = measured_targets()
    print(f"[{time.time()-t0:.0f}s] 实测目标：ΔRT p25/p50/p75 = "
          f"{tgt['drt_p25']:+.0f}/{tgt['drt_p50']:+.0f}/{tgt['drt_p75']:+.0f} ms、"
          f"Δacc {tgt['dacc']:+.3f}、漏答 {tgt['omission']:.1%}、RT 中位 {tgt['rt_med']:.0f} ms")

    base = DG.TRUTH_LIN
    print(f"\n当前真值（beta_S={base.beta_S:.3f}, dz_S={base.dz_S:.3f}）：")
    g0 = predict(base)
    print("   " + ", ".join(f"{k}={v:+.3f}" if isinstance(v, float) else f"{k}={v}"
                            for k, v in g0.items()) + f"  loss={loss(g0, tgt):.3f}")

    print("\n扫描 beta_S × dz_S（每格 2500 抽样，6 个 (P,T,W) 格）")
    print("  beta_S   dz_S   ΔRT p25/p50/p75    Δacc    漏答   RT中位   loss")
    rows = []
    for b in (-0.30, -0.15, 0.00, 0.15, 0.30, 0.45):
        for z in (0.00, 0.02, 0.04, 0.06, 0.08):
            p = MappingParams(**{**base.__dict__, "beta_S": b, "dz_S": z})
            g = predict(p)
            L = loss(g, tgt)
            rows.append((L, b, z, g))
            print(f"  {b:+5.2f}  {z:4.2f}  {g['drt_p25']:+5.0f}/{g['drt_p50']:+5.0f}/"
                  f"{g['drt_p75']:+5.0f}  {g['dacc']:+.3f}  {g['omission']:5.1%}  "
                  f"{g['rt_med']:5.0f}  {L:6.3f}   [{time.time()-t0:.0f}s]")
    rows.sort(key=lambda r: r[0])
    best = rows[0]
    print("\n最优三组：")
    for L, b, z, g in rows[:3]:
        print(f"  beta_S={b:+.2f}, dz_S={z:.2f}  loss={L:.3f}  → ΔRT {g['drt_p50']:+.0f} ms、"
              f"Δacc {g['dacc']:+.3f}、漏答 {g['omission']:.1%}、RT 中位 {g['rt_med']:.0f} ms")

    L, b, z, g = best
    payload = {"beta_S": b, "dz_S": z, "loss": L, "predicted": g, "target": tgt,
               "note": "由 _scratch/_truth_calibrate.py 生成；只改 beta_S/dz_S，其余沿用 TRUTH_LIN"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaved: {OUT}\n总耗时 {time.time()-t0:.0f}s")
