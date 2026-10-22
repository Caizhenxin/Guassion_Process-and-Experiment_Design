"""gen_model_data.py —— 三条模型（M-T1 / M-T2 / M-T3）的试次级数据生成器。

一条命令生成一个模型的 CSV（默认写到 `2_Data/Generate_Data/<模型>/`）::

    python 1_Code/Experiment/gen_model_data.py --model M-T1
    python 1_Code/Experiment/gen_model_data.py --model all

产物（每个模型一份，列名与真实流水线一致，可直接喂 `run_pipeline.py`）
-----------------------------------------------------------------------
``trials_long.csv``      逐试次（含真值潜变量，便于恢复检验）
``subjects.csv``         逐被试真值参数
``cells.csv``            逐单元汇总（正确率 / 遗漏率 / RT 均值与中位）
``meta.json``            本次生成的模型、真值、随机种子、试次数

三条模型的差别只有一处：**漂移在刺激期内怎么长、掩蔽之后怎么降**
------------------------------------------------------------------
=====  ==========================  ==================  ==================
模型    刺激期内漂移                 掩蔽后               一句话
=====  ==========================  ==================  ==================
M-T1   ``d_stim``（阶跃）            ``rho·d_stim``      「呈现期满速积累，掩蔽后打折」
M-T2   ``d_stim·(1−e^{−t/τ_T})``     ``rho·d_stim·g(T)``  「漂移本身要时间才升到满」
M-T3   ``d_stim``（阶跃）            ``d_stim``（rho=1）  「掩蔽没有影响」
=====  ==========================  ==================  ==================

真值（`GEN_TRUTH`）与「设计前提真值」不同，这是有意的
------------------------------------------------------
`mapping.TRUTH_EXP`（D100 的设计前提）在 P=0/8/32 处会把漂移**截断到 0**
（`mapping.drift_magnitude` 取 ``max(d, 1e-6)``），因为它是「以 P_ref=120 为锚、
beta_P=1.5」的外推参数化。用那套真值生成数据，三组被试会是**零漂移**（正确率 0.50、
无任何 T 效应），既不可视化也不可检。所以生成数据用**全 P 水平漂移为正**的一套
（`GEN_TRUTH`，D109/§13 里的「中段参数」），只保证行为量级合理；它**不代表**论文的
最终真值假设——论文的样本量论证仍以 CRLB 的 `TRUTH_EXP` 为准。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent            # 1_Code/Experiment
_ROOT = _HERE.parents[1]                           # 仓库根
for _p in (str(_HERE.parent / "DDM_Core"), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mapping import MappingParams, PARAM_BOUNDS, trial_params      # noqa: E402
import twophase                                                    # noqa: E402
import ramp as ramp_mod                                            # noqa: E402

__all__ = ["MODELS", "GEN_TRUTH", "build_design", "draw_subject",
           "generate", "load_trials", "DEFAULT_OUT"]

DEFAULT_OUT = _ROOT / "2_Data" / "Generate_Data"

#: 设计水平（与 Stage 5 定稿一致）
P_LEVELS = [0.0, 8.0, 32.0, 120.0]
T_LEVELS = [2 / 60, 5 / 60, 9 / 60, 15 / 60]       # 33.3 / 83.3 / 150 / 250 ms
W_LEVELS = [48 / 60, 72 / 60, 108 / 60]            # 800 / 1200 / 1800 ms
N_REP = 12                                          # 每个 (T, W, 身份, 匹配) 单元的重复

#: 三条模型。``kind`` 决定用哪条生成路径。
MODELS = {
    "M-T1": {"kind": "twophase", "label": "两阶段阶跃（掩蔽后 × rho）",
             "gloss": "刺激期内漂移恒为 d_stim；掩蔽后降为 rho·d_stim"},
    "M-T2": {"kind": "ramp", "label": "两阶段斜坡（漂移逐步爬升）",
             "gloss": "刺激期内 d(t)=d_stim·(1−e^{−t/τ_T})；掩蔽后 × rho"},
    "M-T3": {"kind": "single", "label": "单阶段（掩蔽无影响，rho=1）",
             "gloss": "M-T1 在 rho=1 处的严格嵌套特例"},
}

#: 生成用真值：``lin`` 形状（无时标），四个 P 水平的漂移都为正。
#: 数值按「行为量级像这个范式」标定过（`_scratch/_probe_gen_truth*.py`）：
#: 正确率 ≈ 0.74、遗漏 ≈ 0.13、RT 中位 ≈ 530 ms，且三个设计变量都**看得见**——
#: T 越长越准（0.73 → 0.82）、W 越长反应越慢（458 → 632 ms）、自我比他人准 ~6 个百分点。
GEN_TRUTH = MappingParams(
    shape_model="lin", P_ref=30.0, T_ref=0.10, W_ref=1.20,
    d_ref=0.80, beta_P=0.35, tau_P=30.0,
    beta_T=0.95, beta_S=0.30, beta_ST=0.12,
    a_ref=1.52, delta_a=0.30, t0=0.19,
)

#: 被试抽样的个体差异（SD）；``None`` 表示不抖动。全部截断在 `PARAM_BOUNDS` 内。
#:
#: 2026-10-22 清理：此处原先**重复定义两次**，第二份静默覆盖第一份
#: （``d_ref`` 0.16→0.22、``beta_T`` 0.18→0.15、``a_ref`` 0.14→0.12、
#: ``beta_ST`` 0.050→0.030），读代码的人会拿到错的那一组。
#: 保留下来的就是**一直生效的那一份**，数值未改，故既有生成产物（
#: ``2_Data/Generate_Data/M-T*/``）不受影响、无需重跑。
GEN_SD = {"d_ref": 0.22, "beta_T": 0.15, "beta_S": 0.10, "a_ref": 0.12,
          "t0": 0.030, "beta_ST": 0.030, "delta_a": 0.08}


# ----------------------------------------------------------------------
# 设计表
# ----------------------------------------------------------------------
def build_design(group: int, n_rep: int = N_REP) -> tuple[dict, list[dict]]:
    """构造一个被试的试次表（不含观测）。

    ``group`` 从 1 起（1..4 ⇒ P = 0/8/32/120）。匹配与不匹配**在单元内平衡**
    （``n_rep=12`` ⇒ 每格 6 : 6），这样 ``is_match`` 不会与身份/T 共线。
    """
    group = int(group)
    if not 1 <= group <= len(P_LEVELS):
        raise ValueError(f"group 必须在 1..{len(P_LEVELS)}，收到 {group}")
    P = P_LEVELS[group - 1]
    design = {"P": [], "T": [], "W": [], "is_self": [], "is_match": []}
    rows: list[dict] = []
    for T in T_LEVELS:
        for W in W_LEVELS:
            block = W_LEVELS.index(W) + 1
            for is_self in (0, 1):
                for k in range(2 * n_rep):      # 匹配 / 不匹配各 n_rep 次
                    design["P"].append(P)
                    design["T"].append(T)
                    design["W"].append(W)
                    design["is_self"].append(float(is_self))
                    design["is_match"].append(int(k % 2))
                    rows.append({"P": P, "T_ms": round(T * 1000.0, 4),
                                 "W_ms": round(W * 1000.0, 1),
                                 "is_self": is_self, "is_match": int(k % 2),
                                 "block": block})
    return ({k: np.asarray(v, dtype=float) for k, v in design.items()}, rows)


def draw_subject(sid: int, group: int, rng: np.random.Generator,
                 truth: MappingParams = GEN_TRUTH,
                 sd: dict | None = GEN_SD) -> MappingParams:
    """按 ``truth ± N(0, sd)`` 抽一名被试的真值参数（截断在参数边界内）。"""
    sd = {} if sd is None else dict(sd)
    if not sd:
        return truth
    vals = {}
    for name, s in sd.items():
        lo, hi = PARAM_BOUNDS[name]
        vals[name] = float(np.clip(rng.normal(getattr(truth, name), s), lo, hi))
    return truth.replace(**vals)


# ----------------------------------------------------------------------
# 生成
# ----------------------------------------------------------------------
def _simulate(kind: str, design: dict, p: MappingParams, rho: float,
              rng: np.random.Generator, dt: float,
              tau_ramp: float | None, drift_sd: float = 0.0) -> dict:
    if kind == "ramp":
        return ramp_mod.simulate_ramp_subject(design, p, rho, rng, dt=dt,
                                              tau_ramp=tau_ramp,
                                              drift_sd=drift_sd)
    r = 1.0 if kind == "single" else float(rho)
    return twophase.simulate_euler_subject(design, p, r, rng, dt=dt,
                                           drift_sd=drift_sd)


def generate(model: str, out_dir: Path | str | None = None,
             n_subjects_per_group: int = 2, n_rep: int = N_REP,
             rho: float = 0.8, tau_ramp: float | None = None,
             ramp_beta_t: str = "zero", dt: float = 5e-5,
             drift_sd: float = 0.25,
             seed: int = 20261021, truth: MappingParams = GEN_TRUTH,
             verbose: bool = True) -> dict:
    """生成一个模型的试次级数据，写 CSV，返回元信息。"""
    if model not in MODELS:
        raise ValueError(f"未知模型：{model}（可选 {list(MODELS)}）")
    spec = MODELS[model]
    kind = spec["kind"]

    p_truth = truth
    if kind == "ramp" and ramp_beta_t == "zero":
        # M-T2 的 T 效应来自斜坡本身，映射层的 beta_T 必须关掉（见模块 docstring）
        p_truth = truth.replace(beta_T=0.0)

    out = Path(out_dir) if out_dir is not None else DEFAULT_OUT / model
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    trial_rows: list[dict] = []
    subject_rows: list[dict] = []
    t_start = time.time()

    sid = 0
    for group in range(1, len(P_LEVELS) + 1):
        for j in range(int(n_subjects_per_group)):
            sid += 1
            p_sub = draw_subject(sid, group, rng, p_truth, GEN_SD)
            design, meta = build_design(group, n_rep)
            sim = _simulate(kind, design, p_sub, rho, rng, dt, tau_ramp, drift_sd)
            tp = trial_params(design, p_sub)
            rt = sim["rt"]
            side = sim["side"]
            om = sim["omission"]
            for i, m in enumerate(meta):
                is_om = int(om[i])
                correct = 0 if is_om else int(side[i] == int(m["is_match"]))
                trial_rows.append({
                    "subject_id": sid,
                    "group": group,
                    "P": m["P"],
                    "T_ms": m["T_ms"],
                    "W_ms": m["W_ms"],
                    "is_self": m["is_self"],
                    "is_match": m["is_match"],
                    "block": m["block"],
                    "rt_ms": ("" if is_om else round(float(rt[i]) * 1000.0, 3)),
                    "response": "none" if is_om else ("upper" if side[i] == 1 else "lower"),
                    "correct": correct,
                    "omission": is_om,
                    "timeout": is_om,
                    "d_stim": round(float(tp["d"][i]), 6),
                    "a": round(float(tp["a"][i]), 6),
                    "z": round(float(tp["z"][i]), 6),
                    "t0_ms": round(float(tp["t0"]) * 1000.0, 3),
                })
            row = {"subject_id": sid, "group": group, "P": P_LEVELS[group - 1],
                   "model": model, "rho": (1.0 if kind == "single" else float(rho))}
            row.update({k: round(float(getattr(p_sub, k)), 6)
                        for k in ("d_ref", "beta_P", "beta_T", "tau_P", "tau_T",
                                  "beta_S", "beta_ST", "a_ref", "delta_a", "t0")})
            subject_rows.append(row)
            if verbose:
                acc = 1.0 - np.mean([r["omission"] for r in trial_rows[-len(meta):]])
                print(f"  [{model}] 被试 {sid:>2}（组 {group}，P={P_LEVELS[group-1]:>0.0f}）"
                      f" 试次 {len(meta)}  响应率 {acc:.3f}  "
                      f"{time.time() - t_start:5.1f}s")

    # --- 落盘 ---
    _write_csv(out / "trials_long.csv", trial_rows)
    _write_csv(out / "subjects.csv", subject_rows)
    _write_csv(out / "cells.csv", summarize_cells(trial_rows))

    meta = {
        "model": model,
        "label": spec["label"],
        "gloss": spec["gloss"],
        "kind": kind,
        "rho": (1.0 if kind == "single" else float(rho)),
        "tau_ramp": (None if kind != "ramp" else
                     float(tau_ramp if tau_ramp is not None else p_truth.tau_T)),
        "ramp_beta_t": ramp_beta_t,
        "dt": dt,
        "drift_sd": float(drift_sd),
        "n_subjects": len(subject_rows),
        "n_subjects_per_group": int(n_subjects_per_group),
        "n_rep": int(n_rep),
        "n_trials_total": len(trial_rows),
        "seed": int(seed),
        "truth": {k: float(getattr(p_truth, k)) for k in
                  ("d_ref", "beta_P", "beta_T", "beta_S", "beta_ST", "a_ref",
                   "delta_a", "t0", "P_ref", "T_ref", "W_ref")},
        "truth_note": ("beta_T 已置 0：M-T2 的 T 效应由斜坡产生" if
                       (kind == "ramp" and ramp_beta_t == "zero") else ""),
        "elapsed_s": round(time.time() - t_start, 1),
        "schema_version": 1,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    if verbose:
        print(f"  [{model}] 完成：{len(trial_rows)} 行 → {out}  "
              f"（{meta['elapsed_s']} s）")
    return {"model": model, "dir": str(out), "meta": meta,
            "trials": trial_rows, "subjects": subject_rows}


def summarize_cells(trial_rows: list[dict]) -> list[dict]:
    """逐 (group, P, T_ms, W_ms, is_self) 汇总正确率 / 遗漏率 / RT。"""
    buckets: dict[tuple, list[dict]] = {}
    for r in trial_rows:
        key = (r["group"], r["P"], r["T_ms"], r["W_ms"], r["is_self"])
        buckets.setdefault(key, []).append(r)
    out = []
    for key in sorted(buckets):
        rows = buckets[key]
        rt = [r["rt_ms"] for r in rows if r["rt_ms"] != ""]
        acc = np.mean([r["correct"] for r in rows if not r["omission"]]) if rt else float("nan")
        out.append({
            "group": key[0], "P": key[1], "T_ms": key[2], "W_ms": key[3],
            "is_self": key[4], "n_trials": len(rows),
            "n_resp": len(rt),
            "acc_given_response": round(float(acc), 4),
            "omission_rate": round(float(np.mean([r["omission"] for r in rows])), 4),
            "rt_mean_ms": round(float(np.mean(rt)), 1) if rt else "",
            "rt_median_ms": round(float(np.median(rt)), 1) if rt else "",
        })
    return out


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ----------------------------------------------------------------------
# 读回（给 notebook 与画图脚本用）
# ----------------------------------------------------------------------
def load_trials(path_or_dir: Path | str):
    """读 ``trials_long.csv``（给路径或目录），返回 pandas DataFrame。"""
    import pandas as pd
    p = Path(path_or_dir)
    if p.is_dir():
        p = p / "trials_long.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    df["rt_s"] = df["rt_ms"] / 1000.0
    df["T_s"] = df["T_ms"] / 1000.0
    df["W_s"] = df["W_ms"] / 1000.0
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成 M-T1/M-T2/M-T3 的试次级数据")
    ap.add_argument("--model", default="all",
                    help=f"{' / '.join(MODELS)} / all（默认 all）")
    ap.add_argument("--out", default=None, help="输出根目录（默认 2_Data/Generate_Data）")
    ap.add_argument("--n-subjects-per-group", type=int, default=4)
    ap.add_argument("--n-rep", type=int, default=N_REP)
    ap.add_argument("--rho", type=float, default=0.8, help="掩蔽后保留率（M-T1/M-T2）")
    ap.add_argument("--tau-ramp", type=float, default=None, help="斜坡时标（秒，M-T2）")
    ap.add_argument("--ramp-beta-t", choices=["zero", "mapping"], default="zero",
                    help="M-T2 的映射层 beta_T：zero（默认，T 效应由斜坡产生）/ mapping")
    ap.add_argument("--dt", type=float, default=5e-5, help="Euler 步长（秒）")
    ap.add_argument("--drift-sd", type=float, default=0.25,
                    help="逐试次漂移变异（lognormal，均值 1）；0 = 参数同质模型")
    ap.add_argument("--seed", type=int, default=20261021)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    root = Path(a.out) if a.out else DEFAULT_OUT
    models = list(MODELS) if a.model == "all" else [a.model]
    for m in models:
        if m not in MODELS:
            raise SystemExit(f"未知模型：{m}（可选 {list(MODELS)} 或 all）")
        generate(m, root / m, n_subjects_per_group=a.n_subjects_per_group,
                 n_rep=a.n_rep, rho=a.rho, tau_ramp=a.tau_ramp,
                 ramp_beta_t=a.ramp_beta_t, dt=a.dt, drift_sd=a.drift_sd,
                 seed=a.seed, verbose=not a.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
