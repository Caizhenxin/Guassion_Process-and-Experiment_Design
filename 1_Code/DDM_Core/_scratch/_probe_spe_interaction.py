# -*- coding: utf-8 -*-
"""SPE 是漂移（敏感性）还是判据（反应偏向）？——Matching × Identity 的 2×2 检验。

判据偏移（起点/边界偏向"匹配"）预测：
  - 自我条件在 match 试次更快、在 nonmatch 试次更慢（ΔRT 的 Matching 交互）
  - 命中率↑、虚报率↑ 同时发生 ⇒ c 下降而 d' 不变
漂移差异（证据质量）预测：
  - 两个匹配条件同向变快
  - d' 上升、c 基本不变
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path[:0] = [str(REPO / "1_Code" / "DDM_Core"),
                str(REPO / "1_Code" / "Experiment")]

import stage8_run as S          # noqa: E402
from mapping import MappingParams  # noqa: E402

DATA = REPO / "2_Data" / "Real_Data" / "New_Design" / "_stage8_in"


def sdt(hits, n_sig, fa, n_noise):
    """log-linear 校正后的 d' 与 c。"""
    h = (hits + 0.5) / (n_sig + 1.0)
    f = (fa + 0.5) / (n_noise + 1.0)
    zh, zf = stats.norm.ppf(h), stats.norm.ppf(f)
    return float(zh - zf), float(-0.5 * (zh + zf))


def main():
    people, _ = S.collect([DATA], None, MappingParams(shape_model="lin"))
    rows = []
    for p in people:
        tr = p["tr"]
        om = np.asarray(tr["omission"]) == 0
        side = np.asarray(tr["side"])[om]
        match = np.asarray(tr["is_match"])[om] == 1
        rt = np.asarray(tr["rt"])[om]
        self_ = np.asarray(tr["is_self"])[om] == 1
        resp_match = side == 1
        corr = resp_match == match

        rec = {"sid": p.get("sid", "?")}
        for name, m in (("sm", self_ & match), ("sn", self_ & ~match),
                        ("om", ~self_ & match), ("on", ~self_ & ~match)):
            rec[name + "_n"] = int(m.sum())
            rec[name + "_rt"] = float(np.median(rt[m])) if m.any() else np.nan
            rec[name + "_acc"] = float(corr[m].mean()) if m.any() else np.nan
        # SDT
        for tag, sel in (("self", self_), ("other", ~self_)):
            hit = int((resp_match[sel & match]).sum())
            n_sig = int((sel & match).sum())
            fa = int((resp_match[sel & ~match]).sum())
            n_noise = int((sel & ~match).sum())
            rec[tag + "_d"], rec[tag + "_c"] = sdt(hit, n_sig, fa, n_noise)
            rec[tag + "_hit"] = hit / max(n_sig, 1)
            rec[tag + "_fa"] = fa / max(n_noise, 1)
        rows.append(rec)

    ids = [r["sid"] for r in rows]
    def col(k):
        return np.array([r[k] for r in rows], float)

    print(f"被试 {len(rows)} 人：{ids}\n")
    print("一、2×2 单元中位 RT / 正确率（每格是被试内中位，再对 17 人取中位）")
    print(f"{'单元':<22}{'n/人':>7}{'RT(ms)':>10}{'ACC':>8}")
    for name, lab in (("sm", "自我 × 匹配"), ("sn", "自我 × 非匹配"),
                      ("om", "他人 × 匹配"), ("on", "他人 × 非匹配")):
        print(f"{lab:<22}{col(name + '_n').mean():>7.0f}"
              f"{np.nanmedian(col(name + '_rt')) * 1000:>10.0f}"
              f"{np.nanmedian(col(name + '_acc')):>8.3f}")

    d_rt_m = (col("sm_rt") - col("om_rt")) * 1000
    d_rt_n = (col("sn_rt") - col("on_rt")) * 1000
    d_ac_m = col("sm_acc") - col("om_acc")
    d_ac_n = col("sn_acc") - col("on_acc")
    gap_rt = d_rt_m - d_rt_n
    gap_ac = d_ac_m - d_ac_n

    def rep(name, x):
        t, p = stats.ttest_1samp(x, 0.0)
        d = x.mean() / x.std(ddof=1)
        w = stats.wilcoxon(x).pvalue if np.any(x != 0) else 1.0
        sign_pos = int((x > 0).sum())
        print(f"{name:<26}{x.mean():>+9.1f}{x.std(ddof=1):>9.1f}"
              f"{d:>+7.2f}{t:>+7.2f}{p:>9.4f}{w:>9.4f}{sign_pos:>5d}/{len(x)}")

    print("\n二、逐被试效应（单位 ms / 比例）")
    print(f"{'量':<26}{'均值':>9}{'SD':>9}{'dz':>7}{'t':>7}{'p':>9}{'p(W)':>9}{'同号':>7}")
    rep("ΔRT 匹配 (自我−他人)", d_rt_m)
    rep("ΔRT 非匹配 (自我−他人)", d_rt_n)
    rep("ΔACC 匹配", d_ac_m * 100)
    rep("ΔACC 非匹配", d_ac_n * 100)
    rep("交互: ΔRT(匹配−非匹配)", gap_rt)
    rep("交互: ΔACC(匹配−非匹配) 百分点", gap_ac * 100)

    print("\n三、信号检测量（log-linear 校正）")
    dd = col("self_d") - col("other_d")
    dc = col("self_c") - col("other_c")
    print(f"{'量':<26}{'均值':>9}{'SD':>9}{'dz':>7}{'t':>7}{'p':>9}{'p(W)':>9}{'同号':>7}")
    rep("Δd' (自我−他人)", dd)
    rep("Δc  (自我−他人)", dc)
    print(f"\n  命中率：自我 {col('self_hit').mean():.3f} 他人 {col('other_hit').mean():.3f}"
          f" ⇒ Δ {col('self_hit').mean() - col('other_hit').mean():+.3f}")
    print(f"  虚报率：自我 {col('self_fa').mean():.3f} 他人 {col('other_fa').mean():.3f}"
          f" ⇒ Δ {col('self_fa').mean() - col('other_fa').mean():+.3f}")

    # 混合 2×2 ANOVA（被试内，两因素各 2 水平）——手算
    Y = np.column_stack([
        col("sm_rt"), col("sn_rt"), col("om_rt"), col("on_rt")
    ]) * 1000.0
    n = len(Y)
    gm = Y.mean()
    a = Y[:, [0, 1, 2, 3]].mean(axis=1)          # 被试均值
    idn = np.column_stack([Y[:, 0], Y[:, 1]]).mean(1) - np.column_stack([Y[:, 2], Y[:, 3]]).mean(1)
    mtc = np.column_stack([Y[:, 0], Y[:, 2]]).mean(1) - np.column_stack([Y[:, 1], Y[:, 3]]).mean(1)
    inter = (Y[:, 0] - Y[:, 1]) - (Y[:, 2] - Y[:, 3])
    for nm, eff in (("Identity", idn), ("Matching", mtc), ("Id×Match", inter)):
        t, p = stats.ttest_1samp(eff, 0.0)
        print(f"  ANOVA(被试内) {nm:<10} 均值 {eff.mean():+8.1f} ms  F(1,{n-1})={t**2:6.2f}  p={p:.4f}")

    out = REPO / "2_Data" / "Real_Data" / "New_Design" / "_pipeline"
    out.mkdir(parents=True, exist_ok=True)
    import json
    (out / "spe_interaction_20261028.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nsaved: {out / 'spe_interaction_20261028.json'}")


if __name__ == "__main__":
    main()
