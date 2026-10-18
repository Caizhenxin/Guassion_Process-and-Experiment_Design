# -*- coding: utf-8 -*-
"""给 `_make_ddm_pilot.py` 加两项**可选**能力，默认行为逐字节不变：

1. `--anticipation <率>`：按比例把正式段试次改成「抢按」（`RT < T` 的短反应，
   真实被试约 1%–3%）。没有它，DDM 生成的 RT 全部 ≥ `t0`（0.15 s），
   `stimulus_dur_actual` 永远等于 `T`，于是
   `check_stage1_acceptance.py` 的 **6-B**（最小 T 档里要至少有 1 例刺激期内按键）
   必然 FAIL —— 这不是数据坏了，是**合成数据缺少真实被试的抢按**。
2. 抢按行的时间戳改成与程序一致：`stimulus_dur_actual` = 按键时刻**向上取整到下一帧**
   （而不是名义 `T`），`stimulus_frames = round(dur/FLIP)`、`mask_onset = onset + dur`。

这两项只在 `--anticipation > 0` 时启用；`--anticipation 0`（默认）下 `dur` 仍是 `T`。
"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\_scratch\_make_ddm_pilot.py")
src = P.read_text(encoding="utf-8")

ARG_ANCHOR = """    ap.add_argument("--n-practice", type=int, default=0,"""
ARG_NEW = """    ap.add_argument("--anticipation", type=float, default=0.0,
                    help="抢按比例（真实被试约 0.01–0.03）；>0 时同时把抢按行的 "
                         "stimulus_dur_actual 改成「按键后下一帧」，供 6-B 通过")
    ap.add_argument("--n-practice", type=int, default=0,"""
assert src.count(ARG_ANCHOR) == 1
src = src.replace(ARG_ANCHOR, ARG_NEW)

SIM_ANCHOR = """        om = np.asarray(sim["omission"], dtype=int)
"""
SIM_NEW = """        om = np.asarray(sim["omission"], dtype=int)

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
"""
assert src.count(SIM_ANCHOR) == 1
src = src.replace(SIM_ANCHOR, SIM_NEW)

DUR_ANCHOR = """            dur = T
            cols = [args.group, sid, 2, 24, 2, stage, i + 1, int(design["P"][i]),"""
DUR_NEW = """            # 抢按行：刺激在「按键后下一帧」就结束（与 Exp_Design_Formal.m 一致）
            in_stim = (not om[i]) and (rtv is not None) and (rtv < T)
            dur = max(FLIP, np.ceil(rtv / FLIP) * FLIP) if in_stim else T
            cols = [args.group, sid, 2, 24, 2, stage, i + 1, int(design["P"][i]),"""
assert src.count(DUR_ANCHOR) == 1
src = src.replace(DUR_ANCHOR, DUR_NEW)

PRINT_ANCHOR = """        print(f"  ✓ {path.name} —— {len(lines) - 1} 试次、响应 {n_resp}"
              f"（rho = {args.rho}、t0 = {p.t0:.3f} s）")"""
PRINT_NEW = """        print(f"  ✓ {path.name} —— {len(lines) - 1} 试次、响应 {n_resp}"
              f"（rho = {args.rho}、t0 = {p.t0:.3f} s、抢按 {n_ant}）")"""
assert src.count(PRINT_ANCHOR) == 1
src = src.replace(PRINT_ANCHOR, PRINT_NEW)

P.write_text(src, encoding="utf-8", newline="\n")
print("[ok] 已加 --anticipation；文件", len(src.split("\n")), "行")
