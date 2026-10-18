"""D98 文档补丁（第二批）：Stage8 方案的 §9 行与变更日志、Stage6 方案的 §9 清单与变更日志。

第一批（主计划 + README）已由 _apply_d98_docs.py 落盘，此脚本只补剩下两份。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S8 = ROOT / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
S6 = ROOT / "5_Reference" / "08_工作流" / "Stage6_Pilot方案.md"
JSON1 = ROOT / "2_Data" / "Real_Data" / "_SYNTHETIC_DEMO_v1" / "_stage8_out" / "stage8_group_1.json"


def stats() -> str:
    d = json.loads(JSON1.read_text(encoding="utf-8"))
    out = []
    for name, r in (d.get("results") or {}).items():
        loo = r.get("loo") or {}
        out.append(f"{name} ELPD {loo.get('elpd_loo', float('nan')):.1f}"
                   f"（`p_loo` {loo.get('p_loo', float('nan')):.2f}、`k_diag_ok` {loo.get('k_diag_ok')}）")
    return "；".join(out)


def patch(path: Path, subs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in subs:
        c = text.count(old)
        if c != 1:
            print(f"[FAIL] {path.name}：锚点命中 {c} 次（应为 1）\n  {old[:90]}")
            sys.exit(1)
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[ok] {path.name}：{len(text.splitlines())} 行")


def main() -> int:
    s = stats()
    patch(S8, [
        ("| `1_Code/DDM_Core/stage8_run.py`（输入契约，D66） |",
         "| `1_Code/Experiment/run_pipeline.py`（D98） | 把整条分析链串成一条命令"
         "（入库 → 达标 → 层级拟合 → 出图 → 结果节骨架），并用合成数据（8 人 × 576 试次）"
         "端到端验证；每步只调用既有工具，不复制判据 | "
         f"`_stage8_out/stage8_group_1.json` 实测 **{s}**；`intake.py` 8/8 KEEP、"
         "`stage6_report.py` 判「可进入 Stage 7」 |\n"
         "| `1_Code/DDM_Core/stage8_run.py`（输入契约，D66） |"),
        ("| v1.8 | 2026-10-17 |",
         "| v1.9 | 2026-10-18 | **§9 加 `run_pipeline.py` 一行（D98）**：全流程一键跑通，"
         "合成数据 8 人端到端；`loo.psis_loo` 增 `k_diag_ok`（`n_draws < 25` 时 `k̂` 恒 0，"
         "此前是静默的健康读数；`check_loo.py` 26/26 仍全过）。 |\n"
         "| v1.8 | 2026-10-17 |"),
    ])
    patch(S6, [
        ("8. ☐ 按 §8 决策，并把结果回填到 §10 指定的三处。",
         "8. ☐ 一条命令跑完全链路（入库 → 达标 → 拟合 → 图 → 结果节骨架）："
         "`python -X utf8 1_Code\\Experiment\\run_pipeline.py 1_Code\\Experiment\\pilot_data --profile formal`"
         "；只重出图时加 `--reuse-stage8`。用法见 "
         "`5_Reference/08_工作流/全流程一键跑通_使用说明.md`。\n"
         "9. ☐ 按 §8 决策，并把结果回填到 §10 指定的三处。"),
        ("| v1.3 | 2026-10-18 | 新增 §6.3",
         "| v1.4 | 2026-10-18 | 新增 §9 第 8 条（D98：`run_pipeline.py` 一条命令跑完全链路，"
         "原第 8/9 条顺延）；判据本身未变 |\n"
         "| v1.3 | 2026-10-18 | 新增 §6.3"),
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
