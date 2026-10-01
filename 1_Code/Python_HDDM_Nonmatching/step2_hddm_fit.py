# -*- coding: utf-8 -*-
"""Step 2: Docker 内 HDDM 拟合（NonMatching 全试次）

2026-09-30 修订
==============
【修复】旧设定 `depends_on={"v": "identity"}` 让**匹配与不匹配共用同一个 v**，
  其硬性推论是 `P(正确|匹配) + P(正确|不匹配) ≡ 1`；
  实测（87 人）为 **1.458**（self 1.516 / stranger 1.395），偏离 0.46。
  → 该设定在数学上无法产生这份数据，必须让 v 的漂移方向随刺激正确性变化。

现在提供 4 个模型规格（`--model`），构成逐步放开的消融阶梯：

  M0  按键编码 + 单 v（identity）                      ← 旧设定，仅用于复现被否证的结果
  M1  按键编码 + 四格漂移（v 依 cell = identity×condition）
  M2  正确性编码 + 共享 |v|（identity）+ 起点按 condition
  M3  正确性编码 + 共享 |v|（identity）+ 起点按 cell    ← 默认主模型

为什么 M2/M3 是正确的
====================
* `response` 改为**正确性编码**（1 = 作对）：上界 = "正确"边界，
  于是 `v` 是"朝正确方向积累证据的速率"，漂移方向随刺激自动翻转，
  两个正确率不再互补，可以同时很高（1.458 才能被解释）。
* `z` 仍按**按键**编码：在"正确界"坐标下，一份恒定的匹配键偏向 b 表现为
     匹配试次   z = 0.5 + b
     不匹配试次 z = 0.5 − b
  因此 `z ~ condition` 即可估计它，`b = (z_匹配 − z_不匹配) / 2`；
  再让 z 依 `cell` 变化，就得到自我国/陌生人的偏向差 Δb —— 本项目的核心待检量。

参数解读（在 step3 中自动计算）
============================
  Δv = v(self) − v(stranger)                       ← 证据优势成分
  b_i = (z(匹配,i) − z(不匹配,i)) / 2               ← 身份 i 的匹配键偏向
  Δb = b_self − b_stranger                         ← 偏向成分（SPE 的第二条通道）

多链与收敛诊断（2026-10-01 新增）
==============================
* `--chains N`（N>1）：走 HDDM 的多链路径，`kabuki` 内部用 joblib 并行跑 N 条链
  （`n_jobs = min(cpu_count, chains)`）。留存样本数 = `draws − burn`（pymc2 语义）。
  ⚠️ HDDM 的多链实现（`kabuki.utils.concat_models`）是**按链序把 trace 拼进 `_trace[0]`**：
  chain0 的全部 draw，接着 chain1 …，因此扁平迹线可以 `reshape(chains, ntrace)` 还原逐链样本。
  这两个数写进 `model_spec.json`（`chains` / `ntrace_per_chain`），step3 可直接还原。
* 拟合后自动算 **R̂（Gelman–Rubin）** 与 **ESS**，逐参数写入 `<stem>_conv.csv`，
  并把核心参数的 R̂ 最大值、超标个数、NaN 个数记入 `model_spec.json`。
* ⚠️ `kabuki.sample` 在多链分支里把单链异常**吞掉**（`except Exception: return None`），
  会让链数悄悄变少。因此这里显式比对 `model.chains` 与请求链数，不一致直接报错。
* ⚠️ 若某参数 R̂ 为 NaN（常量链/长度异常），**不得**视为通过；会把 NaN 个数单独报出来。

用法（在 Docker 容器内）
======================
  %run /home/jovyan/work/1_Code/Python_HDDM_Nonmatching/step2_hddm_fit.py --model M3
  # 复现旧设定：        ... step2_hddm_fit.py --model M0
  # 一次跑全部阶梯：    ... step2_hddm_fit.py --model all
  # 4 链 + 收敛诊断：   ... step2_hddm_fit.py --model M3 --chains 4 --draws 8000 --burn 2000
  # 冒烟测试单组：      ... step2_hddm_fit.py --model M3 --groups 3 --draws 300 --burn 100
"""
import argparse
import copy
import json
import pickle
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Ready_Nonmatching"
OUT_DIR = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Traces_Nonmatching"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# 模型规格阶梯
# ------------------------------------------------------------------
MODEL_SPECS = {
    "M0": {
        "desc": "按键编码 + 单 v（旧设定，与数据不相容，仅复现）",
        "response": "key",
        "depends_on": {"v": "identity"},
    },
    "M1": {
        "desc": "按键编码 + 四格漂移 v(cell)",
        "response": "key",
        "depends_on": {"v": "cell"},
    },
    "M2": {
        "desc": "正确性编码 + v(identity) + z(condition)",
        "response": "correct",
        "depends_on": {"v": "identity", "z": "condition"},
    },
    "M3": {
        "desc": "正确性编码 + v(identity) + z(cell) —— 主模型",
        "response": "correct",
        "depends_on": {"v": "identity", "z": "cell"},
    },
}

