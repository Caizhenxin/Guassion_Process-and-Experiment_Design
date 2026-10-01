# -*- coding: utf-8 -*-
"""Step 3: 提取 NonMatching 模型的参数后验，并计算派生量 Δv / b / Δb

2026-09-30 重写
==============
* 支持 step2 的四个模型规格（读取 `HDDM_Traces_Nonmatching/model_spec.json`）
* 派生量**逐 draws 计算**（而不是只对后验均值做算术），因此带正确的不确定度：

    Δv   = v(self) − v(stranger)                    证据优势成分
    b_i  = (z(匹配,i) − z(不匹配,i)) / 2              身份 i 的匹配键偏向
    Δb   = b_self − b_stranger                      偏向成分（SPE 的第二条通道）

  仅在"正确性编码 + z 依 condition/cell"的规格（M2/M3）下才有 b/Δb，
  因为按键编码下 z 不是按键偏向。

用法
====
  python step3_extract_params.py
"""

import json
import pickle
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[2]
TRACE_DIR = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Traces_Nonmatching"
FIG_DIR = BASE_DIR / "3_Figures" / "HDDM_Results_Nonmatching"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# 身份 / 条件的编码（与 step1 一致）
IDENT_NAME = {0: "stranger", 1: "self"}
COND_NAME = {1: "matching", 0: "nonmatching"}
# cell = identity * 2 + condition
CELL_SELF_M, CELL_SELF_N = 1 * 2 + 1, 1 * 2 + 0   # 3, 2
CELL_STR_M, CELL_STR_N = 0 * 2 + 1, 0 * 2 + 0     # 1, 0


def single(v):
    """把 depends_on 的值统一成单个列名。

    ⚠️ HDDM 会**就地改写**传入的 `depends_on` dict（把 `'identity'` 规范化成 `['identity']`），
    因此 `model_spec.json` 里记下的值可能是列表。若不还原，`z_key == 'cell'` 会永远为假，
    结果是 b / Δb **被静默丢弃**（2026-10-01 实测踩到）。
    """
    if isinstance(v, (list, tuple)):
        return v[0] if len(v) == 1 else tuple(v)
    return v


# ------------------------------------------------------------------
# 工具
# ------------------------------------------------------------------
def find_trace(traces: dict, name: str):
    """在迹线字典里按精确名取值（HDDM 的键名可能带或不带括号形式）。"""
    if name in traces:
        return np.asarray(traces[name], dtype=float)
    alt = name.replace("(", "").replace(")", "")
    if alt in traces:
        return np.asarray(traces[alt], dtype=float)
    return None


def phi(x):
    """标准正态 CDF。优先 scipy.special.ndtr（向量化），退回 math.erf。

    注意：HDDM 的迹线里 z 以 probit 形式存放（`z_trans(N)`），需要用它还原为边界比例。
    """
    x = np.asarray(x, dtype=float)
    try:
        from scipy.special import ndtr
        return ndtr(x)
    except Exception:
        import math
        flat = [0.5 * (1.0 + math.erf(float(v) / math.sqrt(2.0))) for v in x.ravel()]
        return np.asarray(flat, dtype=float).reshape(x.shape)


def stat_row(stats, name):
    """从 gen_stats() 结果里取某参数的 mean/std/95%CI；'z' 兼容 z_trans（probit）。"""
    if name in stats.index:
        r = stats.loc[name]
        return {"mean": float(r["mean"]), "std": float(r["std"]),
                "lo": float(r["2.5q"]), "hi": float(r["97.5q"])}
    if name == "z":
        from scipy.stats import norm
        for k in ("z_trans", "z_trans_subj"):
            if k in stats.index:
                r = stats.loc[k]
                return {"mean": float(norm.cdf(r["mean"])), "std": float(r["std"]),
                        "lo": float(norm.cdf(r["2.5q"])), "hi": float(norm.cdf(r["97.5q"]))}
    return None


