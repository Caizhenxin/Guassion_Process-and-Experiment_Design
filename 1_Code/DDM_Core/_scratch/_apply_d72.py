# -*- coding: utf-8 -*-
"""D72 落纸：Stage 8 组级缓存 + `--resume`（含配置绑定）。

用法：python -X utf8 -u _apply_d72.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

DECISION = (
    "| **D72** | 2026-10-17 | ✅ **Stage 8 长跑可恢复：组级缓存 + `--resume`，且缓存绑定配置**。"
    "① 动机：Stage 8 §10 第 1 条要求正式数据「每组 ~40 人」跑层级拟合，按 §8.40 的成本是"
    "**单次几十小时的批处理作业**；而 `stage8_run.py::main` 原本只在**全部组跑完后**写一次 "
    "`stage8_results.json` ⇒ 第 3 组崩溃 = 前两组白跑。② 做法：每组拟合完立刻写 "
    "`stage8_group_<组>.json`（`tag`/`lines`/`results`/`config`）；`--resume` 命中缓存即跳过拟合，"
    "报告里插一行 `> ♻️ 组 g 复用缓存 …（未重拟合）`；缓存**绑定配置**（`n_em`/`n_draws`/`n_x`/"
    "`n_ppc`/`seed`/`hyper_method`/`bruteforce`/数据源），不一致直接 `ValueError`；缓存非 JSON 或"
    "缺字段也 `ValueError`（**不静默重算**）。③ 牙齿：`_scratch/check_stage8_run.py` **26 → 30 项**"
    "（E13 落盘且报告含该组结果、E14 `--resume` 后 `run_group` 调用 **0** 次且缓存字节不变、"
    "E15 换 `n_em` 必须报配置不一致、E14b 坏缓存报错）。④ 边界：缓存只按**组号**匹配，配置已绑定；"
    "换数据/换配置时必须换 `--out` 目录（或删缓存）。 |"
)

PROGRESS = (
    "| 2026-10-17 | **8**（长跑可恢复 → D72） | **把「N=160 的数十小时批处理」从「一崩全丢」"
    "变成「按组可续」**：每组落盘 `stage8_group_<组>.json` + `--resume`（缓存绑定配置，"
    "损坏/不一致都报错），`check_stage8_run.py` **30/30**。 | `1_Code/DDM_Core/stage8_run.py`"
    "（`_group_file`/`_load_group`/`--resume`）、`_scratch/check_stage8_run.py`（E13–E15）、"
    "`_scratch/_check_stage8_run_d72.txt` | 仍等用户侧 Stage 1 实机验收 / Stage 6 Pilot / "
    "Stage 7 正式采集 / 定稿签批 |"
)

CHANGELOG = (
    "| 2026-10-17 | **新增 D72：Stage 8 组级缓存与 `--resume`**。`stage8_run.py` 每组拟合完立刻写 "
    "`stage8_group_<组>.json`（`tag`/`lines`/`results`/`config`）；`--resume` 命中缓存跳过拟合、"
    "报告里留「♻️ 复用缓存」行；缓存绑定配置（换 `n_em` 等即 `ValueError`）、坏缓存也报错。"
    "`check_stage8_run.py` **26 → 30/30**（E13 落盘、E14 零拟合、E15 配置不一致、E14b 坏缓存）。 |"
)

FILE_ROW = (
    "| `1_Code/DDM_Core/stage8_run.py`（**D72**：`_group_file`/`_load_group`/`--resume`/`config` 绑定）"
    " + `_scratch/check_stage8_run.py`（**30/30**，E13–E15） + `_scratch/_check_stage8_run_d72.txt` "
    "| 2026-10-17（D72） |"
)

S8_ROW = (
    "| `1_Code/DDM_Core/stage8_run.py`（组级缓存/续跑，D72） | 每组拟合完立刻写 "
    "`stage8_group_<组>.json`（含 `config`）；`--resume` 复用已完成组并在报告里留「♻️ 复用缓存」行；"
    "缓存损坏或配置不一致 ⇒ `ValueError`（不静默重算） | `_scratch/check_stage8_run.py` **30/30**"
    "（E13 落盘与报告内容、E14 `run_group` 调用 **0** 次且缓存字节不变、E15 换 `n_em` 报配置不一致、"
    "E14b 坏缓存报错）；E 组原 26 项仍全绿 |"
)

S8_LIMIT = (
    "7. **真实规模必须按组续跑**：每组 ~40 人 × 576 试次的层级拟合是**几十小时**的批处理作业"
    "（§11 第 5 条）；`stage8_run.py` 自 D72 起每组落盘、`--resume` 可续，但缓存**只按组号匹配**"
    "且配置已绑定 ⇒ 换数据/换 `n_em` 必须换 `--out` 目录。报告里「♻️ 复用缓存」行必须保留，"
    "否则读者无法分辨哪些组是这次算的。"
)

RD_SECTION = """### 8.47 组级缓存与 `--resume`（2026-10-17，D72）

