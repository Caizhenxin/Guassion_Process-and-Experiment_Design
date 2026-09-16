# -*- coding: utf-8 -*-
"""
refit_main_fits.py —— 主口径重跑（多链、更大抽样）2026-09-13
==========================================================
动机（来自收敛诊断）：历史主拟合为**单链** 3,000 draws / 500 burn-in，G3 严重不收敛
（z 的 ESS = 8.6、R̂ = 1.32）、G8 的起始点参数不达标（ESS = 22）。

本脚本按建议重跑主口径 6 个条件（G3–G8，可选含 G1/G2）：
    chains = 4、draws = 8,000、burn-in = 2,000（HDDM 原生多链 + parallel=True）
并完成三件事：
    ① 严格的多链 R-hat / ESS 诊断；
    ② 新旧参数对照（判断重跑是否实质改变结论）；
    ③ 输出可供下游（Sigmoid 校准 / GP / PPC / 留出验证）直接使用的新冻结表。

用法
----
    python refit_main_fits.py --mode prepare                # 生成作业（数据已存在，无需复制）
    python refit_main_fits.py --mode fit --parallel 4       # Docker 并行拟合（6 个作业）
    python refit_main_fits.py --mode collect                # 诊断 + 新旧对照 + 新冻结表

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/refit/
    fits/{tag}_stats.csv、{tag}_chains.npz、{tag}_meta.json
    convergence_multichain.csv     多链 R̂ / ESS（逐条件 × 逐参数）
    refit_vs_old.csv               新参数 vs 历史参数（含变化量与推断）
    input_conditions_g3g8_refit.csv 新冻结表（供冻结版流程使用）
3_Figures/Thesis_v3_20260912/F6-7_refit_comparison.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import (HDDM_READY_DIR, OUT_DATA_DIR, OUT_FIG_DIR,  # noqa: E402
                       extract_params_from_stats, setup_cjk_font)

REFIT = OUT_DATA_DIR / "refit"
FITS = REFIT / "fits"
JOBS = REFIT / "jobs.json"
OLD_PARAMS = BASE / "2_Data" / "Real_Data" / "HDDM_Traces" / "all_groups_ddm_params.csv"
OLD_FROZEN = BASE / "2_Data" / "Generate_Data" / "GP_Sigmoid_Cleaned" / "step3_cleaned_hddm_params_main.csv"

DEFAULT_IMAGE, DEFAULT_MOUNT = "hcp4715/hddm", \
    "D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work"
CW = "/home/jovyan/work"
PARAMS = ["v_self", "v_stranger", "a", "t", "z", "SPE_v"]
CORE = ["v(0)", "v(1)", "a", "t", "z_trans"]
RHAT_OK, ESS_OK = 1.01, 400.0


# ------------------------------------------------------------------
def prepare(groups: list[int], draws: int, burn: int, chains: int, seed: int):
    REFIT.mkdir(parents=True, exist_ok=True)
    FITS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for gid in groups:
        f = list(HDDM_READY_DIR.glob(f"hddm_data_group{gid}_*.csv"))
        if not f:
            print(f"  ⚠️ G{gid} 无数据，跳过")
            continue
        rel = f[0].relative_to(BASE / "2_Data" / "Real_Data")  # 直接使用 HDDM_Ready 数据
        jobs.append({"group_id": gid, "tag": f"g{gid}_refit", "scheme": "censor",
                     "data_rel": f"2_Data/Real_Data/{rel.as_posix()}",
                     "p_outlier": 0.0})
    JOBS.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 自动生成：主口径多链重跑"]
    for j in jobs:
        cmd = ["docker", "run", "--rm", "--cpus=4", "-v", DEFAULT_MOUNT, DEFAULT_IMAGE,
               "python", f"{CW}/1_Code/Python_for_Check/TenRules_Revision_20260912/fit_one_hddm_chains.py",
               "--data", f"{CW}/{j['data_rel']}",
               "--out-dir", f"{CW}/2_Data/Generate_Data/TenRules_Revision_20260912/refit/fits",
               "--tag", j["tag"], "--p-outlier", "0.0",
               "--draws", str(draws), "--burn", str(burn), "--chains", str(chains), "--seed", str(seed)]
        lines.append("& " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    (REFIT / "run_refit.ps1").write_text("\n".join(lines), encoding="utf-8")
    print(f"[prepare] 作业 {len(jobs)} 个（chains={chains}, draws={draws}, burn={burn}）→ {JOBS}")


def _cmd(j, draws, burn, chains, seed):
    return ["docker", "run", "--rm", "--cpus=4", "-v", DEFAULT_MOUNT, DEFAULT_IMAGE,
            "python", f"{CW}/1_Code/Python_for_Check/TenRules_Revision_20260912/fit_one_hddm_chains.py",
            "--data", f"{CW}/{j['data_rel']}",
            "--out-dir", f"{CW}/2_Data/Generate_Data/TenRules_Revision_20260912/refit/fits",
            "--tag", j["tag"], "--p-outlier", str(j["p_outlier"]),
            "--draws", str(draws), "--burn", str(burn), "--chains", str(chains), "--seed", str(seed)]


def fit(parallel: int, draws: int, burn: int, chains: int, seed: int):
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    todo = [j for j in jobs if not (FITS / f"{j['tag']}_stats.csv").exists()]
    print(f"[fit] 待拟合 {len(todo)} / {len(jobs)}（chains={chains}, draws={draws}, 并行 {parallel}）", flush=True)
    if shutil.which("docker") is None:
        print("[fit] 未找到 docker；请执行 run_refit.ps1")
        return
    lock = threading.Lock()
    box = {"ok": 0, "fail": 0}

    def one(pair):
        i, j = pair
        log = FITS / f"{j['tag']}.log"
        with open(log, "w", encoding="utf-8", errors="replace") as fh:
            r = subprocess.run(_cmd(j, draws, burn, chains, seed), stdout=fh, stderr=subprocess.STDOUT)
        with lock:
            if r.returncode == 0:
                box["ok"] += 1
                print(f"[fit] ({i}/{len(todo)}) {j['tag']} 完成", flush=True)
            else:
                box["fail"] += 1
                print(f"[fit] ({i}/{len(todo)}) {j['tag']} 失败 rc={r.returncode}（见 {log.name}）", flush=True)

    if parallel > 1:
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            list(ex.map(one, list(enumerate(todo, 1))))
    else:
        for item in enumerate(todo, 1):
            one(item)
    print(f"[fit] 结束（成功 {box['ok']} / 失败 {box['fail']}）", flush=True)


# ------------------------------------------------------------------
def multi_chain_diag(arr2d: np.ndarray) -> tuple[float, float]:
    """多链 R-hat 与 ESS（arr2d: (chains, draws)）。"""
    x = np.asarray(arr2d, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2:
        return float("nan"), float("nan")
    m, n = x.shape
    means = x.mean(axis=1)
    W = x.var(axis=1, ddof=1).mean()
    B = n * means.var(ddof=1)
    if W <= 0:
        return float("nan"), float("nan")
    var_hat = (n - 1) / n * W + B / n
    rhat = float(np.sqrt(var_hat / W))

    def ess_1d(y):
        y = y - y.mean()
        N = len(y)
        f = np.fft.rfft(y, n=2 * N)
        acf = np.fft.irfft(f * np.conj(f))[:N].real
        if acf[0] <= 0:
            return float(N)
        acf /= acf[0]
        s = 0.0
        for k in range(1, N):
            if acf[k] <= 0:
                break
            s += acf[k]
        return float(max(N / (1 + 2 * s), 1.0))

    return rhat, float(sum(ess_1d(x[c]) for c in range(m)))


def collect(draws: int, chains: int):
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    diag_rows, param_rows = [], []
    old = pd.read_csv(OLD_PARAMS).set_index("group_id") if OLD_PARAMS.exists() else None

    for j in jobs:
        gid, tag = j["group_id"], j["tag"]
        sp, np_ = FITS / f"{tag}_stats.csv", FITS / f"{tag}_chains.npz"
        if not sp.exists():
            print(f"  ⚠️ {tag} 缺少结果，跳过")
            continue
        stats = pd.read_csv(sp, index_col=0)
        new = extract_params_from_stats(stats)

        if np_.exists():
            z = np.load(np_)
            for p in CORE:
                if p in z.files:
                    rhat, ess = multi_chain_diag(z[p])
                    diag_rows.append({"group_id": gid, "param": p, "rhat": rhat, "ess": ess,
                                      "n_chains": int(z[p].shape[0]) if z[p].ndim == 2 else 1,
                                      "n_draws": int(z[p].shape[-1])})
            # 被试层参数（若存在）
            for key in z.files:
                if key.endswith("_std") or "subj" in key:
                    continue
        else:
            print(f"  ⚠️ {tag} 无多链迹线（也许 infdata 不可用），仅报告参数")

        for p in PARAMS:
            if p not in new:
                continue
            row = {"group_id": gid, "param": p, "new_est": new[p]["mean"],
                   "new_lo": new[p]["lo"], "new_hi": new[p]["hi"],
                   "new_ci_width": new[p]["hi"] - new[p]["lo"]}
            if old is not None and gid in old.index:
                col = {"v_self": "v_self_mean", "v_stranger": "v_stranger_mean", "a": "a_mean",
                       "t": "t_mean", "z": "z_mean"}.get(p)
                if col:
                    row["old_est"] = float(old.loc[gid, col])
                    row["delta"] = row["new_est"] - row["old_est"]
                elif p == "SPE_v":
                    row["old_est"] = float(old.loc[gid, "v_self_mean"] - old.loc[gid, "v_stranger_mean"])
                    row["delta"] = row["new_est"] - row["old_est"]
            param_rows.append(row)

    diag = pd.DataFrame(diag_rows)
    diag.to_csv(REFIT / "convergence_multichain.csv", index=False)
    cmp_df = pd.DataFrame(param_rows)
    cmp_df.to_csv(REFIT / "refit_vs_old.csv", index=False)

    print("\n[collect] 多链收敛（核心参数）：")
    if not diag.empty:
        core = diag[diag["param"].isin(CORE)]
        for gid, g in core.groupby("group_id"):
            ok = ((g.rhat <= RHAT_OK) & (g.ess >= ESS_OK)).mean()
            print(f"  G{gid}: 达标 {ok:.0%}（{int(((g.rhat<=RHAT_OK)&(g.ess>=ESS_OK)).sum())}/{len(g)}）"
                  f" R̂最大 {g.rhat.max():.3f}，ESS最小 {g.ess.min():.0f}")
    print("\n[collect] 新旧参数对照（关键行）：")
    if not cmp_df.empty:
        piv = cmp_df.pivot_table(index="group_id", columns="param", values=["old_est", "new_est", "delta"])
        print(piv.round(3).to_string())

    # 新冻结表：基于旧冻结表替换群体参数
    if OLD_FROZEN.exists() and not cmp_df.empty:
        fr = pd.read_csv(OLD_FROZEN)
        fr["_gid"] = fr["source_group_ids"].astype(int)
        for p, col in [("v_self", "v_self_mean"), ("v_stranger", "v_stranger_mean"),
                       ("a", "a_mean"), ("t", "t_mean"), ("z", "z_mean")]:
            m = cmp_df[cmp_df.param == p].set_index("group_id")["new_est"]
            fr[col] = fr["_gid"].map(m).fillna(fr[col])
        fr["SPE_v"] = fr["v_self_mean"] - fr["v_stranger_mean"]
        fr.to_csv(REFIT / "input_conditions_g3g8_refit.csv", index=False)
        print(f"\n[collect] 新冻结表 → {REFIT / 'input_conditions_g3g8_refit.csv'}")

    # 图：新旧参数对照
    if not cmp_df.empty:
        setup_cjk_font()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
        for ax, p in zip(axes, ["v_self", "a", "z"]):
            sub = cmp_df[cmp_df.param == p].sort_values("group_id")
            x = np.arange(len(sub))
            ax.errorbar(x - .12, sub.old_est, yerr=None, fmt="o", color="#999999", label="历史（单链 3k）")
            ax.errorbar(x + .12, sub.new_est,
                        yerr=[sub.new_est - sub.new_lo, sub.new_hi - sub.new_est],
                        fmt="o", color="#2a6f97", capsize=3, label=f"重跑（4 链 8k）")
            ax.set_xticks(x); ax.set_xticklabels([f"G{int(g)}" for g in sub.group_id])
            ax.set_title(p); ax.legend(fontsize=8)
        fig.suptitle("图6-7 主口径重跑：新旧群体层参数对照（含 95% CI）")
        fig.tight_layout(); fig.savefig(OUT_FIG_DIR / "F6-7_refit_comparison.png", dpi=300)
        plt.close(fig)
        print(f"[collect] 图 → {OUT_FIG_DIR / 'F6-7_refit_comparison.png'}")


def main():
    ap = argparse.ArgumentParser(description="主口径多链重跑")
    ap.add_argument("--mode", required=True, choices=["prepare", "fit", "collect"])
    ap.add_argument("--groups", default="3,4,5,6,7,8")
    ap.add_argument("--draws", type=int, default=8000)
    ap.add_argument("--burn", type=int, default=2000)
    ap.add_argument("--chains", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--parallel", type=int, default=3)
    args = ap.parse_args()

    if args.mode == "prepare":
        prepare([int(g) for g in args.groups.split(",") if g.strip()], args.draws, args.burn,
                args.chains, args.seed)
    elif args.mode == "fit":
        fit(args.parallel, args.draws, args.burn, args.chains, args.seed)
    else:
        collect(args.draws, args.chains)


if __name__ == "__main__":
    main()
