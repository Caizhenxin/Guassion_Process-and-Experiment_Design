#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把一次 `stage9_loop.py` 运行的落盘 JSON 折成一份可读的 `stage9_report.md`。

**为什么报告要生成而不是手写**：报告里每个数字都必须能追溯到一次**具体运行**的落盘件。
手写报告最容易出的错是「数字来自上一次运行，而这次口径变了」（`5_Reference/AGENTS.md`
§六 的「忘记同步数字」）。所以本脚本只做一件事：**读一次运行的 payload，把里面的数字
按固定版式摊开**，并把「运行设置」与「作用域」印在最前面。

⚠️ **报告的权威性不超过它读的那次运行**：
  - `budget` 决定四臂各抽了多少点；`front_scope` 决定前沿/推荐点覆盖了多少点
    （D56：这两件事必须分开看，`--budget` 小不影响前沿的正确性，只要 `front_scope` 是全空间）；
  - `(A)` **依赖 `n_fim`**：同一设计 D4 在 `n_fim = 1 / 2 / 12` 下 `(A) = 0.3858 / 0.3519 / 0.268`
    ⇒ 任何 `(A)` 值必须连同 `n_fim` 一起引用，跨 `n_fim` 比较无效；
  - 报告的结论段（推荐点、支配关系）只对**这次运行读到的那个候选空间**成立。

用法：
    python stage9_report.py <payload.json> [输出 .md 路径]
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent

# ❗ D60：判据带宽是「**两个设计的差**」的噪声带，不是「单个设计读数」的噪声带。
# `measure_noise` 量的 `sd_A` 来自**同一个设计**（锚点）在不同种子下的重算；而 §5/§7
# 比较的是两条臂各自选中的**不同设计**（种子由名字哈希导出 ⇒ 独立）⇒ `Var(差) = 2·sd²`
# ⇒ 系数必须是 `2·√2`。用 `2·sd` 会把差的噪声低估 √2 ≈ 1.41 倍（偏宽松）。
# ⚠️ 报告不导入生产模块也要用同一个常数：`check_stage9_report.py` 有一条判据钉住
# 本常量与 `stage9_loop.DIFF_BAND_FACTOR` **逐位相等**（两处必须一起改）。
DIFF_BAND_FACTOR = 2.0 * math.sqrt(2.0)


def _f(v, nd: int = 4) -> str:
    """把数字印成定宽文本；`inf` / `nan` / 缺失一律印 `—`。

    为什么不让 `inf`/`nan` 漏出去：它在报告里会被读成「极好」或「极差」，而两者都错——
    `A_best = inf` 的真实含义是**这条臂在本预算内没有取到可行点**，是「没有数据」。
    """
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(x):
        return "—"
    return f"{x:.{nd}f}"


def _dominates(a: dict, b: dict, tol: float = 1e-12) -> bool:
    """`a` 是否在 `(A 小, B 大)` 上支配 `b`（只对可行点有意义）。"""
    return (float(a["A"]) <= float(b["A"]) + tol) and (float(a["B"]) >= float(b["B"]) - tol)


def _composition(cache: dict) -> dict:
    """把已评估的设计按**闸门成因**分三类（D56 §8 的口径）。

    为什么不用「不可行」一个筐：`feasible=False` 至少有三种成因 —— 遗漏率带外、
    `cond > 1e10`（相关矩阵病态 ⇒ OPG 不可信）、`n_bad > 0`（平均信息矩阵里有
    **数值上不可识别的方向**，定义见 `1_Code/DDM_Core/likelihood.py::fim_diagnostics`）。
    把它们混成一个数字，会把「设计不好」与「数值算不出来」说成同一件事。

    ❗ 两个数值闸门是**两段不同的文本**（`cond=… > 1e+10（病态，相关不可信）` 与
    `n_bad=… > 0（有不可识别方向）`），必须**都认**。只认 `cond` 那一段会在
    「只被 `n_bad` 否决」的设计上静默漏判 —— `n_fim = 1` 这 174 个候选里两者恰好重合
    （123 / 123），所以漏判**看不出来**；换一档 `n_fim` 或换一个真值就可能露出来。
    """
    out = {"n": 0, "feasible": 0, "band_only": 0, "ill_cond": 0, "band_and_ill": 0,
           "other": 0}
    for r in cache.values():
        out["n"] += 1
        if r.get("feasible"):
            out["feasible"] += 1
            continue
        gates = r.get("gates") or []
        band = any("D54" in g for g in gates)
        ill = (any(("cond" in g) or ("n_bad" in g) for g in gates)
               or float(r.get("cond", 0.0)) > 1e10
               or int(r.get("n_bad", 0)) > 0)
        if band and ill:
            out["band_and_ill"] += 1
        elif band:
            out["band_only"] += 1
        elif ill:
            out["ill_cond"] += 1
        else:
            out["other"] += 1
    return out


