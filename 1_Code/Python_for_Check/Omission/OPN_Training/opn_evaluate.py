#!/usr/bin/env python3
"""
OPN 评估与可视化模块（Omission Probability Network Evaluation）

功能:
  1. 加载已训练的 OPN 模型
  2. 参数敏感性分析（每个特征对 omission_rate 的边际效应）
  3. 生成训练曲线、残差分布、真实 vs 预测散点图
  4. 对比 HDDM 真实 omission 率与 OPN 预测

参考文献: Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025).
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter
from sklearn.preprocessing import StandardScaler

# 字体设置（支持中文）
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

logger = logging.getLogger(__name__)

# 项目根目录
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR
for _ in range(5):
    if (_PROJECT_ROOT / "1_Code").exists():
        break
    _PROJECT_ROOT = _PROJECT_ROOT.parent

# 路径配置
DATA_DIR = _PROJECT_ROOT / "2_Data" / "Generate_Data" / "OPN_Training"
FIG_DIR = _PROJECT_ROOT / "3_Figures" / "OPN_Training"
FIG_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = ["v (drift rate)", "a (boundary)", "t0 (nondecision time)",
                 "zr (relative starting point)", "deadline (s)"]
FEATURE_LABELS_SHORT = ["v", "a", "t0", "zr", "deadline"]


# ============================================================================
# 核心评估函数
# ============================================================================


def predict_omission_rate(
    opn,
    scaler: StandardScaler,
    params: np.ndarray,
) -> np.ndarray:
    """
    用 OPN 预测 omission 率。

    Parameters
    ----------
    opn : MLPRegressor
    scaler : StandardScaler
    params : np.ndarray, shape (n, 5)
        输入参数 (v, a, t0, zr, deadline)

    Returns
    -------
    np.ndarray
        预测的 omission_rate，clipped to [1e-10, 1-1e-10]
    """
    X_scaled = scaler.transform(params)
    p = opn.predict(X_scaled)
    return np.clip(p, 1e-10, 1 - 1e-10)


def feature_sensitivity_analysis(
    opn,
    scaler: StandardScaler,
    feature_idx: int,
    n_points: int = 100,
    fixed_params: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    分析单个特征对 omission_rate 的边际效应。

    固定其他参数为中位值，仅变化目标特征。

    Parameters
    ----------
    opn : MLPRegressor
    scaler : StandardScaler
    feature_idx : int
        目标特征索引 (0=v, 1=a, 2=t0, 3=zr, 4=deadline)
    n_points : int
        采样点数
    fixed_params : np.ndarray, shape (5,), optional
        固定参数值，默认使用中位值

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (feature_values, predicted_omission_rates)
    """
    if fixed_params is None:
        fixed_params = np.array([1.0, 1.2, 0.3, 0.5, 1.0])  # 典型值

    # 根据特征确定变化范围
    ranges = [
        (-5.0, 5.0),     # v
        (0.2, 3.0),      # a
        (0.1, 0.7),      # t0
        (0.05, 0.95),    # zr
        (0.3, 2.5),      # deadline
    ]
    lo, hi = ranges[feature_idx]
    feature_vals = np.linspace(lo, hi, n_points)

    # 构建输入矩阵
    X_eval = np.tile(fixed_params, (n_points, 1))
    X_eval[:, feature_idx] = feature_vals

    pred = predict_omission_rate(opn, scaler, X_eval)
    return feature_vals, pred


# ============================================================================
# 可视化函数
# ============================================================================


