"""让试次图的真值可选（--truth design|qc），并把三处口径落差写进 figures_index.md。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\make_sim_figures.py")
s = p.read_text(encoding="utf-8")


def rep(old: str, new: str, tag: str):
    global s
    assert s.count(old) == 1, (tag, s.count(old))
    s = s.replace(old, new)
    print("ok:", tag)


rep(
    '''def trial_data(seed: int = 2026, n_subjects: int = 3) -> dict:
    """同一真值下模拟若干名被试并合并（提高分单元的试次数，压住抽样噪声）。"""
    import twophase as TP
    import _make_ddm_pilot as GEN

    design, _meta, _mk = GEN.rows_for_subject(1, 12, 1, 0)''',
    '''def pick_truth(choice: str):
    """试次图用哪套真值。

    * ``design``（默认）：``design_grid.TRUTH_LIN`` —— 与 CRLB 图同一设计前提的线性近似
      （``mapping.match_lin_to_exp`` 的残差 0.045），口径可与 Stage 4 对齐。
    * ``qc``：``_make_ddm_pilot.QC_TRUTH`` —— 合成数据集实际用的那套（更接近 Pilot 行为量级，
      但 ``beta_T = 0.45`` 使 T 的漂移跨度只有 0.098，比设计前提弱 3-4 倍）。
    """
    import design_grid as DGRID
    import _make_ddm_pilot as GEN
    if choice == "qc":
        return GEN.QC_TRUTH, "qc（_make_ddm_pilot.QC_TRUTH）"
    return DGRID.TRUTH_LIN, "design（design_grid.TRUTH_LIN）"


def trial_data(seed: int = 2026, n_subjects: int = 3, truth_choice: str = "design") -> dict:
    """同一真值下模拟若干名被试并合并（提高分单元的试次数，压住抽样噪声）。"""
    import twophase as TP
    import _make_ddm_pilot as GEN

    truth, truth_name = pick_truth(truth_choice)
    design, _meta, _mk = GEN.rows_for_subject(1, 12, 1, 0)''',
    "trial_data signature",
)

rep(
    '''        sim = TP.simulate_euler_subject(design, GEN.QC_TRUTH, 0.8,
                                        np.random.default_rng(seed + s), dt=5e-5)''',
    '''        sim = TP.simulate_euler_subject(design, truth, 0.8,
                                        np.random.default_rng(seed + s), dt=5e-5)''',
    "truth in loop",
)

rep(
    '''            "per": per, "truth": GEN.QC_TRUTH.as_dict(), "rho": 0.8,
            "n_subjects": n_subjects}''',
    '''            "per": per, "truth": truth.as_dict(), "truth_name": truth_name, "rho": 0.8,
            "n_subjects": n_subjects}''',
    "truth in return",
)

rep(
    '''    ap.add_argument("--seed", type=int, default=2026)''',
    '''    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--truth", default="design", choices=["design", "qc"],
                    help="试次图的真值：design=design_grid.TRUTH_LIN（与 CRLB 同口径，默认）；"
                         "qc=_make_ddm_pilot.QC_TRUTH（合成数据集实际用的那套）")''',
    "cli truth",
)

rep(
    '''        "* 试次级模拟（1 名被试、576 试次、rho = 0.8）的分单元结果见 `sim_trials_conditions.csv`；"
        "真值参数见 `sim_trials_truth.json`。",
        "",''',
    '''        f"* 试次级模拟（{td['n_subjects']} 名被试 × 576 试次、rho = 0.8）的真值为 "
        f"**{td['truth_name']}**；分单元结果见 `sim_trials_conditions.csv`，真值参数见 "
        "`sim_trials_truth.json`。",
        "",
        "## 三处口径落差（读本目录三张图前必须知道）",
        "",
        "| 对象 | 用的真值 | 影响 |",
        "|---|---|---|",
        "| `fig_sim_crlb.png` | `design_fim.TRUTH`（exp 形式，`beta_P = 1.5`、`P_ref = 120`） | 组层 SE 与所需人数 |",
        "| `fig_sim_trials.png` | `design_grid.TRUTH_LIN`（同一设计前提的线性近似，换算残差 0.045） | 图的形态与量级 |",
        "| `2_Data/Real_Data/_SYNTHETIC_DEMO_v1/` | `_make_ddm_pilot.QC_TRUTH`（lin，`beta_T = 0.45`） | T 的漂移跨度只有 0.098，比设计前提弱 3–4 倍 ⇒ **恢复验证偏保守** |",
        "",
        "* 设计真值在 **P = 0** 组的漂移约 0.0005（`exp` 形式在 `P=0` 处几乎归零）⇒ 期望正确率 0.50，"
        "而 S6-5 的下限是 0.45；两者不相容（首场真实数据 0.440 正落在这一位置）。",
        "* 设计真值的遗漏率约 0.32（`design_fim.TRUTH`）/ 0.35（`TRUTH_LIN`）⇒ 高于 S6-1 的 20% 阈值，"
        "说明设计真值偏悲观，须与 S6-5/S6-1 一起复核。",
        "",''',
    "index notes",
)

p.write_text(s, encoding="utf-8", newline="\n")
print("patched", len(s.split("\n")), "行")
