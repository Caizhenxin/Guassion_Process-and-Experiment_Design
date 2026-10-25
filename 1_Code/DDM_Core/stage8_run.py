# -*- coding: utf-8 -*-
"""stage8_run.py — Stage 8 的**全量运行器**（批处理作业）。

主计划 §3 Stage 8 与 `5_Reference/08_工作流/Stage8_建模与验证方案.md` 都点名要它：
在**每组 ~40 人**的正式数据上跑「层级拟合 → 超参数后验 → 以被试为单位的 PSIS-LOO →
M-T1 vs M-T3 模型比较 → 分单元 PPC」，并把结果落成报告与机器可读的 JSON。

为什么必须是一个**独立脚本**而不是交互式会话里跑
--------------------------------------------------
成本来自实测（`1_Code/DDM_Core/_scratch/_probe_stage8_timing.py`，576 试次/人、K=4）：
单次 `log_likelihood_step` **84 ms**、`hessian_x` **3.43 s**、冷启动 L-BFGS ≤60 步 **9.32 s**。
`hier_fit` 每轮 EM 要对每人做一次众数搜索 + 一次拉普拉斯 → 单人单轮约 13 s；
再乘 `n_em` 与 `n_draws`（LOO 矩阵对每个 (抽取, 被试) 都要重求众数），
40 人 × 50 抽取就是数小时量级 ⇒ **必须挂后台跑**，且 `--plan-only` 能先给出预估。

用法
----
    # 0) 只看计划与成本预估（不拟合）
    python stage8_run.py --data <目录或文件...> --plan-only

    # 1) 正式数据（v4.1 MATLAB 输出），按 groupID 分组
    python stage8_run.py --data <目录> --out _stage8_out --n-em 12 --n-draws 50

    # 2) 真实数据到手前的**干跑**：用合成 v4.1 数据把整条链路走通
    python stage8_run.py --synthetic 4 --limit 2 --n-em 4 --n-draws 12 \
                         --n-ppc 8 --out _stage8_dryrun

判定规则（`5_Reference/08_工作流/Stage8_建模与验证方案.md` 的四挡）
------------------------------------------------------------------
``k <= 0.7`` 报 ΔELPD + **配对** SE；``0.7 < k <= 1.0`` 降级为提示性；
``k > 1.0`` 判定**不构成证据**并提示改用 `hier.loo_bruteforce`（真留一）。
本脚本把这些判断**直接印在报告里**，而不是留给读者自己记得。
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXP_DIR = REPO / "1_Code" / "Experiment"
for _p in (HERE, EXP_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hier                                                      # noqa: E402
import read_formal_data as RF                                    # noqa: E402
import stage8 as S8                                              # noqa: E402
from likelihood import log_likelihood                            # noqa: E402
from mapping import WITHIN_FREE_LIN, MappingParams                # noqa: E402

#: 主计划点名的两个模型：M-T1 = 两阶段漂移（rho 自由）、M-T3 = 单阶段（rho = 1）
MODELS = {"M-T1": True, "M-T3": False}

#: 实测标定（`_scratch/_probe_warm_mode.py` 与 `_scratch/_probe_s8run_profile.py`）。
#: 校准点：48 试次/人、`n_x=41`、`MappingParams(shape_model="lin")`。
#:   · 一次**温启动**众数搜索 = L-BFGS 24/27 次 + `hessian_x` 的 2K + 4·K(K−1)/2 次
#:     ⇒ M-T3（K=7）122 次、M-T1（K=8）155 次似然评估
#:   · 单次 `log_likelihood_step` ≈ 34 ms；16/48/144 试次 ⇒ 23/36/51 ms（幂律指数 ≈ 0.42）
#:   · 两个独立探针交叉核对：122 × 34 ms = 4.15 s vs 实测 4.435 s（差 7%）
#:   · 冷启动（EM 每轮每题一次）在 48 试次下 M-T3 120 次、M-T1 180 次 L-BFGS 评估
_COST = dict(
    trials_cal=48.0, ll_ms=34.0, power=0.42,
    evals_warm={"M-T3": 24 + 98, "M-T1": 27 + 128},
    evals_cold={"M-T3": 120 + 98, "M-T1": 180 + 128},
)

#: 超过这个预估时长就提醒：现行 `hier.hyper_hessian` 让正式规模不可行
_COST_WARN_H = 24.0

#: 超过这个人数就提醒这是批处理作业（README：全量拟合不能在交互式会话跑）
_BATCH_WARN_N = 12


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def _synthetic(n_subjects: int, seed: int, group: int, outdir: Path,
               n_rep: int | None = None) -> Path:
    """用 `_scratch/make_fake_pilot.py` 造 v4.1 合成数据（干跑用）。"""
    maker = HERE / "_scratch" / "make_fake_pilot.py"
    if not maker.exists():
        raise SystemExit(f"找不到合成数据生成器：{maker}")
    cmd = [sys.executable, "-u", str(maker), str(outdir),
           "--n-subjects", str(n_subjects), "--group", str(group), "--seed", str(seed)]
    if n_rep is not None:
        cmd += ["--n-rep", str(n_rep)]
    print(f"[合成] {' '.join(cmd[1:])}")
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"合成数据生成失败（exit {r.returncode}）：\n{r.stdout}\n{r.stderr}")
    return outdir


def _no_inputs_message(rejected: list[dict]) -> str:
    """一个可用被试都没有时的退出信息（D66：不留白板 traceback）。"""
    head = "没有任何可用的 v4.1 逐被试 txt 输入"
    if not rejected:
        return head + "（目录里也没有文件）。\n需要先跑 Stage 7 采集，或用 --synthetic 干跑。"
    lines = [head + f"，共 {len(rejected)} 项被拒："]
    for r in rejected[:5]:
        lines.append(f"  ⛔ {r.get('file', '?')}：{r.get('reason', '')}")
    if len(rejected) > 5:
        lines.append(f"  … 另有 {len(rejected) - 5} 项")
    return "\n".join(lines)


def _non_txt_reason(path: Path) -> str:
    """给「不是 v4.1 逐被试 txt」的输入一句可执行的拒绝理由（D66）。

    历史汇总 CSV（`2_Data/Real_Data/EXP_data_combined.csv`）看着像数据，但缺
    `HEADER25` 里 9 列（`block` / `premature_press` / `timeout` /
    `responded_by_deadline` / 三个 `*_actual` / `stimulus_frames`）⇒ **不是转换
    问题，是信息不存在**。这里把缺的列名逐条列出来，免得下一个人再去试。
    """
    head_note = ""
    try:
        first = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
        is_csv = first.count(",") >= first.count("\t")
        cols = [c.strip() for c in (first.split(",") if is_csv else first.split("\t"))]
        missing = [c for c in RF.HEADER25 if c not in cols]
        if missing:
            head_note = (f"；该文件表头缺 {len(missing)} 列 v4.1 必填字段："
                         + "、".join(f"`{c}`" for c in missing))
        elif is_csv:
            head_note = "；列名齐全但分隔符是逗号（v4.1 用制表符）"
    except Exception:                                            # noqa: BLE001
        head_note = "（表头读不出来）"
    return (
        f"本运行器只吃 **v4.1 逐被试 txt**（制表符分隔、`HEADER25` 25 列，"
        f"由 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` 直接写出）"
        f"{head_note}。历史汇总 CSV 无法补出这些列（任何补法都是猜测）⇒ "
        f"Stage 8 的真实数据输入必须是 Stage 7 采集产出的逐被试 txt。"
    )


def collect(paths: list[Path], limit: int | None, p_base: MappingParams):
    """读入并校验全部被试；返回 (参与者列表, 被拒列表)。

    D66：**格式不合格的输入在入口就被点名拒绝**，不再掉进 `load_file` 之后的
    `KeyError`（历史行为：喂一个 CSV 直接抛未捕获的 `KeyError: 'matchKey'`）。
    """
    files, rejected = [], []
    for p in paths:
        if p.is_dir():
            found = sorted(p.glob("*.txt"))
            if not found:
                others = [q for q in sorted(p.glob("*")) if q.is_file()]
                rejected.append({"file": p.name,
                                 "reason": f"目录里没有 *.txt（有 {len(others)} 个其它"
                                           f"文件，例如 "
                                           + "、".join(q.name for q in others[:3])
                                           + "）⇒ 本运行器只吃 v4.1 逐被试 txt"})
            files.extend(found)
        elif p.suffix.lower() != ".txt":
            rejected.append({"file": p.name, "reason": _non_txt_reason(p)})
        else:
            files.append(p)
    if limit is not None:
        files = files[:limit]
    if not files:
        print(_no_inputs_message(rejected), file=sys.stderr)
        raise SystemExit(2)

    people = []
    for f in files:
        try:
            rec, rep = RF.load_file(f, stage="formal")
        except Exception as e:                                   # noqa: BLE001
            rejected.append({"file": f.name, "reason": f"读取异常：{e}"})
            continue
        if not rec:
            rejected.append({"file": f.name,
                             "reason": f"{rep.get('error', '未解析出观测')}"
                                       f"（表头：{rep.get('header', '未知')}）"})
            continue
        try:
            errs, warns = RF.validate_split(rec, RF.to_trials(rec))
        except Exception as e:                                   # noqa: BLE001
            rejected.append({"file": f.name, "subject": rec.get("subjectID"),
                             "reason": f"校验异常：{type(e).__name__}: {e}"})
            continue
        if errs:
            rejected.append({"file": f.name, "subject": rec.get("subjectID"),
                             "reason": "; ".join(errs[:3])})
            print(f"  ⛔ {f.name}：{errs[0]}" + (f"（另有 {len(errs) - 1} 条）"
                                                 if len(errs) > 1 else ""))
            continue
        # 软项（逐行技术异常，如掉帧 1 行）只记录、不拒收：判据与筛查层的
        # `intake.py` 同源（D122），否则同一份数据在两个入口有 15 人 / 17 人两种答案。
        if warns:
            print(f"  ⚠ {f.name}：{warns[0]}" + (f"（另有 {len(warns) - 1} 条）"
                                                if len(warns) > 1 else ""))
        tr_full = RF.to_trials(rec)
        # D123：`rec` 传进去才能按「刺激期内按键」剔除（`|dur − T| > 一帧`），
        # 否则 min(RT) 常落在 150–200 ms 的机会水平带上，把 t0 上界顶死。
        tr, fr = RF.fit_ready(tr_full, rec=rec)
        # 每人的 t0 上界不同（= 保留试次最小 RT − 余量）⇒ 必须逐人写进 bounds
        tb = RF.t0_bounds(tr)
        people.append({
            "file": f.name, "subject": int(rec["subjectID"]),
            "group": int(rec["groupID"]), "n_trials": int(np.asarray(tr["rt"]).size),
            "n_dropped": int(fr.get("n_dropped", 0)),
            "n_dropped_dev": int(fr.get("n_dropped_dev", 0)),
            "t0_hi": float(tb["t0"][1]), "tr": tr, "tr_full": tr_full,
            "t0_bounds": tb, "p_base": p_base,
        })
        print(f"  ✅ {f.name}：被试 {rec['subjectID']}（组 {rec['groupID']}）"
              f"{people[-1]['n_trials']} 试次、剔抢按 {people[-1]['n_dropped']}"
              f"（其中刺激期内按键 {people[-1]['n_dropped_dev']}）、"
              f"t0 上界 {people[-1]['t0_hi']:.3f}")
    return people, rejected


def _subjects(people, rho_free: bool, n_x: int):
    return [hier.ddm_subject(p["tr"], p["p_base"], WITHIN_FREE_LIN,
                             rho_free=rho_free, bounds_override=p["t0_bounds"],
                             n_x=n_x) for p in people]


def project(people, n_em: int, n_draws: int, n_models: int, n_ppc: int,
            hyper_method: str = "fd") -> str:
    """按**实测**单位预估总时长。

    计价单位（全部来自 `_probe_warm_mode.py` / `_probe_s8run_profile.py`，校准点
    = 48 试次/人、`n_x=41`）：一次众数搜索 = 固定次数的似然评估 × 单次评估耗时；
    单次评估耗时随试次数按幂律 ≈ 0.42 增长（实测 23/36/51 ms @ 16/48/144 试次）。

    ``hyper_method="analytic"``（Louis 恒等式，见主计划 D47）时超参数 Hessian
    **不需要任何众数搜索**，`hyper` 一项直接归零 —— 那正是它存在的理由。
    """
    n = len(people)
    trials = float(np.mean([len(p["tr"]["rt"]) for p in people])) if n else 0.0
    scale = (max(trials, 1.0) / _COST["trials_cal"]) ** _COST["power"]
    ll = _COST["ll_ms"] / 1000.0 * scale
    analytic = (hyper_method == "analytic")

    nw = len(WITHIN_FREE_LIN)
    fit = hyper = loo = 0.0
    n_fit = n_hyper = n_loo = 0.0
    for name, rho_free in MODELS.items():
        k = nw + (1 if rho_free else 0)
        nh = 2 * k
        # ❗ 主导项：`hier.hyper_hessian` 对 nh = 2K 维做中心差分 Hessian，
        #    需要 4·nh(nh+1)/2 次目标评估，而**每次评估都对全部 N 名被试
        #    各做一次温启动众数搜索**。K=7 的 M-T3 ⇒ 420·N；K=8 的 M-T1 ⇒ 544·N。
        #    它**不随 n_em / n_draws 变小** ⇒ 再小的干跑也被它拖住。
        per_person = 4.0 * nh * (nh + 1) / 2.0
        n_fit += n * n_em
        fit += n * n_em * _COST["evals_cold"][name] * ll
        if not analytic:
            n_hyper += per_person * n
            hyper += per_person * n * _COST["evals_warm"][name] * ll
        n_loo += n_draws * n
        loo += n_draws * n * _COST["evals_warm"][name] * ll
    ppc = n * n_ppc * 1.0
    total = fit + hyper + loo + ppc
    if analytic:
        hyper_line = ("    超参数 Hessian：**解析法（Louis）⇒ 0 次众数搜索**、"
                      "只剩矩阵运算（主计划 D47）\n")
    else:
        hyper_line = (f"    **超参数 Hessian ≈ {hyper / 60:.1f} min**"
                      f"（{n_hyper:.0f} 次温启动众数搜索 —— 主导项，"
                      f"不随 n_em/n_draws 变小）\n")
    msg = (f"预估（实测标定：{_COST['trials_cal']:.0f} 试次/人、`n_x=41`、"
           f"单次似然 {_COST['ll_ms']:.0f} ms；本次人均 {trials:.0f} 试次 ⇒ "
           f"单次评估 ×{scale:.2f}）\n"
           f"    人数 {n}、n_em {n_em}、n_draws {n_draws}、模型 {n_models} 个、"
           f"PPC 抽取 {n_ppc}、超参数法 {hyper_method}\n"
           f"    层级拟合 ≈ {fit / 60:.1f} min（{n_fit:.0f} 次冷启动众数搜索）\n"
           + hyper_line +
           f"    LOO 矩阵 ≈ {loo / 60:.1f} min、PPC ≈ {ppc / 60:.1f} min\n"
           f"    ⇒ 合计 ≈ **{total / 3600:.2f} h**")
    if total / 3600.0 > _COST_WARN_H:
        msg += ("\n    ⚠️ 该规模下 `hier.hyper_hessian` 让正式运行不可行："
                "正式采集前必须先把它换成更省的做法（跨超参数扰动复用逐被试"
                "曲率 / 向量化 / 只取超参数 Hessian 的对角）。")
    return msg


def fit_group(people, n_em: int, n_x: int, n_draws: int, seed: int,
              do_bruteforce: bool, hyper_method: str = "fd",
              loo_level: str = "participant") -> dict:
    """只做拟合：返回 ``{模型名: hier.fit_and_loo(...) 的结果}``。"""
    results = {}
    for name, rho_free in MODELS.items():
        subs = _subjects(people, rho_free, n_x)
        t0 = time.time()
        print(f"  [{name}] rho_free={rho_free} 开始（{len(subs)} 人、n_em={n_em}、"
              f"n_draws={n_draws}、超参数法 {hyper_method}、"
              f"LOO 口径 {loo_level}）…", flush=True)
        r = hier.fit_and_loo(subs, n_draws=n_draws, seed=seed, n_em=n_em,
                             do_bruteforce=do_bruteforce,
                             hyper_method=hyper_method, loo_level=loo_level)
        r["seconds"] = time.time() - t0
        r["rho_free"] = rho_free
        lk = r["loo"]
        # ⚠️ 键名必须与 `loo.psis_loo` 的**真实**返回一致：是 `n_k_gt_bad` / `n_obs`，
        #    不是 `n_bad` / `n`（那两个键从来不存在）。
        print(f"  [{name}] 完成 {r['seconds']:.1f}s：ELPD {lk['elpd_loo']:.3f} "
              f"± {lk['se']:.3f}；p_loo {lk['p_loo']:.2f}；k_max {lk['k_max']:.3f}；"
              f"越界 {lk['n_k_gt_bad']}/{lk['n_obs']}；"
              f"不可用 {lk.get('n_k_gt_unusable', 0)}；失败 {lk.get('n_failed', 0)}；"
              f"非有限 {r.get('n_nonfinite_loglik', 0)}")
        # ❗ 退化计数必须打印出来：它们量的是 `n_nonfinite_loglik` **看不见**的东西
        #    （众数搜索退回初值 / 目标函数非有限），见主计划 D51。
        st = r.get("loo_stats") or {}
        n_fb = int(st.get("n_fallback", 0)) + int(r.get("n_fallback_fit", 0))
        n_nf = int(st.get("n_nonfinite_g", 0)) + int(r.get("n_nonfinite_g_fit", 0))
        n_hf = int(st.get("n_hessian_fail", 0))
        if n_fb or n_nf or n_hf:
            print(f"  [{name}] ⚠️ 退化计数：众数搜索退回初值 {n_fb} 次"
                  f"（LOO 阶段 {st.get('n_fallback', 0)}/{st.get('n_searches', 0)} 次搜索、"
                  f"拟合阶段 {r.get('n_fallback_fit', 0)}）；"
                  f"目标函数非有限 {n_nf} 次；**拉普拉斯 Hessian 非有限 {n_hf} 格"
                  f"（已记 −inf、PSIS 计为失败）** —— "
                  f"这些**不会**出现在 n_nonfinite_loglik 里", flush=True)
        r["n_degenerate_fallback"] = n_fb
        r["n_degenerate_nonfinite"] = n_nf
        r["n_degenerate_hessian"] = n_hf
        results[name] = r
    # ⚠️ 这里**不能** pop `log_lik`：`render_group` 还要用它做 `compare_models`
    #    （配对差需要同一批被试的 (S,N) 矩阵）。剥离交给 `strip_matrices`，
    #    在渲染**之后**调用 —— 否则 `compare_models` 必 `KeyError`。
    return results


def strip_matrices(results: dict) -> dict:
    """从结果里剥掉体积大且不可序列化的 ``log_lik``（渲染完之后才允许调用）。"""
    for r in results.values():
        r.pop("log_lik", None)
    return results


def render_group(results: dict, people, tag: str, n_draws: int, seed: int) -> list[str]:
    """把**已拟合**的结果渲染成报告行（k 挡位判定 + 模型比较 + 分单元 PPC）。

    与 `fit_group` 分开是为了让这条链路可以**不重拟合**地被自测（`_scratch/check_stage8_run.py`）。
    """
    lines = [f"### 组 {tag}（{len(people)} 人）", ""]
    # ❗ LOO 口径必须写在**每个组的第一行**：同一份报告里换过口径、或读者拿旧报告
    #    对照时，`n_obs` 到底是「人数」还是「总试次」决定 `p_loo/n_obs` 怎么读（D73）。
    lv = {r.get("loo_level", "participant") for r in results.values()}
    lv_txt = "、".join(sorted(lv))
    if lv == {"trial"}:
        lines += ["> LOO 口径：**试次层**（D73；`n_obs` = 总试次、模型比较用这一层）；"
                  "⚠️ 可用性的**前置条件**是超参数 Hessian 正定（D74：非正定时两层都越界）", ""]
    else:
        lines += [f"> LOO 口径：**{lv_txt}**（`n_obs` = 人数；⚠️ 被试层 `p_loo` 不可估，"
                  f"见 D73/§8.48）", ""]
    for name, r in results.items():
        lk = r["loo"]
        k, bad = float(lk["k_max"]), int(lk["n_k_gt_bad"])
        n_obs = int(lk["n_obs"])
        nonfin = int(r.get("n_nonfinite_loglik", 0))
        ploo = float(lk["p_loo"])
        plo_ratio = (ploo / n_obs) if n_obs else float("nan")
        # ⚠️ `nan` **不是**最差挡位。若不单独处理，`nan <= 0.7` 与 `nan <= 1.0` 都是
        #    False ⇒ 会掉进「k > 1.0 ⇒ 不构成证据」那一档，把"k 不可用"误报成
        #    "k 超界"。必须显式分开：不可用 ≠ 超界。
        #
        # ❗ 决策 D52：**`k_max` 单独没有分辨力**。N=4 的 analytic 干跑实测
        #    `k_max = 0.000`、`n_failed = 0`（上面两条判据全过），而 `p_loo = 2816.26`
        #    对 `n_obs = 4`（LOO 单位 = 被试）⇒ 有效参数数是观测数的 704 倍。
        #    同一个 `k_max = 0.000` 在**健康**矩阵上也会出现（实测
        #    `rng.normal(-3.0, 0.3, size=(30, 3))` 的另一抽样：`p_loo = 0.222`、
        #    `k_max = 0.0`）⇒ 0 既可能是"权重近似均匀"也可能是"权重彻底退化"，
        #    所以必须再看 `p_loo`。健康区间是 `[0, n_obs]`：`p_loo < 0` 意味着
        #    留一比拟合内还准（不可能），`p_loo > n_obs` 意味着惩罚超过全部信息量。
        reasons = []
        # ❗ 决策 D74：**「换到试次层」不是充分条件**。LOO 矩阵的每一列都是「给定一组超参数
        #    的条件后验边际」，超参数协方差若非正定（`n_flipped > 0`），抽样里就混着 |θ| 达
        #    数百的荒诞尾部值 ⇒ 该列被这些抽样支配，**两层都会越界**。实测对照（同一份代码）：
        #      * 3 人、`n_em=2`、`n_x=21`、S=20：Hessian 正定（min eig 0.0265、`n_flipped`=0）
        #        ⇒ 试次层 `p_loo/n_obs = 0.138`；
        #      * 2 人、`n_em=1`、`n_x=11`、S=15：2 个负特征值、`theta` 逐维 SD 达 134、|θ| 达 303
        #        ⇒ 试次层 `p_loo/n_obs = 8.57`（M-T1）/ 12.7（M-T3）。
        #    ⇒ 前置条件先判 Hessian，再判层与比值。
        n_flipped_hy = int((r.get("hyper") or {}).get("n_flipped", 0))
        if n_flipped_hy > 0:
            reasons.append(f"超参数 Hessian **非正定**（`n_flipped` = {n_flipped_hy}）"
                           f"⇒ 抽取含荒诞尾部值，`p_loo` 不可解读（D74；层不是充分条件）")
        if not np.isfinite(k):
            reasons.append("`k_max` 非有限")
        if int(lk.get("n_failed", 0)) >= n_obs:
            reasons.append(f"`n_failed` {int(lk.get('n_failed', 0))}/{n_obs}")
        if not (0.0 <= ploo <= n_obs):
            reasons.append(f"`p_loo` {ploo:.2f} 落在健康区间 [0, {n_obs}] 之外"
                           f"（p_loo/n_obs = {plo_ratio:.3g}）")
        if reasons:
            verdict = (f"⛔ **本组 LOO 无效**（" + "；".join(reasons) +
                       f"；非有限 log-lik {nonfin}/"
                       f"{r['log_lik'].size if r.get('log_lik') is not None else '?'}）"
                       f" ⇒ 不得引用 ELPD/ΔELPD；先查 `n_draws` 与样本量")
        elif k <= 0.7:
            verdict = "可报 ΔELPD + 配对 SE"
        elif k <= 1.0:
            verdict = "⚠️ 降级为提示性（0.7 < k ≤ 1.0）"
        else:
            verdict = ("⛔ **不构成证据**（k > 1.0）⇒ 改用 `hier.loo_bruteforce` 真留一；"
                       "本组 n 太小，需在正式数据（~40 人/组）上复验")
        lines += [f"* **{name}**：ELPD **{lk['elpd_loo']:.3f} ± {lk['se']:.3f}**、"
                  f"`p_loo` {ploo:.2f}（**`p_loo`/`n_obs` = {plo_ratio:.3g}**）、"
                  f"`k_max` **{k:.3f}**、"
                  f"越界 {bad}/{n_obs}、拟合 {r['seconds']:.0f}s ⇒ {verdict}"]
        # ❗ 超参数 Hessian 的正定性必须单独成行、并写清「不正定 ⇒ σ 不可解读」的**后果**。
        #    只报 `n_flipped` 而不说后果，等于让人以为「记一笔就行」；实测机制是
        #    `hier.subject_map_laplace` 把非正特征值抬到 `floor = max(1e-8·max|λ|, 1e-12)`
        #    再取逆 ⇒ 该方向的**方差 ≈ 1/floor**（可到 1e5 量级），而层级 σ² 的定义
        #    正是 `mean[(x − μ)² + Cov_kk]` ⇒ 一个被抬过的方向就能把 σ 撑到没有意义。
        hy = r.get("hyper") or {}
        ev = hy.get("eigval")
        if ev is not None and len(ev):
            e_min, e_max = float(np.min(ev)), float(np.max(ev))
            n_flip = int(hy.get("n_flipped", 0))
            # ❗ D75：`n_flipped` 是**符号**判据；失败拟合的 `λ_min` 常常只到 −0.005
            #    （相对 `λ_max` 约 1e-5），单看符号说不清"有多坏"。与之同步恶化的是
            #    **抽样跑了多远**（`max_abs_theta`）。扫描实测分离 5–40 倍：正定 ≤ 7.3，
            #    非正定 33.6 / 62.8 / 97.9 / 303 ⇒ 两个数必须并列印。
            matt = hy.get("max_abs_theta")
            if matt is not None:
                tail_txt = f"、本次抽样 `|θ|` 最大 = **{float(matt):.3g}**"
            else:
                tail_txt = "、本次抽样 `|θ|` 最大 = **（未记录）**"
            if n_flip == 0:
                lines += [f"  * 超参数 Hessian：**正定**（`n_flipped` = 0/{len(ev)}、"
                          f"特征值 [{e_min:.3g}, {e_max:.3g}]）{tail_txt}"]
            else:
                floor = max(1e-8 * max(abs(e_min), abs(e_max)), 1e-12)
                # 把**本次实际收敛**的 σ 末行也印出来：1/floor 是机制上界，
                # 实测值才是"这次到底有没有被撑大"的证据（N=3 里 M-T1 实测 2.27e+03）。
                # ⚠️ 退化拟合（`hyper_draws` 抛异常走兜底）时没有 `sigma` 字段，
                #    此时**整段省略**——曾因写死 `**{sig_txt}**` 印出 `****` 空粗体。
                sig_clause = ""
                ls = hy.get("sigma")
                if ls is not None:
                    try:
                        arr = np.asarray(ls, dtype=float)
                        arr = arr[-1].ravel() if arr.ndim > 1 else arr.ravel()
                        sig_clause = ("，本次收敛 σ ∈ "
                                      f"[{float(np.min(arr)):.3g}, "
                                      f"{float(np.max(arr)):.3g}]（末轮）")
                    except Exception:                               # noqa: BLE001
                        sig_clause = ""
                lines += [f"  * 超参数 Hessian：`n_flipped` = **{n_flip}/{len(ev)}**、"
                          f"特征值 [{e_min:.3g}, {e_max:.3g}]{tail_txt} ⇒ ⛔ **本次的 σ"
                          f"（被试间 SD）不得解读**：非正方向被 `floor = max(1e-8·max|λ|, "
                          f"1e-12)` 抬起，该方向方差 ≈ 1/floor ≈ {1.0 / floor:.3g}，"
                          f"σ² = mean[(x − μ)² + Cov_kk] 会被它撑大"
                          f"{sig_clause}；加大人数或改 `hyper_method` 后再判"]
    if len(results) == 2:
        lines += ["", "```", hier.compare_models(results).rstrip(), "```"]
        bf = [r.get("bruteforce_total") for r in results.values()]
        if all(v is not None for v in bf):
            a, b = list(results)
            lines += ["", f"真留一（bruteforce）合计：{a} {bf[0]:.3f}、{b} {bf[1]:.3f}"
                          f" ⇒ 差 {bf[0] - bf[1]:+.3f}"]

    # ---- 分单元 PPC：用层级 MAP 处的拉普拉斯后验 ----
    for name, r in results.items():
        if S8 is None:
            continue
        print(f"  [{name}] 分单元 PPC …", flush=True)
        rows_md = []
        names = WITHIN_FREE_LIN + (["rho"] if r["rho_free"] else [])
        for i, p in enumerate(people):
            # ⚠️ 必须用**这名被试自己的** bounds 反变换：t0 上界是逐人算的
            #    （T0_SAFE_MARGIN + 该人剔除抢按后的最小 RT），拿别人的 bounds
            #    会把 t0 静默换成另一个值，PPC 于是模拟的不是刚拟合的那个模型。
            ov = {**p["t0_bounds"]}
            if r["rho_free"]:
                ov = {**ov, "rho": (0.0, 3.0)}
            lo, hi = hier._bounds_with_rho(names, ov)
            xm = np.asarray(r["fit"]["modes"][i], float)
            th = hier._from_x(xm, lo, hi)
            p_map = p["p_base"].with_vector(WITHIN_FREE_LIN, th[:len(WITHIN_FREE_LIN)])
            d = S8.subject_laplace(p["tr"], WITHIN_FREE_LIN, p_map, n_draws=n_draws,
                                   seed=seed, bounds_override=p["t0_bounds"])
            design = {k: np.asarray(p["tr"][k]) for k in ("P", "T", "W", "is_self", "is_match")}
            res = S8.ppc_table(p["tr"], design, d, n_rep_draw=n_draws, seed=seed,
                               with_cells=True)
            glob_ok = sum(1 for x in res["rows"] if x["ok"])
            cell_ok = sum(1 for x in res["cell_rows"] if x["ok"])
            n_cell = len(res["cell_rows"])
            rows_md += ["", f"#### {name} / 被试 {p['subject']}", "",
                        f"* 全局 {glob_ok}/{len(res['rows'])} 在带内；"
                        f"**分单元 {cell_ok}/{n_cell}**",
                        f"* `n_flipped` = {d['n_flipped']}（>0 说明协方差被抬过，"
                        f"必须报）"]
            rows_md += ["", "```", S8.format_ppc(res).rstrip(), "```"]
        lines += ["", f"### 组 {tag} / {name} 的分单元 PPC", *rows_md]
    return lines


def run_group(people, tag: str, n_em: int, n_draws: int, n_x: int, seed: int,
              do_bruteforce: bool, keep_matrices: bool,
              hyper_method: str = "fd", loo_level: str = "participant") -> dict:
    """对一组人拟合两个模型、比较、并对每人跑分单元 PPC。"""
    print(f"\n{'=' * 92}\n组 {tag}：{len(people)} 人\n{'=' * 92}")
    results = fit_group(people, n_em, n_x, n_draws, seed, do_bruteforce,
                        hyper_method=hyper_method, loo_level=loo_level)
    lines = render_group(results, people, tag, n_draws, seed)
    if not keep_matrices:
        strip_matrices(results)
    return {"lines": lines, "results": results}


def _group_file(outdir: Path, g) -> Path:
    """单组结果缓存文件（D72）。用组号命名 ⇒ `--resume` 只按组跳过。"""
    return outdir / f"stage8_group_{g}.json"


def _load_group(gf: Path) -> dict:
    """读单组缓存。❗ 缓存破了必须**大声失败**，不许静默重拟合：
    静默重跑会让「命中了旧缓存」和「重新算过」在日志里长得一样。"""
    try:
        obj = json.loads(gf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{gf} 不是合法 JSON（{exc}）⇒ 删掉该文件后重跑") from exc
    missing = [k for k in ("tag", "lines", "results") if k not in obj]
    if missing:
        raise ValueError(f"{gf} 缺少字段 {missing} ⇒ 删掉该文件后重跑")
    return obj


def _write_json_atomic(path: Path, obj) -> None:
    """原子写 JSON：先写 `<path>.tmp` 再 `os.replace`。
    ❗ 长跑被杀是常态，而 `Path.write_text` 写到一半会留下**半截 JSON**；
    原子写让「文件存在」= 「内容完整」，`--resume` 才不会读到残片。"""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stage 8 全量运行器（批处理）")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--data", nargs="+", help="正式数据：文件或目录")
    src.add_argument("--synthetic", type=int, metavar="N",
                     help="干跑：先生成 N 人的 v4.1 合成数据（另有 --synthetic-seed/--group）")
    ap.add_argument("--synthetic-seed", type=int, default=7)
    ap.add_argument("--synth-n-rep", type=int, default=None,
                    help="合成数据的每格重复次数（默认 12 = 正式设计；调小只为快速干跑）")
    ap.add_argument("--group", type=int, default=1, help="合成数据的组别（1–4）")
    ap.add_argument("--limit", type=int, default=None, help="只用前 N 名被试")
    ap.add_argument("--n-em", type=int, default=12)
    ap.add_argument("--n-draws", type=int, default=50)
    ap.add_argument("--n-x", type=int, default=81)
    ap.add_argument("--n-ppc", type=int, default=0, help="PPC 的预测数据集份数（0=跳过）")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hyper-method", choices=("fd", "analytic"), default="fd",
                    help="超参数 Hessian 的算法：fd = 有限差分（历史口径，"
                         "正式规模下 420·N / 544·N 次众数搜索，不可行）；"
                         "analytic = Louis 恒等式（**0 次众数搜索**，正式采集用这个；"
                         "注意它算的是真边际的 Hessian，内层拉普拉斯误差见 D47）")
    ap.add_argument("--loo-level", choices=("participant", "trial"), default="participant",
                    help="PSIS-LOO 的观测单位（D73）：participant = 被试层（历史口径，"
                         "⚠️ 该层 `p_loo` 量的是 profile 边际的离散度、**不可估**）；"
                         "trial = 试次层（`n_obs` = 总试次，模型比较用这一层，额外成本≈0）")
    ap.add_argument("--bruteforce", action="store_true", help="额外跑真留一（很贵）")
    ap.add_argument("--plan-only", action="store_true", help="只做校验与成本预估，不拟合")
    ap.add_argument("--allow-large", action="store_true",
                    help=f"超过 {_BATCH_WARN_N} 人时不再拦（提醒：应当是后台作业）")
    ap.add_argument("--resume", action="store_true",
                    help="断点续跑（D72）：已有 `stage8_group_<组>.json` 的组直接复用、"
                         "不再拟合；缓存损坏时报错而不是静默重算")
    ap.add_argument("--out", default="_stage8_out", help="输出目录")
    args = ap.parse_args(argv)

    outdir = (Path(args.out) if Path(args.out).is_absolute() else REPO / args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # 干跑结束后必须清掉合成数据，别把它混进真实结果目录
    tmp = None
    if args.synthetic:
        tmp = Path(tempfile.mkdtemp(prefix="stage8_syn_"))
        _synthetic(args.synthetic, args.synthetic_seed, args.group, tmp,
                   n_rep=args.synth_n_rep)
        paths = [tmp]
    else:
        paths = [Path(p) if Path(p).is_absolute() else REPO / p for p in args.data]

    p_base = MappingParams(shape_model="lin")
    print(f"{'=' * 92}\nStage 8 全量运行器\n{'=' * 92}")
    people, rejected = collect(paths, args.limit, p_base)
    print(f"\n可用被试 {len(people)} 名；被拒 {len(rejected)} 份")
    if not people:
        print("❗ 没有可用被试，终止。")
        return 1
    if len(people) > _BATCH_WARN_N and not args.allow_large:
        print(f"❗ {len(people)} 人 > {_BATCH_WARN_N} ⇒ 这是**批处理作业**，"
              f"不应在交互式会话里跑。确认请在后台重跑并加 `--allow-large`。")
        print(project(people, args.n_em, args.n_draws, len(MODELS), args.n_ppc,
                      args.hyper_method))
        (outdir / "stage8_manifest.json").write_text(
            json.dumps(_jsonable({"rejected": rejected, "people": [
                {k: v for k, v in p.items() if k not in ("tr", "tr_full", "p_base")}
                for p in people]}), ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    print(project(people, args.n_em, args.n_draws, len(MODELS), args.n_ppc,
                  args.hyper_method))
    if args.plan_only:
        print("\n（--plan-only：不拟合）")
        return 0

    groups = {}
    for p in people:
        groups.setdefault(p["group"], []).append(p)

    t_all = time.time()
    report = ["# Stage 8 运行报告", "",
              f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}；"
              f"来源：{'合成（干跑）' if args.synthetic else ('--data ' + '、'.join(str(x) for x in (args.data or []))[:120])}；"
              f"`n_em`={args.n_em}、`n_draws`={args.n_draws}、`n_x`={args.n_x}、"
              f"超参数 Hessian = `{args.hyper_method}`、"
              f"LOO 口径 = `{args.loo_level}`",
              "",
              "> ⚠️ 本线全线是**最大似然 + 拉普拉斯近似**，不是贝叶斯后验；"
              "拉普拉斯协方差的特征值谱与 `n_flipped` 必须一并报告。", ""]
    if rejected:
        report += ["## 被拒文件", ""] + [
            f"* `{r['file']}`：{r['reason']}" for r in rejected] + [""]

    payload = {"rejected": rejected, "groups": {}}
    # ❗ 缓存必须绑定配置：同一 `--out` 目录换了 `n_em`/数据源再 `--resume`，
    #    静默复用旧组会把两套配置混进同一份报告。
    run_config = {
        "n_em": args.n_em, "n_draws": args.n_draws, "n_x": args.n_x,
        "n_ppc": args.n_ppc, "seed": args.seed,
        "hyper_method": args.hyper_method, "bruteforce": bool(args.bruteforce),
        "loo_level": args.loo_level,
        "source": (f"synthetic:{args.synthetic}:{args.synthetic_seed}:"
                   f"{args.group}:{args.synth_n_rep}"
                   if args.synthetic else "data:" + "|".join(str(p) for p in paths)),
    }
    for g, plist in sorted(groups.items()):
        gf = _group_file(outdir, g)
        if args.resume and gf.exists():
            obj = _load_group(gf)
            if obj.get("config") != run_config:
                raise ValueError(
                    f"{gf} 的配置与本次不一致：缓存 {obj.get('config')} ≠ 本次 "
                    f"{run_config} ⇒ 换 `--out` 目录重跑，或删掉缓存")
            print(f"\n组 {g}：命中缓存 `{gf.name}`（--resume，跳过拟合）")
            # 报告里必须留下痕迹：读者要能分辨「这次算的」与「上次算的」
            report += [f"> ♻️ 组 {g} 复用缓存 `{gf.name}`（`--resume`，未重拟合）", ""]
            report += obj["lines"] + [""]
            payload["groups"][str(g)] = obj["results"]
            continue
        out = run_group(plist, str(g), args.n_em, args.n_draws, args.n_x,
                        args.seed, args.bruteforce, keep_matrices=False,
                        hyper_method=args.hyper_method, loo_level=args.loo_level)
        report += out["lines"] + [""]
        obj = {"tag": str(g), "lines": list(out["lines"]),
               "results": _jsonable(out["results"]), "config": run_config}
        payload["groups"][str(g)] = obj["results"]
        # ❗ 单组一落盘 ⇒ 长跑（真实 N 下几十小时）中途崩掉只丢当前组，不丢全部；
        #    写盘走原子路径（D72）：半截文件不会冒充完整缓存
        _write_json_atomic(gf, obj)

    report += [f"总耗时 {time.time() - t_all:.1f}s", ""]
    (outdir / "stage8_report.md").write_text("\n".join(report), encoding="utf-8")
    (outdir / "stage8_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{'=' * 92}\n报告已写出：\n  {outdir / 'stage8_report.md'}\n"
          f"  {outdir / 'stage8_results.json'}\n总耗时 {time.time() - t_all:.1f}s")
    if tmp is not None:
        print(f"（合成数据在临时目录 {tmp}，可手动清理）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
