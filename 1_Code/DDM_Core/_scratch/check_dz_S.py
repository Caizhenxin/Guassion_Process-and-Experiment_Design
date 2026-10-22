# -*- coding: utf-8 -*-
"""check_dz_S.py —— Δz_S（起点/判据通道）加入后的四道自检
================================================================
1. **逐位回归**：``dz_S = 0`` 时 `mapping.trial_params` 的输出与加入前（git HEAD
   的 ``mapping.py``）**逐位相同**。因为似然是 ``(v, a, z, t0, 设计表)`` 的纯函数，
   输入逐位相同 ⇒ 对数似然逐位相同 ⇒ 既有拟合结果不受影响。
2. **方向**：``dz_S > 0`` ⇒ 自我试次更多走上边界（= 正确答案为 Match 的那一侧）
   ⇒ 更"敢说一样" ⇒ SDT 判据 ``c`` 更负。这是向用户交代过的方向约定，必须验。
3. **边界**：`PARAM_BOUNDS["dz_S"]` 与 ``z_ratio`` 配合保证 ``z/a ∈ [0.05, 0.95]``。
4. **一致性**：两份自由参数名单里的每个名字都有界；``dz_S`` 出现在两份名单里。

运行：``python -X utf8 1_Code/DDM_Core/_scratch/check_dz_S.py``
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
ROOT = CORE.parent.parent
sys.path.insert(0, str(CORE))

import mapping as M  # noqa: E402
from simulate import build_design, simulate_subject  # noqa: E402

FAIL = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def load_head_mapping():
    """把 git HEAD 版本的 mapping.py 取到临时目录并作为独立模块加载。"""
    src = subprocess.run(["git", "show", "HEAD:1_Code/DDM_Core/mapping.py"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    tmp = Path(tempfile.mkdtemp(prefix="dz_old_"))
    f = tmp / "mapping_head.py"
    f.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("mapping_head", f)
    mod = importlib.util.module_from_spec(spec)
    # dataclass + `from __future__ import annotations` 需要模块已登记在 sys.modules
    sys.modules["mapping_head"] = mod
    spec.loader.exec_module(mod)
    return mod, f


# ----------------------------------------------------------------------
print("\n[1] dz_S = 0 时与 git HEAD 逐位一致")
old, old_path = load_head_mapping()
print(f"    旧版 = {old_path}")

design = build_design(30.0, [0.05, 0.10, 0.18, 0.25], [0.80, 1.20, 1.80], n_rep=3)
kw = dict(P_ref=30.0, T_ref=0.10, W_ref=1.20,
          d_ref=0.80, beta_P=0.35, tau_P=30.0, beta_T=0.95, tau_T=0.08,
          beta_S=0.30, beta_SP=0.0, beta_ST=0.12,
          w_model="W1", a_ref=1.52, delta_a=0.30, tau_a=0.70,
          t0=0.19, z_ratio=0.50)
for shape in ("exp", "lin"):
    p_old = old.MappingParams(shape_model=shape, **kw)
    p_new = M.MappingParams(shape_model=shape, **kw)       # dz_S 取默认 0.0
    tp_old, tp_new = old.trial_params(design, p_old), M.trial_params(design, p_new)
    same = all(np.array_equal(np.asarray(tp_old[k]), np.asarray(tp_new[k]))
               for k in ("v", "a", "z", "t0", "d"))
    check(f"shape={shape}: v/a/z/t0/d 逐位相同", same,
          f"|Δz|max={np.max(np.abs(np.asarray(tp_new['z']) - np.asarray(tp_old['z'])))}"
          if not same else f"z 唯一值={np.unique(tp_new['z']).round(6)}")
    check(f"shape={shape}: dz_S 默认值 = 0.0", p_new.dz_S == 0.0)

# ----------------------------------------------------------------------
print("\n[2] 方向：dz_S > 0 ⇒ 自我试次更多走上边界（Match 键）")
# 把**其他**身份通道关掉（beta_S = beta_ST = 0），这样差异只可能来自 dz_S。
p0 = M.MappingParams(shape_model="lin", **{**kw, "beta_S": 0.0, "beta_ST": 0.0})
share_self = {}
for dz in (0.00, 0.15, 0.30):
    p = p0.replace(dz_S=dz)
    shares, rts = {}, {}
    for is_self in (0, 1):
        d_one = build_design(30.0, [0.10], [1.20], n_rep=1500,
                             self_levels=(is_self,), match_levels=(1,))
        out = simulate_subject(d_one, p, np.random.default_rng(20261022))
        ok = out["omission"] == 0
        shares[is_self] = float(np.mean(out["side"][ok] == 1))
        rts[is_self] = float(np.median(out["rt"][ok]))
    share_self[dz] = shares[1]
    print(f"    dz_S={dz:.2f}  P(上界|他人)={shares[0]:.4f}  P(上界|自我)={shares[1]:.4f}"
          f"  中位RT 他人={rts[0]*1000:.0f}ms 自我={rts[1]*1000:.0f}ms")
    if dz == 0.00:
        check("dz_S=0 且关掉其他身份通道 ⇒ 身份不改变上界占比（差 <0.02）",
              abs(shares[1] - shares[0]) < 0.02, f"Δ={shares[1]-shares[0]:+.4f}")
    else:
        check(f"dz_S={dz:.2f} 时自我更偏上界", shares[1] > shares[0],
              f"Δ={shares[1]-shares[0]:+.4f}")
check("越大越偏（P(上界|自我) 随 dz_S 单调上升）",
      share_self[0.00] < share_self[0.15] < share_self[0.30],
      f"{share_self[0.00]:.3f} → {share_self[0.15]:.3f} → {share_self[0.30]:.3f}")

# 打开真实的 beta_S（0.30）后两条通道叠加：身份差异 = 张开(beta_S) + 上移(dz_S)
p1 = M.MappingParams(shape_model="lin", **kw)
for dz in (0.00, 0.15):
    p = p1.replace(dz_S=dz)
    s = {}
    for is_self in (0, 1):
        d_one = build_design(30.0, [0.10], [1.20], n_rep=1500,
                             self_levels=(is_self,), match_levels=(1,))
        out = simulate_subject(d_one, p, np.random.default_rng(20261022))
        ok = out["omission"] == 0
        s[is_self] = float(np.mean(out["side"][ok] == 1))
    print(f"    [含 beta_S] dz_S={dz:.2f}  P(上界|他人)={s[0]:.4f} P(上界|自我)={s[1]:.4f}"
          f"  Δ={s[1]-s[0]:+.4f}")

# z 的实际取值（他人 / 自我）
a = float(M.boundary_a([1.20], p0)[0])
tz = M.trial_params({"P": np.array([30.0]), "T": np.array([0.10]),
                     "W": np.array([1.20]), "is_self": np.array([1.0]),
                     "is_match": np.array([1])}, p0.replace(dz_S=0.30))
check("dz_S=0.30 时 z_self = 0.80·a", abs(float(tz["z"][0]) - 0.80 * a) < 1e-12,
      f"z={float(tz['z'][0]):.6f}, 0.8a={0.8*a:.6f}")

# ----------------------------------------------------------------------
print("\n[3] 边界：z/a 始终严格落在 (0, 1) 内")
lo, hi = M.PARAM_BOUNDS["dz_S"]
zmin, zmax = p0.z_ratio + lo, p0.z_ratio + hi
check("PARAM_BOUNDS['dz_S'] = (-0.45, 0.45)", (lo, hi) == (-0.45, 0.45), f"({lo}, {hi})")
check("z/a 下界 > 0 且上界 < 1", zmin > 0 and zmax < 1, f"z/a ∈ [{zmin:.2f}, {zmax:.2f}]")
for dz in (lo, hi):
    p = p0.replace(dz_S=dz)
    tp = M.trial_params({"P": np.array([30.0, 30.0]), "T": np.array([0.10, 0.10]),
                         "W": np.array([0.80, 1.80]), "is_self": np.array([0.0, 1.0]),
                         "is_match": np.array([1, 0])}, p)
    check(f"dz_S={dz:+.2f} 时 0 < z < a 逐试次成立",
          bool(np.all(tp["z"] > 0) and np.all(tp["z"] < tp["a"])),
          f"z/a={np.round(tp['z']/tp['a'], 3)}")

# ----------------------------------------------------------------------
print("\n[4] 名单与界的一致性")
check("dz_S ∈ WITHIN_FREE", "dz_S" in M.WITHIN_FREE)
check("dz_S ∈ WITHIN_FREE_LIN", "dz_S" in M.WITHIN_FREE_LIN)
check("dz_S ∉ BETWEEN_FREE（被试内对比，不是被试间）", "dz_S" not in M.BETWEEN_FREE)
missing = [n for n in M.WITHIN_FREE + M.WITHIN_FREE_LIN + M.BETWEEN_FREE
           if n not in M.PARAM_BOUNDS]
check("所有自由参数都有界", not missing, f"缺界：{missing}" if missing else "")
print(f"    WITHIN_FREE     = {len(M.WITHIN_FREE)} 个：{M.WITHIN_FREE}")
print(f"    WITHIN_FREE_LIN = {len(M.WITHIN_FREE_LIN)} 个：{M.WITHIN_FREE_LIN}")
r = M.MappingParams().replace(**{n: 0.1 for n in M.WITHIN_FREE_LIN})
check("replace/vector/with_vector 能承载 dz_S",
      np.allclose(r.vector(M.WITHIN_FREE_LIN),
                  M.MappingParams().with_vector(M.WITHIN_FREE_LIN,
                                                r.vector(M.WITHIN_FREE_LIN))
                  .vector(M.WITHIN_FREE_LIN)))

# ----------------------------------------------------------------------
print("\n" + "=" * 74)
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
