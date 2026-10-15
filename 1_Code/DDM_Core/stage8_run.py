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


def collect(paths: list[Path], limit: int | None, p_base: MappingParams):
    """读入并校验全部被试；返回 (参与者列表, 被拒列表)。"""
    files = []
    for p in paths:
        files.extend(sorted(p.glob("*.txt")) if p.is_dir() else [p])
    if limit is not None:
        files = files[:limit]
    if not files:
        raise SystemExit("没有找到任何数据文件")

    people, rejected = [], []
    for f in files:
        try:
            rec, rep = RF.load_file(f, stage="formal")
        except Exception as e:                                   # noqa: BLE001
            rejected.append({"file": f.name, "reason": f"读取异常：{e}"})
            continue
        errs = RF.validate(rec, RF.to_trials(rec))
        if errs:
            rejected.append({"file": f.name, "subject": rec.get("subjectID"),
                             "reason": "; ".join(errs[:3])})
            print(f"  ⛔ {f.name}：{errs[0]}" + (f"（另有 {len(errs) - 1} 条）"
                                                 if len(errs) > 1 else ""))
            continue
        tr_full = RF.to_trials(rec)
        tr, fr = RF.fit_ready(tr_full)
        # 每人的 t0 上界不同（= 保留试次最小 RT − 余量）⇒ 必须逐人写进 bounds
        tb = RF.t0_bounds(tr)
        people.append({
            "file": f.name, "subject": int(rec["subjectID"]),
            "group": int(rec["groupID"]), "n_trials": int(np.asarray(tr["rt"]).size),
            "n_dropped": int(fr.get("n_dropped", 0)),
            "t0_hi": float(tb["t0"][1]), "tr": tr, "tr_full": tr_full,
            "t0_bounds": tb, "p_base": p_base,
        })
        print(f"  ✅ {f.name}：被试 {rec['subjectID']}（组 {rec['groupID']}）"
              f"{people[-1]['n_trials']} 试次、剔抢按 {people[-1]['n_dropped']}、"
              f"t0 上界 {people[-1]['t0_hi']:.3f}")
    return people, rejected


def _subjects(people, rho_free: bool, n_x: int):
    return [hier.ddm_subject(p["tr"], p["p_base"], WITHIN_FREE_LIN,
                             rho_free=rho_free, bounds_override=p["t0_bounds"],
                             n_x=n_x) for p in people]


def project(people, n_em: int, n_draws: int, n_models: int, n_ppc: int) -> str:
    """按**实测**单位预估总时长。

    计价单位（全部来自 `_probe_warm_mode.py` / `_probe_s8run_profile.py`，校准点
    = 48 试次/人、`n_x=41`）：一次众数搜索 = 固定次数的似然评估 × 单次评估耗时；
    单次评估耗时随试次数按幂律 ≈ 0.42 增长（实测 23/36/51 ms @ 16/48/144 试次）。
    """
    n = len(people)
    trials = float(np.mean([len(p["tr"]["rt"]) for p in people])) if n else 0.0
    scale = (max(trials, 1.0) / _COST["trials_cal"]) ** _COST["power"]
    ll = _COST["ll_ms"] / 1000.0 * scale

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
        n_hyper += per_person * n
        hyper += per_person * n * _COST["evals_warm"][name] * ll
        n_loo += n_draws * n
        loo += n_draws * n * _COST["evals_warm"][name] * ll
    ppc = n * n_ppc * 1.0
    total = fit + hyper + loo + ppc
    msg = (f"预估（实测标定：{_COST['trials_cal']:.0f} 试次/人、`n_x=41`、"
           f"单次似然 {_COST['ll_ms']:.0f} ms；本次人均 {trials:.0f} 试次 ⇒ "
           f"单次评估 ×{scale:.2f}）\n"
           f"    人数 {n}、n_em {n_em}、n_draws {n_draws}、模型 {n_models} 个、"
           f"PPC 抽取 {n_ppc}\n"
           f"    层级拟合 ≈ {fit / 60:.1f} min（{n_fit:.0f} 次冷启动众数搜索）\n"
           f"    **超参数 Hessian ≈ {hyper / 60:.1f} min**"
           f"（{n_hyper:.0f} 次温启动众数搜索 —— 主导项，不随 n_em/n_draws 变小）\n"
           f"    LOO 矩阵 ≈ {loo / 60:.1f} min、PPC ≈ {ppc / 60:.1f} min\n"
           f"    ⇒ 合计 ≈ **{total / 3600:.2f} h**")
    if total / 3600.0 > _COST_WARN_H:
        msg += ("\n    ⚠️ 该规模下 `hier.hyper_hessian` 让正式运行不可行："
                "正式采集前必须先把它换成更省的做法（跨超参数扰动复用逐被试"
                "曲率 / 向量化 / 只取超参数 Hessian 的对角）。")
    return msg


