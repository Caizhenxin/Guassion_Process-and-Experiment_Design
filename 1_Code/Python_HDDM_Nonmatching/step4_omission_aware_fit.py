# -*- coding: utf-8 -*-
"""阶段 1 · 步骤 4：三臂对比拟合（Drop / Censor / Omission-aware）

三臂**共用同一模型规格（M3）与同一采样设置**，只改"遗漏怎么进似然"：

| 臂 | 遗漏处理 |
|---|---|
| `drop` | 删掉遗漏行（现行常见做法，Leng et al. 证明有偏） |
| `censor` | 遗漏行写成 `rt = deadline`、`correct = 0`（项目现行做法；§4.2 已证是把遗漏
  伪造成"恰好在截止时刻犯了一个错"，只作对照） |
| `omission` | RT 似然只用作答试次 + 把遗漏作为**第三类反应**挂 `pm.Potential`（本方案） |

⚠️ 多链是**自己循环**的，不走 kabuki 的 `chains>1` 路径——那条路径会 `deepcopy` 后用
`nodes_db` 重建 MCMC，**把遗漏势函数丢掉**（见 `omission_potential.py` 文档第 4 条）。
自己循环还有个好处：三臂的链处理完全一致，`R̂` 可直接跨链算。

用法
====
  # 先做单组冒烟
  python step4_omission_aware_fit.py --arm all --groups 1 --draws 1500 --burn 500
  # 正式三臂（建议 2 链起步）
  python step4_omission_aware_fit.py --arm all --draws 4000 --burn 1000 --chains 2
"""
import argparse
import copy
import json
import pickle
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from omission_potential import attach_omission_potential, validate_wiring  # noqa: E402
from step2_hddm_fit import MODEL_SPECS, build_fit_frame, rhat_ess, rhat_manual  # noqa: E402

DATA_DIR = _THIS_DIR.parents[1] / "2_Data" / "Real_Data" / "HDDM_Ready_Nonmatching"
OUT_DIR = _THIS_DIR.parents[1] / "2_Data" / "Real_Data" / "HDDM_Traces_Nonmatching" / "omission_arms"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ARMS = ("drop", "censor", "omission")
MAIN_COLS = ["subj_idx", "rt", "response", "correct", "identity",
             "condition", "cell", "deadline", "omission"]


def load_group(gid):
    main_f = next(DATA_DIR.glob(f"hddm_data_group{gid}_*.csv"), None)
    omit_f = next(DATA_DIR.glob(f"hddm_omission_group{gid}_*.csv"), None)
    if main_f is None or omit_f is None:
        raise SystemExit(f"未找到 group{gid} 的数据：{DATA_DIR}")
    return pd.read_csv(main_f), pd.read_csv(omit_f)


def prepare_arm(data, omit, arm):
    """返回 (交给 HDDM 的 DataFrame, 遗漏 DataFrame 或 None, deadline)。"""
    deadline = float(data["deadline"].iloc[0])
    if arm == "drop":
        return data, None, deadline
    if arm == "censor":
        cens = omit.reindex(columns=MAIN_COLS).copy()
        cens["rt"] = deadline          # 伪造成"恰好在截止时刻反应"
        cens["response"] = 0
        cens["correct"] = 0            # 且固定落在"错误"一侧（§4.2 的已知缺陷）
        cens["omission"] = 0
        return pd.concat([data, cens], ignore_index=True), None, deadline
    if arm == "omission":
        return data, omit, deadline
    raise ValueError(arm)


