#!/usr/bin/env python3
"""
OPN 主训练流程脚本（Omission Probability Network Training Pipeline）

功能:
  1. 配置管理（支持命令行参数和配置文件）
  2. DDM 仿真数据生成
  3. OPN 模型训练
  4. 模型评估、保存、日志输出

使用示例:
  # 快速测试模式（5000 组参数）
  python opn_train.py --mode fast

  # 完整训练模式（50000 组参数）
  python opn_train.py --mode full

  # 从已有数据训练
  python opn_train.py --mode train_only --data_file path/to/data.npz

参考文献: Leng, X., Fengler, A., Shenhav, A., & Frank, M. J. (2025).
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---- 项目根目录 ----
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR
for _ in range(5):  # 向上回溯到项目根目录
    if (_PROJECT_ROOT / "1_Code").exists():
        break
    _PROJECT_ROOT = _PROJECT_ROOT.parent

sys.path.insert(0, str(_SCRIPT_DIR))

# ---- 本地模块 ----
from opn_simulator import SIMULATOR, benchmark_simulator
from opn_data import (
    DEFAULT_PRIOR_RANGES,
    generate_opn_training_data,
    prepare_train_test_split,
    save_training_data,
    load_training_data,
)
from opn_model import (
    build_opn,
    train_opn,
    evaluate_opn,
    print_evaluation_summary,
    save_model,
)

# ---- 路径配置 ----
CODE_DIR = _SCRIPT_DIR
DATA_DIR = _PROJECT_ROOT / "2_Data" / "Generate_Data" / "OPN_Training"
FIG_DIR = _PROJECT_ROOT / "3_Figures" / "OPN_Training"

for _d in [DATA_DIR, FIG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ---- 日志配置 ----
LOG_FILE = DATA_DIR / f"opn_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("OPN_Train")


# ============================================================================
# 默认配置
# ============================================================================

DEFAULT_CONFIG = {
    "mode": "fast",             # fast | full | train_only
    "seed": 42,
    "n_train_samples_fast": 5000,
    "n_train_samples_full": 50000,
    "n_sim_per_sample": 5000,
    "test_size": 0.2,
    "hidden_layer_sizes": (128, 64, 32),
    "max_iter": 500,
    "alpha": 0.001,
    "prior_ranges": DEFAULT_PRIOR_RANGES,
    "data_file": None,          # train_only 模式指定的数据文件
    "model_prefix": "opn",
    "output_data_dir": str(DATA_DIR),
    "output_fig_dir": str(FIG_DIR),
}


# ============================================================================
# 命令行参数
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OPN (Omission Probability Network) 训练脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python opn_train.py --mode fast          # 快速测试 (5000 组)
  python opn_train.py --mode full          # 完整训练 (50000 组)
  python opn_train.py --mode train_only --data_file ../data.npz
        """,
    )
    parser.add_argument("--mode", choices=["fast", "full", "train_only", "benchmark"],
                        default="fast", help="运行模式 (默认: fast)")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--n_samples", type=int, default=None,
                        help="训练样本数 (覆盖默认值)")
    parser.add_argument("--n_sim", type=int, default=None,
                        help="每组参数仿真试次数")
    parser.add_argument("--data_file", type=str, default=None,
                        help="train_only 模式: 已有 .npz 数据文件路径")
    parser.add_argument("--hidden_layers", type=str, default="128,64,32",
                        help="隐藏层结构，逗号分隔 (默认: 128,64,32)")
    parser.add_argument("--max_iter", type=int, default=500, help="最大训练迭代数")
    parser.add_argument("--alpha", type=float, default=0.001, help="L2 正则化强度")
    parser.add_argument("--model_prefix", type=str, default="opn",
                        help="模型文件名前缀")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> dict:
    """根据命令行参数构建配置字典。"""
    config = DEFAULT_CONFIG.copy()
    config["mode"] = args.mode
    config["seed"] = args.seed

    if args.n_samples is not None:
        config["n_train_samples_fast" if args.mode == "fast" else "n_train_samples_full"] = args.n_samples

    if args.n_sim is not None:
        config["n_sim_per_sample"] = args.n_sim

    if args.data_file:
        config["data_file"] = args.data_file

    config["hidden_layer_sizes"] = tuple(int(x) for x in args.hidden_layers.split(","))
    config["max_iter"] = args.max_iter
    config["alpha"] = args.alpha
    config["model_prefix"] = args.model_prefix

    return config


# ============================================================================
# 主训练流程
# ============================================================================


