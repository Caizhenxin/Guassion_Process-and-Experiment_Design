"""在**推荐的 t0 上界**处，量出"实际被用到的那条密度"离 `flux` 的抵消地板有多远。

动机：`flux` 的特征函数级数项幅 O(k)、真值指数级小，真值落到 ~kmax·eps 以下时
符号是噪声，而 `per_trial_loglik` 的 `np.any(f <= 0)` 会把**整份**数据判成 None。
`t0` 的安全余量必须由这个地板**实测**决定，不能凭感觉写。
"""
import pathlib
import subprocess
import sys

# 控制台常是 GBK：中文/数学符号输出必须先改成 UTF-8，否则 UnicodeEncodeError。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "Experiment"))

import numpy as np

import likelihood as L
import read_formal_data as R
import wfpt

OUT = HERE / "_fake_v41"
path = OUT / "exp_group1_subject1.txt"
if not path.exists():
    subprocess.run([sys.executable, str(HERE / "make_fake_pilot.py"), str(OUT),
                    "--n-subjects", "4", "--group", "1", "--seed", "7"],
                   check=True, encoding="utf-8", errors="replace")

rec, _ = R.load_file(path)
tr = R.to_trials(rec)
tr_fit, rep = R.fit_ready(tr)
print(R.format_fit_ready(rep))

eps = float(np.finfo(float).eps)
tb = R.t0_bounds(tr_fit)
hi = float(tb["t0"][1])
print(f"\n推荐 t0 上界 = {hi:.4f}（margin = {R.T0_SAFE_MARGIN}），"
      f"库内上界 {L.MappingParams(shape_model='lin').__class__} 的 t0 默认 = "
      f"{L.MappingParams(shape_model='lin').t0}")

p = L.MappingParams(shape_model="lin", t0=hi)
ll = L.per_trial_loglik(p, tr_fit)
resp = ~tr_fit["omission"].astype(bool)
f = np.exp(np.asarray(ll, dtype=float))
print(f"per_trial_loglik 返回有限 = {ll is not None}")
print(f"已响应试次 {int(resp.sum())} 条；被用到的密度 f：")
print(f"  min = {f[resp].min():.3e}   median = {np.median(f[resp]):.3e}   "
      f"max = {f[resp].max():.3e}")

t = tr_fit["rt"][resp] - hi
order = np.argsort(t)
print("\n最小的 6 个 t（= rt − t0 上界）与其密度：")
for j in order[:6]:
    print(f"  t = {t[j]:.5f} s   f = {f[resp][j]:.3e}")

print("\n各级 kmax 对应的抵消地板 ~ kmax·eps：")
for kmax in (10, 20, 50, 100, 200, 500):
    print(f"  kmax = {kmax:3d} ⇒ {kmax * eps:.2e}")

# 真实调用的 kmax
amax = 2.0
kmax_real = wfpt._k_max(float(np.min(t)), amax, wfpt._TOL)
print(f"\nwfpt._k_max(t_min={np.min(t):.5f}, a={amax}, tol={wfpt._TOL}) = {kmax_real}"
      f" ⇒ 地板 ~ {kmax_real * eps:.2e}")
print(f"实测最小密度 / 地板 = {f[resp].min() / (kmax_real * eps):.2e}")

# 对照：库内上界会怎样
for label, t0v in (("推荐上界", hi), ("min(RT)", float(np.nanmin(tr_fit['rt'][resp]))),
                   ("min(RT)−0.005", float(np.nanmin(tr_fit['rt'][resp])) - 0.005)):
    p2 = L.MappingParams(shape_model="lin", t0=t0v)
    ll2 = L.per_trial_loglik(p2, tr_fit)
    if ll2 is None:
        print(f"  对照 {label:16s} t0={t0v:.4f} ⇒ None（整份数据判死）")
    else:
        f2 = np.exp(np.asarray(ll2, float))[resp]
        print(f"  对照 {label:16s} t0={t0v:.4f} ⇒ 有限，最小 f = {f2.min():.3e}")
