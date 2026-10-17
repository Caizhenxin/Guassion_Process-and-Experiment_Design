"""自测：`spe_timing_convention.py`（时序口径桥）。

判据分六组：
  A 换算恒等式与单一事实来源
  B 历史 8 组（v2 数据）—— 桥能**恢复** README 的 W 列，并**保物理量**不变
  C v4.1 的 D4 设计点：约束守卫通过；误用造成的 deadline 夸大随 T 单调增
  D ❗门控损害可复现：legacy `apply_window_gate` 把刺激期内按键**静默改写**掉
  E 守卫有牙齿（违反 `W > T + 200` 必须报错）
  F 源码锚点：本文档与桥引用的字句真的在源文件里（防引用漂移）

跑法：`python 1_Code/AutoRA_SPE/check_timing_convention.py`
"""

from __future__ import annotations

import os
import sys

try:  # Windows 控制台默认 GBK，本文件含 ⇄ − 等非 GBK 字符
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import spe_timing_convention as B  # noqa: E402

try:
    import spe_design_model as L  # noqa: E402  (legacy/v2 实现，只读不改)

    _HAS_LEGACY = True
except Exception as _exc:  # pragma: no cover
    L = None
    _HAS_LEGACY = False
    _LEGACY_ERR = repr(_exc)

RESULTS = []


def check(name, cond, detail=""):
    ok = bool(cond)
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def note(name, detail):
    print(f"[note] {name} — {detail}")


# 历史 8 组：**v2 口径**（`1_Code/AutoRA_SPE/README.md` §3 表；W 的语义是"掩蔽后窗口长度"）
#         group,  T_ms, W_legacy_ms, max_RT_obs_ms, T+W(README), W-200(README)
GROUPS = [
    (1, 30.0, 300.0, 332.4, 330.0, 100.0),
    (2, 30.0, 600.0, 632.8, 630.0, 400.0),
    (3, 30.0, 600.0, 635.4, 630.0, 400.0),
    (4, 80.0, 600.0, 683.6, 680.0, 400.0),
    (5, 100.0, 1100.0, 1194.2, 1200.0, 900.0),
    (6, 500.0, 1500.0, 1975.2, 2000.0, 1300.0),
    (7, 30.0, 800.0, 884.3, 830.0, 600.0),
    (8, 80.0, 800.0, 884.3, 880.0, 600.0),
]

# v4.1 的 D4 设计点（`5_Reference/08_工作流/工作流_主计划.md` D4）：W 是**自 onset 的截止时刻**
D4_T_MS = (33.33, 83.33, 149.99, 249.98)
D4_W_MS = (799.98, 1199.9, 1799.9)


def group_A():
    print("\n== A 换算恒等式与单一事实来源 ==")
    if _HAS_LEGACY:
        check(
            "A1 掩蔽时长只有一处事实来源",
            B.MASK_MS == float(L.MASK_MS) == 200.0,
            f"bridge={B.MASK_MS} legacy={L.MASK_MS}",
        )
    else:
        check("A1 掩蔽时长为 200 ms", B.MASK_MS == 200.0, f"(legacy 未导入: {_LEGACY_ERR})")

    worst = 0.0
    for T, W_leg in [(33.33, 766.65), (100.0, 1100.0), (500.0, 1500.0)]:
        W_cur = B.legacy_to_current_W(T, W_leg)
        back = B.current_to_legacy_W(T, W_cur)
        worst = max(worst, abs(back - W_leg))
    check("A2 双向换算恒等（往返误差 < 1e-12 ms）", worst < 1e-12, f"max|Δ| = {worst:.3e}")

    check(
        "A3 v4.1 的窗口开启时刻 = 0（自 onset 即采集按键，对应程序 L14–17）",
        B.current_window_open_ms() == 0.0,
        f"window_open = {B.current_window_open_ms()} ms",
    )

    d_cur = B.current_deadline_ms(500.0, 1500.0)
    d_leg = B.legacy_deadline_ms(500.0, 1500.0)
    check(
        "A4 同一对数字在两套口径下相差恰好 T",
        abs((d_leg - d_cur) - 500.0) < 1e-12,
        f"legacy={d_leg} current={d_cur} 差={d_leg - d_cur}（T=500）",
    )


