# -*- coding: utf-8 -*-
"""GP 层数学性质核验（答辩用）

对"Sigmoid 理论先验 + GP 残差"混合模型中 GP 层的数学性质做直接核验，产出可引用的数值：

  A. 设计几何：6 个条件在归一化 (P,T,W) 空间的秩、条件数、最近邻距离、近重复簇
  B. GP 超参辨识：每个目标学到的 ConstantKernel/RBF/WhiteKernel 超参（含尺度对比）
  C. 样本内插值 vs 外推：训练点/中点/候选点的 GP 后验标准差与先验标准差之比（饱和现象）
  D. 非唯一分解（弱可辨识）：α1 剖面 —— 纯 Sigmoid 的 RMSE 有明确极小，
     而"加 GP 后"的对数边际似然几乎不变
  E. 候选设计点：复现"不确定性排序平台化"，并量化其到最近训练点的距离

用法：
    & $py -u gp_math_audit.py
"""
from __future__ import annotations
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

BASE = Path(__file__).resolve().parents[3]
GP_DIR = BASE / "1_Code" / "Python_HDDM" / "GP+Sigmoid"
sys.path.insert(0, str(GP_DIR))
from gp_sigmoid_hybrid_model import GPSigmoidHybridModel  # noqa: E402

REFIT_DIR = BASE / "2_Data" / "Generate_Data" / "TenRules_Revision_20260912" / "refit"
FROZEN6B = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6b"
OLD_CAND = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Frozen6" / "step6_candidate_design_points.csv"
OUT = BASE / "2_Data" / "Generate_Data" / "TenRules_Revision_20260912" / "gp_audit"
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = ["v_self", "v_stranger", "a", "t", "z"]
GROUPS = [3, 4, 5, 6, 7, 8]


def load_df6() -> pd.DataFrame:
    df = pd.read_csv(REFIT_DIR / "input_conditions_g3g8_refit.csv")
    df["_gid"] = df["source_group_ids"].astype(int)
    df = df[df["_gid"].isin(GROUPS)].sort_values("_gid").reset_index(drop=True)
    df["group_id"] = df["_gid"]
    return df


def load_cp() -> dict:
    p = pd.read_csv(FROZEN6B / "step4_sigmoid_calibrated_params_frozen6b.csv").iloc[0]
    keys = ["alaph1", "alaph2", "beta1", "beta2", "gamma", "base_scale_v", "base_scale_a",
            "t_baseline", "z_baseline"]
    return {k: float(p[k]) for k in keys}


# ----------------------------------------------------------------------
# A. 设计几何
# ----------------------------------------------------------------------
def part_a(df: pd.DataFrame):
    print("\n" + "=" * 78)
    print("A. 设计几何：6 个条件在归一化 (P,T,W) 空间中的信息量")
    print("=" * 78)
    X = GPSigmoidHybridModel.normalize_PTW(df["P"].values, df["T_ms"].values, df["W_ms"].values)
    sv = np.linalg.svd(X - X.mean(0), compute_uv=False)
    A = np.column_stack([np.ones(len(X)), X])
    cond = float(np.linalg.cond(A))
    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(D, np.inf)
    nearest = D.min(1)
    print(f"设计点（原始单位；组号=论文中的 G 编号）:")
    for g, r in df.iterrows():
        print(f"  G{int(r['_gid'])}: P={r['P']:>5.1f}  T={r['T_ms']:>5.1f}  W={r['W_ms']:>6.1f}"
              f"   → 归一化 {np.round(X[g], 3)}")
    print(f"\n各维水平数: P={df['P'].nunique()} 个 {sorted(df['P'].unique())}"
          f" | T={df['T_ms'].nunique()} 个 {sorted(df['T_ms'].unique())}"
          f" | W={df['W_ms'].nunique()} 个 {sorted(df['W_ms'].unique())}")
    print(f"中心化设计矩阵奇异值 = {np.round(sv, 4)}"
          f"   （有效秩≈{int((sv > 0.1 * sv[0]).sum())}，最大/最小 = {sv[0] / sv[-1]:.2f}）")
    print(f"设计矩阵 [1, P, T, W] 条件数 = {cond:.1f}")
    print(f"最近邻距离（归一化单位）: {np.round(nearest, 3)}")
    print(f"  最小最近邻距离 = {nearest.min():.3f}（G4–G7 构成近重复簇）"
          f"，最大最近邻距离 = {nearest.max():.3f}")
    out = pd.DataFrame({
        "group_id": df["_gid"].values, "P": df["P"].values, "T_ms": df["T_ms"].values,
        "W_ms": df["W_ms"].values,
        "P_norm": X[:, 0], "T_norm": X[:, 1], "W_norm": X[:, 2],
        "nearest_neighbour_dist": nearest,
    })
    out.to_csv(OUT / "design_geometry.csv", index=False)
    return X