def fit_group(people, n_em: int, n_x: int, n_draws: int, seed: int,
              do_bruteforce: bool) -> dict:
    """只做拟合：返回 ``{模型名: hier.fit_and_loo(...) 的结果}``。"""
    results = {}
    for name, rho_free in MODELS.items():
        subs = _subjects(people, rho_free, n_x)
        t0 = time.time()
        print(f"  [{name}] rho_free={rho_free} 开始（{len(subs)} 人、n_em={n_em}、"
              f"n_draws={n_draws}）…", flush=True)
        r = hier.fit_and_loo(subs, n_draws=n_draws, seed=seed, n_em=n_em,
                             do_bruteforce=do_bruteforce)
        r["seconds"] = time.time() - t0
        r["rho_free"] = rho_free
        lk = r["loo"]
        print(f"  [{name}] 完成 {r['seconds']:.1f}s：ELPD {lk['elpd_loo']:.3f} "
              f"± {lk['se']:.3f}；p_loo {lk['p_loo']:.2f}；k_max {lk['k_max']:.3f}；"
              f"越界 {lk['n_bad']}/{lk['n']}；失败 {lk.get('n_failed', 0)}")
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
    for name, r in results.items():
        lk = r["loo"]
        k, bad = float(lk["k_max"]), int(lk["n_bad"])
        if k <= 0.7:
            verdict = "可报 ΔELPD + 配对 SE"
        elif k <= 1.0:
            verdict = "⚠️ 降级为提示性（0.7 < k ≤ 1.0）"
        else:
            verdict = ("⛔ **不构成证据**（k > 1.0）⇒ 改用 `hier.loo_bruteforce` 真留一；"
                       "本组 n 太小，需在正式数据（~40 人/组）上复验")
        lines += [f"* **{name}**：ELPD **{lk['elpd_loo']:.3f} ± {lk['se']:.3f}**、"
                  f"`p_loo` {lk['p_loo']:.2f}、`k_max` **{k:.3f}**、"
                  f"越界 {bad}/{lk['n']}、拟合 {r['seconds']:.0f}s ⇒ {verdict}"]
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
              do_bruteforce: bool, keep_matrices: bool) -> dict:
    """对一组人拟合两个模型、比较、并对每人跑分单元 PPC。"""
    print(f"\n{'=' * 92}\n组 {tag}：{len(people)} 人\n{'=' * 92}")
    results = fit_group(people, n_em, n_x, n_draws, seed, do_bruteforce)
    lines = render_group(results, people, tag, n_draws, seed)
    if not keep_matrices:
        strip_matrices(results)
    return {"lines": lines, "results": results}


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
    ap.add_argument("--bruteforce", action="store_true", help="额外跑真留一（很贵）")
    ap.add_argument("--plan-only", action="store_true", help="只做校验与成本预估，不拟合")
    ap.add_argument("--allow-large", action="store_true",
                    help=f"超过 {_BATCH_WARN_N} 人时不再拦（提醒：应当是后台作业）")
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
        print(project(people, args.n_em, args.n_draws, len(MODELS), args.n_ppc))
        (outdir / "stage8_manifest.json").write_text(
            json.dumps(_jsonable({"rejected": rejected, "people": [
                {k: v for k, v in p.items() if k not in ("tr", "tr_full", "p_base")}
                for p in people]}), ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    print(project(people, args.n_em, args.n_draws, len(MODELS), args.n_ppc))
    if args.plan_only:
        print("\n（--plan-only：不拟合）")
        return 0

    groups = {}
    for p in people:
        groups.setdefault(p["group"], []).append(p)

    t_all = time.time()
    report = ["# Stage 8 运行报告", "",
              f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}；"
              f"来源：{'合成（干跑）' if args.synthetic else '正式数据'}；"
              f"`n_em`={args.n_em}、`n_draws`={args.n_draws}、`n_x`={args.n_x}",
              "",
              "> ⚠️ 本线全线是**最大似然 + 拉普拉斯近似**，不是贝叶斯后验；"
              "拉普拉斯协方差的特征值谱与 `n_flipped` 必须一并报告。", ""]
    if rejected:
        report += ["## 被拒文件", ""] + [
            f"* `{r['file']}`：{r['reason']}" for r in rejected] + [""]

    payload = {"rejected": rejected, "groups": {}}
    for g, plist in sorted(groups.items()):
        out = run_group(plist, str(g), args.n_em, args.n_draws, args.n_x,
                        args.seed, args.bruteforce, keep_matrices=False)
        report += out["lines"] + [""]
        payload["groups"][str(g)] = _jsonable(out["results"])

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
