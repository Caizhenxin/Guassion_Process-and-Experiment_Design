#!/usr/bin/env python3
"""
OPN 训练用的批量 DDM 仿真器（Omission Probability Network Simulator）

基于现有 model_engine.py 中的 simulate_ddm_with_deadline() 改写，
支持批量向量化仿真以加速 OPN 训练数据的生成。

参考文献: Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025).
          The Perils of Omitting Omissions when Modeling Evidence Accumulation.
"""

import logging
import time
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ============================================================================
# 方案 A: 纯 NumPy 向量化版本
# ============================================================================


def simulate_ddm_batch_vectorized(
    v: float,
    a: float,
    z: float,
    t0: float,
    deadline_s: float,
    n_trials: int = 5000,
    dt: float = 0.001,
) -> int:
    """
    对同一组 (v, a, z, t0, deadline) 运行 n_trials 次 DDM 仿真，
    返回 omission 次数。

    使用向量化实现：所有试次并行 Euler-Maruyama stepper。

    Parameters
    ----------
    v : float
        漂移率（drift rate）
    a : float
        边界分离（boundary separation），必须 > 0
    z : float
        绝对起始点（absolute starting point），0 < z < a
    t0 : float
        非决策时间（non-decision time），秒
    deadline_s : float
        截止时间（deadline），秒
    n_trials : int
        仿真试次数
    dt : float
        Euler 步长，默认 0.001s

    Returns
    -------
    int
        omission 试次数
    """
    decision_budget = deadline_s - t0
    if decision_budget <= dt:
        return n_trials

    max_steps = int(decision_budget / dt)

    # 初始化：所有试次的证据累积位置
    x = np.full(n_trials, z, dtype=np.float64)
    # 跟踪哪些试次仍在活跃（未穿越边界）
    active = np.ones(n_trials, dtype=bool)
    omission = np.ones(n_trials, dtype=bool)  # 默认全是 omission

    for _step in range(max_steps):
        if not active.any():
            break

        n_active = active.sum()
        # Euler-Maruyama step: dx = v*dt + sqrt(dt)*N(0,1)
        noise = np.random.randn(n_active)
        dx = v * dt + np.sqrt(dt) * noise
        x[active] += dx

        # 上边界检查 (response=1)
        hit_upper = (x >= a) & active
        if hit_upper.any():
            omission[hit_upper] = False
            active[hit_upper] = False

        # 下边界检查 (response=0)
        hit_lower = (x <= 0.0) & active
        if hit_lower.any():
            omission[hit_lower] = False
            active[hit_lower] = False

    return int(omission.sum())


# ============================================================================
# 方案 B: Numba JIT 加速版本
# ============================================================================

try:
    from numba import njit  # type: ignore[import-untyped]

    @njit
    def _simulate_ddm_batch_numba_kernel(
        v: float,
        a: float,
        z: float,
        max_steps: int,
        n_trials: int,
        dt: float,
    ) -> int:
        """Numba JIT 编译的批量 DDM 仿真核心（单线程）。"""
        # 使用 Python float 避免 numba 类型推断问题
        dt_f = float(dt)
        sqrt_dt = np.sqrt(dt_f)
        v_f = float(v)
        a_f = float(a)
        z_f = float(z)

        x = np.full(n_trials, z_f)
        active = np.ones(n_trials, dtype=np.bool_)
        omission_count = 0

        for _step in range(max_steps):
            n_active = int(active.sum())
            if n_active == 0:
                break

            noise = np.random.randn(n_active)

            # 逐个试次更新（numba 中向量索引较复杂，用循环）
            idx = 0
            for i in range(n_trials):
                if not active[i]:
                    continue
                x[i] += v_f * dt_f + sqrt_dt * noise[idx]
                idx += 1

                if x[i] >= a_f:
                    active[i] = False
                elif x[i] <= 0.0:
                    active[i] = False
                    omission_count += 1

        # 剩余的活跃试次 = omission
        omission_count += int(active.sum())
        return omission_count

    def simulate_ddm_batch_numba(
        v: float,
        a: float,
        z: float,
        t0: float,
        deadline_s: float,
        n_trials: int = 5000,
        dt: float = 0.001,
    ) -> int:
        """Numba JIT 编译的批量 DDM 仿真入口。"""
        decision_budget = deadline_s - t0
        if decision_budget <= dt:
            return n_trials
        max_steps = int(decision_budget / dt)
        return _simulate_ddm_batch_numba_kernel(v, a, z, max_steps, n_trials, dt)

    # 预热 JIT 编译
    _ = simulate_ddm_batch_numba(v=1.0, a=1.0, z=0.5, t0=0.3, deadline_s=1.0, n_trials=10)
    SIMULATOR = simulate_ddm_batch_numba
    logger.info("OPN Simulator: 使用 Numba JIT 加速版本")

except ImportError:
    SIMULATOR = simulate_ddm_batch_vectorized
    logger.warning("OPN Simulator: Numba 未安装，使用纯 NumPy 版本（速度较慢）")


# ============================================================================
# 速度基准测试
# ============================================================================


def benchmark_simulator(
    v: float = 1.5,
    a: float = 1.2,
    z: float = 0.6,
    t0: float = 0.3,
    deadline_s: float = 0.8,
    n_trials: int = 5000,
    n_repeats: int = 10,
) -> Tuple[float, float]:
    """
    运行仿真器速度基准测试。

    Returns
    -------
    tuple[float, float]
        (trials_per_second, avg_omission_rate)
    """
    omission_rates = []
    t_start = time.perf_counter()
    for _ in range(n_repeats):
        n_om = SIMULATOR(v=v, a=a, z=z, t0=t0, deadline_s=deadline_s, n_trials=n_trials)
        omission_rates.append(n_om / n_trials)
    elapsed = time.perf_counter() - t_start

    total_trials = n_repeats * n_trials
    tps = total_trials / elapsed
    avg_rate = np.mean(omission_rates)

    logger.info(f"Simulator 基准: {total_trials} trials in {elapsed:.1f}s → {tps:.0f} trials/s, "
                f"omission_rate={avg_rate:.3f}")
    return tps, avg_rate


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 60)
    print("OPN Simulator 测试")
    print("=" * 60)

    # 测试 1: 高 omission 参数
    n_om = SIMULATOR(v=-1.0, a=2.0, z=1.0, t0=0.3, deadline_s=0.6, n_trials=1000)
    rate = n_om / 1000
    print(f"  高 omission 参数: {n_om}/1000 = {rate:.1%}  (预期 > 50%)")

    # 测试 2: 低 omission 参数
    n_om = SIMULATOR(v=3.0, a=0.8, z=0.4, t0=0.2, deadline_s=1.5, n_trials=1000)
    rate = n_om / 1000
    print(f"  低 omission 参数: {n_om}/1000 = {rate:.1%}  (预期 < 10%)")

    # 测试 3: 速度基准
    tps, rate = benchmark_simulator()
    print(f"  速度基准: {tps:.0f} trials/s  (omission rate = {rate:.3f})")

    print("\n✅ Simulator 测试完成")
