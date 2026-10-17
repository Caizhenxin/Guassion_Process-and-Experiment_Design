#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成合成 Pilot 数据，用来给 `1_Code/Experiment/analyze_pilot.py` 做正向/负向自测。

本机没有 MATLAB，跑不出真数据；这个生成器按 `Exp_Design_Formal.m`（v4/v4.1）的
25 列格式与 D4 试次结构造一份"已知答案"的数据，让检查器的每一条判据都被
至少一次触发，包括故意注入的缺陷。

用法
----
    python make_fake_pilot.py <输出目录> [--n-subjects 2] [--group 1] [--seed 7]
                              [--rt-lt-t 0.03]   # RT<T 的目标比例（0.03 干净 / 0.30 触发 WARN）
                              [--defect-1f]       # T/W 用 %.1f 打印（复现 v4.1 缺陷）
                              [--defect-mismatch] # 注入 Response 与 RT 自相矛盾的行
                              [--defect-missing-t] # 只写 2 档 T（复现"T 档丢失"）

期望结果（见 Stage6_Pilot方案.md 的自测记录）：
    干净            → S6-2 PASS 或 WARN(rt-lt-t 决定)，其余 PASS，退出码 0
    --rt-lt-t 0.30  → S6-2 WARN，退出码 0
    --defect-1f     → S6-4 FAIL，退出码 1
    --defect-missing-t → S6-4 FAIL，退出码 1
    --defect-mismatch  → S6-3 FAIL，退出码 1
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

T_LEVELS = [2 / 60, 5 / 60, 9 / 60, 15 / 60]          # 秒（2/5/9/15 帧 @60 Hz）
W_LEVELS = [48 / 60, 72 / 60, 108 / 60]
FLIP = 1.0 / 60.0

#: ⚠️ `CorrectKey` 由程序的 `getPairingRules`（`rules{mod(subjectID,4)+1}`）决定，**逐被试不同**。
#: 本节是从 `Exp_Design_Formal.m` 的规则表**独立转录**的一张表（故意不 import 被测的
#: `read_formal_data.py`：生成器必须独立于被测代码，否则被测代码的错会传播成"真值"）。
#: 索引 = `subjectID % 4`，元素 = {(shape, label): correctKey}。
PAIRING_RULES = {
    0: {("square", "self"): "f", ("square", "stranger"): "j",
        ("circle", "self"): "j", ("circle", "stranger"): "f"},
    1: {("square", "self"): "j", ("square", "stranger"): "f",
        ("circle", "self"): "f", ("circle", "stranger"): "j"},
    2: {("square", "self"): "j", ("square", "stranger"): "f",
        ("circle", "self"): "f", ("circle", "stranger"): "j"},
    3: {("square", "self"): "f", ("square", "stranger"): "j",
        ("circle", "self"): "j", ("circle", "stranger"): "f"},
}
_SHAPE_LABELS = (("circle", "self"), ("square", "self"),
                 ("circle", "stranger"), ("square", "stranger"))


def kinds_for(subject_id: int) -> list:
    """该被试的 4 个 `(shape, label, correctKey)` 三元组。

    ❗ 旧版这里是一张**对所有被试相同**的 `KINDS` 表，它只等于 `subjectID % 4 ∈ {1,2}`
    那两档的规则 ⇒ 3/4 的被试写出来的 `CorrectKey` 与程序不符，`read_formal_data` 的两条
    独立路径必然打架。这是**生成器的缺陷**（不是读取器的），而它会伪装成"读取器把好数据
    判成了坏数据"⇒ 修掉，否则 >2 人的干跑无法进行。
    """
    rule = PAIRING_RULES[int(subject_id) % 4]
    return [(sh, lb, rule[(sh, lb)]) for sh, lb in _SHAPE_LABELS]


N_REP = 12
HEADER = ("groupID\tsubjectID\tgender\tage\thandedness\tstage\ttrialID\tP\tT\tW\t"
          "Shape\tLabel\tCorrectKey\tResponse\tRT\tCorrect\t"
          "block\tpremature_press\ttimeout\tresponded_by_deadline\t"
          "stimulus_onset_actual\tstimulus_offset_actual\tmask_onset_actual\t"
          "stimulus_dur_actual\tstimulus_frames")


# 25 列的转换说明符，与 Exp_Design_Formal.m 的 fprintf(fileID, ...) 逐位对应
SPECS = ["%d", "%d", "%d", "%d", "%d", "%s", "%d", "%d", "%.6f", "%.6f",
         "%s", "%s", "%s", "%s", "%.3f", "%d",
         "%d", "%d", "%d", "%d", "%.6f", "%.6f", "%.6f", "%.6f", "%d"]


