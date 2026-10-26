# -*- coding: utf-8 -*-
"""SPE 到底有多大：真实数据 vs 生成模型（真值）vs 拟合后模型。

三个问题，一次量清：
1. 真实 17 人里 Self−Other 的 ΔRT 有多大、在哪几个分位明显、几个人方向一致；
2. 生成模型在 `TRUTH_LIN` / `QC_TRUTH` 下的 ΔRT 有多大（用户说「生成数据的 Self/Other 分不开」，
   要区分是「真值本来就小」还是「画图/抽样问题」）；
3. 拟合后的 M-T3 组均值参数能复现出多大的 ΔRT（判模型层要不要改）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"),
                str(REPO / "1_Code" / "DDM_Core" / "_scratch"),
                str(REPO / "1_Code" / "Experiment")]

import design_grid as DG          # noqa: E402
import stage8_run as S            # noqa: E402
import twophase as TP             # noqa: E402
import _make_ddm_pilot as GEN     # noqa: E402
from mapping import MappingParams  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"
QS = [10, 25, 50, 75, 90]


def q(x):
    return np.percentile(np.asarray(x, float), QS) * 1000.0


def delta_rt(rt_self, rt_other):
    return q(rt_self) - q(rt_other)


def boot_delta(rt_self, rt_other, n_boot=2000, seed=7):
    rng = np.random.default_rng(seed)
    ds = np.empty((n_boot, len(QS)))
    for i in range(n_boot):
        a = rng.choice(rt_self, rt_self.size, replace=True)
        b = rng.choice(rt_other, rt_other.size, replace=True)
        ds[i] = delta_rt(a, b)
    return np.percentile(ds, [2.5, 97.5], axis=0)


# --------------------------------------------------------------------------- #
print("=" * 92)
print("一、真实数据（17 名在册被试、stage8 实际保留的响应试次）")
print("=" * 92)
people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
rt, corr, is_self, P = [], [], [], []
for p in people:
    tr = p["tr"]
    om = np.asarray(tr["omission"]) == 0
    side = np.asarray(tr["side"])[om]
    match = np.asarray(tr["is_match"])[om]
    rt.append(np.asarray(tr["rt"])[om])
    corr.append((side == 1) == (match == 1))
    is_self.append(np.asarray(tr["is_self"])[om])
    P.append(np.asarray(tr["P"])[om])
rt = np.concatenate(rt); corr = np.concatenate(corr)
is_self = np.concatenate(is_self); P = np.concatenate(P)

sm, om_ = is_self == 1, is_self == 0
print(f"试次：自我 {sm.sum()}、他人 {om_.sum()}")
print(f"RT 中位：自我 {np.median(rt[sm]) * 1000:.0f} ms、他人 {np.median(rt[om_]) * 1000:.0f} ms"
      f" ⇒ Δ中位 {np.median(rt[sm]) * 1000 - np.median(rt[om_]) * 1000:+.0f} ms")
print(f"正确率：自我 {corr[sm].mean():.3f}、他人 {corr[om_].mean():.3f}"
      f" ⇒ Δacc {corr[sm].mean() - corr[om_].mean():+.3f}")

d = delta_rt(rt[sm], rt[om_])
ci = boot_delta(rt[sm], rt[om_])
print(f"\n{'分位':>6s}{'Self(ms)':>11s}{'Other(ms)':>11s}{'Δ(ms)':>9s}{'95%CI':>18s}{'显著':>6s}")
for k, qq in enumerate(QS):
    lo, hi = ci[0, k], ci[1, k]
    sig = "✅" if (lo > 0 or hi < 0) else "—"
    print(f"{qq:>6d}{q(rt[sm])[k]:>11.0f}{q(rt[om_])[k]:>11.0f}{d[k]:>9.0f}"
          f"   [{lo:>6.0f},{hi:>6.0f}]{sig:>6s}")

print("\n按 P 组（P = 自我被掩蔽的比例，越大越快）：")
for pv in sorted(set(int(x) for x in P)):
    m = P == pv
    ds_ = delta_rt(rt[sm & m], rt[om_ & m])
    print(f"  P={pv:>3d}  n={int(m.sum()):>4d}  Δ中位 {np.median(rt[sm & m]) * 1000 - np.median(rt[om_ & m]) * 1000:+.0f} ms"
          f"  Δp90 {ds_[-1]:+.0f} ms  Δacc {corr[sm & m].mean() - corr[om_ & m].mean():+.3f}")

pos = 0
print("\n逐被试 Δ中位（self−other）：")
for p in people:
    tr = p["tr"]
    o = np.asarray(tr["omission"]) == 0
    s_ = np.asarray(tr["is_self"])[o] == 1
    r_ = np.asarray(tr["rt"])[o]
    dd = (np.median(r_[s_]) - np.median(r_[~s_])) * 1000
    pos += dd > 0
    print(f"  {int(p['group'])}-{int(p['subject'])}: {dd:+6.0f} ms", end="\n" if int(p['subject']) % 3 == 0 else "")
print(f"\nΔ中位 > 0（自我更慢）的被试：{pos}/{len(people)}")

# --------------------------------------------------------------------------- #
print("\n" + "=" * 92)
print("二、生成模型真值下的 ΔRT（同一份设计 × 8 个随机种子 ≈ 4,600 试次）")
print("=" * 92)
design, _meta, _mk = GEN.rows_for_subject(1, 12, 1, 0)
Is = np.asarray(design["is_self"], float) == 1


def sim_pool(truth, rho, rng0=2026, n_seed=8):
    rs, os_, Is_ = [], [], []
    for s in range(n_seed):
        sim = TP.simulate_euler_subject(design, truth, rho,
                                        np.random.default_rng(rng0 + s), dt=5e-5)
        rs.append(np.asarray(sim["rt"], float))
        os_.append(np.asarray(sim["omission"], int))
        Is_.append(Is)
    r = np.concatenate(rs).ravel()
    o = np.concatenate(os_).ravel()
    s_ = np.concatenate(Is_).ravel()
    keep = (o == 0) & np.isfinite(r)
    return r[keep], s_[keep], float((~keep).mean())


for name, truth in (("TRUTH_LIN", DG.TRUTH_LIN), ("QC_TRUTH", GEN.QC_TRUTH)):
    r, s_, om_rate = sim_pool(truth, 0.8)
    dd = delta_rt(r[s_], r[~s_])
    print(f"{name}: 自我中位 {np.median(r[s_]) * 1000:.0f} ms、他人 {np.median(r[~s_]) * 1000:.0f} ms"
          f" ⇒ Δ中位 {np.median(r[s_]) * 1000 - np.median(r[~s_]) * 1000:+.0f} ms（漏答 {om_rate:.3f}）")
    print("    Δ 分位(10/25/50/75/90) = " + " ".join(f"{x:+.0f}" for x in dd) + " ms")
    pr = truth.as_dict() if hasattr(truth, "as_dict") else dict(truth)
    print(f"    参数：d_ref {pr['d_ref']:.3f}、beta_S {pr['beta_S']:.3f}、"
          f"beta_ST {pr['beta_ST']:.3f}、dz_S {pr.get('dz_S', 0.0):.3f}")

# --------------------------------------------------------------------------- #
print("\n" + "=" * 92)
print("三、拟合后（M-T3 组均值参数）能生成多大的 ΔRT —— 用 Stage 8 的 MAP 反推")
print("=" * 92)
import json
import hier as H
from likelihood import _from_x
from twophase import RHO_NAME

RES = REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline" / "stage8_d123" / "stage8_results.json"
res = json.loads(RES.read_text(encoding="utf-8"))
names = list(MappingParams(shape_model="lin").__dataclass_fields__)  # noqa: SLF001
free = [n for n in names if n in ("d_ref", "beta_T", "beta_S", "beta_ST", "a_ref",
                                  "delta_a", "t0", "dz_S")]
lo, hi = H._bounds_with_rho(free)
for gid, g in res["groups"].items():
    fit = g["M-T3"]["fit"]
    hypo = g["M-T3"]["hyper"]
    mu = np.asarray(hypo["mu"])
    if mu.ndim == 2:
        mu = mu[-1]
    th = _from_x(np.asarray(mu, float), lo, hi)
    p = MappingParams(shape_model="lin", **{n: float(v) for n, v in zip(free, th)})
    r, s_, om_rate = sim_pool(p, 1.0, rng0=11 + int(gid))
    dd = delta_rt(r[s_], r[~s_])
    print(f"组 {gid}: 自我中位 {np.median(r[s_]) * 1000:.0f} ms、他人 {np.median(r[~s_]) * 1000:.0f} ms"
          f" ⇒ Δ中位 {np.median(r[s_]) * 1000 - np.median(r[~s_]) * 1000:+.0f} ms、"
          f"Δp90 {dd[-1]:+.0f} ms（beta_S {p.beta_S:+.3f}、dz_S {p.dz_S:+.3f}、漏答 {om_rate:.3f}）")

# --------------------------------------------------------------------------- #
print("\n" + "=" * 92)
print("四、逐被试 MAP 参数 + 该被试自己的试次设计（真正的 PPC 口径）")
print("=" * 92)
free8 = ["d_ref", "beta_T", "beta_S", "beta_ST", "a_ref", "delta_a", "t0", "dz_S"]
lo8, hi8 = H._bounds_with_rho(free8)
rows = []
for (gid_s, g), pps in zip(res["groups"].items(), [None] * 4):
    pass
for gid_s, g in res["groups"].items():
    modes = np.asarray(g["M-T3"]["fit"]["modes"], float)
    mine = [p for p in people if int(p["group"]) == int(gid_s)]
    mine.sort(key=lambda p: int(p["subject"]))
    for j, pp in enumerate(mine):
        if j >= len(modes):
            break
        th = _from_x(modes[j], lo8, hi8)
        par = MappingParams(shape_model="lin", **{n: float(v) for n, v in zip(free8, th)})
        tr = pp["tr"]
        des = {"P": np.asarray(tr["P"], float), "T": np.asarray(tr["T"], float),
               "W": np.asarray(tr["W"], float),
               "is_self": np.asarray(tr["is_self"], float),
               "is_match": np.asarray(tr["is_match"], int)}
        Is_s = des["is_self"] == 1
        rs, os_, ss = [], [], []
        for k_ in range(3):
            sim = TP.simulate_euler_subject(des, par, 1.0,
                                            np.random.default_rng(500 + 7 * j + k_), dt=5e-5)
            rs.append(np.asarray(sim["rt"], float))
            os_.append(np.asarray(sim["omission"], int))
            ss.append(Is_s)
        r = np.concatenate(rs).ravel(); o = np.concatenate(os_).ravel()
        s_ = np.concatenate(ss).ravel()
        keep = (o == 0) & np.isfinite(r)
        rr, ss2 = r[keep], s_[keep]
        if ss2.sum() < 50 or (~ss2).sum() < 50:
            continue
        obs_om = float(np.mean(np.asarray(tr["omission"]) == 1))
        rows.append((int(gid_s), int(pp["subject"]),
                     float(np.median(rr[ss2]) * 1000 - np.median(rr[~ss2]) * 1000),
                     float(1.0 - keep.mean()), obs_om,
                     float(np.median(rr) * 1000)))
rows.sort(key=lambda x: x[2])
print(f"{'被试':>7s}{'模型Δ中位':>11s}{'模型漏答':>9s}{'实测漏答':>9s}{'模型RT中位':>11s}")
for gid_s, sub, dd, om_m, om_o, rtm in rows:
    print(f"{f'{gid_s}-{sub}':>7s}{dd:>10.0f}ms{om_m * 100:>8.1f}%{om_o * 100:>8.1f}%{rtm:>10.0f}ms")
if rows:
    arr = np.array([r[2] for r in rows])
    print(f"\n模型 Δ中位：均值 {arr.mean():+.0f} ms、范围 {arr.min():+.0f}…{arr.max():+.0f} ms、"
          f"负号人数 {int((arr < 0).sum())}/{arr.size}（实测：均值约 −42 ms、负号 17/17）")
