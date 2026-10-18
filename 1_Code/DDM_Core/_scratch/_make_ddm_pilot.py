#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 **DDM 生成**的 Pilot 数据（v4.1 25 列格式），给 Stage 8 做**正向对照**。

## 它为什么存在

`make_fake_pilot.py` 是按 `Exp_Design_Formal.m` 的规则表转录的生成器，**没有证据
累积过程**。用它跑 `stage8_run.py` 时 PPC 必然失配（遗漏率观测 0.06–0.09 vs 预测
0.19–0.26）——那是**阴性对照成功**（PPC 认出"数据不是这个模型生成的"），不能用来
证明管线"在真实数据上能跑"。

本脚本补上另一半：用 `twophase.simulate_euler_subject`（M-T1，含 rho 污染）生成
**确实是这个模型生成的数据**，再写成 v4.1 的 25 列 txt。于是：

* PPC 应当在带内（正向对照）；
* 模型比较应当把**生成数据的那个模型**挑出来（`--rho 0.8` ⇒ M-T1 应胜 M-T3；
  `--rho 1.0` ⇒ M-T3 应胜 M-T1）。

对应 `Stage8_建模与验证方案.md` §11 第 12 条（合成数据不是 DDM 生成的）的补足。

## 用法

    python -X utf8 _make_ddm_pilot.py <输出目录> [--n-subjects 3] [--group 1]
        [--n-rep 2] [--rho 0.8] [--seed 7] [--dt 5e-5]