def _canonical(p: Path) -> str:
    """把 payload 路径渲染成**与调用方式无关**的规范形式。

    ❗ 理由：报告是交付件，必须**可复现** —— 同一个 payload、同一份生成器，无论调用时给的是
    相对路径还是绝对路径，生成的文件都必须逐字相同（否则自测里「交付件 == 现生成结果」这条
    判据会莫名其妙地红）。仓库内的路径一律印成相对仓库根的 `posix` 形式，仓库外的才印绝对路径。
    """
    try:
        root = _HERE.parents[1]  # 1_Code/AutoRA_SPE → 1_Code → 仓库根
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (IndexError, ValueError):
        return p.as_posix()


def _norm_histories(h: dict) -> dict:
    """把 payload 的 `histories` 折成 `compare_arms` 认得的形状。

    只做一件事：兼容 D57 之前的**旧键** `B_at_best_A`（那个键名分叉曾让报告把
    「`B`@`(A)` 最优点」整列静默印成 `—`）。
    """
    out: dict = {}
    for arm, v in (h or {}).items():
        if not isinstance(v, dict):
            continue
        w = dict(v)
        if "B_at_A_best" not in w and "B_at_best_A" in w:
            w["B_at_A_best"] = w["B_at_best_A"]
        out[arm] = w
    return out


def _recompute_verdicts(d: dict, noise: dict) -> tuple[dict | None, str]:
    """用**当前**的 `stage9_loop.compare_arms` 从落盘件离线重算四臂判词。

    返回 `({臂: 判词}, "")`，或 `(None, 失败原因)`。**为什么要重算**：判词是运行时
    生成的冻结产物，而生成它的规则已经改过三代（D55 洗白 → D59 各判各的 → D60
    差的带宽）；只转印、不重算，读者就无从判断手上这份文本该不该信。
    """
    try:
        if str(_HERE) not in sys.path:
            sys.path.insert(0, str(_HERE))
        import stage9_loop as L                      # noqa: PLC0415  （延迟导入：只有复核才需要）
        rows = L.compare_arms(_norm_histories(d.get("histories", {})), noise)
        return ({r["arm"]: r.get("verdict", "") for r in rows}, "")
    except Exception as exc:                          # noqa: BLE001  （复核失败要**说出来**，不能静默）
        return None, f"{type(exc).__name__}: {exc}"


