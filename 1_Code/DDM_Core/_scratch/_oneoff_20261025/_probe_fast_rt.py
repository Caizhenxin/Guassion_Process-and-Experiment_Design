"""抢跑试次（RT < 200 ms）的成因诊断：是均匀污染、重复按键、还是记录故障。

只读，不改数据。输出六块：
  ① 总量与分布（按身份 / P / T 档 / 被试）
  ② 正确率：快试次是否接近机会水平（猜测）还是系统性错误（perseveration）
  ③ RT 细分布：0–300 ms 每 20 ms 一箱（均匀 vs 单调下降 vs 尖峰）
  ④ 与前试次的关系：前试次是否也快 / 是否同键（惯性连按）
  ⑤ premature_press 标记的重叠率（程序是否已把它标成提前按键）
  ⑥ 随机性检验：快试次的 CorrectKey 是否与 Response 独立、是否与被试基线一致
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import real_data_check as R  # noqa: E402

DATA = ROOT / "2_Data" / "Real_Data" / "New_Design"
pd.set_option("display.width", 160)


def main() -> None:
    files = sorted(DATA.glob("Condition */*.csv"))
    raw = R.load_files(files)
    d = raw[raw["is_formal"]].copy()

    print(f"正式段试次 {len(d)}，被试 {d.subject_id.nunique()}")
    d["fast"] = ((d.responded == 1) & (d.rt_ms > 0) & (d.rt_ms < 200)).astype(int)
    print(f"RT<200 ms 且已响应：{int(d.fast.sum())}（{d.fast.mean()*100:.2f}%）\n")

    print("== ① 按身份 ==")
    print(d.groupby("is_self").agg(n=("fast", "size"), n_fast=("fast", "sum"),
                                   pct=("fast", "mean")).round(4))
    print("\n== ① 按 P ==")
    print(d.groupby("P").agg(n=("fast", "size"), n_fast=("fast", "sum"),
                             pct=("fast", "mean")).round(4))
    print("\n== ① 按 T 档 ==")
    print(d.groupby("T_lvl").agg(n=("fast", "size"), n_fast=("fast", "sum"),
                                 pct=("fast", "mean")).round(4))
    print("\n== ① 按被试（只列有快试次的）==")
    t = d.groupby("subject_id").agg(n=("fast", "size"), n_fast=("fast", "sum"),
                                    pct=("fast", "mean")).round(4)
    print(t[t.n_fast > 0].sort_values("pct", ascending=False))

    f = d[d.fast == 1]
    print("\n== ② 正确率 ==")
    print(f"快试次（n={len(f)}）正确率 {f.correct.mean():.3f}")
    print(f"慢试次（n={len(d) - len(f)}）正确率 {d[d.fast == 0].correct.mean():.3f}")
    print(f"快试次按身份：自我 {f[f.is_self == 1].correct.mean():.3f} / "
          f"他人 {f[f.is_self == 0].correct.mean():.3f}")
    # 被试自身基线（非快试次）的正确率，判断快试次是否「系统性反着按」
    base = d[d.fast == 0].groupby("subject_id").correct.mean()
    f = f.assign(base=f.subject_id.map(base))
    print(f"快试次正确率 vs 本人基线：快试次更低 {int((f.correct < f.base).sum())}/{len(f)} 人场内比较"
          f"（逐人差均值 {float((f.correct - f.base).mean()):+.3f}）")

    print("\n== ③ RT 细分布（0–300 ms，20 ms 一箱）==")
    bins = np.arange(0, 320, 20)
    cnt, _ = np.histogram(f.rt_ms, bins=bins)
    for lo, c in zip(bins[:-1], cnt):
        bar = "█" * int(round(c / max(cnt.max(), 1) * 40))
        print(f"  {lo:>3.0f}–{lo+20:>3.0f} ms  {c:>3d}  {bar}")

    print("\n== ④ 与前试次的关系（同被试、同 block 内按 trialID 排序）==")
    d2 = d.sort_values(["subject_id", "block", "trialID"]).reset_index(drop=True)
    g = d2.groupby("subject_id")
    d2["prev_rt"] = g["rt_ms"].shift(1)
    d2["prev_correct"] = g["correct"].shift(1)
    key = d2["CorrectKey"].astype(str).str.lower().str.strip()
    resp = d2["Response"].astype(str).str.lower().str.strip()
    d2["prev_key"] = key.shift(1)
    d2["prev_resp"] = resp.shift(1)
    d2["same_as_prev_resp"] = (resp == d2["prev_resp"]).astype(int)
    d2["fast"] = ((d2.responded == 1) & (d2.rt_ms > 0) & (d2.rt_ms < 200)).astype(int)
    ff = d2[d2.fast == 1]
    nf = d2[(d2.fast == 0) & d2.prev_rt.notna()]
    print(f"快试次里前试次也快的比例 {float((ff.prev_rt < 200).mean()):.3f}"
          f"（慢试次 {float((nf.prev_rt < 200).mean()):.3f}）")
    print(f"快试次里「与前试次同键」比例 {float(ff.same_as_prev_resp.mean()):.3f}"
          f"（慢试次 {float(nf.same_as_prev_resp.mean()):.3f}）")
    print(f"快试次里前试次也快的条件概率 = P(prev<200) 对照 "
          f"P(prev<200 | 本试次慢) = {float((nf.prev_rt < 200).mean()):.3f}")
    print(f"快试次的前试次 RT 中位 {float(ff.prev_rt.median()):.0f} ms"
          f"（全体 {float(d2.rt_ms.median()):.0f} ms）")

    print("\n== ⑤ premature_press 标记重叠 ==")
    print(d.groupby("fast").premature.agg(["mean", "sum", "size"]).round(4))

    print("\n== ⑥ 随机性 ==")
    print(f"快试次 Response 分布：{resp[d2.fast == 1].value_counts().to_dict()}")
    print(f"快试次 CorrectKey 分布：{key[d2.fast == 1].value_counts().to_dict()}")
    print(f"快试次是否响应=1（必然）：{int((f.responded == 1).sum())}")
    print(f"RT 最小值 {float(d.rt_ms.min()):.0f} ms；RT<150 ms 的个数 {int((d.rt_ms < 150).sum())}"
          f"；RT<100 ms 的个数 {int((d.rt_ms < 100).sum())}")


if __name__ == "__main__":
    main()
