# -*- coding: utf-8 -*-
"""auto-generated from the S3 notebook: 按顺序执行全部代码单元（用于验证 notebook 能跑通）"""
import matplotlib
matplotlib.use('Agg')

# ===== 0. 环境与路径 =====
import sys, json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 自动向上找仓库根（含 1_Code/DDM_Core 的那一层），这样从任何目录打开都能跑
def find_repo(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "1_Code" / "DDM_Core" / "mapping.py").exists():
            return p
    raise RuntimeError("找不到仓库根（应包含 1_Code/DDM_Core/mapping.py）")

REPO = find_repo(Path.cwd())
CORE = REPO / "1_Code" / "DDM_Core"
sys.path.insert(0, str(CORE))
print("仓库根：", REPO)

from mapping import MappingParams, drift_magnitude, trial_params   # noqa: E402
from simulate import build_design, draw_subject_params             # noqa: E402
from twophase import simulate_euler_subject                        # noqa: E402

print("numpy", np.__version__, "| pandas", pd.__version__)

# ----------------------------------------------------------------------

# ===== 1. 真值参数 =====
TRUTH = MappingParams(
    P_ref=30.0, T_ref=0.10, W_ref=1.20,
    d_ref=0.70, beta_P=0.35, tau_P=30.0,
    beta_T=0.55, tau_T=0.080,
    beta_S=0.16, beta_ST=0.10, beta_SP=0.0,
    w_model="W1", a_ref=2.00, delta_a=0.55, tau_a=0.70,
    t0=0.22, z_ratio=0.50,
)
RHO = 0.80          # 掩蔽后证据保留率；设成 1.0 即退化为单阶段 DDM（M-T3）

# 被试间随机效应（个体差异）：这些 SD 决定「人跟人有多不一样」
SUBJECT_SD = {"d_ref": 0.15, "beta_S": 0.10, "a_ref": 0.25, "t0": 0.030}

# 设计变量
P_LEVELS = [0.0, 8.0, 32.0, 120.0]                    # 组间：练习量
T_LEVELS = [0.0333, 0.0833, 0.14999, 0.24998]         # 被试内：呈现时长（s）
W_LEVELS = [0.79998, 1.19990, 1.79990]                # 被试内：反应期限（s）
N_REP    = 12                                          # 每单元重复次数
TRIALS_PER_SUBJECT = len(T_LEVELS) * len(W_LEVELS) * 2 * 2 * N_REP
print("每被试试次 =", TRIALS_PER_SUBJECT)

# 派生量：每个 P 水平、每个 T 水平的漂移真值（看设计有没有真的动起来）
print("\n[每个 P 水平的漂移]（T = T_ref = 100 ms, 他人条件）")
for p in P_LEVELS:
    d = float(drift_magnitude(np.array([p]), TRUTH.T_ref, 0, TRUTH)[0])
    print(f"  P={p:6.1f} → d = {d:.3f}")

print("\n[每个 T 水平的漂移]（P = P_ref = 30, 他人条件）")
for t in T_LEVELS:
    d = float(drift_magnitude(np.array([TRUTH.P_ref]), np.array([t]), 0, TRUTH)[0])
    print(f"  T={t*1000:6.1f} ms → d = {d:.3f}")

# ----------------------------------------------------------------------

# ===== 2. 设计网格 + 逐试次参数检查 =====
design = build_design(P_LEVELS[0], T_LEVELS, W_LEVELS, N_REP)   # 先用 P=0 看结构
df_design = pd.DataFrame({k: v for k, v in design.items()})
print("单元数：", df_design.groupby(["T", "W", "is_self", "is_match"]).size().describe()[["count", "min", "max"]].to_dict())

tp = trial_params(design, TRUTH)
print("\n逐试次参数的前 8 行（v=漂移, a=边界, z=起点, t0=非决策时间）：")
pd.DataFrame({"P": design["P"][:8], "T": design["T"][:8], "W": design["W"][:8],
              "is_self": design["is_self"][:8].astype(int),
              "v": np.round(tp["v"][:8], 4), "a": np.round(tp["a"][:8], 4),
              "z": np.round(tp["z"][:8], 4),
              "t0": np.round(np.full(8, float(tp["t0"])), 4)})

# ----------------------------------------------------------------------

# ===== 3. 单个被试：生成试次级数据 =====
rng = np.random.default_rng(20261021)
sim = simulate_euler_subject(design, TRUTH, RHO, rng, dt=5e-5)

print("返回的键：", list(sim.keys()))
print("RT 前 5 个（秒，未反应为 NaN）：", np.round(sim["rt"][:5], 4))
print("侧别前 5 个（1=上/0=下）：", sim["side"][:5])
print("遗漏前 5 个：", sim["omission"][:5])
print(f"\n该被试：准确率 {np.mean(sim['side'][sim['omission']==0] == np.asarray(design['is_match'])[sim['omission']==0]):.3f}"
      f"｜遗漏率 {sim['omission'].mean():.3f}"
      f"｜中位 RT {np.nanmedian(sim['rt'])*1000:.1f} ms")

