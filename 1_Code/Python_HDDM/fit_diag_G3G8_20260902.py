# -*- coding: utf-8 -*-
"""
HDDM 收敛诊断重拟合（G3–G8，Censor 基线，4 链）— 2026-09-02
=============================================================
用途：为冻结口径（G3–G8）主拟合补齐 R-hat / ESS 收敛诊断。
- 模型配置与既有主拟合 step2_hddm_fit.py 一致：HDDM(df, depends_on={'v':'identity'},
  include=['v','a','t','z'], bias=False, p_outlier=0.05)，输入为 HDDM_Ready/*_censor 编码 CSV。
- 采样：draws=2000, burn=500, chains=4（并行），return_infdata=True。
- 输出：每组 group 层节点（不含 *_subj.*）的 arviz 摘要（mean/sd/r_hat/ess_bulk/ess_tail）csv，
  及汇总表 all_G3_G8_diag_summary.csv → 2_Data/Generate_Data/HDDM_Diagnostics/。
在容器内运行：python /home/jovyan/work/1_Code/Python_HDDM/fit_diag_G3G8_20260902.py
"""
import os
import re
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = "/home/jovyan/work"
DATA_DIR = os.path.join(ROOT, "2_Data", "Real_Data", "HDDM_Ready")
OUT_DIR = os.path.join(ROOT, "2_Data", "Generate_Data", "HDDM_Diagnostics")
os.makedirs(OUT_DIR, exist_ok=True)

GROUPS = [int(x) for x in sys.argv[1:] if x.isdigit()] or [3, 4, 5, 6, 7, 8]
DRAWS = int(sys.argv[sys.argv.index("--draws") + 1]) if "--draws" in sys.argv else 2000
BURN = int(sys.argv[sys.argv.index("--burn") + 1]) if "--burn" in sys.argv else 500
CHAINS = 4

import hddm
import arviz as az


def pick_rhat_col(summ):
    for cand in ["r_hat", "rhat"]:
        if cand in summ.columns:
            return cand
    return None


def main():
    files = sorted(os.listdir(DATA_DIR))
    parts = []
    for g in GROUPS:
        cand = [f for f in files
                if f.startswith("hddm_data_group%d_" % g) and f.endswith(".csv")]
        if not cand:
            print("[%d] 未找到数据文件，跳过" % g, flush=True)
            continue
        fp = os.path.join(DATA_DIR, cand[0])
        df = pd.read_csv(fp)
        n_subj = int(df["subj_idx"].nunique())
        n_tri = int(len(df))
        n_om = int(df["omission"].sum())
        print("[G%d] %s | 被试 %d 试次 %d 遗漏 %d (%.1f%%)"
              % (g, cand[0], n_subj, n_tri, n_om, 100 * n_om / max(n_tri, 1)), flush=True)

        model = hddm.HDDM(df, depends_on={"v": "identity"},
                          include=["v", "a", "t", "z"], bias=False, p_outlier=0.05)
        t0 = time.time()
        inf = model.sample(DRAWS, burn=BURN, chains=CHAINS,
                           return_infdata=True, progress_bar=False)
        mins = (time.time() - t0) / 60.0
        print("[G%d] 采样完成，耗时 %.1f 分钟" % (g, mins), flush=True)

        summ = az.summary(inf.posterior)
        summ = summ.reset_index().rename(columns={"index": "param"})
        # 只保留 group 层节点（剔除 *_subj.* 个体节点）
        core = summ[~summ["param"].astype(str).str.contains("subj")]
        keep_cols = ["param", "mean", "sd"]
        rc = pick_rhat_col(core)
        if rc:
            keep_cols.append(rc)
        for ess in ["ess_bulk", "ess_tail"]:
            if ess in core.columns:
                keep_cols.append(ess)
        core = core[keep_cols]
        core.insert(0, "group", g)
        print(core.to_string(index=False), flush=True)
        core.to_csv(os.path.join(OUT_DIR, "G%d_diag.csv" % g), index=False)
        parts.append(core)

    if parts:
        comb = pd.concat(parts, ignore_index=True)
        comb.to_csv(os.path.join(OUT_DIR, "all_G3_G8_diag_summary.csv"), index=False)
        print("汇总已保存: %s" % os.path.join(OUT_DIR, "all_G3_G8_diag_summary.csv"), flush=True)
    print("全部完成", flush=True)


if __name__ == "__main__":
    main()
