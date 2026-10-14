# -*- coding: utf-8 -*-
"""check_rho_power.py —— Stage 5 / Q1：D4 设计能否区分 M-T1（阶跃）与 M-T3（恒定）？

**为什么这是 Stage 5 的核心问题**
Stage 3 的全部恢复率、Stage 4 的全部设计比较，都用的是**单阶段** WFPT
（漂移 = ``d(T)`` 恒定，T 只作可用性上界）——那正是 **M-T3**。
若真实生成过程是 M-T1（掩蔽后漂移降为 ``ρ·d(T)``），这些数值就全是**设定错误**。

★ **结构性事实**：M-T3 是 M-T1 在 ``ρ = 1`` 处的**严格嵌套特例**
（`wfpt` 的 W1 与 `check_twophase_lik.py` 的 A 段已验到 2e-6 相对差）。
因此 Q1 不必新建模型比较框架，只需问：**``ρ`` 在这份设计里可估吗？**

判据（每个 ``ρ_true`` 档，``N_SUBJ`` 名被试，D4 = 576 试次/人）：
  * ``ρ̂`` 的均值与跨被试 SD；
  * 似然比 ``LRT = 2(ℓ₁ − ℓ₃)`` 的均值，与拒绝 M-T3 的比例（``LRT > 3.841``）；
  * ``ΔBIC = BIC₃ − BIC₁``（> 0 偏向 M-T1；``k`` 用 7 vs 8，``n`` = 576）；
  * ``ρ_true = 1.0`` 那一行是**假阳性率**的标定行，必须接近名义水平。

生成用 Euler（`twophase.simulate_euler_subject`，dt=5e-5，已标定）；
两套拟合都从**同一初值**出发，唯一差别是 M-T1 多一个自由参数 ``ρ``。

用法：``python _scratch/check_rho_power.py [N_SUBJ] [输出路径]``
      输出路径相对 ``_scratch/``（或给绝对路径）。给了就**由脚本自己以 UTF-8 写日志**
      （推荐，避免 PowerShell `>` 产生 UTF-16LE 的日志）。
"""
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


class _Tee:
    """可选：把 stdout 同时写进 UTF-8 文件，绕开 PowerShell `>` 的编码陷阱。

    ⚠️ 实测教训：`check_rho_power_n10_u8.txt` 是 **UTF-16LE（BOM FF FE）**——
    用 PowerShell 重定向产生的日志并不总是 UTF-8，下游解析会
    `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0`。
    规范：**日志一律由脚本自己以 UTF-8 写**。
    """

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


if len(sys.argv) > 2:
    _out = Path(sys.argv[2])
    if not _out.is_absolute():
        _out = _HERE.parent / _out
    _out.parent.mkdir(parents=True, exist_ok=True)
    _fh = open(_out, "w", encoding="utf-8", newline="\n")
    sys.stdout = _Tee(sys.stdout, _fh)

from likelihood import fit_mle, trials_from_arrays
from mapping import (PARAM_BOUNDS, MappingParams, WITHIN_FREE_LIN,
                     match_lin_to_exp)
from simulate import build_design, design_arrays
from twophase import bic, fit_mle_step, simulate_euler_subject

T0_EPS = 0.005
CHI2_1_95 = 3.841458820694124

T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]
W_LEVELS = [0.79998, 1.19990, 1.79990]
N_REP = 12
DESIGN = build_design(120.0, T_LEVELS, W_LEVELS, N_REP)
N_OBS = int(DESIGN["T"].size)
ARRAYS = design_arrays(DESIGN)

TRUTH_EXP = MappingParams(
    P_ref=120.0, T_ref=0.10, W_ref=1.20, d_ref=0.70, beta_P=1.50, tau_P=30.0,
    beta_T=0.55, tau_T=0.080, beta_S=0.16, beta_SP=0.0, beta_ST=0.10,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70, t0=0.22,
    z_ratio=0.50, shape_model="exp")
TRUTH_LIN, _ = match_lin_to_exp(TRUTH_EXP, T_LEVELS, W_LEVELS)
INIT_LIN, _ = match_lin_to_exp(
    MappingParams(P_ref=120.0, T_ref=0.10, W_ref=1.20, d_ref=0.50,
                  beta_P=1.50, tau_P=30.0, beta_T=0.90, tau_T=0.150,
                  beta_S=0.30, beta_SP=0.0, beta_ST=0.00, w_model="W1",
                  a_ref=1.60, delta_a=0.10, tau_a=0.50, t0=0.25,
                  z_ratio=0.50, shape_model="exp"),
    T_LEVELS, W_LEVELS)

NAMES = list(WITHIN_FREE_LIN)
RHO_TRUE_LIST = [0.0, 0.50, 0.75, 1.00, 1.25, 1.50]
N_SUBJ = int(sys.argv[1]) if len(sys.argv) > 1 else 3
DT_GEN = 5e-5

