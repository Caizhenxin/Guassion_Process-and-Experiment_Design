# -*- coding: utf-8 -*-
"""为合成数据集写「这是合成数据」的声明 + 真值清单。

数据本身由 `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`（M-T1 两阶段 DDM 模拟）生成，
**不是人类被试数据**。真值直接从生成器的 `QC_TRUTH` / `TRUTH` 导出，避免手抄出错。
"""
from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
OUT = ROOT / "2_Data" / "Real_Data" / "_SYNTHETIC_DEMO_v1"
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core" / "_scratch"))

import _make_ddm_pilot as G  # noqa: E402

P_BY_GROUP = {1: 0, 2: 8, 3: 32, 4: 120}


def main() -> int:
    truth = dataclasses.asdict(G.QC_TRUTH)
    manifest = {
        "kind": "SYNTHETIC",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generator": "1_Code/DDM_Core/_scratch/_make_ddm_pilot.py",
        "model": "M-T1（两阶段漂移；相位边界 = T）",
        "params": {
            "rho": 0.8,
            "n_rep": 12,
            "anticipation": 0.03,
            "preset": "qc",
            "seed_base": 100,
        },
        "group_truth": {g: dict(truth) for g in (1, 2, 3, 4)},
        "sessions": [
            {
                "group": g,
                "subject": s,
                "file": f"exp_group{g}_subject{s}.txt",
                "P": P_BY_GROUP[g],
                "n_practice": max(4, P_BY_GROUP[g]),
                "n_rows": max(4, P_BY_GROUP[g]) + 576,
                "seed": 100 + g,
            }
            for g in (1, 2, 3, 4)
            for s in (1, 2)
        ],
    }
    (OUT / "synth_truth.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    readme = OUT / "README.md"
    readme.write_text(
        "\n".join([
            "# `_SYNTHETIC_DEMO_v1` —— **合成数据，不是人类被试数据**",
            "",
            f"生成时间：{manifest['generated_at']}",
            "",
            "## 这是什么",
            "",
            "这一目录里的 8 个 `.txt` 由 `1_Code/DDM_Core/_scratch/_make_ddm_pilot.py`",
            "（M-T1 两阶段 DDM）模拟生成，**只用于把 Stage 1 → Stage 8 的流水线跑通**。",
            "它们**不得**进入任何正式分析、也不得写进论文的结果表格。",
            "",
            "## 真值（用于对照「流程能不能把已知参数捞回来」）",
            "",
            "见 `synth_truth.json`（由生成器直接导出，非手抄）：",
            "",
            "- 相位污染系数 `rho = 0.8`（M-T1 为真，M-T3 应被拒绝）",
            "- P 效应 `beta_P = 1.5`（组 1/2/3/4 = P 0/8/32/120）",
            "- 其它参数见 `group_truth`",
            "",
            "## 规模与构成",
            "",
            "| 组 | P | 练习试次 | 正式试次 | 被试 |",
            "|---|---|---|---|---|",
            "| 1 | 0 | 4 | 576 | 2 |",
            "| 2 | 8 | 8 | 576 | 2 |",
            "| 3 | 32 | 32 | 576 | 2 |",
            "| 4 | 120 | 120 | 576 | 2 |",
            "",
            "合计 8 名被试、每名 12 个 `(T, W)` 格 × 48 试次。抢按按 3% 注入（真实被试约 1%–3%），",
            "以便 `check_stage1_acceptance.py` 的 6-B「刺激期内按键」有样本。",
            "",
            "## 换真数据时怎么做",
            "",
            "把主试用 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` 收来的",
            "`EXP_data_group*_*.csv` + `exp_group*_subject*.txt` 放进 `2_Data/Real_Data/` 下",
            "一个新目录（例如 `2026-11_pilot/`），然后对那个目录重跑同一套命令即可；",
            "**不要**把真数据和本目录混放（`intake.py` 会把同名快照判为 shadowed）。",
            "",
        ]),
        encoding="utf-8", newline="\n")
    print("[ok] synth_truth.json + README.md 已写")
    print("     数据目录：", OUT)
    print("     被试：", len(manifest["sessions"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
