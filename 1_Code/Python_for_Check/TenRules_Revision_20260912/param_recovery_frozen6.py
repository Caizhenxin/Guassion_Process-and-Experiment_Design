# -*- coding: utf-8 -*-
"""
param_recovery_frozen6.py —— 规则5：冻结版参数恢复（Parameter Recovery）
=======================================================================
对应《计算建模十条规则》规则5："Check that you can recover your parameters"
以及规则4（多起点/全局最优）与规则9（报告参数恢复）。

核心逻辑
--------
1. **真值** = 冻结主口径 6 条件（G3–G8）的 HDDM 群体后验均值（来自 `input_conditions_g3g8.csv`）。
2. **合成数据** = 用冻结口径的 Euler–Maruyama 仿真器，按每条件真实被试数、每身份 130 试次、
   真实 deadline(=T+W) 生成（可加入被试水平抖动模拟个体差异）。
3. **恢复** = 对合成数据跑与研究二完全相同的两条流程（Censor / Drop）做 HDDM 层级拟合。
4. **指标** = 真值 vs 恢复值的偏差、RMSE、95% CI 覆盖率、跨条件相关；
   并额外给出"**遗漏率 → 偏倚**"曲线（把论文中 35%/15% 的描述性分档升级为仿真支持的结论）。

用法
----
    # ① 生成合成数据 + 拟合作业（宿主机，需 numpy/pandas）
    python param_recovery_frozen6.py --mode prepare --n-reps 3

    # ② 在 Docker 中执行全部 HDDM 拟合（可先跑 --dry-run 看命令）
    python param_recovery_frozen6.py --mode fit-docker --dry-run
    python param_recovery_frozen6.py --mode fit-docker

    # ③ 汇总指标与图（宿主机）
    python param_recovery_frozen6.py --mode collect

    # 附加：仅生成"遗漏率–偏倚"曲线数据（8 个水平 × 2 方案 × 2 重复）
    python param_recovery_frozen6.py --mode curve --curve-reps 2

    # 自检：不依赖 Docker，验证仿真器与统计口径
    python param_recovery_frozen6.py --mode sanity

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/param_recovery/
    prepared/{censor,drop}/*.csv      HDDM 输入
    fits/{censor,drop}/*_stats.csv    拟合结果（Docker 产出）
    jobs.json                         作业清单（含真值、deadline、遗漏率）
    recovery_by_job.csv / recovery_summary.csv / omission_curve_bias.csv
3_Figures/TenRules_Revision_20260912/param_recovery_*.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # 控制台编码兜底（避免 ⚠️ 等字符在 GBK 控制台报错）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import (  # noqa: E402
    BASE_DIR, OUT_DATA_DIR, OUT_FIG_DIR, TRIALS_PER_IDENTITY,
    ensure_dirs, extract_params_from_stats, load_frozen_truth,
    simulate_condition_block, simulate_trials, to_drop,
)

PR_ROOT = OUT_DATA_DIR / "param_recovery"
PREPARED = PR_ROOT / "prepared"
FITS = PR_ROOT / "fits"
JOBS_JSON = PR_ROOT / "jobs.json"

DEFAULT_IMAGE = "hcp4715/hddm"
DEFAULT_MOUNT = "D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work"
CONTAINER_WORK = "/home/jovyan/work"
PARAMS = ["v_self", "v_stranger", "a", "t", "z", "SPE_v"]

JITTER_PRESETS = {
    "none": None,
    # 被试水平抖动的保守设定（文献典型量级，用于检验"个体差异存在时恢复是否仍成立"）
    "moderate": {"v_self": 0.30, "v_stranger": 0.30, "a": 0.20, "t": 0.02, "z": 0.02},
}


# ------------------------------------------------------------------
# 数据生成
# ------------------------------------------------------------------
def _jobs_for_datasets(truth: pd.DataFrame, n_reps: int, schemes: list[str],
                       n_subjects_override: int | None, trials_per_identity: int,
                       jitter_sd: dict | None, seed: int, kind: str = "condition",
                       curve_levels: list[float] | None = None,
                       curve_truth: dict | None = None) -> list[dict]:
    jobs: list[dict] = []
    rng_master = np.random.default_rng(seed)

    if kind == "condition":
        iterable = [(int(r.group_id), r, None) for _, r in truth.iterrows()]
    else:  # curve：固定真值、扫描 deadline 以命中目标遗漏率
        iterable = [(idx, None, lvl) for idx, lvl in enumerate(curve_levels or [])]

    for key, row, level in iterable:
        if kind == "condition":
            params = {"v_self": float(row.v_self), "v_stranger": float(row.v_stranger),
                      "a": float(row.a), "t": float(row.t), "z": float(row.z)}
            deadline = float((row.T_ms + row.W_ms) / 1000.0)
            n_subjects = int(n_subjects_override or row.n_subjects)
            gid = int(row.group_id)
        else:
            params = dict(curve_truth)
            n_subjects = int(n_subjects_override or 12)
            gid = -1

        for rep in range(1, n_reps + 1):
            rng = np.random.default_rng(rng_master.integers(1, 2**31 - 1))
            if kind == "curve":
                deadline, realized = find_deadline_for_omission(
                    params, float(level), rng, trials_per_identity=trials_per_identity)
                if realized is None:
                    print(f"  [curve] 目标遗漏率 {level:.2f} 无法命中，跳过")
                    continue
            else:
                sim_check = simulate_condition_block(
                    params["v_self"], params["v_stranger"], params["a"], params["t"], params["z"],
                    deadline, min(n_subjects, 6), rng, trials_per_identity=trials_per_identity,
                    jitter_sd=jitter_sd)
                realized = float(sim_check["omission"].mean())

            rng = np.random.default_rng(rng_master.integers(1, 2**31 - 1))
            df = simulate_condition_block(
                params["v_self"], params["v_stranger"], params["a"], params["t"], params["z"],
                deadline, n_subjects, rng, trials_per_identity=trials_per_identity,
                jitter_sd=jitter_sd)
            realized = float(df["omission"].mean())

            frames = {"censor": df, "drop": to_drop(df)}
            for scheme in schemes:
                if kind == "condition":
                    tag = f"cond{gid}_rep{rep}_{scheme}"
                else:
                    tag = f"curve{int(round(level*100)):02d}_rep{rep}_{scheme}"
                n = len(frames[scheme])
                jobs.append({
                    "kind": kind, "scheme": scheme, "tag": tag, "group_id": gid, "rep": rep,
                    "level": level, "deadline": deadline, "realized_omission": realized,
                    "n_subjects": n_subjects, "n_trials": int(n),
                    "trials_per_identity": trials_per_identity,
                    "truth": params,
                    "p_outlier": 0.0 if scheme == "censor" else 0.05,
                    "_frame": frames[scheme],
                    "rel_path": f"TenRules_Revision_20260912/param_recovery/prepared/{scheme}/{tag}.csv",
                })
    return jobs


def find_deadline_for_omission(params: dict, target: float, rng, trials_per_identity: int = 130,
                               n_probe: int = 2000, max_iter: int = 22, tol: float = 0.01):
    """给定真实参数，二分搜索使遗漏率命中 target 的 deadline（秒）。"""
    def rate_at(deadline: float) -> float:
        sim_s = simulate_trials(params["v_stranger"], params["a"], params["t"], params["z"],
                                deadline, n_probe, rng)
        sim_self = simulate_trials(params["v_self"], params["a"], params["t"], params["z"],
                                   deadline, n_probe, rng)
        om = np.concatenate([sim_s["omission"], sim_self["omission"]])
        return float(om.mean())

    lo = params["t"] + 0.02          # 极短 deadline → 遗漏率最高
    hi = max(lo + 0.05, 4.0)         # 极长 deadline → 遗漏率 ~ 0
    r_lo, r_hi = rate_at(lo), rate_at(hi)
    if not (r_hi - tol <= target <= r_lo + tol):
        return None, None
    deadline, realized = lo, r_lo
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        realized = rate_at(mid)
        deadline = mid
        if abs(realized - target) <= tol:
            break
        if realized > target:     # 遗漏过多 → 需要更长 deadline
            lo = mid
        else:
            hi = mid
    return float(deadline), float(realized)


def write_prepared(jobs: list[dict], append: bool = False) -> list[dict]:
    ensure_dirs()
    for scheme in ["censor", "drop"]:
        (PREPARED / scheme).mkdir(parents=True, exist_ok=True)
        (FITS / scheme).mkdir(parents=True, exist_ok=True)

    existing = []
    if append and JOBS_JSON.exists():
        existing = json.loads(JOBS_JSON.read_text(encoding="utf-8"))
        existing = [j for j in existing if j["tag"] not in {x["tag"] for x in jobs}]

    rows = []
    for job in jobs:
        path = BASE_DIR / "2_Data" / "Generate_Data" / job["rel_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        job["_frame"].to_csv(path, index=False)
        rows.append({k: v for k, v in job.items() if not k.startswith("_")})

    all_jobs = existing + rows
    JOBS_JSON.write_text(json.dumps(all_jobs, ensure_ascii=False, indent=2), encoding="utf-8")

    # 生成可直接运行的 Docker 批处理脚本
    _write_run_scripts(all_jobs)
    print(f"[prepare] 写入 {len(rows)} 个数据集 → {PREPARED}")
    print(f"[prepare] 作业清单 → {JOBS_JSON}（累计 {len(all_jobs)} 个作业）")
    return all_jobs


def _docker_cmd(job: dict, image: str, mount: str) -> list[str]:
    return [
        "docker", "run", "--rm", "--cpus=2",
        "-v", mount,
        image,
        "python", f"{CONTAINER_WORK}/1_Code/Python_for_Check/TenRules_Revision_20260912/fit_one_hddm.py",
        "--data", f"{CONTAINER_WORK}/2_Data/Generate_Data/{job['rel_path']}",
        "--out-dir", f"{CONTAINER_WORK}/2_Data/Generate_Data/TenRules_Revision_20260912/param_recovery/fits/{job['scheme']}",
        "--tag", job["tag"],
        "--p-outlier", str(job["p_outlier"]),
    ]


def _write_run_scripts(jobs: list[dict], image: str = DEFAULT_IMAGE, mount: str = DEFAULT_MOUNT):
    ps1 = ["# 自动生成：依次执行全部 HDDM 拟合（PowerShell）"]
    sh = ["#!/usr/bin/env bash", "# 自动生成：依次执行全部 HDDM 拟合（bash）"]
    for job in jobs:
        cmd = _docker_cmd(job, image, mount)
        ps1.append("& " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        sh.append(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    (PR_ROOT / "run_fits.ps1").write_text("\n".join(ps1), encoding="utf-8")
    (PR_ROOT / "run_fits.sh").write_text("\n".join(sh), encoding="utf-8")


def run_docker(jobs: list[dict], image: str, mount: str, dry_run: bool, skip_existing: bool,
               parallel: int = 1):
    todo = [j for j in jobs if not (skip_existing and (FITS / j["scheme"] / f"{j['tag']}_stats.csv").exists())]
    print(f"[fit-docker] 待拟合 {len(todo)} / 共 {len(jobs)} 个（镜像 {image}）")
    if dry_run:
        for job in todo[:5]:
            print("  " + " ".join(_docker_cmd(job, image, mount)))
        if len(todo) > 5:
            print(f"  ...（其余 {len(todo)-5} 条见 {PR_ROOT / 'run_fits.ps1'}）")
        return
    if shutil.which("docker") is None:
        print("[fit-docker] 未找到 docker 命令。请在装有 Docker Desktop 的机器上运行，"
              f"或直接执行 {PR_ROOT / 'run_fits.ps1'}")
        return
    box = {"ok": 0, "fail": 0, "lock": None}
    import threading
    box["lock"] = threading.Lock()

    def _one(idx_job):
        idx, job = idx_job
        log_path = FITS / job["scheme"] / f"{job['tag']}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
            r = subprocess.run(_docker_cmd(job, image, mount), stdout=fh, stderr=subprocess.STDOUT)
        with box["lock"]:
            if r.returncode == 0:
                box["ok"] += 1
                print(f"[fit-docker] ({idx}/{len(todo)}) {job['tag']} 完成", flush=True)
            else:
                box["fail"] += 1
                print(f"[fit-docker] ({idx}/{len(todo)}) {job['tag']} 失败：returncode={r.returncode}"
                      f"（详见 {log_path.name}）", flush=True)

    if parallel and parallel > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=int(parallel)) as ex:
            list(ex.map(_one, list(enumerate(todo, 1))))
    else:
        for item in enumerate(todo, 1):
            _one(item)
    print(f"[fit-docker] 全部作业执行完毕（成功 {box['ok']} / 失败 {box['fail']}）")


# ------------------------------------------------------------------
# 指标汇总
# ------------------------------------------------------------------
def collect(jobs: list[dict]):
    rows, missing = [], 0
    for job in jobs:
        stats_path = FITS / job["scheme"] / f"{job['tag']}_stats.csv"
        if not stats_path.exists():
            missing += 1
            continue
        stats = pd.read_csv(stats_path, index_col=0)
        est = extract_params_from_stats(stats)
        truth = job["truth"]
        row = {
            "kind": job["kind"], "scheme": job["scheme"], "tag": job["tag"],
            "group_id": job["group_id"], "rep": job["rep"], "level": job.get("level"),
            "deadline": job["deadline"], "realized_omission": job["realized_omission"],
            "n_subjects": job["n_subjects"], "n_trials": job["n_trials"],
        }
        for p in PARAMS:
            true_val = (truth["v_self"] - truth["v_stranger"]) if p == "SPE_v" else truth.get(p)
            row[f"{p}_true"] = true_val
            if p in est:
                row[f"{p}_est"] = est[p]["mean"]
                row[f"{p}_lo"] = est[p]["lo"]
                row[f"{p}_hi"] = est[p]["hi"]
                row[f"{p}_bias"] = est[p]["mean"] - true_val
                row[f"{p}_covered"] = int(est[p]["lo"] <= true_val <= est[p]["hi"])
        rows.append(row)

    if missing:
        print(f"[collect] ⚠️ {missing} 个作业缺少拟合结果（需先运行 --mode fit-docker）")

    if not rows:
        print("[collect] 尚无可汇总的拟合结果。")
        return None

    by_job = pd.DataFrame(rows)
    by_job.to_csv(PR_ROOT / "recovery_by_job.csv", index=False)

    summary = []
    for (kind, scheme), g in by_job.groupby(["kind", "scheme"]):
        for p in PARAMS:
            if f"{p}_est" not in g.columns:
                continue
            sub = g.dropna(subset=[f"{p}_est"])
            if sub.empty:
                continue
            summary.append({
                "kind": kind, "scheme": scheme, "param": p, "n": len(sub),
                "bias_mean": sub[f"{p}_bias"].mean(),
                "bias_sd": sub[f"{p}_bias"].std(ddof=1) if len(sub) > 1 else np.nan,
                "rmse": float(np.sqrt((sub[f"{p}_bias"] ** 2).mean())),
                "coverage_95": sub[f"{p}_covered"].mean() if f"{p}_covered" in sub else np.nan,
                "r_pearson": sub[f"{p}_est"].corr(sub[f"{p}_true"]),
                "r_spearman": sub[f"{p}_est"].corr(sub[f"{p}_true"], method="spearman"),
            })
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(PR_ROOT / "recovery_summary.csv", index=False)

    # 遗漏率 → 偏倚曲线
    curve = by_job[by_job["kind"] == "curve"]
    if not curve.empty:
        crows = []
        bins = [0, .05, .10, .15, .20, .25, .35, .45, .60, 1.0]
        curve = curve.assign(bin=pd.cut(curve["realized_omission"], bins))
        for (scheme, b), g in curve.groupby(["scheme", "bin"], observed=True):
            for p in ["v_self", "v_stranger", "a", "SPE_v"]:
                if f"{p}_bias" in g:
                    crows.append({"scheme": scheme, "omission_bin": str(b),
                                  "omission_mid": g["realized_omission"].mean(),
                                  "param": p, "bias_mean": g[f"{p}_bias"].mean(), "n": len(g)})
        pd.DataFrame(crows).to_csv(PR_ROOT / "omission_curve_bias.csv", index=False)

    _plot(by_job, summary_df)
    print(f"[collect] 汇总完成 → {PR_ROOT}")
    print(summary_df.round(3).to_string(index=False))
    return by_job


def _plot(by_job: pd.DataFrame, summary_df: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sim_utils import setup_cjk_font
    setup_cjk_font()

    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    cond = by_job[by_job["kind"] == "condition"]

    # 图1：真值 vs 恢复值
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for j, scheme in enumerate(["censor", "drop"]):
        sub = cond[cond["scheme"] == scheme]
        for k, p in enumerate(["v_self", "v_stranger", "a"]):
            ax = axes[j, k]
            if f"{p}_est" in sub:
                ax.scatter(sub[f"{p}_true"], sub[f"{p}_est"], s=28)
                lim = [min(sub[f"{p}_true"].min(), sub[f"{p}_est"].min()) - 0.2,
                       max(sub[f"{p}_true"].max(), sub[f"{p}_est"].max()) + 0.2]
                ax.plot(lim, lim, "k--", lw=1)
                ax.set_xlim(lim); ax.set_ylim(lim)
            ax.set_title(f"{scheme} · {p}")
            ax.set_xlabel("真值"); ax.set_ylabel("恢复值")
    fig.suptitle("参数恢复：真值 vs 恢复值（冻结 6 条件）")
    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "param_recovery_scatter.png", dpi=200)
    plt.close(fig)

    # 图2：遗漏率 → 偏倚
    curve = by_job[by_job["kind"] == "curve"]
    if not curve.empty:
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
        for ax, p in zip(axes, ["v_self", "a", "SPE_v"]):
            for scheme, mk in [("censor", "o"), ("drop", "s")]:
                sub = curve[curve["scheme"] == scheme]
                if f"{p}_bias" in sub:
                    ax.plot(sub["realized_omission"] * 100, sub[f"{p}_bias"], mk + "-", label=scheme)
            ax.axhline(0, color="k", lw=0.8)
            ax.axvline(35, color="r", ls=":", lw=1)
            ax.axvline(15, color="orange", ls=":", lw=1)
            ax.set_xlabel("实际遗漏率 (%)"); ax.set_ylabel(f"{p} 偏倚 (估计 − 真值)")
            ax.set_title(p); ax.legend()
        fig.suptitle("遗漏率 → 参数偏倚（红/橙虚线 = 论文中的 35% / 15% 分档）")
        fig.tight_layout()
        fig.savefig(OUT_FIG_DIR / "param_recovery_omission_bias.png", dpi=200)
        plt.close(fig)

    # 图3：95% CI 覆盖率
    cov = summary_df[summary_df["kind"] == "condition"].dropna(subset=["coverage_95"])
    if not cov.empty:
        piv = cov.pivot_table(index="param", columns="scheme", values="coverage_95")
        ax = piv.plot(kind="bar", figsize=(8, 4), rot=0)
        ax.axhline(0.95, color="k", ls="--", lw=1, label="名义 95%")
        ax.set_ylabel("95% CI 覆盖率"); ax.set_title("参数恢复的区间覆盖率（条件水平）")
        ax.legend()
        ax.figure.tight_layout()
        ax.figure.savefig(OUT_FIG_DIR / "param_recovery_coverage.png", dpi=200)
        ax.figure.clf()


# ------------------------------------------------------------------
# sanity：不需 Docker 的自检
# ------------------------------------------------------------------
def sanity(truth: pd.DataFrame, trials_per_identity: int, seed: int = 42):
    print("=" * 68)
    print("sanity：验证仿真器行为是否与真实数据同量级（不需 Docker）")
    print("=" * 68)
    rng = np.random.default_rng(seed)
    for _, row in truth.iterrows():
        df = simulate_condition_block(row.v_self, row.v_stranger, row.a, row.t, row.z,
                                      float((row.T_ms + row.W_ms) / 1000.0), int(row.n_subjects),
                                      rng, trials_per_identity=trials_per_identity)
        om = df["omission"].mean()
        responded = df[df["omission"] == 0]
        acc = (responded["response"] == 1).mean()
        rt = responded.loc[responded["response"] == 1, "rt"].mean() * 1000
        print(f"G{int(row.group_id)} P{int(row.P)} T{int(row.T_ms)} W{int(row.W_ms)} | "
              f"仿真遗漏 {om*100:5.1f}% (真实 {row.omission_rate*100:5.1f}%) | "
              f"responded ACC {acc:.3f} | 正确RT均值 {rt:6.1f} ms")
    print("\n提示：若某条件仿真遗漏率与真实差异过大，说明该条件的 HDDM 参数本身不可靠"
          "（正是研究二 G1–G4 的情况），应在论文中据实说明。")


def main():
    ap = argparse.ArgumentParser(description="冻结版参数恢复（规则5）")
    ap.add_argument("--mode", required=True,
                    choices=["sanity", "prepare", "fit-docker", "collect", "curve", "all"])
    ap.add_argument("--n-reps", type=int, default=3, help="每条件重复次数（默认 3）")
    ap.add_argument("--schemes", default="censor,drop")
    ap.add_argument("--trials-per-identity", type=int, default=TRIALS_PER_IDENTITY)
    ap.add_argument("--n-subjects-override", type=int, default=None,
                    help="覆盖每条件被试数（例如 20，用于预览样本量扩充后的精度）")
    ap.add_argument("--jitter", default="none", choices=list(JITTER_PRESETS))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--mount", default=DEFAULT_MOUNT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-existing", action="store_true", default=True)
    ap.add_argument("--parallel", type=int, default=4, help="并行运行的 docker 容器数（默认 4）")
    ap.add_argument("--append", action="store_true", help="prepare 时保留既有作业清单")
    ap.add_argument("--curve-reps", type=int, default=2)
    ap.add_argument("--curve-levels", default="0.05,0.10,0.15,0.20,0.25,0.35,0.50,0.70")
    ap.add_argument("--curve-truth-group", type=int, default=0,
                    help="曲线用的真值来自哪个条件的参数；0=6 条件参数均值（默认）")
    args = ap.parse_args()

    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()]
    truth = load_frozen_truth()
    jitter_sd = JITTER_PRESETS[args.jitter]

    if args.mode == "sanity":
        sanity(truth, args.trials_per_identity, args.seed)
        return

    if args.mode in ("prepare", "all"):
        jobs = _jobs_for_datasets(truth, args.n_reps, schemes, args.n_subjects_override,
                                  args.trials_per_identity, jitter_sd, args.seed, kind="condition")
        write_prepared(jobs, append=args.append)

    if args.mode == "curve":
        if args.curve_truth_group == 0:
            curve_truth = {"v_self": float(truth.v_self.mean()), "v_stranger": float(truth.v_stranger.mean()),
                           "a": float(truth.a.mean()), "t": float(truth.t.mean()), "z": float(truth.z.mean())}
        else:
            r = truth[truth.group_id == args.curve_truth_group].iloc[0]
            curve_truth = {"v_self": float(r.v_self), "v_stranger": float(r.v_stranger),
                           "a": float(r.a), "t": float(r.t), "z": float(r.z)}
        levels = [float(x) for x in args.curve_levels.split(",")]
        print(f"[curve] 真值 = {curve_truth}\n[curve] 目标遗漏率 = {levels}")
        jobs = _jobs_for_datasets(truth, args.curve_reps, schemes, args.n_subjects_override,
                                  args.trials_per_identity, jitter_sd, args.seed,
                                  kind="curve", curve_levels=levels, curve_truth=curve_truth)
        write_prepared(jobs, append=True)

    if args.mode in ("fit-docker", "all"):
        if not JOBS_JSON.exists():
            print("请先运行 --mode prepare 生成作业清单")
            return
        jobs = json.loads(JOBS_JSON.read_text(encoding="utf-8"))
        run_docker(jobs, args.image, args.mount, args.dry_run, args.skip_existing, args.parallel)

    if args.mode in ("collect", "all"):
        if not JOBS_JSON.exists():
            print("请先运行 --mode prepare 生成作业清单")
            return
        jobs = json.loads(JOBS_JSON.read_text(encoding="utf-8"))
        collect(jobs)


if __name__ == "__main__":
    main()
