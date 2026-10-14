#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 6 Pilot 数据检查器 —— 把 `Exp_Design_Formal.m`（v4/v4.1，25 列）的输出直接判成结论。

对应 `5_Reference/08_工作流/工作流_主计划.md` §3 Stage 6：

    用定稿设计的小规模版本（N ≈ 5–8）；
    检查：实际 RT 分布、**RT < T 的比例**、timeout 比例、实际呈现时长、按键是否丢失；
    **RT < T 的比例是关键**：若较高，说明需要"时变输入"模型，Stage 8 要相应扩展。
    验收标准：Pilot 数据能通过 Stage 1 的技术验收，且行为量级合理。

用法
----
    python analyze_pilot.py <数据目录或文件...> [--flip 0.0166667] [--out 报告.txt]

不带参数时默认扫描本脚本所在目录下的 `exp_group*_subject*.txt`。

判据（全部事前登记在 `5_Reference/08_工作流/Stage6_Pilot方案.md`，此处即其实现）
--------------------------------------------------------------------------
    S1-1 时长精度：无抢按试次里 |stimulus_dur_actual − T| < 1 帧 的比例 ≥ 99%
    S6-1 timeout  ：整体 ≤ 20%，且最差 (T,W) 单元 ≤ 40%
    S6-2 RT < T   ：整体 ≤ 20% PASS；> 20% WARN —— 不是 FAIL，
                    因为它的作用是决定 Stage 8 要不要上时变输入模型，而不是"数据坏"
    S6-2c 真正驱动 Stage 8 的那一半：把 RT < T 拆成
                    ① 预期性（RT < 0.15 s，刺激刚上屏就按，短 T 下必然出现）
                    ② 刺激内完成累计（0.15 s ≤ RT < T）
                    只有 ② 的比例 > 20% 才要求 Stage 8 扩展为时变输入模型
                    （⚠ 短 T 下 RT < T ⇔ RT < 0.15 s，不拆分就会把"短 T 多"误读成"需要时变模型"）
    S6-3 一致性   ：Response 与 RT / responded_by_deadline 自相矛盾的行 = 0
    S6-4 设计完整 ：正式段 4 个 T × 3 个 W 全部出现，且每格试次数 = 4 类 × 12 = 48
    S6-5 行为量级 ：正确率 0.55–0.98；RT 中位数 0.3–2.0 s；
                    RT < 0.15 s 的比例 ≤ 10%（**口径：只在 RT ≥ T 的试次里算**）
    S6-6 注视期   ：premature_press 比例 ≤ 10%

任一 FAIL → 退出码 1（WARN 不影响退出码）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V1_NCOL = 16
V4_NCOL = 25

# 定稿设计（D4）的名义水平；仅用于"数据里到底出现没出现这几档"的对照报告，
# 真正的帧长从数据本身估计（见 estimate_flip），所以在 60/100/144 Hz 上都成立。
T_NOMINAL_MS = [33.33, 83.33, 149.99, 249.98]
W_NOMINAL_MS = [799.98, 1199.9, 1799.9]
N_STIM_KINDS = 4
N_REP = 12            # 每个 (T,W) 单元每类刺激重复次数
TRIALS_PER_CELL = N_STIM_KINDS * N_REP   # 48

MISSING = {"", "na", "nan", "n/a", "-", "[]"}


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #
def _to_float(tok: str) -> float | None:
    """容错解析：MATLAB 用 `%d`/`%.3f` 打印 NaN 时会写出 'NaN'，未响应写 'NA'。"""
    t = tok.strip()
    if t.lower() in MISSING:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    if v != v:  # NaN
        return None
    return v


