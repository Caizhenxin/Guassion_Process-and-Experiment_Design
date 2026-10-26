# -*- coding: utf-8 -*-
"""三版对照图（最终版）：老 v2.4 / 新模型（解析抽样）/ 实测。

新模型面板不用 `simulate_step_subject`（288 试次要 90 s 且 median 的 SE 太大），
改成对 12 个设计格各抽 4000 个试次（同格 self/other 用同一随机流），总计 4.8 万/侧，
曲线平滑、ΔRT 的 SE 约 3 ms。
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"), str(REPO / "1_Code" / "Experiment")]

import design_grid as DG                   # noqa: E402
import twophase as TP                     # noqa: E402
import stage8_run as S                    # noqa: E402
from make_figures import setup_matplotlib  # noqa: E402

OLD = REPO / "1_Code" / "Python_for_Generate" / "Py" / "Generate_Data_v2.4_runner.py"
OUT = REPO / "3_Figures" / "_real_check"
CELLS = [(p, t, w) for p in (0.0, 8.0, 32.0, 120.0)
         for t, w in ((0.100, 0.800), (0.150, 1.200), (0.250, 1.800))]
NS = 4000
T0 = time.time()

# ---- 老 v2.4 ----
spec = importlib.util.spec_from_file_location("oldgen", OLD)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
df, _ = old.generate_dataset_s2(n_subjects=8, trials_per_sub=60, seed=42)
rt_old = df["RT"].to_numpy(float)
ok = np.isfinite(rt_old)
df, rt_old = df[ok], rt_old[ok]
corr_old = df["response"].to_numpy() == 1
self_old = df["label"].to_numpy() == "self"
print(f"[{time.time()-T0:.0f}s] 老 v2.4：{rt_old.size} 试次")

# ---- 新模型（解析抽样，TRUTH_LIN）----
p = DG.TRUTH_LIN
rt_new, sm_new, co_new = [], [], []
for P, T, W in CELLS:
    for is_self in (1.0, 0.0):
        d = {"P": np.array([P]), "T": np.array([T]), "W": np.array([W]),
             "is_self": np.array([is_self]), "is_match": np.array([1.0])}
        tp = TP.trial_params(d, p)
        v, a, z = float(tp["v"][0]), float(tp["a"][0]), float(tp["z"][0])
        t0 = float(tp["t0"])
        tau, b = TP.sample_step(v, 0.8 * v, a, z, T, NS,
                                np.random.default_rng(2026), n_grid=3000)
        rt = tau + t0
        keep = np.isfinite(rt) & (rt <= W)
        rt_new.append(rt[keep])
        sm_new.append(np.full(int(keep.sum()), is_self == 1.0))
        co_new.append(b[keep] == 1)          # is_match=1 ⇒ 上边界为正确
    print(f"[{time.time()-T0:.0f}s] 格 P={P:g} T={T*1000:g} W={W*1000:g} 完成")
rt_new, sm_new, co_new = (np.concatenate(x) for x in (rt_new, sm_new, co_new))
print(f"[{time.time()-T0:.0f}s] 新模型：{rt_new.size} 试次（漏答约 "
      f"{1 - rt_new.size / (NS * 2 * len(CELLS)):.0%}）")

# ---- 实测 ----
people, _ = S.collect([REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"], None, p)
rt_re, sm_re, co_re = [], [], []
for one in people:
    tr = one["tr"]
    o = np.asarray(tr["omission"]) == 0
    rt_re.append(np.asarray(tr["rt"])[o])
    sm_re.append(np.asarray(tr["is_self"])[o] == 1)
    co_re.append((np.asarray(tr["side"])[o] == 1) == (np.asarray(tr["is_match"])[o] == 1))
rt_re, sm_re, co_re = (np.concatenate(x) for x in (rt_re, sm_re, co_re))

rows = [
    ("老 v2.4：SPE 写成漂移乘法（self ×2.5 / stranger ×0.6）",
     rt_old, self_old, corr_old, ("self", "stranger")),
    ("新模型 TRUTH_LIN（12 格各 4000 试次）", rt_new, sm_new, co_new, ("self", "other")),
    ("实测 17 人", rt_re, sm_re, co_re, ("self", "other")),
]
plt, lang = setup_matplotlib("zh")
fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.0), sharey=True)
for ax, (title, rt, sm, co, labs) in zip(axes, rows):
    bins = np.linspace(0.15, 2.4, 60)
    for mask, c, lab in ((sm, "#1f77b4", labs[0]), (~sm, "#ff7f0e", labs[1])):
        ax.hist(rt[mask], bins=bins, density=True, alpha=0.5, color=c, label=lab)
    d_rt = (np.median(rt[sm]) - np.median(rt[~sm])) * 1000
    d_acc = co[sm].mean() - co[~sm].mean()
    ax.set_title(f"{title}\nΔRT = {d_rt:+.0f} ms，Δacc = {d_acc:+.3f}"
                 f"（负 ΔRT = 自我更快）", fontsize=9.5)
    ax.set_xlabel("RT（秒）")
    ax.set_xlim(0.15, 2.4)
    ax.legend(fontsize=8, loc="upper right")
    print(f"{title}: ΔRT {d_rt:+.0f} ms、Δacc {d_acc:+.3f}、n={rt.size}")
axes[0].set_ylabel("密度")
fig.suptitle("三版数据的 self/other 分离度：老版「看得出」是漂移率开到 3.5 倍换来的",
             fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.92))
out = OUT / "fig_spe_old_vs_new.png"
fig.savefig(out, bbox_inches="tight")
print("saved:", out, f"[{time.time()-T0:.0f}s]")
