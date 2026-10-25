"""只重画 fig13（不改数据）：从已落盘的 CSV 重建图，避免为改版式重跑 13 min 拟合。"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import power_recovery as PR  # noqa: E402

df = pd.read_csv(PR.OUT / "power_discriminate.csv")
curve = pd.read_csv(PR.OUT / "power_discriminate_curve.csv")
print("columns:", list(df.columns), "|", list(curve.columns))
PR.fig_discriminate(df, curve, 0.60, PR.FIG_OUT / "fig13_power_discriminate.png")
