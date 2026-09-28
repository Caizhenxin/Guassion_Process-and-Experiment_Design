# -*- coding: utf-8 -*-
"""
model_comparison_frozen6.py —— 规则2/6：模型比较与模型恢复
=========================================================
对应《计算建模十条规则》：
* 规则2 "Design good models"：模型要覆盖假设，竞争模型不能是稻草人；
* 规则6 "Can you arbitrate between different models?"：模型比较须用**模型恢复**（混淆矩阵）验证；
* 规则9 "Reporting model-based analyses"：报告模型比较结果与胜出计数。

四个候选模型（同一预测任务：由 (P,T,W) 预测 v_self、v_stranger、a）
    M1 Mean        : 训练折均值（下界基线）
    M2 Linear      : [P,T,W] 标准化后的多元线性回归
    M3 Sigmoid     : 7 参数 Sigmoid 理论映射（与冻结版相同的函数形式与搜索边界）
    M4 Sigmoid+GP  : 论文主模型（Sigmoid 理论先验 + GP 残差）

评价：留一条件交叉验证（LOCV, 6 折）的预测 RMSE（v_self/v_stranger/a 的均值）——与论文研究三同口径。

模型恢复（parameter-level）
    对每个生成模型 g：用其对 6 条件的预测 + 噪声（拟合残差 SD 或固定 SD）生成 R 个合成"真值表"，
    每个合成表都跑完整的四模型 LOCV 比较，记录胜出模型 → 混淆矩阵 p(胜出 | 生成)。
    ⚠️ 该恢复在**参数层**（设计→参数映射）进行，不是行为层；论文中须写明这一范围限定。

用法
----
    python -u model_comparison_frozen6.py --reps 100
    python -u model_comparison_frozen6.py --skip-recovery          # 只做模型比较（很快）

说明：DE 预算（--maxiter/--popsize）在**所有模型上一致**，因此比较公平；
模型恢复使用更小的预算（--rec-*）以控制用时，并在输出中记录实际取值。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim_utils import FROZEN6_TABLE, OUT_DATA_DIR, OUT_FIG_DIR  # noqa: E402

MC_DIR = OUT_DATA_DIR / "model_comparison"
TARGETS = ["v_self", "v_stranger", "a"]
PARAM_NAMES = ["alaph1", "alaph2", "beta1", "beta2", "gamma", "base_scale_v", "base_scale_a"]
BOUNDS = [(0.1, 3.0), (-2.0, 1.0), (-1.0, 2.0), (-1.0, 1.0), (0.01, 1.0), (1.0, 10.0), (1.0, 10.0)]
GP_DIR = Path(__file__).resolve().parents[2] / "Python_HDDM" / "GP+Sigmoid"
MODEL_NAMES = ["M1_Mean", "M2_Linear", "M3_Sigmoid", "M4_SigmoidGP"]


# ------------------------------------------------------------------
# Sigmoid 前向函数（逐行对齐 gp_sigmoid_hybrid_model.py）
# ------------------------------------------------------------------
def sigmoid_v(T, P, cond, cp):
    T = np.asarray(T, dtype=float); P = np.asarray(P, dtype=float)
    k = 0.1 + (0.05 - 0.1) / (1 + np.exp(-cp["gamma"] * (P - 32)))
    v_T = 1.0 / (1.0 + np.exp(-0.01 * (T - 100.0)))
    v_P = 1.0 / (1.0 + np.exp(-k * (P - 4)))
    v_0 = v_T * v_P * cp["base_scale_v"]
    cond = np.asarray(cond)
    return np.where(cond == 1, v_0 * (1 + cp["alaph1"]), v_0 * (1 + cp["alaph2"]))


def sigmoid_a(M, cp):
    M = np.asarray(M, dtype=float)
    a_0 = 1.0 / (1.0 + np.exp(-0.01 * (M - 600.0))) * cp["base_scale_a"]
    return np.where(M > 600, a_0 * (1 + cp["beta1"]), a_0 * (1 + cp["beta2"]))


def load_table(path: Path = FROZEN6_TABLE, groups: list[int] | None = None) -> pd.DataFrame:
    df = pd.read_csv(path).sort_values("source_group_ids").reset_index(drop=True)
    df["group_id"] = df["source_group_ids"].astype(int)
    if groups:
        df = df[df["group_id"].isin(groups)].reset_index(drop=True)
    return df


# ------------------------------------------------------------------
# 候选模型
# ------------------------------------------------------------------
class MeanModel:
    name = "M1_Mean"

    def fit(self, df):
        self.mu = {t: float(df[f"{t}_mean"].mean()) for t in TARGETS}
        return self

    def predict(self, df):
        return {t: np.full(len(df), self.mu[t]) for t in TARGETS}


class LinearModel:
    name = "M2_Linear"

    def fit(self, df):
        X = df[["P", "T_ms", "W_ms"]].to_numpy(float)
        self.mu_x = X.mean(0); self.sd_x = X.std(0, ddof=0); self.sd_x[self.sd_x == 0] = 1.0
        A = np.column_stack([np.ones(len(X)), (X - self.mu_x) / self.sd_x])
        self.coef = {t: np.linalg.lstsq(A, df[f"{t}_mean"].to_numpy(float), rcond=None)[0] for t in TARGETS}
        return self

    def predict(self, df):
        X = df[["P", "T_ms", "W_ms"]].to_numpy(float)
        A = np.column_stack([np.ones(len(X)), (X - self.mu_x) / self.sd_x])
        return {t: A @ self.coef[t] for t in TARGETS}


class SigmoidModel:
    name = "M3_Sigmoid"

    def __init__(self, seed=42, maxiter=80, popsize=8):
        self.seed, self.maxiter, self.popsize = seed, maxiter, popsize

    def fit(self, df):
        T = df["T_ms"].to_numpy(float); P = df["P"].to_numpy(float); M = T + df["W_ms"].to_numpy(float)
        ones = np.ones(len(df)); zeros = np.zeros(len(df))
        y_self = df["v_self_mean"].to_numpy(float)
        y_str = df["v_stranger_mean"].to_numpy(float)
        y_a = df["a_mean"].to_numpy(float)

        def objective(x):
            cp = dict(zip(PARAM_NAMES, x))
            e1 = sigmoid_v(T, P, ones, cp) - y_self
            e2 = sigmoid_v(T, P, zeros, cp) - y_str
            e3 = sigmoid_a(M, cp) - y_a
            e = np.concatenate([e1, e2, e3])
            return float(np.sqrt(np.mean(e ** 2)))

        res = differential_evolution(objective, BOUNDS, maxiter=self.maxiter, popsize=self.popsize,
                                     seed=self.seed, tol=1e-7, polish=True)
        self.cp = dict(zip(PARAM_NAMES, res.x))
        self.rmse = float(res.fun)
        return self

    def predict(self, df):
        T = df["T_ms"].to_numpy(float); P = df["P"].to_numpy(float); M = T + df["W_ms"].to_numpy(float)
        return {
            "v_self": sigmoid_v(T, P, np.ones(len(df)), self.cp),
            "v_stranger": sigmoid_v(T, P, np.zeros(len(df)), self.cp),
            "a": sigmoid_a(M, self.cp),
        }


class HybridModel:
    """Sigmoid 校准 + GP 残差；复用项目 GPSigmoidHybridModel（核函数与目标完全一致）。

    gp_restarts 控制 GP 超参随机重启次数（项目默认 10，这里默认 2 以控制用时；
    该预算在所有模型间一致，故比较公平）。
    """
    name = "M4_SigmoidGP"

    def __init__(self, gp_dir: Path = GP_DIR, seed=42, maxiter=80, popsize=8, gp_restarts=2):
        self.seed, self.maxiter, self.popsize, self.gp_restarts = seed, maxiter, popsize, gp_restarts
        sys.path.insert(0, str(gp_dir))
        from gp_sigmoid_hybrid_model import GPSigmoidHybridModel  # noqa: E402
        self._cls = GPSigmoidHybridModel

    def fit(self, df):
        self.sig = SigmoidModel(seed=self.seed, maxiter=self.maxiter, popsize=self.popsize).fit(df)
        cp = dict(self.sig.cp)
        cp["t_baseline"] = float(df["t_mean"].mean())
        cp["z_baseline"] = float(df["z_mean"].mean())

        model = self._cls(seed=self.seed)
        if self.gp_restarts is not None:
            from sklearn.gaussian_process import GaussianProcessRegressor
            for attr in ["gp_v_self", "gp_v_stranger", "gp_a", "gp_t", "gp_z"]:
                old = getattr(model, attr)
                setattr(model, attr, GaussianProcessRegressor(
                    kernel=old.kernel, normalize_y=True,
                    n_restarts_optimizer=self.gp_restarts, random_state=self.seed))
        self.gp = model.fit(df, cp)
        return self

    def predict(self, df):
        df = df.reset_index(drop=True)
        out = {t: np.zeros(len(df)) for t in TARGETS}
        for i, row in df.iterrows():
            v_self, a_self, _t1, _z1 = self.gp.predict(row["P"], row["T_ms"], row["W_ms"], 1)
            v_str, a_str, _t0, _z0 = self.gp.predict(row["P"], row["T_ms"], row["W_ms"], 0)
            out["v_self"][i] = float(np.asarray(v_self).ravel()[0])
            out["v_stranger"][i] = float(np.asarray(v_str).ravel()[0])
            out["a"][i] = 0.5 * (float(np.asarray(a_self).ravel()[0]) + float(np.asarray(a_str).ravel()[0]))
        return out


def fresh_model(name: str, seed: int, maxiter: int, popsize: int, gp_restarts: int):
    if name == "M1_Mean":
        return MeanModel()
    if name == "M2_Linear":
        return LinearModel()
    if name == "M3_Sigmoid":
        return SigmoidModel(seed=seed, maxiter=maxiter, popsize=popsize)
    return HybridModel(seed=seed, maxiter=maxiter, popsize=popsize, gp_restarts=gp_restarts)


# ------------------------------------------------------------------
# LOCV 比较
# ------------------------------------------------------------------
def locv_compare(df: pd.DataFrame, seed: int, maxiter: int, popsize: int, gp_restarts: int,
                 verbose: bool = False) -> dict:
    acc = {n: {"sq": {t: [] for t in TARGETS}, "obs": {t: [] for t in TARGETS},
               "pred": {t: [] for t in TARGETS}} for n in MODEL_NAMES}
    groups = sorted(df["group_id"].unique())
    for gid in groups:
        train = df[df["group_id"] != gid]
        test = df[df["group_id"] == gid]
        for name in MODEL_NAMES:
            model = fresh_model(name, seed, maxiter, popsize, gp_restarts).fit(train)
            pred = model.predict(test)
            for t in TARGETS:
                obs = test[f"{t}_mean"].to_numpy(float)
                p = np.asarray(pred[t], dtype=float).ravel()
                acc[name]["sq"][t].append((p - obs) ** 2)
                acc[name]["obs"][t].append(obs)
                acc[name]["pred"][t].append(p)
        if verbose:
            print(f"    fold G{gid} 完成", flush=True)

    out = {}
    for name, d in acc.items():
        rmse, r = {}, {}
        for t in TARGETS:
            sq = np.concatenate(d["sq"][t]); obs = np.concatenate(d["obs"][t]); pred = np.concatenate(d["pred"][t])
            rmse[t] = float(np.sqrt(sq.mean()))
            r[t] = float(np.corrcoef(obs, pred)[0, 1]) if obs.std() > 0 and pred.std() > 0 else np.nan
        out[name] = {"rmse": rmse, "r": r, "aggregate": float(np.mean([rmse[t] for t in TARGETS]))}
    return out


def model_recovery(df: pd.DataFrame, reps: int, noise: str, fixed_noise: float, seed: int,
                   maxiter: int, popsize: int, gp_restarts: int,
                   rec_maxiter: int, rec_popsize: int, verbose_every: int = 10):
    rng = np.random.default_rng(seed)
    confusion = pd.DataFrame(0, index=MODEL_NAMES, columns=MODEL_NAMES, dtype=int)

    for gen in MODEL_NAMES:
        gen_model = fresh_model(gen, seed, maxiter, popsize, gp_restarts).fit(df)
        pred_full = gen_model.predict(df)
        sd = {}
        for t in TARGETS:
            resid = np.asarray(pred_full[t], float) - df[f"{t}_mean"].to_numpy(float)
            s = float(np.std(resid, ddof=1)) if noise == "fitted" else float(fixed_noise)
            sd[t] = s if np.isfinite(s) and s > 0 else float(fixed_noise)
        print(f"  [recovery] 生成模型 {gen}（噪声 SD: " +
              ", ".join(f"{t}={sd[t]:.3f}" for t in TARGETS) + "）", flush=True)

        for rep in range(reps):
            synth = df.copy()
            for t in TARGETS:
                synth[f"{t}_mean"] = np.asarray(pred_full[t], float) + rng.normal(0, sd[t], len(df))
            res = locv_compare(synth, seed + rep, rec_maxiter, rec_popsize, gp_restarts)
            winner = min(res, key=lambda k: res[k]["aggregate"])
            confusion.loc[gen, winner] += 1
            if verbose_every and (rep + 1) % verbose_every == 0:
                print(f"    {gen}: {rep+1}/{reps} 完成", flush=True)
    return confusion


def main():
    ap = argparse.ArgumentParser(description="模型比较与模型恢复（规则2/6）")
    ap.add_argument("--reps", type=int, default=100, help="模型恢复重复次数（默认 100）")
    ap.add_argument("--noise", default="fitted", choices=["fitted", "fixed"])
    ap.add_argument("--fixed-noise", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--maxiter", type=int, default=80, help="DE 迭代上限（主比较；默认 80）")
    ap.add_argument("--popsize", type=int, default=8)
    ap.add_argument("--gp-restarts", type=int, default=2, help="GP 超参随机重启次数（默认 2；项目冻结版为 10）")
    ap.add_argument("--rec-maxiter", type=int, default=15)
    ap.add_argument("--rec-popsize", type=int, default=5)
    ap.add_argument("--skip-recovery", action="store_true")
    ap.add_argument("--table", default=None,
                    help="条件冻结表路径（默认 GP_Sigmoid_Frozen6/input_conditions_g3g8.csv；"
                         "传入重跑表可复算表7-2/表7-3）")
    ap.add_argument("--out-dir", default=None, help="数据产物目录（默认 model_comparison）")
    ap.add_argument("--fig-dir", default=None, help="图产物目录（默认 TenRules 图目录）")
    ap.add_argument("--groups", default=None,
                    help="限定组号，逗号分隔（如 3,4,5,6,7,8）；默认使用表中全部行。"
                         "注意重跑表含 G1–G8，主口径必须传 3,4,5,6,7,8")
    args = ap.parse_args()

    global MC_DIR, OUT_FIG_DIR
    if args.table:
        global FROZEN6_TABLE
        FROZEN6_TABLE = Path(args.table)
    if args.out_dir:
        MC_DIR = Path(args.out_dir)
    if args.fig_dir:
        OUT_FIG_DIR = Path(args.fig_dir)

    MC_DIR.mkdir(parents=True, exist_ok=True)
    groups = [int(g) for g in args.groups.split(",")] if args.groups else None
    df = load_table(FROZEN6_TABLE, groups=groups)
    print(f"[model] 条件表 {FROZEN6_TABLE}", flush=True)
    print(f"[model] 条件数 {len(df)}：G{list(df.group_id)}", flush=True)
    print(f"[model] DE 预算 maxiter={args.maxiter}, popsize={args.popsize}, GP restarts={args.gp_restarts}", flush=True)

    print("[model] 运行 LOCV（留一条件，6 折 × 4 模型）...", flush=True)
    res = locv_compare(df, args.seed, args.maxiter, args.popsize, args.gp_restarts, verbose=True)

    rows = [{"model": n, "target": t, "locv_rmse": d["rmse"][t], "locv_r": d["r"][t]}
            for n, d in res.items() for t in TARGETS]
    pd.DataFrame(rows).sort_values(["target", "locv_rmse"]).to_csv(MC_DIR / "model_comparison_locv.csv", index=False)

    summ = pd.DataFrame([{"model": n, **{f"rmse_{t}": d["rmse"][t] for t in TARGETS},
                          "aggregate_rmse": d["aggregate"]} for n, d in res.items()])
    summ = summ.sort_values("aggregate_rmse").reset_index(drop=True)
    summ["rank"] = np.arange(1, len(summ) + 1)
    summ.to_csv(MC_DIR / "model_comparison_summary.csv", index=False)
    print("\n[model] LOCV 聚合 RMSE（越小越好）：", flush=True)
    print(summ.round(4).to_string(index=False), flush=True)

    prob = None
    if not args.skip_recovery:
        print(f"\n[model] 模型恢复：4 个生成模型 × {args.reps} 次重复（噪声={args.noise}）...", flush=True)
        confusion = model_recovery(df, args.reps, args.noise, args.fixed_noise, args.seed,
                                   args.maxiter, args.popsize, args.gp_restarts,
                                   args.rec_maxiter, args.rec_popsize)
        confusion.to_csv(MC_DIR / "model_recovery_confusion.csv")
        prob = confusion.div(confusion.sum(axis=1), axis=0)
        prob.to_csv(MC_DIR / "model_recovery_confusion_prob.csv")
        (MC_DIR / "model_recovery_summary.json").write_text(json.dumps({
            "reps": args.reps, "noise": args.noise, "fixed_noise": args.fixed_noise,
            "de_budget": {"maxiter": args.maxiter, "popsize": args.popsize},
            "recovery_budget": {"maxiter": args.rec_maxiter, "popsize": args.rec_popsize},
            "gp_restarts": args.gp_restarts,
            "confusion_counts": confusion.to_dict(),
            "diagonal_recovery_rate": {n: float(prob.loc[n, n]) for n in confusion.index},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[model] 混淆矩阵（行=生成模型，列=胜出模型）：\n" + confusion.to_string(), flush=True)

    _plot(summ, prob)
    print(f"\n[model] 产物 → {MC_DIR}", flush=True)


def _plot(summ: pd.DataFrame, prob: pd.DataFrame | None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sim_utils import setup_cjk_font
    setup_cjk_font()

    OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    ncol = 2 if prob is not None else 1
    fig, axes = plt.subplots(1, ncol, figsize=(12 if ncol == 2 else 6, 4.2), squeeze=False)

    ax = axes[0][0]
    ax.barh(summ["model"], summ["aggregate_rmse"], color="tab:blue", alpha=.85)
    for i, v in enumerate(summ["aggregate_rmse"]):
        ax.text(v, i, f" {v:.3f}", va="center", fontsize=9)
    ax.set_xlabel("LOCV 聚合 RMSE（v_self/v_stranger/a 均值）")
    ax.set_title("模型比较：预测误差"); ax.invert_yaxis()

    if prob is not None:
        ax2 = axes[0][1]
        im = ax2.imshow(prob.to_numpy(float), cmap="Blues", vmin=0, vmax=1)
        ax2.set_xticks(range(len(prob.columns)))
        ax2.set_xticklabels(prob.columns, rotation=45, ha="right", fontsize=8)
        ax2.set_yticks(range(len(prob.index)))
        ax2.set_yticklabels(prob.index, fontsize=8)
        for i in range(prob.shape[0]):
            for j in range(prob.shape[1]):
                ax2.text(j, i, f"{prob.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8,
                         color="white" if prob.iloc[i, j] > .5 else "black")
        ax2.set_xlabel("胜出模型"); ax2.set_ylabel("生成模型")
        ax2.set_title("模型恢复混淆矩阵")
        fig.colorbar(im, ax=ax2, fraction=.046)

    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "model_comparison.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