class Val:
    """一个后验量：优先用 draws（可精确做代数运算），否则退化为 mean/CI 传播。"""

    __slots__ = ("draws", "mean", "lo", "hi")

    def __init__(self, draws=None, mean=None, lo=None, hi=None):
        self.draws, self.mean, self.lo, self.hi = draws, mean, lo, hi

    @classmethod
    def from_traces(cls, traces, name):
        t = find_trace(traces, name)
        if t is not None:
            return cls(draws=t)
        # HDDM 的迹线把 z 存成 probit（z_trans(N)），需还原为边界比例后才能在 draws 上做代数
        m = re.fullmatch(r"z\((\d+)\)", name)
        if m:
            t = find_trace(traces, "z_trans(%s)" % m.group(1))
            if t is not None:
                return cls(draws=phi(t))
        return None

    @classmethod
    def from_stats(cls, stats, name):
        s = stat_row(stats, name)
        return cls(mean=s["mean"], lo=s["lo"], hi=s["hi"]) if s else None

    def ci(self) -> dict:
        if self.draws is not None:
            x = self.draws[np.isfinite(self.draws)]
            if x.size:
                return {"mean": float(x.mean()), "std": float(x.std()),
                        "lo": float(np.percentile(x, 2.5)),
                        "hi": float(np.percentile(x, 97.5))}
        return {"mean": self.mean, "std": np.nan, "lo": self.lo, "hi": self.hi}

    def _mean(self):
        if self.mean is not None:
            return self.mean
        if self.draws is not None and self.draws.size:
            return float(np.nanmean(self.draws))
        return np.nan

    def _bin(self, other, sign):
        if self.draws is not None and other.draws is not None:
            n = min(len(self.draws), len(other.draws))
            return Val(draws=self.draws[:n] + sign * other.draws[:n])
        # 任一侧缺 draws：退化为均值差 + 端点向不利方向传播（保守）
        a_lo, a_hi = self.lo, self.hi
        b_lo, b_hi = (other.lo, other.hi) if sign > 0 else (other.hi, other.lo)
        a_lo = np.nan if a_lo is None else a_lo
        a_hi = np.nan if a_hi is None else a_hi
        b_lo = np.nan if b_lo is None else b_lo
        b_hi = np.nan if b_hi is None else b_hi
        return Val(mean=self._mean() + sign * other._mean(),
                   lo=a_lo + sign * b_lo, hi=a_hi + sign * b_hi)

    def __sub__(self, other):
        return self._bin(other, -1)

    def scale(self, k):
        if self.draws is not None:
            return Val(draws=self.draws * k)
        return Val(mean=self.mean * k, lo=self.lo * k, hi=self.hi * k)


def derive(traces: dict, spec: dict, stats: pd.DataFrame) -> dict:
    """按规格计算派生量。返回 {名称: {mean,std,lo,hi}}。"""
    dep = spec["depends_on"]
    out: dict = {}

    def get(name):
        return Val.from_traces(traces, name) or Val.from_stats(stats, name)

    # --- Δv = v_self − v_stranger ---
    v_s, v_g = get("v(1)"), get("v(0)")
    if v_s is not None and v_g is not None:
        out["delta_v"] = (v_s - v_g).ci()

    # --- 匹配键偏向 b（仅"正确性编码 + z 依 condition/cell"时有意义）---
    z_key = single(dep.get("z"))
    if spec["response"] != "correct" or z_key is None:
        return out

    if z_key == "cell":
        z_sm, z_sn = get(f"z({CELL_SELF_M})"), get(f"z({CELL_SELF_N})")
        z_gm, z_gn = get(f"z({CELL_STR_M})"), get(f"z({CELL_STR_N})")
        if None not in (z_sm, z_sn, z_gm, z_gn):
            b_s = (z_sm - z_sn).scale(0.5)
            b_g = (z_gm - z_gn).scale(0.5)
            out["b_self"] = b_s.ci()
            out["b_stranger"] = b_g.ci()
            out["delta_b"] = (b_s - b_g).ci()
            out["z_self_matching"] = z_sm.ci()
            out["z_self_nonmatching"] = z_sn.ci()
            out["z_stranger_matching"] = z_gm.ci()
            out["z_stranger_nonmatching"] = z_gn.ci()
    elif z_key == "condition":
        z_m, z_n = get("z(1)"), get("z(0)")
        if z_m is not None and z_n is not None:
            out["b"] = (z_m - z_n).scale(0.5).ci()
    return out


