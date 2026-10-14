# -*- coding: utf-8 -*-
"""校验 mapping.match_lin_to_exp：exp 真值 → 设计层行为匹配的 lin 真值。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from mapping import MappingParams, match_lin_to_exp, WITHIN_FREE_LIN  # noqa: E402

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]

TRUTH_EXP = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, shape_model="exp",
    d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080,
    beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)

lin, rep = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)

print("=" * 92)
print("match_lin_to_exp 校验：exp 真值 → lin 真值（设计层行为最小二乘匹配）")
print("=" * 92)
print("\n换算出的 lin 真值（自由参数 %d 个）：" % len(WITHIN_FREE_LIN))
for n in WITHIN_FREE_LIN:
    print(f"  {n:>10s} = {getattr(lin, n):10.4f}")
print(f"  {'shape_model':>10s} = {lin.shape_model}")
for n in ("tau_T", "tau_a"):
    print(f"  {n:>10s} = {getattr(lin, n):10.4f}   （lin 下被忽略）")

print("\n--- T 通路（非自我漂移 d）---")
print(f"{'T(ms)':>8s} {'d_exp':>9s} {'d_lin':>9s} {'残差':>9s}")
for i, T in enumerate(rep["T_levels"]):
    print(f"{T*1000:8.2f} {rep['d_exp'][i]:9.4f} {rep['d_lin'][i]:9.4f} "
          f"{rep['d_resid'][i]:+9.4f}")
print(f"  跨度：exp {rep['d_span_exp']:.4f} vs lin {rep['d_span_lin']:.4f} "
      f"→ 恢复 {100*rep['d_span_lin']/rep['d_span_exp']:.1f}%")
print(f"  max|残差| = {np.abs(rep['d_resid']).max():.4f}")

print("\n--- W 通路（边界 a）---")
print(f"{'W(ms)':>8s} {'a_exp':>9s} {'a_lin':>9s} {'残差':>9s}")
for i, W in enumerate(rep["W_levels"]):
    print(f"{W*1000:8.2f} {rep['a_exp'][i]:9.4f} {rep['a_lin'][i]:9.4f} "
          f"{rep['a_resid'][i]:+9.4f}")
print(f"  跨度：exp {rep['a_span_exp']:.4f} vs lin {rep['a_span_lin']:.4f} "
      f"→ 恢复 {100*rep['a_span_lin']/rep['a_span_exp']:.1f}%")
print(f"  max|残差| = {np.abs(rep['a_resid']).max():.4f}")

# ---------------- 与旧的手写 TRUTH_LIN 对比 ----------------
OLD = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, shape_model="lin",
    d_ref=0.70, beta_P=0.35, tau_P=30.0,
    beta_T=1.279, tau_T=0.080,
    beta_S=0.16, beta_SP=0.0, beta_ST=0.233,
    w_model="W1", a_ref=2.00, delta_a=0.226, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)
xT = np.asarray(T_LEVELS) - 0.10
xW = np.asarray(W_LEVELS) - 1.20
d_old = OLD.d_ref + OLD.beta_T * xT
a_old = OLD.a_ref + OLD.delta_a * xW

print("\n" + "=" * 92)
print("对照：design_grid.py 旧手写 TRUTH_LIN（beta_T=1.279, delta_a=0.226）")
print("=" * 92)
print(f"  d 跨度：exp {rep['d_span_exp']:.4f} vs 旧 lin {np.ptp(d_old):.4f} "
      f"→ {100*np.ptp(d_old)/rep['d_span_exp']:.1f}%   新 lin {rep['d_span_lin']:.4f} "
      f"→ {100*rep['d_span_lin']/rep['d_span_exp']:.1f}%")
print(f"  a 跨度：exp {rep['a_span_exp']:.4f} vs 旧 lin {np.ptp(a_old):.4f} "
      f"→ {100*np.ptp(a_old)/rep['a_span_exp']:.1f}%   新 lin {rep['a_span_lin']:.4f} "
      f"→ {100*rep['a_span_lin']/rep['a_span_exp']:.1f}%")
print(f"  旧 d 最大残差 {np.abs(d_old - rep['d_exp']).max():.4f}；"
      f"新 d 最大残差 {np.abs(rep['d_resid']).max():.4f}")
print(f"  旧 a 最大残差 {np.abs(a_old - rep['a_exp']).max():.4f}；"
      f"新 a 最大残差 {np.abs(rep['a_resid']).max():.4f}")
print("\n  旧值问题：T 斜率乘了 exp 幅度 0.55，W 斜率却用了未乘的原始比值 →")
print(f"  边界效应被夸大 {((OLD.delta_a*0.99992)/rep['a_span_exp']):.2f} 倍"
      f"（旧 a 跨度 {np.ptp(a_old):.4f} vs exp {rep['a_span_exp']:.4f}）。")

# ---------------- 自检 ----------------
print("\n" + "=" * 92)
print("自检")
print("=" * 92)
ok = True
if lin.shape_model == "lin":
    print("  ✓ shape_model 已切换为 lin")
else:
    ok = False
    print("  ✗ shape_model 未切换")
if lin.beta_T > 0 and lin.delta_a > 0:
    print("  ✓ 斜率符号与 exp 效应方向一致（drift 随 T 升、边界随 W 升）")
else:
    ok = False
    print("  ✗ 斜率符号异常")
if abs(lin.d_ref - (TRUTH_EXP.d_ref)) < 0.20:
    print(f"  ✓ d_ref 仅微调 {lin.d_ref - TRUTH_EXP.d_ref:+.4f}（行为匹配不改变量级）")
else:
    ok = False
    print("  ✗ d_ref 偏移过大")
# 参考点处两模型必须一致
if abs((lin.d_ref + lin.beta_T * 0.0) - (TRUTH_EXP.d_ref + TRUTH_EXP.beta_T * 0.0)) < 0.20:
    print("  ✓ 参考点 T_ref 处 d 一致（由 c_T 吸收，差异 < 0.20）")
try:
    match_lin_to_exp(lin, T_LEVELS, W_LEVELS)
    ok = False
    print("  ✗ 未对非 exp 真值报错")
except ValueError as e:
    print(f"  ✓ 非 exp 真值正确报错：{e}")
print("\n结果：" + ("全部通过" if ok else "存在失败"))