# 与论文主口径（配置 C）保持一致：不引入额外污染项
P_OUTLIER = 0.0

# 收敛诊断里"核心参数"的匹配式（群体层面参数，而不是逐被试的 _subj 分量）
CORE_PARAM_RE = re.compile(r"^(v\(\d+\)|a|t|z|z_trans|(a|t|v|z|sv|sz)_std)$")
RHAT_MAX_OK = 1.05


def single(v):
    """把 depends_on 的值统一成单个列名。

    ⚠️ HDDM 会**就地改写**传入的 `depends_on` dict（把 `'identity'` 规范化成 `['identity']`）。
    因此从 `model_spec.json` 读回来、或被 HDDM 碰过的 spec，其值可能是列表。
    """
    if isinstance(v, (list, tuple)):
        return v[0] if len(v) == 1 else tuple(v)
    return v


# ------------------------------------------------------------------
# 收敛诊断
# ------------------------------------------------------------------
def split_chains(flat: np.ndarray, chains: int, ntrace: int) -> np.ndarray:
    """把 HDDM 拼接后的扁平迹线还原成 (chains, ntrace)。

    `kabuki.utils.concat_models` 把 N 条链**按链序**依次拼进 `_trace[0]`：
    先是 chain0 的 ntrace 个 draw，再 chain1……（与 `gen_draw_index` 的 chain-major 一致）。
    """
    if flat.size != chains * ntrace:
        raise ValueError(f"迹线长度 {flat.size} != chains×ntrace = {chains}×{ntrace}")
    return flat.reshape(chains, ntrace)


def rhat_manual(chain_draws: np.ndarray) -> float:
    """手写 Gelman–Rubin R̂（用于交叉校验 arviz；链数 < 2 或链内方差为 0 时返回 nan）。"""
    m, n = chain_draws.shape
    if m < 2 or n < 2:
        return float("nan")
    w = chain_draws.var(axis=1, ddof=1).mean()        # 链内方差均值
    b = chain_draws.mean(axis=1).var(ddof=1) * n      # 链间方差（乘 n）
    if not np.isfinite(w) or w <= 0:
        return float("nan")
    return float(np.sqrt(((n - 1) / n * w + b / n) / w))


def rhat_ess(chain_draws: np.ndarray):
    """算 (R̂, ESS, 方法标签)。

    优先 arviz：`convert_to_dataset` 后取 **rank-normalized split-R̂** 与 ESS（现代标准）。
    ⚠️ arviz 不接受裸多维 ndarray（`TypeError: Only uni-dimensional ndarray variables are
    supported`），必须先 `convert_to_dataset`——2026-10-01 踩过，静默退回了朴素 ESS。
    arviz 不可用时退回手写 Gelman–Rubin R̂ + 忽略自相关的朴素 ESS，并**在标签里注明**，
    以免把高估的 ESS 当成真值。
    """
    if chain_draws.shape[0] < 2:
        # 单链：R̂ 不可定义；直接返回 nan，避免 arviz 反复抛 shape 警告刷屏
        return float("nan"), float(chain_draws.size), "single-chain(无 R̂)"
    try:
        import arviz as az
        ds = az.convert_to_dataset(chain_draws)
        r = float(np.asarray(az.rhat(ds)["x"].values))
        e = float(np.asarray(az.ess(ds)["x"].values))
        if np.isfinite(r) and np.isfinite(e):
            return r, e, "arviz(rank-split R̂)"
    except Exception:
        pass
    return rhat_manual(chain_draws), float(chain_draws.size), "manual GB + naive ESS"


