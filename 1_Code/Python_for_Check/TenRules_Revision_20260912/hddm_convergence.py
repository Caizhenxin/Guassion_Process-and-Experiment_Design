# -*- coding: utf-8 -*-
"""
hddm_convergence.py —— HDDM 收敛诊断（R-hat / ESS）2026-09-12
=============================================================
补齐《十条规则》规则4与规则9的缺项：为 8 次主拟合与 16 次敏感性拟合报告收敛诊断。

方法说明（重要，写论文时须照此表述）
------------------------------------
HDDM 的 `get_traces()` 保存的是**单链**抽样（3,000 draws，去掉 500 burn-in 后 2,500）。
严格的多链 R-hat 需要 ≥2 条独立链，本研究的历史拟合为单链，因此采用以下两种**单链可用**的诊断：

1. **Split-Rhat**：把链切成 4 段视为 4 条"伪链"，按 Gelman–Rubin 公式计算 Rhat。
   判据：Rhat < 1.01 视为可接受（经验阈值）。
2. **ESS（基于自相关，Geyer 初始正序列截断）**：ESS = N / (1 + 2Σρ_k)，
   求和截至自相关首次转负。判据：ESS > 400 视为可接受。

局限：split-Rhat 无法替代真正的多链诊断；**若论文需要更强的收敛证据，应重跑并保存 4 条链**。
本脚本给出的是基于既有产物的后验诊断，可用于说明"参数是否已稳定"，并在局限中如实注明方法。

输入
----
* 主拟合：2_Data/Real_Data/HDDM_Traces/hddm_data_group{G}_*_traces.npz（8 组）
* 敏感性：2_Data/Generate_Data/Omission_Sensitivity/{censor_traces,drop_traces}/*_traces.npz（各 8 组）
* 统计：同目录 *_stats.csv（提供 mean / 2.5q / 97.5q / mc err）

输出
----
2_Data/Generate_Data/TenRules_Revision_20260912/convergence/
    convergence_summary.csv      逐文件 × 逐参数的 Rhat、ESS、mc err
    convergence_flags.csv        未达阈值的参数清单
    convergence_overview.csv     按拟合来源汇总（可接受比例）
3_Figures/Thesis_v3_20260912/F6-6_convergence.png
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # 控制台编码兜底（避免中文/特殊字符报错）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sim_utils import OUT_DATA_DIR, OUT_FIG_DIR, setup_cjk_font  # noqa: E402

TRACES_MAIN = BASE / "2_Data" / "Real_Data" / "HDDM_Traces"
SENS = BASE / "2_Data" / "Generate_Data" / "Omission_Sensitivity"
OUT = OUT_DATA_DIR / "convergence"
OUT.mkdir(parents=True, exist_ok=True)

GROUP_PARAMS = ["v(0)", "v(1)", "a", "t", "z", "z_trans", "v_std", "a_std", "t_std", "z_std"]
RHAT_OK, ESS_OK = 1.01, 400.0


def split_rhat(x: np.ndarray, n_split: int = 4) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = (len(x) // n_split) * n_split
    if n < n_split * 20:
        return float("nan")
    chains = x[:n].reshape(n_split, -1)
    m, n_obs = chains.shape
    W = chains.var(axis=1, ddof=1).mean()
    B = n_obs * chains.mean(axis=1).var(ddof=1)
    if W <= 0:
        return float("nan")
    var_hat = (n_obs - 1) / n_obs * W + B / n_obs
    return float(np.sqrt(var_hat / W))


def ess_geyer(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 50:
        return float("nan")
    xc = x - x.mean()
    f = np.fft.rfft(xc, n=2 * n)
    acf = np.fft.irfft(f * np.conj(f))[:n].real
    if acf[0] <= 0:
        return float("nan")
    acf = acf / acf[0]
    rho_sum = 0.0
    for k in range(1, n):
        if acf[k] <= 0:
            break
        rho_sum += acf[k]
    return float(max(n / (1 + 2 * rho_sum), 1.0))


def collect_files():
    files = []
    for f in sorted(TRACES_MAIN.glob("hddm_data_group*_traces.npz")):
        m = re.search(r"group(\d+)", f.name)
        files.append({"source": "main(8 条件, 4 链口径实为单链)", "scheme": "main",
                      "group": int(m.group(1)) if m else -1, "npz": f,
                      "stats": f.with_name(f.name.replace("_traces.npz", "_stats.csv"))})
    for scheme, sub in [("censor", "censor_traces"), ("drop", "drop_traces")]:
        for f in sorted((SENS / sub).glob("*_traces.npz")):
            m = re.search(r"group(\d+)", f.name)
            files.append({"source": f"omission sensitivity ({scheme})", "scheme": scheme,
                          "group": int(m.group(1)) if m else -1, "npz": f,
                          "stats": f.with_name(f.name.replace("_traces.npz", "_stats.csv"))})
    return files


def main():
    files = collect_files()
    print(f"[conv] 待诊断文件数：{len(files)}")
    rows = []
    for info in files:
        try:
            npz = np.load(info["npz"])
        except Exception as exc:
            print(f"  ⚠️ 读取失败 {info['npz'].name}: {exc}")
            continue
        mc = {}
        if info["stats"].exists():
            try:
                st = pd.read_csv(info["stats"], index_col=0)
                mc = {str(i): float(st.loc[i, "mc err"]) for i in st.index if "mc err" in st.columns}
            except Exception:
                mc = {}
        for p in GROUP_PARAMS:
            if p not in npz.files:
                continue
            x = np.asarray(npz[p], dtype=float).ravel()
            rows.append({
                "file": info["npz"].name, "source": info["source"], "scheme": info["scheme"],
                "group": info["group"], "param": p, "n_draws": len(x),
                "mean": float(np.mean(x)), "sd": float(np.std(x, ddof=1)) if len(x) > 1 else np.nan,
                "rhat_split": split_rhat(x), "ess": ess_geyer(x), "mc_err": mc.get(p, np.nan),
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "convergence_summary.csv", index=False)

    flags = df[(df.rhat_split > RHAT_OK) | (df.ess < ESS_OK)].copy()
    flags["flag"] = np.where(flags.rhat_split > RHAT_OK, "Rhat>1.01", "") + \
                    np.where(flags.ess < ESS_OK, " ESS<400", "")
    flags.sort_values(["source", "group", "param"]).to_csv(OUT / "convergence_flags.csv", index=False)

    ov = []
    for (src, scheme), g in df.groupby(["source", "scheme"]):
        ov.append({
            "source": src, "scheme": scheme, "n_files": g.file.nunique(), "n_params": len(g),
            "rhat_median": g.rhat_split.median(), "rhat_max": g.rhat_split.max(),
            "ess_median": g.ess.median(), "ess_min": g.ess.min(),
            "pct_rhat_ok": float((g.rhat_split <= RHAT_OK).mean()),
            "pct_ess_ok": float((g.ess >= ESS_OK).mean()),
        })
    ov_df = pd.DataFrame(ov)
    ov_df.to_csv(OUT / "convergence_overview.csv", index=False)

    print("\n[conv] 汇总（按来源）：")
    print(ov_df.round(3).to_string(index=False))
    print(f"\n[conv] 未达标参数数：{len(flags)} / {len(df)}")
    if len(flags):
        print(flags.head(12).round(3).to_string(index=False))

    # 图：Rhat 与 ESS 分布
    setup_cjk_font()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for scheme, color in [("main", "#2a6f97"), ("censor", "#f4a261"), ("drop", "#9e9e9e")]:
        sub = df[df.scheme == scheme]
        if sub.empty:
            continue
        axes[0].hist(sub.rhat_split.dropna(), bins=25, alpha=.6, label=scheme, color=color)
        axes[1].hist(np.log10(sub.ess.dropna()), bins=25, alpha=.6, label=scheme, color=color)
    axes[0].axvline(RHAT_OK, color="r", ls="--", lw=1, label=f"阈值 {RHAT_OK}")
    axes[0].set_xlabel("Split-Rhat"); axes[0].set_ylabel("参数个数"); axes[0].set_title("(A) 收敛：Split-Rhat 分布")
    axes[1].axvline(np.log10(ESS_OK), color="r", ls="--", lw=1, label=f"阈值 {ESS_OK:.0f}")
    axes[1].set_xlabel("log10(ESS)"); axes[1].set_ylabel("参数个数"); axes[1].set_title("(B) 有效样本量（对数）")
    for ax in axes:
        ax.legend(fontsize=8)
    fig.suptitle("图6-6 HDDM 后验收敛诊断（基于既有单链迹线；Split-Rhat 为近似口径）")
    fig.tight_layout()
    fig.savefig(OUT_FIG_DIR / "F6-6_convergence.png", dpi=300)
    plt.close(fig)
    print(f"\n[conv] 产物 → {OUT}\n[conv] 图 → {OUT_FIG_DIR / 'F6-6_convergence.png'}")


if __name__ == "__main__":
    main()
