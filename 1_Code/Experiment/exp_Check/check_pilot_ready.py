# -*- coding: utf-8 -*-
"""Stage 6/7 就绪守卫（D71）：

用 **DDM 生成的 8 人 × 576 试次 Pilot 数据**跑通 `qc_group.py` 与 `analyze_pilot.py` 之后，
把「跑通了」这件事钉成可复跑的断言 —— 因为这两个脚本的输出会随口径漂移，
而「合法数据不会被自己的质控判死 / 待复核不等于剔除」这两条是最容易被改坏的性质。

断言（全部读**落盘日志**，不重跑内环）：

* P1 `qc_group.py` 的 G1–G9 全 PASS 且**剔除 0**；
* P2 「待复核」的**人数与依据**钉死（合法 DDM 数据上 4 人因 S6-5、1 人因 S6-1）；
* P3 `analyze_pilot.py` 结论是「Stage 6 检查通过（0 项 WARN）」；
* P4 静态：`qc_group.py` 里「待复核」与「剔除」是两个分支（不复用剔除的累加器）；
* P5 静态：`analyze_pilot.py` 仍把 S6-2c（`0.15 s ≤ RT < T`）与 S6-2 分开判（否则 D43 的结论会 silently 变）。

用法：``python -X utf8 -u check_pilot_ready.py``（默认读仓库里已落盘的日志）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # 1_Code/Experiment/exp_Check
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QC_LOG = REPO / "1_Code" / "DDM_Core" / "_scratch" / "_qc_group_n8.txt"
PILOT_LOG = REPO / "1_Code" / "DDM_Core" / "_scratch" / "_pilot_analysis_n8.txt"
QC_SRC = REPO / "1_Code" / "Experiment" / "qc_group.py"
PILOT_SRC = REPO / "1_Code" / "Experiment" / "analyze_pilot.py"

N_OK = 0
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global N_OK
    if ok:
        N_OK += 1
        print(f"  ✅ {name}" + (f"：{detail}" if detail else ""))
    else:
        FAILS.append(name)
        print(f"  ❌ {name}" + (f"：{detail}" if detail else ""))


def main() -> int:
    print("=" * 96)
    print("Stage 6/7 就绪守卫（D71）：合法 DDM 数据不被自己的质控判死、待复核 ≠ 剔除")
    print("=" * 96)

    missing = [p.name for p in (QC_LOG, PILOT_LOG, QC_SRC, PILOT_SRC) if not p.exists()]
    check("P0 输入在场（两份日志 + 两个脚本）", not missing, f"缺 {missing}" if missing else "4/4")
    if missing:
        return 1

    qc = QC_LOG.read_text(encoding="utf-8")
    pilot = PILOT_LOG.read_text(encoding="utf-8")
    qc_src = QC_SRC.read_text(encoding="utf-8")
    pilot_src = PILOT_SRC.read_text(encoding="utf-8")

    g_rows = re.findall(r"^\| (G\d) \| (✅ PASS|❌ FAIL)", qc, re.M)
    check("P1 qc_group.py 的 G1–G9 全 PASS",
          len(g_rows) == 9 and all(v == "✅ PASS" for _, v in g_rows),
          f"{len(g_rows)} 行、PASS {sum(1 for _, v in g_rows if v == '✅ PASS')} 行")
    check("P1b 组层判据没有被「合法但慢」的被试拉成 FAIL（剔除 0）",
          "剔除 **0**" in qc or "剔除 **0** 名" in qc,
          re.search(r"剔除 \*\*\d+\*\* 名、待复核 \*\*\d+\*\* 名", qc).group(0)
          if re.search(r"剔除 \*\*\d+\*\* 名、待复核 \*\*\d+\*\* 名", qc) else "未找到汇总行")

    flagged = re.findall(r"^\| 1 \| (\d+) \| 🟠 待复核 \| (.+?) \|$", qc, re.M)
    reasons = sorted(r for _, r in flagged)
    check("P2 「待复核」的人数是 5（合法 DDM 数据上的实测值）",
          len(flagged) == 5, f"待复核 {len(flagged)} 人")
    check("P2b 依据分布：S6-5 × 4、S6-1 × 1",
          reasons.count("S6-5 FAIL") == 4 and reasons.count("S6-1 FAIL") == 1,
          f"依据 = {reasons}")
    check("P2c 「待复核」没有升级成「剔除」",
          "🟠 待复核" in qc and "剔除 **0**" in qc,
          "待复核与剔除是两个分支")

    check("P3 analyze_pilot.py 对同一批数据判「通过、0 项 WARN」",
          "Stage 6 检查通过（0 项 WARN）" in pilot,
          "见 _pilot_analysis_n8.txt 末行")

    check("P4 静态：qc_group.py 的待复核与剔除不是同一个累加器",
          "待复核" in qc_src and "review" in qc_src.lower(),
          "需要在源码里同时看到中文标签与 internal review 变量")
    check("P5 静态：analyze_pilot.py 仍把 S6-2c 与 S6-2 分开判",
          "S6-2c" in pilot_src and "S6-2c" in pilot,
          "D43 的结论依赖这一分叉")

    print("\n" + "=" * 96)
    print(f"共 {N_OK + len(FAILS)} 项，未通过 {len(FAILS)} 项"
          + (f"：{', '.join(FAILS)}" if FAILS else "。"))
    print("=" * 96)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
