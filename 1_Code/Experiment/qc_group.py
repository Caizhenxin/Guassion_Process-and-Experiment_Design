#!/usr/bin/env python3
"""Stage 7 采集期「逐 P 组」数据质量快检。

主计划 §3 Stage 7 的原文要求：

    按定稿设计执行，遵守 Stage 1 的记录规范；
    **每完成一个 P 组就做一次数据质量快检**（不要等收完再查）。

Stage 6 的 `analyze_pilot.py` 面向「一份数据 / 一个目录」，回答的是
「这批数据还能不能用」；本脚本面向**整个采集期**，回答的是
「这 4 个 P 组各自收到什么程度、有没有被试要复核或剔除、
 组间可比性有没有被破坏」。两者分工：

    analyze_pilot.py  逐被试 / 整批的**技术判据**（S1-1 … S6-6）
    qc_group.py       逐 P 组的**进度 + 均衡 + 排除**（G1 … G10）

本脚本**不重新实现** Stage 6 的判据：每个被试的 S1/S6 裁决由
`analyze_pilot.py` 子进程给出（单一事实来源）。本脚本只负责
聚合、分组、以及与设计规格的对照。

用法
----
    python qc_group.py <采集目录> [--out 报告.md] [--json out.json]
                       [--flip 0.0166667] [--expect-n 40]
                       [--groups 1,2,3,4] [--final] [--no-subject-check]

`--expect-n` 默认 **40**（定稿设计 `正式采集_候选设计_v2_定稿.md`：4 组 × ~40 人 = 160 人，
另留 +20% 损耗 ⇒ 招募 192 人）。采集期内不要加 `--final`；收满后再加，让 G1 真正判定。

退出码
------
    0  没有任何「剔除」级问题（WARN 与「待复核」不影响退出码）
    1  存在「剔除」级问题（见下）

剔除 / 复核口径（**事前登记，采集中途不得改**）
----------------------------------------------
* **剔除**（数据不可用）：
  - Stage 6 的 **S6-3** FAIL —— `Response`/`RT`/`responded_by_deadline` 自相矛盾，
    说明按键被丢或被误记，该被试的按键数据不可信；
  - 正式段试次数 < 90% × 576 —— 提前退出，试次结构不完整。
* **待复核**（不自动剔除，需人工看过再定）：
  - Stage 6 的任何其它 FAIL；
  - 试次数不等于规格（正式 576 / 练习 P 或 4）；
  - 组内 timeout 比例 > 40%；
  - 该被试的帧长估计与组内中位数相差 > 2%。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import analyze_pilot as ap  # noqa: E402  （只借用纯函数：read_table/row_dicts/estimate_flip/统计量）

# --------------------------------------------------------------------------- #
# 设计规格（`正式采集_候选设计_v2_定稿.md` / D4）
# --------------------------------------------------------------------------- #
P_BY_GROUP = {1: 0, 2: 8, 3: 32, 4: 120}
T_LEVELS_S = (0.033330, 0.083330, 0.149990, 0.249980)
W_LEVELS_S = (0.799980, 1.199900, 1.799900)
N_BLOCK = 3
N_KINDS = 4
N_REP = 12
N_FORMAL = N_BLOCK * len(T_LEVELS_S) * N_KINDS * N_REP  # 576
N_PER_CELL = N_KINDS * N_REP                            # 48
V4_NCOL = ap.V4_NCOL

FNAME = re.compile(r"^exp_group(\d+)_subject(\d+)\.txt$")
VERDICT = re.compile(r"([\u2705\U0001F7E0\u274C\u00B7])\s*\[([^\]]+)\]\s*(.*)")
ICON_TO_STATUS = {"\u2705": "PASS", "\U0001F7E0": "WARN", "\u274C": "FAIL", "\u00B7": "INFO"}


# --------------------------------------------------------------------------- #
# 逐被试
# --------------------------------------------------------------------------- #
def run_subject_check(path: Path, flip: float | None) -> dict[str, str]:
    """调用 `analyze_pilot.py` 取该被试的逐条裁决。返回 {tag: status}。"""
    cmd = [sys.executable, str(HERE / "analyze_pilot.py"), str(path)]
    if flip:
        cmd += ["--flip", repr(flip)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    verdicts: dict[str, str] = {}
    for line in (proc.stdout or "").splitlines():
        m = VERDICT.search(line)
        if m and m.group(2).startswith(("S1-", "S6-")):
            verdicts[m.group(2)] = ICON_TO_STATUS[m.group(1)]
    return verdicts


def subject_metrics(path: Path, group: int, subject: int) -> dict:
    """读出该被试的原始行并算出 Stage 7 需要的量。"""
    header, rows_raw = ap.read_table(path)
    header = [h.strip().lstrip("\ufeff") for h in header]
    rows = ap.row_dicts(header, rows_raw)

    legacy = len(header) < V4_NCOL
    rec: dict = {
        "file": path.name, "group": group, "subject": subject,
        "legacy": legacy, "n_cols": len(header),
        "n_formal": 0, "n_practice": 0, "p_vals": set(),
        "timeout": [], "acc": [], "rt": [], "rt_lt_t": 0,
        "in_stim": 0, "anticip": 0, "per_cell": {}, "flip": None,
        "verdicts": {},
    }
    if legacy:
        return rec

    for r in rows:
        stage = (r.get("stage") or "").strip().strip('"')
        pv = ap._to_float(r.get("P", ""))
        if pv is not None:
            rec["p_vals"].add(int(round(pv)))
        if stage == "practice":
            rec["n_practice"] += 1
            continue
        if stage != "formal":
            continue
        rec["n_formal"] += 1
        T = ap._to_float(r.get("T", ""))
        W = ap._to_float(r.get("W", ""))
        if T is not None and W is not None:
            key = (round(T, 6), round(W, 6))
            rec["per_cell"][key] = rec["per_cell"].get(key, 0) + 1
        rt = ap._to_float(r.get("RT", ""))
        rec["timeout"].append(1 if (rt is None) else 0)
        c = ap._to_float(r.get("Correct", ""))
        if c is not None:
            rec["acc"].append(c)
        if rt is None or T is None:
            continue
        rec["rt"].append(rt)
        if rt < T:
            rec["rt_lt_t"] += 1
            if rt < 0.15:
                rec["anticip"] += 1
            else:
                rec["in_stim"] += 1

    rec["p_vals"] = sorted(rec["p_vals"])
    n_rt_ok = rec["n_formal"] - sum(rec["timeout"])
    rec["timeout_prop"] = (sum(rec["timeout"]) / rec["n_formal"]) if rec["n_formal"] else None
    rec["acc_mean"] = ap.mean(rec["acc"]) if rec["acc"] else None
    rec["rt_med"] = ap.median(rec["rt"]) if rec["rt"] else None
    rec["rt_lt_t_prop"] = (rec["rt_lt_t"] / n_rt_ok) if n_rt_ok else None
    rec["in_stim_prop"] = (rec["in_stim"] / n_rt_ok) if n_rt_ok else None
    rec["anticip_prop"] = (rec["anticip"] / n_rt_ok) if n_rt_ok else None
    rec["flip"] = ap.estimate_flip(rows)
    return rec


def classify(rec: dict, flip_group: float | None) -> tuple[str, list[str]]:
    """→ (KEEP | REVIEW | EXCLUDE, 理由列表)。口径见模块 docstring。"""
    reasons: list[str] = []
    if rec["legacy"]:
        return "EXCLUDE", [f"旧 {rec['n_cols']} 列文件（不是 v4/v4.1 格式）"]
    v = rec["verdicts"]
    if v.get("S6-3") == "FAIL":
        return "EXCLUDE", ["S6-3 FAIL：按键被丢或被误记"]
    if rec["n_formal"] < 0.9 * N_FORMAL:
        reasons.append(f"正式段只有 {rec['n_formal']}/{N_FORMAL} 试次（提前退出）")
        return "EXCLUDE", reasons
    for tag, st in sorted(v.items()):
        if st == "FAIL":
            reasons.append(f"{tag} FAIL")
    if rec["n_formal"] != N_FORMAL:
        reasons.append(f"正式段试次数 {rec['n_formal']} ≠ {N_FORMAL}")
    if rec["timeout_prop"] is not None and rec["timeout_prop"] > 0.40:
        reasons.append(f"timeout {rec['timeout_prop']:.1%} > 40%")
    if flip_group and rec["flip"]:
        ratio = abs(rec["flip"] - flip_group) / flip_group
        if ratio > 0.02:
            reasons.append(f"帧长估计 {rec['flip']*1000:.2f} ms 偏离组内中位数 > 2%")
    return ("REVIEW" if reasons else "KEEP"), reasons


# --------------------------------------------------------------------------- #
# 逐组
# --------------------------------------------------------------------------- #
def group_report(gid: int, recs: list[dict], expect_n: int, final: bool) -> dict:
    kept = [r for r in recs if r["class"] == "KEEP"]
    usable = [r for r in recs if r["class"] != "EXCLUDE"]      # KEEP + REVIEW
    v4 = [r for r in recs if not r["legacy"]]                  # 结构类判据看**全部** v4 记录
    flips = [r["flip"] for r in usable if r["flip"]]
    flip_med = ap.median(flips) if flips else None

    def agg(field: str, pool: list[dict]) -> float | None:
        xs = [r[field] for r in pool if r.get(field) is not None]
        return ap.mean(xs) if xs else None

    timeouts = [r["timeout_prop"] for r in usable if r["timeout_prop"] is not None]
    accs = [r["acc_mean"] for r in usable if r["acc_mean"] is not None]
    in_stims = [r["in_stim_prop"] for r in usable if r["in_stim_prop"] is not None]
    anticips = [r["anticip_prop"] for r in usable if r["anticip_prop"] is not None]
    cells_ok = bool(v4) and all(
        len(r["per_cell"]) == len(T_LEVELS_S) * len(W_LEVELS_S)
        and all(v == N_PER_CELL for v in r["per_cell"].values())
        for r in v4
    )

    crit: list[tuple[str, str, str]] = []
    p_expect = P_BY_GROUP.get(gid)

    # G1 进度
    n = len(usable)
    if n >= expect_n:
        crit.append(("G1", "PASS", f"可用被试 {n}/{expect_n}（剔除 {len(recs) - len(usable)}）"))
    else:
        st = "FAIL" if final else "INFO"
        crit.append(("G1", st, f"可用被试 {n}/{expect_n}（剔除 {len(recs) - len(usable)}）"
                               + ("" if final else "　—— 采集中，未达目标不算失败")))

    # G2 试次结构（看全部 v4 记录：被剔除的被试也要能看到结构问题）
    bad_n = [r for r in v4 if r["n_formal"] != N_FORMAL]
    crit.append(("G2", "FAIL" if not v4 else ("PASS" if not bad_n else "WARN"),
                 "无 v4 数据" if not v4 else
                 f"正式段 {N_FORMAL} 试次：{'全部合规' if not bad_n else f'{len(bad_n)} 名不符'}"))

    # G3 训练段试次数（= P，或 P=0 时兜底 4）
    if p_expect is None:
        crit.append(("G3", "INFO", "组号不在设计内，跳过练习段规格核对"))
    else:
        n_exp = p_expect if p_expect else 4
        bad_p = [r for r in v4 if r["n_practice"] != n_exp]
        crit.append(("G3", "FAIL" if not v4 else ("PASS" if not bad_p else "WARN"),
                     "无 v4 数据" if not v4 else
                     f"组 {gid}（P={p_expect}）练习段应为 {n_exp} 试次："
                     f"{'全部合规' if not bad_p else f'{len(bad_p)} 名不符'}"))

    # G4 每格试次数
    crit.append(("G4", "PASS" if cells_ok else "FAIL",
                 "无 v4 数据" if not v4 else
                 f"每 (T,W) 格 {N_PER_CELL} 试次 × {len(T_LEVELS_S)}×{len(W_LEVELS_S)} 格："
                 f"{'全部合规' if cells_ok else '有被试不符（T/W 列精度或试次生成有错）'}"))

    # G5 timeout
    t = agg("timeout_prop", usable)
    if t is None:
        crit.append(("G5", "INFO", "无可用数据"))
    else:
        st = "PASS" if t <= 0.20 else ("WARN" if t <= 0.40 else "FAIL")
        crit.append(("G5", st, f"组层 timeout {t:.1%}（判据 ≤ 20% 为 PASS）"))

    # G6 正确率
    a = agg("acc_mean", usable)
    if a is None:
        crit.append(("G6", "INFO", "无可用数据"))
    else:
        st = "PASS" if 0.55 <= a <= 0.98 else ("WARN" if 0.50 <= a <= 0.99 else "FAIL")
        crit.append(("G6", st, f"组层正确率 {a:.3f}（合理区间 0.55–0.98）"))

    # G7 刺激内完成累计（Stage 8 触发器）
    s = agg("in_stim_prop", usable)
    if s is None:
        crit.append(("G7", "INFO", "无可用数据"))
    else:
        st = "PASS" if s <= 0.20 else "WARN"
        crit.append(("G7", st, f"组层「刺激内完成累计」(0.15 s ≤ RT < T) {s:.2%}"
                               + ("　⇒ 无需时变输入模型" if st == "PASS"
                                  else "　⇒ **Stage 8 必须扩展为时变输入模型**")))

    # G8 P 值一致性（防 groupID 错配）
    if p_expect is None:
        crit.append(("G8", "INFO", "组号不在设计内"))
    else:
        seen = sorted({p for r in usable for p in r["p_vals"]})
        ok = seen == [p_expect]
        crit.append(("G8", "PASS" if ok else "FAIL",
                     f"数据里的 P 值 {seen} vs 设计 P={p_expect}"))

    # G9 帧长一致性
    if len(flips) >= 2:
        ratio = max(flips) / min(flips)
        crit.append(("G9", "PASS" if ratio <= 1.02 else "WARN",
                     f"帧长估计 {flip_med*1000:.3f} ms（跨被试 max/min = {ratio:.4f}）"))
    else:
        crit.append(("G9", "INFO", "可用被试不足，跳过帧长一致性"))

    return {
        "group": gid, "P": p_expect,
        "n_files": len(recs), "n_usable": len(usable), "n_kept": len(kept),
        "n_review": len([r for r in recs if r["class"] == "REVIEW"]),
        "n_exclude": len(recs) - len(usable),
        "timeout": t, "acc": a, "in_stim": s,
        "anticip": agg("anticip_prop", usable),
        "rt_med": agg("rt_med", usable),
        "rt_lt_t": agg("rt_lt_t_prop", usable),
        "flip": flip_med, "criteria": crit,
    }


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{x*100:.2f}%"


def fmt_num(x: float | None, nd: int = 3) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def main() -> int:
    ap_cli = argparse.ArgumentParser(description="Stage 7 逐 P 组采集质量快检")
    ap_cli.add_argument("datadir", help="采集目录（递归找 exp_group*_subject*.txt）")
    ap_cli.add_argument("--out", default=None, help="把 Markdown 报告写到该文件")
    ap_cli.add_argument("--json", dest="json_out", default=None, help="结构化结果写到该文件")
    ap_cli.add_argument("--flip", type=float, default=None,
                        help="显示器帧长（秒）；默认逐被试自估")
    ap_cli.add_argument("--expect-n", type=int, default=40,
                        help="每个 P 组的可用被试目标（定稿设计为 40/组；默认 40）")
    ap_cli.add_argument("--groups", default="1,2,3,4", help="要报告的组号，逗号分隔")
    ap_cli.add_argument("--final", action="store_true",
                        help="按「采集已结束」判定 G1：组人数不足即 FAIL")
    ap_cli.add_argument("--no-subject-check", action="store_true",
                        help="跳过逐被试调用 analyze_pilot.py（快，但拿不到 S1/S6 裁决）")
    args = ap_cli.parse_args()

    root = Path(args.datadir)
    if not root.is_dir():
        print(f"❌ 目录不存在：{root}")
        return 1
    want = {int(g) for g in args.groups.split(",") if g.strip()}

    found: list[tuple[int, int, Path]] = []
    for p in sorted(root.rglob("exp_group*_subject*.txt")):
        m = FNAME.match(p.name)
        if m:
            found.append((int(m.group(1)), int(m.group(2)), p))
    if not found:
        print(f"❌ 在 {root} 下没找到 exp_group*_subject*.txt")
        return 1

    lines: list[str] = []
    def out(s: str = "") -> None:
        print(s)
        lines.append(s)

    out(f"# Stage 7 采集质量快检（逐 P 组）")
    out()
    out(f"- 采集目录：`{root}`")
    out(f"- 数据文件：**{len(found)}** 个（组 {sorted({g for g, _, _ in found})}）")
    out(f"- 目标：每组 **{args.expect_n}** 名可用被试；"
        f"每人正式段 **{N_FORMAL}** 试次（{N_BLOCK} block × {len(T_LEVELS_S)} T × "
        f"{N_KINDS} 类 × {N_REP} 次）")
    out(f"- 模式：{'采集已结束（--final）' if args.final else '采集中'}；"
        f"逐被试 Stage 6 裁决：{'跳过' if args.no_subject_check else '启用'}")
    out()
    out("> 口径见 `1_Code/Experiment/qc_group.py` 模块文档；"
        "剔除 / 复核规则**事前登记，采集中途不得改**。")

    recs: list[dict] = []
    for gid, sid, path in found:
        r = subject_metrics(path, gid, sid)
        if not args.no_subject_check and not r["legacy"]:
            r["verdicts"] = run_subject_check(path, args.flip)
        recs.append(r)

    # 组内帧长中位数（用于 classify）
    for gid in sorted({r["group"] for r in recs}):
        pool = [r for r in recs if r["group"] == gid and r["flip"]]
        fm = ap.median([r["flip"] for r in pool]) if pool else None
        for r in recs:
            if r["group"] == gid:
                r["class"], r["reasons"] = classify(r, fm)

    groups = [group_report(g, [r for r in recs if r["group"] == g], args.expect_n, args.final)
              for g in sorted({r["group"] for r in recs}) if g in want]

    # ---- 组层总表 ---- #
    out()
    out("## 1. 各组汇总")
    out()
    out("| 组 | P | 文件 | 可用 | 剔除 | 待复核 | timeout | 正确率 | RT 中位 | `RT<T` | 其中刺激内 | 帧长(ms) |")
    out("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for g in groups:
        flip_ms = "—" if not g["flip"] else f"{g['flip'] * 1000:.3f}"
        out(f"| {g['group']} | {g['P']} | {g['n_files']} | {g['n_usable']} | {g['n_exclude']} | "
            f"{g['n_review']} | {fmt_pct(g['timeout'])} | {fmt_num(g['acc'])} | "
            f"{fmt_num(g['rt_med'])} | {fmt_pct(g['rt_lt_t'])} | {fmt_pct(g['in_stim'])} | "
            f"{flip_ms} |")

    # ---- 逐组判据 ---- #
    n_fail = n_warn = 0
    out()
    out("## 2. 逐组判据")
    for g in groups:
        out()
        out(f"### 组 {g['group']}（P = {g['P']}）")
        out()
        out("| ID | 结果 | 说明 |")
        out("|---|---|---|")
        icon = {"PASS": "✅", "WARN": "🟠", "FAIL": "❌", "INFO": "·"}
        for cid, st, detail in g["criteria"]:
            if st == "FAIL":
                n_fail += 1
            elif st == "WARN":
                n_warn += 1
            out(f"| {cid} | {icon[st]} {st} | {detail} |")

    # ---- 被试清单 ---- #
    out()
    out("## 3. 被试处置清单")
    out()
    out("| 组 | 被试 | 处置 | 依据 |")
    out("|---|---|---|---|")
    for r in sorted(recs, key=lambda x: (x["group"], x["subject"])):
        mark = {"KEEP": "✅ 保留", "REVIEW": "🟠 待复核", "EXCLUDE": "❌ 剔除"}[r["class"]]
        why = "；".join(r["reasons"]) if r["reasons"] else "—"
        out(f"| {r['group']} | {r['subject']} | {mark} | {why} |")

    # ---- 结论 ---- #
    excl = [r for r in recs if r["class"] == "EXCLUDE"]
    rev = [r for r in recs if r["class"] == "REVIEW"]
    out()
    out("## 4. 结论")
    out()
    out(f"- 剔除 **{len(excl)}** 名、待复核 **{len(rev)}** 名、"
        f"判据 FAIL {n_fail} 项 / WARN {n_warn} 项")
    if any(g["criteria"] and any(c[0] == "G7" and c[1] == "WARN" for c in g["criteria"]) for g in groups):
        out("- ⚠️ **有组的「刺激内完成累计」> 20% ⇒ Stage 8 必须按"
            "`Stage6_Pilot方案.md` §8 扩展为时变输入模型**")
    if n_fail or excl:
        out("- ❌ **存在剔除级问题**：先按上表复核，再决定是否补被试")
        rc = 1
    else:
        out("- ✅ 没有剔除级问题（WARN / 待复核见上表）")
        rc = 0

    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"\n报告已写到 {args.out}")
    if args.json_out:
        payload = {
            "datadir": str(root), "expect_n": args.expect_n, "final": bool(args.final),
            "n_formal_expected": N_FORMAL,
            "groups": groups,
            "subjects": [{k: v for k, v in r.items() if k != "per_cell"} for r in recs],
        }
        Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                                  default=str), encoding="utf-8")
        print(f"结构化结果已写到 {args.json_out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