def read_table(path: Path) -> tuple[list[str], list[list[str]]]:
    """读一个 tab 分隔的数据文件，返回 (表头, 数据行)。表头缺失时用列号当名字。

    ⚠️ 用 `utf-8-sig` 读：数据可能被 Excel / 记事本 / PowerShell 重存过而带上 UTF-8 BOM。
    不剥 BOM 时 `rows[0][0] == "\\ufeffgroupID"`，这里的表头识别会失败 ⇒ 全部列名退化成
    `col1..col25`，下游把"正式段试次数"读成 **0**（**不报错，只是所有计数变成 0**）。
    """
    raw = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    rows = [ln.rstrip("\n").split("\t") for ln in raw if ln.strip()]
    if not rows:
        return [], []
    head = [c.strip().lstrip("\ufeff") for c in rows[0]]
    # 表头识别：第一行里出现 groupID 即认为是表头（容忍前置空列 / BOM 残留）
    if any(c == "groupID" for c in head[:3]):
        return head, rows[1:]
    return [f"col{i}" for i in range(1, len(rows[0]) + 1)], rows


def row_dicts(header: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    out = []
    for r in rows:
        if len(r) < V1_NCOL:
            continue
        d = {h: (r[i] if i < len(r) else "") for i, h in enumerate(header)}
        d["_ncol"] = str(len(r))
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# 统计小工具（不引入 numpy/pandas，保持零依赖）
# --------------------------------------------------------------------------- #
def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def quantile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def median(xs: list[float]) -> float:
    return quantile(xs, 0.5)


def estimate_flip(rows: list[dict]) -> float:
    """从数据本身估计一帧的秒数：无抢按试次里 round(dur/flip)*flip == dur ⇒ dur/frames = flip。"""
    ratios = []
    for d in rows:
        dur, fr = _to_float(d.get("stimulus_dur_actual", "")), _to_float(d.get("stimulus_frames", ""))
        if dur and fr and fr >= 4:
            ratios.append(dur / fr)
    if ratios:
        return median(ratios)
    return 1.0 / 60.0


# --------------------------------------------------------------------------- #
# 判据
# --------------------------------------------------------------------------- #
class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.fails: list[str] = []
        self.warns: list[str] = []

    def out(self, s: str = "") -> None:
        print(s)
        self.lines.append(s)

    def verdict(self, tag: str, status: str, detail: str) -> None:
        icon = {"PASS": "✅", "WARN": "🟠", "FAIL": "❌", "INFO": "·"}[status]
        self.out(f"  {icon} [{tag}] {detail}")
        if status == "FAIL":
            self.fails.append(f"{tag}: {detail}")
        elif status == "WARN":
            self.warns.append(f"{tag}: {detail}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 6 Pilot 数据检查（25 列 v4/v4.1 格式）")
    ap.add_argument("paths", nargs="*", help="数据文件或目录（默认：脚本所在目录）")
    ap.add_argument("--flip", type=float, default=None, help="显示器帧长（秒）；默认从数据估计")
    ap.add_argument("--out", default=None, help="同时把报告写到该文件")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    targets: list[Path] = []
    if args.paths:
        for p in args.paths:
            p = Path(p)
            if p.is_dir():
                targets += sorted(p.glob("exp_group*_subject*.txt"))
            elif p.exists():
                targets.append(p)
    else:
        targets += sorted(here.glob("exp_group*_subject*.txt"))
    # 去掉同名重复
    seen: set[str] = set()
    targets = [t for t in targets if not (t.name in seen or seen.add(t.name))]

    rep = Report()
    rep.out("=" * 78)
    rep.out("Stage 6 Pilot 数据检查（判据见 5_Reference/08_工作流/Stage6_Pilot方案.md）")
    rep.out("=" * 78)
    if not targets:
        rep.out(f"❌ 没找到任何 exp_group*_subject*.txt（查找目录：{here}）")
        return 1
    rep.out(f"数据文件 {len(targets)} 个：")
    for t in targets:
        rep.out(f"   · {t.name}")

    # ---- 版本分流：16 列是旧版，不能做 Stage 1 时间戳检查 ---- #
    v4_files, v1_files = [], []
    all_rows: list[dict] = []
    for t in targets:
        header, data = read_table(t)
        if len(header) >= V4_NCOL:
            v4_files.append(t)
            all_rows += row_dicts(header, data)
        else:
            v1_files.append(t)
    if v1_files:
        rep.out("")
        rep.out(f"⚠ 跳过 {len(v1_files)} 个旧版（{V1_NCOL} 列，无 Stage 1 时间戳列）文件："
                + "、".join(t.name for t in v1_files))
        rep.out("  旧文件仍能看行为量级，但无法验收 Stage 1；请用 v4/v4.1 程序重采。")
    if not v4_files:
        rep.out("")
        rep.out(f"❌ 没有任何 25 列（v4/v4.1）数据文件，无法执行 Stage 6 检查。")
        return 1

    formal = [d for d in all_rows if d.get("stage", "").strip().strip('"') == "formal"]
    practice = [d for d in all_rows if d.get("stage", "").strip().strip('"') == "practice"]
    rep.out("")
    rep.out(f"试次：正式 {len(formal)}、练习 {len(practice)}（合计 {len(all_rows)}）")
    subjects = sorted({(d.get("groupID", "?"), d.get("subjectID", "?")) for d in all_rows})
    rep.out(f"被试：{len(subjects)} 名 —— " + "、".join(f"组{g}-{s}" for g, s in subjects))
    if not formal:
        rep.out("❌ 没有正式段试次。")
        return 1

    flip = args.flip if args.flip else estimate_flip(formal)
    rep.out(f"帧长：{'给定' if args.flip else '从数据估计'} = {flip * 1000:.3f} ms"
            f"（≈ {1 / flip:.1f} Hz）")

    # ===================================================================== #
    # S1-1 实际呈现时长
    # ===================================================================== #
    rep.out("")
    rep.out("── Stage 1 技术验收 ──")
    ok = bad = 0
    worst = (0.0, None)
    pressed_in_stim = 0
    dur_vs_rt_violation = 0
    for d in formal + practice:
        T = _to_float(d.get("T", ""))
        dur = _to_float(d.get("stimulus_dur_actual", ""))
        if T is None or dur is None:
            continue
        if dur < T - 0.5 * flip:            # D5：刺激期内按键 ⇒ 刺激被提前结束
            pressed_in_stim += 1
            rt = _to_float(d.get("RT", ""))
            if rt is not None and dur + 1.5 * flip < rt:
                dur_vs_rt_violation += 1
            continue
        err = abs(dur - T)
        if err < flip:
            ok += 1
        else:
            bad += 1
            if err > worst[0]:
                worst = (err, d)
    tot = ok + bad
    rate = ok / tot if tot else float("nan")
    if tot == 0:
        rep.verdict("S1-1", "FAIL", "找不到任何未被提前结束的试次，无法核对时长")
    else:
        detail = (f"无抢按试次 {tot} 个，|实际时长 − T| < 1 帧（{flip * 1000:.2f} ms）的占 "
                  f"{rate:.2%}（判据 ≥ 99%）")
        if worst[1] is not None:
            detail += f"；最大偏离 {worst[0] * 1000:.2f} ms"
        rep.verdict("S1-1", "PASS" if rate >= 0.99 else "FAIL", detail)
    rep.verdict("S1-1b", "INFO",
                f"刺激期内按键（刺激被提前结束）{pressed_in_stim} 个试次；"
                f"其中「实际时长 < RT」的矛盾行 {dur_vs_rt_violation} 个（应 ≈ 0）")
    if dur_vs_rt_violation > 0:
        rep.verdict("S1-1b", "FAIL", f"有 {dur_vs_rt_violation} 行 stimulus_offset_actual 早于按键时刻")

    # ===================================================================== #
    # S6-4 设计完整性（先做，因为后面的分格统计依赖它）
    # ===================================================================== #
    rep.out("")
    rep.out("── Stage 6 行为检查 ──")
    t_levels = sorted({_to_float(d["T"]) for d in formal if _to_float(d.get("T", "")) is not None})
    w_levels = sorted({_to_float(d["W"]) for d in formal if _to_float(d.get("W", "")) is not None})
    rep.out("  T 档：" + "、".join(f"{v * 1000:.2f} ms" for v in t_levels))
    rep.out("  W 档：" + "、".join(f"{v * 1000:.2f} ms" for v in w_levels))
    if len(t_levels) < len(T_NOMINAL_MS):
        rep.verdict("S6-4", "FAIL",
                    f"正式段只出现 {len(t_levels)} 档 T（设计 4 档）⇒ T 列精度不足或试次生成有问题"
                    "（v4.1 前的 %.1f 缺陷就会造成这个现象）")
    elif len(w_levels) < len(W_NOMINAL_MS):
        rep.verdict("S6-4", "FAIL", f"正式段只出现 {len(w_levels)} 档 W（设计 3 档）")
    else:
        cells: dict[tuple, int] = {}
        for d in formal:
            key = (_to_float(d.get("T", "")), _to_float(d.get("W", "")))
            cells[key] = cells.get(key, 0) + 1
        n_subj = max(1, len(subjects))
        expect = TRIALS_PER_CELL * n_subj
        off = {k: v for k, v in cells.items() if v != expect}
        if off:
            rep.verdict("S6-4", "WARN",
                        f"12 个 (T,W) 单元中 {len(off)} 个的试次数 ≠ {expect}"
                        f"（{n_subj} 名被试 × {TRIALS_PER_CELL}）")
        else:
            rep.verdict("S6-4", "PASS",
                        f"12 个 (T,W) 单元齐全，每格 {expect} 试次（{n_subj} 人 × {TRIALS_PER_CELL}）")

    # ===================================================================== #
    # RT < T（关键项）
    # ===================================================================== #
    rt_lt_t = 0
    rt_ok = 0
    anticip = 0      # RT < 0.15 s：刺激刚上屏就按，属预期性/抢按
    in_stim = 0      # 0.15 s ≤ RT < T：刺激内完成累计 —— 只有这一部分需要时变输入模型
    by_T: dict[float, list[int]] = {}
    for d in formal:
        T, rt = _to_float(d.get("T", "")), _to_float(d.get("RT", ""))
        if T is None or rt is None:
            continue
        rt_ok += 1
        hit = 1 if rt < T else 0
        rt_lt_t += hit
        if hit:
            if rt < 0.15:
                anticip += 1
            else:
                in_stim += 1
        by_T.setdefault(T, [0, 0])
        by_T[T][0] += hit
        by_T[T][1] += 1
    prop = rt_lt_t / rt_ok if rt_ok else float("nan")
    prop_real = in_stim / rt_ok if rt_ok else float("nan")
    if rt_ok == 0:
        rep.verdict("S6-2", "FAIL", "没有任何有效 RT，无法评估 RT < T")
    else:
        st = "PASS" if prop <= 0.20 else "WARN"
        rep.verdict("S6-2", st,
                    f"**RT < T 比例 = {prop:.2%}**（{rt_lt_t}/{rt_ok}；判据 ≤ 20% 为 PASS）"
                    f"　拆成两半：预期性 RT<0.15 s = {anticip / rt_ok:.2%}、"
                    f"刺激内累计 0.15 s ≤ RT < T = {prop_real:.2%}")
        for T in sorted(by_T):
            h, n = by_T[T]
            rep.out(f"       T = {T * 1000:7.2f} ms：{h / n:6.2%}（{h}/{n}）")
        # ⚠ 短 T 下"RT < T"必然也 < 0.15 s：T=2 帧(33 ms) 时 RT<T ⇔ RT<33 ms，
        #   这在行为上是预期性按键，不是"证据在刺激内累计完"。真正要看的是
        #   【足够长的 T 上还能不能在被截断前累积完】——用 0.15 s ≤ RT < T 这一半来判。
        st_real = "PASS" if prop_real <= 0.20 else "WARN"
        rep.verdict("S6-2c", st_real,
                    f"**驱动 Stage 8 的那一半 = {prop_real:.2%}**（0.15 s ≤ RT < T；判据 ≤ 20%）"
                    + ("⇒ 需要「时变输入」模型，Stage 8 必须相应扩展" if prop_real > 0.20
                       else "⇒ 无需时变输入模型，Stage 8 按现计划做"))
        if prop_real > 0.20:
            rep.warns.append("Stage 8 需扩展为时变输入模型（0.15s ≤ RT < T 比例 > 20%）")

    # 交叉核对：用 stimulus_frames 独立判一次"刺激被提前结束"
    xcheck = agree = 0
    for d in formal:
        T, fr = _to_float(d.get("T", "")), _to_float(d.get("stimulus_frames", ""))
        if T is None or fr is None:
            continue
        xcheck += 1
        if round(T / flip) - fr >= 1:
            agree += 1
    if xcheck:
        rep.verdict("S6-2b", "INFO",
                    f"独立口径核对：按 stimulus_frames 判「刺激被提前结束」占 {agree / xcheck:.2%}"
                    f"（对应 stimulus_dur_actual 口径的 {pressed_in_stim / xcheck:.2%}）")

    # ===================================================================== #
    # S6-1 timeout / S6-6 premature_press
    # ===================================================================== #
    to_overall = [d for d in formal if _to_float(d.get("timeout", "")) == 1]
    p_to = len(to_overall) / len(formal)
    cells_to: dict[tuple, list[int]] = {}
    for d in formal:
        key = (_to_float(d.get("T", "")), _to_float(d.get("W", "")))
        c = cells_to.setdefault(key, [0, 0])
        c[1] += 1
        if _to_float(d.get("timeout", "")) == 1:
            c[0] += 1
    worst_cell = max(((v[0] / v[1], k) for k, v in cells_to.items() if v[1]), default=(0.0, None))
    st = "PASS" if (p_to <= 0.20 and worst_cell[0] <= 0.40) else "FAIL"
    rep.verdict("S6-1", st,
                f"timeout 整体 {p_to:.2%}（判据 ≤ 20%）；最差单元 T={worst_cell[1][0] * 1000:.2f} ms"
                f"/W={worst_cell[1][1] * 1000:.0f} ms 处 {worst_cell[0]:.2%}（判据 ≤ 40%）"
                if worst_cell[1] else f"timeout 整体 {p_to:.2%}（判据 ≤ 20%）")
    rep.out("       timeout 按 (T,W) 单元：")
    for k in sorted(cells_to):
        h, n = cells_to[k]
        rep.out(f"         T={k[0] * 1000:7.2f} ms  W={k[1] * 1000:6.0f} ms : {h / n:6.1%}（{h}/{n}）")

    n_pre = sum(1 for d in formal if _to_float(d.get("premature_press", "")) == 1)
    p_pre = n_pre / len(formal)
    rep.verdict("S6-6", "PASS" if p_pre <= 0.10 else "WARN",
                f"注视期抢按 {p_pre:.2%}（{n_pre}/{len(formal)}；判据 ≤ 10%）")

    # ===================================================================== #
    # S6-3 一致性 / 按键丢失
    # ===================================================================== #
    bad_rows = []
    for d in formal:
        resp = d.get("Response", "").strip().strip('"')
        rt = _to_float(d.get("RT", ""))
        rbd = _to_float(d.get("responded_by_deadline", ""))
        has_resp = resp.lower() not in MISSING
        if has_resp and rt is None:
            bad_rows.append(("有按键但 RT 缺失", d))
        elif (not has_resp) and rt is not None:
            bad_rows.append(("无按键但 RT 存在", d))
        elif rbd is not None and bool(rbd) != has_resp:
            bad_rows.append(("responded_by_deadline 与 Response 不一致", d))
    if bad_rows:
        rep.verdict("S6-3", "FAIL", f"{len(bad_rows)} 行 Response/RT/responded_by_deadline 自相矛盾")
        for why, d in bad_rows[:5]:
            rep.out(f"       例：组{d.get('groupID')}-{d.get('subjectID')} trial{d.get('trialID')}"
                    f" stage={d.get('stage')} Response={d.get('Response')} RT={d.get('RT')} —— {why}")
    else:
        rep.verdict("S6-3", "PASS",
                    f"{len(formal)} 个正式试次里 Response / RT / responded_by_deadline 全部自洽"
                    "（无按键丢失或误记）")

    # ===================================================================== #
    # S6-5 行为量级
    # ===================================================================== #
    rts = [_to_float(d["RT"]) for d in formal if _to_float(d.get("RT", "")) is not None]
    corr = [_to_float(d["Correct"]) for d in formal if _to_float(d.get("Correct", "")) is not None]
    acc = mean(corr) if corr else float("nan")
    # ⚠ 过快只在「刺激已结束才按」的试次（RT ≥ T）里算：短 T 下 RT < T 必然也 < 0.15 s，
    #   那是预期性按键，已由 S6-2/S1-1b 统计，重复计入会把「短 T 多」误报成「被试乱按」。
    rts_post = [_to_float(d["RT"]) for d in formal
                if _to_float(d.get("RT", "")) is not None
                and _to_float(d.get("T", "")) is not None
                and _to_float(d["RT"]) >= _to_float(d["T"])]
    too_fast = (sum(1 for r in rts_post if r < 0.15) / len(rts_post)) if rts_post else float("nan")
    rep.out("")
    rep.out("  RT 分布（正式段，已响应试次）：")
    if rts:
        rep.out(f"       n={len(rts)}  均值 {mean(rts):.3f} s  SD {sd(rts):.3f} s")
        rep.out(f"       分位 q10/25/50/75/90 = "
                + " / ".join(f"{quantile(rts, q):.3f}" for q in (0.10, 0.25, 0.50, 0.75, 0.90)))
        rep.out("       RT 按 T：")
        for T in sorted({_to_float(d["T"]) for d in formal
                         if _to_float(d.get("T", "")) is not None and _to_float(d.get("RT", "")) is not None}):
            sub = [_to_float(d["RT"]) for d in formal
                   if _to_float(d.get("T", "")) == T and _to_float(d.get("RT", "")) is not None]
            rep.out(f"         T={T * 1000:7.2f} ms : n={len(sub):4d}  中位 {median(sub):.3f} s"
                    f"  SD {sd(sub):.3f} s")
        rep.out("       正确率按 T：")
        for T in sorted({_to_float(d["T"]) for d in formal if _to_float(d.get("T", "")) is not None}):
            sub = [_to_float(d["Correct"]) for d in formal
                   if _to_float(d.get("T", "")) == T and _to_float(d.get("Correct", "")) is not None]
            rep.out(f"         T={T * 1000:7.2f} ms : n={len(sub):4d}  {mean(sub):.3f}")
    else:
        rep.out("       （无有效 RT）")

    problems5 = []
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

    # ===================================================================== #
    rep.out("")
    rep.out("=" * 78)
    if rep.fails:
        rep.out(f"❌ Stage 6 未通过：{len(rep.fails)} 项 FAIL、{len(rep.warns)} 项 WARN")
        for f in rep.fails:
            rep.out(f"   - {f}")
    else:
        rep.out(f"✅ Stage 6 检查通过（{len(rep.warns)} 项 WARN）")
    for w in rep.warns:
        rep.out(f"   🟠 {w}")
    rep.out("=" * 78)

    if args.out:
        Path(args.out).write_text("\n".join(rep.lines) + "\n", encoding="utf-8")
        print(f"报告已写入 {args.out}")
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main())
