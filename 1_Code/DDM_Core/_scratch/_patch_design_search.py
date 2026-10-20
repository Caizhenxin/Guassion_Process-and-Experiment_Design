# -*- coding: utf-8 -*-
"""把 design_search.py 的被试间部分改为「解析 Jacobian 三参数协方差」。

原版只算了 beta_P / d_ref 的线性 WLS，把 tau_P 那个判据写成了 d_ref 的判据
（等于漏判）；这里改为对 (d_ref, beta_P, tau_P) 做 WLS + 数值导数的协方差。
"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\design_search.py")
s = p.read_text(encoding="utf-8")

old_start = s.index("def between_var(")
old_end = s.index("# --------------------------------------------------------------------- 搜索空间")
new_block = '''def between_cov(se_d: float, n_per_level: int, P_levels) -> dict:
    """组层回归 (d_ref, beta_P, tau_P) 的解析协方差（含试次噪声）。

    模型：``d_i = d_ref + beta_P * reg_i(tau_P) + e_i``，
    ``Var(e_i) = (SD_d^2 + se_d^2) / n`` —— 前者是被试间随机效应，后者是该 P 组
    被试层估计的试次噪声。两者一起进权重，才不会把「加人」和「加密 P 水平」
    的收益算成同一件事。``tau_P`` 的识别来自 ``reg`` 相对 P 的曲率，故用数值导数
    进 Jacobian（``beta_P * dreg/dtau_P``）。
    """
    P_arr = np.array(P_levels, float)
    tau = GROUP_TRUTH["tau_P"]
    base = f_P(P_arr, tau) - f_P(P_COMMON_REF, tau)
    h = max(1e-3, 1e-4 * tau)
    dreg = (f_P(P_arr, tau + h) - f_P(P_arr, tau - h)) / (2 * h)
    J = np.column_stack([np.ones_like(base), base, GROUP_TRUTH["beta_P"] * dreg])
    var_i = (SUBJECT_SD["d_ref"] ** 2 + se_d ** 2) / n_per_level
    w = 1.0 / var_i
    cov = np.linalg.pinv(J.T @ (w[:, None] * J))
    return {"cov": cov,
            "sd": np.sqrt(np.maximum(np.diag(cov), 0.0)),
            "dreg_span": float(np.ptp(base)),
            "curv_span": float(np.ptp(dreg)) * abs(GROUP_TRUTH["beta_P"])}


def rel_at(n: int, se_d: float, P_levels) -> dict:
    sd = between_cov(se_d, n, P_levels)["sd"]
    return {"d_ref": float(sd[0] / abs(GROUP_TRUTH["d_ref"])),
            "beta_P": float(sd[1] / abs(GROUP_TRUTH["beta_P"])),
            "tau_P": float(sd[2] / abs(GROUP_TRUTH["tau_P"]))}


def needed_n_between(se_d: float, P_levels, judge: float, which: str,
                     n_max: int = 400) -> dict:
    """二分找满足判据所需的最少组人数（每水平相同 n）。"""
    if rel_at(n_max, se_d, P_levels)[which] > judge:
        return {"n": None, "rel_at_max": rel_at(n_max, se_d, P_levels)[which]}
    lo, hi = 2, n_max
    while lo < hi:
        mid = (lo + hi) // 2
        if rel_at(mid, se_d, P_levels)[which] <= judge:
            hi = mid
        else:
            lo = mid + 1
    return {"n": int(lo), "rel_at_n": rel_at(lo, se_d, P_levels)[which]}


'''
s = s[:old_start] + new_block + s[old_end:]

# 调用处：tau_P 判据改用 which="tau_P"
s = s.replace(
    'nt = needed_n_between(se_d_abs, levels, JUDGE["tau_P"], "d_ref")',
    'nt = needed_n_between(se_d_abs, levels, JUDGE["tau_P"], "tau_P")')
s = s.replace('rows = assemble(TARGET_TRIALS, n_fim)', 'rows = assemble(n_fim)')
s = s.replace('def assemble(n_rep: int, n_fim: int) -> list[dict]:',
              'def assemble(n_fim: int) -> list[dict]:')
s = s.replace('                "n_beta_P": n_bp, "n_tau_P": n_tp, "n_total": n_total,\n                "acc": None,\n',
              '                "n_beta_P": n_bp, "n_tau_P": n_tp, "n_total": n_total,\n')
p.write_text(s, encoding="utf-8", newline="\n")
print("patched, lines", len(s.split("\n")))
