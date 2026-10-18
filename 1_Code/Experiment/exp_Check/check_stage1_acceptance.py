#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 1 实机验收的**机器判据**：吃一份（或几份）v4.1 逐被试 txt，逐条给出通过/未通过。

为什么要有这个文件
------------------
`5_Reference/08_工作流/Stage1_技术验证记录.md` §6 的四张表（6-A…6-D）是空的 ——
它是 Stage 1 是否算"完成"的唯一判据，但验收方式原本是"人眼比对数字"。
人眼比对的后果是这个仓里已经出现过的：**判据写了、但没人真的去核**。
本脚本把能自动化的 6-B/6-C/6-D 变成可复现的检查；6-A 依赖 MATLAB 命令行回显，
留给人看（脚本会显式声明"本项无法从 txt 判断"）。

判据来源（逐条对齐 `Stage1_技术验证记录.md` §6）
-------------------------------------------------
* **6-B**：刺激期内按键要真的被记下来（`T = 33.33 ms` 单元里至少 1 例
  `RT < 0.0333` 且 `Response` 非 `NA`）；抢按记 `premature_press = 1`；
  掩蔽期按键落在 `T ~ T+200 ms`；`timeout` 与 `responded_by_deadline` 互补。
* **6-C**（核心）：对**没有**刺激期内按键的行（`RT` 为 NaN 或 `RT > T`）：
  `|stimulus_dur_actual − T| < FlipIntv`、`stimulus_frames == round(T/FlipIntv)`、
  `stimulus_offset_actual == mask_onset_actual`、
  `mask_onset_actual == stimulus_onset_actual + stimulus_dur_actual`。
* **6-D**：表头 25 列与 `read_formal_data.HEADER25` 逐字一致；漏答行
  `Response == NA`、`Correct == NaN`、`timeout == 1`、`responded_by_deadline == 0`；
  有反应行 `RT` 有限、`Correct ∈ {0,1}`；练习行 `block == 0`、正式行 `block ∈ {1,2,3}`；
  文件里没有 `0x00` 字节。

用法
----
    python -X utf8 1_Code/Experiment/exp_Check/check_stage1_acceptance.py <txt...>
    python -X utf8 1_Code/Experiment/exp_Check/check_stage1_acceptance.py --self-test

D81（2026-10-18，用主试 165 Hz 实机产物回放发现）：本检查器原先有 4 处判据只在
60 Hz 上成立 —— FlipIntv 用 `T/stimulus_frames` 反推（高刷屏低估 4%）、
`stimulus_frames` 拿名义 T 去比（程序写的是**实际时长**的帧数）、
`mask−onset−dur` 用 1e-6 容差（实测正好 ±1e-6 的浮点尘土）、6-B 的最小 T 档写死 2/60。
四处合起来把 165 Hz 实机上的**正常行**判成缺陷。已全部修正。

