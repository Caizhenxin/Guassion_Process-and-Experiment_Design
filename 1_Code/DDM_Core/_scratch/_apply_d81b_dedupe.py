# -*- coding: utf-8 -*-
"""D81b：验收检查器按 `trialID` 去重（崩溃后重跑会 append 到同一个 txt）。

发现经过（2026-10-18，主试实机产物）：`1_Code/Experiment/exp_matlab/exp_group1_subject1.txt`
有 588 行，而同一场的 `EXP_data_group1_1.csv` 只有 576 行；`trialID` 1–6 各出现 **3 次**。
根因：txt 通道以 `fopen(...,'a+')` 打开（追加），主试先后跑了 3 次——前两次各在
第 6 个试次处崩（D78 的"第一个未响应试次崩"），第三次跑完 576 个试次。
于是 txt 里留下 6+6+576 = 588 行，而 CSV 是最后一次运行的 `cell2table` 快照（576 行）。

后果：`check_stage1_acceptance.py` 若不去重，会把崩溃run的 12 行也算进 6-C/6-D 的
分母与计数里（且这些行来自旧版本程序）。修法：按 `trialID` 去重、**保留最后一次**
出现的行，并在报告里打印"丢了 N 行重复"以免静默。

幂等：断言每处命中恰好 1 次。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TARGET = REPO / "1_Code" / "Experiment" / "exp_Check" / "check_stage1_acceptance.py"

EDITS: list[tuple[str, str, str]] = [
    (
        "新增 _dedupe 函数",
        "def check_6d(rep: Report, header: list[str], rows: list[dict], raw: bytes):",
        'def dedupe(rows: list[dict]) -> tuple[list[dict], int]:\n'
        '    """按 `trialID` 去重，**保留最后一次**出现的行；返回 (去重后, 丢弃行数)。\n'
        "\n"
        "    D81b：txt 通道是 `fopen(...,'a+')` 追加打开的，主试崩溃后重跑会往同一个文件\n"
        "    继续写同一批 `trialID`。CSV（`cell2table` 快照）只保留最后一次运行，两者行数\n"
        "    不一致时以 CSV 为准。顺序稳定的字典保序 ⇒ 去重后行序不变。\n"
        '    """\n'
        "    last: dict[str, int] = {}\n"
        "    for i, r in enumerate(rows):\n"
        '        tid = (r.get("trialID") or "").strip()\n'
        "        if tid:\n"
        "            last[tid] = i\n"
        "    keep = set(last.values())\n"
        "    out = [r for i, r in enumerate(rows) if i in keep]\n"
        "    return out, len(rows) - len(out)\n"
        "\n"
        "\n"
        "def check_6d(rep: Report, header: list[str], rows: list[dict], raw: bytes):",
    ),
    (
        "analyze 里调用去重",
        "        all_rows.extend(rows)\n",
        "        rows, n_dup = dedupe(rows)\n"
        "        if n_dup:\n"
        '            rep.info("0 口径", f"{p.name}：按 `trialID` 去重丢弃 {n_dup} 行"\n'
        '                     "（`fopen` 追加写 ⇒ 崩溃重跑会重复写同一批试次；"\n'
        '                     "以最后一次出现的行为准，与 CSV 快照一致）")\n'
        "        all_rows.extend(rows)\n",
    ),
]


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    for name, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            print(f"❌ [{name}] 命中 {n} 次（要求恰好 1 次），中止，未写文件")
            return 1
        src = src.replace(old, new)
        print(f"✅ [{name}]")
    TARGET.write_text(src, encoding="utf-8", newline="\n")
    print(f"\n已写回 {TARGET}（{len(src.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