输出：`<目录>/exp_group{group}_subject{s}.txt`，表头与 `read_formal_data.HEADER25`
逐字一致（本脚本直接 import 它，避免重复维护列名——但**配对规则独立转录**，
见 `PAIRING_RULES`）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
_CODE = _HERE.parents[1]                       # 1_Code/
for _p in (str(_CODE / "DDM_Core"), str(_CODE / "Experiment")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import read_formal_data as RF                   # noqa: E402
import twophase as TP                           # noqa: E402
from mapping import MappingParams               # noqa: E402
from simulate import draw_subject_params        # noqa: E402

#: 与 `make_fake_pilot.PAIRING_RULES` 同一张表（从 `Exp_Design_Formal.m` 的
#: `getPairingRules` 独立转录；索引 = `subjectID % 4`）。
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
KINDS = (("circle", "self"), ("square", "self"),
         ("circle", "stranger"), ("square", "stranger"))

T_LEVELS = [2 / 60, 5 / 60, 9 / 60, 15 / 60]
W_LEVELS = [48 / 60, 72 / 60, 108 / 60]
FLIP = 1.0 / 60.0

#: 组层真值（与 `_scratch/_probe_hess_scaling.py` 用的是同一套 `lin` 真值）。
TRUTH = MappingParams(shape_model="lin", d_ref=1.20, beta_T=0.45, beta_S=0.25,
                      beta_ST=0.05, a_ref=1.10, delta_a=0.30, t0=0.15)

#: 「像 Pilot」的那一档真值：**只为了让 nalyze_pilot.py 的 S6-5 判据也过**
#: （正确率 0.55–0.98、RT 中位 0.3–2.0 s）。与 TRUTH 的区别：漂移略小、边界略大、
#: t0 略大 ⇒ RT 中位 ≈ 0.33 s、正确率 ≈ 0.59。用 TRUTH（d=1.20/a=1.10/t0=0.15）
#: 时 RT 中位只有 0.275 s，会被 S6-5 判 FAIL —— 那不是 DDM 的问题，是**真值选得比
#: 被试快**。Stage 9 的可识别性探针继续用 TRUTH（口径不变、日志可复现）。
QC_TRUTH = TRUTH.replace(d_ref=1.15, a_ref=1.15, t0=0.18)


def build_trials(n_rep: int, group: int) -> dict:
    """构造一个被试的（不含观测的）试次表。"""
    P = [0, 8, 32, 120][group - 1]
    rows = []
    for T in T_LEVELS:
        for W in W_LEVELS:
            for sh, lb in KINDS:
                for _ in range(n_rep):
                    rows.append((T, W, sh, lb))
    return {"P": P, "rows": rows}


def rows_for_subject(sid: int, n_rep: int, group: int,
                     n_practice: int = 0) -> tuple[dict, list, str]:
    """返回（设计数组, 行元数据列表, matchKey）。

    ``n_practice > 0`` 时在最前面插练习段（`block = 0`、`T = W = W_LEVELS[1]`，
    与 `make_fake_pilot.py` 同口径）—— `qc_group.py` 的 G3 要求练习段恰好是程序
    规定的次数，缺了会被判 WARN。
    """
    rule = PAIRING_RULES[int(sid) % 4]
    mk = RF.match_key(int(sid))
    base = build_trials(n_rep, group)
    rows = [(T, W, sh, lb, block)
            for (T, W, sh, lb), block in
            zip(base["rows"], [W_LEVELS.index(r[1]) + 1 for r in base["rows"]])]
    for i in range(n_practice):
        sh, lb = KINDS[i % 4]
        rows.insert(i, (W_LEVELS[1], W_LEVELS[1], sh, lb, 0))
    T = np.array([r[0] for r in rows], dtype=float)
    W = np.array([r[1] for r in rows], dtype=float)
    kinds = [(r[2], r[3]) for r in rows]
    ck = np.array([rule[k] for k in kinds], dtype=object)
    design = {
        "P": np.full(T.size, float(base["P"])),
        "T": T, "W": W,
        "is_self": np.array([1.0 if lb == "self" else 0.0 for _, lb in kinds]),
        "is_match": np.array([1 if c == mk else 0 for c in ck], dtype=int),
    }
    meta = [(kinds[i], str(ck[i]), float(T[i]), float(W[i]), int(rows[i][4]))
            for i in range(T.size)]
    return design, meta, mk


def fmt_row(cols: list) -> str:
    """与 `Exp_Design_Formal.m` 的 fprintf 逐位对应（缺值写 NA / NaN）。"""
    specs = ["%d", "%d", "%d", "%d", "%d", "%s", "%d", "%d", "%.6f", "%.6f",
             "%s", "%s", "%s", "%s", "%.3f", "%d",
             "%d", "%d", "%d", "%d", "%.6f", "%.6f", "%.6f", "%.6f", "%d"]
    toks = []
    for c, sp in zip(cols, specs):
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
    ap.add_argument("--n-subjects", type=int, default=3)
    ap.add_argument("--group", type=int, default=1)
    ap.add_argument("--n-rep", type=int, default=2,
                    help="每个 (T,W,类) 格的重复次数（正式设计是 12）")
    ap.add_argument("--rho", type=float, default=0.8,
                    help="掩蔽阶段的漂移污染系数；1.0 = 无污染（M-T3 为真）")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dt", type=float, default=5e-5)
    ap.add_argument("--preset", choices=("fim", "qc"), default="qc",
                    help="组层真值预设：qc = 像 Pilot 的那一档（默认）、fim = 与 Stage 9 探针同口径")
    ap.add_argument("--d-ref", type=float, default=None,
                    help="覆盖组层真值的 d_ref（默认 1.20；调大 ⇒ RT 变快）")
    ap.add_argument("--a-ref", type=float, default=None,
                    help="覆盖组层真值的 a_ref（默认 1.10）")
    ap.add_argument("--t0", type=float, default=None,
                    help="覆盖组层真值的 t0（默认 0.15 s）")
    ap.add_argument("--anticipation", type=float, default=0.0,
                    help="抢按比例（真实被试约 0.01–0.03）；>0 时同时把抢按行的 "
                         "stimulus_dur_actual 改成「按键后下一帧」，供 6-B 通过")
    ap.add_argument("--n-practice", type=int, default=0,
                    help="练习段试次数（组 1 的程序规定是 4；qc_group 的 G3 会查）")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for sid in range(1, args.n_subjects + 1):
        rng = np.random.default_rng(int(args.seed) + sid)
        design, meta, mk = rows_for_subject(sid, args.n_rep, args.group,
                                           args.n_practice)
        truth = QC_TRUTH if args.preset == "qc" else TRUTH
        if any(v is not None for v in (args.d_ref, args.a_ref, args.t0)):
            truth = QC_TRUTH if args.preset == "qc" else TRUTH.replace(
                d_ref=TRUTH.d_ref if args.d_ref is None else float(args.d_ref),
                a_ref=TRUTH.a_ref if args.a_ref is None else float(args.a_ref),
                t0=TRUTH.t0 if args.t0 is None else float(args.t0))
        p = draw_subject_params(truth, rng, mode="truncate")
        sim = TP.simulate_euler_subject(design, p, float(args.rho), rng,
                                        dt=float(args.dt))
        rt = np.asarray(sim["rt"], dtype=float)
        side = np.asarray(sim["side"], dtype=int)
        om = np.asarray(sim["omission"], dtype=int)

        # ---- 抢按（可选）：真实被试会在刺激期结束前就按键 ----
        n_ant = 0
        if args.anticipation > 0:
            formal_idx = [i for i, m in enumerate(meta) if m[4] != 0]
            n_ant = int(rng.binomial(len(formal_idx), float(args.anticipation)))
            if n_ant > 0:
                for i in rng.choice(formal_idx, size=min(n_ant, len(formal_idx)),
                                    replace=False):
                    T_i = float(meta[i][2])
                    om[i] = 0
                    rt[i] = float(rng.uniform(0.5 * FLIP,
                                              max(0.6 * FLIP, 0.85 * T_i)))
                    side[i] = int(rng.integers(0, 2))

        lines = ["\t".join(RF.HEADER25)]
        t_class = 1000.0
        other = {"f": "j", "j": "f"}[mk]
        n_drop = 0
        for i, ((sh, lb), ck, T, W, block) in enumerate(meta):
            t_class += 2.0
            stage = "practice" if block == 0 else "formal"
            if om[i]:
                resp, rtv, corr = None, None, None
                timeout, rbd = 1, 0
            else:
                # DDM 的 side=1 是"按了匹配键"（上边界）⇒ 与 read_formal_data 的
                # side = (Response == matchKey) 定义一致
                resp = mk if side[i] == 1 else other
                rtv = float(rt[i])
                corr = 1 if resp == ck else 0
                timeout, rbd = 0, 1
            # 抢按行：刺激在「按键后下一帧」就结束（与 Exp_Design_Formal.m 一致）
            in_stim = (not om[i]) and (rtv is not None) and (rtv < T)
            dur = max(FLIP, np.ceil(rtv / FLIP) * FLIP) if in_stim else T
            cols = [args.group, sid, 2, 24, 2, stage, i + 1, int(design["P"][i]),
                    T, W, sh, lb, ck, resp, None if rtv is None else round(rtv, 3),
                    corr, block, 0, timeout, rbd,
                    round(t_class, 6), round(t_class + dur, 6), round(t_class + dur, 6),
                    round(dur, 6), round(dur / FLIP)]
            lines.append(fmt_row(cols))

        path = outdir / f"exp_group{args.group}_subject{sid}.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        n_resp = int(np.sum(~om.astype(bool)))
        acc = np.nan
        written.append((path, len(lines) - 1, n_resp, n_drop))
        print(f"  ✓ {path.name} —— {len(lines) - 1} 试次、响应 {n_resp}"
              f"（rho = {args.rho}、t0 = {p.t0:.3f} s、抢按 {n_ant}）")
    print(f"合成完成：{len(written)} 名被试（DDM/M-T1 生成，n_rep = {args.n_rep}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