print("=" * 100)
print("Stage 5 / Q1：M-T1（阶跃，ρ 自由）vs M-T3（恒定，ρ ≡ 1）——D4 设计下的 ρ 可识别性")
print("=" * 100)
print(f"设计 D4 = {N_OBS} 试次/人（{len(T_LEVELS)}T × {len(W_LEVELS)}W × 2 self × 2 match × {N_REP}）")
print("lin 真值：" + "  ".join(f"{k}={getattr(TRUTH_LIN, k):.4f}"
                               for k in NAMES))
print(f"生成器：Euler dt={DT_GEN:g}（偏差 |Δacc|≈0.0022，见 _scratch/check_euler_dt_u8.txt）")
print(f"每档 {N_SUBJ} 名被试；LRT 阈值 χ²(1,0.95) = {CHI2_1_95:.3f}")
print()

rows = []
for rho_true in RHO_TRUE_LIST:
    print("-" * 100)
    print(f"ρ_true = {rho_true:.2f}")
    print(f"  {'subj':>5}{'omit':>8}{'acc':>8}{'RTms':>8}"
          f"{'ll_M3':>11}{'ll_M1':>11}{'rho_hat':>9}{'LRT':>9}{'dBIC':>9}"
          f"{'sec':>7}")
    for s in range(N_SUBJ):
        t_start = time.perf_counter()
        rng = np.random.default_rng(9100 + s * 17 + int(rho_true * 100) * 1009)
        sim = simulate_euler_subject(DESIGN, TRUTH_LIN, rho_true, rng,
                                     dt=DT_GEN)
        tr = trials_from_arrays(sim["rt"], sim["side"], sim["omission"], *ARRAYS)
        kept = sim["omission"] == 0
        m = kept & (DESIGN["is_match"] == 1)
        acc = float(np.mean(sim["side"][m] == 1))
        rt_ms = float(np.mean(sim["rt"][kept])) * 1000
        ov = {"t0": (PARAM_BOUNDS["t0"][0],
                     min(PARAM_BOUNDS["t0"][1],
                         max(float(np.nanmin(sim["rt"])) - T0_EPS, 0.06)))}

        f3 = fit_mle(tr, NAMES, INIT_LIN, n_restart=2, seed=1000 + s,
                     maxiter=250, maxfun=6000, bounds_override=ov,
                     gtol=1e-8, ftol=1e-12)
        f1 = fit_mle_step(tr, NAMES, f3["params"], rho_init=1.0, n_restart=1,
                          seed=2000 + s, maxiter=250, maxfun=4000,
                          bounds_override=ov, gtol=1e-7, ftol=1e-11, n_x=81)
        lrt = 2.0 * (f1["loglik"] - f3["loglik"])
        dbic = bic(f3["loglik"], 7, N_OBS) - bic(f1["loglik"], 8, N_OBS)
        el = time.perf_counter() - t_start
        rows.append(dict(rho_true=rho_true, subj=s, rho_hat=f1["rho"],
                         lrt=lrt, dbic=dbic, ll3=f3["loglik"], ll1=f1["loglik"],
                         acc=acc, omit=float(np.mean(sim["omission"]))))
        print(f"  {s:>5}{np.mean(sim['omission']):>8.3f}{acc:>8.3f}{rt_ms:>8.1f}"
              f"{f3['loglik']:>11.3f}{f1['loglik']:>11.3f}{f1['rho']:>9.4f}"
              f"{lrt:>9.3f}{dbic:>9.3f}{el:>7.1f}")

print()
print("=" * 100)
print("汇总")
print("=" * 100)
print(f"{'ρ_true':>8}{'ρ̂ 均值':>10}{'ρ̂ SD':>9}{'LRT 均值':>11}{'拒绝 M-T3':>11}"
      f"{'ΔBIC 均值':>11}{'准确率':>9}{'遗漏':>8}")
for rho_true in RHO_TRUE_LIST:
    r = [x for x in rows if x["rho_true"] == rho_true]
    rh = np.array([x["rho_hat"] for x in r])
    lrt = np.array([x["lrt"] for x in r])
    db = np.array([x["dbic"] for x in r])
    rej = float(np.mean(lrt > CHI2_1_95))
    print(f"{rho_true:>8.2f}{rh.mean():>10.4f}{rh.std(ddof=1) if rh.size > 1 else 0.0:>9.4f}"
          f"{lrt.mean():>11.3f}{rej:>11.1%}{db.mean():>11.3f}"
          f"{np.mean([x['acc'] for x in r]):>9.3f}"
          f"{np.mean([x['omit'] for x in r]):>8.3f}")

print()
print("读法：")
print("  * ρ_true = 1.00 一行是**假阳性**标定：LRT 应大体低于阈值、ρ̂ 应围绕 1.00。")
print("  * 若 ρ_true = 1.00 也被系统性拒绝，说明 Euler 生成器与解析似然不匹配")
print("    （生成器偏差被当成模型偏离），该轮数字不可用。")
print("  * 拒绝率对 |ρ_true − 1| 的曲线就是本设计对「掩蔽是否打断积累」的检验力。")
