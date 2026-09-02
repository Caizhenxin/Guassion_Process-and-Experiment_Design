#!/usr/bin/env python3
"""
OPN 模型构建、训练与评估模块（Omission Probability Network Model）

核心功能:
  1. 构建多层感知器 (MLP) 回归器作为 OPN
  2. 训练流程（含早停、正则化）
  3. 模型评估（R², MAE, RMSE）
  4. 模型持久化（保存/加载）

参考文献: Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025).
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ============================================================================
# 特征名称（5 个输入维度）
# ============================================================================

FEATURE_NAMES = ["v (drift rate)", "a (boundary)", "t0 (nondecision time)",
                 "zr (relative starting point)", "deadline"]

# 默认模型超参数
DEFAULT_OPN_PARAMS: Dict[str, Any] = {
    "hidden_layer_sizes": (128, 64, 32),
    "activation": "relu",
    "solver": "adam",
    "alpha": 0.001,               # L2 正则化强度
    "batch_size": 256,
    "learning_rate": "adaptive",
    "learning_rate_init": 0.001,
    "max_iter": 500,
    "early_stopping": True,
    "validation_fraction": 0.1,
    "n_iter_no_change": 20,
    "random_state": 42,
}


# ============================================================================
# 模型构建与训练
# ============================================================================


def build_opn(
    hidden_layer_sizes: Tuple[int, ...] = (128, 64, 32),
    **kwargs: Any,
) -> MLPRegressor:
    """
    构建 OPN（MLP 回归器）。

    Parameters
    ----------
    hidden_layer_sizes : tuple
        隐藏层结构，默认 (128, 64, 32)
    **kwargs
        传递给 MLPRegressor 的额外参数

    Returns
    -------
    MLPRegressor
    """
    params = {**DEFAULT_OPN_PARAMS, "hidden_layer_sizes": hidden_layer_sizes, **kwargs}
    opn = MLPRegressor(**params)
    logger.info(f"OPN 模型已构建: hidden_layers={hidden_layer_sizes}")
    return opn


def train_opn(
    opn: MLPRegressor,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> MLPRegressor:
    """
    训练 OPN 模型。

    Parameters
    ----------
    opn : MLPRegressor
    X_train : np.ndarray
        缩放后的训练特征
    y_train : np.ndarray
        训练标签

    Returns
    -------
    MLPRegressor
        训练后的模型
    """
    logger.info(f"开始训练 OPN: {X_train.shape[0]} samples, "
                f"{X_train.shape[1]} features")
    opn.fit(X_train, y_train)
    logger.info(f"训练完成: {opn.n_iter_} 次迭代, 最终损失 = {opn.loss_:.6f}")
    return opn


# ============================================================================
# 模型评估
# ============================================================================


def evaluate_opn(
    opn: MLPRegressor,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> Dict[str, float]:
    """
    评估 OPN 模型性能。

    Parameters
    ----------
    opn : MLPRegressor
    X_train, y_train : np.ndarray
        训练集
    X_test, y_test : np.ndarray
        测试集

    Returns
    -------
    dict
        评估指标: {train_r2, test_r2, train_mae, test_mae, train_rmse, test_rmse}
    """
    y_train_pred = opn.predict(X_train)
    y_test_pred = opn.predict(X_test)

    train_r2 = opn.score(X_train, y_train)
    test_r2 = opn.score(X_test, y_test)

    train_mae = float(np.mean(np.abs(y_train - y_train_pred)))
    test_mae = float(np.mean(np.abs(y_test - y_test_pred)))

    train_rmse = float(np.sqrt(np.mean((y_train - y_train_pred) ** 2)))
    test_rmse = float(np.sqrt(np.mean((y_test - y_test_pred) ** 2)))

    metrics = {
        "train_r2": train_r2,
        "test_r2": test_r2,
        "train_mae": train_mae,
        "test_mae": test_mae,
        "train_rmse": train_rmse,
        "test_rmse": test_rmse,
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "n_features": int(X_train.shape[1]),
    }

    logger.info(f"评估完成: test R²={test_r2:.4f}, test MAE={test_mae:.4f}, "
                f"test RMSE={test_rmse:.4f}")

    return metrics


def print_evaluation_summary(metrics: Dict[str, float]) -> None:
    """打印格式化的评估摘要。"""
    print("\n" + "=" * 60)
    print("OPN 模型评估摘要")
    print("=" * 60)
    print(f"  训练集 ({metrics['train_samples']} samples):")
    print(f"    R²  = {metrics['train_r2']:.4f}")
    print(f"    MAE = {metrics['train_mae']:.4f} ({metrics['train_mae'] * 100:.1f} p.p.)")
    print(f"    RMSE = {metrics['train_rmse']:.4f}")
    print(f"  测试集 ({metrics['test_samples']} samples):")
    print(f"    R²  = {metrics['test_r2']:.4f}")
    print(f"    MAE = {metrics['test_mae']:.4f} ({metrics['test_mae'] * 100:.1f} p.p.)")
    print(f"    RMSE = {metrics['test_rmse']:.4f}")
    print("=" * 60)


# ============================================================================
# 模型持久化
# ============================================================================


def save_model(
    opn: MLPRegressor,
    scaler: StandardScaler,
    metrics: Dict[str, float],
    model_dir: Path,
    prefix: str = "opn",
) -> None:
    """
    保存 OPN 模型、scaler 和评估指标。

    Parameters
    ----------
    opn : MLPRegressor
    scaler : StandardScaler
    metrics : dict
    model_dir : Path
    prefix : str
    """
    model_dir.mkdir(parents=True, exist_ok=True)

    # 保存模型 (joblib 对 sklearn 模型更高效)
    joblib.dump(opn, model_dir / f"{prefix}_model.joblib")
    joblib.dump(scaler, model_dir / f"{prefix}_scaler.joblib")

    # 保存评估指标
    with open(model_dir / f"{prefix}_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # 同时保存 pickle 格式（兼容性）
    with open(model_dir / f"{prefix}_model.pkl", "wb") as f:
        pickle.dump(opn, f)
    with open(model_dir / f"{prefix}_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    logger.info(f"模型已保存到: {model_dir}")
    logger.info(f"  文件: {prefix}_model.joblib, {prefix}_scaler.joblib, {prefix}_metrics.json")


def load_model(model_dir: Path, prefix: str = "opn") -> Tuple[MLPRegressor, StandardScaler, Dict[str, float]]:
    """
    加载已保存的 OPN 模型。

    Parameters
    ----------
    model_dir : Path
    prefix : str

    Returns
    -------
    tuple[MLPRegressor, StandardScaler, dict]
    """
    opn = joblib.load(model_dir / f"{prefix}_model.joblib")
    scaler = joblib.load(model_dir / f"{prefix}_scaler.joblib")

    metrics_path = model_dir / f"{prefix}_metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    else:
        metrics = {}

    logger.info(f"模型已加载: {model_dir / f'{prefix}_model.joblib'}")
    return opn, scaler, metrics


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("OPN 模型模块测试")
    print("=" * 60)

    # 生成合成数据
    rng = np.random.default_rng(123)
    X_synthetic = rng.uniform(-2, 2, size=(500, 5))
    # 合成 omission_rate: sigmoid-like 响应
    y_synthetic = 1.0 / (1.0 + np.exp(-X_synthetic.sum(axis=1) * 0.5))
    y_synthetic += rng.normal(0, 0.05, size=500)
    y_synthetic = np.clip(y_synthetic, 0, 1)

    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    X_tr, X_te, y_tr, y_te = train_test_split(X_synthetic, y_synthetic, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    # 构建并训练
    opn_model = build_opn(hidden_layer_sizes=(64, 32, 16), max_iter=200)
    opn_model = train_opn(opn_model, X_tr_s, y_tr)

    # 评估
    metrics = evaluate_opn(opn_model, X_tr_s, y_tr, X_te_s, y_te)
    print_evaluation_summary(metrics)

    print("\n✅ 模型模块测试完成")