def plot_training_diagnostics(
    X_test: np.ndarray,
    y_test: np.ndarray,
    y_pred: np.ndarray,
    save_path: Optional[Path] = None,
) -> plt.Figure:
    """
    生成 OPN 训练诊断图（3×2 面板）。

    面板内容:
      - 真实 vs 预测散点图
      - 残差直方图
      - 4 个主要特征的边缘效应图

    Parameters
    ----------
    X_test : np.ndarray
    y_test : np.ndarray
    y_pred : np.ndarray
    save_path : Path, optional

    Returns
    -------
    plt.Figure
    """
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    # Panel 1: 真实 vs 预测
    ax = axes[0]
    ax.scatter(y_test, y_pred, alpha=0.3, s=10, c="#4472C4", edgecolors="none")
    lims = [0, 1]
    ax.plot(lims, lims, "k--", alpha=0.5, linewidth=1)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("True Omission Rate")
    ax.set_ylabel("Predicted Omission Rate")
    ax.set_title("True vs Predicted", fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)

    # 添加 R² 注释
    ss_res = np.sum((y_test - y_pred) ** 2)
    ss_tot = np.sum((y_test - y_test.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    ax.text(0.05, 0.95, f"R² = {r2:.3f}", transform=ax.transAxes,
            fontsize=11, verticalalignment="top", fontweight="bold",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    # Panel 2: 残差直方图
    ax = axes[1]
    residuals = y_pred - y_test
    ax.hist(residuals, bins=50, alpha=0.7, edgecolor="black", color="#ED7D31")
    ax.axvline(0, color="red", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Residual (Pred - True)")
    ax.set_ylabel("Count")
    mae = np.mean(np.abs(residuals))
    ax.set_title(f"Residual Distribution (MAE = {mae:.4f})", fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    # Panels 3-7: 各特征的边际效应
    for i in range(4):
        ax = axes[i + 2]
        feat_vals, pred_rates = feature_sensitivity_analysis(
            None, None, i, n_points=80,
            fixed_params=np.array([1.0, 1.2, 0.3, 0.5, 1.0]),
        )
        # 这里 feature_sensitivity_analysis 需要 opn 和 scaler
        # 在调用此函数前由外部注入
        ax.plot(feat_vals, pred_rates, "b-", linewidth=2)
        ax.set_xlabel(FEATURE_NAMES[i], fontsize=9)
        ax.set_ylabel("Predicted Omission Rate")
        ax.set_title(f"Marginal Effect: {FEATURE_NAMES[i]}", fontsize=10, fontweight="bold")
        ax.set_ylim(0, 1)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
        ax.grid(alpha=0.3)

    fig.suptitle("OPN Training Diagnostics", fontsize=14, fontweight="bold")
    plt.tight_layout()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches="tight")
        logger.info(f"诊断图已保存: {save_path}")

    return fig


def plot_full_diagnostics(
    opn,
    scaler: StandardScaler,
    X_test: np.ndarray,
    y_test: np.ndarray,
    save_dir: Path = FIG_DIR,
    prefix: str = "opn",
) -> None:
    """
    生成完整的 OPN 诊断图集。

    Parameters
    ----------
    opn : MLPRegressor
    scaler : StandardScaler
    X_test : np.ndarray  (scaled)
    y_test : np.ndarray
    save_dir : Path
    prefix : str
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    y_pred = opn.predict(X_test)

    # --- Figure 1: 训练诊断 (6面板) ---
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    axes = axes.flatten()

    # 1a: 真实 vs 预测
    ax = axes[0]
    ax.scatter(y_test, y_pred, alpha=0.3, s=12, c="#4472C4", edgecolors="none")
    lims = [-0.02, 1.02]
    ax.plot(lims, lims, "k--", alpha=0.5)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("True Omission Rate", fontsize=9)
    ax.set_ylabel("Predicted Omission Rate", fontsize=9)
    ss_res = np.sum((y_test - y_pred) ** 2)
    ss_tot = np.sum((y_test - y_test.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    ax.set_title(f"True vs Predicted (R²={r2:.3f})", fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)

    # 1b: 残差分布
    ax = axes[1]
    residuals = y_pred - y_test
    ax.hist(residuals, bins=50, alpha=0.7, edgecolor="black", color="#ED7D31")
    ax.axvline(0, color="red", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Residual", fontsize=9)
    ax.set_ylabel("Count", fontsize=9)
    mae = np.mean(np.abs(residuals))
    ax.set_title(f"Residuals (MAE={mae:.4f})", fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    # 1c-1g: 边际效应（5个特征）
    fixed_default = np.array([1.0, 1.2, 0.3, 0.5, 1.0])
    for i in range(4):
        ax = axes[i + 2]
        try:
            feat_vals, pred_rates = feature_sensitivity_analysis(
                opn, scaler, i, n_points=80, fixed_params=fixed_default
            )
            ax.plot(feat_vals, pred_rates, "b-", linewidth=2)
            ax.fill_between(feat_vals, 0, pred_rates, alpha=0.1, color="blue")
            ax.set_xlabel(FEATURE_LABELS_SHORT[i], fontsize=9)
            ax.set_ylabel("Omission Rate", fontsize=9)
            ax.set_title(f"Marginal Effect of {FEATURE_LABELS_SHORT[i]}", fontsize=10,
                         fontweight="bold")
            ax.set_ylim(-0.02, 1.02)
            ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
            ax.grid(alpha=0.3)
        except Exception as e:
            logger.warning(f"边际效应分析 feature {i} 失败: {e}")
            ax.text(0.5, 0.5, "N/A", transform=ax.transAxes, ha="center", va="center")

    fig.suptitle("OPN Model Diagnostics", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(save_dir / f"{prefix}_diagnostics.png", dpi=200, bbox_inches="tight")
    logger.info(f"诊断图 1 已保存: {save_dir / f'{prefix}_diagnostics.png'}")
    plt.close(fig)

    # --- Figure 2: 损失曲线 (如可用) ---
    if hasattr(opn, "loss_curve_"):
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(opn.loss_curve_, color="#4472C4", linewidth=1)
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("Loss")
        ax2.set_title("OPN Training Loss Curve", fontweight="bold")
        ax2.grid(alpha=0.3)
        if hasattr(opn, "validation_scores_"):
            # 验证分数在早停点
            ax2.axvline(opn.n_iter_, color="red", linestyle="--", alpha=0.5,
                        label=f"Best iter: {opn.n_iter_}")
            ax2.legend()
        fig2.tight_layout()
        fig2.savefig(save_dir / f"{prefix}_loss_curve.png", dpi=200, bbox_inches="tight")
        logger.info(f"诊断图 2 (损失曲线) 已保存: {save_dir / f'{prefix}_loss_curve.png'}")
        plt.close(fig2)

    print(f"\n✅ 诊断图已保存到: {save_dir}")
    print(f"   1. {prefix}_diagnostics.png  (6 面板诊断)")
    if hasattr(opn, "loss_curve_"):
        print(f"   2. {prefix}_loss_curve.png   (训练损失曲线)")


# ============================================================================
# 与真实 HDDM omission 率对比
# ============================================================================


def compare_with_real_data(
    opn,
    scaler: StandardScaler,
    real_params: List[Dict],
    save_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    用真实 DDM 参数预测 omission 率，并与观测值对比。

    Parameters
    ----------
    opn : MLPRegressor
    scaler : StandardScaler
    real_params : list[dict]
        每项包含: group_id, v_self_mean, a_mean, t_mean, z_mean, deadline_s,
                  observed_omission_rate, n_omission, n_total
    save_path : Path, optional

    Returns
    -------
    pd.DataFrame
        对比结果表
    """
    X_real = np.array([
        [p["v_self_mean"], p["a_mean"], p["t_mean"], p["z_mean"], p["deadline_s"]]
        for p in real_params
    ])
    predicted = predict_omission_rate(opn, scaler, X_real)

    rows = []
    for i, p in enumerate(real_params):
        rows.append({
            "group_id": p["group_id"],
            "v_self": p["v_self_mean"],
            "a": p["a_mean"],
            "t": p["t_mean"],
            "z": p["z_mean"],
            "deadline_s": p["deadline_s"],
            "observed_rate": p["observed_omission_rate"],
            "predicted_rate": predicted[i],
            "delta": predicted[i] - p["observed_omission_rate"],
        })

    df = pd.DataFrame(rows)
    mae_compare = float(np.mean(np.abs(df["delta"])))
    logger.info(f"真实数据对比 MAE: {mae_compare:.4f} ({mae_compare * 100:.1f} p.p.)")

    if save_path:
        df.to_csv(save_path, index=False)
        logger.info(f"对比结果已保存: {save_path}")

    return df


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("OPN 评估与可视化")
    print("=" * 60)

    # 加载模型
    model_path = DATA_DIR / "opn_model.joblib"
    scaler_path = DATA_DIR / "opn_scaler.joblib"

    if not model_path.exists():
        print(f"❌ 模型文件不存在: {model_path}")
        print("请先运行: python opn_train.py --mode fast")
        sys.exit(1)

    opn = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    print(f"模型已加载: {model_path}")

    # 加载测试数据
    data_path = DATA_DIR / "opn_training_data_fast.npz"
    if data_path.exists():
        data = np.load(data_path)
        X, y = data["X"], data["y"]
        from sklearn.model_selection import train_test_split
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        X_test_s = scaler.transform(X_test)
        plot_full_diagnostics(opn, scaler, X_test_s, y_test, FIG_DIR, "opn")
    else:
        print(f"⚠️ 数据文件不存在: {data_path}，跳过诊断图")

    print("\n✅ 评估完成")