def build(payload_path: Path) -> str:
    raw = payload_path.read_bytes()
    d = json.loads(raw.decode("utf-8"))
    st = d.get("settings", {})
    fs = d.get("front_scope", {})
    noise = d.get("noise", {})
    cache = d.get("cache", {})
    comp = _composition(cache)
    band_a = DIFF_BAND_FACTOR * float(noise.get("sd_A", 0.0))
    band_b = DIFF_BAND_FACTOR * float(noise.get("sd_B", 0.0))

    best = d.get("best", {})
    anchor = d.get("anchor", {})
    d54 = d.get("d54", {})

    L: list[str] = []
    L.append("# Stage 9 优化循环报告（由落盘件生成，请勿手改）")
    L.append("")
    L.append(f"- 日期：{__import__('datetime').date.today().isoformat()}")
    L.append("- 状态：✅现行（由 `1_Code/AutoRA_SPE/stage9_report.py` 从一次运行的 payload 生成）")
    L.append(f"- 依据：`{_canonical(payload_path)}`（{len(raw)} 字节、"
             f"sha256 `{hashlib.sha256(raw).hexdigest()[:16]}…`）")
    L.append(f"- 权威性：**不超过这次运行** —— 结论只对本次读到的候选空间与这次 `n_fim` 成立")
    L.append("")

    L.append("## 1. 运行设置与作用域（读结论前必须先看这一节）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 冻结 Objective 哈希 `spec_sha256` | `{d.get('spec_sha256', '?')}` |")
    L.append(f"| `budget`（每条臂的评估预算） | {st.get('budget')} |")
    L.append(f"| `n_fim`（每个设计的 FIM 试次数） | **{st.get('n_fim')}** |")
    L.append(f"| `n_subjects` / `rho` / `seed` | {st.get('n_subjects')} / "
             f"{_f(st.get('rho'), 3)} / {st.get('seed')} |")
    L.append(f"| 候选空间规模 `n_candidates` | {fs.get('n_candidates')} |")
    L.append(f"| **算前沿前缓存里已有** `n_cached_before_full_eval` | **{fs.get('n_cached_before_full_eval')}** |")
    L.append(f"| **前沿/推荐点的实际覆盖** `n_evaluated` | **{fs.get('n_evaluated')}** |")
    L.append(f"| 前沿点数 `n_front` | {fs.get('n_front')} |")
    L.append(f"| 内环评估调用 `n_evals` / 内环耗时 | {d.get('n_evals')} 次 / "
             f"{_f(d.get('seconds'), 0)} s |")
    L.append("")
    if fs.get("n_evaluated") == fs.get("n_candidates"):
        L.append("✅ `n_evaluated == n_candidates`：**前沿与推荐点是在整个候选空间上算的**"
                 "（D56 的判据）。")
    else:
        L.append(f"⚠️ `n_evaluated = {fs.get('n_evaluated')} ≠ n_candidates = "
                 f"{fs.get('n_candidates')}`：**前沿/推荐点只覆盖了一部分候选空间**，"
                 f"下面的「推荐点」不可当作空间最优（D56）。")
    L.append("")
    L.append(f"⚠️ `(A)` **依赖 `n_fim`**：本报告的 `(A)` 只在 `n_fim = {st.get('n_fim')}` 内可比。")
    L.append("")

    L.append("## 2. 噪声标定（判据的两根带子都由它决定，不能来自期望）")
    L.append("")
    L.append(f"`n_repeats = {noise.get('n_repeats')}`（同一锚点设计在不同 CRN 种子下重算）")
    L.append("")
    L.append("| 量 | 逐次读数 | `sd` | `2·sd`（**单设计**读数带，⚠️不是判据带） |")
    L.append("|---|---|---|---|")
    for k, lab in (("A", "`(A)` 归一化信息量（越小越好）"), ("B", "`(B)` 精度（越大越好）"),
                   ("omission", "遗漏率"), ("J", "`J`（参考：受 (C) 支配，噪声大）"),
                   ("C", "`(C)` 遗漏率罚分")):
        vals = noise.get(k, [])
        L.append(f"| {lab} | {', '.join(_f(v) for v in vals)} | "
                 f"`{_f(noise.get('sd_' + k))}` | **`{_f(2.0 * float(noise.get('sd_' + k, 0.0)))}`** |")
    L.append("")
    L.append(f"`alpha = max(sd_J², 1e-12) = {_f(noise.get('alpha'), 6)}`（BO 的观测噪声先验）。")
    L.append("")
    L.append(f"❗ **判据用（D60：`(A)`/`(B)` 比的是两个不同设计的差）**："
             f"`2·√2·sd_A = {_f(band_a)}`、`2·√2·sd_B = {_f(band_b)}`。"
             f"上表里的 `2·sd_A = {_f(2.0 * float(noise.get('sd_A', 0.0)))}`、"
             f"`2·sd_B = {_f(2.0 * float(noise.get('sd_B', 0.0)))}` 是**单个设计读数**的带，"
             f"比判据带窄 `√2 ≈ 1.41` 倍 —— 拿它判「差异显著」是偏宽松的，"
             f"D60 之前的所有判词都受这个影响。")
    L.append("")
    # ❗ D59：把**标定种子族**印出来 —— `sd` 的可靠性同时取决于"重抽几次"和"种子从哪来"。
    #    实测（`_scratch_anchor_seed_scan.py`，`n_fim = 1`、锚点 D4）：
    #    `cell_seed(name, base + 791_900 + 37k)`（同族**算术邻居**）给 `sd_A = 0.004779`，
    #    48 个**无关**种子给 `0.018933`（4.0 倍），另一族算术邻居给 `0.015623`（0.83 倍）
    #    ⇒ 不是"邻居相关"，是那一族恰好抽在密集区（`A` 的种子分布重尾）。
    _seeds = noise.get("seeds")
    if not isinstance(_seeds, list) or not _seeds:
        L.append("⚠️ **本落盘件没有记录标定种子**（D59 之前的版本）⇒ 无法复核 `sd` 是"
                 "「独立重抽」还是「同一族算术邻居」，而后者实测会把 `sd_A` **低报约 4 倍**"
                 "（`n_fim = 1`：`0.0048` vs `0.0189`）"
                 "⇒ **上面两根带子与 `alpha` 都要按这个幅度打折看**。")
    else:
        L.append(f"标定种子族：`{noise.get('family', '（未记录）')}`")
        L.append("")
        L.append(f"标定种子（{len(_seeds)} 个）：`"
                 f"{', '.join(str(int(s)) for s in _seeds)}`")
    L.append("")
    # ❗ `sd` 本身也是估计量：`n_repeats` 个样本的样本标准差，其相对不确定度 ≈ `1/√(2(n−1))`。
    #    只用 2 次重复时该不确定度约 71% ⇒ **判据带宽本身就不确定**，而 `alpha = sd_J²`
    #    的相对不确定度是它的两倍。实测（`1_Code/AutoRA_SPE/_scratch_noise_repeats.py`，
    #    同一锚点、`n_fim = 12`）：2 次重复给 `sd_J = 0.4056 ⇒ alpha = 0.165`，
    #    6 次重复给 `sd_J = 0.6272 ⇒ alpha = 0.393`（**2.4 倍**）；`sd_B` 0.0386 → 0.0509。
    #    `alpha` 直接决定 BO 臂的取点 ⇒ 拿它比较 BO 与基线时必须把重复数印出来。
    _nr = int(noise.get("n_repeats") or 0)
    if _nr >= 2:
        _rel = 1.0 / math.sqrt(2.0 * (_nr - 1.0))
        if _nr < 4:
            L.append(f"⚠️ 本次标定只用 **{_nr}** 次重复 ⇒ **`sd` 自身的不确定度约 {_rel * 100:.0f}%**"
                     f"、`alpha = sd_J²` 约 {2 * _rel * 100:.0f}%"
                     f"（样本标准差的相对不确定度 ≈ `1/√(2(n−1))`）⇒ 上面两根带子与 `alpha`"
                     f"都有这个量级的不确定度，**不要当成精确门槛**。要把它们钉死，"
                     f"至少用 6 次重复（`--noise-repeats 6`）。")
        else:
            L.append(f"标定用 **{_nr}** 次重复 ⇒ `sd` 自身的不确定度约 {_rel * 100:.0f}%、"
                     f"`alpha = sd_J²` 约 {2 * _rel * 100:.0f}%。")
        L.append("")

    L.append("## 3. 可行域构成（D54 的遗漏率带 + 数值条件数）")
    L.append("")
    scope_ok = fs.get("n_evaluated") == fs.get("n_candidates")
    L.append(f"冻结遗漏率带 = `[{d54.get('omission_band', ['?', '?'])[0]}, "
             f"{d54.get('omission_band', ['?', '?'])[1]}]`、判据 `{d54.get('criterion')}`；"
             f"带外被否决 {d54.get('n_band_rejected')} 个、可行 {d54.get('n_feasible')} 个。")
    if not scope_ok:
        L.append(f"⚠️ 上面两个数字只在 `n_evaluated = {fs.get('n_evaluated')}` 个候选上算过，"
                 f"**不是全空间真值**（D56 的第二处受害者：`n_band_rejected` 曾在部分空间下报 22、"
                 f"全空间真值 93）。")
    L.append("")
    L.append("| 类别 | 个数 | 说明 |")
    L.append("|---|---|---|")
    L.append(f"| 可行 | {comp['feasible']} | 遗漏率在带内、`cond ≤ 1e10`、`n_bad = 0`（无不可识别方向） |")
    L.append(f"| 只被遗漏率带否决 | {comp['band_only']} | 数值健康但遗漏率带外 ⇒ 罚分改成约束后不进可行集 |")
    L.append(f"| **数值病态** | {comp['ill_cond']} | `cond > 1e10`（相关矩阵病态 ⇒ OPG 不可信）**或** `n_bad > 0`（平均信息矩阵里有不可识别的方向） |")
    L.append(f"| 两者兼有 | {comp['band_and_ill']} | — |")
    if comp["other"]:
        L.append(f"| 其它闸门 | {comp['other']} | 见逐设计 `gates` |")
    L.append(f"| 合计 | {comp['n']} | — |")
    L.append("")
    L.append("`n_bad` 是 `1_Code/DDM_Core/likelihood.py::fim_diagnostics` 数出来的**不可识别方向条数**"
             "（平均信息矩阵里 `ev < max(ev_max * 1e-8, 1e-300)` 的特征值个数）；它说的是"
             "「这个设计有方向不可识别」，**不是**「数据里有若干试次坏了」——两者要采取的行动不同"
             "（前者改设计，后者查采集）。`cond` 与 `n_bad` 是两个判据；"
             "D61 实测：`n_fim = 1` 与 `n_fim = 12` 两档下 `n_bad > 0` 的设计**逐设计相同**"
             "（都 123 个）⇒ 这两条判据在本候选空间里恰好重合，而这是**候选空间的结构性质**。"
             "`n_fim` 改变的是**遗漏率带内的成员**，不是病态集。")
    L.append("")
    if comp["ill_cond"] + comp["band_and_ill"] > 0.5 * max(comp["n"], 1):
        L.append(f"❗ **半数以上的候选是被数值条件数刷掉的**（{comp['ill_cond'] + comp['band_and_ill']}"
                 f"/{comp['n']}）⇒ 「可行集为什么这么小」的答案可能主要不在设计上。"
                 f"**D61 已在正式 `n_fim = 12` 下重测这一节**：仍 123/174、且 `n_bad > 0` 的设计"
                 f"**逐设计相同** ⇒ 这是候选空间的**结构性质**（`r24` + 两档 `W` 型设计的 `cond` "
                 f"在 `n_fim` 1 → 12 时只从 2.231e15 走到 2.013e15、`n_bad` 一直是 1），"
                 f"不是 `n_fim` 太小造成的。")
        L.append("")

    L.append("## 4. 四路曲线（每条臂「至今最好的 `(A)`」，越小越好）")
    L.append("")
    arms = [a for a in ("grid", "random", "manual", "bo") if a in (d.get("histories") or {})]
    hist = d.get("histories", {})
    L.append("| 评估序号 | " + " | ".join(f"`{a}`" for a in arms) + " |")
    L.append("|---" * (len(arms) + 1) + "|")
    n_steps = max((len(hist[a].get("best_A_so_far", [])) for a in arms), default=0)
    for i in range(n_steps):
        cells = []
        for a in arms:
            cur = hist[a].get("best_A_so_far", [])
            cells.append(_f(cur[i]) if i < len(cur) else "—")
        L.append(f"| {i + 1} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("| 臂 | 抽到的设计数 | 参考 `best J` | 内环耗时 |")
    L.append("|---|---|---|---|")
    for a in arms:
        h = hist[a]
        L.append(f"| `{a}` | {len(h.get('picked', []))} | {_f(h.get('best_J'))} | "
                 f"{_f(h.get('seconds'), 1)} s |")
    L.append("")

    L.append("## 5. 四臂裁决（判据只建立在 `(A)/(B)` 上，差异必须超噪声带）")
    L.append("")
    L.append("⚠️ 表里的 `B`@同一点必须是**同一个点**的 `B`（键名 `B_at_A_best`，与 "
             "`histories[arm]` 里**同名** ⇒ 配对是结构性保证，不是靠人工抄对）。"
             "曾经两处用了两个名字，报告读错一个键就把这一列静默印成 `—`。")
    L.append("")
    L.append("| 臂 | `(A)` 最小可行点 | `B`@同一点 | 可行点数 | 参考 `best J` | `ΔA` | `ΔB` |")
    L.append("|---|---|---|---|---|---|---|")
    for r in d.get("compare", []):
        L.append(f"| `{r['arm']}` | {_f(r.get('A_best'))} | {_f(r.get('B_at_A_best'))} | "
                 f"{r.get('n_feasible')} | {_f(r.get('best_J'))} | {_f(r.get('dA_vs_best'))} | "
                 f"{_f(r.get('dB_vs_best'))} |")
    L.append("")
    for r in d.get("compare", []):
        L.append(f"- **`{r['arm']}`**：{r.get('verdict', '')}")
    L.append("")
    # ❗ D59/D60：判词是**运行时**生成的冻结产物，而生成它的规则已经改过三代。
    # 所以不能只满足于「自报版本号」——直接从 `histories` + `noise` 用**当前**的
    # `stage9_loop.compare_arms` 离线重算一遍，再与转印的判词比对：一致 ⇒ 转印可信；
    # 不一致 ⇒ **以重算为准**（转印段只当作"落盘件里原本写了什么"的记录）。
    _vl = d.get("verdict_logic")
    if _vl:
        L.append(f"落盘件自报的裁决规则版本：**{_vl}**。")
    else:
        L.append("⚠️ **本落盘件没有记录裁决规则版本**（D59 之前的运行）⇒ 上面的判词可能由已被"
                 "修正的规则生成（例如在 `ΔA` 落在噪声带内时**借 `ΔB` 的带子**下结论）。")
    L.append("")
    _fresh, _ferr = _recompute_verdicts(d, noise)
    if _fresh is None:
        L.append(f"⚠️ **离线复核失败**（`{_ferr}`）⇒ 上面的判词**未经复核**，"
                 f"不得当作当前规则下的结论。")
    else:
        L.append("**离线复核**（当前规则 `stage9_loop.compare_arms`，读本落盘件的 "
                 "`histories` + `noise`，带宽按 D60 的 `2·√2·sd`）：")
        L.append("")
        for r in d.get("compare", []):
            L.append(f"- **`{r['arm']}`**：{_fresh.get(r['arm'], '（重算里没有这条臂）')}")
        L.append("")
        _diff = [r["arm"] for r in d.get("compare", [])
                 if _fresh.get(r["arm"]) != r.get("verdict", "")]
        if not _diff:
            L.append("✅ 与上面**转印**的判词逐字一致 ⇒ 转印的文本就是当前规则生成的。")
        else:
            L.append(f"⚠️ **与上面转印的判词不一致的臂：{', '.join(f'`{a}`' for a in _diff)}** "
                     f"⇒ 转印的判词由旧规则生成，**以本节的复核文本为准**"
                     f"（上面那一段只是「落盘件里原本写了什么」的记录）。")
    L.append("")
    # 只在落盘件真的带 `inf`/`nan` 时才告警（否则这条告警会变成噪音）。
    stale = any(
        not math.isfinite(float(r.get("A_best", float("nan"))))
        or not math.isfinite(float(r.get("B_at_A_best", float("nan"))))
        for r in d.get("compare", [])
    )
    if stale:
        L.append("⚠️ 上面的裁决文本**逐字来自落盘件**（生成报告的脚本不重算那一段），而本落盘件里"
                 "有臂的 `(A)` 不是有限值 ⇒ 它可能带着已被修正的措辞 —— 例如把 `A_best = ∞`"
                 "（该臂在预算内没取到可行点）印成「比次好臂的 A 小 inf ⇒ 最好」，即"
                 "**把「没有数据」说成「大幅领先」**。判据：一条臂的 `(A)` 列若印成 `—`"
                 "（即 `A_best` 非有限），它在本次运行里**没有可行点**，任何以它为对照的比较"
                 "都无意义。**以本节的离线复核文本为准**（它有 D57 的 `∞` 分支）。")
        L.append("")

    L.append("## 6. Pareto 前沿（可行集内 `(A)` 小、`(B)` 大的非支配点）")
    L.append("")
    front = d.get("pareto", [])
    if not front:
        L.append("（空：本次运行没有可行点）")
    else:
        L.append("| # | 设计 | `(A)` | `(B)` | `J`（参考） |")
        L.append("|---|---|---|---|---|")
        for i, p in enumerate(front, 1):
            L.append(f"| {i} | `{p['name']}` | {_f(p.get('A'))} | {_f(p.get('B'))} | "
                     f"{_f(p.get('J'))} |")
    L.append("")

    L.append("## 7. 推荐点与「D4 离最优多远」")
    L.append("")
    if best:
        L.append(f"- **推荐点**（D54：可行集内 `(A)` 最小，判据 `{best.get('criterion')}`）："
                 f"`{best.get('name')}`")
        L.append(f"  - `(A) = {_f(best.get('A'))}`、`(B) = {_f(best.get('B'))}`、"
                 f"`J = {_f(best.get('J'))}`")
        rec = cache.get(best.get("name"), {})
        if rec:
            cond = rec.get("cond")
            cond_s = f"{cond:.2e}" if isinstance(cond, (int, float)) else "—"
            L.append(f"  - 遗漏率 `{_f(rec.get('omission'), 3)}`（带 `{rec.get('omission_band')}`）、"
                     f"`cond = {cond_s}`、不可识别方向 `{rec.get('n_bad')}` 条")
        # ❗ D61：「最优」这个词的信息量取决于可行集内部铺开多少。带宽既然按**差**的噪声带
        #    算（D60 的 `2·√2·sd`），就必须拿它去量可行集内部：若与最优**不可分辨**的设计
        #    不止一个，那么上面点名的推荐点只是**可行带内的一个点**，不是被数据选出来的
        #    唯一解 ⇒ 论文里不得写成「唯一最优」。（实测：`n_fim = 1` 与 `n_fim = 12`
        #    两档点名的推荐点是两个不同的设计 —— 见 D61。）
        _feas_all = [r for r in cache.values() if r.get("feasible")]
        if len(_feas_all) >= 2 and band_a > 0:
            _as = sorted(float(r["A"]) for r in _feas_all)
            _amin, _amax, _amed = _as[0], _as[-1], _as[len(_as) // 2]
            _near = [r for r in _feas_all if float(r["A"]) - _amin < band_a]
            _near_b = ([r for r in _feas_all
                        if abs(float(r.get("B", float("nan"))) - float(best.get("B", float("nan"))))
                        < band_b] if band_b > 0 else [])
            L.append(f"- **可行集里「最优设计」的身份是否唯一**（D61，从 `cache` 现算）："
                     f"可行 **{len(_feas_all)}** 个，`(A)` 最小 `{_f(_amin)}` / 中位 `{_f(_amed)}` "
                     f"/ 最大 `{_f(_amax)}` ⇒ 极差 `{_f(_amax - _amin)}` = "
                     f"**{_f((_amax - _amin) / band_a, 1)} 倍**判据带 `2·√2·sd_A = {_f(band_a)}`")
            L.append(f"  - ⇒ 与最优**不可分辨**（`ΔA < 2·√2·sd_A`）的可行设计："
                     f"**{len(_near)} / {len(_feas_all)}**；`(B)` 上与推荐点不可分辨的："
                     f"**{len(_near_b)} / {len(_feas_all)}**")
            L.append(f"  - ⇒ 上面点名的推荐点只是**可行带内的一个点**（`(A)` 上还有 "
                     f"**{len(_near) - 1}** 个设计与其不可分辨）⇒ 论文里**不得**写成"
                     f"「唯一最优」；换一个 `n_fim` 就可能换一个推荐点（D61 实测："
                     f"`n_fim = 1` 与 `n_fim = 12` 两档点名的是**两个不同设计**）。")
        elif _feas_all:
            L.append(f"- **可行集里「最优设计」的身份是否唯一**（D61）：可行集只有 "
                     f"**{len(_feas_all)}** 个设计 ⇒ 本落盘件里不存在「谁更优」的问题"
                     f"（⚠️ 这只是**可行域本身小**，不代表它在更宽的设计空间里最优）。")
    if anchor:
        # ⚠️ `anchor` 段只带 name/A/B/J/feasible；遗漏率与闸门文本要去 `cache` 里取同一个设计
        # 的完整记录（否则会印出 `—`，而「锚点是否可行」恰恰是本节最要紧的一行）。
        arec = cache.get(anchor.get("name"), {})
        L.append(f"- **锚点 D4**（Stage 5 已定稿、据以准备正式采集）：`{anchor.get('name')}`")
        L.append(f"  - `(A) = {_f(anchor.get('A'))}`、`(B) = {_f(anchor.get('B'))}`、"
                 f"`J = {_f(anchor.get('J'))}`、遗漏率 `{_f(arec.get('omission'), 3)}`"
                 f"（带 `{arec.get('omission_band')}`）、可行 = **{anchor.get('feasible')}**")
        for g in (arec.get("gates") or []):
            L.append(f"    - 闸门：{g}")
        if best:
            dA = float(anchor.get("A", float("nan"))) - float(best.get("A", float("nan")))
            dB = float(best.get("B", float("nan"))) - float(anchor.get("B", float("nan")))
            L.append(f"  - **离最优多远**：`ΔA = {_f(dA)}`（推荐点更小）⇒ "
                     f"**{_f(dA / band_a if band_a else float('nan'), 1)} 倍** 判据带宽 "
                     f"`2·√2·sd_A = {_f(band_a)}`（D60：比的是**两个不同设计**的差）；"
                     f"`ΔB = {_f(dB)}`（推荐点更大 = 更好）")
            # ❗ D59/D60：这个「几倍」的分母来自 n_repeats 次重抽**且**要按差的噪声带算。
            #    `n_fim = 1` 下同一份读数实测可印成 3.0 倍或 0.77 倍（旧族 sd_A = 0.0048 vs
            #    48 个无关种子 0.0189）⇒ 必须把这句话钉在同一节里，不能只靠在 §2 提一句。
            L.append(f"  - ⚠️ **这个倍数只与标定种子样本一样可靠**（D59）：分母 "
                     f"`2·√2·sd_A` 由 `{noise.get('n_repeats')}` 次重抽估出"
                     f"{'（本落盘件**未记录**标定种子 ⇒ 无法复核它是独立重抽还是同族算术邻居）' if not noise.get('seeds') else ''}。"
                     f"`n_fim = 1` 下实测：旧标定族的 `sd_A = 0.0048`、48 个**无关**种子的 "
                     f"`sd_A = 0.0189`（**4.0 倍**）⇒ 同一份 `ΔA = 0.0412` 在旧族下印成 "
                     f"**3.0 倍**带子、在无关族下只有 **0.77 倍**带子（**连一根带都没到**）。"
                     f"**换带重判**用 "
                     f"`python -u 1_Code/AutoRA_SPE/_scratch_reverdict.py <payload.json> <sd_A> <sd_B>`"
                     f"（它内部调的就是当前 `compare_arms`，系数已含 D60 的 `2·√2`）。")
            if dA > band_a:
                L.append(f"  - ⇒ 锚点在 `(A)` 上比推荐点**显著更差**（`ΔA > 2·√2·sd_A`），"
                         f"这不是噪声。")
            else:
                L.append("  - ⇒ 锚点与推荐点在 `(A)` 上**不可分辨**（`ΔA ≤ 2·√2·sd_A`）。")
            # ❗ D60 同族第五处读数：推荐点是**极值统计量**（可行集里 `(A)` 最小的那个）
            #    ⇒ 自己带 *winner's curse*。实测（`n_fim = 1`、32 个无关种子、逐设计）：
            #    推荐点的读数比它自己的种子均值低 2.26σ、锚点高 1.58σ ⇒ 单种子 CRN 下的
            #    「谁更好」可能是抽签结果。**只作为举例**（那是 n_fim = 1 与当时那批设计），
            #    本 payload 自己的种子均值必须另算 —— 断言式结论不能超出测量范围。
            L.append("  - ⚠️ **推荐点自身带有选择偏差**（D60）：`(A)` 是 MC 估计量"
                     "（`n_fim = 1` 下逐设计实测 `sd_A = 0.0180 / 0.0186 / 0.0213`，同量级），"
                     "而推荐点是**可行集内 `(A)` 最小的那个** ⇒ 它是极值统计量、系统性偏低"
                     "（*winner's curse*）。**举例**（`n_fim = 1`、32 个无关种子、D59 之前"
                     "那份 payload 的锚点与 CRN 口径推荐点）：推荐点的读数比它自己的种子均值"
                     "**低 2.26σ**、锚点**高 1.58σ** ⇒ 那次按种子均值比，**锚点反而更优约 0.029**。"
                     "**本落盘件的种子均值见下一条**；换一份 payload 则必须另算："
                     "`python -u 1_Code/AutoRA_SPE/_scratch_mean_A_rank.py <payload.json> [n_seeds] [n_fim]`"
                     "（它对 CRN 口径的前几名逐个扫种子，给出按均值的排名与每个设计的偏差 σ）。")
            L.append("    - ❗ **口径提醒**：那个脚本的**配对**比较走 `_scratch_anchor_seed_scan._one()`，"
                     "它把种子**直接**交给 `inner_eval` ⇒ 同一份种子表下**所有设计共用同一条随机流**"
                     "（共享 CRN），实测逐设计读数正相关（`_scratch_pair_corr.py`：ρ ≈ +0.49…+0.85）"
                     "⇒ 配对标准误偏小、t 值偏灵敏。而**本报告的判词**（第 5 节）走 "
                     "`stage9_loop.Evaluator._raw`，用 `seed=cell_seed(d[\"name\"], base_seed)` ⇒ "
                     "**每个设计各自一条流**、两条臂相互独立 ⇒ 带宽必须是 `2·√2·sd`（D60）。"
                     "**两处口径都能用，但不可混用**：种子平均的配对结论不能替代第 5 节的判词。")
            # ❗ D62：上一段是「本 payload 没算过种子均值」的告警。D62 把它算出来了（正式
            #    `n_fim = 12`、32 个无关种子）—— 结论是**锚点在期望意义上更好**，与 CRN 单点
            #    读数相反。这条必须写进报告，否则「推荐点更小 0.0378」会被读成「推荐点更好」。
            L.append("    - ✅ **D62 实测：本依据件的种子平均已经算过**（`n_fim = 12`、32 个无关种子、"
                     "`1_Code/AutoRA_SPE/_scratch_mean_A_rank_nfim12_u8.txt`）：锚点 D4 的种子均值 "
                     "`(A) = 0.3401 ± 0.0014`，按 CRN 口径进入排名的 6 个可行设计均值 `0.3747–0.3852`，"
                     "**全部**比锚点差（配对 `t = +25.5…+41.1`，最大差 `0.0451`）⇒ **在期望意义上锚点更好**。"
                     "`n_fim = 1` 那档同向（锚点 `0.3573`、推荐点 `0.3867`）。")
            L.append("    - ⚠️ 但这**不改变推荐点**：锚点被 D54 的遗漏率带排斥（`0.3546` 远在 "
                     "`[0.05, 0.2]` 外）⇒ 它是「`(A)` 更好但**不可执行**」；推荐点仍然是**可行集**里 "
                     "`(A)` 最小的那个。论文里这两个事实要**同时**报，只说一个都会误导。")
            # D64：D60 的带宽用 `2·√2·sd`，前提是**两条臂的 σ 同量级**（同方差）。上一轮只在
            #   `n_fim = 1` 上验过 3 个设计（1.18 倍）。本轮那份 32 种子的逐设计读数里正好有
            #   `n_fim = 12` 的 7 个设计 ⇒ 可以直接给出正式 `n_fim` 下的同方差证据。
            L.append("    - ✅ **D64 实测：同方差假定在正式 `n_fim` 下也站得住**"
                     "（`_scratch_pair_corr_nfim12_u8.txt`，源数据 = 上一段那份 32 种子的逐设计读数）："
                     "7 个设计的逐种子 `sd_A` 落在 **0.0068–0.0085**（最大/最小 = **1.24 倍**）；"
                     "`n_fim = 1` 那档 3 个设计是 1.18 倍 ⇒ 两档都不支持「不同设计的 σ 差好几倍」，"
                     "这正是 `2·√2·sd` 里那个 `√2` 可以取**常数**的前提。")
        # 从 cache 现算支配关系（落盘件自足，不依赖任何中间态）
        feas = [r for r in cache.values() if r.get("feasible")]
        dom = [r for r in feas if _dominates(r, anchor)] if anchor else []
        dom_wo_self = [r for r in dom if r.get("name") != anchor.get("name")]
        L.append(f"  - **支配它的可行设计**：{len(dom_wo_self)} 个"
                 f"（可行集共 {len(feas)} 个）")
        if dom_wo_self:
            s = min(dom_wo_self, key=lambda r: float(r["A"]))
            L.append(f"    - 最强者 `{s.get('name')}`：`(A) = {_f(s.get('A'))}`、"
                     f"`(B) = {_f(s.get('B'))}`、遗漏率 `{_f(s.get('omission'), 3)}`"
                     f"（**在带内** ⇒ 可执行）")
            L.append(f"    - ⇒ 锚点既**不可行**（遗漏率带外），也被 {len(dom_wo_self)} 个"
                     f"**可行**设计在 `(A,B)` 上支配（D56 更正 D55 的那条）")
        else:
            L.append("    - ⇒ 没有可行设计在 `(A,B)` 上支配锚点（**只在本次读到的候选空间内成立**）")
    L.append("")

    L.append("## 8. 本次运行的局限（不要把报告读成更强的结论）")
    L.append("")
    L.append(f"1. **`n_fim = {st.get('n_fim')}`**：`(A)` 随 `n_fim` 单调下降（有限样本偏差，"
             "不是 MC 噪声）⇒ 可行集与推荐点都可能在更大的 `n_fim` 下改变；")
    L.append(f"2. **`budget = {st.get('budget')}`**：四臂各只抽了 {st.get('budget')} 个点 ⇒ "
             "第 5 节的臂间裁决只在这点预算内成立（第 1 节的作用域说明它**不影响**第 6/7 节）；")
    L.append(f"3. **候选空间固定为 {fs.get('n_candidates')} 个**（`T_POOL_MS` × `W_POOL_MS` × "
             "`n_rep` 受 C1/C3 耦合约束）⇒ 报告不覆盖被 C3 否决的设计；")
    L.append("4. 第 3 节的「数值病态」比例**不是**本次 `n_fim` 的产物（D61：`n_fim = 1` 与 `12` "
             "两档 `n_bad > 0` 的集合逐设计相同、都 123/174），而是候选空间在 `T`/`W`/`n_rep` "
             "耦合约束下的**结构性质**。")
    L.append("")
    return "\n".join(L)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"❌ 找不到 payload：{src}")
        return 2
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else _HERE / "stage9_report.md"
    text = build(src)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"✍️ 已生成 {out}（{len(text.splitlines())} 行）← {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