# ----------------------------------------------------------------------

# ===== 4. 多名被试：加入个体差异（随机效应） =====
N_SUBJECTS = 8           # 每 P 组 2 名；想多要就改这里
SEED = 20261021

def make_subject_rows(subject_id: int, group_id: int, P: float, p_sub: MappingParams,
                      rng: np.random.Generator) -> pd.DataFrame:
    """生成一名被试的全部试次（长表）。"""
    d = build_design(P, T_LEVELS, W_LEVELS, N_REP)
    s = simulate_euler_subject(d, p_sub, RHO, rng, dt=5e-5)
    tp = trial_params(d, p_sub)
    rt_s = s["rt"]
    om = s["omission"]
    # CorrectKey：Shape=circle → 上侧（f）；square → 下侧（j）
    # 这里用 is_match 的配对关系近似（模拟数据只需结构自洽）
    is_match = np.asarray(d["is_match"]).astype(int)
    is_self = np.asarray(d["is_self"]).astype(int)
    return pd.DataFrame({
        "subjectID": subject_id,
        "groupID": group_id,
        "trialID": np.arange(1, rt_s.size + 1),
        "P": P,
        "T": np.asarray(d["T"]),
        "W": np.asarray(d["W"]),
        "is_self": is_self,
        "is_match": is_match,
        "v": tp["v"],            # 带符号（+ = 上侧为「正确侧」）
        "v_abs": np.abs(tp["v"]),  # 漂移幅度（论文里说的 d）
        "a": tp["a"],
        "z": tp["z"],
        "t0": np.full(rt_s.size, float(tp["t0"])),
        "rho": RHO,
        "rt_s": rt_s,
        "rt_ms": rt_s * 1000.0,
        "side": s["side"],
        "omission": om,
        "responded": 1 - om,
    })

rows, subj_rows = [], []
rng = np.random.default_rng(SEED)
for i in range(N_SUBJECTS):
    group_id = i % len(P_LEVELS)
    P = P_LEVELS[group_id]
    p_sub = draw_subject_params(TRUTH.replace(beta_P=TRUTH.beta_P), rng, sd=SUBJECT_SD, mode="truncate")
    rows.append(make_subject_rows(i + 1, group_id + 1, P, p_sub, rng))
    subj_rows.append({"subjectID": i + 1, "groupID": group_id + 1, "P": P,
                      "d_ref": p_sub.d_ref, "beta_S": p_sub.beta_S,
                      "a_ref": p_sub.a_ref, "t0": p_sub.t0})

trials = pd.concat(rows, ignore_index=True)
subject_params = pd.DataFrame(subj_rows)
print("试次总数：", len(trials))
print(trials.head(5).to_string())
print("\n被试层真值：")
print(subject_params.round(4).to_string(index=False))

# ----------------------------------------------------------------------

# ===== 5. 检查生成的数据有没有「像数据」 =====
g = trials[trials.omission == 0]
acc = (g.side == np.where(g.is_match == 1, 1, 0)).mean()

print(f"总准确率 {acc:.3f}｜总遗漏率 {trials.omission.mean():.3f}")
cell = (trials.groupby(["P", "T"], as_index=False)
        .agg(n=("rt_ms", "size"), omission=("omission", "mean"),
             rt_med=("rt_ms", "median")))
recs = []
for (p, t), sub in trials.groupby(["P", "T"]):
    ok = sub.omission == 0
    acc_p = float((sub.side[ok] == np.where(sub.is_match[ok] == 1, 1, 0)).mean()) if ok.any() else np.nan
    recs.append({"P": p, "T": t, "acc": acc_p})
cell = cell.merge(pd.DataFrame(recs), on=["P", "T"], how="left")
print("\n[P × T 单元汇总]")
print(cell.round(3).to_string(index=False))

# ----------------------------------------------------------------------

# ===== 6. 落盘（CSV） =====
OUT = REPO / "2_Data" / "Real_Data" / "_SYNTHETIC_NOTEBOOK"
OUT.mkdir(parents=True, exist_ok=True)

trials.to_csv(OUT / "trial_level.csv", index=False, encoding="utf-8-sig")
subject_params.to_csv(OUT / "subject_params.csv", index=False, encoding="utf-8-sig")