def run_pipeline(config: dict) -> None:
    """
    执行完整的 OPN 训练流水线。

    流程:
      1. 仿真器基准测试
      2. 生成/加载训练数据
      3. 数据划分与标准化
      4. 模型训练
      5. 评估与保存
    """
    mode = config["mode"]
    seed = config["seed"]
    data_dir = Path(config["output_data_dir"])
    model_prefix = config["model_prefix"]

    logger.info("=" * 60)
    logger.info(f"OPN 训练流水线启动 | 模式: {mode} | 种子: {seed}")
    logger.info(f"数据目录: {data_dir}")
    logger.info("=" * 60)

    # ========== Step 1: 仿真器基准测试 ==========
    logger.info("Step 1/5: 仿真器基准测试")
    try:
        tps, om_rate = benchmark_simulator()
        logger.info(f"仿真器速度: {tps:.0f} trials/s")
    except Exception as e:
        logger.warning(f"基准测试失败（不影响继续）: {e}")

    # ========== Step 2: 生成/加载训练数据 ==========
    logger.info("Step 2/5: 准备训练数据")

    if mode == "train_only":
        # 从已有文件加载
        data_path = Path(config["data_file"]) if config["data_file"] else data_dir / "opn_training_data_full.npz"
        if not data_path.exists():
            logger.error(f"数据文件不存在: {data_path}")
            sys.exit(1)
        X, y = load_training_data(data_path)

    elif mode == "benchmark":
        # 仅仿真器测试，不训练
        logger.info("基准测试模式，跳过训练")
        return

    else:
        # 生成新数据
        n_samples = (config["n_train_samples_fast"] if mode == "fast"
                     else config["n_train_samples_full"])
        n_sim = config["n_sim_per_sample"]

        logger.info(f"生成训练数据: {n_samples} 组参数 × {n_sim} 次仿真")
        est_hours = n_samples * n_sim / 5000 / 3600
        logger.info(f"预估耗时: {est_hours:.1f} 小时")

        X, y = generate_opn_training_data(
            n_samples=n_samples,
            n_sim=n_sim,
            prior_ranges=config["prior_ranges"],
            seed=seed,
        )

        # 保存训练数据
        suffix = "fast" if mode == "fast" else "full"
        save_training_data(X, y, data_dir / f"opn_training_data_{suffix}.npz")

    logger.info(f"训练数据: {X.shape}")

    # ========== Step 3: 数据划分与标准化 ==========
    logger.info("Step 3/5: 数据划分与标准化")
    X_train, X_test, y_train, y_test, scaler = prepare_train_test_split(
        X, y, test_size=config["test_size"], random_state=seed
    )

    # ========== Step 4: 模型训练 ==========
    logger.info("Step 4/5: 训练 OPN 模型")
    logger.info(f"  隐藏层: {config['hidden_layer_sizes']}")
    logger.info(f"  最大迭代: {config['max_iter']}")

    opn = build_opn(
        hidden_layer_sizes=config["hidden_layer_sizes"],
        max_iter=config["max_iter"],
        alpha=config["alpha"],
        random_state=seed,
    )

    t0 = time.perf_counter()
    opn = train_opn(opn, X_train, y_train)
    train_time = time.perf_counter() - t0
    logger.info(f"训练耗时: {train_time:.1f}s")

    # ========== Step 5: 评估与保存 ==========
    logger.info("Step 5/5: 评估与保存")
    metrics = evaluate_opn(opn, X_train, y_train, X_test, y_test)
    metrics["train_time_seconds"] = round(train_time, 1)
    metrics["mode"] = mode
    metrics["n_samples"] = int(X.shape[0])
    metrics["timestamp"] = datetime.now().isoformat()

    print_evaluation_summary(metrics)

    # 保存模型
    save_model(opn, scaler, metrics, data_dir, prefix=model_prefix)

    # 保存配置
    config_path = data_dir / f"{model_prefix}_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        serializable_config = {k: (str(v) if isinstance(v, tuple) else v)
                               for k, v in config.items()}
        serializable_config["prior_ranges"] = {
            k: list(v) for k, v in DEFAULT_PRIOR_RANGES.items()
        }
        json.dump(serializable_config, f, indent=2, ensure_ascii=False)
    logger.info(f"配置已保存: {config_path}")

    # 质量检查
    if metrics["test_r2"] < 0.85:
        logger.warning(f"⚠️ 测试 R² = {metrics['test_r2']:.3f} < 0.85，可能需要增加训练数据或调整网络结构")
    else:
        logger.info(f"✅ 测试 R² = {metrics['test_r2']:.3f} >= 0.85，模型质量合格")

    logger.info("=" * 60)
    logger.info("OPN 训练流水线完成")
    logger.info(f"模型位置: {data_dir / f'{model_prefix}_model.joblib'}")
    logger.info(f"日志文件: {LOG_FILE}")
    logger.info("=" * 60)


# ============================================================================
# 入口
# ============================================================================

if __name__ == "__main__":
    args = parse_args()
    config = build_config(args)
    run_pipeline(config)