def group_B():
    print("\n== B 历史 8 组：桥必须恢复 README 的 W 列并保物理量 ==")
    bad_w = []
    bad_win = []
    for g, T, W_leg, _max_rt, t_plus_w, win_legacy in GROUPS:
        W_cur = B.legacy_to_current_W(T, W_leg)
        # 桥把 current 的 W 换回 legacy 的 W，必须回到 README 里的那个数
        if abs(B.current_to_legacy_W(T, W_cur) - W_leg) > 1e-9:
            bad_w.append(g)
        # 物理量：v4.1 的"掩蔽后可按键时长"必须等于 README 的"窗口时长 W−200"
        got = B.current_postmask_pressable_ms(T, W_cur)
        if abs(got - win_legacy) > 1e-9:
            bad_win.append((g, got, win_legacy))
        # README 的 T+W 列必须等于 v4.1 的 deadline（这就是被换算的那个物理量）
        assert abs(B.current_deadline_ms(T, W_cur) - t_plus_w) < 1e-9, (g, T, W_cur, t_plus_w)

    check("B1 桥恢复 README 的 W_legacy 列（8/8）", not bad_w, f"不匹配 group={bad_w}")
    check(
        "B2 保物理量：v4.1 掩蔽后可按键时长 == README 的 W_legacy−200（8/8）",
        not bad_win,
        f"不匹配 {bad_win}",
    )

    # B3：误用方向 —— 把 legacy 的 W 数字直接当 current 的 W 用，后掩蔽窗口会少算 T
    worst = (0.0, None)
    for g, T, W_leg, _m, _tw, win_legacy in GROUPS:
        got = B.current_postmask_pressable_ms(T, W_leg)  # 误用
        err = abs(got - win_legacy)
        if err > worst[0]:
            worst = (err, g)
    check(
        "B3 误用会把'掩蔽后可按键时长'少算恰好 T",
        worst[0] > 0.0,
        f"最大偏离 {worst[0]:.1f} ms（group {worst[1]}）",
    )

    # B4：D2 RT 下界是 legacy 的产物，不是 v4.1 的
    check(
        "B4 legacy 的 D2 下界 = T+200（v4.1 不存在此下界）",
        all(
            abs(B.misuse_distortion(T, W)["gate_floor_if_legacy_ms"] - (T + 200.0)) < 1e-9
            for _g, T, W, _m, _tw, _w in GROUPS
        )
        and B.current_window_open_ms() == 0.0,
        "legacy floor = T+200 ms；v4.1 floor = 0",
    )

    note(
        "实测（README §3）",
        "max RT − (T+W) = +2.4/+2.8/+5.4/+3.6/−5.8/−24.8/+54.3/+4.3 ms；"
        "g7 是唯一大偏离（+54）",
    )


