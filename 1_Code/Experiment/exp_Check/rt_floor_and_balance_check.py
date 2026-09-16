# -*- coding: utf-8 -*-
"""
rt_floor_and_balance_check.py  (v2)

对原始行为数据做三项独立核查，输出可直接引用到排查文档的数字。

  (1) RT 计时核查：实测 RT 是否满足用户假设 RT >= T，以及程序实际下限 RT >= T + 200ms；
      并按时间带统计（刺激期内 / 掩蔽期内 / 反应窗口内）。
      ★ 以【数据文件内部的 P/T/W 列】为准（因为历史数据的组号与当前代码 conditions 表存在错位）。

  (2) 规则索引审计：由每个文件的 (Shape,Label)->CorrectKey 反推它使用的是哪一行 rules，
      再与两种可能的索引方式比较：
         方式 A（当前代码）：modResult = mod(subjectID, 4)
         方式 B（错位写法）：modResult = mod(subjectID - 1, 4)   ← 与 getMatchKey 的索引一致
      用于发现"采集时编号/索引错位"的被试。

  (3) 平衡性审计：Identity-link（形状↔身份联结方向）与 F/J 按键平衡（代码层 + 数据层），
      并统计每名被试的 Matching / NonMatching 正确率，标记"程序期望与自己学到的相反"的被试。

数据：2_Data/Real_Data/UnExtact/raw/EXP_data_group*_*.csv
输出：命令行报告 + exp_Check/rt_floor_report.csv
                      exp_Check/subject_audit_report.csv
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
RAW_DIR = ROOT / "2_Data" / "Real_Data" / "UnExtact" / "raw"
OUT_DIR = ROOT / "1_Code" / "Experiment" / "exp_Check"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MASK_DUR = 0.2  # 掩蔽/空白段时长（秒），四个程序版本一致

# 代码中的 rules 表（四个版本完全一致），行索引 = modResult
RULES = {
    0: {"square": {"self": "f", "stranger": "j"}, "circle": {"self": "j", "stranger": "f"}},
    1: {"square": {"self": "j", "stranger": "f"}, "circle": {"self": "f", "stranger": "j"}},
    2: {"square": {"self": "j", "stranger": "f"}, "circle": {"self": "f", "stranger": "j"}},
    3: {"square": {"self": "f", "stranger": "j"}, "circle": {"self": "j", "stranger": "f"}},
}


def rule_pattern(row):
    """把一行 rules 压成可比较的签名：((shape,label) -> key) 的排序元组。

    注意：代码的 rules 表只有两种互异模式——
        P1: square-self=f, square-stranger=j, circle-self=j, circle-stranger=f  (mod4 ∈ {0,3})
        P2: square-self=j, square-stranger=f, circle-self=f, circle-stranger=j  (mod4 ∈ {1,2})
    因为 rules 表第 1 行与第 4 行相同、第 2 行与第 3 行相同（差异由 correctPairs 的奇偶决定）。
    """
    return tuple(sorted((sh, lb, RULES[row][sh][lb]) for sh in ("square", "circle")
                        for lb in ("self", "stranger")))


P1 = rule_pattern(0)
P2 = rule_pattern(1)
PATTERN_NAME = {P1: "P1(mod4∈{0,3})", P2: "P2(mod4∈{1,2})"}


def expected_pattern(subject_id):
    """按当前代码推断该编号应使用的按键模式。"""
    return P1 if subject_id % 4 in (0, 3) else P2


def match_key(subject_id):
    return ["f", "j", "j", "f"][(subject_id - 1) % 4]


def link_direction(subject_id):
    """correctPairs_0 / correctPairs_1：偶 → square=self；奇 → circle=self"""
    return "square=self" if subject_id % 2 == 0 else "circle=self"


def load_raw():
    files = sorted(RAW_DIR.glob("EXP_data_group*_*.csv"))
    frames = []
    meta = []
    for f in files:
        m = re.search(r"group(\d+)_(\d+)\.csv$", f.name)
        if not m:
            continue
        g, s = int(m.group(1)), int(m.group(2))
        df = pd.read_csv(f)
        df["__file"] = f.name
        df["__folder_group"] = g
        df["__folder_subject"] = s
        frames.append(df)
        d = df[df["stage"].astype(str).str.strip() == "formal"]
        meta.append(dict(
            file=f.name, folder_group=g, folder_subject=s,
            in_group=int(pd.to_numeric(d["groupID"], errors="coerce").median()),
            in_subject=int(pd.to_numeric(d["subjectID"], errors="coerce").median()),
            P=float(pd.to_numeric(d["P"], errors="coerce").median()),
            T=float(pd.to_numeric(d["T"], errors="coerce").median()),
            W=float(pd.to_numeric(d["W"], errors="coerce").median()),
            n_formal=len(d),
        ))
    return pd.concat(frames, ignore_index=True), pd.DataFrame(meta)


# --------------------------------------------------------------------------
# (1) RT 下限核查（以文件内 T/W 为准）
# --------------------------------------------------------------------------
def rt_floor_check(all_df, meta):
    print("=" * 104)
    print("(1) RT 计时核查（以数据文件内部的 T/W 为准；掩蔽段 200ms）")
    print("=" * 104)
    out = []
    key_cols = ["folder_group", "in_group", "P", "T", "W"]
    for k, grp in meta.groupby(key_cols):
        g, ig, P, T, W = k
        subs = set(grp.folder_subject)
        d = all_df[(all_df["__folder_group"] == g)
                   & (all_df["__folder_subject"].isin(subs))
                   & (all_df["stage"].astype(str).str.strip() == "formal")]
        rt = pd.to_numeric(d["RT"], errors="coerce")
        v = rt.dropna()
        out.append(dict(
            folder_group=g, in_group=ig, n_subj=len(subs),
            P=int(P), T_ms=int(T * 1000), W_ms=int(W * 1000), deadline_ms=int((T + W) * 1000),
            n_formal=len(d), n_rt=len(v), omission_pct=round((len(d) - len(v)) / len(d) * 100, 1),
            min_rt_ms=round(v.min() * 1000, 1),
            p1_ms=round(v.quantile(0.01) * 1000, 1),
            median_ms=round(v.median() * 1000, 1),
            max_rt_ms=round(v.max() * 1000, 1),
            lt_T=int((v < T).sum()),
            lt_floor=int((v < T + MASK_DUR - 0.003).sum()),
            near_floor=int(((v >= T + MASK_DUR - 0.003) & (v < T + MASK_DUR + 0.05)).sum()),
            gt_deadline=int((v > T + W).sum()),
            gt_deadline_plus60=int((v > T + W + 0.06).sum()),
        ))
    r = pd.DataFrame(out).sort_values("folder_group")
    r["pct_near_floor"] = (r["near_floor"] / r["n_rt"] * 100).round(1)
    print(r.to_string(index=False))
    print()
    print("全样本合计：被试 %d 人，formal 试次 %d，其中有反应 %d，"
          "RT < T 的试次 %d，RT < T+200ms 的试次 %d，RT > deadline+60ms 的试次 %d"
          % (r["n_subj"].sum(), r["n_formal"].sum(), r["n_rt"].sum(),
             r["lt_T"].sum(), r["lt_floor"].sum(), r["gt_deadline_plus60"].sum()))
    print()
    r.to_csv(OUT_DIR / "rt_floor_report.csv", index=False, encoding="utf-8-sig")
    return r


# --------------------------------------------------------------------------
# (2)(3) 规则索引审计 + 平衡性审计
# --------------------------------------------------------------------------
def subject_audit(all_df, meta):
    print("=" * 104)
    print("(2) 规则索引审计：每个文件的 CorrectKey 模式对应哪一行 rules？")
    print("=" * 104)
    rows = []
    for _, m in meta.iterrows():
        d = all_df[(all_df["__file"] == m["file"])
                   & (all_df["stage"].astype(str).str.strip() == "formal")].copy()
        sid = int(m["in_subject"])
        sig = tuple(sorted({(str(a), str(b), str(k).strip())
                            for a, b, k in zip(d["Shape"], d["Label"], d["CorrectKey"])}))
        pat_obs = PATTERN_NAME.get(sig, "other")
        pat_exp = PATTERN_NAME[expected_pattern(sid)]
        pattern_ok = bool(sig == expected_pattern(sid))

        mk = match_key(sid)
        ismatch = d["CorrectKey"].astype(str).str.strip() == mk
        resp = d["Response"].astype(str).str.strip()
        acc_match = (resp[ismatch] == d["CorrectKey"].astype(str).str.strip()[ismatch]).mean() if ismatch.any() else np.nan
        acc_non = (resp[~ismatch] == d["CorrectKey"].astype(str).str.strip()[~ismatch]).mean() if (~ismatch).any() else np.nan
        # 反向判定：若被试系统性地按"另一套映射"作答，则 acc_match 低而 acc_non 高
        inverted = bool((not np.isnan(acc_match)) and (not np.isnan(acc_non))
                        and acc_match < 0.5 and acc_non > 0.8)

        rows.append(dict(
            file=m["file"], folder_group=int(m["folder_group"]), folder_subject=int(m["folder_subject"]),
            in_group=int(m["in_group"]), in_subject=sid,
            T_ms=int(m["T"] * 1000), W_ms=int(m["W"] * 1000), n_formal=int(m["n_formal"]),
            rule_pattern_observed=pat_obs, rule_pattern_expected=pat_exp,
            pattern_ok=pattern_ok,
            match_key=mk, link=link_direction(sid),
            acc_match=round(float(acc_match), 3) if acc_match == acc_match else np.nan,
            acc_nonmatch=round(float(acc_non), 3) if acc_non == acc_non else np.nan,
            inverted_flag=inverted,
            group_number_mismatch=bool(int(m["folder_group"]) != int(m["in_group"])),
        ))
    s = pd.DataFrame(rows)
    ok = int(s.pattern_ok.sum())
    print(f"按键模式与编号规则一致：{ok}/{len(s)} 人")
    bad = s[~s.pattern_ok]
    if len(bad):
        print("\n★ 按键模式与编号不匹配的文件（需核查/剔除）：")
        print(bad[["file", "in_group", "in_subject", "T_ms", "W_ms",
                   "rule_pattern_observed", "rule_pattern_expected",
                   "match_key", "link", "acc_match", "acc_nonmatch"]].to_string(index=False))
    print()
    print("=" * 104)
    print("(3) 平衡性审计：各组 联结方向 × 匹配键 分布（代码层理想：四格各 1/4）")
    print("=" * 104)
    for g, d in s.groupby("folder_group"):
        tab = d.groupby(["link", "match_key"]).size().unstack(fill_value=0)
        print(f"组{g}  (n={len(d)}，T={d.T_ms.iloc[0]}ms, W={d.W_ms.iloc[0]}ms):")
        print("   " + tab.to_string().replace("\n", "\n   "))
    print()
    print("全样本 联结方向 × 匹配键：")
    print(s.groupby(["link", "match_key"]).size().unstack(fill_value=0).to_string())
    print()
    print("每组 Matching / NonMatching 正确率（被试均值）与异常标记：")
    agg = s.groupby("folder_group").agg(
        n=("file", "count"),
        acc_match_mean=("acc_match", "mean"),
        acc_nonmatch_mean=("acc_nonmatch", "mean"),
        n_inverted=("inverted_flag", "sum"),
    ).round(3)
    print(agg.to_string())
    print()
    s.to_csv(OUT_DIR / "subject_audit_report.csv", index=False, encoding="utf-8-sig")
    return s


def main():
    all_df, meta = load_raw()
    print(f"读取文件 {all_df['__file'].nunique()} 个，被试 {len(meta)} 人")
    print("提示：folder_group 与 in_group 不一致即为组号错位（历史数据存在此问题）")
    print()
    rt_floor_check(all_df, meta)
    s = subject_audit(all_df, meta)
    print("报告已保存：", OUT_DIR / "rt_floor_report.csv", "|", OUT_DIR / "subject_audit_report.csv")


if __name__ == "__main__":
    main()
