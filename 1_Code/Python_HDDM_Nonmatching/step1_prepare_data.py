# -*- coding: utf-8 -*-
"""Step 1: 由原始 CSV 生成 HDDM 输入（含 NonMatching）

2026-09-30 修订
==============
【修复 A】遗漏试次不再被伪造为"恰好在 deadline 按了错误键"
  旧实现：`rt = deadline`；`response = 1 − Correct`  ⇒ 遗漏恒落在"错误"一侧。
  实测代价：group3 有 1978/5200 = 38.0% 的试次被这样伪造，会把 v 系统性压向 0。
  新实现：遗漏试次的 `rt` 与 `response` 一律留空（NaN），只由 `omission` 列标记；
          主文件只含有反应的试次（**Drop 口径**），可直接喂给 HDDM；
          另存一份 omissions 文件，保留后续 omission-aware 似然所需的全部信息。

【新增 B】永久化的按键映射自检
  以「设计规则」（shape/label × 被试编号奇偶）推导 condition，
  再与「记录值」（CorrectKey == 该被试匹配键）逐行比对，不一致即报警。
  这道检查正是 2026-09-30 查出 `EXP_data_group2_11.csv` 100% 反转的那一个，
  现在固化进流程，防止同类问题再次静默通过。

输出
====
2_Data/Real_Data/HDDM_Ready_Nonmatching/
  hddm_data_group{gid}_P{}_T{}_W{}.csv      有反应试次（Drop 口径，HDDM 直接可用）
  hddm_omission_group{gid}_P{}_T{}_W{}.csv  仅遗漏试次（供 omission-aware 阶段）

主文件列
========
subj_idx | rt | response | correct | identity | condition | cell | deadline | omission
  response  : 1 = 判断为 Matching（上界）, 0 = 判断为 NonMatching（下界）  ← 按键编码
  correct   : 1 = 作答正确, 0 = 作答错误                                  ← 正确性编码
  condition : 1 = Matching 试次, 0 = NonMatching 试次
  cell      : identity * 2 + condition（0..3），用于 window 内估计身份×条件的参数
  deadline  : 反应窗口关闭时刻（秒，自刺激起点计）= T + W
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "2_Data" / "Real_Data" / "UnExtact" / "raw"
OUT_DIR = BASE_DIR / "2_Data" / "Real_Data" / "HDDM_Ready_Nonmatching"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 匹配键按被试编号轮换（与 1_Code/Python_for_Check/Visualization/app_server.py 一致）
MATCH_KEYS = ["f", "j", "j", "f"]


def correct_order(subject_id: int) -> dict:
    """设计规则：图形 → 与之绑定的身份标签。"""
    if subject_id % 2 == 0:
        return {"square": "self", "circle": "stranger"}
    return {"square": "stranger", "circle": "self"}


print("=" * 68)
print("Step 1: 生成 HDDM 输入数据（含 NonMatching，2026-09-30 修订版）")
print("=" * 68)

csv_files = sorted(RAW_DIR.glob("EXP_data_group*.csv"))
print(f"\n发现 {len(csv_files)} 个原始数据文件")
if not csv_files:
    raise SystemExit(f"未找到原始数据：{RAW_DIR}")

df_all = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
print(f"合并总行数: {len(df_all)}")

df_f = df_all[df_all["stage"] == "formal"].copy()
print(f"过滤 stage='formal' 后: {len(df_f)} 行")

# ------------------------------------------------------------------
# condition：设计规则与记录值双路推导 + 逐行比对
# ------------------------------------------------------------------
df_f["Shape"] = df_f["Shape"].astype(str).str.strip().str.lower()
df_f["Label"] = df_f["Label"].astype(str).str.strip().str.lower()
df_f["CorrectKey"] = df_f["CorrectKey"].astype(str).str.strip().str.lower()
bad_cell = ~df_f["Shape"].isin(["square", "circle"]) | ~df_f["Label"].isin(["self", "stranger"])
if bad_cell.any():
    raise SystemExit(f"发现 {int(bad_cell.sum())} 行 Shape/Label 取值异常，请先核查")

# 路 1：设计规则
order = df_f["subjectID"].map(correct_order)
cond_by_design = (df_f["Label"] == [o[s] for o, s in zip(order, df_f["Shape"])]).astype(int)

# 路 2：记录值（CorrectKey 是否等于该被试的匹配键）
match_key = df_f["subjectID"].map(lambda s: MATCH_KEYS[(int(s) - 1) % 4])
cond_by_record = (df_f["CorrectKey"] == match_key).astype(int)

mismatch = cond_by_design != cond_by_record
n_mismatch = int(mismatch.sum())
if n_mismatch:
    print(f"\n⚠️  按键映射自检未通过：{n_mismatch} 行设计规则与记录值不一致")
    bad_subj = (
        df_f.loc[mismatch]
        .groupby(["groupID", "subjectID"])
        .size()
        .rename("n_mismatch")
        .reset_index()
    )
    bad_subj["n_formal"] = bad_subj.apply(
        lambda r: int(((df_f["groupID"] == r["groupID"]) & (df_f["subjectID"] == r["subjectID"])).sum()),
        axis=1,
    )
    bad_subj["mismatch_pct"] = (bad_subj["n_mismatch"] / bad_subj["n_formal"] * 100).round(1)
    print(bad_subj.to_string(index=False))
    print("→ 请在 2_Data/Real_Data/Excluded/ 登记并移出这些被试后重跑本脚本。")
else:
    print(f"\n✅ 按键映射自检通过：{len(df_f)} 行全部一致（设计规则 == 记录值）")

df_f["condition"] = cond_by_design
df_f["identity"] = df_f["Label"].map({"self": 1, "stranger": 0}).astype(int)
df_f["cell"] = (df_f["identity"] * 2 + df_f["condition"]).astype(int)

# ------------------------------------------------------------------
# 反应与遗漏：**不再伪造任何反应方向**
# ------------------------------------------------------------------
df_f["T_s"] = pd.to_numeric(df_f["T"], errors="coerce")
df_f["W_s"] = pd.to_numeric(df_f["W"], errors="coerce")
df_f["deadline"] = df_f["T_s"] + df_f["W_s"]

df_f["rt"] = pd.to_numeric(df_f["RT"], errors="coerce")
df_f["omission"] = df_f["rt"].isna().astype(int)

# 按键编码：1 = 判断为 Matching
resp_key = np.where(df_f["condition"] == 1, df_f["Correct"], 1 - df_f["Correct"])
df_f["response"] = np.where(df_f["omission"] == 1, np.nan, resp_key)
# 正确性编码：1 = 作答正确
df_f["correct"] = np.where(df_f["omission"] == 1, np.nan, df_f["Correct"])

n_match = int(df_f["condition"].sum())
n_nonmatch = len(df_f) - n_match
print(f"\nMatching 试次: {n_match} ({n_match / len(df_f) * 100:.1f}%)")
print(f"NonMatching 试次: {n_nonmatch} ({n_nonmatch / len(df_f) * 100:.1f}%)")
print(f"遗漏试次: {int(df_f['omission'].sum())} ({df_f['omission'].mean() * 100:.1f}%) "
      f"→ rt / response / correct 均留空，不再写入 deadline")

MAIN_COLS = ["subj_idx", "rt", "response", "correct", "identity",
             "condition", "cell", "deadline", "omission"]
OMIT_COLS = ["subj_idx", "identity", "condition", "cell", "deadline",
             "T_ms", "W_ms", "P"]

print("\n" + "=" * 68)
print(f"{'组':>3} {'P':>4} {'T':>5} {'W':>5} {'被试':>5} {'有效':>7} {'遗漏':>7} "
      f"{'遗漏率':>7} {'判M比例':>8} {'匹配ACC':>8} {'不匹配ACC':>9}")
print("=" * 68)

for gid in sorted(df_f["groupID"].unique()):
    gdf = df_f[df_f["groupID"] == gid].copy()
    subj_map = {s: i for i, s in enumerate(sorted(gdf["subjectID"].unique()))}
    gdf["subj_idx"] = gdf["subjectID"].map(subj_map).astype(int)

    P_val = int(gdf["P"].iloc[0])
    T_val = int(round(gdf["T_s"].iloc[0] * 1000))
    W_val = int(round(gdf["W_s"].iloc[0] * 1000))
    tag = f"group{gid}_P{P_val}_T{T_val}_W{W_val}"

    # 有反应试次 → HDDM 输入
    gdf[gdf["omission"] == 0][MAIN_COLS].to_csv(OUT_DIR / f"hddm_data_{tag}.csv", index=False)

    # 遗漏试次 → 供 omission-aware 阶段使用
    omit = gdf[gdf["omission"] == 1].copy()
    omit["T_ms"] = T_val
    omit["W_ms"] = W_val
    omit[OMIT_COLS].to_csv(OUT_DIR / f"hddm_omission_{tag}.csv", index=False)

    ans = gdf[gdf["omission"] == 0]
    acc_m = ans.loc[ans["condition"] == 1, "correct"].mean()
    acc_n = ans.loc[ans["condition"] == 0, "correct"].mean()
    print(f"{gid:>3} {P_val:>4} {T_val:>5} {W_val:>5} {len(subj_map):>5} "
          f"{len(ans):>7} {len(omit):>7} {len(omit) / len(gdf) * 100:>6.1f}% "
          f"{ans['response'].mean() * 100:>7.1f}% {acc_m * 100:>7.1f}% {acc_n * 100:>8.1f}%")

# ------------------------------------------------------------------
# 全局自检：单 v 模型的可证伪推论
# ------------------------------------------------------------------
ans = df_f[df_f["omission"] == 0]
for ident, name in [(1, "self"), (0, "stranger")]:
    sub = ans[ans["identity"] == ident]
    acc_m = sub.loc[sub["condition"] == 1, "correct"].mean()
    acc_n = sub.loc[sub["condition"] == 0, "correct"].mean()
    print(f"  {name:<9} P(正确|匹配) + P(正确|不匹配) = {acc_m + acc_n:.3f}")

print("""
说明：若上两行之和显著偏离 1，则「匹配与不匹配共用同一个 v」的模型设定
      在数学上无法产生该数据（详见
      5_Reference/02_方法学审查/路线B模型规格与遗漏建模路线_20260930.md §2.2）。
      正确处理方式是让 v 按正确性编码（配合 z 按按键编码），见 step2 的 M2/M3。""")

print(f"\n有反应数据 -> {OUT_DIR}\\hddm_data_*.csv")
print(f"遗漏数据   -> {OUT_DIR}\\hddm_omission_*.csv")
print("=" * 68)