def convergence_report(traces: dict, chains: int, ntrace: int, stem: str) -> dict:
    """逐参数算 R̂ / ESS，写 `<stem>_conv.csv`，打印摘要并返回摘要 dict。"""
    rows = []
    for key, val in traces.items():
        arr = np.asarray(val, dtype=float).ravel()
        if arr.size != chains * ntrace:
            continue
        cd = split_chains(arr, chains, ntrace)
        r, e, how = rhat_ess(cd)
        rows.append({"param": key, "rhat": r, "rhat_manual": rhat_manual(cd),
                     "ess": e, "ess_method": how})

    tab = pd.DataFrame(rows)
    # 自检列：arviz 的 rank-split R̂ 与手写 GB R̂ 应当接近
    tab["rhat_absdiff"] = (tab["rhat"] - tab["rhat_manual"]).abs()
    tab.to_csv(OUT_DIR / f"{stem}_conv.csv", index=False)

    is_core = tab["param"].astype(str).str.match(CORE_PARAM_RE)
    core = tab[is_core] if is_core.any() else tab
    r_all = tab["rhat"].to_numpy(dtype=float)
    r_core = core["rhat"].to_numpy(dtype=float)
    ess_core = core["ess"].to_numpy(dtype=float)

    n_thr = int(np.nansum(r_all > RHAT_MAX_OK))
    n_nan = int(np.sum(~np.isfinite(r_all)))
    r_max_core = float(np.nanmax(r_core)) if np.isfinite(r_core).any() else float("nan")
    r_max_all = float(np.nanmax(r_all)) if np.isfinite(r_all).any() else float("nan")
    eps_min = float(np.nanmin(ess_core)) if np.isfinite(ess_core).any() else float("nan")
    method = str(tab["ess_method"].iloc[0]) if len(tab) else "n/a"
    d = tab["rhat_absdiff"].to_numpy(dtype=float)
    diff_max = float(np.nanmax(d)) if np.isfinite(d).any() else float("nan")

    print(f"  收敛诊断（{chains} 链 × {ntrace} draws，方法 = {method}）：")
    print(f"    核心参数 R̂ 最大 = {r_max_core:.3f} | 全部参数 R̂ 最大 = {r_max_all:.3f}"
          f" | 阈值 {RHAT_MAX_OK}")
    print(f"    R̂ 超阈值 = {n_thr} / {len(tab)} | R̂ 为 NaN = {n_nan}"
          f" | 核心参数 ESS 最小 = {eps_min:.0f}")
    print(f"    自检：arviz 与手写 GB 的 R̂ 最大差 = {diff_max:.4f}（应远小于 0.05）")
    if n_nan:
        print(f"    ⚠️ 有 {n_nan} 个参数 R̂ 为 NaN（常量链或长度异常）——**不可视为通过**！")
    if n_thr:
        worst = (tab.dropna(subset=["rhat"]).sort_values("rhat", ascending=False)
                 .head(5)[["param", "rhat", "rhat_manual", "ess"]])
        print("    R̂ 最大的 5 个参数：")
        print(worst.round(3).to_string(index=False))

    return {"chains": chains, "ntrace_per_chain": ntrace, "ess_method": method,
            "rhat_threshold": RHAT_MAX_OK, "n_params": int(len(tab)),
            "rhat_max_core": r_max_core, "rhat_max_all": r_max_all,
            "n_rhat_gt_thr": n_thr, "n_rhat_nan": n_nan, "ess_min_core": eps_min,
            "rhat_arviz_vs_manual_maxdiff": diff_max}