def group_C():
    print("\n== C v4.1 的 D4 设计点 ==")
    ok_valid = True
    bad = []
    for T in D4_T_MS:
        for W in D4_W_MS:
            try:
                B.assert_current_design(T, W)
            except ValueError as exc:
                ok_valid = False
                bad.append((T, W, str(exc)[:60]))
    check("C1 D4 全部 12 个组合满足程序 L22 的 `W > T+200`", ok_valid, f"违反 {bad}")

    # C2：误用造成的 deadline 相对误差 = T/W_cur。**固定 W 时**随 T 严格单调增。
    #     ⚠️ 但整个 D4 网格上不单调 —— W 也在变，所以"单调"这句话必须带作用域。
    mono_cols = {}
    for W in D4_W_MS:
        rels = [B.misuse_distortion(T, W)["deadline_rel_err"] for T in D4_T_MS]
        mono_cols[W] = all(rels[i] < rels[i + 1] for i in range(len(rels) - 1))
    check(
        "C2 固定 W 时，误用造成的相对误差随 T 严格单调增（3/3 列）",
        all(mono_cols.values()),
        "  ".join(f"W={W}:{'✓' if ok else '✗'}" for W, ok in mono_cols.items()),
    )

    # C3：整个网格（12 点）上的范围。误差 = T/W_cur ⇒ 最短 deadline 那一列最糟。
    grid = [
        (T, W, B.misuse_distortion(T, W)["deadline_rel_err"])
        for T in D4_T_MS
        for W in D4_W_MS
    ]
    lo_t, lo_w, lo = min(grid, key=lambda x: x[2])
    hi_t, hi_w, hi = max(grid, key=lambda x: x[2])
    check(
        "C3 网格范围 = 1.85%–31.25%，最大误差落在**最短 deadline**（T=249.98, W=799.98）",
        abs(lo - 33.33 / 1799.9) < 1e-9
        and abs(hi - 249.98 / 799.98) < 1e-9
        and lo_t == 33.33
        and lo_w == 1799.9
        and hi_t == 249.98
        and hi_w == 799.98,
        f"最小 {lo:.3%} @ (T={lo_t}, W={lo_w})；最大 {hi:.3%} @ (T={hi_t}, W={hi_w})",
    )
    note(
        "C3 的作用域",
        "『3%–31%』只在 W=799.98 这一列成立；换成 W=1799.9 就只剩 1.85%–13.89% —— "
        "报范围必须连同它跨的是哪个网格一起报",
    )

    # C4：M_ms 也被多算 T
    d = B.misuse_distortion(249.98, 799.98)
    check(
        "C4 `design_to_params` 的 M_ms 同样多算 T（794 → 1049.96）",
        abs(d["M_ms_correct"] - 799.98) < 1e-9 and abs(d["M_ms_if_legacy"] - 1049.96) < 1e-9,
        f"correct={d['M_ms_correct']} legacy={d['M_ms_if_legacy']}",
    )


def group_D():
    print("\n== D ❗legacy 门控把刺激期内按键静默改写（可复现） ==")
    if not _HAS_LEGACY:
        check("D1 legacy 门控可复现", False, f"legacy 未导入: {_LEGACY_ERR}")
        return

    T_ms = 249.98
    rt = np.array([0.040, 0.120, 0.300, 0.449, 0.700])  # 秒，自刺激 onset
    omit = np.zeros(rt.size, dtype=int)
    resp = np.ones(rt.size, dtype=int)
    floor = L.window_open_s(T_ms)
    gated = L.apply_window_gate(rt, resp, omit, T_ms)
    expect = np.array([floor, floor, floor, floor, 0.700])
    check(
        "D1 legacy 门控 = 把 `rt < T+200` 抬到 `T+200`（不是删行）",
        np.allclose(gated, expect, atol=1e-12),
        f"floor={floor:.3f}s  gated={np.round(gated, 3).tolist()}",
    )

    n_below_T_before = int(np.sum(rt < T_ms / 1000.0))
    n_below_T_after = int(np.sum(gated < T_ms / 1000.0))
    check(
        "D2 刺激期内按键（RT < T）在门控后**不再可被识别**",
        n_below_T_before == 2 and n_below_T_after == 0,
        f"门控前 {n_below_T_before} 个 RT<T → 门控后 {n_below_T_after} 个",
    )

    check(
        "D3 门控人为复现 legacy 伪迹 `min RT == T + 200 ms`",
        abs(float(np.min(gated)) - (T_ms / 1000.0 + 0.2)) < 1e-12,
        f"min(gated)={float(np.min(gated)):.3f}s = T+0.200s",
    )

    cur = B.apply_current_window_gate(rt, omit)
    check(
        "D4 v4.1 门控 = 恒等（刺激期内按键原样保留）",
        np.allclose(cur, rt, atol=0.0),
        f"current={np.round(cur, 3).tolist()}",
    )

    n_kept = int(np.sum(cur < T_ms / 1000.0))
    check(
        "D5 同一批数据：v4.1 门控下 RT<T 的试次全部保留（D5 想抓的就是它们）",
        n_kept == n_below_T_before,
        f"{n_kept}/{n_below_T_before}",
    )


