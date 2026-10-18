# -*- coding: utf-8 -*-
"""D91 补：设计文档 §9 变更日志加 v2.6 行（幂等）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / "5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md"

ROW = (
    "| **v2.6（掩蔽因子取舍 → D91）** | 2026-10-18 | 用户问「是否必要全部都有掩蔽、要不要新增无掩蔽组做对比」"
    "⇒ 评估后**裁定不加**，新增 **§7 第 ⑨ 行**记录理由：`twophase.py:5-8` 的相位边界在 T、似然里没有 M 参数、"
    "掩蔽效力由 `rho` 吸收；加对照只买「直接因果对照 / rho×T 假设检验 / 泛化性声明」三项，"
    "都不进主估计量 P\\|T\\|W → SPE；代价为 SE ×1.41（`delta_a` 条件 SE 30.8% → ~43.5%）或场次翻倍到 33 min；"
    "87 份历史 CSV 无 group 7 ⇒ 无免费对照 |"
)

lines = DESIGN.read_text(encoding="utf-8").split("\n")
hits = [i for i, ln in enumerate(lines) if ln.startswith("| **v2.5（W/T 取点答疑落纸")]
assert len(hits) == 1, f"v2.5 行命中 {len(hits)} 次"
i = hits[0]
assert "v2.6" not in "\n".join(lines), "v2.6 行已存在，脚本非幂等"
lines = lines[: i + 1] + [ROW] + lines[i + 1 :]
DESIGN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("设计文档 §9 已加 v2.6 行")
