# -*- coding: utf-8 -*-
"""
fit_one_hddm_chains.py —— 容器内多链 HDDM 拟合（2026-09-13）
==========================================================
与 fit_one_hddm.py 的区别：使用 HDDM 原生的多链抽样（chains=N、parallel=True），
从而可以计算**严格的多链 R-hat / ESS**（此前历史拟合为单链，只能用 Split-R̂ 近似）。

用法（容器内，由 refit_main_fits.py 生成命令）::

    python fit_one_hddm_chains.py --data ... --out-dir ... --tag g5_refit \
        --p-outlier 0.0 --draws 8000 --burn 2000 --chains 4 --seed 42

产物
----
    <tag>_stats.csv        gen_stats()（群体层参数均值与 95% CI）
    <tag>_chains.npz       多链后验：每个参数保存为 shape (chains, draws)
    <tag>_meta.json        运行配置（draws/burn/chains/seed/p_outlier/耗时）
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--p-outlier", type=float, default=0.0)
    ap.add_argument("--draws", type=int, default=8000)
    ap.add_argument("--burn", type=int, default=2000)
    ap.add_argument("--chains", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    data_path = Path(args.data)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    print(f"[chains] {args.tag}: {df['subj_idx'].nunique()} 被试 / {len(df)} 试次 / "
          f"chains={args.chains} draws={args.draws} burn={args.burn} p_outlier={args.p_outlier}", flush=True)

    np.random.seed(args.seed)
    import hddm
    try:
        hddm.model_config.model_config["z"]["default"] = 0.5
    except Exception as exc:
        print(f"[chains] 设置 z 默认值失败（忽略）：{exc}", flush=True)

    model = hddm.HDDM(df, depends_on={"v": "identity"}, include=["v", "a", "t", "z"],
                      bias=False, p_outlier=args.p_outlier)

    t0 = time.time()
    idata = None
    try:
        idata = model.sample(args.draws, burn=args.burn, chains=args.chains,
                             parallel=True, return_infdata=True)
    except TypeError as exc:
        print(f"[chains] return_infdata 不受支持，退回普通抽样：{exc}", flush=True)
        model.sample(args.draws, burn=args.burn, chains=args.chains, parallel=True)
    elapsed = time.time() - t0

    stats = model.gen_stats()
    stats.to_csv(out_dir / f"{args.tag}_stats.csv")

    saved, note = {}, ""
    try:
        post = idata.posterior  # xarray.Dataset: dims (chain, draw, ...)
        for name in post.data_vars:
            arr = np.asarray(post[name].values, dtype=float)
            if arr.ndim == 2:                      # (chain, draw)
                saved[str(name)] = arr
            elif arr.ndim >= 3:                    # (chain, draw, extra...) → 取均值降维
                saved[str(name)] = arr.reshape(arr.shape[0], arr.shape[1], -1).mean(axis=2)
        note = "idiata.posterior"
    except Exception as exc:
        note = f"infdata 解析失败（{exc}）→ 使用 get_traces（拼接链）"
        try:
            tr = model.get_traces()
            for k, v in tr.items():
                arr = np.asarray(v, dtype=float).ravel()
                if arr.size:
                    saved[str(k)] = arr
        except Exception as exc2:
            note += f"；get_traces 亦失败（{exc2}）"

    if saved:
        np.savez_compressed(out_dir / f"{args.tag}_chains.npz", **saved)

    meta = {"tag": args.tag, "data": str(data_path), "n_subjects": int(df["subj_idx"].nunique()),
            "n_trials": int(len(df)), "p_outlier": args.p_outlier, "draws": args.draws,
            "burn": args.burn, "chains": args.chains, "seed": args.seed,
            "elapsed_sec": round(elapsed, 1),
            "arrays": {k: list(np.shape(v)) for k, v in saved.items()}, "source": note}
    (out_dir / f"{args.tag}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
    print(f"[chains] 完成 {args.tag}（{elapsed/60:.1f} 分钟；迹线 {note}）", flush=True)


if __name__ == "__main__":
    main()
