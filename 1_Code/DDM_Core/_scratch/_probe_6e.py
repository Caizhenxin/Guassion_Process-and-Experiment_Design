# -*- coding: utf-8 -*-
"""6-E（刺激内 / 刺激后按键的延时可比性）取证：两场数据里的检测延时。"""
import csv
import statistics as st

FILES = {
    "group1_subject99(v4.6,576)": r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\EXP_data_group1_99.csv",
    "group2_subject99(截断,80行)": r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\exp_group2_subject99.txt",
}


def load(p):
    txt = open(p, encoding="utf-8-sig", errors="replace").read()
    if txt.lstrip().startswith("groupID\t") or "\t" in txt.splitlines()[0]:
        lines = [ln for ln in txt.splitlines() if ln.strip()]
        h = lines[0].split("\t")
        return [dict(zip(h, ln.split("\t"))) for ln in lines[1:]]
    return list(csv.DictReader(txt.splitlines()))


for name, p in FILES.items():
    rows = load(p)
    rows = [r for r in rows if r.get("stage") == "formal"]
    resp = [r for r in rows if r.get("Response") in ("f", "j")]
    T = [float(r["T"]) for r in resp]
    RT = [float(r["RT"]) for r in resp]
    dur = [float(r["stimulus_dur_actual"]) for r in resp]
    fr = [int(float(r["stimulus_frames"])) for r in resp]
    flip = 1.0 / 60.004
    inside = [(a, b, d, f) for a, b, d, f in zip(T, RT, dur, fr) if b < a]
    after = [(a, b, d, f) for a, b, d, f in zip(T, RT, dur, fr) if b >= a]
    print("=" * 70)
    print(name, "formal", len(rows), "responded", len(resp))
    print(" 刺激内按键 n=%d" % len(inside))
    if inside:
        lat = [d - b for _, b, d, _ in inside]
        print("   检测延时 dur-RT(ms):", [round(x * 1000, 1) for x in lat])
        print("   max %.1f ms (1 帧 = %.1f ms) 全部 ≤ 1 帧: %s" % (
            max(lat) * 1000, flip * 1000, all(x <= flip * 1.05 for x in lat)))
        print("   max RT/T: %.3f" % max(b / a for a, b, _, _ in inside))
    print(" 刺激后按键 n=%d" % len(after))
    if after:
        mask = [b - a for a, b, _, _ in after if b - a <= 0.200 + 1e-9]
        late = [b - a for a, b, _, _ in after if b - a > 0.200 + 1e-9]
        print("   落在掩蔽窗(0~200ms) n=%d RT−T(ms) %s" % (len(mask), [round(x * 1000, 1) for x in mask]))
        print("   掩蔽后(>200ms) n=%d RT−T(ms) min %.1f max %.1f" % (
            len(late), min(late) * 1000 if late else float("nan"), max(late) * 1000 if late else float("nan")))
        print("   dur−RT(ms):", [round((d - b) * 1000, 1) for _, b, d, _ in after][:12])
    print(" 可疑（RT < 50 ms）n=%d:" % sum(1 for b in RT if b < 0.050),
          [round(b * 1000, 1) for b in RT if b < 0.050])