def parse_args():
    p = argparse.ArgumentParser(description="NonMatching HDDM 拟合")
    p.add_argument("--model", default="M3", choices=list(MODEL_SPECS) + ["all"],
                   help="模型规格；all = 依次跑完 M0..M3")
    p.add_argument("--draws", type=int, default=3000)
    p.add_argument("--burn", type=int, default=500)
    p.add_argument("--chains", type=int, default=1,
                   help="链数；>1 走 HDDM 多链并行路径，并自动做 R̂/ESS 收敛诊断")
    p.add_argument("--no-parallel", dest="parallel", action="store_false",
                   help="多链串行执行（默认并行：n_jobs = min(cpu_count, chains)）")
    p.add_argument("--tag", default="",
                   help="输出文件名后缀（如 conv），便于与旧结果并存")
    p.add_argument("--spec-file", default="model_spec.json",
                   help="规格登记表文件名；分组并行跑时各自写自己的分片，避免并发覆盖")
    p.add_argument("--groups", default="",
                   help="只跑指定组，逗号分隔（如 3,4）；默认全部")
    p.set_defaults(parallel=True)
    return p.parse_args()


def build_fit_frame(df: pd.DataFrame, spec: dict):
    """按规格准备 HDDM 输入：选定 response 编码并断言无缺失。"""
    out = df.copy()
    out["response"] = (out["correct"] if spec["response"] == "correct" else out["response"])
    out = out.dropna(subset=["rt", "response"])
    out["response"] = out["response"].astype(int)
    for col in sorted({single(c) for c in spec["depends_on"].values()}):
        out[col] = out[col].astype(int)
        if col == "cell" and not set(out[col].unique()) <= {0, 1, 2, 3}:
            raise SystemExit(f"cell 取值异常：{sorted(out[col].unique())}")
    return out


def fit_one(gid, df, spec_name, spec, args):
    import hddm

    tag = f"_{args.tag}" if args.tag else ""
    stem = f"model{spec_name}_{gid}{tag}"
    print(f"\n{'=' * 62}")
    print(f"[{spec_name}] group {gid} | {spec['desc']}")
    print(f"{'=' * 62}")

    df = build_fit_frame(df, spec)
    n_subj = int(df["subj_idx"].nunique())
    print(f"  被试 {n_subj} | 试次 {len(df)} | response 编码 = {spec['response']}")
    print("  各方格试次数：")
    print(df.groupby(["cell"]).size().rename("n").to_frame().T.to_string())

    model = hddm.HDDM(
        df,
        # ⚠️ 必须传副本：HDDM 会就地改写该 dict（str → [str]），否则 MODEL_SPECS 常量被污染，
        #    记录进 model_spec.json 的也会是列表形式，step3 将静默丢掉 Δb。
        depends_on=copy.deepcopy(spec["depends_on"]),
        include=["v", "a", "t", "z"],
        bias=False,
        p_outlier=P_OUTLIER,
    )
    mode = "并行" if (args.chains > 1 and args.parallel) else "串行"
    print(f"  开始采样（{args.chains} 链 × {args.draws} draws / burn {args.burn}，{mode}）..."
          f"  [留存 = draws − burn]")
    t_start = time.time()
    db_name = str(OUT_DIR / f"_tmp_{stem}.db")
    model.sample(args.draws, burn=args.burn, dbname=db_name, db="pickle",
                 chains=args.chains, parallel=args.parallel)
    print(f"  采样完成，用时 {time.time() - t_start:.1f} s")

    # ⚠️ kabuki 多链分支 `except Exception: return None` 会静默丢链 → 必须显式核对
    got_chains = int(getattr(model, "chains", args.chains))
    if got_chains != args.chains:
        raise RuntimeError(
            f"[{stem}] 请求 {args.chains} 链，实际只拿到 {got_chains} 链。"
            "kabuki 已把失败链静默丢弃，请查看上面的 'Error processing' 信息。")
    ntrace = int(getattr(model, "ntrace", 0))
    print(f"  实际 {got_chains} 链 × {ntrace} draws（留存样本）")

    stats = model.gen_stats()
    stats.to_csv(OUT_DIR / f"{stem}_stats.csv")

    traces_raw = model.get_traces()
    traces = {}
    for key, val in traces_raw.items():
        try:
            arr = np.asarray(val, dtype=float).flatten()
            if arr.size:
                traces[key] = arr
        except Exception:
            continue
    if traces:
        with open(OUT_DIR / f"{stem}_traces.pkl", "wb") as f:
            pickle.dump(traces, f, protocol=pickle.HIGHEST_PROTOCOL)
        np.savez_compressed(OUT_DIR / f"{stem}_traces.npz", **traces)
        print(f"  迹线已存：{len(traces)} 个参数 × {next(iter(traces.values())).size} draws")

    conv = None
    if args.chains > 1:
        conv = convergence_report(traces, got_chains, ntrace, stem)
    else:
        print("  ⚠️ 单链运行：R̂ 不可定义，跳过收敛诊断（需 R̂ 请加 --chains N，N>1）")

    # 清理临时 db（多链会落下 _tmp_<stem>_chain*.db 与拼接后的 _tmp_<stem>_<ts>.db）
    for p in OUT_DIR.glob(f"_tmp_{stem}*.db"):
        try:
            p.unlink()
        except OSError:
            pass

    rec = {"group_id": gid, "model": spec_name, "desc": spec["desc"], "stem": stem,
           "response_coding": spec["response"], "depends_on": spec["depends_on"],
           "p_outlier": P_OUTLIER, "draws": args.draws, "burn": args.burn,
           "chains": got_chains, "ntrace_per_chain": ntrace, "parallel": bool(args.parallel),
           "n_subjects": n_subj, "n_trials": int(len(df)), "convergence": conv}
    return rec