def iter_runs():
    """按 model_spec.json 逐 (模型, 组) 处理；无登记表时回退到目录扫描。"""
    stats_files = sorted(TRACE_DIR.glob("*_stats.csv"))
    if not stats_files:
        raise FileNotFoundError(
            f"未找到拟合结果！\n预期位置: {TRACE_DIR}\n请先在 Docker 中运行 step2_hddm_fit.py")

    spec_path = TRACE_DIR / "model_spec.json"
    if spec_path.exists():
        for rec in json.loads(spec_path.read_text(encoding="utf-8")):
            stem = f"model{rec['model']}_{rec['group_id']}"
            p = TRACE_DIR / f"{stem}_stats.csv"
            if p.exists():
                yield rec["group_id"], rec["model"], rec, p
        return

    print("⚠️  未找到 model_spec.json，回退为按文件名解析（假定 z 为标量、按键编码）")
    for p in stats_files:
        m = re.search(r"group(\d+)_P(\d+)_T(\d+)_W(\d+)", p.stem)
        if not m:
            continue
        gid = int(m.group(1))
        yield gid, "legacy", {"model": "legacy", "response_coding": "key",
                              "depends_on": {"v": "identity"}}, p


def main():
    print("=" * 66)
    print("Step 3: 提取参数后验 + 计算派生量 Δv / b / Δb")
    print("=" * 66)

    rows = []
    for gid, model, rec, stats_path in iter_runs():
        stem = stats_path.stem.replace("_stats", "")
        stats = pd.read_csv(stats_path, index_col=0)

        pkl = TRACE_DIR / f"{stem}_traces.pkl"
        traces = {}
        if pkl.exists():
            with open(pkl, "rb") as f:
                traces = pickle.load(f)

        spec = {"response": rec.get("response_coding", "key"),
                "depends_on": rec.get("depends_on", {"v": "identity"})}

        row = {"model": model, "group_id": gid}
        m = re.search(r"P(\d+)_T(\d+)_W(\d+)", stem)
        if m:
            row.update({"P": int(m.group(1)), "T_ms": int(m.group(2)), "W_ms": int(m.group(3))})
            row["M_ms"] = row["T_ms"] + row["W_ms"]
        row["response_coding"] = spec["response"]

        # 原始群体参数
        for name, label in [("v(0)", "v_stranger"), ("v(1)", "v_self"),
                            ("a", "a"), ("t", "t"), ("z", "z")]:
            s = stat_row(stats, name)
            if s:
                for k, v in s.items():
                    row[f"{label}_{k}"] = v
        for lvl in range(4):
            for pre, lab in (("v", "v"), ("z", "z")):
                s = stat_row(stats, f"{pre}({lvl})")
                if s:
                    row[f"{lab}_cell{lvl}_mean"] = s["mean"]

        # 派生量
        for k, v in derive(traces, spec, stats).items():
            for kk, vv in v.items():
                row[f"{k}_{kk}"] = vv

        rows.append(row)
        print(f"\n[{model}] 组 {gid}")
        for k in ["delta_v", "b_self", "b_stranger", "delta_b"]:
            if f"{k}_mean" in row:
                print(f"  {k:<12} = {row[f'{k}_mean']:+.3f} "
                      f"[{row[f'{k}_lo']:+.3f}, {row[f'{k}_hi']:+.3f}]")

    df = pd.DataFrame(rows).sort_values(["model", "group_id"])
    out_csv = TRACE_DIR / "all_groups_ddm_params.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n汇总表 -> {out_csv}")

    # 跨组汇总（每个模型一行）
    print("\n" + "=" * 66)
    print("跨条件的派生量汇总（后验均值 ± 跨组 SD）")
    print("=" * 66)
    for model in df["model"].unique():
        sub = df[df["model"] == model]
        print(f"\n[{model}]  n = {len(sub)} 组")
        for k, desc in [("delta_v", "Δv 证据优势"), ("delta_b", "Δb 偏向成分"),
                        ("b_self", "b 自我"), ("b_stranger", "b 陌生人")]:
            col = f"{k}_mean"
            if col in sub.columns and sub[col].notna().any():
                vals = sub[col].dropna()
                print(f"  {desc:<12} {vals.mean():+.3f} ± {vals.std(ddof=1) if len(vals) > 1 else 0:.3f}"
                      f"   （逐组：{', '.join(f'{v:+.2f}' for v in vals)}）")

    # ---------------- 绘图 ----------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError:
        print("\n（matplotlib 不可用，跳过绘图）")
        return

    main_model = "M3" if (df["model"] == "M3").any() else df["model"].iloc[-1]
    d = df[df["model"] == main_model].sort_values("group_id")
    print(f"\n绘图使用模型：{main_model}")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    x = np.arange(len(d))
    labels = [f"G{int(g)}" for g in d["group_id"]]

    def panel(ax, col, title, ylabel):
        if f"{col}_mean" not in d.columns:
            ax.axis("off")
            return
        y = d[f"{col}_mean"].to_numpy(float)
        lo = d.get(f"{col}_lo", pd.Series(np.full(len(d), np.nan))).to_numpy(float)
        hi = d.get(f"{col}_hi", pd.Series(np.full(len(d), np.nan))).to_numpy(float)
        yerr = np.vstack([np.nan_to_num(y - lo), np.nan_to_num(hi - y)])
        ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=5, color="steelblue")
        ax.axhline(0, color="gray", ls="--", lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45)
        ax.set_ylabel(ylabel)
        ax.set_title(title)

    panel(axes[0, 0], "delta_v", f"Δv = v_self − v_stranger（{main_model}）", "Δv")
    if "v_self_mean" in d.columns:
        w = 0.36
        axes[0, 1].bar(x - w / 2, d["v_self_mean"], w, label="Self", alpha=.85)
        axes[0, 1].bar(x + w / 2, d["v_stranger_mean"], w, label="Stranger", alpha=.85)
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(labels, rotation=45)
        axes[0, 1].axhline(0, color="gray", ls="--", lw=1)
        axes[0, 1].set_ylabel("v")
        axes[0, 1].set_title("漂移率（正确性编码）")
        axes[0, 1].legend()
    panel(axes[1, 0], "delta_b", f"Δb 匹配键偏向差（{main_model}）", "Δb")
    if "b_self_mean" in d.columns and d["b_self_mean"].notna().any():
        w = 0.36
        axes[1, 1].bar(x - w / 2, d["b_self_mean"], w, label="Self", alpha=.85)
        axes[1, 1].bar(x + w / 2, d["b_stranger_mean"], w, label="Stranger", alpha=.85)
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(labels, rotation=45)
        axes[1, 1].axhline(0, color="gray", ls="--", lw=1)
        axes[1, 1].set_ylabel("b")
        axes[1, 1].set_title("匹配键偏向 b = (z_匹配 − z_不匹配)/2")
        axes[1, 1].legend()
    else:
        axes[1, 1].axis("off")

    plt.tight_layout()
    fig_path = FIG_DIR / f"ddm_params_{main_model}.png"
    plt.savefig(fig_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"图 -> {fig_path}")
    print("Step 3 完成")


if __name__ == "__main__":
    main()