1. **动机**：Stage 8 §10 第 1 条要求正式数据「每组 ~40 人」跑层级拟合；按 §8.40 的成本，那是
   **单次几十小时**的批处理作业，而 `main()` 原本只在**全部组跑完后**写一次 `stage8_results.json`
   ⇒ 第 3 组崩溃 = 前两组白跑。
2. **做法**（`1_Code/DDM_Core/stage8_run.py`）：每组拟合完立刻写 `stage8_group_<组>.json`
   （`tag`/`lines`/`results`/`config`）；`--resume` 命中缓存即跳过拟合，报告里插一行
   `> ♻️ 组 g 复用缓存 …（未重拟合）`；缓存**绑定配置**（`n_em`/`n_draws`/`n_x`/`n_ppc`/`seed`/
   `hyper_method`/`bruteforce`/数据源），不一致 ⇒ `ValueError`；缓存非 JSON/缺字段 ⇒ `ValueError`
   （**不静默重算**）。
3. **证据**：`_scratch/check_stage8_run.py` **30/30**（E13 落盘且报告含该组结果；E14 `--resume`
   后 `run_group` 调用 **0** 次、缓存字节不变、报告含「复用缓存」；E15 换 `n_em` 报配置不一致；
   E14b 坏缓存报错）。
4. **边界**：缓存只按**组号**匹配；配置虽然绑定，但换数据/换配置时**必须换 `--out` 目录**。
   这是「别把两套配置混进同一份报告」的最后一道人工防线。
"""

RD_ITEM = (
    "| 56 | ✅ **Stage 8 组级缓存与 `--resume`（D72，§8.47）** | 每组落盘 `stage8_group_<组>.json`"
    "（含 `config`）；`--resume` 跳过已完成组并在报告里留「♻️ 复用缓存」行；坏缓存/配置不一致都"
    "`ValueError`；`check_stage8_run.py` **30/30**（E13–E15） |"
)


def insert_after(text: str, prefix: str, new: str) -> str:
    lines = text.split("\n")
    hit = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hit) == 1, f"{prefix[:40]}… 命中 {len(hit)} 行"
    i = hit[0]
    lines.insert(i + 1, new)
    return "\n".join(lines)


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}")
    jobs = []
    t = MP.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D72" in t:
        print("  [跳过] 工作流_主计划.md（已落）")
    else:
        t = insert_after(t, "| **D71** | 2026-10-17 |", DECISION)
        t = insert_after(t, "| 2026-10-17 | **6/7**（真实规模就绪实测 → D71） |", PROGRESS)
        t = insert_after(t, "| 2026-10-17 | **新增 D71：", CHANGELOG)
        t = insert_after(t, "| `1_Code/Experiment/exp_Check/check_pilot_ready.py`（**新建**，9/9）",
                         FILE_ROW)
        jobs.append((MP, t))

    t = S8.read_text(encoding="utf-8")
    assert "\r" not in t
    if "D72" in t:
        print("  [跳过] Stage8_建模与验证方案.md（已落）")
    else:
        t = insert_after(t, "| `1_Code/DDM_Core/stage8_run.py`（输入契约，D66）", S8_ROW)
        anchor = "6. **仿真器的事实来源存在潜在冲突**"
        lines = t.split("\n")
        hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor)]
        assert len(hits) == 1, hits
        lines.insert(hits[0] + 1, S8_LIMIT)
        t = "\n".join(lines)
        jobs.append((S8, t))

    t = RD.read_text(encoding="utf-8")
    assert "\r" not in t
    if "### 8.47" in t:
        print("  [跳过] README.md（已落）")
    else:
        old = "组层 timeout 7.38%、正确率 0.570、`RT < T` 2.23%、\n   帧长 16.667 ms"
        assert t.count(old) == 1, t.count(old)
        t = t.replace(old, "组层 timeout 7.4%、正确率 0.570、`RT < T` 2.23%、\n   帧长 16.667 ms")
        lines = t.split("\n")
        hits = [i for i, ln in enumerate(lines) if ln.startswith("## 9. 尚未做")]
        assert len(hits) == 1, hits
        blocks = RD_SECTION.split("\n")
        lines[hits[0]:hits[0]] = blocks + [""]
        i55 = [i for i, ln in enumerate(lines) if ln.startswith("| 55 | ✅")]
        assert len(i55) == 1, i55
        lines.insert(i55[0] + 1, RD_ITEM)
        jobs.append((RD, "\n".join(lines)))

    for path, text in jobs:
        if APPLY:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"  [写入] {path.name}")
        else:
            print(f"  [干跑] {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