def main():
    args = parse_args()
    try:
        import hddm  # noqa: F401
    except ImportError:
        print("hddm 未安装，请在 Docker 容器 (hcp4715/hddm) 中运行：")
        print('docker run -it --rm --cpus=4 -v "D:/GitHub_programe/GitHub/'
              'Guassion-Process-Experiment-Design:/home/jovyan/work" \\')
        print("  -p 8888:8888 hcp4715/hddm jupyter notebook")
        raise SystemExit(1)

    csv_files = sorted(DATA_DIR.glob("hddm_data_group*.csv"))
    if not csv_files:
        raise SystemExit(f"未找到 HDDM 就绪数据：{DATA_DIR}\n请先运行 step1_prepare_data.py")

    frames = {}
    for p in csv_files:
        gid = int(p.stem.split("group")[1].split("_")[0])
        frames[gid] = pd.read_csv(p)
    print(f"发现 {len(frames)} 个条件组")

    want = [g.strip() for g in args.groups.split(",") if g.strip()]
    if want:
        frames = {g: v for g, v in frames.items() if str(g) in want}
        print(f"按 --groups 过滤后：{sorted(frames)}")
    if not frames:
        raise SystemExit("--groups 过滤后没有可跑的组")

    specs = (list(MODEL_SPECS) if args.model == "all" else [args.model])
    total = len(specs) * len(frames)
    runs, k = [], 0
    for name in specs:
        for gid, df in frames.items():
            k += 1
            print(f"\n>>> 进度 {k}/{total}")
            runs.append(fit_one(gid, df, name, MODEL_SPECS[name], args))

    spec_path = OUT_DIR / args.spec_file
    prev = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else []
    prev = [r for r in prev if (r["group_id"], r["model"]) not in
            {(n["group_id"], n["model"]) for n in runs}]
    spec_path.write_text(json.dumps(prev + runs, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"\n规格登记 -> {spec_path}")

    if args.chains > 1:
        print("\n" + "=" * 66)
        print(f"收敛诊断汇总（核心参数 R̂ < {RHAT_MAX_OK} 且无 NaN 才算通过）")
        print("=" * 66)
        n_bad = 0
        for r in runs:
            c = r["convergence"]
            ok = (c["n_rhat_gt_thr"] == 0 and c["n_rhat_nan"] == 0)
            n_bad += 0 if ok else 1
            print(f"  {'✅' if ok else '❌'} g{r['group_id']:<2} "
                  f"R̂max(核心)={c['rhat_max_core']:.3f} R̂max(全部)={c['rhat_max_all']:.3f} "
                  f"ESSmin(核心)={c['ess_min_core']:.0f} "
                  f"超阈值={c['n_rhat_gt_thr']} NaN={c['n_rhat_nan']}")
        print(f"  → {'全部通过收敛判据' if n_bad == 0 else f'❌ {n_bad} 组未通过，需加大 draws/burn'}")
    print("\n下一步：本机运行 step3_extract_params.py")


if __name__ == "__main__":
    main()