# ----------------------------------------------------------------------
# B/C. GP 超参 + 后验标准差饱和
# ----------------------------------------------------------------------
def fit_residual_gps(df: pd.DataFrame, cp: dict, seed: int = 42, restarts: int = 10):
    n = len(df)
    X = GPSigmoidHybridModel.normalize_PTW(df["P"].values, df["T_ms"].values, df["W_ms"].values)
    M = df["T_ms"].values + df["W_ms"].values
    sig = {
        "v_self": GPSigmoidHybridModel.sigmoid_v_prediction(df["T_ms"].values, df["P"].values,
                                                            np.ones(n), cp),
        "v_stranger": GPSigmoidHybridModel.sigmoid_v_prediction(df["T_ms"].values, df["P"].values,
                                                                np.zeros(n), cp),
        "a": GPSigmoidHybridModel.sigmoid_a_prediction(M, cp),
        "t": np.full(n, cp["t_baseline"]),
        "z": np.full(n, cp["z_baseline"]),
    }
    real = {"v_self": df["v_self_mean"].values, "v_stranger": df["v_stranger_mean"].values,
            "a": df["a_mean"].values, "t": df["t_mean"].values, "z": df["z_mean"].values}
    gps = {}
    for i, tgt in enumerate(TARGETS):
        y = real[tgt] - sig[tgt]
        gp = GaussianProcessRegressor(
            kernel=ConstantKernel(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1),
            normalize_y=True, n_restarts_optimizer=restarts, random_state=seed + i)
        gp.fit(X, y)
        gps[tgt] = gp
    return X, sig, real, gps