def fit_arm(gid, arm, spec_name, draws, burn, chains, seed, verbose=True):
    """跑一个臂 × 一个组 × N 链（自己循环），返回统计与派生量。"""
    import hddm

    data, omit = load_group(gid)
    df_in, omit_in, deadline = prepare_arm(data, omit, arm)
    spec = MODEL_SPECS[spec_name]
    frame = build_fit_frame(df_in, spec)

    print(f"\n{'=' * 70}")
    print(f"[{arm}] group {gid} | 规格 {spec_name} | "
          f"试次 {len(frame)} | deadline {deadline:.3f}s | {chains} 链 × {draws} draws")
    print(f"{'=' * 70}")

    per_chain, info = {}, None
    for c in range(chains):
        np.random.seed(seed + c)
        model = hddm.HDDM(frame,
                          depends_on=copy.deepcopy(spec["depends_on"]),
                          include=["v", "a", "t", "z"], bias=False, p_outlier=0.0)
        if arm == "omission":
            info = attach_omission_potential(model, omit_in, deadline, verbose=(c == 0))
            if c == 0 and verbose:
                ok, _ = validate_wiring(model, omit_in, info, deadline)
                if not ok:
                    raise RuntimeError("遗漏势函数接线自检未通过，停止拟合")
        t_start = time.time()
        model.sample(draws, burn=burn)
        print(f"  链 {c + 1}/{chains} 完成，用时 {time.time() - t_start:.1f}s"
              + (f" | 势函数 logp = {info['potential'].logp:.2f}" if arm == "omission" else ""))
        for k, v in model.get_traces().items():
            try:
                arr = np.asarray(v, dtype=float).ravel()
            except (TypeError, ValueError):
                continue
            per_chain.setdefault(k, []).append(arr)

    traces = {k: np.stack(vs) for k, vs in per_chain.items()
              if len(vs) == chains and len({v.size for v in vs}) == 1}
    ntrace = next(iter(traces.values())).shape[1] if traces else 0

    # 收敛诊断（单链时 R̂ 不可定义，跳过）
    conv_rows = []
    if chains >= 2:
        for k, arr in traces.items():
            r, e, how = rhat_ess(arr)
            conv_rows.append({"param": k, "rhat": r, "rhat_manual": rhat_manual(arr),
                              "ess": e, "ess_method": how})
    else:
        print("  ⚠️ 单链运行：R̂ 不可定义，跳过收敛诊断（要 R̂ 请加 --chains N，N≥2）")
    conv = pd.DataFrame(conv_rows)
    stem = f"{arm}_{spec_name}_{gid}"
    if not conv.empty:
        conv["rhat_absdiff"] = (conv["rhat"] - conv["rhat_manual"]).abs()
        conv.to_csv(OUT_DIR / f"{stem}_conv.csv", index=False)
        r_all = conv["rhat"].to_numpy(float)
        r_nan = int(np.sum(~np.isfinite(r_all)))
        r_gt = int(np.nansum(r_all > 1.05))
    else:
        r_nan = r_gt = 0

    # 后验汇总（跨链合并）
    stat = {}
    for k, arr in traces.items():
        x = arr.ravel()
        x = x[np.isfinite(x)]
        if x.size:
            stat[k] = {"mean": float(x.mean()), "std": float(x.std()),
                       "lo": float(np.percentile(x, 2.5)), "hi": float(np.percentile(x, 97.5))}
    (OUT_DIR / f"{stem}_stats.json").write_text(
        json.dumps(stat, ensure_ascii=False, indent=2), encoding="utf-8")
    if traces:
        np.savez_compressed(OUT_DIR / f"{stem}_traces.npz", **traces)

    return {"arm": arm, "group_id": gid, "model": spec_name, "stem": stem,
            "draws": draws, "burn": burn, "chains": chains, "n_trials": int(len(frame)),
            "n_omission": int(len(omit_in)) if omit_in is not None else 0,
            "deadline": deadline, "rhat_max": stat_max_rhat(conv), "n_rhat_gt_1.05": r_gt,
            "n_rhat_nan": r_nan, "n_params": int(len(stat)),
            "omission_cells": info["n_cells_in_likelihood"] if info else 0,
            "logp_omission_final": (float(info["potential"].logp) if info else None)}


def stat_max_rhat(conv):
    if conv is None or conv.empty:
        return None
    r = conv["rhat"].to_numpy(dtype=float)
    r = r[np.isfinite(r)]
    return float(r.max()) if r.size else None


def main():
    ap = argparse.ArgumentParser(description="阶段 1 三臂对比（Drop / Censor / Omission-aware）")
    ap.add_argument("--arm", default="all", choices=list(ARMS) + ["all"])
    ap.add_argument("--model", default="M3", choices=list(MODEL_SPECS))
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--burn", type=int, default=1000)
    ap.add_argument("--chains", type=int, default=1)
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--groups", default="", help="逗号分隔；默认全部")
    ap.add_argument("--manifest", default="arms_manifest.json",
                    help="清单文件名；多进程分批跑时各写各的分片，避免并发覆盖")
    args = ap.parse_args()

    csv_files = sorted(DATA_DIR.glob("hddm_data_group*.csv"))
    gids = [int(p.stem.split("group")[1].split("_")[0]) for p in csv_files]
    want = [g.strip() for g in args.groups.split(",") if g.strip()]
    if want:
        gids = [g for g in gids if str(g) in want]
    if not gids:
        raise SystemExit("没有可跑的组")

    arms = list(ARMS) if args.arm == "all" else [args.arm]
    runs = []
    for arm in arms:
        for gid in gids:
            runs.append(fit_arm(gid, arm, args.model, args.draws, args.burn,
                                args.chains, args.seed))

    reg = OUT_DIR / args.manifest
    prev = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else []
    keys = {(r["arm"], r["group_id"], r["model"]) for r in runs}
    prev = [r for r in prev if (r["arm"], r["group_id"], r["model"]) not in keys]
    reg.write_text(json.dumps(prev + runs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n清单 -> {reg}")


if __name__ == "__main__":
    main()
