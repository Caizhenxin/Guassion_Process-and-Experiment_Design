# -*- coding: utf-8 -*-
"""老生成器 v2.4 的 SPE 有多大、新模型要多大 beta_S 才「看得出来」。

回答用户：
  「为啥现在的版本没办法让效应量大一些？以前和现在哪个更好？」
做法：
  A. 直接跑老的 `Generate_Data_v2.4_runner.generate_dataset_s2`，量 self/stranger 的
     RT 中位、正确率、Δ（老代码里 SPE 是漂移率的乘法因子 2.5 vs 0.6）。
  B. 在**同一套实验设计**（T=100 ms ⇒ beta_ST 项为 0，只留漂移通道）下扫 beta_S，
     量 ΔRT 中位与 Δacc，找出「要多大才看得出」和「多大就开始失真」。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core")]

import twophase as TP          # noqa: E402
from mapping import MappingParams  # noqa: E402

OLD = REPO / "1_Code" / "Python_for_Generate" / "Py" / "Generate_Data_v2.4_runner.py"


# ---------------- A. 老生成器 ----------------
def old_side(n_subj: int = 8, trials: int = 60, seed: int = 42):
    spec = importlib.util.spec_from_file_location("oldgen", OLD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # 只定义函数，__main__ 段不会跑
    df, _ = mod.generate_dataset_s2(n_subjects=n_subj, trials_per_sub=trials, seed=seed)
    rt = df["RT"].to_numpy(float)
    ok = ~np.isnan(rt)
    df = df[ok]
    rt = rt[ok]
    # response 1 = 上边界（老代码里上边界=「自我/匹配」判定），2 = 下边界
    corr = df["response"].to_numpy() == 1
    self_ = df["label"].to_numpy() == "self"
    print("\n=== A. 老生成器 v2.4（SPE = 漂移率 ×2.5 vs ×0.6）===")
    print(f"  试次 {len(df)}、被试 {n_subj}")
    print(f"  漂移 v：self {df['v'][self_].mean():.2f} vs stranger {df['v'][~self_].mean():.2f}"
          f"（比值 {df['v'][self_].mean() / df['v'][~self_].mean():.2f}×）")
    print(f"  边界 a：self {df['a'][self_].mean():.2f} vs stranger {df['a'][~self_].mean():.2f}")
    print(f"  RT 中位：self {np.median(rt[self_]) * 1000:.0f} ms vs stranger "
          f"{np.median(rt[~self_]) * 1000:.0f} ms ⇒ Δ = "
          f"{(np.median(rt[self_]) - np.median(rt[~self_])) * 1000:+.0f} ms")
    print(f"  正确率：self {corr[self_].mean():.3f} vs stranger {corr[~self_].mean():.3f}"
          f" ⇒ Δacc = {corr[self_].mean() - corr[~self_].mean():+.3f}")
    # 老 CSV 的 SPEm 定义：self - stranger 的被试均值
    per = df.groupby(["subject", "label"])["RT"].mean().unstack()
    spe = (per["self"] - per["stranger"]) * 1000
    print(f"  逐被试 SPE_ms（self−stranger 均值）：{spe.mean():.0f} ± {spe.std(ddof=1):.0f}"
          f"（范围 {spe.min():.0f}…{spe.max():.0f}）")


# ---------------- B. 新模型：扫 beta_S ----------------
def new_design(n_trial: int = 576, seed: int = 11):
    rng = np.random.default_rng(seed)
    P = np.tile(np.array([0.0, 8.0, 32.0, 120.0]), n_trial // 4)
    return {"P": P,
            "T": np.full(n_trial, 0.100),      # ⇒ dqt = 0，beta_ST 不起作用
            "W": np.full(n_trial, 0.800),
            "is_self": rng.integers(0, 2, n_trial).astype(float),
            "is_match": rng.integers(0, 2, n_trial).astype(float)}


def run_one(base: MappingParams, design: dict, seeds=(11, 23)):
    d_rt, d_acc, om, med = [], [], [], []
    for s in seeds:
        rng = np.random.default_rng(s)
        out = TP.simulate_step_subject(design, base, 0.8, rng)
        rt = np.asarray(out["rt"], float)          # 长度 n，漏答为 NaN
        o = np.asarray(out["omission"]) == 1
        side = np.asarray(out["side"])
        match = np.asarray(design["is_match"])
        good = ~o & np.isfinite(rt)
        correct = (side[good] == 1) == (match[good] == 1)
        sm_all = np.asarray(design["is_self"]) == 1     # 全长度掩码
        sm = sm_all[good]                               # 已对齐 good
        d_rt.append((np.median(rt[good & sm_all]) - np.median(rt[good & ~sm_all])) * 1000)
        d_acc.append(correct[sm].mean() - correct[~sm].mean())
        om.append(o.mean())
        med.append(np.median(rt[good]) * 1000)
    return (float(np.mean(d_rt)), float(np.mean(d_acc)), float(np.mean(om)), float(np.mean(med)))


def new_side():
    design = new_design()
    print("\n=== B. 新模型：T=100 ms 下扫 beta_S（其余为 TRUTH_LIN）===")
    print("  beta_S   ΔRT中位(ms)   Δacc     漏答率   RT中位(ms)")
    for b in (0.0, 0.15, 0.30, 0.45, 0.60, 0.90, 1.30):
        p = MappingParams(shape_model="lin", beta_S=float(b))
        d_rt, d_acc, om, med = run_one(p, design)
        print(f"  {b:5.2f}   {d_rt:+9.0f}   {d_acc:+.3f}   {om:6.1%}   {med:8.0f}")
    print("\n  === B2. 只动起点通道 dz_S（beta_S=0）===")
    print("  dz_S     ΔRT中位(ms)   Δacc     漏答率   RT中位(ms)")
    for z in (0.0, 0.05, 0.10, 0.20):
        p = MappingParams(shape_model="lin", beta_S=0.0, dz_S=float(z))
        d_rt, d_acc, om, med = run_one(p, design)
        print(f"  {z:5.2f}   {d_rt:+9.0f}   {d_acc:+.3f}   {om:6.1%}   {med:8.0f}")


if __name__ == "__main__":
    old_side()
    new_side()
    print("\n对照：实测 17 人 ΔRT 中位 = −33 ms、Δacc = +0.067、漏答 27%、RT 中位 692 ms")