退出码：0 = 全部强制项通过；1 = 有强制项未通过；2 = 输入不可用（找不到/读不了）。
`--self-test` 用 `_scratch/make_fake_pilot.py` 造"干净 / 帧量化缺陷 / 缺值与响应矛盾"
三套数据，验证本检查器**既能放行也能拦住**（只放行不拦住的检查器等于没检查）。
"""
from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
EXP_DIR = HERE.parent
sys.path.insert(0, str(EXP_DIR))

import read_formal_data as RF                                  # noqa: E402

#: 掩蔽期的名义长度（秒）：`Exp_Design_Formal.m` v4.1 的 `mask_dur = 0.2`
MASK_WIN = 0.2
#: `T` 的最小档（2 帧 @60 Hz）—— 6-B 要求"这一档里也能记到刺激期内按键"
T_MIN = 2.0 / 60.0
TOL = 1e-9


def num(s: str) -> float:
    """把 MATLAB 写出的数值串转成 float；`NaN`/空/`NA` ⇒ nan。"""
    s = (s or "").strip()
    if s in ("", "NA", "NaN", "nan"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


class Report:
    """收集每条判据的结果，最后统一打印与给退出码。"""

    def __init__(self, files: list[Path]):
        self.files = files
        self.items: list[tuple[str, bool, str, bool]] = []   # (节, 通过?, 明细, 是否强制)

    def add(self, section: str, ok: bool, detail: str, mandatory: bool = True):
        self.items.append((section, bool(ok), detail, mandatory))

    def info(self, section: str, detail: str):
        self.items.append((section, True, detail, False))

    def ok(self) -> bool:
        return all(ok for _, ok, _, mand in self.items if mand)

    def fails(self) -> list[str]:
        return [f"{s}｜{d}" for s, ok, d, mand in self.items if mand and not ok]

    def render(self) -> str:
        out = [f"文件：{', '.join(p.name for p in self.files)}"]
        cur = None
        for section, ok, detail, mand in self.items:
            if section != cur:
                out.append("")
                out.append(f"[{section}]")
                cur = section
            mark = "✅" if ok else ("❌" if mand else "⚠️")
            tag = "" if mand else "（信息项）"
            out.append(f"  {mark} {detail}{tag}")
        out.append("")
        if self.ok():
            out.append("✅ **强制项全部通过**")
        else:
            out.append("❌ **有强制项未通过**：")
            for f in self.fails():
                out.append(f"    - {f}")
        return "\n".join(out)


def sniff_delimiter(header_line: str) -> str:
    """按首行嗅探分隔符：有制表符按 txt 处理，否则若含逗号按 CSV 处理。

    MATLAB 侧两条通道并存：逐试次 `fopen` 写的是 **制表符** txt，
    `cell2table` 快照写的是 **逗号** CSV。检查器两种都必须吃（D83）。
    """
    if "\t" in header_line:
        return "\t"
    if "," in header_line:
        return ","
    return "\t"


def split_line(line: str, delim: str) -> list[str]:
    if delim == ",":
        return next(csv.reader([line]))
    return line.split(delim)


def load_rows(path: Path) -> tuple[list[str], list[dict], bytes]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    delim = sniff_delimiter(lines[0])
    header = split_line(lines[0], delim)
    rows = []
    for ln in lines[1:]:
        cells = split_line(ln, delim)
        row = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(header)}
        rows.append(row)
    return header, rows, raw


def dedupe(rows: list[dict]) -> tuple[list[dict], int]:
    """按 `trialID` 去重，**保留最后一次**出现的行；返回 (去重后, 丢弃行数)。

    D81b：txt 通道是 `fopen(...,'a+')` 追加打开的，主试崩溃后重跑会往同一个文件
    继续写同一批 `trialID`。CSV（`cell2table` 快照）只保留最后一次运行，两者行数
    不一致时以 CSV 为准。顺序稳定的字典保序 ⇒ 去重后行序不变。
    """
    last: dict[str, int] = {}
    for i, r in enumerate(rows):
        tid = (r.get("trialID") or "").strip()
        if tid:
            last[tid] = i
    keep = set(last.values())
    out = [r for i, r in enumerate(rows) if i in keep]
    return out, len(rows) - len(out)


def check_6d(rep: Report, header: list[str], rows: list[dict], raw: bytes):
    rep.add("6-D 输出列与缺失值", header == list(RF.HEADER25),
            f"表头 25 列与 `HEADER25` 逐字一致（实得 {len(header)} 列）")
    if header != list(RF.HEADER25):
        miss = [c for c in RF.HEADER25 if c not in header]
        extra = [c for c in header if c not in RF.HEADER25]
        if miss:
            rep.add("6-D 输出列与缺失值", False, f"缺列：{miss}")
        if extra:
            rep.add("6-D 输出列与缺失值", False, f"多列：{extra}")

    bad_na, bad_resp, bad_block = [], [], []
    for i, r in enumerate(rows, start=2):
        resp = (r.get("Response") or "").strip()
        rt = num(r.get("RT"))
        correct = num(r.get("Correct"))
        timeout = num(r.get("timeout"))
        rbd = num(r.get("responded_by_deadline"))
        block = num(r.get("block"))
        stage = (r.get("stage") or "").strip()
        if not (timeout + rbd == 1.0):
            bad_na.append(f"L{i} timeout={timeout:g}+responded_by_deadline={rbd:g}≠1")
        if resp == "NA":
            if not math.isnan(rt):
                bad_na.append(f"L{i} Response=NA 但 RT={rt:g}")
            if not math.isnan(correct):
                bad_na.append(f"L{i} Response=NA 但 Correct={correct:g}")
            if not (timeout == 1.0 and rbd == 0.0):
                bad_na.append(f"L{i} 漏答行 timeout/responded_by_deadline 不是 1/0")
        else:
            if math.isnan(rt):
                bad_resp.append(f"L{i} Response={resp} 但 RT 缺失")
            if correct not in (0.0, 1.0):
                bad_resp.append(f"L{i} Correct={correct:g} 不在 {{0,1}}")
        if stage == "practice" and block != 0.0:
            bad_block.append(f"L{i} 练习行 block={block:g}")
        elif stage == "formal" and block not in (1.0, 2.0, 3.0):
            bad_block.append(f"L{i} 正式行 block={block:g}")
    rep.add("6-D 输出列与缺失值", not bad_na,
            "漏答行是 NA/NaN、timeout 与 responded_by_deadline 互补"
            + ("" if not bad_na else f"（{len(bad_na)} 处：{bad_na[:3]}）"))
    rep.add("6-D 输出列与缺失值", not bad_resp,
            "有反应行 RT 有限、Correct ∈ {0,1}"
            + ("" if not bad_resp else f"（{len(bad_resp)} 处：{bad_resp[:3]}）"))
    rep.add("6-D 输出列与缺失值", not bad_block,
            "练习行 block = 0、正式行 block ∈ {1,2,3}"
            + ("" if not bad_block else f"（{len(bad_block)} 处：{bad_block[:3]}）"))
    rep.add("6-D 输出列与缺失值", b"\x00" not in raw, "文件里没有 0x00 字节")


# 实验室机刷新率（设计文档 §1 的帧量化表就是按它算的：60.004 Hz / 16.6656 ms）
EXPECT_HZ = 60.004


def estimate_flip(rows: list[dict]) -> float:
    """由 `stimulus_dur_actual / stimulus_frames` 的中位数反推 FlipIntv。

    ⚠️ D81：不能用 `T / stimulus_frames`。程序第 25 列写的是
    `round(stimulus_dur_actual / FlipIntv)`（**实际**时长的帧数，含 0~1 帧 vsync
    余量），不是名义 T 的帧数。用 `T / frames` 反推会系统性低估 FlipIntv
    （165 Hz 实机：算出 5.83 ms，真值 6.06 ms，低 4%），进而把正常行判成缺陷。

    ⚠️ D87：也不能用 `median(dur / frames)`（D81 的写法）。dur 比名义时长多
    0~1 帧，这个余量被整份摊进一帧里，T 越小抬得越狠：60.004 Hz 实机实测
    中位 17.02 ms（真值 16.666 ms，偏 +2.1%）⇒ 读成 58.7 Hz，于是
    ① 6-C 的 `frames == round(dur/flip)` 把 1 行正常数据判成缺陷；
    ② 环境门把这块真·60.004 Hz 的屏判成「证据降级」。
    改为**解约束**（见下），不再依赖任何单一比值。
    """
    pts: list[tuple[float, int]] = []
    for r in rows:
        dur = num(r.get("stimulus_dur_actual"))
        fr = num(r.get("stimulus_frames"))
        if dur > 0 and fr >= 1 and math.isfinite(fr):
            pts.append((dur * 1000.0, int(round(fr))))
    if not pts:
        return float("nan")
    # 网格搜索：真值必须让尽可能多的行满足 round(dur/flip) == frames。
    # 步长 0.01 ms（对 16.67 ms 是 0.06%），搜索区间 5~25 ms 覆盖 40~200 Hz。
    best_n: int = -1
    best: list[float] = []
    flip_ms = 5.0
    while flip_ms <= 25.0 + 1e-9:
        n = sum(1 for d, f in pts if round(d / flip_ms) == f)
        if n > best_n:
            best_n, best = n, [flip_ms]
        elif n == best_n:
            best.append(flip_ms)
        flip_ms = round(flip_ms + 0.01, 4)
    return (best[0] + best[-1]) / 2.0 / 1000.0


def check_refresh_rate(rep: Report, flip: float, expect_hz: float) -> bool:
    """D81c：数据是否来自实验室那块 60.004 Hz 的屏。

    返回 True 表示"可以作为 Stage 1 帧量化证据"。不需要反推得准到小数点后三位——
    60.004 Hz 与 59.94/60.00/59.95 的差别都在 1% 以内，而临时环境的 165 Hz 差 175%。
    """
    if not (flip and math.isfinite(flip) and flip > 0):
        rep.info("环境门（D81c）", "反推不出刷新率，无法判断这块屏是不是实验室那块")
        return False
    hz = 1.0 / flip
    tol = max(1.0, 0.01 * expect_hz)
    if abs(hz - expect_hz) <= tol:
        rep.info("环境门（D81c）", f"刷新率 {hz:.3f} Hz 与实验室口径 {expect_hz:.3f} Hz 相符"
                                   f"（±{tol:.2f} Hz）⇒ 该数据可作 Stage 1 帧量化证据")
        return True
    rep.info("环境门（D81c）",
             f"证据降级：刷新率 {hz:.3f} Hz ≠ 实验室口径 {expect_hz:.3f} Hz（差 {hz - expect_hz:+.1f} Hz）"
             " ⇒ **该数据只作「程序能跑通、能出 25 列」的连通性证据，不作 Stage 1 帧量化依据**。"
             f"实验室机（{expect_hz:.3f} Hz）上重跑一场，才能真正回填 §6 的 6-B/6-C/6-D 三张表。")
    return False


def check_6c(rep: Report, rows: list[dict]) -> float:
    flip = estimate_flip(rows)
    rep.info("6-C 帧量化（核心）", f"由 `stimulus_dur_actual / stimulus_frames` 反推 FlipIntv ≈ "
             f"{flip * 1000:.3f} ms（{1 / flip:.1f} Hz）" if flip and math.isfinite(flip)
             else "反推不出 FlipIntv（没有可用的 `stimulus_frames`）")
    bad_dur, bad_frames, bad_off, bad_mask = [], [], [], []
    n_checked = 0
    for i, r in enumerate(rows, start=2):
        rt = num(r.get("RT"))
        T = num(r.get("T"))
        if not math.isfinite(T) or T <= 0:
            bad_dur.append(f"L{i} T={r.get('T')}（不是正的数）")
            continue
        if math.isfinite(rt) and rt < T:
            continue                       # 刺激期内按键：时长被有意截断，6-C 不管这些行
        n_checked += 1
        dur = num(r.get("stimulus_dur_actual"))
        fr = num(r.get("stimulus_frames"))
        on = num(r.get("stimulus_onset_actual"))
        off = num(r.get("stimulus_offset_actual"))
        mask = num(r.get("mask_onset_actual"))
        # D81：程序的口径是「实际时长 = 名义 T + 0~1 帧 vsync 余量」（Stage1 §7 第 2 条），
        # 所以容差必须是 1.5 帧；用 1 帧会把 +1 帧的正常行全部判死。
        if not (math.isfinite(dur) and -0.5 * flip - TOL <= dur - T < 1.5 * flip + TOL):
            bad_dur.append(f"L{i} (dur−T)/FlipIntv={(dur - T) / flip:+.2f} 帧"
                           f"（{abs(dur - T) * 1000:.2f} ms）")
        if not (math.isfinite(fr) and fr == round(dur / flip)):
            bad_frames.append(f"L{i} frames={fr:g} ≠ round(dur/FlipIntv)={round(dur / flip):g}")
        if not (math.isfinite(off) and math.isfinite(mask) and abs(off - mask) < 1e-6):
            bad_off.append(f"L{i} offset−mask_onset={off - mask:.6g}")
        if not (math.isfinite(mask) and math.isfinite(on) and math.isfinite(dur)
                and abs(mask - on - dur) < 1e-5):      # D81：实测差值正好 ±1e-6
            bad_mask.append(f"L{i} mask−onset−dur={mask - on - dur:.6g}")
    rep.add("6-C 帧量化（核心）", not bad_dur,
            f"无刺激期按键的 {n_checked} 行：stimulus_dur_actual − T ∈ [−0.5, +1.5) 帧"
            + ("" if not bad_dur else f"（{len(bad_dur)} 处：{bad_dur[:3]}）"))
    rep.add("6-C 帧量化（核心）", not bad_frames,
            f"`stimulus_frames == round(stimulus_dur_actual/FlipIntv)`"
            + ("" if not bad_frames else f"（{len(bad_frames)} 处：{bad_frames[:3]}）"))
    rep.add("6-C 帧量化（核心）", not bad_off,
            "`stimulus_offset_actual == mask_onset_actual`"
            + ("" if not bad_off else f"（{len(bad_off)} 处：{bad_off[:3]}）"))
    rep.add("6-C 帧量化（核心）", not bad_mask,
            "`mask_onset_actual == stimulus_onset_actual + stimulus_dur_actual`"
            + ("" if not bad_mask else f"（{len(bad_mask)} 处：{bad_mask[:3]}）"))
    check_refresh_rate(rep, flip, EXPECT_HZ)
    return flip


def check_6b(rep: Report, rows: list[dict], flip: float):
    if not math.isfinite(flip) or flip <= 0:
        rep.info("6-B KbQueue 刺激期按键", "无法反推 FlipIntv，跳过（先修 6-C）")
        return
    # D81：最小 T 档不能写死成 2/60（那是 60 Hz 的 2 帧）——165 Hz 下最小档是
    # 5 帧 = 30.3 ms，写死会让「明明有刺激期内按键」的数据被判成没记到。
    t_vals = [num(r.get("T")) for r in rows]
    t_vals = [t for t in t_vals if math.isfinite(t) and t > 0]
    t_floor = min(t_vals) if t_vals else T_MIN

    n_in_stim = 0
    n_tmin = 0
    n_mask_win = 0
    n_premature = 0
    for r in rows:
        rt = num(r.get("RT"))
        T = num(r.get("T"))
        resp = (r.get("Response") or "").strip()
        if num(r.get("premature_press")) == 1.0:
            n_premature += 1
        if not (math.isfinite(rt) and math.isfinite(T)):
            continue
        if rt < T and resp != "NA":
            n_in_stim += 1
            if abs(T - t_floor) < 0.5 * flip:
                n_tmin += 1
        if T < rt <= T + MASK_WIN and resp != "NA":
            n_mask_win += 1
    rep.add("6-B KbQueue 刺激期按键", n_in_stim > 0,
            f"刺激期内按键被记录：{n_in_stim} 例"
            f"（其中最小 T 档 {t_floor * 1000:.2f} ms 有 {n_tmin} 例）"
            + ("" if n_in_stim > 0 else " ⇒ **本次回放没有刺激期内按键**，6-B 无法算通过："
               "请在实机验收时有意识地在该档内按一次"))
    rep.add("6-B KbQueue 刺激期按键", n_tmin > 0,
            f"最小 T 档（{t_floor * 1000:.2f} ms）里至少 1 例 `Response` 非 NA 且 `RT < T`"
            f"（实得 {n_tmin} 例）"
            + ("" if n_tmin > 0 else " ⇒ 缺这个证据就说明 2 帧条件的按键没被记到"))
    rep.info("6-B KbQueue 刺激期按键",
             f"掩蔽期内按键（T ~ T+200 ms）{n_mask_win} 例、`premature_press = 1` "
             f"{n_premature} 例（这两项只报计数，判据不设阈值）")


def check_6a(rep: Report):
    rep.info("6-A 掩蔽纹理预加载", "本项判据是 MATLAB 命令行回显"
             "（`掩蔽纹理预加载完成：self 5 张、stranger 5 张`），**txt 里看不到** ⇒ "
             "必须由执行者把命令行窗口截图/文本回填到 Stage1 文档 §6-A 表")


def analyze(files: list[Path]) -> Report:
    rep = Report(files)
    all_rows: list[dict] = []
    bad_header: list[str] = []
    for p in files:
        header, rows, raw = load_rows(p)
        if list(header) != list(RF.HEADER25):
            bad_header.append(f"{p.name}（{len(header)} 列）")
            continue
        if p is files[0]:
            check_6d(rep, header, rows, raw)
        else:
            rep.add("6-D 输出列与缺失值", header == list(RF.HEADER25),
                    f"{p.name}：表头 25 列一致")
            rep.add("6-D 输出列与缺失值", b"\x00" not in raw,
                    f"{p.name}：无 0x00 字节")
        rows, n_dup = dedupe(rows)
        if n_dup:
            rep.info("0 口径", f"{p.name}：按 `trialID` 去重丢弃 {n_dup} 行"
                     "（`fopen` 追加写 ⇒ 崩溃重跑会重复写同一批试次；"
                     "以最后一次出现的行为准，与 CSV 快照一致）")
        all_rows.extend(rows)

    if bad_header:
        # 口径守卫：历史 v2/v3 的 16–20 列文件与 v4.1 不是同一套列名，
        # 拿它们跑 6-B/6-C/6-D 只会喷一墙"缺列"，看不出真正原因。
        rep.add("0 口径", False,
                "这批文件的表头**不是 v4.1 的 25 列**"
                f"（{'、'.join(bad_header)}）⇒ 本检查器的判据全部不适用；"
                "历史 v2/v3 口径的数据请勿用于 Stage 1 验收"
                "（v4.1 的输出列见 `read_formal_data.HEADER25`）")
        check_6a(rep)
        return rep

    flip = check_6c(rep, all_rows)
    check_6b(rep, all_rows, flip)
    check_6a(rep)
    return rep


# ----------------------------------------------------------------------
# 自测：干净数据必须放行，两类缺陷必须被拦住
# ----------------------------------------------------------------------
def _make(maker: Path, outdir: Path, extra: list[str]) -> list[Path]:
    cmd = [sys.executable, "-u", str(maker), str(outdir),
           "--n-subjects", "2", "--n-rep", "3",
           "--rt-lt-t", "0.5", "--in-stim-top", "0.2", "--timeout", "0.08"] + extra
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"合成数据生成失败：{r.stdout}\n{r.stderr}")
    return sorted(outdir.glob("*.txt"))


def self_test() -> int:
    maker = EXP_DIR.parent / "DDM_Core" / "_scratch" / "make_fake_pilot.py"
    if not maker.exists():
        print(f"找不到合成数据生成器：{maker}")
        return 2
    fails = 0
    with tempfile.TemporaryDirectory(prefix="stage1_accept_") as td:
        tmp = Path(td)
        cases = [("干净数据", [], True, None),
                 ("--defect-1f（帧量化缺陷）", ["--defect-1f"], False, "6-C"),
                 ("--defect-mismatch（响应与 RT 矛盾）", ["--defect-mismatch"], False, "6-D")]
        good_files: list[Path] = []
        for name, extra, expect_ok, expect_key in cases:
            files = _make(maker, tmp / name.replace("/", "_").replace(" ", "_"), extra)
            if expect_ok:
                good_files = files
            rep = analyze(files)
            got = rep.ok()
            good = (got == expect_ok)
            if not good:
                fails += 1
            extra_note = ""
            if expect_key is not None:
                hit = any(expect_key in f for f in rep.fails())
                extra_note = f"、拦住 {expect_key} = {'✅' if hit else '❌'}"
                if not hit:
                    fails += 1
            print(f"  {'✅' if good else '❌'} {name}："
                  f"判为{'通过' if got else '未通过'}（期望{'通过' if expect_ok else '未通过'}）"
                  f"{extra_note}")
            if not good:
                print(rep.render())

        # 变异用例：直接改"干净数据"的字节，验证 6-D 的另外两条判据也有牙齿。
        # 不加这两例的话，`Response=NA 但 RT 有值` 与 `0x00 字节` 两条判据
        # 在自测里**从未被触发过**，等于没检查。
        mutations = [
            ("变异：Response=NA 但 RT 有值", _mut_rt_under_na, "6-D"),
            ("变异：文件里混进 0x00 字节", _mut_nul_byte, "6-D"),
            ("变异：历史 16 列口径", _mut_legacy16, "0 口径"),
        ]
        for name, fn, key in mutations:
            mdir = tmp / ("mut_" + str(abs(hash(name)) % 10 ** 6))
            fn(good_files, mdir)
            rep = analyze(sorted(mdir.glob("*.txt")))
            hit = any(key in f for f in rep.fails())
            ok = (not rep.ok()) and hit
            if not ok:
                fails += 1
                print(rep.render())
            print(f"  {'✅' if ok else '❌'} {name}：判为未通过、拦住 {key} = "
                  f"{'✅' if hit else '❌'}")

        # 用例（D87）：帧量化反推的稳健性。用**真实实机**的 (dur, frames) 数对
        # （60.004 Hz 那场，含 0~1 帧 vsync 余量与截断行）。旧的 `median(dur/frames)`
        # 会给出 17.02 ms（+2.1%）并连带判错 6-C 与环境门；新估计器必须 < 1%。
        REAL_PAIRS = [(8.336, 1), (25.491, 2), (33.331, 2), (41.664, 3), (42.164, 3),
                      (58.759, 4), (75.491, 5), (91.241, 5), (149.990, 9),
                      (158.633, 10), (249.168, 15), (254.879, 15)]
        flip_true = 1.0 / 60.004
        pairs_rows = [{"stimulus_dur_actual": str(d / 1000.0),
                       "stimulus_frames": str(f)} for d, f in REAL_PAIRS]
        ratios = sorted(d / f for d, f in REAL_PAIRS)
        naive = ratios[len(ratios) // 2] / 1000.0
        est = estimate_flip(pairs_rows)
        rel_new = abs(est - flip_true) / flip_true
        rel_old = abs(naive - flip_true) / flip_true
        ok = rel_new < 0.01 and rel_old > 0.015
        print(f"  {'✅' if ok else '❌'} 帧量化反推稳健性：新估计器 {est * 1000:.3f} ms"
              f"（偏 {rel_new:+.2%}）｜旧 `median(dur/frames)` {naive * 1000:.3f} ms"
              f"（偏 {rel_old:+.2%}，需 > 1.5% 才算本用例有牙）")
        if not ok:
            fails += 1
    print()
    print(f"自测：{'✅ 全部符合预期（2 例生成缺陷 + 3 例变异都被拦住）' if fails == 0 else f'❌ {fails} 项不符合预期'}")
    return 0 if fails == 0 else 1


def _mut_legacy16(src: list[Path], dst: Path):
    """造一份历史 v2 口径的 16 列表头 ⇒ 必须被「口径守卫」一句话拦住。"""
    dst.mkdir(parents=True, exist_ok=True)
    hdr = ["subID", "block", "trial_index", "cond", "T", "W", "Response", "RT",
           "Correct", "timeout", "responded_by_deadline", "premature_press",
           "stimulus_onset_actual", "stimulus_offset_actual", "mask_onset_actual", "timestamp"]
    for p in src:
        rows = p.read_text(encoding="utf-8").splitlines()
        cells = [ln.split("\t") for ln in rows[1:]]
        out = ["\t".join(hdr)]
        for c in cells:
            out.append("\t".join((c + [""] * 16)[:16]))
        (dst / p.name).write_text("\n".join(out) + "\n", encoding="utf-8")


def _mut_rt_under_na(src: list[Path], dst: Path):
    """把某个漏答行的 `RT` 改成 0.5（Response 仍为 NA）⇒ 6-D 必须报错。"""
    dst.mkdir(parents=True, exist_ok=True)
    for p in src:
        lines = p.read_text(encoding="utf-8").splitlines()
        header = lines[0].split("\t")
        i_resp, i_rt = header.index("Response"), header.index("RT")
        done = False
        for k in range(1, len(lines)):
            cells = lines[k].split("\t")
            if not done and cells[i_resp] == "NA":
                cells[i_rt] = "0.500"
                lines[k] = "\t".join(cells)
                done = True
        (dst / p.name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mut_nul_byte(src: list[Path], dst: Path):
    """在文件末尾塞一个 `0x00` ⇒ 6-D 必须报错（"十六进制查看器搜不到 0x00"）。"""
    dst.mkdir(parents=True, exist_ok=True)
    for p in src:
        (dst / p.name).write_bytes(p.read_bytes() + b"\x00\n")


def main() -> int:
    global EXPECT_HZ          # 允许 --expect-hz 覆盖实验室口径（见 D81c）
    ap = argparse.ArgumentParser(description="Stage 1 实机验收的机器判据（6-B/6-C/6-D）")
    ap.add_argument("txt", nargs="*", help="v4.1 逐被试 txt（可多个）")
    ap.add_argument("--expect-hz", type=float, default=EXPECT_HZ,
                    help=f"实验室机刷新率（默认 {EXPECT_HZ} Hz）；数据来自别的屏幕时"
                         "用来自动标注证据等级")
    ap.add_argument("--self-test", action="store_true", help="用合成数据自测本检查器")
    args = ap.parse_args()
    EXPECT_HZ = args.expect_hz
    if args.self_test:
        return self_test()
    files = [Path(p) for p in args.txt]
    if not files:
        print("用法：python -X utf8 check_stage1_acceptance.py <txt...> 或 --self-test")
        return 2
    missing = [p for p in files if not p.exists()]
    if missing:
        print(f"找不到文件：{missing}")
        return 2
    rep = analyze(files)
    print(rep.render())
    return 0 if rep.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
