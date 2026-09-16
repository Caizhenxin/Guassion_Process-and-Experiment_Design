# -*- coding: utf-8 -*-
"""
fit_one_hddm.py —— 在 Docker 容器（镜像 hcp4715/hddm）内拟合单个数据集
====================================================================
供 param_recovery_frozen6.py 的 prepare 模式生成的作业调用；也可单独使用。

用法（容器内）::

    python fit_one_hddm.py --data /home/jovyan/work/.../sim_cond5_rep1_censor.csv \
                           --out-dir /home/jovyan/work/.../fits/censor \
                           --tag sim_cond5_rep1_censor --p-outlier 0.0

用法（Windows 宿主机，通过 Docker）::

    docker run --rm --cpus=4 ^
      -v "D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design:/home/jovyan/work" ^
      hcp4715/hddm python /home/jovyan/work/1_Code/Python_for_Check/TenRules_Revision_20260912/fit_one_hddm.py ^
      --data /home/jovyan/work/... --out-dir /home/jovyan/work/... --tag ... --p-outlier 0.0

模型设定与项目一致（见 1_Code/Python_for_Check/Omission/run_censor_fit.py）：
    depends_on = {"v": "identity"}, include = ["v", "a", "t", "z"], bias = False
    MCMC: 3000 draws / 500 burn-in（可用 --draws/--burn 调整）

⚠️ p_outlier 口径说明
    项目 notebook（产出论文结果的那次）用的是 Censor: p_outlier = 0.0、Drop: p_outlier = 0.05；
    而仓库脚本 run_censor_fit.py 写的是 0.05（已知不一致）。本脚本默认 **Censor=0.0 / Drop=0.05**，
    但显式暴露 --p-outlier，便于复现与敏感性检查，并在 meta.json 中记录实际取值。
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="HDDM 输入 CSV（列：subj_idx, rt, response, identity[, omission]）")
    ap.add_argument("--out-dir", required=True, help="结果输出目录（容器内路径）")
    ap.add_argument("--tag", required=True, help="输出文件前缀")
    ap.add_argument("--p-outlier", type=float, default=None,
                    help="outlier 概率；缺省时按文件名推断：含 censor → 0.0，含 drop → 0.05")
    ap.add_argument("--draws", type=int, default=3000)
    ap.add_argument("--burn", type=int, default=500)
    ap.add_argument("--save-traces", action="store_true", default=True)
    args = ap.parse_args()

    data_path = Path(args.data)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.p_outlier is None:
        p_outlier = 0.0 if "censor" in data_path.stem else 0.05
    else:
        p_outlier = float(args.p_outlier)

    df = pd.read_csv(data_path)
    n_subj = int(df["subj_idx"].nunique())
    n_trials = int(len(df))
    n_omission = int(df["omission"].sum()) if "omission" in df.columns else 0
    omission_rate = n_omission / n_trials if n_trials else float("nan")

    print(f"[fit_one_hddm] {args.tag}: {n_subj} 被试 / {n_trials} 试次 / omission={omission_rate:.3f} / p_outlier={p_outlier}")

    import hddm  # 只应在容器内可用
    try:
        # 与项目既有脚本一致：把 z 的默认起点设为 0.5
        # （不同 hddm 版本的 API 可能不同，失败不致命，仅提示）
        hddm.model_config.model_config["z"]["default"] = 0.5
    except Exception as exc:  # pragma: no cover
        print(f"[fit_one_hddm] 设置 z 默认值失败（忽略）：{exc}")

    model = hddm.HDDM(
        df,
        depends_on={"v": "identity"},
        include=["v", "a", "t", "z"],
        bias=False,
        p_outlier=p_outlier,
    )

    t0 = time.time()
    db_name = out_dir / f"_tmp_{args.tag}.db"
    model.sample(args.draws, burn=args.burn, dbname=str(db_name), db="pickle")
    elapsed = time.time() - t0

    stats = model.gen_stats()
    stats.to_csv(out_dir / f"{args.tag}_stats.csv")

    traces_saved = False
    if args.save_traces:
        try:
            raw = model.get_traces()
            simple = {}
            for k, v in raw.items():
                try:
                    arr = np.asarray(v, dtype=float).flatten()
                    if arr.size:
                        simple[k] = arr
                except Exception:
                    continue
            if simple:
                np.savez_compressed(out_dir / f"{args.tag}_traces.npz", **simple)
                traces_saved = True
        except Exception as exc:  # pragma: no cover
            print(f"[fit_one_hddm] 迹线保存失败：{exc}")

    meta = {
        "tag": args.tag,
        "data": str(data_path),
        "n_subjects": n_subj,
        "n_trials": n_trials,
        "n_omission": n_omission,
        "omission_rate": omission_rate,
        "p_outlier": p_outlier,
        "draws": args.draws,
        "burn": args.burn,
        "elapsed_sec": round(elapsed, 1),
        "traces_saved": traces_saved,
        "stats_file": f"{args.tag}_stats.csv",
    }
    (out_dir / f"{args.tag}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        if db_name.exists():
            os.remove(db_name)
    except Exception:
        pass

    print(f"[fit_one_hddm] 完成 {args.tag}（{elapsed/60:.1f} 分钟）→ {out_dir}")


if __name__ == "__main__":
    main()
