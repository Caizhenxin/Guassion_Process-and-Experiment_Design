#!/usr/bin/env python3
"""
OPN 数据生成与预处理模块（Omission Probability Network Data Module）

功能:
  1. 从 DDM 参数 prior 采样生成训练数据
  2. 数据加载、标准化、划分训练/测试集
  3. 数据保存与加载

参考文献: Leng et al. (2025), The Perils of Omitting Omissions
          Tran et al. (2021), Systematic Parameter Reviews in Cognitive Modeling
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from opn_simulator import SIMULATOR

logger = logging.getLogger(__name__)

# ============================================================================
# 默认参数先验范围（基于 Tran et al., 2021 的经验分布和本项目的参数范围）
# 单位：秒
# ============================================================================

DEFAULT_PRIOR_RANGES: Dict[str, Tuple[float, float]] = {
    "v": (-5.0, 5.0),           # 漂移率，覆盖本项目的 -4.86 ~ +2.81
    "a": (0.2, 3.0),             # 边界分离，文献 E-LB=0.11, E-UB=7.47
    "t": (0.1, 0.7),             # 非决策时间，文献 0~3.69
    "z": (0.0, 1.0),            # 相对起始点 zr ∈ (0,1)
    "deadline": (0.3, 2.5),     # deadline（秒），覆盖本项目 330ms-2000ms
}

# 默认训练配置
DEFAULT_N_TRAIN_SAMPLES = 50000     # 完整训练：5 万组参数
DEFAULT_N_SIM_PER_SAMPLE = 5000    # 每组参数仿真 5000 次
DEFAULT_N_TRAIN_SAMPLES_FAST = 5000  # 快速测试：5 千组


# ============================================================================
# 训练数据生成
# ============================================================================


def generate_opn_training_data(
    n_samples: int = DEFAULT_N_TRAIN_SAMPLES,
    n_sim: int = DEFAULT_N_SIM_PER_SAMPLE,
    prior_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成 OPN 训练数据：从参数 prior 采样，运行批量 DDM 仿真，统计 omission 率。

    Parameters
    ----------
    n_samples : int
        采样参数组数
    n_sim : int
        每组参数仿真试次数
    prior_ranges : dict, optional
        参数先验范围字典，默认为 DEFAULT_PRIOR_RANGES
    seed : int
        随机种子

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        X: shape (n_samples, 5)，特征 (v, a, t, zr, deadline)
        y: shape (n_samples,)，标签 omission_rate ∈ [0, 1]
    """
    if prior_ranges is None:
        prior_ranges = DEFAULT_PRIOR_RANGES

    rng = np.random.default_rng(seed)

    X = np.zeros((n_samples, 5))
    y = np.zeros(n_samples)

    t_start = time.perf_counter()
    valid_count = 0

    logger.info(f"开始生成 OPN 训练数据: {n_samples} 组参数 × {n_sim} 次仿真/组")

    for i in range(n_samples):
        # 从 prior 均匀采样
        v_val = rng.uniform(*prior_ranges["v"])
        a_val = rng.uniform(*prior_ranges["a"])
        t0_val = rng.uniform(*prior_ranges["t"])
        zr_val = rng.uniform(*prior_ranges["z"])
        z_val = zr_val * a_val
        d_val = rng.uniform(*prior_ranges["deadline"])

        # 跳过不合逻辑的组合
        if d_val <= t0_val:
            continue

        # 批量仿真
        try:
            n_om = SIMULATOR(v=v_val, a=a_val, z=z_val, t0=t0_val, deadline_s=d_val, n_trials=n_sim)
        except Exception as e:
            logger.warning(f"Simulation failed for params (v={v_val:.2f}, a={a_val:.2f}, "
                           f"t0={t0_val:.2f}, zr={zr_val:.2f}, d={d_val:.2f}): {e}")
            continue

        X[valid_count] = [v_val, a_val, t0_val, zr_val, d_val]
        y[valid_count] = n_om / n_sim
        valid_count += 1

        # 进度报告 (每 5%)
        report_interval = max(1, n_samples // 20)
        if (i + 1) % report_interval == 0:
            elapsed = time.perf_counter() - t_start
            eta = elapsed / (i + 1) * (n_samples - i - 1)
            logger.info(f"进度: {i + 1}/{n_samples} ({(i + 1) / n_samples * 100:.0f}%) | "
                        f"耗时: {elapsed / 60:.1f} min | 预计剩余: {eta / 60:.1f} min")

    # 截取有效数据
    X = X[:valid_count]
    y = y[:valid_count]

    elapsed = time.perf_counter() - t_start
    logger.info(f"数据生成完成: {valid_count} 有效样本 | 总耗时: {elapsed / 60:.1f} min")

    return X, y


# ============================================================================
# 数据保存与加载
# ============================================================================


def save_training_data(X: np.ndarray, y: np.ndarray, filepath: Path) -> None:
    """
    保存 OPN 训练数据为压缩 .npz 文件。

    Parameters
    ----------
    X : np.ndarray
        特征矩阵
    y : np.ndarray
        标签向量
    filepath : Path
        输出路径
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(filepath, X=X, y=y)
    logger.info(f"训练数据已保存: {filepath} ({X.shape[0]} samples)")


def load_training_data(filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    加载 OPN 训练数据。

    Parameters
    ----------
    filepath : Path
        .npz 文件路径

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (X, y)
    """
    data = np.load(filepath)
    X = data["X"]
    y = data["y"]
    logger.info(f"训练数据已加载: {filepath} ({X.shape[0]} samples)")
    return X, y


# ============================================================================
# 数据划分与标准化
# ============================================================================


def prepare_train_test_split(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    """
    划分训练/测试集并标准化特征。

    Parameters
    ----------
    X : np.ndarray
    y : np.ndarray
    test_size : float
    random_state : int

    Returns
    -------
    tuple
        (X_train_scaled, X_test_scaled, y_train, y_test, scaler)
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    logger.info(f"数据划分: train={X_train.shape[0]}, test={X_test.shape[0]} "
                f"({test_size:.0%} test ratio)")

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("OPN 数据模块测试")
    print("=" * 60)

    # 快速测试：500 组参数 × 500 次仿真
    print("生成小样本测试数据 (500 × 500)...")
    X_test, y_test = generate_opn_training_data(
        n_samples=500, n_sim=500, seed=42
    )
    print(f"  生成 {X_test.shape[0]} 个有效样本")
    print(f"  y 范围: [{y_test.min():.4f}, {y_test.max():.4f}]")
    print(f"  y 均值: {y_test.mean():.4f}")

    # 划分
    X_tr, X_te, y_tr, y_te, scaler = prepare_train_test_split(X_test, y_test)
    print(f"  训练集: {X_tr.shape}, 测试集: {X_te.shape}")

    print("\n✅ 数据模块测试完成")