def group_E():
    print("\n== E 守卫有牙齿 ==")
    teeth = 0
    cases = [
        (249.98, 449.98, "W == T+200（边界，必须拒绝：程序要求严格 >）"),
        (249.98, 400.0, "W < T+200"),
        (0.0, 1000.0, "T == 0"),
        (-10.0, 1000.0, "T < 0"),
    ]
    for T, W, why in cases:
        try:
            B.assert_current_design(T, W)
            check(f"E{teeth + 1} 拒绝：{why}", False, "未抛错")
        except ValueError as exc:
            teeth += 1
            check(f"E{teeth} 拒绝：{why}", True, str(exc)[:70])

    good = B.assert_current_design(249.98, 450.0)
    check("E5 合法点（W = T+200+ε）必须通过", good is None, "返回 None，未抛错")

    try:
        B.apply_current_window_gate(np.array([-0.01, 0.5]))
        check("E6 拒绝负 RT", False, "未抛错")
    except ValueError:
        check("E6 拒绝负 RT（自 onset 起算不可能为负）", True, "抛 ValueError")


def group_F():
    print("\n== F 源码锚点（防引用漂移） ==")
    prog = os.path.join(_ROOT, "1_Code", "Experiment", "exp_matlab", "Exp_Design_Formal.m")
    model = os.path.join(_ROOT, "1_Code", "AutoRA_SPE", "spe_design_model.py")
    for path in (prog, model):
        if not os.path.isfile(path):
            check("F0 源文件存在", False, f"缺少 {path}")
            return

    with open(prog, "r", encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    anchors = [
        ("deadline = stimulusFlipTime + W", "v4.1 的 W 语义（程序 L18）"),
        ("responseTime = respAbs - stimulusFlipTime;", "RT 自刺激 onset（L600/L651）"),
        ("W 必须 > T + 200ms", "启动自检约束（L22）"),
        ("W − T − 200ms", "掩蔽后真正可按键时长（L22）"),
        ("respondedByDeadline = double(~isnan(responseTime) && responseTime <= W);", "L656/L984"),
        ("自【刺激 onset】起全程轮询键盘", "刺激期内也采集按键（L14）"),
    ]
    missing = [why for lit, why in anchors if lit not in src]
    check("F1 程序里的六处锚点全部命中", not missing, f"缺失 {missing}")

    with open(model, "r", encoding="utf-8", errors="replace") as fh:
        msrc = fh.read()
    manchors = [
        ("return float(T_ms) + float(W_ms)", "legacy `deadline = T + W`（L119）"),
        ("return float(W_ms) - float(mask_ms)", "legacy `window_duration = W − 200`（L129）"),
        ("rt[mask_ok] = np.maximum(rt[mask_ok], floor)", "门控是**抬高**而非删除（L330）"),
    ]
    mmissing = [why for lit, why in manchors if lit not in msrc]
    check("F2 legacy 模块里的三处锚点全部命中", not mmissing, f"缺失 {mmissing}")


def main():
    print("自测：spe_timing_convention.py（时序口径桥 v2 ⇄ v4.1）")
    print(f"仓库根：{_ROOT}")
    if _HAS_LEGACY:
        print(f"legacy 模块：{os.path.relpath(L.__file__, _ROOT)}")
    else:
        print(f"⚠ legacy 模块未导入（{_LEGACY_ERR}）")
    group_A()
    group_B()
    group_C()
    group_D()
    group_E()
    group_F()

    n_ok = sum(1 for _n, ok, _d in RESULTS if ok)
    n = len(RESULTS)
    print(f"\n===== {n_ok}/{n} =====")
    for name, ok, _d in RESULTS:
        if not ok:
            print(f"  FAIL: {name}")
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
