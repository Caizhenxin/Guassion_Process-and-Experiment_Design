# -*- coding: utf-8 -*-
"""D81：修正 `check_stage1_acceptance.py` 四处在高刷屏上误判的判据。

背景：2026-10-18 用主试实机产物（165 Hz，FlipIntv≈6.06 ms）回放，
6-C/6-B 共报 4 条强制项 ❌，逐条核对后**全部是本检查器的问题**，不是数据的问题：

1. `estimate_flip` 用 `T / stimulus_frames` 反推 FlipIntv；但程序第 25 列写的是
   `round(stimulus_dur_actual / FlipIntv)`（实际时长，含 0~1 帧 vsync 余量），
   于是 165 Hz 被算成 171.6 Hz（5.83 ms vs 真值 6.06 ms）。
2. `|dur − T| < 1 帧`：程序设计就是"实际时长 ≈ 名义 T + 0~1 帧"（Stage1 §7 第 2 条
   已写明），1 帧的容差正好把 +1 帧的正常行判死。改为 [−0.5, +1.5) 帧。
3. `stimulus_frames == round(T/FlipIntv)`：应比 `round(stimulus_dur_actual/FlipIntv)`。
4. `mask − onset − dur` 用 `1e-6` 容差，实测差值**正好 ±1e-6**（浮点尘土）⇒ 误判。
   改为 `1e-5`。
5. 6-B 把"最小 T 档"写死成 `2/60`；165 Hz 下最小档是 5 帧 = 30.3 ms，写死会让
   **明明有刺激期内按键**的数据被判"没记到"。改为取数据里实测的最小 T。

幂等：每处都断言"命中且仅命中 1 次"，重复运行会因已替换而失败（不会写坏文件）。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TARGET = REPO / "1_Code" / "Experiment" / "exp_Check" / "check_stage1_acceptance.py"

EDITS: list[tuple[str, str, str]] = [
    # ---------------------------------------------------------------- 0 头部说明
    (
        "docstring 顶部补 D81 说明",
        "退出码：0 = 全部强制项通过；1 = 有强制项未通过；2 = 输入不可用（找不到/读不了）。",
        "D81（2026-10-18，用主试 165 Hz 实机产物回放发现）：本检查器原先有 4 处判据只在\n"
        "60 Hz 上成立 —— FlipIntv 用 `T/stimulus_frames` 反推（高刷屏低估 4%）、\n"
        "`stimulus_frames` 拿名义 T 去比（程序写的是**实际时长**的帧数）、\n"
        "`mask−onset−dur` 用 1e-6 容差（实测正好 ±1e-6 的浮点尘土）、6-B 的最小 T 档写死 2/60。\n"
        "四处合起来把 165 Hz 实机上的**正常行**判成缺陷。已全部修正。\n"
        "\n"
        "退出码：0 = 全部强制项通过；1 = 有强制项未通过；2 = 输入不可用（找不到/读不了）。",
    ),
    # ---------------------------------------------------------------- 1 FlipIntv
    (
        "estimate_flip 改用 dur/frames",
        '    """由 `T / stimulus_frames` 的中位数反推屏幕 FlipIntv（不依赖启动打印）。"""\n'
        "    est = []\n"
        "    for r in rows:\n"
        '        T = num(r.get("T"))\n'
        '        fr = num(r.get("stimulus_frames"))\n'
        "        if T > 0 and fr >= 1 and math.isfinite(fr):\n"
        "            est.append(T / fr)\n",
        '    """由 `stimulus_dur_actual / stimulus_frames` 的中位数反推 FlipIntv。\n'
        "\n"
        "    ⚠️ D81：不能用 `T / stimulus_frames`。程序第 25 列写的是\n"
        "    `round(stimulus_dur_actual / FlipIntv)`（**实际**时长的帧数，含 0~1 帧 vsync\n"
        "    余量），不是名义 T 的帧数。用 `T / frames` 反推会系统性低估 FlipIntv\n"
        "    （165 Hz 实机：算出 5.83 ms，真值 6.06 ms，低 4%），进而把正常行判成缺陷。\n"
        '    """\n'
        "    est = []\n"
        "    for r in rows:\n"
        '        dur = num(r.get("stimulus_dur_actual"))\n'
        '        fr = num(r.get("stimulus_frames"))\n'
        "        if dur > 0 and fr >= 1 and math.isfinite(fr):\n"
        "            est.append(dur / fr)\n",
    ),
    (
        "6-C 的 FlipIntv 回显措辞",
        '    rep.info("6-C 帧量化（核心）", f"由 `T / stimulus_frames` 反推 FlipIntv ≈ "',
        '    rep.info("6-C 帧量化（核心）", f"由 `stimulus_dur_actual / stimulus_frames` 反推 FlipIntv ≈ "',
    ),
    # ---------------------------------------------------------------- 2 dur 容差
    (
        "|dur−T| 容差 1 帧 → [−0.5,+1.5) 帧",
        "        if not (math.isfinite(dur) and abs(dur - T) < flip + TOL):\n"
        '            bad_dur.append(f"L{i} |dur−T|={abs(dur - T) * 1000:.2f} ms ≥ 1 帧")',
        "        # D81：程序的口径是「实际时长 = 名义 T + 0~1 帧 vsync 余量」（Stage1 §7 第 2 条），\n"
        "        # 所以容差必须是 1.5 帧；用 1 帧会把 +1 帧的正常行全部判死。\n"
        "        if not (math.isfinite(dur) and -0.5 * flip - TOL <= dur - T < 1.5 * flip + TOL):\n"
        '            bad_dur.append(f"L{i} (dur−T)/FlipIntv={(dur - T) / flip:+.2f} 帧"\n'
        '                           f"（{abs(dur - T) * 1000:.2f} ms）")',
    ),
    (
        "dur 判据的文字",
        '            f"无刺激期按键的 {n_checked} 行：|stimulus_dur_actual − T| < 1 帧"',
        '            f"无刺激期按键的 {n_checked} 行：stimulus_dur_actual − T ∈ [−0.5, +1.5) 帧"',
    ),
    # ---------------------------------------------------------------- 3 frames 基准
    (
        "stimulus_frames 比 dur 而不是 T",
        "        if not (math.isfinite(fr) and fr == round(T / flip)):\n"
        '            bad_frames.append(f"L{i} frames={fr:g} ≠ round(T/flip)={round(T / flip):g}")',
        "        if not (math.isfinite(fr) and fr == round(dur / flip)):\n"
        '            bad_frames.append(f"L{i} frames={fr:g} ≠ round(dur/FlipIntv)={round(dur / flip):g}")',
    ),
    (
        "frames 判据的文字",
        '            f"`stimulus_frames == round(T/FlipIntv)`"',
        '            f"`stimulus_frames == round(stimulus_dur_actual/FlipIntv)`"',
    ),
    # ---------------------------------------------------------------- 4 浮点尘土
    (
        "mask−onset−dur 容差 1e-6 → 1e-5",
        "                and abs(mask - on - dur) < 1e-6):",
        "                and abs(mask - on - dur) < 1e-5):      # D81：实测差值正好 ±1e-6",
    ),
    # ---------------------------------------------------------------- 5 最小 T 档
    (
        "6-B 取实测最小 T 档",
        "    n_in_stim = 0\n    n_tmin = 0\n",
        "    # D81：最小 T 档不能写死成 2/60（那是 60 Hz 的 2 帧）——165 Hz 下最小档是\n"
        "    # 5 帧 = 30.3 ms，写死会让「明明有刺激期内按键」的数据被判成没记到。\n"
        '    t_vals = [num(r.get("T")) for r in rows]\n'
        "    t_vals = [t for t in t_vals if math.isfinite(t) and t > 0]\n"
        "    t_floor = min(t_vals) if t_vals else T_MIN\n"
        "\n"
        "    n_in_stim = 0\n    n_tmin = 0\n",
    ),
    (
        "6-B 用 t_floor 比较",
        "            if abs(T - T_MIN) < 0.5 * flip:",
        "            if abs(T - t_floor) < 0.5 * flip:",
    ),
    (
        "6-B 计数回显",
        '            f"刺激期内按键被记录：{n_in_stim} 例（其中 `T = 33.33 ms` 档 {n_tmin} 例）"',
        '            f"刺激期内按键被记录：{n_in_stim} 例"\n'
        '            f"（其中最小 T 档 {t_floor * 1000:.2f} ms 有 {n_tmin} 例）"',
    ),
    (
        "6-B 判据回显",
        '            f"`T = 33.33 ms` 档里至少 1 例 `Response` 非 NA 且 `RT < 0.0333`"\n'
        '            f"（实得 {n_tmin} 例）"',
        '            f"最小 T 档（{t_floor * 1000:.2f} ms）里至少 1 例 `Response` 非 NA 且 `RT < T`"\n'
        '            f"（实得 {n_tmin} 例）"',
    ),
    (
        "6-B 兜底提示措辞",
        '               "请在实机验收时有意识地在该档内按一次"))',
        '               "请在实机验收时有意识地在该档内按一次"))',
    ),
]


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    orig = src
    for name, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            print(f"❌ [{name}] 命中 {n} 次（要求恰好 1 次），中止，未写文件")
            return 1
        src = src.replace(old, new)
        print(f"✅ [{name}]")
    if src == orig:
        print("无改动")
        return 0
    TARGET.write_text(src, encoding="utf-8", newline="\n")
    print(f"\n已写回 {TARGET}（{len(src.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