# --- 与真实实验同列名的宽表（每被试 576 行 + 表头） ---
def to_experiment_style(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for sid, sub in df.groupby("subjectID"):
        sub = sub.sort_values("trialID")
        onset = 1000.0 + np.arange(len(sub)) * 3.2 + np.random.default_rng(sid).normal(0, 0.05, len(sub))
        dur = sub["T"].to_numpy()
        responded = (sub["omission"].to_numpy() == 0)
        shape = np.where(sub["is_match"].to_numpy() == 1, "circle", "square")
        key = np.where(shape == "circle", "f", "j")
        resp = np.where(sub["side"].to_numpy() == 1, "f", "j")
        resp = np.where(responded, resp, "none")
        out.append(pd.DataFrame({
            "groupID": sub["groupID"].to_numpy(),
            "subjectID": sid,
            "gender": 2, "age": 22, "handedness": 2,
            "stage": "formal",
            "trialID": sub["trialID"].to_numpy(),
            "P": sub["P"].to_numpy() / 120.0,          # 与真实记录一致：P 归一化到 0–1
            "T": dur,
            "W": sub["W"].to_numpy(),
            "Shape": shape,
            "Label": np.where(sub["is_self"].to_numpy() == 1, "self", "stranger"),
            "CorrectKey": key,
            "Response": resp,
            "RT": sub["rt_s"].to_numpy(),
            "Correct": np.where(responded, (key == resp).astype(int), 0),
            "block": 1,
            "premature_press": 0,
            "timeout": sub["omission"].to_numpy(),
            "responded_by_deadline": responded.astype(int),
            "stimulus_onset_actual": onset,
            "stimulus_offset_actual": onset + dur,
            "mask_onset_actual": onset + dur,
            "stimulus_dur_actual": dur,
            "stimulus_frames": np.round(dur * 60).astype(int),
        }))
    return pd.concat(out, ignore_index=True)

exp_style = to_experiment_style(trials)
exp_style.to_csv(OUT / "trials_experiment_style.csv", index=False, encoding="utf-8-sig")
cell_summary = cell.copy()
cell_summary.to_csv(OUT / "cell_summary.csv", index=False, encoding="utf-8-sig")

print("已写出：")
for p in sorted(OUT.glob("*.csv")):
    print(f"  {p.name:32s} {p.stat().st_size/1024:8.1f} KB")

# ----------------------------------------------------------------------

# ===== 7. 三张图（看数据长得对不对） =====
from matplotlib import font_manager
_cands = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC"]
_have = {f.name for f in font_manager.fontManager.ttflist}
for _c in _cands:
    if _c in _have:
        plt.rcParams["font.sans-serif"] = [_c]
        break
plt.rcParams["axes.unicode_minus"] = False

fig, axes = plt.subplots(1, 3, figsize=(16, 4.2), dpi=130)

# (a) RT 分布（按 T）
ax = axes[0]
for t in T_LEVELS:
    r = trials[(trials["T"] == t) & (trials.omission == 0)]["rt_ms"].dropna()
    ax.hist(r, bins=40, alpha=0.45, label=f"T={t*1000:.0f} ms")
ax.set_xlabel("RT (ms)"); ax.set_ylabel("试次数"); ax.set_title("RT 分布（只看已反应）"); ax.legend(fontsize=8)

# (b) 正确率 / 遗漏率随 W
ax = axes[1]
for t in T_LEVELS:
    sub = trials[trials["T"] == t]
    xs, accs, oms = [], [], []
    for w in W_LEVELS:
        s = sub[sub.W == w]; ok = s.omission == 0
        if not ok.any():
            continue
        xs.append(w * 1000)
        accs.append((s.side[ok] == np.where(s.is_match[ok] == 1, 1, 0)).mean())
        oms.append(s.omission.mean())
    ax.plot(xs, accs, "-o", label=f"正确率 T={t*1000:.0f}")
    ax.plot(xs, oms, "--s", alpha=0.6, label=f"遗漏率 T={t*1000:.0f}")
ax.set_xlabel("期限 W (ms)"); ax.set_ylabel("概率"); ax.set_title("正确率 / 遗漏率"); ax.legend(fontsize=7)

# (c) 各 P 组的漂移真值
ax = axes[2]
d_model = np.array([float(drift_magnitude(np.array([p]), TRUTH.T_ref, 0, TRUTH)[0]) for p in P_LEVELS])
ax.bar(range(1, len(P_LEVELS) + 1), d_model, alpha=0.45, color="0.6", label="模型真值（T=T_ref）")
for i, (gid, sub) in enumerate(trials.groupby("groupID"), start=1):
    subj_means = sub.groupby("subjectID").v_abs.mean().to_numpy()
    ax.scatter([i] * subj_means.size, subj_means, color="C3", zorder=3, s=18)
ax.set_xticks(range(1, len(P_LEVELS) + 1))
ax.set_xticklabels([f"P={p:.0f}" for p in P_LEVELS], fontsize=8)
ax.set_xlabel("组（P 水平）"); ax.set_ylabel("平均漂移幅度 |v|")
ax.set_title("练习量 → 漂移：灰柱=真值，红点=各被试实测均值")

fig.tight_layout()
fig.savefig(OUT / "fig_trial_sim_check.png", dpi=150)
plt.show()
print("图已存：", OUT / "fig_trial_sim_check.png")

# ----------------------------------------------------------------------
