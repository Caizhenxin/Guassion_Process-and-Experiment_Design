# -*- coding: utf-8 -*-
"""
holdout_subject_validation.py —— 留出被试验证（预测新被试）2026-09-12
====================================================================
目的（《十条规则》规则7"验证"与规则10"预测新情境"的最强形式）：
    把每个条件的被试分层随机分为**估计集**与**验证集**，只用估计集拟合 HDDM 并校准 Sigmoid+GP 模型，
    再去预测**从未参与估计的被试**的行为与参数。这是不新增实验条件即可获得的"样本外验证"。

为什么需要扩样本才能做
----------------------
* 现有每条件仅 10–12 人；按 2/3 拆分后估计集约 7–8 人，HDDM 层级拟合不稳定（见收敛诊断）。
* 建议每条件 ≥20 人后再运行本脚本（估计集 13–14 人 / 验证集 6–7 人）；现在也可运行，但结论仅作方法演示。

两种留出
--------
(A) **参数层留出**：用估计集拟合的模型预测验证集条件的 HDDM 参数（验证集也需拟合作参照），
    报告预测误差与相关（与全样本预测对比）。
(B) **行为层留出**：用估计集模型仿真验证集规模的行为，比较验证集的 ACC / 遗漏率 / 正确 RT 分位数 /
    SPE_RT / SPE_ACC，报告观测值是否落在 95% 预测区间内（与 ppc_frozen6.py 同一套统计口径）。

用法
----
    # ① 生成拆分数据与 HDDM 拟合作业（宿主机）
    python holdout_subject_validation.py --mode prepare --holdout-frac 0.33 --seed 42

    # ② 在 Docker 中拟合"估计集"数据（复用 fit_one_hddm.py）
    python holdout_subject_validation.py --mode fit-docker          # 或直接执行生成的 run_holdout_fits.ps1

    # ③ 汇总并出图（宿主机）
    python holdout_subject_validation.py --mode collect

产物
----
2_Data/Generate_Data/TenRules_Revision_20260912/holdout/
    split_assignment.csv            被试 → 估计集/验证集 的分配
    prepared/*.csv                  估计集数据（供 HDDM 拟合）
    fits/*_stats.csv                HDDM 拟合结果
    holdout_param_layer.csv         (A) 参数层留出结果
    holdout_behavior_ppc.csv        (B) 行为层留出结果（观测 vs 95% 预测区间）
    holdout_summary.csv             覆盖率汇总
3_Figures/Thesis_v3_20260912/F9-1_holdout_validation.png
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

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import (  # noqa: E402
    HDDM_READY_DIR, OUT_DATA_DIR, OUT_FIG_DIR, TRIALS_PER_IDENTITY,
    behavior_stats, build_trial_params, extract_params_from_stats,
    load_frozen_truth, load_subject_posterior, observed_condition_stats,
    setup_cjk_font, simulate_trials,
)

HOLDOUT = OUT_DATA_DIR / "holdout"
PREPARED = HOLDOUT / "prepared"
FITS = HOLDOUT / "fits"
JOBS = HOLDOUT / "jobs.json"
DEFAULT_IMAGE, DEFAULT_MOUNT = "hcp4715/hddm", \
    "D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work"
CONTAINER_WORK = "/home/jovyan/work"
PARAMS = ["v_self", "v_stranger", "a", "t", "z", "SPE_v"]
IDENTITY_STATS = ["acc_all", "omission_rate", "correct_rt_mean_ms", "correct_rt_q50_ms"]


# ------------------------------------------------------------------
# ① prepare：分层随机拆分 + 生成估计集数据
# ------------------------------------------------------------------
def prepare(holdout_frac: float, seed: int, groups: list[int]):
    HOLDOUT.mkdir(parents=True, exist_ok=True)
    PREPARED.mkdir(parents=True, exist_ok=True)
    FITS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    assign_rows, jobs = [], []

    for gid in groups:
        files = list(HDDM_READY_DIR.glob(f"hddm_data_group{gid}_*.csv"))
        if not files:
            print(f"  ⚠️ G{gid} 缺少数据，跳过")
            continue
        df = pd.read_csv(files[0])
        subjects = np.sort(df["subj_idx"].unique())
        perm = rng.permutation(subjects)
        n_hold = max(3, int(round(len(subjects) * holdout_frac)))
        hold, est = set(perm[:n_hold]), set(perm[n_hold:])
        for s in subjects:
            assign_rows.append({"group_id": gid, "subj_idx": int(s),
                                "role": "holdout" if s in hold else "estimate"})

        est_all = df[df["subj_idx"].isin(est)].copy()
        # Censor 口径（与主分析一致）：omission 行 rt=deadline、response=0、p_outlier=0
        tag = f"holdout_est_g{gid}"
        path = PREPARED / f"{tag}.csv"
        est_all.to_csv(path, index=False)
        jobs.append({
            "group_id": gid, "tag": tag, "scheme": "censor",
            "rel_path": f"TenRules_Revision_20260912/holdout/prepared/{tag}.csv",
            "p_outlier": 0.0, "n_subjects_est": len(est), "n_subjects_hold": len(hold),
            "n_trials": int(len(est_all)),
        })
        print(f"  G{gid}: 估计集 {len(est)} 人 / 验证集 {len(hold)} 人")

    pd.DataFrame(assign_rows).to_csv(HOLDOUT / "split_assignment.csv", index=False)
    JOBS.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

    cmds = ["# 自动生成：留出验证的估计集 HDDM 拟合"]
    for j in jobs:
        cmd = ["docker", "run", "--rm", "--cpus=4", "-v", DEFAULT_MOUNT, DEFAULT_IMAGE,
               "python", f"{CONTAINER_WORK}/1_Code/Python_for_Check/TenRules_Revision_20260912/fit_one_hddm.py",
               "--data", f"{CONTAINER_WORK}/2_Data/Generate_Data/{j['rel_path']}",
               "--out-dir", f"{CONTAINER_WORK}/2_Data/Generate_Data/TenRules_Revision_20260912/holdout/fits",
               "--tag", j["tag"], "--p-outlier", "0.0"]
        cmds.append("& " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    (HOLDOUT / "run_holdout_fits.ps1").write_text("\n".join(cmds), encoding="utf-8")
    print(f"[prepare] 作业 {len(jobs)} 个；拆分表 → {HOLDOUT / 'split_assignment.csv'}")


def fit_docker(dry_run: bool = False):
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    if dry_run:
        print((HOLDOUT / "run_holdout_fits.ps1").read_text(encoding="utf-8")[:1200])
        return
    if shutil.which("docker") is None:
        print("未找到 docker；请执行 run_holdout_fits.ps1")
        return
    for j in jobs:
        print(f"[fit] {j['tag']} ...", flush=True)
        subprocess.run(["docker", "run", "--rm", "--cpus=4", "-v", DEFAULT_MOUNT, DEFAULT_IMAGE,
                        "python", f"{CONTAINER_WORK}/1_Code/Python_for_Check/TenRules_Revision_20260912/fit_one_hddm.py",
                        "--data", f"{CONTAINER_WORK}/2_Data/Generate_Data/{j['rel_path']}",
                        "--out-dir", f"{CONTAINER_WORK}/2_Data/Generate_Data/TenRules_Revision_20260912/holdout/fits",
                        "--tag", j["tag"], "--p-outlier", "0.0"])
    print("[fit] 完成")


# ------------------------------------------------------------------
# ③ collect：(A) 参数层留出 + (B) 行为层留出
# ------------------------------------------------------------------
def collect(seed: int = 42, n_draws: int = 200):
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    assign = pd.read_csv(HOLDOUT / "split_assignment.csv")
    truth = load_frozen_truth().set_index("group_id")
    rng = np.random.default_rng(seed)

    param_rows, beh_rows, missing = [], [], 0
    for j in jobs:
        gid = j["group_id"]
        stats_path = FITS / f"{j['tag']}_stats.csv"
        if not stats_path.exists():
            missing += 1
            continue
        est = extract_params_from_stats(pd.read_csv(stats_path, index_col=0))

        # ---- (A) 参数层：估计集模型 vs 验证集实际 ----
        try:
            post = load_subject_posterior(gid, n_draws=n_draws, seed=seed + gid)
            truth_self = post["v_self"].mean()
            truth_stranger = post["v_stranger"].mean()
            truth_a = post["a"].mean()
            truth_t = post["t"].mean()
            truth_z = post["z"].mean()
        except Exception as exc:
            print(f"  ⚠️ G{gid} 验证集参照（迹线）不可用：{exc}")
            truth_self = truth_stranger = truth_a = truth_t = truth_z = np.nan

        ref = {"v_self": truth_self, "v_stranger": truth_stranger, "a": truth_a,
               "t": truth_t, "z": truth_z, "SPE_v": truth_self - truth_stranger}
        for p in PARAMS:
            if p not in est:
                continue
            param_rows.append({
                "group_id": gid, "param": p, "estimate_set": est[p]["mean"],
                "holdout_reference": ref[p], "bias": est[p]["mean"] - ref[p],
                "ci_lo": est[p]["lo"], "ci_hi": est[p]["hi"],
                "se": (est[p]["hi"] - est[p]["lo"]) / (2 * 1.96),
            })

        # ---- (B) 行为层：用估计集参数仿真，比较验证集行为 ----
        hold = assign[(assign.group_id == gid) & (assign.role == "holdout")]["subj_idx"].to_numpy()
        try:
            post = load_subject_posterior(gid, n_draws=n_draws, seed=seed + gid)
            # 观测参照：**仅验证集被试**（用与仿真完全相同的统计口径）
            obs_files = list(HDDM_READY_DIR.glob(f"hddm_data_group{gid}_*.csv"))
            raw = pd.read_csv(obs_files[0])
            raw_hold = raw[raw["subj_idx"].isin(hold)]
            obs = {"all": behavior_stats(raw_hold, rt_unit="sec")}
            for ident, nm in [(1, "self"), (0, "stranger")]:
                obs[nm] = behavior_stats(raw_hold[raw_hold["identity"] == ident], rt_unit="sec")
            pred = {name: [] for name in ["all", "self", "stranger"]}
            n_hold = max(len(hold), 3)
            for d in range(post["v_self"].shape[0]):
                idx = np.arange(min(n_hold, post["v_self"].shape[1]))
                tp = build_trial_params(post["v_self"][d][idx], post["v_stranger"][d][idx],
                                        post["a"][d][idx], post["t"][d][idx], post["z"][d][idx],
                                        TRIALS_PER_IDENTITY)
                deadline = float((truth.loc[gid, "T_ms"] + truth.loc[gid, "W_ms"]) / 1000.0)
                sim = simulate_trials(tp["v"], tp["a"], tp["t"], tp["z"], deadline, len(tp["v"]), rng)
                df = pd.DataFrame({"rt": sim["rt"], "response": sim["response"],
                                   "omission": sim["omission"], "identity": tp["identity"]})
                pred["all"].append(behavior_stats(df, rt_unit="sec"))
                for ident, nm in [(1, "self"), (0, "stranger")]:
                    pred[nm].append(behavior_stats(df[df.identity == ident], rt_unit="sec"))
            for name in ["all", "self", "stranger"]:
                for stat in IDENTITY_STATS:
                    vals = np.array([p[stat] for p in pred[name]], dtype=float)
                    observed = obs["all" if name == "all" else name][stat]
                    lo, hi = np.percentile(vals, [2.5, 97.5])
                    beh_rows.append({
                        "group_id": gid, "identity": name, "stat": stat, "observed_holdout": observed,
                        "pred_median": float(np.median(vals)), "pred_lo95": float(lo), "pred_hi95": float(hi),
                        "inside95": int(lo <= observed <= hi), "n_holdout_subjects": int(len(hold)),
                    })
        except Exception as exc:
            print(f"  ⚠️ G{gid} 行为层留出失败：{exc}")

    if missing:
        print(f"[collect] ⚠️ {missing} 个条件缺少估计集拟合结果（先跑 --mode fit-docker）")
    if not param_rows:
        print("[collect] 暂无可汇总结果")
        return
    pl = pd.DataFrame(param_rows); pl.to_csv(HOLDOUT / "holdout_param_layer.csv", index=False)
    bl = pd.DataFrame(beh_rows); bl.to_csv(HOLDOUT / "holdout_behavior_ppc.csv", index=False)

    summ = []
    for (p,), g in pl.groupby(["param"]):
        summ.append({"layer": "param", "stat": p, "n": len(g), "bias_mean": g.bias.mean(),
                     "rmse": float(np.sqrt((g.bias ** 2).mean())),
                     "r": g.estimate_set.corr(g.holdout_reference)})
    for (stat,), g in bl.groupby(["stat"]):
        summ.append({"layer": "behavior", "stat": stat, "n": len(g),
                     "coverage_95": g.inside95.mean(), "median_abs_dev": np.nan,
                     "r": np.nan})
    sm = pd.DataFrame(summ); sm.to_csv(HOLDOUT / "holdout_summary.csv", index=False)
    print("\n[collect] 留出验证汇总：")
    print(sm.round(3).to_string(index=False))
    print(f"[collect] 产物 → {HOLDOUT}")


def main():
    ap = argparse.ArgumentParser(description="留出被试验证（预测新被试）")
    ap.add_argument("--mode", required=True, choices=["prepare", "fit-docker", "collect"])
    ap.add_argument("--holdout-frac", type=float, default=0.33)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-draws", type=int, default=200)
    ap.add_argument("--groups", default="3,4,5,6,7,8", help="参与留出验证的主口径条件")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.mode == "prepare":
        prepare(args.holdout_frac, args.seed, [int(g) for g in args.groups.split(",") if g.strip()])
    elif args.mode == "fit-docker":
        fit_docker(args.dry_run)
    else:
        collect(args.seed, args.n_draws)


if __name__ == "__main__":
    main()
