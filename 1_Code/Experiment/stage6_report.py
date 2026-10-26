# -*- coding: utf-8 -*-
"""Stage 6 达标报告器：一个目录 → 一份「Pilot 能不能进 Stage 7」的 Markdown 报告。

**为什么需要它**：`analyze_pilot.py` 面向「一份数据 / 一个目录」逐条打印裁决；`qc_group.py` 是
Stage 7 的**组层数据质量**判据（G1–G9）；`intake.py` 判的是**单场能不能计入 N**。Stage 6 真正
要回答的问题——「这 N 个人加起来的 Pilot 算不算过关、按 `Stage6_Pilot方案.md` §8 该走哪条决策
分支」——此前只能由人对着屏算。本脚本把它变成一条命令，并且**不重复实现任何判据**：

- 单场裁决：`intake.audit_one`（内部复用 `check_stage1_acceptance` 与 `qc_group`）；
- 逐条 S1/S6 裁决：`qc_group.run_subject_check`（内部用子进程调 `analyze_pilot.py`，单一事实来源）；
- 决策表：`5_Reference/08_工作流/Stage6_Pilot方案.md` §8 的行，逐字搬进 `RULES`。

用法：

    python -X utf8 1_Code/Experiment/stage6_report.py 1_Code/Experiment/pilot_data
    python -X utf8 1_Code/Experiment/stage6_report.py <dir> --expect-n 8 --out report.md

退出码：0 = 可进 Stage 7；1 = 有 FAIL / 计入 N 不足；2 = 目录里没有场次。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "exp_Check"))

import intake                                                   # noqa: E402

# 判据标签的固定顺序（与 `Stage6_Pilot方案.md` §5 一致；S6-2b 是 INFO 核对行）
TAGS = ["S1-1", "S1-1b", "S6-3", "S6-4", "S6-1", "S6-2", "S6-2c", "S6-5", "S6-6", "S6-2b"]

# §8 决策规则：触发标签 → 决定。键里的标签任一 FAIL 即触发。
RULES: list[tuple[tuple[str, ...], str]] = [
    (("S1-1", "S1-1b", "S6-3"), "**停止**：回到 Stage 1 修程序；Pilot 数据作废重跑"),
    (("S6-4",), "先查 T/W 列打印精度（方案 §11 第 2 条），再查试次生成；修完重跑"),
    (("S6-1",), "回改设计（缩短 W 或减少长 T 档），更新定稿文档；**不要**用「被试不认真」解释掉"),
    (("S6-5",), "任务难度问题：先查是否与 `P` 档有关，再决定是否调整掩蔽或刺激呈现时间"),
    (("S6-6",), "加长注视期或改指导语，然后重跑 Pilot"),
]

ICON = {"PASS": "✅", "WARN": "🟠", "FAIL": "❌", "INFO": "·"}
BAD = {"FAIL"}


def verdicts_of(rec: dict) -> dict[str, str]:
    """从 `intake` 的 rec 里取逐条裁决；结构层没跑通时返回空表（当作未知，不当作通过）。"""
    return dict(rec.get("verdicts") or {})


def tally(sessions: list[dict]) -> dict[str, dict[str, int]]:
    """按标签累计 PASS/WARN/FAIL/INFO，只统计**计入 N** 的场次。"""
    out = {tag: {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0, "MISS": 0} for tag in TAGS}
    for s in sessions:
        if s["verdict"] != "KEEP":
            continue
        v = s["verdicts"]
        for tag in TAGS:
            status = v.get(tag)
            if status is None:
                out[tag]["MISS"] += 1
            else:
                out[tag][status] = out[tag].get(status, 0) + 1
    return out


def fired_rules(counts: dict[str, dict[str, int]]) -> list[tuple[str, str]]:
    """返回 [(触发的标签, 决定文本)]。"""
    hits = []
    for tags, decision in RULES:
        bad = [t for t in tags if counts.get(t, {}).get("FAIL", 0) > 0]
        if bad:
            hits.append(("／".join(bad), decision))
    return hits


def non_pass(s: dict) -> list[str]:
    """该场次的非 PASS 裁决（WARN/FAIL），用于把「被排除的原因」与「裁决缺陷」并列显示。"""
    return [f"{k} {v}" for k, v in s["verdicts"].items() if k != "S6-2b" and v in ("WARN", "FAIL")]


def build(sessions: list[dict], counts: dict[str, dict[str, int]], expect_n: int | None) -> tuple[str, bool]:
    keep = [s for s in sessions if s["verdict"] == "KEEP"]
    drop = [s for s in sessions if s["verdict"] != "KEEP"]
    groups = sorted({s["gid"] for s in keep})
    hits = fired_rules(counts)

    reviews = [s for s in keep
               if any(v == "WARN" for k, v in s["verdicts"].items() if k != "S6-2b")]
    n_short = expect_n is not None and len(keep) < expect_n
    stage8_dynamic = counts.get("S6-2c", {}).get("WARN", 0) > 0

    L: list[str] = []
    L.append("# Stage 6 ｜Pilot 达标报告")
    L.append("")
    L.append(f"- 目录：`{sessions[0]['root']}`" if sessions else "- 目录：—")
    L.append(f"- 场次：{len(sessions)}（计入 N = **{len(keep)}**，不计入 = {len(drop)}）")
    L.append(f"- 覆盖 P 档：{len(groups)} / 4（{', '.join(f'组{g}' for g in groups) or '—'}）")
    if expect_n is not None:
        L.append(f"- 目标 N：{expect_n} ⇒ {'**不足**' if n_short else '已满足'}")
    L.append("")

    L.append("## 1. 逐场次")
    L.append("")
    L.append("| 组 | 编号 | 判定 | 正式/练习 | 去重 | 正确率 | timeout | 复核标记／不计入原因 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for s in sessions:
        r = s["rec"]
        if s["verdict"] == "KEEP":
            flag = sum(1 for k, v in s["verdicts"].items() if k != "S6-2b" and v == "WARN")
            cells = [
                str(s["gid"]), str(s["sid"]), "✅ KEEP",
                f"{r.get('n_formal', '?')}/{r.get('n_practice', '?')}",
                str(r.get("n_dropped", 0)),
                f"{r.get('acc_mean', float('nan')):.3f}",
                f"{r.get('timeout_prop', float('nan')):.1%}",
                "—" if flag == 0 else f"{flag} 项",
            ]
        else:
            why = s["hard"][0] if s["hard"] else s["verdict"]
            tags = non_pass(s)
            if tags:
                why += "；裁决：" + "、".join(tags)
            cells = [str(s["gid"]), str(s["sid"]), s["verdict"], "—", "—", "—", "—", why]
        L.append("| " + " | ".join(cells) + " |")
    L.append("")

    L.append("## 2. 判据汇总（仅计入场次）")
    L.append("")
    L.append("| 判据 | PASS | WARN | FAIL | INFO | 未取到 |")
    L.append("|---|---|---|---|---|---|")
    for tag in TAGS:
        c = counts[tag]
        L.append(f"| **{tag}** | {c['PASS']} | {c['WARN']} | {c['FAIL']} | {c['INFO']} | {c['MISS']} |")
    L.append("")

    L.append("## 3. 按 §8 决策规则触发的分支")
    L.append("")
    if hits:
        for tag, decision in hits:
            L.append(f"- `{tag}` FAIL ⇒ {decision}")
    else:
        L.append("- 无 FAIL 触发。")
    L.append(f"- `S6-2c` {'WARN ⇒ **Stage 8 扩展为时变输入模型**' if stage8_dynamic else '未超 20% ⇒ Stage 8 按现计划（静态输入）'}。")
    dropped_bad = [(s, non_pass(s)) for s in drop if non_pass(s)]
    if dropped_bad:
        L.append("")
        L.append("> 不计入场次里仍有非 PASS 裁决（**不触发** §8，仅作缺陷线索保留）："
                 + "；".join(f"组{s['gid']}-被试{s['sid']} " + "、".join(t) for s, t in dropped_bad) + "。")
    L.append("")

    L.append("## 4. 结论")
    L.append("")
    ok = (not hits) and (not n_short) and len(keep) > 0
    if keep and not hits and not n_short:
        L.append("**可进入 Stage 7。** 所有计入场次无 FAIL；把本报告与 `analyze_pilot_log.txt` 一起归档，")
        L.append("并按方案 §10 回填三处（`Stage1_技术验证记录.md` §6、主计划 §2/§3/进度表/证据表、`Stage4_识别性结论与设计处方.md` §7）。")
    else:
        reasons = []
        if hits:
            reasons.append("存在 FAIL 触发分支（见 §3）")
        if n_short:
            reasons.append(f"计入 N 只有 {len(keep)}，不足 {expect_n}")
        if not keep:
            reasons.append("没有一场判定为 KEEP")
        L.append("**暂不可进入 Stage 7。** 原因：" + "；".join(reasons) + "。")
    if reviews:
        L.append("")
        L.append(f"> 复核提示（方案 §11 第 7 条）：{len(reviews)}/{len(keep)} 名计入被试带 WARN 标记 "
                 f"（复核率 {len(reviews) / len(keep):.0%}）。**复核 ≠ 剔除**：逐被试阈值在个体差异下会频繁触及边界，"
                 "处置是人工看一眼，不是删数据、也不是放宽阈值。")
    L.append("")
    return "\n".join(L), ok


def collect(path: Path, expect_n: int | None = None) -> list[dict]:
    sessions = intake.find_sessions([path])
    if not sessions:
        return []
    # D120：裁决只走 intake.screen()（五层），不在报告器里另走一遍三层口径——
    # 两份裁决会给同一批数据两个答案（19/1/0 vs 17/1/2，见 2026-10-25 事故）。
    out = intake.screen(sessions, expect_n=expect_n or 8)
    by_id = {(r["gid"], r["sid"]): r for r in out["res"]}
    for s in sessions:
        r = by_id[(s["gid"], s["sid"])]
        s.update({"verdict": r["verdict"], "hard": r["hard"], "soft": r["soft"],
                  "notes": r.get("notes", []), "rec": r["rec"],
                  "verdicts": verdicts_of(r["rec"]), "root": str(path)})
        print(f"[intake] 组{s['gid']} 被试{s['sid']} ⇒ {r['verdict']}"
              + (f"（{r['hard'][0]}）" if r["hard"] else ""), file=sys.stderr)
    return sessions


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 6 Pilot 达标报告器（单场判定 + 判据汇总 + §8 决策）")
    ap.add_argument("path", help="包含 EXP_data_group<组>_<编号>.csv 的目录（或单个 csv）")
    ap.add_argument("--expect-n", type=int, default=None, help="预期计入人数（方案 §3 推荐 8）")
    ap.add_argument("--out", default=None, help="把报告写成这个 .md（默认只打印）")
    args = ap.parse_args()

    path = Path(args.path)
    if path.is_file():
        path = path.parent
    if not path.is_dir():
        print(f"[FAIL] 不是目录：{path}", file=sys.stderr)
        return 2

    sessions = collect(path, args.expect_n)
    if not sessions:
        print(f"[FAIL] {path} 下没有找到 `EXP_data_group<组>_<编号>.csv` 或 `exp_group<组>_subject<编号>.txt`。",
              file=sys.stderr)
        return 2

    counts = tally(sessions)
    md, ok = build(sessions, counts, args.expect_n)
    print(md)
    if args.out:
        Path(args.out).write_text(md + "\n", encoding="utf-8", newline="\n")
        print(f"\n[写盘] {args.out}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
