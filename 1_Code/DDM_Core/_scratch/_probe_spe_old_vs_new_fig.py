# -*- coding: utf-8 -*-
"""三版数据放一起（老 v2.4 / 新模型 TRUTH_LIN / 实测），外加 beta_S / dz_S 轻量扫描。

关键修正：新模型必须用 `design_grid.TRUTH_LIN`（MappingParams 对象），
不能用 `MappingParams(shape_model="lin")`（那是默认参数，不是真值）。
设计改成**平衡因子**（is_self × is_match × P × T 各格等量），否则 self/other 的
match 比例不平衡会伪造出几十 ms 的假 ΔRT。
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"), str(REPO / "1_Code" / "Experiment")]

import design_grid as DG                  # noqa: E402
import twophase as TP                    # noqa: E402
import stage8_run as S                   # noqa: E402
from make_figures import setup_matplotlib  # noqa: E402
from mapping import MappingParams        # noqa: E402

OLD = REPO / "1_Code" / "Python_for_Generate" / "Py" / "Generate_Data_v2.4_runner.py"
OUT = REPO / "3_Figures" / "_real_check"
T0 = time.time()


def balanced_design(reps: int = 2) -> dict:
    """is_self × is_match × P × (T,W) 完全平衡；W 跟着 T 走，贴近实测的 27% 漏答。"""
    cells = [(s, m, p, t, w)
             for s in (1.0, 0.0) for m in (1.0, 0.0)
             for p in (0.0, 8.0, 32.0, 120.0)
             for t, w in ((0.100, 0.800), (0.150, 1.200), (0.250, 1.800))]
    grid = np.repeat(np.array(cells, float), reps, axis=0)
    return {"P": grid[:, 2], "T": grid[:, 3], "W": grid[:, 4],
            "is_self": grid[:, 0], "is_match": grid[:, 1]}


def sim(base: MappingParams, d: dict, seed: int = 11, n_grid: int = 1500):
    out = TP.simulate_step_subject(d, base, 0.8, np.random.default_rng(seed), n_grid=n_grid)
    rt = np.asarray(out["rt"], float)
    good = ((np.asarray(out["omission"]) == 1) == False) & np.isfinite(rt)
    sm = (np.asarray(d["is_self"]) == 1)[good]
    co = ((np.asarray(out["side"])[good] == 1) == (np.asarray(d["is_match"])[good] == 1))
    d_rt = (np.median(rt[good][sm]) - np.median(rt[good][~sm])) * 1000
    return rt[good], sm, co, float(d_rt), float(co[sm].mean() - co[~sm].mean()), float((~good).mean())


# ---------- 1. 老 v2.4 ----------
spec = importlib.util.spec_from_file_location("oldgen", OLD)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
df, _ = old.generate_dataset_s2(n_subjects=8, trials_per_sub=60, seed=42)
rt_old = df["RT"].to_numpy(float)
ok = np.isfinite(rt_old)
df, rt_old = df[ok], rt_old[ok]
corr_old = df["response"].to_numpy() == 1
self_old = df["label"].to_numpy() == "self"
print(f"[{time.time()-T0:.0f}s] 老 v2.4 就绪：{rt_old.size} 试次")

# ---------- 2. 新模型 TRUTH_LIN ----------
d_main = balanced_design(reps=6)
print(f"[{time.time()-T0:.0f}s] 模拟 TRUTH_LIN（{d_main['P'].size} 试次）…")
rt_new, self_new, corr_new, drt_new, dacc_new, om_new = sim(DG.TRUTH_LIN, d_main)
print(f"[{time.time()-T0:.0f}s] TRUTH_LIN: ΔRT {drt_new:+.0f} ms、Δacc {dacc_new:+.3f}、"
      f"漏答 {om_new:.1%}")

# ---------- 3. 实测 ----------
people, _ = S.collect([REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"], None,
                      DG.TRUTH_LIN)
rt_re, sm_re, co_re = [], [], []
for p in people:
    tr = p["tr"]
    o = np.asarray(tr["omission"]) == 0
    rt_re.append(np.asarray(tr["rt"])[o])
    sm_re.append(np.asarray(tr["is_self"])[o] == 1)
    co_re.append((np.asarray(tr["side"])[o] == 1) == (np.asarray(tr["is_match"])[o] == 1))
rt_re, sm_re, co_re = (np.concatenate(x) for x in (rt_re, sm_re, co_re))

# ---------- 4. 扫描（略：48 试次噪声太大，结论改用解析关系 + 老版/实测对照）----------

# ---------- 5. 图 ----------
rows = [
    ("老 v2.4（单阶段、SPE 写在漂移乘法里）", rt_old, self_old, corr_old, ("self", "stranger")),
    ("新模型 TRUTH_LIN", rt_new, self_new, corr_new, ("self", "other")),
    ("实测 17 人", rt_re, sm_re, co_re, ("self", "other")),
]
plt, lang = setup_matplotlib("zh")
fig, axes = plt.subplots(1, 3, figsize=(15.2, 4.9), sharey=True)
for ax, (title, rt, sm, co, labs) in zip(axes, rows):
    bins = np.linspace(0.15, 2.4, 48)
    for mask, c, lab in ((sm, "#1f77b4", labs[0]), (~sm, "#ff7f0e", labs[1])):
        ax.hist(rt[mask], bins=bins, density=True, alpha=0.5, color=c, label=lab)
    d_rt = (np.median(rt[sm]) - np.median(rt[~sm])) * 1000
    d_acc = co[sm].mean() - co[~sm].mean()
    ax.set_title(f"{title}\nΔRT = {d_rt:+.0f} ms，Δacc = {d_acc:+.3f}（负 ΔRT = 自我更快）",
                 fontsize=10)
    ax.set_xlabel("RT（秒）")
    ax.set_xlim(0.15, 2.4)
    ax.legend(fontsize=8, loc="upper right")
    print(f"{title}: ΔRT {d_rt:+.0f} ms、Δacc {d_acc:+.3f}、n={rt.size}")
axes[0].set_ylabel("密度")
fig.suptitle("三版数据的 self/other 分离度：老版「看得出」是漂移率开到 3.5 倍换来的", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.93))
p = OUT / "fig_spe_old_vs_new.png"
fig.savefig(p, bbox_inches="tight")
print("saved:", p, f"[{time.time()-T0:.0f}s]")
