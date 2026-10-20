# -*- coding: utf-8 -*-
"""让 --group-truth 同时切换被试内仿真的 beta_P / P_ref。

否则 P=0/8 的被试层 CRLB 会继续被 `design_fim.TRUTH`（beta_P=1.5、P_ref=120、
幅度被 max(0,·) 截断）判成「无信息」，组层真值的切换就白做了。
"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\design_search.py")
s = p.read_text(encoding="utf-8")

old = '''def use_truth(name: str) -> None:
    """切换组层真值（模块级，供 main 调用）。"""
    global GROUP_TRUTH, GROUP_P_REF
    GROUP_TRUTH = dict(TRUTHS[name])
    GROUP_P_REF = GROUP_TRUTH["P_ref"]'''
new = '''WITHIN_TRUTH = TRUTH


def use_truth(name: str) -> None:
    """切换组层真值，**同时**把被试内仿真的 beta_P / P_ref 换成同一套。

    这是必须的：`design_fim.TRUTH` 的 beta_P=1.5、P_ref=120，而
    `drift_magnitude` 对幅度取 max(0,·)，于是 P≤32 的漂移被截到 0，被试层
    CRLB 在漂移簇上直接奇异（SE 恰为 0）⇒ 低 P 水平会被当成「无信息水平」
    剔除。若只改组层真值而不改这里，两种口径会跑出完全相同的结果。
    """
    global GROUP_TRUTH, GROUP_P_REF, WITHIN_TRUTH
    GROUP_TRUTH = dict(TRUTHS[name])
    GROUP_P_REF = GROUP_TRUTH["P_ref"]
    WITHIN_TRUTH = TRUTH.replace(beta_P=GROUP_TRUTH["beta_P"],
                                 P_ref=GROUP_P_REF)'''
assert s.count(old) == 1
s = s.replace(old, new)

# subject_se / rel_se 用 WITHIN_TRUTH
s = s.replace('    design = build_design(P, T_levels, W_levels, n_rep)\n    Is = []',
              '    design = build_design(P, T_levels, W_levels, n_rep)\n    Is = []')
s = s.replace('        sim = simulate_subject(design, TRUTH, rng)',
              '        sim = simulate_subject(design, WITHIN_TRUTH, rng)')
s = s.replace('        I, _ = opg_information(tr, NAMES, TRUTH)',
              '        I, _ = opg_information(tr, NAMES, WITHIN_TRUTH)')
s = s.replace('def rel_se(se: dict) -> dict:\n    t = TRUTH.as_dict()',
              'def rel_se(se: dict) -> dict:\n    t = WITHIN_TRUTH.as_dict()')
p.write_text(s, encoding="utf-8", newline="\n")
print("patched within-truth switch")
