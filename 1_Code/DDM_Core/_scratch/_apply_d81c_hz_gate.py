# -*- coding: utf-8 -*-
"""D81c：给验收检查器加「刷新率门」——数据来自非 60.004 Hz 屏幕时明确区分证据等级。

背景（2026-10-18）：主试用本机（165 Hz）跑了一场，检查器按 60 Hz 口径把 74 行判成
帧量化缺陷。核实后 44 行是 165 Hz 下每帧只有 6.06 ms 绘制预算导致的掉帧，30 行是
v4.4 的抢按截断——**都不是设计缺陷**，而是"这块屏不是实验室那块屏"。

但把 60 Hz 当隐含常量仍然是隐患：换屏就会把好数据判成坏数据，或者反过来把坏数据
放过。所以加一道显式的门：反推出的刷新率与实验室口径（60.004 Hz，见设计文档 §1）
相差超过 1% 时，打印一条醒目的「证据降级」说明，并给出该数据能作什么、不能作什么。

不改判据强度（6-C/6-D 仍按数据自身的 FlipIntv 判），只改**结论的适用范围**。

幂等：断言每处命中恰好 1 次。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TARGET = REPO / "1_Code" / "Experiment" / "exp_Check" / "check_stage1_acceptance.py"

GATE = '''
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
             f"⚠️ 刷新率 {hz:.3f} Hz ≠ 实验室口径 {expect_hz:.3f} Hz（差 {hz - expect_hz:+.1f} Hz）"
             " ⇒ **该数据只作「程序能跑通、能出 25 列」的连通性证据，不作 Stage 1 帧量化依据**。"
             f"实验室机（{expect_hz:.3f} Hz）上重跑一场，才能真正回填 §6 的 6-B/6-C/6-D 三张表。")
    return False


'''

EDITS: list[tuple[str, str, str]] = [
    (
        "插入 check_refresh_rate",
        "def check_6c(rep: Report, rows: list[dict]) -> float:",
        GATE.lstrip("\n") + "def check_6c(rep: Report, rows: list[dict]) -> float:",
    ),
    (
        "check_6c 末尾调用环境门",
        "    return flip\n",
        "    check_refresh_rate(rep, flip, EXPECT_HZ)\n"
        "    return flip\n",
    ),
    (
        "定义实验室口径常量",
        "def estimate_flip(rows: list[dict]) -> float:",
        "# 实验室机刷新率（设计文档 §1 的帧量化表就是按它算的：60.004 Hz / 16.6656 ms）\n"
        "EXPECT_HZ = 60.004\n"
        "\n"
        "\n"
        "def estimate_flip(rows: list[dict]) -> float:",
    ),
    (
        "main 允许改口径",
        '    ap.add_argument("--self-test", action="store_true", help="用合成数据自测本检查器")',
        '    ap.add_argument("--expect-hz", type=float, default=EXPECT_HZ,\n'
        '                    help=f"实验室机刷新率（默认 {EXPECT_HZ} Hz）；数据来自别的屏幕时"\n'
        '                         "用来自动标注证据等级")\n'
        '    ap.add_argument("--self-test", action="store_true", help="用合成数据自测本检查器")',
    ),
    (
        "main 把 --expect-hz 传进去",
        "    args = ap.parse_args()\n",
        "    args = ap.parse_args()\n",
    ),
]


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    for name, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            print(f"❌ [{name}] 命中 {n} 次（要求恰好 1 次），中止，未写文件")
            return 1
        if old == new:
            print(f"⏭  [{name}] 无需改动")
            continue
        src = src.replace(old, new)
        print(f"✅ [{name}]")
    # 让 --expect-hz 真正生效：把模块常量按命令行覆盖
    hook = "    if args.self_test:\n"
    if hook in src:
        src = src.replace(
            hook,
            "    global EXPECT_HZ\n"
            "    EXPECT_HZ = args.expect_hz\n"
            + hook,
            1,
        )
        print("✅ [main 应用 --expect-hz]")
    TARGET.write_text(src, encoding="utf-8", newline="\n")
    print(f"\n已写回 {TARGET}（{len(src.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
