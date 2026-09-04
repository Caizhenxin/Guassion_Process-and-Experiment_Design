# -*- coding: utf-8 -*-
"""
HDDM 规范 4 链重拟合（G3–G8，Censor 基线）— 2026-09-02
=====================================================
背景：旧单链拟合（HDDM_Traces）在 G4/G6/G8 等条件出现模式不稳定（v/a 绝对水平与
SPE 相关结论受影响），需以多链拟合作为论文规范参数来源。
本脚本（容器内运行）：
1) G3–G8 每组 hddm.HDDM(..., depends_on={'v':'identity'}, include=['v','a','t','z'],
   bias=False, p_outlier=0.05)，4 链 MCMC；
2) 保存每组完整 arviz 摘要 → 2_Data/Generate_Data/HDDM_Diagnostics/G{g}_full_diag.csv；
3) 生成被试级 stats 文件（v_subj(0/1).N 后验均值）→ 2_Data/Real_Data/HDDM_Traces_4chain/
   （格式与旧 *_stats.csv 兼容，供 BF/ANOVA 冻结脚本复算 S03–S05）；
4) 汇总组级规范参数表 all_G3_G8_4chain_group.csv 与 被试级 SPE_v 表 subject_spe_4chain.csv。
运行：python /home/jovyan/work/1_Code/Python_HDDM/fit_canonical_4chain_20260902.py [组号...] [--draws N --burn N]
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
DIAG_DIR = os.path.join(ROOT, "2_Data", "Generate_Data", "HDDM_Diagnostics")
STATS_DIR = os.path.join(ROOT, "2_Data", "Real_Data", "HDDM_Traces_4chain")
os.makedirs(DIAG_DIR, exist_ok=True)
os.makedirs(STATS_DIR, exist_ok=True)

GROUPS = [int(x) for x in sys.argv[1:] if x.isdigit()] or [3, 4, 5, 6, 7, 8]
DRAWS = int(sys.argv[sys.argv.index("--draws") + 1]) if "--draws" in sys.argv else 3000
BURN = int(sys.argv[sys.argv.index("--burn") + 1]) if "--burn" in sys.argv else 500
CHAINS = 4

DESIGN = {3: (120, 30, 600), 4: (120, 80, 600), 5: (8, 100, 1100),
          6: (120, 500, 1500), 7: (120, 30, 800), 8: (120, 80, 800)}

import hddm
import arviz as az


def parse_subject_var(param):
    """接受 arviz 中两种可能命名，返回 (identity, subj_id) 或 None。"""
    m = re.match(r"^v\((\d)\)_subj\.(\d+)$", param) or re.match(r"^v_subj\((\d)\)\.(\d+)$", param)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def main():
    files = sorted(os.listdir(DATA_DIR))
    group_rows, subj_rows = [], []
    for g in GROUPS:
        cand = [f for f in files if f.startswith("hddm_data_group%d_" % g) and f.endswith(".csv")]
        if not cand:
            print("[%d] 无数据文件，跳过" % g, flush=True)
            continue
        fp = os.path.join(DATA_DIR, cand[0])
        df = pd.read_csv(fp)
        print("[G%d] 开始拟合 %s（被试 %d，试次 %d，遗漏 %.1f%%）"
              % (g, cand[0], df["subj_idx"].nunique(), len(df),
                 100 * df["omission"].mean()), flush=True)
        model = hddm.HDDM(df, depends_on={"v": "identity"},
                          include=["v", "a", "t", "z"], bias=False, p_outlier=0.05)
        t0 = time.time()
        inf = model.sample(DRAWS, burn=BURN, chains=CHAINS,
                           return_infdata=True, progress_bar=False)
        print("[G%d] 采样完成，%.1f 分钟" % (g, (time.time() - t0) / 60), flush=True)

        summ = az.summary(inf.posterior).reset_index().rename(columns={"index": "param"})
        summ.to_csv(os.path.join(DIAG_DIR, "G%d_full_diag.csv" % g), index=False)

        def val(p):
            r = summ[summ["param"] == p]
            return float(r["mean"].iloc[0]) if len(r) else np.nan

        group_rows.append({"group_id": g, "P": DESIGN[g][0], "T_ms": DESIGN[g][1],
                           "W_ms": DESIGN[g][2],
                           "v_stranger_mean": val("v(0)"), "v_self_mean": val("v(1)"),
                           "a_mean": val("a"), "t_mean": val("t"), "z_mean": val("z"),
                           "SPE_v": val("v(1)") - val("v(0)")})

        # 被试级 SPE_v：匹配 v(0)_subj.N / v(1)_subj.N
        sub_map0, sub_map1 = {}, {}
        for p in summ["param"].astype(str):
            got = parse_subject_var(p)
            if not got:
                continue
            ident, sid = got
            meanv = float(summ.loc[summ["param"] == p, "mean"].iloc[0])
            (sub_map0 if ident == 0 else sub_map1)[sid] = meanv
        stats_rows = []
        for sid in sorted(set(sub_map0) & set(sub_map1)):
            spe = sub_map1[sid] - sub_map0[sid]
            subj_rows.append({"group_id": g, "subject": sid, "SPE_v": spe,
                              "v_stranger": sub_map0[sid], "v_self": sub_map1[sid]})
            stats_rows.append({"param": "v_subj(0).%d" % sid, "mean": sub_map0[sid]})
            stats_rows.append({"param": "v_subj(1).%d" % sid, "mean": sub_map1[sid]})
        pd.DataFrame(stats_rows).to_csv(
            os.path.join(STATS_DIR, "hddm_data_group%d_P%d_T%d_W%d_stats.csv"
                         % (g, DESIGN[g][0], DESIGN[g][1], DESIGN[g][2])),
            index=False, encoding="utf-8")
        print("[G%d] 被试级 %d 人 → stats 已写入 HDDM_Traces_4chain"
              % (g, len(stats_rows) // 2), flush=True)

    pd.DataFrame(group_rows).to_csv(os.path.join(DIAG_DIR, "all_G3_G8_4chain_group.csv"),
                                    index=False, encoding="utf-8")
    pd.DataFrame(subj_rows).to_csv(os.path.join(DIAG_DIR, "subject_spe_4chain.csv"),
                                   index=False, encoding="utf-8")
    print("组级表:", os.path.join(DIAG_DIR, "all_G3_G8_4chain_group.csv"), flush=True)
    print("被试级表:", os.path.join(DIAG_DIR, "subject_spe_4chain.csv"), flush=True)
    print("完成", flush=True)


if __name__ == "__main__":
    main()
