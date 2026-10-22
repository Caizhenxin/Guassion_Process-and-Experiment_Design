"""SPE 的函数形式该选哪一支？——7 个候选机制在同一模拟器上的对照（D117）。

背景：λ 天花板族（`d_self = d_other + Δ_S[1 − (1−λ)f_P]`）只解决了「练习让 SPE 收缩」的**方向**，
它并没有让 SPE 在数据里变得更**显眼**——因为在 P=0 处它和加法常数模型完全等价。
于是要问：换一个**链接函数 / 作用通道**，能不能同时做到
  ① P=0 处的 SPE 更大（更可见、更好检验）；
  ② 仍能解释长期练习下 SPE 收缩（HuYQ：−3.30 ms/阶段，p=.00029）。

本脚本把 7 支候选放在同一个 Euler 模拟器、同一群被试、同一噪声流（共同随机数）上比较：

| 代号 | 机制 | 数学形式 | 预期签名 |
|---|---|---|---|
| `const` | 加法常数（现行主模型） | `v_S = v_O + Δ` | 正确率↑、RT 差随分位放大、与练习无关 |
| `ceiling` | λ 天花板族 | `v_S = v_O + Δ[1−(1−λ)f_P]` | 同上，但随练习收缩到 `λΔ` |
| `selfsat` | 自我单独饱和 | `v_S = v_O + Δ·e^{−P/τ_S}` | 收缩更快、无下限 |
| `power` | 幂律衰减 | `v_S = v_O + Δ(1+P)^{−α}` | 长训练尺度更贴合（练习文献偏幂律） |
| `ratio` | 乘性比例（旧项目口径） | `v_S = v_O(1+γ)` | **绝对差随练习变大**（方向相反） |
| `gate` | 加工速率通道 | `v_S = r_S·v_O`，噪声 ×√r | RT 整体加速、正确率不变；练习加速后 ms 差自动缩小 |
| `noise` | 噪声通道 | `c_S = c_O·(1−δ)` | 正确率↑为主、RT 差很小 |

判据：
- **可见度** = 该机制在 P=0 给出的 `|Δacc|` 与 `|ΔRT| / SD_RT`；
- **可辨识性** = 在 n=40/组 下关键参数的 `SE`（用 `SD_between / |dSPE/dθ| / √n` 近似）；
- **方向一致** = SPE 随练习是否下降（与 HuYQ 的符号一致）。

产物：`3_Figures/_compare/fig11_spe_families.png`、
`2_Data/Generate_Data/_families/families.csv`、`families_meta.json`。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

OUT = ROOT / "2_Data" / "Generate_Data" / "_families"
FIG_OUT = ROOT / "3_Figures" / "_compare"

# —— 基线（与 gen_model_data.GEN_TRUTH / practice_lambda 同一口径）——
V_OTHER0 = 0.80         # 未练习时他人试次的漂移
GAIN_P = 0.35           # 练习把他人漂移抬多少
TAU_P = 30.0            # 练习饱和常数
DELTA = 0.30            # P=0 处的自我优势（漂移单位）
A_REF = 1.566
T0 = 0.19
RHO = 0.8
T_STIM = 0.15
W_DEADLINE = 1.8
Z_RATIO = 0.5
P_GRID = (0.0, 8.0, 32.0, 120.0)


def f_practice(p: float, tau: float = TAU_P) -> float:
    return 1.0 - float(np.exp(-p / tau))


def v_other(p: float) -> float:
    return V_OTHER0 + GAIN_P * f_practice(p)


# —— 每支机制：给定练习量 P，返回两条件的 (漂移, 边界, t0, 噪声尺度, 速率) ——
def spec_const(p: float) -> dict:
    v_o = v_other(p)
    return {"self": (v_o + DELTA, A_REF, T0, 1.0, 1.0),
            "other": (v_o, A_REF, T0, 1.0, 1.0)}


def spec_ceiling(p: float, lam: float = 0.5) -> dict:
    v_o = v_other(p)
    dv = DELTA * (1.0 - (1.0 - lam) * f_practice(p))
    return {"self": (v_o + dv, A_REF, T0, 1.0, 1.0),
            "other": (v_o, A_REF, T0, 1.0, 1.0)}


def spec_selfsat(p: float, tau_s: float = 20.0) -> dict:
    v_o = v_other(p)
    dv = DELTA * float(np.exp(-p / tau_s))
    return {"self": (v_o + dv, A_REF, T0, 1.0, 1.0),
            "other": (v_o, A_REF, T0, 1.0, 1.0)}


def spec_power(p: float, alpha: float = 0.45, scale: float = 8.0) -> dict:
    """幂律衰减：Δ·(1+P/scale)^{−α}；scale 给的是「每单位练习的试次尺度」。"""
    v_o = v_other(p)
    dv = DELTA * (1.0 + p / scale) ** (-alpha)
    return {"self": (v_o + dv, A_REF, T0, 1.0, 1.0),
            "other": (v_o, A_REF, T0, 1.0, 1.0)}


def spec_ratio(p: float, gamma: float = 0.33) -> dict:
    v_o = v_other(p)
    return {"self": (v_o * (1.0 + gamma), A_REF, T0, 1.0, 1.0),
            "other": (v_o, A_REF, T0, 1.0, 1.0)}


def spec_gate(p: float, r_self: float = 1.10, g_rate: float = 0.45) -> dict:
    """加工速率通道：自我快 r_self 倍；练习把整体速率抬 g_rate。

    ⚠️ 噪声**不能**再手乘 √r：`simulate` 内部已经按 `sqrt(rate)` 缩放噪声（时间压缩的
    正确做法）。第一版在外部又乘了一次 √r，等价于把噪声放大成 r（信噪比反而变差），
    结果符号反了（自我更慢更不准）。
    """
    r_o = 1.0 + g_rate * f_practice(p)
    v_o = V_OTHER0
    return {"self": (v_o, A_REF, T0, 1.0, r_o * r_self),
            "other": (v_o, A_REF, T0, 1.0, r_o)}


def spec_noise(p: float, delta: float = 0.10, g_noise: float = 0.20) -> dict:
    """噪声通道：自我噪声低 delta；练习把两条件噪声都降 g_noise。"""
    c_o = 1.0 - g_noise * f_practice(p)
    v_o = v_other(p)
    return {"self": (v_o, A_REF, T0, c_o * (1.0 - delta), 1.0),
            "other": (v_o, A_REF, T0, c_o, 1.0)}


def spec_gate_drift(p: float, r_self: float = 1.06, dv: float = 0.15,
                    g_rate: float = 0.45) -> dict:
    """**混合**：自我同时「快一点」（速率）× 「准一点」（漂移小幅抬高）。

    这是本脚本给出的推荐支：单靠漂移的 RT 差只有 20 出头 ms，单靠速率没有正确率差；
    两者各取一半，既能给出量级接近文献的 RT 差，又保留正确率差，而且 ms 差会随练习
    自动缩小（因为 RT 分母变小了），不需要额外的 λ。
    """
    r_o = 1.0 + g_rate * f_practice(p)
    v_o = v_other(p)
    return {"self": (v_o + dv, A_REF, T0, 1.0, r_o * r_self),
            "other": (v_o, A_REF, T0, 1.0, r_o)}


FAMILIES = {
    "const": spec_const,
    "ceiling": spec_ceiling,
    "selfsat": spec_selfsat,
    "power": spec_power,
    "ratio": spec_ratio,
    "gate": spec_gate,
    "gate_drift": spec_gate_drift,
    "noise": spec_noise,
}

LABEL = {
    "const": "加法常数（现行）",
    "ceiling": "λ 天花板",
    "selfsat": "自我单独饱和",
    "power": "幂律衰减",
    "ratio": "乘性比例（旧口径）",
    "gate": "加工速率通道",
    "gate_drift": "速率 + 漂移（推荐）",
    "noise": "噪声通道",
}


def simulate(v: float, a: float, t0: float, rng, n_trials: int,
             noise_scale: float = 1.0, rate: float = 1.0,
             dt: float = 1e-4, chunk: int = 250):
    """两阶段阶跃 Euler；`rate` 同时缩放漂移与时间进程（噪声按 √rate）。"""
    n_steps = int(round(W_DEADLINE / dt)) + 1
    t = np.arange(n_steps) * dt
    step = np.where(t <= T_STIM, v, RHO * v) * rate
    noise_sd = np.sqrt(dt) * noise_scale * np.sqrt(rate)
    out = np.full(n_trials, np.nan)
    side = np.zeros(n_trials, int)
    for s in range(0, n_trials, chunk):
        m = min(chunk, n_trials - s)
        noise = rng.normal(0.0, noise_sd, size=(m, n_steps))
        xs = Z_RATIO * a + np.cumsum(step[None, :] * dt + noise, axis=1)
        up = xs >= a
        dn = xs <= 0.0
        hit = up | dn
        any_hit = hit.any(axis=1)
        idx = np.argmax(hit, axis=1)
        rows = np.arange(m)
        rt = np.where(any_hit, t[idx] / rate + t0, np.nan)
        out[s:s + m] = rt
        side[s:s + m] = np.where(any_hit, np.where(up[rows, idx], 1, -1), 0)
    return out, side


def run(family: str, p_levels, n_subjects: int, n_trials: int, seed: int,
        v_sd: float = 0.10, a_sd: float = 0.06) -> pd.DataFrame:
    spec_fn = FAMILIES[family]
    base = np.random.default_rng(seed)
    rows = []
    for sid in range(n_subjects):
        v_sd_i = base.normal(0.0, v_sd)
        a_sd_i = base.normal(0.0, a_sd)
        sub_seed = seed * 10000 + sid
        for p in p_levels:
            sp = spec_fn(p)
            for ident in (0, 1):
                v, a, t0, c, rate = sp["self"] if ident else sp["other"]
                rng = np.random.default_rng(sub_seed)   # 同一被试两条件同一噪声流
                rt, side = simulate(v + v_sd_i, a + a_sd_i, t0, rng,
                                    n_trials=n_trials, noise_scale=c, rate=rate)
                ok = ~np.isnan(rt)
                rows.append(pd.DataFrame({
                    "family": family, "subject": f"{family}-{sid}",
                    "is_self": ident, "P": p,
                    "rt_ms": rt[ok] * 1000.0,
                    "correct": (side[ok] == 1).astype(int),
                }))
    return pd.concat(rows, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    qs = (0.1, 0.3, 0.5, 0.7, 0.9)
    rows = []
    for (fam, p), sub in df.groupby(["family", "P"], sort=False):
        o, s = sub[sub.is_self == 0], sub[sub.is_self == 1]
        rec = {"family": fam, "P": p,
               "acc_other": float(o.correct.mean()), "acc_self": float(s.correct.mean()),
               "rt_other_med": float(np.median(o.rt_ms)), "rt_self_med": float(np.median(s.rt_ms)),
               "sd_rt": float(np.std(pd.concat([o.rt_ms, s.rt_ms])))}
        rec["d_acc"] = rec["acc_self"] - rec["acc_other"]
        rec["d_rt_med"] = rec["rt_other_med"] - rec["rt_self_med"]
        qo = np.quantile(o.rt_ms, qs)
        qs_s = np.quantile(s.rt_ms, qs)
        rec["d_rt_slope"] = float((qo - qs_s)[-1] - (qo - qs_s)[0])
        rec["vis_acc"] = abs(rec["d_acc"])
        rec["vis_rt"] = abs(rec["d_rt_med"]) / rec["sd_rt"]
        rows.append(rec)
    return pd.DataFrame(rows)


def sensitivity(family: str, n_subjects: int, n_trials: int, seed: int,
                sd_between: float = 17.0) -> dict:
    """关键参数的 |d SPE / dθ|（P=0→32 的差分），再换 SE(θ)@n=40。"""
    key = {"const": None, "ceiling": 0.5, "selfsat": 20.0, "power": 0.45,
           "ratio": 0.33, "gate": 1.10, "gate_drift": 1.06, "noise": 0.10}
    span = {"const": 0.15, "ceiling": 0.35, "selfsat": 8.0, "power": 0.25,
            "ratio": 0.12, "gate": 0.05, "gate_drift": 0.04, "noise": 0.04}
    if key[family] is None:
        return {"family": family, "param": "-", "dSPE_dtheta": float("nan"),
                "se_at_40": float("nan")}
    lo, hi = key[family] - span[family], key[family] + span[family]
    fam = dict(FAMILIES)
    vals = []
    for th in (lo, hi):
        fam[family] = (lambda p, th=th, f=family: _override(f, p, th))
        d = run_via(fam[family], n_subjects, n_trials, seed)
        sm = summarize(d)
        vals.append(float(sm.loc[sm.P == 32.0, "d_rt_med"].iloc[0]))
    slope = abs(vals[1] - vals[0]) / (hi - lo)      # ms per unit θ
    se = sd_between / (slope * np.sqrt(40.0)) if slope > 0 else float("inf")
    return {"family": family, "param": f"{family} θ∈[{lo:.2f},{hi:.2f}]",
            "dSPE_dtheta": slope, "se_at_40": se}


def _override(family: str, p: float, th: float) -> dict:
    if family == "ceiling":
        return spec_ceiling(p, lam=th)
    if family == "selfsat":
        return spec_selfsat(p, tau_s=th)
    if family == "power":
        return spec_power(p, alpha=th)
    if family == "ratio":
        return spec_ratio(p, gamma=th)
    if family == "gate":
        return spec_gate(p, r_self=th)
    if family == "gate_drift":
        return spec_gate_drift(p, r_self=th)
    if family == "noise":
        return spec_noise(p, delta=th)
    return spec_const(p)


def run_via(spec_fn, n_subjects: int, n_trials: int, seed: int) -> pd.DataFrame:
    """用给定的 spec 函数跑一个 family（用于有限差分）。"""
    base = np.random.default_rng(seed)
    rows = []
    for sid in range(n_subjects):
        v_sd_i = base.normal(0.0, 0.10)
        a_sd_i = base.normal(0.0, 0.06)
        sub_seed = seed * 10000 + sid
        for p in (0.0, 32.0):
            sp = spec_fn(p)
            for ident in (0, 1):
                v, a, t0, c, rate = sp["self"] if ident else sp["other"]
                rng = np.random.default_rng(sub_seed)
                rt, side = simulate(v + v_sd_i, a + a_sd_i, t0, rng,
                                    n_trials=n_trials, noise_scale=c, rate=rate)
                ok = ~np.isnan(rt)
                rows.append(pd.DataFrame({
                    "family": "tmp", "subject": f"tmp-{sid}", "is_self": ident, "P": p,
                    "rt_ms": rt[ok] * 1000.0, "correct": (side[ok] == 1).astype(int)}))
    return pd.concat(rows, ignore_index=True)


def make_figure(sm: pd.DataFrame, sens: pd.DataFrame, fig_path: Path) -> None:
    from make_figures import setup_matplotlib
    plt, _ = setup_matplotlib("zh")

    colors = {"const": "#c0392b", "ceiling": "#e67e22", "selfsat": "#8e44ad",
              "power": "#2980b9", "ratio": "#7f8c8d", "gate": "#16a085",
              "gate_drift": "#2c3e50", "noise": "#d4a017"}
    order = ["const", "ceiling", "selfsat", "power", "ratio", "gate",
             "gate_drift", "noise"]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))

    ax = axes[0]
    for fam in order:
        sub = sm[sm.family == fam].sort_values("P")
        ax.plot(sub.P, sub.d_rt_med, "o-", color=colors[fam], lw=1.8, ms=5,
                label=LABEL[fam])
    ax.axhline(0, color="0.5", lw=0.8, ls=":")
    ax.set_xlabel("练习试次数 P"); ax.set_ylabel("SPE（他人 − 自我，RT 中位 ms）")
    ax.set_title("① RT 侧 SPE 随练习的走向")
    ax.legend(fontsize=7.5, ncol=2)

    ax = axes[1]
    for fam in order:
        sub = sm[sm.family == fam].sort_values("P")
        ax.plot(sub.P, sub.d_acc * 100, "o-", color=colors[fam], lw=1.8, ms=5)
    ax.axhline(0, color="0.5", lw=0.8, ls=":")
    ax.set_xlabel("练习试次数 P"); ax.set_ylabel("SPE（自我 − 他人，正确率 pp）")
    ax.set_title("② 正确率侧 SPE 随练习的走向")

    ax = axes[2]
    p0 = sm[sm.P == 0.0].set_index("family")
    xs = [p0.loc[f, "vis_rt"] for f in order]
    ys = [p0.loc[f, "vis_acc"] * 100 for f in order]
    # 同一 (x, y) 的机制在 P=0 处完全等价 ⇒ 合并标注（这本身就是要传达的结论之一）
    groups: dict[tuple[float, float], list[str]] = {}
    for f, x, y in zip(order, xs, ys):
        groups.setdefault((round(x, 3), round(y, 2)), []).append(f)
    offs = {(0.077, 6.37): (-186, -22), (0.057, 5.74): (10, -4),
            (0.187, 0.19): (-118, 16), (0.155, 3.21): (10, -6),
            (0.142, 4.21): (10, 8)}
    for (x, y), fams in groups.items():
        ax.scatter(x, y, s=110, color=colors[fams[0]], edgecolor="white", zorder=3)
        tag = " / ".join(LABEL[f] for f in fams)
        if len(fams) > 1:
            tag += "（P=0 完全同值）"
        ax.annotate(tag, (x, y), fontsize=8,
                    xytext=offs.get((x, y), (8, 6)), textcoords="offset points")
    ax.set_xlabel("RT 可见度 = |ΔRT| / SD(RT)")
    ax.set_ylabel("正确率可见度（pp）")
    ax.set_title("③ P=0 处的可见度：换链接函数不改变 P=0，换通道才改变")
    ax.grid(alpha=0.3)
    ax.set_xlim(0.02, 0.22)
    ax.margins(y=0.18)

    fig.suptitle("SPE 的 8 支候选机制：同一模拟器、同一人群、同一噪声流（模拟，非人类被试）",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"[fig] {fig_path}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    frames = []
    for fam in FAMILIES:
        d = run(fam, P_GRID, n_subjects=12, n_trials=240, seed=20261022)
        frames.append(d)
        print(f"[{fam}] {len(d)} 行  ({time.time()-t0:.0f}s)")
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(OUT / "trials_families.csv", index=False, encoding="utf-8-sig")
    sm = summarize(df)
    sm.to_csv(OUT / "families.csv", index=False, encoding="utf-8-sig")
    print(sm.pivot_table(index="family", columns="P",
                         values=["d_rt_med", "d_acc"]).round(4).to_string())

    sens = []
    for fam in ("ceiling", "selfsat", "power", "ratio", "gate", "gate_drift", "noise"):
        rec = sensitivity(fam, n_subjects=8, n_trials=200, seed=20261022)
        sens.append(rec)
        print(f"[sens] {fam}: dSPE/dθ = {rec['dSPE_dtheta']:.1f} ms/unit, "
              f"SE@40 = {rec['se_at_40']:.3f}")
    sdf = pd.DataFrame(sens)
    sdf.to_csv(OUT / "families_sensitivity.csv", index=False, encoding="utf-8-sig")

    meta = {"p_grid": list(P_GRID), "n_subjects": 12, "n_trials": 240,
            "v_other0": V_OTHER0, "gain_p": GAIN_P, "tau_p": TAU_P, "delta": DELTA,
            "a_ref": A_REF, "t0": T0, "rho": RHO, "t_stim": T_STIM,
            "w_deadline": W_DEADLINE, "seed": 20261022,
            "note": "同一被试两条件同一噪声流（共同随机数）；rt 为已响应试次"}
    (OUT / "families_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    make_figure(sm, sdf, FIG_OUT / "fig11_spe_families.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
