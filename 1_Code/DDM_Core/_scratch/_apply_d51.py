# -*- coding: utf-8 -*-
"""把决策 D51（被静默吸收的退化必须显式记账）写进 `5_Reference/08_工作流/工作流_主计划.md`。

与 `_apply_d47.py` / `_apply_d48.py` / `_apply_d49.py` / `_apply_d50.py` 同体例，五件事：
1. 写回前先**摘掉附录表格末行之后的所有空行**，再连续插入——否则第 1 行插到空行前、
   第 2 行插到空行后，表格内部会多出一个空行（`check_table_integrity.py` 报
   `split_rows = 1`）。
2. 写回后做**断表断言**：任何"空行的前后都是表格行"⇒ 拒绝写回。
3. **幂等守卫**：已存在 `| **D51** |` 就报错退出。
4. **就地更正 D50 进度行末那句"未查清的观察…待复现定位"**——本轮的取证已经把它查清了，
   用 `~~…~~` 保留原文，后接结论。本项目吃过"过时断言留在文档里被继续引用"的亏
   （`5_Reference/AGENTS.md` §六）。
5. **每处都断言分隔符个数**：这一条已经在本项目抓到过 4 次"表格单元格里写了裸 `|`"
   （D49 的 `\\|t\\|`、`5_Reference/README.md` L100 的 `P(正确\\|匹配)`、D50 的 `\\|z\\|`）。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d51.py [--apply]
不给 `--apply` 时只做干跑。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET = Path("5_Reference/08_工作流/工作流_主计划.md")

# ---- 就地更正：D50 进度行末那句"未查清的观察…待复现定位" --------------------
STALE = ("另有一条**未查清的观察**（方案 §9 末）：4 人 analytic 干跑在 M-T1 拟合一开始"
         "出现 scipy `_numdiff` 的 `invalid value encountered in subtract` ⇒ "
         "**目标函数在某个扰动点上返回了非有限值**，待复现定位")
FIXED = ("~~另有一条**未查清的观察**（方案 §9 末）：4 人 analytic 干跑在 M-T1 拟合一开始"
         "出现 scipy `_numdiff` 的 `invalid value encountered in subtract` ⇒ "
         "**目标函数在某个扰动点上返回了非有限值**，待复现定位~~ —— ✅ **2026-10-14 "
         "已查清（见 D51）**：警告出自 `hier.subject_map_laplace` 的 L-BFGS-B 数值"
         "梯度（`ll_x` 非有限时 `g` 返回 `-inf` 这一**有意的可行性屏障**，取负后不可行"
         "区里目标是 `+inf`）；现象**依赖似然网格 `n_x`**——`n_x=31` 下 LOO 阶段 18 次"
         "非有限目标 / 16 条警告，`n_x=41` 下 0 / 0，而**正式干跑用的正是 `--n-x 31`**；"
         "并已修掉真正的缺陷（`hier.py:192-194` 的注释写「如实标记」但返回 dict 里没有"
         "任何字段 ⇒ `n_nonfinite_loglik` 看不见静默退回初值）")

# ---- 四处插入的锚点（前缀，唯一）与要插入的行 ------------------------------

ANCHORS = [
    # (锚点前缀, 插入位置 after, 该表的列数, 新行)
    (
        "| **D50** |",
        "after",
        5,
        "| **D51** | 2026-10-14 | ✅ **退化必须逐项显式记账，不能用「边际似然有限」来"
        "代替「拟合健康」**：`subject_map_laplace` 的**静默退回初值**与**非有限目标值**"
        "各加独立计数器与出参；非有限 Hessian 抛**可归因**的 `ValueError`；"
        "**可行性屏障本身不动**（改它会改变每一个已拟合的数字） | "
        "① `1_Code/DDM_Core/hier.py:192-194` 的注释写着「优化失败：退回初值，并**如实"
        "标记**」，但返回的 dict 里**没有任何字段**记录它 ⇒ 该被试的「众数」其实是起点、"
        "协方差是**起点处的曲率**、`log_marginal` 也在起点算，三样都当作一个真实最优解"
        "进入 EM 的 M 步与 `loo_matrix`；② 报告里的 `n_nonfinite_loglik` **只看 LOO "
        "矩阵的元素是否有限**（`hier.py:518`），**看不见**上面这个过程；③ 实测（4 人"
        "合成、`n_em=2`、`n_draws=4`、M-T1、analytic）：**LOO 阶段 18 次非有限目标 / "
        "16 条 `_numdiff` 警告，而 `fell_back` = 0 次** ⇒ 两个计数器测的确实是两件事；"
        "④ 该现象**依赖 `n_x`**：`n_x=31` → 18 / 16 / `p_loo = −939.75`，`n_x=41` → "
        "**0 / 0** / −1171.77，而**正式干跑用的是 `--n-x 31`**；⑤ 两个独立仪器（"
        "`_scratch/_probe_nonfinite_obj.py` 的 spy 与 D51 的新计数器）给出**逐位相同**的 "
        "18 / 16 / −939.75 ⇒ 计数可信；⑥ 单被试对照（`_scratch/_probe_nx_pair.py`，只从"
        "区间中点起搜）在 `n_x = 31 / 41 / 81` 上**都是 0 次** ⇒ 退化只出现在**热启动**"
        "搜索上；⑦ 反证：`ELPD 0.000 ± nan` / `k_max nan` 在 `n_x=41` 且 **M-T3**"
        "（**零数值退化**）时**照样出现** ⇒ **LOO 退化与 `_numdiff` 警告是两件独立的事**，"
        "前者是已知的小样本 PSIS 失败（D50 之前的第 27 项） | **`1_Code/DDM_Core/hier.py`**："
        "`subject_map_laplace` 新增 `fell_back` / `n_nonfinite_g`；`hier_fit` 聚合为 "
        "`n_fallback` / `n_nonfinite_g`；`loo_matrix(..., stats=None)` 新增 **`stats` "
        "出参**（**不改返回值类型**，仍是 `np.ndarray`，既有调用点零影响）；`fit_and_loo` "
        "输出 `loo_stats` / `n_fallback_fit` / `n_nonfinite_g_fit`；`stage8_run.fit_group` "
        "退化计数非零时打印并落盘 `n_degenerate_fallback` / `n_degenerate_nonfinite`；"
        "`H` 非有限时抛 `ValueError`（原先是一条**完全无法归因**的 "
        "`numpy.linalg.LinAlgError: Eigenvalues did not converge`）。**三条后果**：① "
        "凡报出的 LOO 结果**必须**连同 `loo_stats` 一起报；② 设计比较/拟合的**网格 `n_x` "
        "成为必须写明的配置**（`--n-x 31` 与自测的 41 不是同一个数）；③ 屏障换有限惩罚的 "
        "A/B 对比被**显式延后**，且在换之前不得把警告当作「已知无害」 | ",
    ),
    (
        "| 2026-10-14 | **9**（内环仪器提升 → D50） |",
        "after",
        5,
        "| 2026-10-14 | **8**（退化记账 + `_numdiff` 根因 → D51） | "
        "**把一条不该出现的 scipy `_numdiff` 警告定性到底，顺手挖出 `n_nonfinite_loglik` "
        "看不见的真缺陷**。① **出处**：SciPy 1.16 的 L-BFGS-B 也走数值梯度"
        "（`_lbfgsb_py.py:413` → `ScalarFunction.fun_and_grad` → `approx_derivative`），"
        "而干跑路径上唯一的 `minimize` 就是 `hier.py:189` ⇒ 警告出自 "
        "`hier.subject_map_laplace` 的众数搜索；② **机制**：`ll_x` 非有限时 `g` 返回 "
        "`-inf`（有意的可行性屏障）⇒ 取负后不可行区里目标是 `+inf` ⇒ "
        "`approx_derivative` 算 `inf - finite` → `nan`，L-BFGS-B 拿到 `nan` 梯度后"
        "**照旧继续**；**最小复现** = 把 `ll_x` 换成处处 `-inf` 的桩（不需要任何真实数据）；"
        "③ **真缺陷**：`hier.py:192-194` 说「如实标记」却没有任何字段记录 ⇒ 补 "
        "`fell_back` / `n_nonfinite_g` / `loo_stats` 三个观测项并修 `H` 非有限的报错；"
        "④ **现象依赖 `n_x`**（31 → 18/16，41 → 0/0），而正式干跑用的是 `--n-x 31`；"
        "⑤ **两个独立仪器逐位一致** ⇒ 仪器交叉验证通过；⑥ 单被试对照证明**只发生在热启动"
        "搜索上**，中点起搜在 31/41/81 上都是 0 次；⑦ **明确分开**：`ELPD 0 ± nan` / "
        "`k_max nan` 在 `n_x=41` 的 **M-T3** 上零退化也出现 ⇒ 那是小样本 PSIS 失败，"
        "**不是**这个现象造成的 | 修改 `1_Code/DDM_Core/hier.py`、"
        "`1_Code/DDM_Core/stage8_run.py`；新建 `1_Code/DDM_Core/_scratch/"
        "_probe_degenerate.py`（牙齿测试 + 真实路径计数，`N_X` 已改为 CLI 参数）、"
        "`1_Code/DDM_Core/_scratch/_probe_nx_pair.py`（单被试 `n_x` A/B 对照）、"
        "`1_Code/DDM_Core/_scratch/check_files.py`（通用体检：`ast.parse` + 裸 LF + 无 BOM "
        "+ 行数）；日志 `1_Code/DDM_Core/_scratch/_probe_degenerate_u8.txt`（n_x=41）、"
        "`1_Code/DDM_Core/_scratch/_probe_degenerate_nx31_u8.txt`（n_x=31）、"
        "`1_Code/DDM_Core/_scratch/check_stage8_run_after_d51_u8.txt` | "
        "🔨 **仍开放**：**(1)** `n_x` 在**正式规模**（40 人 × 576 试次）上是否仍只差这一点"
        "——需要真实数据；若粗网格在正式规模上退化更多，`n_x` 本身要进 D51 的结论；"
        "**(2)** 屏障换有限惩罚的 A/B 对比（必须是一次显式的、单独验证的变更）；"
        "**(3)** `n_x` 对 Stage 9 内环的影响——`stage9_inner` 走的是 "
        "`hier.ddm_subject` 的默认 `n_x`，**与干跑的 `--n-x 31` 不是同一个数**，"
        "设计排序要不要跟着改网格需要单列 | ",
    ),
    (
        "| 2026-10-14 | **新增 D50：",
        "after",
        2,
        "| 2026-10-14 | **新增 D51：退化必须逐项显式记账，不能用「边际似然有限」代替"
        "「拟合健康」；可行性屏障本身不动**。① 一条**不该出现**的 scipy "
        "`_numdiff.py:686` 警告被定性到 `hier.subject_map_laplace` 的 L-BFGS-B 数值梯度"
        "（`g` 在 `ll_x` 非有限时返回 `-inf` 这一有意的屏障 ⇒ 取负后不可行区里是 "
        "`+inf`）；② **真缺陷**：`hier.py:192-194` 的注释写「如实标记」却没有任何字段，"
        "而 `n_nonfinite_loglik` 只看 LOO 矩阵元素 ⇒ 静默退回初值对报告**完全不可见**；"
        "③ 补 `fell_back` / `n_nonfinite_g` / `n_fallback` / `loo_stats` 四个观测项"
        "（`loo_matrix` 用 **`stats` 出参**，不改返回类型 ⇒ 既有调用点零影响）"
        "与一条可归因的 `H` 非有限 `ValueError`；④ **现象依赖网格 `n_x`**（31 → 18 次"
        "非有限目标 / 16 条警告；41 → 0 / 0），而正式干跑用的是 `--n-x 31`；"
        "⑤ **两个独立仪器逐位一致**（18 / 16 / `p_loo = −939.75`）⇒ 仪器可信；"
        "⑥ **反证**：`n_x=41` 的 **M-T3** 零退化也给出 `ELPD 0 ± nan` / `k_max nan` ⇒ "
        "**LOO 退化与 `_numdiff` 警告是两件独立的事**，必须分开报；⑦ 屏障**没有动**"
        "（换有限惩罚会改变优化轨迹从而改变每一个已拟合的数字，而现有全部验证都钉在"
        "当前语义上）⇒ 记录它、不动它 | ",
    ),
    (
        "| `1_Code/AutoRA_SPE/stage9_inner.py`（**新建**，551 行 / 裸 LF）",
        "after",
        2,
        "| `1_Code/DDM_Core/hier.py`（修改，+182/−12 行） + `1_Code/DDM_Core/stage8_run.py`"
        "（修改） + `1_Code/DDM_Core/_scratch/_probe_degenerate.py`（**新建**） + "
        "`1_Code/DDM_Core/_scratch/_probe_nx_pair.py`（**新建**） + "
        "`1_Code/DDM_Core/_scratch/check_files.py`（**新建**） | **D51 的一手证据"
        "（被静默吸收的退化）**。**出处链**：`_numdiff.py:686` 的 `df = [f_eval - f0 …]` "
        "在 `_dense_difference`（`:663`）里，只被 `approx_derivative`（`:278`）调用；"
        "SciPy 1.16 的 `_minimize_lbfgsb` 在 `_lbfgsb_py.py:413` 调 "
        "`_prepare_scalar_function(...)` 并用 `sf.fun_and_grad`；全库 grep 后干跑路径上"
        "唯一的 `minimize` 是 `hier.py:189`（`loo.py:110` 用无导数的 Brent "
        "`minimize_scalar(bounded)`）⇒ **警告出自众数搜索**。**牙齿测试**：把 `ll_x` 换成"
        "处处 `-inf` 的桩，修守卫前得到无法归因的 `numpy.linalg.LinAlgError: Eigenvalues "
        "did not converge`，修守卫后得到带 `fell_back=` / `n_nonfinite_g=` / `converged=` / "
        "`n_evals=` 的 `ValueError`，并在同一段直接打出那条警告原文 ⇒ **最小复现成立**。"
        "**计数对照**（同一份 4 人合成数据、187/191/188/190 试次、`n_em=2`、`n_draws=4`、"
        "`seed=0`、M-T1、analytic）：`n_x=31` → LOO 阶段 **18 次非有限目标 / 16 条警告 / "
        "`p_loo = −939.75`**（与 `_probe_nonfinite_obj.py` 的 spy 计数**逐位相同**）；"
        "`n_x=41` → **0 / 0 / −1171.77**。**单被试 `n_x` 对照**：只从区间中点起搜、不做 "
        "EM/LOO，`n_x = 31/41/81` 上 **都是 0 次非有限**、`Σlog_marg` 相差 ≤ 2.3e-05 ⇒ "
        "退化只出现在**热启动**搜索上。**反证**：`n_x=41` 的 M-T3 在**零数值退化**下仍然 "
        "`ELPD 0.000 ± nan` / `k_max nan` / `p_loo = −1057.79` ⇒ 该规模的 LOO 退化是"
        "**已知的小样本 PSIS 失败**（`n_draws=4`、N=4），与 `_numdiff` 警告**无关**。"
        "**回归**：`check_hier.py` **0 项未通过**（820.3 s，exit 0 —— 新增守卫**没有被任何"
        "既有用例触发**）、`check_stage8_run.py` **15/15**、`check_stage9_inner.py` "
        "**29/29**。**顺带定案**：`likelihood.fim_diagnostics` 的 `cond = ev_max / "
        "ev_pos[0]` **只用正特征值** ⇒ `diag(0,1,1,…)` 报 `cond = 1.0`、`n_bad = 1` ⇒ "
        "Stage 9 的 Objective (D) 必须**同时**查 `cond` 与 `n_bad` | ",
    ),
]


def n_sep(line: str) -> int:
    """该行在 Markdown 表格意义上的分隔符个数（`\\|` 不算）。"""
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    raw = TARGET.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "目标文件有 BOM"
    assert b"\r\n" not in raw, "目标文件不是裸 LF"
    text = raw.decode("utf-8")
    lines = text.split("\n")

    if any(l.startswith("| **D51** |") for l in lines):
        print("❌ 已存在 `| **D51** |` ⇒ 幂等守卫拒绝重复插入")
        return 1

    # ---- 0. 就地更正 D50 进度行末那句"未查清的观察" ----
    hit = [i for i, l in enumerate(lines) if STALE in l]
    if len(hit) != 1:
        print(f"❌ 待更正句命中 {len(hit)} 次（应为 1 次）：{STALE[:40]!r}…")
        return 1
    i_fix = hit[0]
    before = lines[i_fix]
    lines[i_fix] = before.replace(STALE, FIXED)
    if n_sep(lines[i_fix]) != n_sep(before):
        print(f"❌ 就地更正改变了分隔符个数：{n_sep(before)} → {n_sep(lines[i_fix])}")
        return 1
    print(f"✅ 就地更正 L{i_fix+1}（D50 进度行的「未查清的观察」标删并接结论）")

    # ---- 1. 逐处定位并断言列数 ----
    plan = []
    for prefix, where, cols, newline in ANCHORS:
        hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 锚点不唯一：{prefix!r} 命中 {len(hits)} 次")
            return 1
        i = hits[0]
        assert where == "after"
        got = n_sep(lines[i])
        want = cols + 1
        if got != want:
            print(f"❌ 锚点列数不符：{prefix!r} 实测 {got} 个分隔符，期望 {want}（{cols} 列）")
            return 1
        if n_sep(newline) != want:
            print(f"❌ 新行列数不符：期望 {want} 个分隔符，实测 {n_sep(newline)}")
            return 1
        plan.append((i, prefix, cols, newline))
        print(f"✅ 锚点 L{i+1}（{cols} 列 / {got} 分隔符）：{prefix!r}")

    # ---- 2. 摘除"末行之后的所有空行"（附录表在 EOF 前有空行）----
    last_i = plan[-1][0]
    tail = lines[last_i + 1:]
    n_blank = 0
    while tail and tail[0].strip() == "":
        tail.pop(0)
        n_blank += 1
    if n_blank:
        print(f"ℹ️  附录末行之后有 {n_blank} 个空行 ⇒ 收掉后再插入（防断表）")
        lines = lines[:last_i + 1] + tail

    # ---- 3. 从后往前插入（避免行号漂移）----
    for i, prefix, cols, newline in sorted(plan, key=lambda p: -p[0]):
        print(f"   ↳ 在 L{i+1} 之后插入 1 行（{cols} 列）")
        lines.insert(i + 1, newline)

    # ---- 4. 断表断言：空行前后都是表格行 ⇒ 拒绝 ----
    def is_row(s: str) -> bool:
        return s.lstrip().startswith("|")

    for k, l in enumerate(lines):
        if l.strip() != "":
            continue
        prev = next((lines[j] for j in range(k - 1, -1, -1) if lines[j].strip()), None)
        nxt = next((lines[j] for j in range(k + 1, len(lines)) if lines[j].strip()), None)
        if prev is not None and nxt is not None and is_row(prev) and is_row(nxt):
            print(f"❌ 断表断言失败：L{k+1} 是空行，但其前后都是表格行")
            return 1

    # ---- 5. 写回（裸 LF，文件末尾保留单个换行）----
    if not lines or lines[-1] != "":
        lines.append("")
    out = "\n".join(lines).encode("utf-8")
    assert out[:3] != b"\xef\xbb\xbf"
    assert b"\r\n" not in out
    print(f"\n行数 {len(text.split(chr(10)))} → {len(lines)}；字节 {len(raw)} → {len(out)}")
    if not apply:
        print("（干跑，未写回；加 --apply 才写）")
        return 0
    TARGET.write_bytes(out)
    print("✅ 已写回")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
