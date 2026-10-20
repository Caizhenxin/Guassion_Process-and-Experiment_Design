# -*- coding: utf-8 -*-
"""给 design_search.py 加 --group-truth 开关：design（P_ref=120, beta_P=1.5）
与 oracle（P_ref=30, beta_P=0.35）两套组层真值各跑一遍。

加这个开关的原因是 ③ 第一轮跑出一个必须解释的落差：在 design 真值下
P=0/8/32 的漂移被 max(·,0) 截到 0（`drift_magnitude` 恒正），只有 P=120
真正携带信息 ⇒ tau_P 需要 160+ 人/组；而 oracle_power.py 那套真值
（P_ref=30、beta_P=0.35、不截断）下只需 20–40 人。两套真值的结构性差别
必须摆在台面上，否则「多少人才够」这句话没有意义。
"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\design_search.py")
s = p.read_text(encoding="utf-8")

old = '''GROUP_TRUTH = {"d_ref": 0.70, "beta_P": 0.35, "beta_S": 0.16,
               "beta_SP": 0.06, "tau_P": 30.0}'''
new = '''#: 两套组层真值（见 `_scratch/_diag_tau_p.py` 的诊断）：
#: * ``design``  —— `design_fim.TRUTH`：P_ref=120、beta_P=1.5 ⇒ 由于
#:   `drift_magnitude` 对幅度取 `max(0, ·)`，P≤32 的漂移被截到 0，
#:   只有 P=120 真正携带信息（P 设计实际只剩 2 个有效水平）；
#: * ``oracle``  —— `oracle_power.TRUTH`：P_ref=30、beta_P=0.35，四个水平都携带信息。
TRUTHS = {
    "design": {"d_ref": 0.70, "beta_P": 1.50, "beta_S": 0.16,
               "beta_SP": 0.06, "tau_P": 30.0, "P_ref": 120.0},
    "oracle": {"d_ref": 0.70, "beta_P": 0.35, "beta_S": 0.16,
               "beta_SP": 0.06, "tau_P": 30.0, "P_ref": 30.0},
}
GROUP_TRUTH = dict(TRUTHS["design"])
GROUP_P_REF = GROUP_TRUTH["P_ref"]


def use_truth(name: str) -> None:
    """切换组层真值（模块级，供 main 调用）。"""
    global GROUP_TRUTH, GROUP_P_REF
    GROUP_TRUTH = dict(TRUTHS[name])
    GROUP_P_REF = GROUP_TRUTH["P_ref"]'''
assert s.count(old) == 1
s = s.replace(old, new)

# between_cov 里的 P_ref 用组层口径
s = s.replace("base = f_P(P_arr, tau) - f_P(P_COMMON_REF, tau)",
              "base = f_P(P_arr, tau) - f_P(GROUP_P_REF, tau)")

# 报告里写清用的是哪套真值
s = s.replace('f"> 预算 {budget} 试次/人；判据：',
              'f"> 组层真值 = **{GROUP_TRUTH[\'name_label\']}**（P_ref={GROUP_P_REF}、'
              'beta_P={GROUP_TRUTH[\'beta_P\']}）；预算 {budget} 试次/人；判据：')
s = s.replace('"group": GROUP_TRUTH', '"group": GROUP_TRUTH')

# main 增参数
s = s.replace('ap.add_argument("--budget", type=int, default=576, help="试次/人 预算（记录用）")',
              'ap.add_argument("--budget", type=int, default=576, help="试次/人 预算（记录用）")\n'
              '    ap.add_argument("--group-truth", choices=list(TRUTHS), default="design")')
s = s.replace('    n_fim = max(1, (2 if args.quick else args.n_fim))',
              '    n_fim = max(1, (2 if args.quick else args.n_fim))\n'
              '    use_truth(args.group_truth)\n'
              '    GROUP_TRUTH["name_label"] = args.group_truth')
p.write_text(s, encoding="utf-8", newline="\n")
print("patched with --group-truth")