def part_bc(df: pd.DataFrame, cp: dict, X: np.ndarray, gps: dict, sig: dict, real: dict):
    print("\n" + "=" * 78)
    print("B. GP 超参数（normalize_y=True；长度尺度定义在归一化设计坐标上）")
    print("=" * 78)
    rows = []
    for tgt in TARGETS:
        gp = gps[tgt]
        resid = real[tgt] - sig[tgt]
        y_std = np.std(resid)
        k_amp = gp.kernel_.k1.k1          # ConstantKernel
        k_rbf = gp.kernel_.k1.k2          # RBF
        k_noise = gp.kernel_.k2           # WhiteKernel
        prior_std = float(np.sqrt(k_amp.constant_value)) * y_std
        noise_std = float(np.sqrt(k_noise.noise_level)) * y_std
        ls = np.atleast_1d(k_rbf.length_scale)
        ard = ls.size > 1
        # 训练点到最近邻的平均距离（归一化）→ 与长度尺度比较
        D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
        np.fill_diagonal(D, 1e9)
        nn = D.min(1).mean()
        ls_eff = float(ls.mean())
        print(f"\n  [{tgt}] 残差 SD={y_std:.4f}  先验 SD={prior_std:.4f}  噪声 SD={noise_std:.4f}"
              f"  (信噪比 {prior_std / max(noise_std, 1e-12):.2f})")
        print(f"        RBF 长度尺度 = {ls_eff:.6g}"
              f"  （{'ARD 逐维' if ard else '各向同性：三维共用同一长度尺度'}）")
        print(f"        训练点平均最近邻距离 = {nn:.4f}  → 距离/长度尺度 = "
              f"{nn / max(ls_eff, 1e-12):.1f}"
              f"{'   ← ℓ→下界，核退化为δ函数（等同"无平滑结构"）' if ls_eff < 1e-3 else ''}")
        hit_lo = int((ls < 1.2e-5 * 1.01).sum())
        # GP 有效自由度（Wahba）：tr[K(K+σ²I)^-1]，在 normalize_y 的尺度上计算
        K_sig = gp.kernel_.k1(X)                    # ConstantKernel × RBF
        n_ = len(X)
        dof = float(np.trace(K_sig @ np.linalg.inv(K_sig + k_noise.noise_level * np.eye(n_)
                                                   + 1e-10 * np.eye(n_))))
        print(f"        长度尺度触及下界(1e-5)的维数 = {hit_lo}/{ls.size}"
              f"{'   ← 该方向在数据中不可辨识' if hit_lo else ''}")
        print(f"        GP 有效自由度 DoF = tr[K(K+σ²I)⁻¹] = {dof:.2f} / n={n_}"
              f"{'   ← 残差层吃掉全部数据点，参数层无独立信息' if dof > n_ - 1.5 else ''}"
              f"{'   ← 残差层≈0，模型退化为 Sigmoid+噪声' if dof < 1.0 else ''}")
        rows.append({"target": tgt, "resid_sd": y_std, "prior_sd": prior_std, "noise_sd": noise_std,
                     "snr": prior_std / max(noise_std, 1e-12),
                     "length_scale": ls_eff, "ard": ard,
                     "ls_max_over_min": float(ls.max() / ls.min()),
                     "mean_nn_dist": nn, "dist_over_ls": nn / max(ls_eff, 1e-12),
                     "gp_dof": dof, "n": n_,
                     "log_marginal_likelihood": float(gp.log_marginal_likelihood_value_)})
    pd.DataFrame(rows).to_csv(OUT / "gp_hyperparameters.csv", index=False)

    print("\n" + "=" * 78)
    print("C. 后验标准差饱和：样本内插值 vs 区域外推")
    print("=" * 78)
    # 候选点（历史 step6 输出的 top-20）
    cand = pd.read_csv(OLD_CAND).head(20)
    Xc = GPSigmoidHybridModel.normalize_PTW(cand["P"].values, cand["T_ms"].values, cand["W_ms"].values)
    # 训练点与设计盒内中点
    Dc = np.sqrt(((Xc[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    d_near = Dc.min(1)
    mid = X.mean(0, keepdims=True) * 0 + 0.5 * (X.max(0) + X.min(0))
    Xq = np.vstack([X, mid, Xc])
    tag = (["训练点"] * len(X) + ["设计盒中心"] + [f"候选{int(c)}" for c in cand["rank"]])

    def ratio(gp, tgt):
        _, sd = gp.predict(Xq, return_std=True)
        y_std = np.std(real[tgt] - sig[tgt])
        k_amp = gp.kernel_.k1.k1
        prior_std = float(np.sqrt(k_amp.constant_value)) * y_std
        return sd, prior_std

    rec = []
    for tgt in ["v_self", "v_stranger", "a"]:
        sd, prior_std = ratio(gps[tgt], tgt)
        print(f"\n  [{tgt}] 先验 SD = {prior_std:.4f}")
        for j, name in enumerate(tag):
            dd = 0.0 if name == "训练点" else (d_near[j - len(X) - 1] if j > len(X) else
                                               np.sqrt(((Xq[j] - X) ** 2).sum(1)).min())
            print(f"     {name:<10} 到最近训练点距离={dd:6.3f}  后验SD={sd[j]:8.5f}"
                  f"  占先验 {100 * sd[j] / prior_std:6.2f}%")
            rec.append({"target": tgt, "point": name, "dist_to_nearest_train": dd,
                        "posterior_sd": sd[j], "prior_sd": prior_std,
                        "pct_of_prior": 100 * sd[j] / prior_std})
    pd.DataFrame(rec).to_csv(OUT / "gp_std_saturation.csv", index=False)

    print("\n  候选点内部离散度（说明排序平台化）：")
    for tgt in ["v_self", "v_stranger", "a"]:
        sd, prior_std = ratio(gps[tgt], tgt)
        sdc = sd[len(X) + 1:]
        print(f"     {tgt:<11} top-20 候选的 SD 极差 = {sdc.max() - sdc.min():.3e}"
              f"  相对极差 = {100 * (sdc.max() - sdc.min()) / sdc.mean():.4f}%")
    print(f"\n  step6 原始输出 total_uncertainty: 极差 = "
          f"{cand['total_uncertainty'].max() - cand['total_uncertainty'].min():.3e}"
          f"  相对极差 = "
          f"{100 * (cand['total_uncertainty'].max() - cand['total_uncertainty'].min()) / cand['total_uncertainty'].mean():.4f}%")
    print(f"  候选点到最近训练点的最小距离 = {d_near.min():.3f}（归一化单位，"
          f"设计盒半宽=1）→ 全部落在数据支撑区之外")
    return d_near


# ----------------------------------------------------------------------
# D. α1 剖面：非唯一分解
# ----------------------------------------------------------------------
def part_d(df: pd.DataFrame, cp: dict, grid=None):
    print("\n" + "=" * 78)
    print("D. 非唯一分解：α1 的剖面（纯 Sigmoid 可辨识 vs 加 GP 后不可辨识）")
    print("=" * 78)
    if grid is None:
        grid = [0.0, 0.15, 0.3, 0.5, 0.8, 1.2, 1.6, 2.0, 2.5]
    n = len(df)
    M = df["T_ms"].values + df["W_ms"].values
    X = GPSigmoidHybridModel.normalize_PTW(df["P"].values, df["T_ms"].values, df["W_ms"].values)
    y_real = df["v_self_mean"].values
    y_str = df["v_stranger_mean"].values
    y_a = df["a_mean"].values
    rows = []
    for a1 in grid:
        c = dict(cp)
        c["alaph1"] = a1
        v_self_sig = GPSigmoidHybridModel.sigmoid_v_prediction(df["T_ms"].values, df["P"].values,
                                                               np.ones(n), c)
        v_str_sig = GPSigmoidHybridModel.sigmoid_v_prediction(df["T_ms"].values, df["P"].values,
                                                              np.zeros(n), c)
        a_sig = GPSigmoidHybridModel.sigmoid_a_prediction(M, c)
        # 纯 Sigmoid：7 参数的完整目标（另外 6 个参数固定，只变 α1）
        pure_rmse = float(np.sqrt(np.mean(np.r_[v_self_sig - y_real, v_str_sig - y_str,
                                                a_sig - y_a] ** 2)))
        # 加 GP：v_self 残差由 GP 吸收
        resid = y_real - v_self_sig
        gp = GaussianProcessRegressor(
            kernel=ConstantKernel(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1),
            normalize_y=True, n_restarts_optimizer=10, random_state=42)
        gp.fit(X, resid)
        lml = float(gp.log_marginal_likelihood_value_)
        pred_in = gp.predict(X)
        hybrid_rmse = float(np.sqrt(np.mean((v_self_sig + pred_in - y_real) ** 2)))
        rows.append({"alaph1": a1, "pure_sigmoid_rmse_all_targets": pure_rmse,
                     "gp_log_marginal_likelihood_vself": lml,
                     "hybrid_insample_rmse_vself": hybrid_rmse,
                     "gp_noise_sd": float(np.sqrt(gp.kernel_.k2.noise_level)) * np.std(resid),
                     "gp_ls": np.atleast_1d(gp.kernel_.k1.k2.length_scale).mean()})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "alpha1_profile.csv", index=False)
    base = out.loc[out["alaph1"] == 0.15, "gp_log_marginal_likelihood_vself"].iloc[0]
    print(f"{'α1':>6} {'纯Sigmoid RMSE':>16} {'加GP后Δlog证据':>16} {'混合模型样本内RMSE':>20}")
    for _, r in out.iterrows():
        print(f"{r['alaph1']:>6.2f} {r['pure_sigmoid_rmse_all_targets']:>16.4f}"
              f" {r['gp_log_marginal_likelihood_vself'] - base:>16.3f}"
              f" {r['hybrid_insample_rmse_vself']:>20.4f}")
    rng = out["gp_log_marginal_likelihood_vself"]
    pure = out["pure_sigmoid_rmse_all_targets"]
    print(f"\n  纯 Sigmoid 目标函数在 α1 上的变化幅度 = {pure.max() - pure.min():.4f}"
          f"（最小 {pure.min():.4f} @ α1={out.loc[pure.idxmin(), 'alaph1']:.2f}）")
    print(f"  加 GP 后对数证据的变化幅度 = {rng.max() - rng.min():.3f}"
          f"（按 Jeffreys 尺度 <2 即不可区分）")
    return out


def main():
    df = load_df6()
    cp = load_cp()
    print("校准参数（重跑配置 C）: " + json.dumps({k: round(v, 4) for k, v in cp.items()},
                                                 ensure_ascii=False))
    X = part_a(df)
    X2, sig, real, gps = fit_residual_gps(df, cp)
    assert np.allclose(X, X2)
    # 复现校验：与 Frozen6b 的训练指标对照
    pred = {t: sig[t] + gps[t].predict(X) for t in TARGETS}
    chk = pd.read_csv(FROZEN6B / "step4_training_metrics_frozen6b.csv").set_index("target")
    print("\n复现校验（本脚本 vs step4_training_metrics_frozen6b.csv）:")
    for t in TARGETS:
        e = float(np.sqrt(np.mean((pred[t] - real[t]) ** 2)))
        print(f"  {t:<11} 复现 RMSE={e:.6f}   记录 RMSE={chk.loc[t, 'rmse']:.6f}"
              f"   一致={abs(e - chk.loc[t, 'rmse']) < 1e-6}")
    part_bc(df, cp, X, gps, sig, real)
    part_d(df, cp)
    print(f"\n产物目录: {OUT}")


if __name__ == "__main__":
    main()
