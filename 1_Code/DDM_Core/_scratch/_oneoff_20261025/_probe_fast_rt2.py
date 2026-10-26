"""抢跑试次的第二轮诊断：区分「程序/掉帧」「注意力滑落（成簇）」与「被试 3-1 单场异常」。

① 剔除 3-1 后的快试次画像（占比 / 正确率 / 身份）
② 成簇性：快试次是否集中在前一两个试次、是否集中在同一 block、block 内位置
③ 与掉帧的关系：快试次的 stimulus_dur_actual 偏差、stimulus_frames
④ 与「同值 RT」的关系：是否有大量完全相同的 RT（程序复写嫌疑）
⑤ 3-1 的快试次在不同 block / 不同 T 档的分布
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
    raw = R.load_files(sorted(DATA.glob("Condition */*.csv")))
    d = raw[raw["is_formal"]].copy()
    d["fast"] = ((d.responded == 1) & (d.rt_ms > 0) & (d.rt_ms < 200)).astype(int)

    print("== ① 剔除 3-1 后 ==")
    e = d[d.subject_id != "3-1"].copy()
    print(f"n={len(e)}，快试次 {int(e.fast.sum())}（{e.fast.mean()*100:.2f}%）")
    print("按 P：" + str(e.groupby("P").fast.mean().round(4).to_dict()))
    print("按身份：" + str(e.groupby("is_self").fast.mean().round(4).to_dict()))
    ff = e[e.fast == 1]
    print(f"快试次正确率 {ff.correct.mean():.3f}（该子集总体 {e.correct.mean():.3f}）")

    print("\n== ② 成簇性（剔除 3-1）==")
    e = e.sort_values(["subject_id", "block", "trialID"]).reset_index(drop=True)
    grp = e.groupby("subject_id")
    e["prev_fast"] = grp["fast"].shift(1)
    e["prev2_fast"] = grp["fast"].shift(2)
    e["pos_in_block"] = e.groupby(["subject_id", "block"]).cumcount() + 1
    f_only = e[e.fast == 1]
    f_only = f_only[f_only.prev_fast.notna()]
    print(f"P(前试次也快 | 本试次快) = {float(f_only.prev_fast.mean()):.3f}"
          f"（基线 P = {float(e.fast.mean()):.3f}）")
    print(f"P(前两试次都快 | 本试次快) = {float(f_only.prev2_fast.mean()):.3f}")
    print("block 内位置分布（前 8 个位置）："
          + str(f_only.pos_in_block.value_counts().sort_index().head(8).to_dict()))
    print(f"block 内位置中位 {float(f_only.pos_in_block.median()):.0f}"
          f"（全体 {float(e.pos_in_block.median()):.0f}）")
    # 每个 block 48 试次；看快试次是否集中在少数 block
    blk = e.groupby(["subject_id", "block"]).fast.sum()
    print(f"有快试次的 block 数 {int((blk > 0).sum())} / {len(blk)}；"
          f"其中单 block 内 >=5 个的 {int((blk >= 5).sum())} 个")

    print("\n== ③ 与掉帧的关系 ==")
    print("刺激时长偏差 |dev|（ms）分档 × 快慢：")
    e["dev_abs"] = e.dur_dev_ms.abs()
    e["dev_bin"] = pd.cut(e.dev_abs, [-1, 1, 20, 50, 1e9],
                          labels=["<=1ms", "1-20ms", "20-50ms", ">50ms"])
    tab = e.pivot_table(index="dev_bin", columns="fast", values="rt_ms",
                        aggfunc="size", observed=False).fillna(0).astype(int)
    tab.columns = [f"慢" if c == 0 else "快" for c in tab.columns]
    tab["快占比"] = (tab["快"] / tab.sum(axis=1)).round(3)
    print(tab)
    print(f"快试次的 |dev| 中位 {float(f_only.dev_abs.median()):.1f} ms"
          f"（全体 {float(e.dev_abs.median()):.1f} ms）")

    print("\n== ④ 相同 RT 值复写嫌疑 ==")
    vc = e.rt_ms.round(1).value_counts()
    print(f"RT 精确重复最多的前 5 个值：{vc.head(5).to_dict()}")
    dup = vc[vc >= 5]
    print(f"出现 >=5 次的 RT 值个数 {len(dup)}，覆盖试次 {int(dup.sum())}")

    print("\n== ⑤ 3-1 的 180 个快试次 ==")
    s = d[d.subject_id == "3-1"].sort_values(["block", "trialID"])
    s["pos_in_block"] = s.groupby("block").cumcount() + 1
    print("按 block 计数：" + str(s[s.fast == 1].block.value_counts().sort_index().to_dict()))
    print("按 T 档：" + str(s[s.fast == 1].T_lvl.value_counts().sort_index().to_dict()))
    print(f"3-1 快试次正确率 {float(s[s.fast == 1].correct.mean()):.3f}，"
          f"该场总体 {float(s.correct.mean()):.3f}")
    print(f"3-1 的 RT：min {float(s.rt_ms.min()):.0f} / q10 {float(s.rt_ms.quantile(.1)):.0f}"
          f" / 中位 {float(s.rt_ms.median()):.0f}")


if __name__ == "__main__":
    main()
