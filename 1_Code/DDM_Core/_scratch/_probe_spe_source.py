# -*- coding: utf-8 -*-
"""现在的 SPE 从哪里来？——把模型的三条身份通道逐条关掉，看 ΔRT/ΔACC 掉多少。

通道（`1_Code/DDM_Core/mapping.py`）：
  beta_S   漂移通道：d += is_self * beta_S            —— 两个匹配条件同向变快
  beta_ST  漂移×T 通道：d += is_self * beta_ST * dqt  —— 同上，随 T 放大
  dz_S     判据通道：z/a = z_ratio + is_self * dz_S   —— 只帮"匹配"这一侧

对照组：Stage 8 组 2 的 M-T3 组均值（真实数据拟合）vs 生成真值 TRUTH_LIN。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"),
                str(REPO / "1_Code" / "Experiment")]

import design_grid as DG          # noqa: E402
import hier as H                  # noqa: E402
import likelihood as L            # noqa: E402
import stage8_run as S            # noqa: E402
import twophase as TP             # noqa: E402
from mapping import MappingParams  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
RES = REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "stage8_d123" / "stage8_results.json"


def group_params(gid: str, model: str) -> MappingParams:
    """把组层 x 空间均值变换回参数尺度。"""
    g = json.loads(RES.read_text(encoding="utf-8"))["groups"][gid][model]
    from mapping import WITHIN_FREE_LIN as names
    lo, hi = H._bounds_with_rho(list(names))
    x = np.asarray(g["hyper"]["mu"])[-1]
    vals = L._from_x(np.asarray(x, float), np.asarray(lo, float), np.asarray(hi, float))
    return MappingParams(**{**DG.TRUTH_LIN.__dict__, **{n: float(v) for n, v in zip(names, vals)}})


def cells_from_design(tr, key_mask=None):
    """把某被试的逐试次设计压成 (P,T,W,is_self,is_match) 计数单元。"""
    P = np.asarray(tr["P"], float); T = np.asarray(tr["T"], float)
    W = np.asarray(tr["W"], float); sf = np.asarray(tr["is_self"], float)
    mt = np.asarray(tr["is_match"], float)
    keys = np.stack([P, T, W, sf, mt], axis=1)
    uniq, cnt = np.unique(np.round(keys, 6), axis=0, return_counts=True)
    return uniq, cnt


def sim(uniq, cnt, p: MappingParams, k: float = 3.0, seed: int = 11):
    """逐单元抽样，返回 pooled (rt, correct, is_self, is_match)。"""
    rng = np.random.default_rng(seed)
    R, C, SF, MT = [], [], [], []
    for (P, T, W, sf, mt), c in zip(uniq, cnt):
        n = int(max(round(c * k), 600))
        d = {"P": np.array([P]), "T": np.array([T]), "W": np.array([W]),
             "is_self": np.array([sf]), "is_match": np.array([mt])}
        tp = TP.trial_params(d, p)
        v, a, z = float(tp["v"][0]), float(tp["a"][0]), float(tp["z"][0])
        t0 = float(tp["t0"])
        tau, b = TP.sample_step(v, 0.8 * v, a, z, float(T), n, rng,
                                t_max=float(W) + 0.05, n_grid=1500)
        rt = tau + t0
        ok = np.isfinite(rt) & (rt <= float(W))
        resp_match = (b == 1)
        corr = resp_match if mt == 1 else ~resp_match
        R.append(rt[ok]); C.append(corr[ok])
        SF.append(np.full(ok.sum(), sf)); MT.append(np.full(ok.sum(), mt))
    return (np.concatenate(R), np.concatenate(C), np.concatenate(SF), np.concatenate(MT))


def report(tag, r, c, sf, mt):
    out = {}
    for name, m in (("self_match", (sf == 1) & (mt == 1)), ("self_nonmatch", (sf == 1) & (mt == 0)),
                    ("other_match", (sf == 0) & (mt == 1)), ("other_nonmatch", (sf == 0) & (mt == 0))):
        out[name] = (float(np.median(r[m])) * 1000, float(c[m].mean()), int(m.sum()))
    d_m = out["self_match"][0] - out["other_match"][0]
    d_n = out["self_nonmatch"][0] - out["other_nonmatch"][0]
    a_m = out["self_match"][1] - out["other_match"][1]
    a_n = out["self_nonmatch"][1] - out["other_nonmatch"][1]
    print(f"  {tag:<26}ΔRT匹配 {d_m:+7.0f}  ΔRT非匹配 {d_n:+7.0f}  |  "
          f"ΔACC匹配 {a_m:+.3f}  ΔACC非匹配 {a_n:+.3f}")
    return dict(d_rt_match=d_m, d_rt_nonmatch=d_n, d_acc_match=a_m, d_acc_nonmatch=a_n,
                med_match=out["self_match"][0], cells=out)


def main():
    people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
    # 组 2 的第一个被试（P=32）作为设计模板
    tr = people[0]["tr"]
    uniq, cnt = cells_from_design(tr)
    print(f"设计模板：{cnt.sum()} 试次、{len(uniq)} 个单元\n")

    p_fit = group_params("2", "M-T3")
    print("组 2 M-T3 组均值：d_ref=%.3f beta_T=%.3f beta_S=%.4f beta_ST=%.3f a_ref=%.3f "
          "delta_a=%.4f t0=%.3f dz_S=%.4f\n"
          % (p_fit.d_ref, p_fit.beta_T, p_fit.beta_S, p_fit.beta_ST,
             p_fit.a_ref, p_fit.delta_a, p_fit.t0, p_fit.dz_S))

    print("一、Stage 8 拟合参数（组 2 M-T3）：逐条关掉身份通道")
    variants = [("全部通道（拟合值）", p_fit),
                ("beta_S = 0", MappingParams(**{**p_fit.__dict__, "beta_S": 0.0})),
                ("dz_S = 0", MappingParams(**{**p_fit.__dict__, "dz_S": 0.0})),
                ("beta_ST = 0", MappingParams(**{**p_fit.__dict__, "beta_ST": 0.0})),
                ("三条全关", MappingParams(**{**p_fit.__dict__, "beta_S": 0.0,
                                              "dz_S": 0.0, "beta_ST": 0.0}))]
    for tag, p in variants:
        report(tag, *sim(uniq, cnt, p))

    print("\n二、生成真值 TRUTH_LIN：把 dz_S 调到拟合值会怎样")
    g2 = [("TRUTH_LIN 原样（dz_S=0）", DG.TRUTH_LIN),
          ("TRUTH_LIN + dz_S=0.02", MappingParams(**{**DG.TRUTH_LIN.__dict__, "dz_S": 0.02})),
          ("TRUTH_LIN + dz_S=0.04", MappingParams(**{**DG.TRUTH_LIN.__dict__, "dz_S": 0.04})),
          ("TRUTH_LIN + dz_S=0.06", MappingParams(**{**DG.TRUTH_LIN.__dict__, "dz_S": 0.06}))]
    for tag, p in g2:
        report(tag, *sim(uniq, cnt, p))

    print("\n三、真实数据（同被试，同一份设计）对照")
    om = np.asarray(tr["omission"]) == 0
    r = np.asarray(tr["rt"])[om]
    sf = np.asarray(tr["is_self"])[om]; mt = np.asarray(tr["is_match"])[om]
    side = np.asarray(tr["side"])[om]
    corr = (side == 1) == (mt == 1)
    report("实测", r, corr, sf, mt)


if __name__ == "__main__":
    main()
