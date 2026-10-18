# -*- coding: utf-8 -*-
"""D94：`qc_group.py` 按 (stage, trialID) 去重（保留最后一次出现）。

实机事实（2026-10-18，组1 被试1，程序 v4.8）：
    txt 正式段 **1152** 行 = 576 × 2，每个 trialID 恰出现两次（被试把整场跑了两遍，
    `fopen(...,'a+')` 追加写把两场都留着）；CSV 只是最后一次快照（576 行）。
    ⇒ G2「正式段 576 试次：1 名不符」、G4「每格 48 试次：有被试不符」都是
      **工具把「一个文件一场」当不变量**造成的假红（D81b 给 Stage 1 检查器加 dedupe 的第四次同根因）。
"""
from pathlib import Path

F = Path("1_Code/Experiment/qc_group.py")
src = F.read_text(encoding="utf-8")

reps = []

reps.append((
    """    rows = ap.row_dicts(header, rows_raw)

    legacy = len(header) < V4_NCOL
""",
    """    rows = ap.row_dicts(header, rows_raw)

    # ★ D94：同一 subjectID 的 txt 是追加写（`fopen(...,'a+')`）⇒ 整场跑两遍就会把
    #   576 个 trialID 各写两遍（实机见过 1152 行）。按 (stage, trialID) 保留最后一次，
    #   与 check_stage1_acceptance.py 的 dedupe() 同一口径；丢弃行数写进汇总表。
    seen: dict = {}
    for r in rows:
        seen[(str(r.get("stage", "")).strip().strip('"'), str(r.get("trialID", "")).strip())] = r
    n_dropped = len(rows) - len(seen)
    rows = list(seen.values())

    legacy = len(header) < V4_NCOL
""",
))

reps.append((
    '''        "n_formal": 0, "n_practice": 0, "p_vals": set(),''',
    '''        "n_formal": 0, "n_practice": 0, "p_vals": set(), "n_dropped": n_dropped,''',
))

reps.append((
    '''    out("| 组 | P | 文件 | 可用 | 剔除 | 待复核 | timeout | 正确率 | RT 中位 | `RT<T` | 其中刺激内 | 帧长(ms) |")
    out("|---|---|---|---|---|---|---|---|---|---|---|---|")''',
    '''    out("| 组 | P | 文件 | 可用 | 剔除 | 待复核 | timeout | 正确率 | RT 中位 | `RT<T` | 其中刺激内 | 帧长(ms) | 去重行 |")
    out("|---|---|---|---|---|---|---|---|---|---|---|---|---|")''',
))

reps.append((
    '''            f"{flip_ms} |")''',
    '''            f"{flip_ms} | {g.get('n_dropped', 0)} |")''',
))

for old, new in reps:
    assert src.count(old) == 1, ("miss", old[:60])
    src = src.replace(old, new)

F.write_text(src, encoding="utf-8", newline="\n")
print(f"qc_group.py：{len(src.splitlines())} 行（dedupe + 汇总列）")