def fmt_row(cols: list, narrow: bool = False) -> str:
    """按 Exp_Design_Formal.m 的格式串排版（narrow=True 复现 v4.1 之前的 %.1f）。

    缺值列按 MATLAB 的写法输出：字符串列写 `NA`，数值列写 `NaN`
    （MATLAB 的 fprintf 用 %d/%.3f 打印 NaN 时就是写 'NaN'，Python 的 %d 做不到，
    所以这里逐列排版而不是整串套 format）。
    """
    toks = []
    for c, sp in zip(cols, SPECS):
        if sp in ("%.6f", "%.1f") and narrow and sp == "%.6f":
            sp = "%.1f"
        if c is None:
            toks.append("NA" if sp == "%s" else "NaN")
        elif sp == "%s":
            toks.append(str(c))
        else:
            toks.append(sp % c)
    return "\t".join(toks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--n-subjects", type=int, default=2)
    ap.add_argument("--group", type=int, default=1)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rt-lt-t", type=float, default=0.03,
                    help="预期性 RT<T 的目标比例（RT 一律 < 0.15 s）")
    ap.add_argument("--in-stim-top", type=float, default=0.0,
                    help="最大 T 档上「刺激内完成累计」的比例（RT ∈ [0.15, 0.98T)）；"
                         "用于驱动 S6-2c 的 Stage 8 分支")
    ap.add_argument("--timeout", type=float, default=0.08)
    ap.add_argument("--n-rep", type=int, default=N_REP,
                    help=f"每个 (T,W,类) 格重复次数（默认 {N_REP} = 正式设计；"
                         f"调小只为**干跑**，如 3 ⇒ 每人 4+144 试次）")
    ap.add_argument("--defect-1f", action="store_true")
    ap.add_argument("--defect-mismatch", action="store_true")
    ap.add_argument("--defect-missing-t", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    P = [0, 8, 32, 120][args.group - 1]
    t_levels = T_LEVELS[:2] if args.defect_missing_t else T_LEVELS
    t0 = 1000.0
    written = []

    for s in range(1, args.n_subjects + 1):
        lines = [HEADER]
        trial = 0
        kinds = kinds_for(s)          # 逐被试的 (shape, label, correctKey)
        # 练习：n_practice 试次，T = 5 帧，W = 72 帧
        n_practice = P if P else 4
        for i in range(n_practice):
            trial += 1
            T, W = T_LEVELS[1], W_LEVELS[1]
            shape, label, key = kinds[i % 4]
            t0 += 2.0
            rt = T + rng.lognormvariate(-0.5, 0.45) if rng.random() > args.timeout else None
            dur = T if (rt is None or rt >= T) else T
            cols = [args.group, s, 2, 24, 2, "practice", trial, P, T, W, shape, label, key,
                    None if rt is None else key, None if rt is None else round(rt, 3),
                    None if rt is None else (1 if rng.random() < 0.75 else 0),
                    0, 0, 1 if rt is None else 0, 1 if rt is not None else 0,
                    round(t0, 6), round(t0 + dur, 6), round(t0 + dur, 6),
                    round(dur, 6), round(dur / FLIP)]
            lines.append(fmt_row(cols, args.defect_1f))
        # 正式：3 block × 4 T × 4 类 × 12 次
        for b, W in enumerate(W_LEVELS, start=1):
            for T in t_levels:
                for shape, label, key in kinds:
                    for _ in range(args.n_rep):
                        trial += 1
                        t0 += 2.0
                        if rng.random() < args.timeout:
                            rt, resp, correct = None, None, None
                        else:
                            p_lt = args.in_stim_top if T == t_levels[-1] else args.rt_lt_t
                            if rng.random() < p_lt:
                                # 刺激期内按键，拆成两类（S6-2c 只认后一类）：
                                #   ① 预期性：RT < 0.15 s —— 刺激刚上屏就按
                                #   ② 刺激内完成累计：0.15 s ≤ RT < T —— 只可能出现在长 T 上
                                if T == t_levels[-1] and args.in_stim_top > 0 and 0.98 * T > 0.15:
                                    rt = rng.uniform(0.15, 0.98 * T)
                                else:
                                    hi = min(0.95 * T, 0.148)
                                    rt = rng.uniform(min(0.05, 0.5 * hi), hi)
                            else:
                                rt = T + rng.lognormvariate(-0.5, 0.45)
                            rt = min(rt, W - 0.001)
                            resp = key if rng.random() < 0.75 else ("j" if key == "f" else "f")
                            correct = 1 if resp == key else 0
                        press_in_stim = rt is not None and rt < T
                        if press_in_stim:
                            dur = min(T, (int(rt / FLIP) + 1) * FLIP)
                        else:
                            dur = T
                        cols = [args.group, s, 2, 24, 2, "formal", trial, P, T, W, shape, label, key,
                                resp, None if rt is None else round(rt, 3), correct,
                                b, 1 if rng.random() < 0.02 else 0,
                                1 if rt is None else 0, 0 if rt is None else 1,
                                round(t0, 6), round(t0 + dur, 6), round(t0 + dur, 6),
                                round(dur, 6), round(dur / FLIP)]
                        if args.defect_mismatch and trial % 97 == 0:
                            cols[13] = key      # 有按键……
                            cols[14] = None     # ……但 RT 缺失
                        lines.append(fmt_row(cols, args.defect_1f))
        p = outdir / f"exp_group{args.group}_subject{s}.txt"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append((p, len(lines) - 1))

    for p, n in written:
        print(f"  ✓ {p} —— {n} 试次")
    print(f"合成完成：{len(written)} 名被试，缺陷开关 "
          f"1f={args.defect_1f} mismatch={args.defect_mismatch} missing_t={args.defect_missing_t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
