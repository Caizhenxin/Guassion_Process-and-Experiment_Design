# -*- coding: utf-8 -*-
"""D85：把 S6-5 的三条阈值改成「两级」并写明历史锚点。

背景：87 份历史真人数据（`2_Data/Real_Data/UnExtact/emp_data`）复算后，
      正确率 0.55 下限会判掉 31/87 = 35.6%，RT 中位 0.30 s 下限会判掉 15/87 = 17.2%。
      ⇒ FAIL 线移到「历史上从未出现过」的位置，模糊区间只 WARN。

本脚本幂等：每处 old 串必须命中恰好 1 次，否则报错退出。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TARGET = REPO / "1_Code" / "Experiment" / "analyze_pilot.py"

OLD_HEADER = 'S6-5 行为量级 ：正确率 0.55–0.98；RT 中位数 0.3–2.0 s；'
NEW_HEADER = ('S6-5 行为量级 ：正确率 0.45–0.995（FAIL）/ 0.55–0.98（PASS，其间 WARN）；'
              'RT 中位 0.20–2.0 s（FAIL 下界）/ 0.30–2.0 s（PASS 下界）；')

OLD_BLOCK = '''    problems5 = []
    if not (0.55 <= acc <= 0.98):
        problems5.append(f"正确率 {acc:.3f} 落在 0.55–0.98 之外")
    if rts and not (0.30 <= median(rts) <= 2.0):
        problems5.append(f"RT 中位数 {median(rts):.3f} s 落在 0.3–2.0 s 之外")
    if rts_post and too_fast > 0.10:
        problems5.append(f"过快（RT < 0.15 s，仅在 RT ≥ T 的试次里）占 {too_fast:.2%} > 10%")
    rep.verdict("S6-5", "FAIL" if problems5 else "PASS",
                f"正确率 {acc:.3f}；RT 中位 {median(rts):.3f} s；"
                f"过快 {too_fast:.2%}（口径：RT ≥ T 的 {len(rts_post)} 个试次，判据 ≤ 10%）"
                + ("；" + "；".join(problems5) if problems5 else "（全部落在合理区间）"))
'''

NEW_BLOCK = '''    # ---- S6-5 阈值的历史锚点（D85，2026-10-18）-------------------------------
    # 参照集：2_Data/Real_Data/UnExtact/emp_data 里 87 份真人逐被试文件（旧设计口径）。
    #   RT 中位        0.234–0.977 s（q05 0.236、中位 0.552）⇒ 0.30 s 下限会判掉 15/87 = 17.2%
    #   正确率         0.431–0.988（q05 0.451、中位 0.645）⇒ 0.55 下限会判掉 31/87 = 35.6%
    #   过快(RT≥T)     0/87 份非零（历史最小 RT 中位 0.234 s）⇒ 10% 上限对真人零误伤
    # 因此：FAIL 线落在「历史真人从未出现」的位置；0.20–0.30 s / 0.45–0.55 只 WARN
    #       （这两段历史真人分别占 15/87、31/87，属于「要人看一眼」而不是「数据坏了」）。
    # 复算这两个比例：python -X utf8 1_Code/Experiment/analyze_rt_baseline.py
    problems5, warns5 = [], []
    if acc != acc:
        warns5.append("无可用正确率，跳过正确率判据")
    elif acc < 0.45 or acc > 0.995:
        problems5.append(f"正确率 {acc:.3f} 低于 0.45 或高于 0.995")
    elif not (0.55 <= acc <= 0.98):
        warns5.append(f"正确率 {acc:.3f} 落在 0.55–0.98 之外（历史真人 31/87 同在此区间）")
    if rts:
        med_rt = median(rts)
        if med_rt < 0.20 or med_rt > 2.0:
            problems5.append(f"RT 中位数 {med_rt:.3f} s 低于 0.20 s 或高于 2.0 s")
        elif med_rt < 0.30:
            warns5.append(f"RT 中位数 {med_rt:.3f} s 落在 0.20–0.30 s 带（历史真人 15/87 同在此区间）")
    elif warns5 is not None:
        warns5.append("无有效 RT，跳过 RT 中位判据")
    if rts_post and too_fast > 0.10:
        problems5.append(f"过快（RT < 0.15 s，仅在 RT ≥ T 的试次里）占 {too_fast:.2%} > 10%")
    verdict5 = "FAIL" if problems5 else ("WARN" if warns5 else "PASS")
    rep.verdict("S6-5", verdict5,
                f"正确率 {acc:.3f}；RT 中位 {median(rts):.3f} s；"
                f"过快 {too_fast:.2%}（口径：RT ≥ T 的 {len(rts_post)} 个试次，判据 ≤ 10%）"
                + ("；" + "；".join(problems5 + warns5) if (problems5 or warns5)
                   else "（全部落在合理区间）"))
'''


def apply(path: Path, old: str, new: str, tag: str) -> None:
    text = path.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        sys.exit(f"[FAIL] {tag}: 命中 {n} 次（应为 1）")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    print(f"[OK] {tag}")


def main() -> int:
    apply(TARGET, OLD_HEADER, NEW_HEADER, "头注 S6-5 阈值行")
    apply(TARGET, OLD_BLOCK, NEW_BLOCK, "S6-5 两级裁决")
    n = len(TARGET.read_text(encoding="utf-8").splitlines())
    print(f"[DONE] analyze_pilot.py = {n} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
